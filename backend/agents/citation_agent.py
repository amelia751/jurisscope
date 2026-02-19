"""
Citation Agent - Generates precise legal citations with page/bbox locations.
Formats citations according to legal standards.
"""
import logging
import re
from typing import Dict, Any, List, Optional

from agents.base_agent import BaseAgent, AgentContext, AgentResponse
from services.elasticsearch import ElasticsearchService
from services.firestore import FirestoreService

logger = logging.getLogger(__name__)


class CitationAgent(BaseAgent):
    """
    Legal citation agent that:
    1. Extracts precise citation locations (page, bbox)
    2. Generates properly formatted citations
    3. Creates citation links for document viewer
    4. Validates citation accuracy
    
    Citation formats supported:
    - Document citations with page numbers
    - Regulation citations (Article X, Section Y)
    - Internal reference citations
    """
    
    name = "citation_agent"
    description = "Generates precise legal citations with page numbers and bounding boxes for document highlighting."
    
    def __init__(self):
        super().__init__()
        self.es_service = ElasticsearchService()
        self.firestore = FirestoreService()
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Generate citations for search results in context.
        
        Steps:
        1. Get search results from context history
        2. Enrich with span map data (bboxes)
        3. Format citations according to document type
        4. Generate viewer URLs with highlight parameters
        """
        self.logger.info(f"Generating citations for context: {context.session_id}")
        
        try:
            # Get previous retrieval results from context
            retrieval_result = self._get_retrieval_result(context)
            if not retrieval_result:
                return AgentResponse(
                    success=False,
                    agent_name=self.name,
                    action_taken="generate_citations",
                    result={"error": "No retrieval results in context"},
                    reasoning="Citation agent requires retrieval results to process."
                )
            
            documents = retrieval_result.get("documents", [])
            formatted_citations = []
            
            for doc in documents:
                # Enrich with span map data
                span_data = await self._get_span_data(doc.get("doc_id"), doc.get("chunk_id"))
                
                # Format citation
                citation = self._format_citation(doc, span_data)
                formatted_citations.append(citation)
            
            # Add to context history
            context.add_step(self.name, "generate_citations", {
                "num_citations": len(formatted_citations)
            })
            
            return AgentResponse(
                success=True,
                agent_name=self.name,
                action_taken="generate_citations",
                result={
                    "citations": formatted_citations,
                    "citation_count": len(formatted_citations)
                },
                citations=formatted_citations,
                reasoning=f"Generated {len(formatted_citations)} precise citations with page and location data."
            )
            
        except Exception as e:
            self.logger.error(f"Citation generation failed: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                agent_name=self.name,
                action_taken="generate_citations",
                result={"error": str(e)},
                reasoning=f"Failed to generate citations: {str(e)}"
            )
    
    def _get_retrieval_result(self, context: AgentContext) -> Optional[Dict[str, Any]]:
        """Get the most recent retrieval result from context history."""
        for step in reversed(context.history):
            if step.get("agent") == "retrieval_agent" and step.get("action") == "hybrid_search":
                return step.get("result", {})
        return None
    
    async def _get_span_data(self, doc_id: str, chunk_id: str = None) -> Dict[str, Any]:
        """Get span map data for precise bbox locations."""
        if not doc_id:
            return {}
        
        span_map = self.firestore.get_span_map(doc_id)
        if span_map and chunk_id and chunk_id in span_map:
            return span_map[chunk_id]
        return {}
    
    def _format_citation(self, doc: Dict[str, Any], span_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format a citation according to document type and legal standards."""
        doc_title = doc.get("doc_title", "Unknown Document")
        doc_id = doc.get("doc_id", "")
        page = doc.get("page", 1)
        text = doc.get("text", "")[:200]
        score = doc.get("score", 0)
        
        # Get bounding boxes for highlighting
        bboxes = doc.get("bbox_list", [])
        if span_data:
            bboxes = span_data.get("bboxes", bboxes)
        
        # Determine citation format based on document type
        citation_format = self._determine_citation_format(doc_title)
        
        # Build citation URL with highlight parameters
        bbox_param = ""
        if bboxes and len(bboxes) > 0:
            bbox = bboxes[0]
            if isinstance(bbox, dict):
                bbox_param = f"&bbox={bbox.get('x1', 0)},{bbox.get('y1', 0)},{bbox.get('x2', 1)},{bbox.get('y2', 1)}"
            elif isinstance(bbox, list) and len(bbox) >= 4:
                bbox_param = f"&bbox={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
        
        chunk_id = doc.get("chunk_id", "")
        url = f"/doc/{doc_id}?page={page}{bbox_param}&hl={chunk_id}"
        
        # Extract article/section references if present
        article_ref = self._extract_article_reference(text)
        
        return {
            "id": f"{doc_id}_{page}",
            "doc_id": doc_id,
            "doc_title": doc_title,
            "page": page,
            "text_snippet": text,
            "highlighted_text": doc.get("highlighted_text", text),
            "score": score,
            "url": url,
            "bboxes": bboxes,
            "format": citation_format,
            "article_reference": article_ref,
            "formatted_citation": self._build_formatted_citation(
                doc_title, page, article_ref, citation_format
            )
        }
    
    def _determine_citation_format(self, doc_title: str) -> str:
        """Determine the appropriate citation format based on document title."""
        title_lower = doc_title.lower()
        
        if any(term in title_lower for term in ["regulation", "directive", "act", "gdpr", "dma"]):
            return "regulation"
        elif any(term in title_lower for term in ["complaint", "response", "letter", "correspondence"]):
            return "correspondence"
        elif any(term in title_lower for term in ["memo", "report", "assessment"]):
            return "internal"
        elif any(term in title_lower for term in ["settlement", "agreement", "contract"]):
            return "contract"
        elif any(term in title_lower for term in ["article", "news"]):
            return "article"
        else:
            return "document"
    
    def _extract_article_reference(self, text: str) -> Optional[str]:
        """Extract Article/Section references from text."""
        # Pattern for Article X, Section Y, Paragraph Z
        patterns = [
            r'Article\s+\d+(?:\s*\(\d+\))?',
            r'Section\s+\d+(?:\.\d+)?',
            r'Paragraph\s+\d+',
            r'Recital\s+\d+',
            r'Annex\s+[IVX]+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def _build_formatted_citation(
        self,
        doc_title: str,
        page: int,
        article_ref: Optional[str],
        format_type: str
    ) -> str:
        """Build a properly formatted citation string."""
        if format_type == "regulation" and article_ref:
            return f"{doc_title}, {article_ref}, at p. {page}"
        elif format_type == "correspondence":
            return f"{doc_title}, p. {page}"
        elif format_type == "internal":
            return f"{doc_title} (Internal), p. {page}"
        elif format_type == "contract":
            return f"{doc_title}, §{article_ref or page}"
        else:
            return f"{doc_title}, p. {page}"
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tools available to this agent."""
        return [
            {
                "name": "generate_citations",
                "description": "Generate formatted citations from search results",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "documents": {
                            "type": "array",
                            "description": "List of documents to cite"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["legal", "academic", "internal"],
                            "description": "Citation format style"
                        }
                    },
                    "required": ["documents"]
                }
            },
            {
                "name": "get_bbox_locations",
                "description": "Get precise bounding box locations for text highlighting",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doc_id": {"type": "string", "description": "Document ID"},
                        "chunk_id": {"type": "string", "description": "Chunk ID"}
                    },
                    "required": ["doc_id", "chunk_id"]
                }
            },
            {
                "name": "validate_citation",
                "description": "Validate that a citation accurately reflects the source text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "citation": {"type": "object", "description": "Citation to validate"},
                        "claimed_text": {"type": "string", "description": "Text claimed to be from source"}
                    },
                    "required": ["citation", "claimed_text"]
                }
            }
        ]
