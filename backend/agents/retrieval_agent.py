"""
Retrieval Agent - Specialized for legal document search.
Uses Elasticsearch hybrid search (BM25 + vector) to find relevant documents.
"""
import logging
from typing import Dict, Any, List

from agents.base_agent import BaseAgent, AgentContext, AgentResponse, Tool
from services.elasticsearch import ElasticsearchService
from services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class RetrievalAgent(BaseAgent):
    """
    Legal document retrieval agent using Elasticsearch hybrid search.
    
    Tools:
    - semantic_search: Vector-based similarity search
    - keyword_search: BM25 text search  
    - hybrid_search: Combined search with RRF/linear fusion
    - filter_by_type: Filter results by document type
    """
    
    name = "retrieval_agent"
    description = "Retrieves relevant legal documents using hybrid search combining semantic understanding with keyword matching."
    
    def __init__(self):
        super().__init__()
        self.es_service = ElasticsearchService()
        self.embeddings_service = EmbeddingService()
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute retrieval based on the query.
        
        Strategy:
        1. Generate query embedding
        2. Perform hybrid search
        3. Re-rank results if needed
        4. Return top-k documents with citations
        """
        self.logger.info(f"Executing retrieval for: {context.query}")
        
        try:
            # Generate query embedding
            query_embedding = self.embeddings_service.generate_embedding(context.query)
            
            # Get search parameters from context
            k = context.metadata.get("k", 10)
            doc_types = context.metadata.get("doc_types", None)
            
            # Perform hybrid search
            results = self.es_service.hybrid_search(
                query_text=context.query,
                query_vector=query_embedding,
                project_id=context.project_id,
                k=k
            )
            
            # Filter by document type if specified
            hits = results.get("hits", [])
            if doc_types:
                hits = [h for h in hits if h.get("doc_type") in doc_types]
            
            # Build citations
            citations = []
            for i, hit in enumerate(hits):
                citations.append({
                    "rank": i + 1,
                    "doc_id": hit.get("doc_id"),
                    "doc_title": hit.get("doc_title"),
                    "page": hit.get("page", 1),
                    "score": hit.get("score", 0),
                    "text": hit.get("text", "")[:500],
                    "highlighted_text": hit.get("highlighted_text", ""),
                    "bbox_list": hit.get("bbox_list", [])
                })
            
            # Add to context history
            context.add_step(self.name, "hybrid_search", {
                "query": context.query,
                "num_results": len(citations)
            })
            
            return AgentResponse(
                success=True,
                agent_name=self.name,
                action_taken="hybrid_search",
                result={
                    "query": context.query,
                    "total_hits": results.get("total", 0),
                    "returned_hits": len(citations),
                    "documents": citations
                },
                citations=citations,
                reasoning=f"Found {len(citations)} relevant documents using hybrid search (BM25 + semantic)."
            )
            
        except Exception as e:
            self.logger.error(f"Retrieval failed: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                agent_name=self.name,
                action_taken="hybrid_search",
                result={"error": str(e)},
                reasoning=f"Search failed: {str(e)}"
            )
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tools available to this agent."""
        return [
            {
                "name": "semantic_search",
                "description": "Search documents using vector similarity for semantic meaning",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "k": {"type": "integer", "description": "Number of results", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "keyword_search",
                "description": "Search documents using BM25 keyword matching",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "k": {"type": "integer", "description": "Number of results", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "hybrid_search",
                "description": "Combined semantic and keyword search with fusion ranking",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "k": {"type": "integer", "description": "Number of results", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "filter_by_document_type",
                "description": "Filter search results by document type (legal_correspondence, internal_docs, regulations, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doc_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of document types to filter by"
                        }
                    },
                    "required": ["doc_types"]
                }
            }
        ]
    
    async def keyword_search(self, query: str, project_id: str, k: int = 10) -> List[Dict[str, Any]]:
        """Perform BM25 keyword search."""
        results = self.es_service.client.search(
            index=self.es_service.index_name,
            query={
                "bool": {
                    "must": [
                        {"match": {"text": query}}
                    ],
                    "filter": [
                        {"term": {"project_id": project_id}}
                    ]
                }
            },
            highlight={
                "fields": {"text": {"fragment_size": 200, "number_of_fragments": 3}}
            },
            size=k
        )
        return self._parse_es_results(results)
    
    async def semantic_search(self, query: str, project_id: str, k: int = 10) -> List[Dict[str, Any]]:
        """Perform vector similarity search."""
        query_embedding = self.embeddings_service.generate_embedding(query)
        
        results = self.es_service.client.search(
            index=self.es_service.index_name,
            knn={
                "field": "vector",
                "query_vector": query_embedding,
                "k": k,
                "num_candidates": k * 2,
                "filter": {"term": {"project_id": project_id}}
            },
            size=k
        )
        return self._parse_es_results(results)
    
    def _parse_es_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Elasticsearch results into a standard format."""
        hits = []
        for hit in results.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            highlight = hit.get("highlight", {}).get("text", [])
            hits.append({
                "doc_id": source.get("doc_id"),
                "doc_title": source.get("doc_title"),
                "page": source.get("page", 1),
                "text": source.get("text", ""),
                "score": hit.get("_score", 0),
                "highlighted_text": " ... ".join(highlight) if highlight else "",
                "bbox_list": source.get("bbox_list", [])
            })
        return hits
