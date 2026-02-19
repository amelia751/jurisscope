"""
Elastic Agent - The core agent using Elasticsearch Agent Builder pattern.
Combines search, inference, and tools for multi-step reasoning.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from services.elastic_inference import get_inference_service, ElasticInferenceService
from services.elasticsearch import ElasticsearchService

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    """A message in the agent conversation."""
    role: str  # user, assistant, system, tool
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_results: Optional[List[Dict]] = None


@dataclass
class AgentContext:
    """Context for agent execution."""
    project_id: str
    messages: List[AgentMessage] = field(default_factory=list)
    tool_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ElasticAgent:
    """
    Multi-step AI agent using Elasticsearch Agent Builder.
    
    This agent:
    1. Receives a query
    2. Decides which tools to use (search, ES|QL, workflows)
    3. Executes tools against Elasticsearch
    4. Uses LLM (via Elastic inference) to reason about results
    5. Returns a structured answer with citations
    
    Tools available:
    - semantic_search: Hybrid search with reranking
    - esql_query: ES|QL analytics
    - get_document: Retrieve specific document
    - compliance_check: Check regulatory compliance
    """
    
    SYSTEM_PROMPT = """You are JurisScope, a legal AI assistant specialized in regulatory compliance analysis.

You have access to the following tools:
- semantic_search: Search legal documents using natural language queries
- esql_analytics: Run analytics queries on document data
- get_document: Retrieve a specific document by ID
- compliance_check: Check compliance with specific regulations

When answering questions:
1. Always cite your sources with document names and page numbers
2. Be precise about regulatory requirements
3. Distinguish between what the documents say vs your interpretation
4. If you're uncertain, say so

Format citations as: [Document Name, p. X]"""

    def __init__(self):
        self.inference = get_inference_service()
        self.es_service = ElasticsearchService()
        logger.info("Elastic Agent initialized with inference and search services")
    
    async def process_query(
        self,
        query: str,
        project_id: str,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Process a user query through multi-step reasoning.
        
        Steps:
        1. Understand the query
        2. Search for relevant documents
        3. Optionally rerank results
        4. Generate answer with citations
        """
        logger.info(f"Processing query: {query}")
        
        # Step 1: Search for relevant documents
        search_results = await self._semantic_search(query, project_id)
        
        # Step 2: Rerank results for better relevance
        if search_results:
            search_results = await self._rerank_results(query, search_results)
        
        # Step 3: Build context from top results
        context = self._build_context(search_results)
        
        # Step 4: Generate answer using LLM
        answer = await self._generate_answer(query, context, search_results)
        
        # Step 5: Format response with citations
        citations = self._format_citations(search_results)
        
        return {
            "query": query,
            "answer": answer,
            "citations": citations,
            "num_sources": len(search_results),
            "tools_used": ["semantic_search", "rerank", "chat_completion"]
        }
    
    async def _semantic_search(
        self,
        query: str,
        project_id: str,
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """Perform semantic search with embeddings."""
        try:
            # Generate query embedding using Elastic inference
            query_embedding = self.inference.generate_embedding(query)
            
            # Perform hybrid search
            results = self.es_service.hybrid_search(
                query_text=query,
                query_vector=query_embedding,
                project_id=project_id,
                k=k
            )
            
            return results.get("hits", [])
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            # Fallback to keyword search
            return self._keyword_search(query, project_id, k)
    
    def _keyword_search(
        self,
        query: str,
        project_id: str,
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """Fallback keyword search."""
        try:
            result = self.es_service.client.search(
                index=self.es_service.index_name,
                query={
                    "bool": {
                        "must": [{"match": {"text": query}}],
                        "filter": [{"term": {"project_id": project_id}}]
                    }
                },
                highlight={"fields": {"text": {"fragment_size": 200}}},
                size=k
            )
            
            hits = []
            for hit in result.get("hits", {}).get("hits", []):
                source = hit.get("_source", {})
                highlight = hit.get("highlight", {}).get("text", [])
                hits.append({
                    "doc_id": source.get("doc_id"),
                    "doc_title": source.get("doc_title"),
                    "page": source.get("page", 1),
                    "text": source.get("text", ""),
                    "score": hit.get("_score", 0),
                    "highlighted_text": " ... ".join(highlight) if highlight else ""
                })
            return hits
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    async def _rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Rerank search results using Elastic's reranker."""
        if not results:
            return []
        
        try:
            # Extract texts for reranking
            texts = [r.get("text", "")[:1000] for r in results]
            
            # Rerank using Elastic inference
            rerank_scores = self.inference.rerank(query, texts, top_k=top_k)
            
            # Apply new scores
            reranked = []
            for score_item in rerank_scores:
                idx = score_item.get("index", 0)
                if idx < len(results):
                    result = results[idx].copy()
                    result["rerank_score"] = score_item.get("relevance_score", 0)
                    reranked.append(result)
            
            return reranked
            
        except Exception as e:
            logger.warning(f"Reranking failed, using original order: {e}")
            return results[:top_k]
    
    def _build_context(self, results: List[Dict[str, Any]]) -> str:
        """Build context string from search results."""
        if not results:
            return "No relevant documents found."
        
        context_parts = []
        for i, result in enumerate(results[:5], 1):
            title = result.get("doc_title", "Unknown")
            page = result.get("page", 1)
            text = result.get("text", "")[:800]
            
            context_parts.append(f"""
[Document {i}: {title}, Page {page}]
{text}
""")
        
        return "\n---\n".join(context_parts)
    
    async def _generate_answer(
        self,
        query: str,
        context: str,
        results: List[Dict[str, Any]]
    ) -> str:
        """Generate answer using Elastic's LLM inference."""
        
        # Build prompt
        user_message = f"""Based on the following legal documents, answer this question:

Question: {query}

Relevant Documents:
{context}

Instructions:
- Cite specific documents and page numbers
- Be precise about regulatory requirements
- If the documents don't contain enough information, say so"""
        
        try:
            answer = self.inference.chat_completion(
                messages=[{"role": "user", "content": user_message}],
                system_prompt=self.SYSTEM_PROMPT
            )
            return answer
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fallback to extractive answer
            return self._extractive_answer(query, results)
    
    def _extractive_answer(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> str:
        """Fallback extractive answer from search results."""
        if not results:
            return "I couldn't find relevant information to answer your question."
        
        answer_parts = [f"Based on the search results for '{query}':\n"]
        
        for i, result in enumerate(results[:3], 1):
            title = result.get("doc_title", "Unknown")
            page = result.get("page", 1)
            text = result.get("highlighted_text") or result.get("text", "")[:200]
            answer_parts.append(f"\n[{i}] From {title} (p. {page}): {text}")
        
        return "".join(answer_parts)
    
    def _format_citations(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format citations from search results."""
        citations = []
        for i, result in enumerate(results[:5], 1):
            doc_id = result.get("doc_id", "")
            page = result.get("page", 1)
            
            citations.append({
                "id": f"{doc_id}_{page}",
                "rank": i,
                "doc_id": doc_id,
                "doc_title": result.get("doc_title", "Unknown"),
                "page": page,
                "snippet": result.get("highlighted_text") or result.get("text", "")[:200],
                "score": result.get("score", 0),
                "rerank_score": result.get("rerank_score"),
                "url": f"/doc/{doc_id}?page={page}"
            })
        
        return citations
    
    async def compliance_analysis(
        self,
        project_id: str,
        regulation: str = "EU AI Act"
    ) -> Dict[str, Any]:
        """
        Perform compliance analysis against a regulation.
        Uses multi-step reasoning:
        1. Search for compliance-related documents
        2. Check each requirement
        3. Generate compliance report
        """
        # Search for compliance documentation
        query = f"compliance {regulation} requirements implementation"
        results = await self._semantic_search(query, project_id, k=20)
        
        if not results:
            return {
                "regulation": regulation,
                "status": "insufficient_data",
                "message": "No compliance documentation found"
            }
        
        # Build context
        context = self._build_context(results)
        
        # Use LLM to analyze compliance
        analysis_prompt = f"""Analyze the following documents for compliance with {regulation}.

Documents:
{context}

For each major requirement of {regulation}, assess:
1. Is there evidence of compliance?
2. Are there any gaps?
3. What recommendations would you make?

Format your response as a structured compliance report."""

        try:
            analysis = self.inference.chat_completion(
                messages=[{"role": "user", "content": analysis_prompt}],
                system_prompt="You are a legal compliance analyst. Be thorough and cite specific documents."
            )
            
            return {
                "regulation": regulation,
                "status": "analyzed",
                "analysis": analysis,
                "sources": len(results),
                "citations": self._format_citations(results[:5])
            }
            
        except Exception as e:
            logger.error(f"Compliance analysis failed: {e}")
            return {
                "regulation": regulation,
                "status": "error",
                "message": str(e)
            }


# Factory function
def get_elastic_agent() -> ElasticAgent:
    """Get an instance of the Elastic Agent."""
    return ElasticAgent()
