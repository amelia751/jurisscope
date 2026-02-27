"""
Ask route for Q&A with A2A (Agent-to-Agent) orchestration.
POST /api/ask - Ask a question and get an answer with citations

Multi-Agent Workflow:
1. search-agent: Hybrid search (BM25 + vector) with reranking
2. answer-agent: Generate answer using Claude/GPT via Elastic inference
3. citation-agent: Extract and format precise citations

Uses Elasticsearch Agent Builder inference endpoints for:
- Embeddings: .jina-embeddings-v3
- Reranking: .jina-reranker-v3
- LLM: .anthropic-claude-4.5-sonnet-chat_completion
"""
import logging
import time
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from services.elasticsearch import ElasticsearchService
from services.embeddings import EmbeddingService
from services.elastic_inference import get_inference_service
from services.local_storage import LocalMetadataService
from config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


class Citation(BaseModel):
    """Citation model."""
    doc_id: str
    doc_title: str
    page: int
    snippet: str
    score: float
    url: str


class AgentStep(BaseModel):
    """A step in the A2A workflow."""
    agent: str
    action: str
    duration_ms: int
    result: str


class AskRequest(BaseModel):
    """Request model for ask endpoint."""
    query: str
    project_id: str
    k: int = 5


class AskResponse(BaseModel):
    """Response model for ask endpoint."""
    query_id: str
    answer: str
    citations: List[Citation]
    num_hits: int
    latency_ms: float
    workflow: Optional[List[AgentStep]] = None  # A2A workflow steps


def generate_answer_with_elastic(query: str, passages: List[dict]) -> str:
    """
    Generate an answer using Elastic's inference API.
    Uses Claude 4.5 Sonnet for high-quality legal analysis.
    """
    inference = get_inference_service()
    
    # Build context with numbered citations
    context_parts = []
    for i, passage in enumerate(passages, 1):
        doc_title = passage.get('doc_title', 'Unknown Document')
        page = passage.get('page', '?')
        text = passage.get('text', '')[:1500]  # More context for better answers
        context_parts.append(f"[{i}] {doc_title} (Page {page}):\n\"{text}\"")
    
    context = "\n\n".join(context_parts)
    
    system_prompt = """You are an expert legal research assistant with deep knowledge of EU regulations, GDPR, AI Act, and corporate law.

Your task is to provide clear, accurate, and well-cited answers based ONLY on the provided documents.

Guidelines:
- Answer the question directly and comprehensively
- ALWAYS cite your sources using [n] markers (e.g., [1], [2])
- Quote relevant passages when helpful
- If the documents don't contain enough information, say so
- Use precise legal terminology
- Structure your answer with clear paragraphs
- Never invent information not found in the documents"""

    user_message = f"""Based on the following legal documents, answer this question:

Question: {query}

Documents:
{context}

Provide a comprehensive answer with proper citations [1], [2], etc."""

    try:
        # Use Claude 4.5 Sonnet for best quality
        answer = inference.chat_completion(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
            model=".anthropic-claude-4.5-sonnet-chat_completion"
        )
        
        if answer and len(answer.strip()) > 10:
            logger.info(f"Generated answer with Elastic inference ({len(answer)} chars)")
            return answer
        else:
            logger.warning("Empty answer from Elastic inference, trying fallback")
            raise Exception("Empty response")
            
    except Exception as e:
        logger.warning(f"Claude 4.5 failed: {e}, trying GPT-4.1")
        
        try:
            # Fallback to GPT-4.1
            answer = inference.chat_completion(
                messages=[{"role": "user", "content": user_message}],
                system_prompt=system_prompt,
                model=".openai-gpt-4.1-chat_completion"
            )
            
            if answer and len(answer.strip()) > 10:
                logger.info(f"Generated answer with GPT-4.1 ({len(answer)} chars)")
                return answer
                
        except Exception as e2:
            logger.warning(f"GPT-4.1 also failed: {e2}")
    
    # Final fallback - structured summary
    return _format_fallback_answer(query, passages)


def _format_fallback_answer(query: str, passages: List[dict]) -> str:
    """Format a structured answer when LLM is unavailable."""
    answer_parts = [f"Based on the available documents regarding '{query}':\n"]
    
    for i, passage in enumerate(passages[:5], 1):
        doc_title = passage.get('doc_title', 'Unknown')
        page = passage.get('page', '?')
        text = passage.get('text', '')[:300].strip()
        
        # Clean up text
        text = ' '.join(text.split())  # Normalize whitespace
        
        answer_parts.append(f"**[{i}] {doc_title}** (Page {page}):")
        answer_parts.append(f"> {text}...")
        answer_parts.append("")
    
    answer_parts.append("\n*Note: Please review the cited documents for complete details.*")
    
    return "\n".join(answer_parts)


def rerank_passages(query: str, passages: List[dict]) -> List[dict]:
    """
    Rerank passages using Elastic's inference API for better relevance.
    """
    if not passages:
        return passages
    
    try:
        inference = get_inference_service()
        
        # Extract texts for reranking
        texts = [p.get('text', '')[:1000] for p in passages]
        
        # Rerank using Jina reranker
        rerank_results = inference.rerank(query, texts, top_k=min(10, len(passages)))
        
        # Reorder passages based on rerank scores
        reranked = []
        for result in rerank_results:
            idx = result.get('index', 0)
            if idx < len(passages):
                passage = passages[idx].copy()
                passage['rerank_score'] = result.get('relevance_score', 0)
                reranked.append(passage)
        
        logger.info(f"Reranked {len(passages)} passages -> top {len(reranked)}")
        return reranked
        
    except Exception as e:
        logger.warning(f"Reranking failed: {e}, using original order")
        return passages


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Ask a question and get an answer with citations.
    
    A2A (Agent-to-Agent) Workflow:
    1. search-agent: Hybrid search (BM25 + kNN) with reranking
    2. answer-agent: Generate answer using Claude via Elastic inference
    3. citation-agent: Extract and format precise citations
    """
    start_time = time.time()
    query_id = str(uuid.uuid4())
    workflow = []
    
    try:
        logger.info(f"[{query_id}] A2A orchestration starting: {request.query[:50]}...")
        
        # Initialize services
        embedding_service = EmbeddingService()
        es_service = ElasticsearchService()
        metadata_service = LocalMetadataService()
        
        # ========== STEP 1: search-agent ==========
        step1_start = time.time()
        logger.info(f"[{query_id}] search-agent: Starting hybrid search...")
        
        # Generate query embedding
        query_embedding = embedding_service.generate_embedding(request.query)
        
        # Hybrid search
        search_results = es_service.hybrid_search(
            query_text=request.query,
            query_vector=query_embedding,
            project_id=request.project_id,
            k=max(20, request.k * 4)
        )
        
        hits = search_results.get("hits", [])
        
        # Deduplicate
        seen_texts = set()
        unique_hits = []
        for hit in hits:
            text_hash = hash(hit.get("text", "")[:200])
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique_hits.append(hit)
        hits = unique_hits
        
        # Rerank for better relevance
        reranked_hits = rerank_passages(request.query, hits)
        top_hits = reranked_hits[:request.k]
        
        step1_duration = int((time.time() - step1_start) * 1000)
        workflow.append(AgentStep(
            agent="search-agent",
            action="Hybrid search + rerank",
            duration_ms=step1_duration,
            result=f"Found {len(hits)} chunks, top {len(top_hits)} selected"
        ))
        logger.info(f"[{query_id}] search-agent: Complete ({step1_duration}ms)")
        
        if not hits:
            return AskResponse(
                query_id=query_id,
                answer="I couldn't find any relevant information to answer your question. Please ensure documents have been uploaded to this project.",
                citations=[],
                num_hits=0,
                latency_ms=(time.time() - start_time) * 1000,
                workflow=workflow
            )
        
        # ========== STEP 2: answer-agent ==========
        step2_start = time.time()
        logger.info(f"[{query_id}] answer-agent: Generating answer...")
        
        answer = generate_answer_with_elastic(request.query, top_hits)
        
        step2_duration = int((time.time() - step2_start) * 1000)
        workflow.append(AgentStep(
            agent="answer-agent",
            action="Generate answer with Claude",
            duration_ms=step2_duration,
            result=f"Generated {len(answer)} char response"
        ))
        logger.info(f"[{query_id}] answer-agent: Complete ({step2_duration}ms)")
        
        # ========== STEP 3: citation-agent ==========
        step3_start = time.time()
        logger.info(f"[{query_id}] citation-agent: Building citations...")
        
        citations = []
        for i, hit in enumerate(top_hits, 1):
            bbox_list = hit.get("bbox_list", [])
            bbox_param = ""
            if bbox_list:
                bbox = bbox_list[0]
                bbox_param = f"&bbox={bbox.get('x1', 0)},{bbox.get('y1', 0)},{bbox.get('x2', 1)},{bbox.get('y2', 1)}"
            
            doc_id = hit.get("doc_id", "")
            page = hit.get("page", 1)
            chunk_id = hit.get("chunk_id", "")
            
            text = hit.get("text", "")
            snippet = text[:350] if len(text) > 350 else text
            snippet = ' '.join(snippet.split())
            if len(text) > 350:
                snippet += "..."
            
            citation = Citation(
                doc_id=doc_id,
                doc_title=hit.get("doc_title", "Unknown"),
                page=page,
                snippet=snippet,
                score=hit.get("rerank_score", hit.get("score", 0)),
                url=f"/doc/{doc_id}?page={page}{bbox_param}&hl={chunk_id}"
            )
            citations.append(citation)
        
        step3_duration = int((time.time() - step3_start) * 1000)
        workflow.append(AgentStep(
            agent="citation-agent",
            action="Extract citations",
            duration_ms=step3_duration,
            result=f"Built {len(citations)} citations"
        ))
        logger.info(f"[{query_id}] citation-agent: Complete ({step3_duration}ms)")
        
        # Log query
        latency_ms = (time.time() - start_time) * 1000
        metadata_service.log_query(
            query_id=query_id,
            query_text=request.query,
            project_id=request.project_id,
            results={
                "num_hits": len(hits),
                "latency_ms": latency_ms,
                "workflow": [s.dict() for s in workflow]
            }
        )
        
        logger.info(f"[{query_id}] ✓ A2A complete in {latency_ms:.0f}ms")
        
        return AskResponse(
            query_id=query_id,
            answer=answer,
            citations=citations,
            num_hits=len(hits),
            latency_ms=latency_ms,
            workflow=workflow
        )
        
    except Exception as e:
        logger.error(f"[{query_id}] A2A orchestration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/{query_id}")
async def get_query_log(query_id: str):
    """Get query log for traceability."""
    try:
        metadata = LocalMetadataService()
        query_log = metadata.get_query_log(query_id)
        
        if not query_log:
            raise HTTPException(status_code=404, detail="Query log not found")
        
        return query_log
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get query log: {e}")
        raise HTTPException(status_code=500, detail=str(e))
