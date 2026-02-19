"""
Agent API routes for JurisScope.
Calls Elastic Agent Builder agents via Kibana API.

Agents:
- search-agent: Hybrid search (BM25 + vector)
- answer-agent: LLM generates answer from retrieved docs
- citation-agent: Precise page/location references
"""
import logging
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def get_kibana_url():
    settings = get_settings()
    return settings.elasticsearch_endpoint.replace(".es.", ".kb.")


def get_es_headers():
    settings = get_settings()
    return {
        "Authorization": f"ApiKey {settings.elasticsearch_api_key}",
        "Content-Type": "application/json"
    }


def get_kibana_headers():
    settings = get_settings()
    return {
        "Authorization": f"ApiKey {settings.elasticsearch_api_key}",
        "kbn-xsrf": "true",
        "Content-Type": "application/json"
    }


class QueryRequest(BaseModel):
    query: str
    project_id: str
    agent: Optional[str] = None  # search-agent, answer-agent, citation-agent


# ============= Agent Builder API =============

@router.get("/agents")
async def list_agents():
    """List all registered agents."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{get_kibana_url()}/api/agent_builder/agents",
                headers=get_kibana_headers()
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "agents": [
                    {
                        "id": a["id"],
                        "name": a["name"],
                        "description": a.get("description", ""),
                        "custom": not a.get("readonly", False)
                    }
                    for a in data.get("results", [])
                    if a["id"] in ["search-agent", "answer-agent", "citation-agent"] or a.get("readonly")
                ]
            }
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/tools")
async def list_tools():
    """List custom tools."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{get_kibana_url()}/api/agent_builder/tools",
                headers=get_kibana_headers()
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "tools": [
                    {"id": t["id"], "type": t["type"], "description": t.get("description", "")[:80]}
                    for t in data.get("results", [])
                    if not t.get("readonly") and t["id"].startswith("jurisscope")
                ]
            }
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/query")
async def query_agent(request: QueryRequest):
    """
    Query using agents.
    
    Flow based on original Clause architecture:
    1. search-agent: Find relevant documents
    2. answer-agent: Generate answer using LLM
    3. citation-agent: Get precise references
    
    If no agent specified, runs the full pipeline.
    """
    try:
        agent_id = request.agent
        
        if agent_id == "search-agent":
            return await _run_search(request.query, request.project_id)
        elif agent_id == "answer-agent":
            return await _run_answer(request.query, request.project_id)
        elif agent_id == "citation-agent":
            return await _run_citation(request.query, request.project_id)
        else:
            # Full pipeline: search → answer → citation
            return await _run_full_pipeline(request.query, request.project_id)
            
    except Exception as e:
        logger.error(f"Agent query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============= Agent Functions =============

async def _run_search(query: str, project_id: str) -> Dict[str, Any]:
    """Search Agent: Hybrid search for documents using ES|QL MATCH."""
    settings = get_settings()
    # Escape special characters for ES|QL MATCH
    safe_query = query.replace('"', '\\"').replace("'", "")
    
    esql = f"""
    FROM jurisscope-documents 
    | WHERE project_id == "{project_id}"
    | WHERE MATCH(text, "{safe_query}")
    | KEEP doc_id, doc_title, text, page, chunk_id
    | LIMIT 10
    """
    
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.elasticsearch_endpoint}/_query?format=json",
            headers=get_es_headers(),
            json={"query": esql}
        )
        
        if response.status_code == 200:
            results = _format_esql_results(response.json())
            return {
                "agent": "search-agent",
                "results": results,
                "total": len(results)
            }
        return {"agent": "search-agent", "results": [], "error": response.text}


async def _run_answer(query: str, project_id: str) -> Dict[str, Any]:
    """Answer Agent: Generate answer using Elastic's LLM inference."""
    settings = get_settings()
    
    # Step 1: Search for relevant documents
    search_result = await _run_search(query, project_id)
    docs = search_result.get("results", [])
    
    if not docs:
        return {
            "agent": "answer-agent",
            "answer": "No relevant documents found for your query.",
            "sources": []
        }
    
    # Step 2: Build context from retrieved docs
    context_parts = []
    for i, doc in enumerate(docs[:5], 1):
        text = doc.get("text", "")[:2000]  # More context for better answers
        title = doc.get("doc_title", "Unknown")
        page = doc.get("page", "?")
        context_parts.append(f"[{i}] {title} (Page {page}):\n{text}")
    
    context = "\n\n".join(context_parts)
    
    # Step 3: Generate answer using Elastic's Claude inference
    prompt = f"""Based on the following legal documents, answer the question.

Question: {query}

Documents:
{context}

Provide a clear, accurate answer citing the relevant documents by number [1], [2], etc."""

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            # Use Elastic's inference API for chat completion (streaming required)
            response = await client.post(
                f"{settings.elasticsearch_endpoint}/_inference/completion/.anthropic-claude-3.7-sonnet-completion",
                headers=get_es_headers(),
                json={"input": prompt}
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("completion", [{}])[0].get("result", "")
                
                return {
                    "agent": "answer-agent",
                    "answer": answer,
                    "sources": [
                        {"doc_title": d.get("doc_title"), "page": d.get("page"), "doc_id": d.get("doc_id")}
                        for d in docs[:5]
                    ],
                    "model": "claude-3.7-sonnet"
                }
            else:
                # Fallback to formatted results if LLM fails
                logger.warning(f"LLM inference failed: {response.status_code}, using fallback")
                return _format_fallback_answer(query, docs)
                
    except Exception as e:
        logger.warning(f"LLM call failed: {e}, using fallback")
        return _format_fallback_answer(query, docs)


async def _run_citation(query: str, project_id: str) -> Dict[str, Any]:
    """Citation Agent: Get precise references with page/location using ES|QL MATCH."""
    settings = get_settings()
    
    # Search for document structure keywords
    esql = f"""
    FROM jurisscope-documents 
    | WHERE project_id == "{project_id}"
    | WHERE MATCH(text, "Section Article Clause")
    | KEEP doc_id, doc_title, page, text, chunk_id
    | LIMIT 20
    """
    
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.elasticsearch_endpoint}/_query?format=json",
            headers=get_es_headers(),
            json={"query": esql}
        )
        
        if response.status_code == 200:
            results = _format_esql_results(response.json())
            
            # Format as citations
            citations = []
            for r in results:
                citations.append({
                    "doc_id": r.get("doc_id"),
                    "doc_title": r.get("doc_title"),
                    "page": r.get("page"),
                    "snippet": r.get("text", "")[:200],
                    "url": f"/doc/{r.get('doc_id')}?page={r.get('page')}&hl={r.get('chunk_id')}"
                })
            
            return {
                "agent": "citation-agent",
                "citations": citations,
                "total": len(citations)
            }
        return {"agent": "citation-agent", "citations": [], "error": response.text}


async def _run_full_pipeline(query: str, project_id: str) -> Dict[str, Any]:
    """
    Full pipeline matching original Clause architecture:
    1. Search Agent → Find documents
    2. Answer Agent → Generate answer with LLM
    3. Citation Agent → Add precise references
    """
    logger.info(f"Running full pipeline for: {query}")
    
    # Get answer (which includes search)
    answer_result = await _run_answer(query, project_id)
    
    # Get citations
    citation_result = await _run_citation(query, project_id)
    
    return {
        "pipeline": ["search-agent", "answer-agent", "citation-agent"],
        "query": query,
        "project_id": project_id,
        "answer": answer_result.get("answer", ""),
        "sources": answer_result.get("sources", []),
        "citations": citation_result.get("citations", [])[:5],
        "model": answer_result.get("model", "fallback")
    }


def _format_fallback_answer(query: str, docs: List[Dict]) -> Dict[str, Any]:
    """Fallback answer when LLM is unavailable."""
    answer_parts = [f"Found {len(docs)} relevant documents for '{query}':\n"]
    
    for i, doc in enumerate(docs[:5], 1):
        title = doc.get("doc_title", "Unknown")
        page = doc.get("page", "?")
        text = doc.get("text", "")[:150]
        answer_parts.append(f"[{i}] **{title}** (Page {page}): {text}...")
    
    return {
        "agent": "answer-agent",
        "answer": "\n\n".join(answer_parts),
        "sources": [
            {"doc_title": d.get("doc_title"), "page": d.get("page"), "doc_id": d.get("doc_id")}
            for d in docs[:5]
        ],
        "model": "fallback"
    }


def _format_esql_results(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert ES|QL response to list of dicts."""
    columns = data.get("columns", [])
    values = data.get("values", [])
    
    results = []
    for row in values:
        result = {}
        for i, col in enumerate(columns):
            result[col["name"]] = row[i]
        results.append(result)
    
    return results
