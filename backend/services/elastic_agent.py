"""
Elastic Agent Builder Service.
Calls the Kibana API to use registered agents and tools.
"""
import logging
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator
import json

from config import get_settings

logger = logging.getLogger(__name__)


class ElasticAgentService:
    """Service to interact with Elastic Agent Builder via Kibana API."""
    
    def __init__(self):
        settings = get_settings()
        
        # Derive Kibana URL from ES endpoint
        es_endpoint = settings.elasticsearch_endpoint
        self.kibana_url = es_endpoint.replace(".es.", ".kb.")
        self.api_key = settings.elasticsearch_api_key
        
        self.headers = {
            "Authorization": f"ApiKey {self.api_key}",
            "kbn-xsrf": "true",
            "Content-Type": "application/json"
        }
        
        # Our custom agent ID
        self.agent_id = "jurisscope-legal-agent"
        
        logger.info(f"Elastic Agent Service initialized: {self.kibana_url}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from Agent Builder."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.kibana_url}/api/agent_builder/tools",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all available agents from Agent Builder."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.kibana_url}/api/agent_builder/agents",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
    
    async def execute_tool(self, tool_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a specific tool directly."""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.kibana_url}/api/agent_builder/tools/{tool_id}/execute",
                headers=self.headers,
                json={"params": params or {}}
            )
            response.raise_for_status()
            return response.json()
    
    async def chat_with_agent(
        self,
        message: str,
        agent_id: str = None,
        conversation_id: str = None
    ) -> Dict[str, Any]:
        """
        Send a message to an agent and get a response.
        Uses streaming internally but returns the complete response.
        """
        agent_id = agent_id or self.agent_id
        
        payload = {
            "message": message
        }
        if conversation_id:
            payload["conversationId"] = conversation_id
        
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                # Try the chat endpoint
                response = await client.post(
                    f"{self.kibana_url}/api/agent_builder/agents/{agent_id}/chat",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.warning(f"Chat endpoint returned {e.response.status_code}, trying stream...")
                # Fall back to using internal tools directly
                return await self._query_with_tools(message)
    
    async def chat_stream(
        self,
        message: str,
        agent_id: str = None,
        conversation_id: str = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat responses from an agent."""
        agent_id = agent_id or self.agent_id
        
        payload = {
            "message": message
        }
        if conversation_id:
            payload["conversationId"] = conversation_id
        
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.kibana_url}/api/agent_builder/agents/{agent_id}/chat/stream",
                headers=self.headers,
                json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        yield line
    
    async def _query_with_tools(self, query: str) -> Dict[str, Any]:
        """
        Fallback: Execute query using our registered ES|QL tools directly.
        """
        settings = get_settings()
        es_endpoint = settings.elasticsearch_endpoint
        
        # First, search using ES|QL
        esql_query = f"""
        FROM jurisscope-documents 
        | WHERE text LIKE "*{query.replace('"', '')}*" 
        | KEEP doc_id, doc_title, text, page, chunk_id 
        | LIMIT 10
        """
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{es_endpoint}/_query?format=json",
                headers={
                    "Authorization": f"ApiKey {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"query": esql_query}
            )
            
            if response.status_code == 200:
                data = response.json()
                columns = data.get("columns", [])
                values = data.get("values", [])
                
                # Convert to readable results
                results = []
                for row in values:
                    result = {}
                    for i, col in enumerate(columns):
                        result[col["name"]] = row[i]
                    results.append(result)
                
                # Format answer
                if results:
                    answer_parts = [f"Found {len(results)} relevant results:\n"]
                    for i, r in enumerate(results[:5], 1):
                        text_preview = r.get("text", "")[:200] + "..." if len(r.get("text", "")) > 200 else r.get("text", "")
                        answer_parts.append(f"\n[{i}] **{r.get('doc_title', 'Unknown')}** (Page {r.get('page', '?')})")
                        answer_parts.append(f"   {text_preview}")
                    
                    return {
                        "message": "\n".join(answer_parts),
                        "results": results,
                        "tool_used": "jurisscope.legal_search",
                        "query": query
                    }
                else:
                    return {
                        "message": f"No results found for: {query}",
                        "results": [],
                        "tool_used": "jurisscope.legal_search",
                        "query": query
                    }
            else:
                logger.error(f"ES|QL query failed: {response.text}")
                return {
                    "message": f"Search failed: {response.text}",
                    "results": [],
                    "error": response.text
                }
    
    async def run_compliance_check(self, project_id: str = None) -> Dict[str, Any]:
        """Run compliance checker tool."""
        settings = get_settings()
        es_endpoint = settings.elasticsearch_endpoint
        
        esql_query = """
        FROM jurisscope-documents 
        | WHERE text LIKE "*GDPR*" OR text LIKE "*AI Act*" OR text LIKE "*compliance*" OR text LIKE "*regulation*" 
        | STATS mentions = COUNT(*) BY doc_title 
        | SORT mentions DESC 
        | LIMIT 15
        """
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{es_endpoint}/_query?format=json",
                headers={
                    "Authorization": f"ApiKey {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"query": esql_query}
            )
            
            if response.status_code == 200:
                data = response.json()
                columns = data.get("columns", [])
                values = data.get("values", [])
                
                results = []
                for row in values:
                    result = {}
                    for i, col in enumerate(columns):
                        result[col["name"]] = row[i]
                    results.append(result)
                
                return {
                    "tool": "jurisscope.compliance_checker",
                    "results": results,
                    "total_documents_with_compliance": len(results)
                }
            else:
                return {"error": response.text}
    
    async def get_project_summary(self, project_id: str = None) -> Dict[str, Any]:
        """Get summary of documents using project summary tool."""
        settings = get_settings()
        es_endpoint = settings.elasticsearch_endpoint
        
        esql_query = """
        FROM jurisscope-documents 
        | STATS chunks = COUNT(*), min_page = MIN(page), max_page = MAX(page) BY project_id, doc_title 
        | SORT project_id, doc_title
        """
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{es_endpoint}/_query?format=json",
                headers={
                    "Authorization": f"ApiKey {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"query": esql_query}
            )
            
            if response.status_code == 200:
                data = response.json()
                columns = data.get("columns", [])
                values = data.get("values", [])
                
                results = []
                for row in values:
                    result = {}
                    for i, col in enumerate(columns):
                        result[col["name"]] = row[i]
                    results.append(result)
                
                return {
                    "tool": "jurisscope.project_summary",
                    "documents": results,
                    "total_documents": len(results)
                }
            else:
                return {"error": response.text}


# Singleton instance
_elastic_agent_service = None

def get_elastic_agent_service() -> ElasticAgentService:
    """Get or create the Elastic Agent Service singleton."""
    global _elastic_agent_service
    if _elastic_agent_service is None:
        _elastic_agent_service = ElasticAgentService()
    return _elastic_agent_service
