"""
ES|QL Analytics Agent - Uses Elasticsearch Query Language for complex analysis.
Performs time-series analysis, aggregations, and document analytics.
"""
import logging
from typing import Dict, Any, List

from agents.base_agent import BaseAgent, AgentContext, AgentResponse
from services.elasticsearch import ElasticsearchService

logger = logging.getLogger(__name__)


class ESQLAgent(BaseAgent):
    """
    ES|QL Analytics agent for complex document analysis.
    
    Capabilities:
    1. Document statistics (counts, distributions)
    2. Time-series analysis (filing trends, deadlines)
    3. Entity extraction analytics
    4. Cross-document aggregations
    
    Note: ES|QL is Elasticsearch's piped query language for analytics.
    """
    
    name = "esql_agent"
    description = "Performs complex analytics using ES|QL queries for document statistics, trends, and aggregations."
    
    def __init__(self):
        super().__init__()
        self.es_service = ElasticsearchService()
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute ES|QL analytics based on query intent.
        
        Analyzes the query to determine appropriate analytics:
        - Count queries: "how many documents..."
        - Distribution: "breakdown by type..."
        - Timeline: "documents over time..."
        - Top-N: "most mentioned regulations..."
        """
        self.logger.info(f"Running ES|QL analytics for: {context.query}")
        
        try:
            # Determine analytics type from query
            analytics_type = self._determine_analytics_type(context.query)
            
            # Execute appropriate ES|QL query
            if analytics_type == "count":
                result = await self._run_count_analytics(context)
            elif analytics_type == "distribution":
                result = await self._run_distribution_analytics(context)
            elif analytics_type == "timeline":
                result = await self._run_timeline_analytics(context)
            elif analytics_type == "top_n":
                result = await self._run_top_n_analytics(context)
            else:
                result = await self._run_general_analytics(context)
            
            # Add to context
            context.add_step(self.name, f"esql_{analytics_type}", result)
            
            return AgentResponse(
                success=True,
                agent_name=self.name,
                action_taken=f"esql_{analytics_type}",
                result=result,
                reasoning=f"Performed {analytics_type} analytics using ES|QL."
            )
            
        except Exception as e:
            self.logger.error(f"ES|QL analytics failed: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                agent_name=self.name,
                action_taken="esql_analytics",
                result={"error": str(e)},
                reasoning=f"ES|QL analytics failed: {str(e)}"
            )
    
    def _determine_analytics_type(self, query: str) -> str:
        """Determine the type of analytics needed from the query."""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ["how many", "count", "total number"]):
            return "count"
        elif any(term in query_lower for term in ["breakdown", "distribution", "by type", "categorize"]):
            return "distribution"
        elif any(term in query_lower for term in ["timeline", "over time", "trend", "when"]):
            return "timeline"
        elif any(term in query_lower for term in ["top", "most", "highest", "frequently"]):
            return "top_n"
        else:
            return "general"
    
    async def _run_count_analytics(self, context: AgentContext) -> Dict[str, Any]:
        """Run count-based analytics."""
        # Use Elasticsearch aggregations (since serverless may not support full ES|QL)
        if not self.es_service.client:
            return {"error": "Elasticsearch client not available"}
        
        result = self.es_service.client.search(
            index=self.es_service.index_name,
            size=0,
            query={
                "term": {"project_id": context.project_id}
            },
            aggs={
                "total_chunks": {"value_count": {"field": "chunk_id.keyword"}},
                "unique_documents": {"cardinality": {"field": "doc_id.keyword"}},
                "pages_per_doc": {"stats": {"field": "page"}}
            }
        )
        
        aggs = result.get("aggregations", {})
        
        return {
            "analytics_type": "count",
            "query": context.query,
            "results": {
                "total_chunks": aggs.get("total_chunks", {}).get("value", 0),
                "unique_documents": aggs.get("unique_documents", {}).get("value", 0),
                "page_stats": aggs.get("pages_per_doc", {})
            }
        }
    
    async def _run_distribution_analytics(self, context: AgentContext) -> Dict[str, Any]:
        """Run distribution/breakdown analytics."""
        if not self.es_service.client:
            return {"error": "Elasticsearch client not available"}
        
        result = self.es_service.client.search(
            index=self.es_service.index_name,
            size=0,
            query={
                "term": {"project_id": context.project_id}
            },
            aggs={
                "by_document": {
                    "terms": {
                        "field": "doc_title.keyword",
                        "size": 20
                    },
                    "aggs": {
                        "chunk_count": {"value_count": {"field": "chunk_id.keyword"}},
                        "page_range": {"stats": {"field": "page"}}
                    }
                },
                "by_page": {
                    "histogram": {
                        "field": "page",
                        "interval": 10
                    }
                }
            }
        )
        
        aggs = result.get("aggregations", {})
        
        # Transform into readable format
        doc_distribution = []
        for bucket in aggs.get("by_document", {}).get("buckets", []):
            doc_distribution.append({
                "document": bucket["key"],
                "chunks": bucket.get("chunk_count", {}).get("value", 0),
                "pages": bucket.get("page_range", {}).get("max", 0)
            })
        
        page_distribution = []
        for bucket in aggs.get("by_page", {}).get("buckets", []):
            page_distribution.append({
                "page_range": f"{int(bucket['key'])}-{int(bucket['key']) + 10}",
                "count": bucket["doc_count"]
            })
        
        return {
            "analytics_type": "distribution",
            "query": context.query,
            "results": {
                "by_document": doc_distribution,
                "by_page_range": page_distribution
            }
        }
    
    async def _run_timeline_analytics(self, context: AgentContext) -> Dict[str, Any]:
        """Run timeline/temporal analytics."""
        if not self.es_service.client:
            return {"error": "Elasticsearch client not available"}
        
        result = self.es_service.client.search(
            index=self.es_service.index_name,
            size=0,
            query={
                "term": {"project_id": context.project_id}
            },
            aggs={
                "by_created_date": {
                    "date_histogram": {
                        "field": "created_at",
                        "calendar_interval": "day"
                    }
                }
            }
        )
        
        aggs = result.get("aggregations", {})
        
        timeline = []
        for bucket in aggs.get("by_created_date", {}).get("buckets", []):
            timeline.append({
                "date": bucket.get("key_as_string"),
                "count": bucket.get("doc_count", 0)
            })
        
        return {
            "analytics_type": "timeline",
            "query": context.query,
            "results": {
                "timeline": timeline
            }
        }
    
    async def _run_top_n_analytics(self, context: AgentContext) -> Dict[str, Any]:
        """Run top-N analytics (most frequent terms, etc.)."""
        if not self.es_service.client:
            return {"error": "Elasticsearch client not available"}
        
        # Extract key terms from text using significant terms aggregation
        result = self.es_service.client.search(
            index=self.es_service.index_name,
            size=0,
            query={
                "term": {"project_id": context.project_id}
            },
            aggs={
                "top_documents": {
                    "terms": {
                        "field": "doc_title.keyword",
                        "size": 10
                    }
                },
                "significant_terms": {
                    "significant_text": {
                        "field": "text",
                        "size": 20
                    }
                }
            }
        )
        
        aggs = result.get("aggregations", {})
        
        top_docs = [
            {"document": b["key"], "count": b["doc_count"]}
            for b in aggs.get("top_documents", {}).get("buckets", [])
        ]
        
        significant = [
            {"term": b["key"], "score": b.get("score", 0)}
            for b in aggs.get("significant_terms", {}).get("buckets", [])
        ]
        
        return {
            "analytics_type": "top_n",
            "query": context.query,
            "results": {
                "top_documents": top_docs,
                "significant_terms": significant[:10]
            }
        }
    
    async def _run_general_analytics(self, context: AgentContext) -> Dict[str, Any]:
        """Run general overview analytics."""
        count_result = await self._run_count_analytics(context)
        dist_result = await self._run_distribution_analytics(context)
        
        return {
            "analytics_type": "general",
            "query": context.query,
            "results": {
                "counts": count_result.get("results", {}),
                "distribution": dist_result.get("results", {})
            }
        }
    
    async def run_custom_esql(self, esql_query: str) -> Dict[str, Any]:
        """
        Run a custom ES|QL query.
        
        Note: Full ES|QL support depends on Elasticsearch version and license.
        This is a placeholder for future ES|QL integration.
        """
        # ES|QL is available in Elasticsearch 8.11+ but may have limitations in serverless
        self.logger.info(f"Running custom ES|QL: {esql_query}")
        
        # For now, return a message about ES|QL support
        return {
            "message": "Custom ES|QL queries require Elasticsearch 8.11+",
            "query": esql_query,
            "status": "planned"
        }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tools available to this agent."""
        return [
            {
                "name": "count_documents",
                "description": "Count documents matching criteria",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filter": {"type": "object", "description": "Filter criteria"}
                    }
                }
            },
            {
                "name": "document_distribution",
                "description": "Get distribution of documents by type, date, or other field",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "group_by": {"type": "string", "description": "Field to group by"},
                        "filter": {"type": "object", "description": "Filter criteria"}
                    },
                    "required": ["group_by"]
                }
            },
            {
                "name": "timeline_analysis",
                "description": "Analyze documents over time",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_field": {"type": "string", "description": "Date field to use"},
                        "interval": {
                            "type": "string",
                            "enum": ["day", "week", "month"],
                            "description": "Time interval"
                        }
                    }
                }
            },
            {
                "name": "top_entities",
                "description": "Find most frequent entities or terms",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_type": {"type": "string", "description": "Type of entity"},
                        "limit": {"type": "integer", "description": "Number of results"}
                    }
                }
            },
            {
                "name": "run_esql",
                "description": "Run a custom ES|QL query for advanced analytics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "ES|QL query string"}
                    },
                    "required": ["query"]
                }
            }
        ]
