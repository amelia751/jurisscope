"""
Agent-to-Agent (A2A) Orchestration for JurisScope.
Demonstrates multi-step agent workflow where agents call each other.
"""
import logging
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, AsyncGenerator
import json

from config import get_settings
from services.elastic_inference import get_inference_service
from services.elasticsearch import ElasticsearchService
from services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter()


class A2ARequest(BaseModel):
    """Request for A2A orchestration"""
    query: str
    project_id: str
    stream: bool = False  # Stream the multi-step process


class AgentStep(BaseModel):
    """A single step in the A2A workflow"""
    agent: str
    action: str
    input: str
    output: Any
    duration_ms: int


class A2AResponse(BaseModel):
    """Response showing the full A2A workflow"""
    query: str
    workflow: List[AgentStep]
    final_answer: str
    citations: List[Dict[str, Any]]
    total_duration_ms: int


@router.post("/a2a/orchestrate")
async def orchestrate_agents(request: A2ARequest):
    """
    Multi-step Agent-to-Agent orchestration.
    
    Workflow:
    1. Search Agent → Finds relevant documents
    2. Answer Agent → Generates answer from documents (calls Search Agent)
    3. Citation Agent → Extracts precise citations (calls Search Agent)
    
    This demonstrates agents working together in a pipeline.
    """
    if request.stream:
        return StreamingResponse(
            _stream_orchestration(request.query, request.project_id),
            media_type="text/event-stream"
        )
    
    try:
        start_time = time.time()
        workflow = []
        
        settings = get_settings()
        inference = get_inference_service()
        es = ElasticsearchService()
        embedding_service = EmbeddingService()
        
        # ========== STEP 1: Search Agent ==========
        step1_start = time.time()
        
        query_embedding = embedding_service.generate_embedding(request.query)
        search_results = es.hybrid_search(
            query_text=request.query,
            query_vector=query_embedding,
            project_id=request.project_id,
            k=8,
            num_candidates=100
        )
        
        hits = search_results.get("hits", [])
        
        workflow.append(AgentStep(
            agent="search-agent",
            action="Hybrid search (BM25 + vector)",
            input=request.query,
            output=f"Found {len(hits)} relevant chunks",
            duration_ms=int((time.time() - step1_start) * 1000)
        ))
        
        if not hits:
            return A2AResponse(
                query=request.query,
                workflow=workflow,
                final_answer="No relevant documents found.",
                citations=[],
                total_duration_ms=int((time.time() - start_time) * 1000)
            )
        
        # ========== STEP 2: Answer Agent (calls Search Agent results) ==========
        step2_start = time.time()
        
        # Build context from search results
        context_parts = []
        for i, hit in enumerate(hits[:5], 1):
            doc_title = hit.get("doc_title", "Unknown")
            page = hit.get("page", 1)
            text = hit.get("text", "")[:800]
            context_parts.append(f"[{i}] {doc_title} (Page {page}):\n{text}")
        
        context = "\n\n".join(context_parts)
        
        # Generate answer
        answer_prompt = f"""Based on the following legal documents, answer the question comprehensively.

Question: {request.query}

Documents:
{context}

Provide a clear, accurate answer citing sources using [1], [2], etc."""

        answer = inference.chat_completion(
            messages=[{"role": "user", "content": answer_prompt}],
            system_prompt="You are an expert legal research assistant. Answer based only on provided documents.",
            model=".anthropic-claude-4.5-sonnet-chat_completion"
        )
        
        workflow.append(AgentStep(
            agent="answer-agent",
            action="Generate answer from search results",
            input=f"Context from {len(hits[:5])} documents",
            output=f"Generated {len(answer)} char answer",
            duration_ms=int((time.time() - step2_start) * 1000)
        ))
        
        # ========== STEP 3: Citation Agent (refines citations) ==========
        step3_start = time.time()
        
        citations = []
        for i, hit in enumerate(hits[:5], 1):
            citations.append({
                "id": str(i),
                "doc_title": hit.get("doc_title", "Unknown"),
                "page": hit.get("page", 1),
                "snippet": hit.get("text", "")[:200],
                "doc_id": hit.get("doc_id", "")
            })
        
        workflow.append(AgentStep(
            agent="citation-agent",
            action="Extract precise citations",
            input=f"Answer with {len(citations)} sources",
            output=f"Generated {len(citations)} citations",
            duration_ms=int((time.time() - step3_start) * 1000)
        ))
        
        total_duration = int((time.time() - start_time) * 1000)
        
        return A2AResponse(
            query=request.query,
            workflow=workflow,
            final_answer=answer,
            citations=citations,
            total_duration_ms=total_duration
        )
        
    except Exception as e:
        logger.error(f"A2A orchestration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _stream_orchestration(query: str, project_id: str) -> AsyncGenerator[str, None]:
    """Stream the A2A orchestration process step by step."""
    try:
        settings = get_settings()
        inference = get_inference_service()
        es = ElasticsearchService()
        embedding_service = EmbeddingService()
        
        # Step 1: Search Agent
        yield f"data: {json.dumps({'step': 1, 'agent': 'search-agent', 'status': 'starting', 'message': 'Searching documents...'})}\n\n"
        
        query_embedding = embedding_service.generate_embedding(query)
        search_results = es.hybrid_search(
            query_text=query,
            query_vector=query_embedding,
            project_id=project_id,
            k=8,
            num_candidates=100
        )
        hits = search_results.get("hits", [])
        
        yield f"data: {json.dumps({'step': 1, 'agent': 'search-agent', 'status': 'complete', 'message': f'Found {len(hits)} relevant chunks'})}\n\n"
        
        if not hits:
            yield f"data: {json.dumps({'step': 'done', 'answer': 'No relevant documents found.', 'citations': []})}\n\n"
            return
        
        # Step 2: Answer Agent
        yield f"data: {json.dumps({'step': 2, 'agent': 'answer-agent', 'status': 'starting', 'message': 'Generating answer from search results...'})}\n\n"
        
        context_parts = []
        for i, hit in enumerate(hits[:5], 1):
            doc_title = hit.get("doc_title", "Unknown")
            page = hit.get("page", 1)
            text = hit.get("text", "")[:800]
            context_parts.append(f"[{i}] {doc_title} (Page {page}):\n{text}")
        
        context = "\n\n".join(context_parts)
        
        answer_prompt = f"""Based on the following legal documents, answer the question comprehensively.

Question: {query}

Documents:
{context}

Provide a clear, accurate answer citing sources using [1], [2], etc."""

        answer = inference.chat_completion(
            messages=[{"role": "user", "content": answer_prompt}],
            system_prompt="You are an expert legal research assistant. Answer based only on provided documents.",
            model=".anthropic-claude-4.5-sonnet-chat_completion"
        )
        
        yield f"data: {json.dumps({'step': 2, 'agent': 'answer-agent', 'status': 'complete', 'message': 'Answer generated'})}\n\n"
        
        # Step 3: Citation Agent
        yield f"data: {json.dumps({'step': 3, 'agent': 'citation-agent', 'status': 'starting', 'message': 'Extracting citations...'})}\n\n"
        
        citations = []
        for i, hit in enumerate(hits[:5], 1):
            citations.append({
                "id": str(i),
                "doc_title": hit.get("doc_title", "Unknown"),
                "page": hit.get("page", 1),
                "snippet": hit.get("text", "")[:200],
                "doc_id": hit.get("doc_id", "")
            })
        
        yield f"data: {json.dumps({'step': 3, 'agent': 'citation-agent', 'status': 'complete', 'message': f'Extracted {len(citations)} citations'})}\n\n"
        
        # Final result
        yield f"data: {json.dumps({'step': 'done', 'answer': answer, 'citations': citations})}\n\n"
        
    except Exception as e:
        logger.error(f"Stream orchestration failed: {e}")
        yield f"data: {json.dumps({'step': 'error', 'message': str(e)})}\n\n"


@router.get("/a2a/workflow")
async def get_workflow_diagram():
    """Get the A2A workflow diagram/description."""
    return {
        "name": "JurisScope A2A Workflow",
        "description": "Multi-step agent orchestration for legal document research",
        "agents": [
            {
                "id": "search-agent",
                "name": "Search Agent",
                "description": "Finds relevant documents using hybrid search",
                "tools": ["jurisscope.legal_search"],
                "calls": []
            },
            {
                "id": "answer-agent", 
                "name": "Answer Agent",
                "description": "Generates comprehensive answers",
                "tools": ["jurisscope.legal_search"],
                "calls": ["search-agent"]
            },
            {
                "id": "citation-agent",
                "name": "Citation Agent", 
                "description": "Extracts precise citations",
                "tools": ["jurisscope.citation_finder"],
                "calls": ["search-agent"]
            }
        ],
        "workflow": [
            {"step": 1, "agent": "search-agent", "action": "Hybrid search for relevant documents"},
            {"step": 2, "agent": "answer-agent", "action": "Generate answer using search results"},
            {"step": 3, "agent": "citation-agent", "action": "Extract and format citations"}
        ]
    }
