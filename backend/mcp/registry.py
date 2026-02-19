"""
MCP Server Registry
Manages all MCP servers and provides a unified interface.
"""
import logging
from typing import Dict, Any, List, Optional

from mcp.document_processor import DocumentProcessorMCP
from mcp.llm_gateway import LLMGatewayMCP

logger = logging.getLogger(__name__)


class MCPRegistry:
    """
    Registry for all MCP servers.
    Provides discovery, tool listing, and unified tool execution.
    """
    
    def __init__(self):
        self.servers: Dict[str, Any] = {}
        self._init_servers()
        logger.info("MCP Registry initialized")
    
    def _init_servers(self):
        """Initialize all MCP servers."""
        self.servers = {
            "document_processor": DocumentProcessorMCP(),
            "llm_gateway": LLMGatewayMCP()
        }
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """List all registered MCP servers."""
        return [
            {
                "name": server.name,
                "version": server.version,
                "description": server.description,
                "tool_count": len(server.get_tools())
            }
            for server in self.servers.values()
        ]
    
    def get_server(self, name: str) -> Optional[Any]:
        """Get a specific MCP server by name."""
        return self.servers.get(name)
    
    def get_manifest(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get the manifest for a specific server."""
        server = self.servers.get(server_name)
        if server:
            return server.get_manifest()
        return None
    
    def list_all_tools(self) -> List[Dict[str, Any]]:
        """List all tools from all servers."""
        all_tools = []
        for server_name, server in self.servers.items():
            for tool in server.get_tools():
                all_tools.append({
                    "server": server_name,
                    **tool
                })
        return all_tools
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on a specific server."""
        server = self.servers.get(server_name)
        if not server:
            return {"error": f"Server not found: {server_name}"}
        
        return await server.call_tool(tool_name, arguments)
    
    def get_server_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Get tools for a specific server."""
        server = self.servers.get(server_name)
        if server:
            return server.get_tools()
        return []


# Global registry instance
mcp_registry = MCPRegistry()


def get_mcp_registry() -> MCPRegistry:
    """Get the global MCP registry instance."""
    return mcp_registry
