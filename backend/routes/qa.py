"""
Q&A route with agent collaboration (Retrieval → LLM → Citation).
POST /api/qa - Answer questions with citations
"""
import logging
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from services.elasticsearch import ElasticsearchService
from services.vertex_ai import VertexAIService
from services.firestore import FirestoreService

logger = logging.getLogger(__name__)

router = APIRouter()


class QARequest(BaseModel):
    """Request model for Q&A endpoint."""
    query: str
    project_id: str
    k: int = 5  # Number of chunks to retrieve


class Citation(BaseModel):
    """Citation model."""
    doc_id: str
    doc_title: str
    page: int
    snippet: str
    score: float
    elastic_doc_id: str


class QAResponse(BaseModel):
    """Response model for Q&A endpoint."""
    query: str
    answer: str
    citations: List[Citation]
    stats: Dict[str, Any]


@router.post("/qa", response_model=QAResponse)
async def answer_question(request: QARequest):
    """
    Answer a question using the multi-agent system:
    1. Retrieval Agent: Hybrid search (BM25 + kNN + RRF)
    2. LLM Agent: Generate answer with Gemini
    3. Citation Agent: Map answer to source documents
    
    Flow:
    - Retrieve relevant chunks from Elasticsearch
    - Generate query embedding
    - Use hybrid search for best results
    - Pass context to LLM
    - Extract and format citations
    """
    try:
        start_time = time.time()
        
        # Initialize services
        es_service = ElasticsearchService()
        vertex_service = VertexAIService()
        firestore_service = FirestoreService()
        
        # Step 1: Retrieval Agent - Generate query embedding
        logger.info(f"[QA] Query: {request.query}")
        logger.info(f"[QA] Step 1/3: Generating query embedding...")
        
        embedding_start = time.time()
        query_vector = vertex_service.generate_query_embedding(request.query)
        embedding_time = (time.time() - embedding_start) * 1000
        logger.info(f"[QA] Embedding generated in {embedding_time:.0f}ms")
        
        # Step 2: Retrieval Agent - Hybrid search
        logger.info(f"[QA] Step 2/3: Hybrid search (BM25 + kNN + RRF)...")
        
        retrieval_start = time.time()
        search_results = es_service.hybrid_search(
            query_text=request.query,
            query_vector=query_vector,
            project_id=request.project_id,
            k=request.k,
            num_candidates=request.k * 10
        )
        retrieval_time = (time.time() - retrieval_start) * 1000
        
        hits = search_results.get("hits", [])
        logger.info(f"[QA] Retrieved {len(hits)} chunks in {retrieval_time:.0f}ms")
        
        if not hits:
            return QAResponse(
                query=request.query,
                answer="I couldn't find any relevant information to answer this question.",
                citations=[],
                stats={
                    "chunks_searched": 0,
                    "retrieval_time_ms": retrieval_time,
                    "llm_time_ms": 0,
                    "total_time_ms": (time.time() - start_time) * 1000
                }
            )
        
        # Build context from retrieved chunks
        context_parts = []
        citations_data = []
        
        for i, hit in enumerate(hits, 1):
            # Fields are already unpacked in the hit dict (not in _source)
            text = hit.get("text", "")
            highlighted_text = hit.get("highlighted_text", "")
            doc_title = hit.get("doc_title", "Unknown")
            page = hit.get("page", 1)
            score = hit.get("score", 0.0)
            
            context_parts.append(f"[{i}] From '{doc_title}' (page {page}):\n{text}\n")
            
            # Use highlighted text for snippet if available (shows actual relevant passage),
            # otherwise fall back to beginning of chunk
            if highlighted_text:
                # Remove HTML tags from highlight (ES uses <em> tags)
                snippet = highlighted_text.replace("<em>", "").replace("</em>", "")
            else:
                snippet = text[:200] + "..." if len(text) > 200 else text
            
            citations_data.append({
                "doc_id": hit.get("doc_id", ""),
                "doc_title": doc_title,
                "page": page,
                "snippet": snippet,
                "score": score,
                "elastic_doc_id": hit.get("chunk_id", "")
            })
        
        context = "\n".join(context_parts)
        
        # Step 3: LLM Agent - Generate answer with citations
        logger.info(f"[QA] Step 3/3: Generating answer with LLM...")
        
        llm_start = time.time()
        
        system_instruction = """You are a legal AI assistant analyzing documents. 
Answer questions based ONLY on the provided context.
Use citation numbers like [1], [2] to reference sources.
If the answer isn't in the context, say so."""
        
        prompt = f"""Context from documents:

{context}

Question: {request.query}

Instructions:
1. Answer based ONLY on the context above
2. Use citation markers [1], [2], etc. to reference sources
3. Be specific and quote key phrases when relevant
4. If the context doesn't contain the answer, say "The provided documents don't contain enough information to answer this question."

Answer:"""
        
        answer = vertex_service.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            max_output_tokens=500,
            temperature=0.3
        )
        
        llm_time = (time.time() - llm_start) * 1000
        logger.info(f"[QA] Answer generated in {llm_time:.0f}ms")
        
        total_time = (time.time() - start_time) * 1000
        
        return QAResponse(
            query=request.query,
            answer=answer,
            citations=[Citation(**c) for c in citations_data],
            stats={
                "chunks_searched": len(hits),
                "embedding_time_ms": embedding_time,
                "retrieval_time_ms": retrieval_time,
                "llm_time_ms": llm_time,
                "total_time_ms": total_time
            }
        )
        
    except Exception as e:
        logger.error(f"Q&A failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

