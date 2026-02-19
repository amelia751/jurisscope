"""
MCP API routes for JurisScope.
Provides REST API access to MCP servers and tools.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from mcp.registry import get_mcp_registry

logger = logging.getLogger(__name__)

router = APIRouter()


class MCPToolCallRequest(BaseModel):
    """Request model for MCP tool calls."""
    server: str
    tool: str
    arguments: Dict[str, Any] = {}


class MCPToolCallResponse(BaseModel):
    """Response model for MCP tool calls."""
    success: bool
    server: str
    tool: str
    result: Dict[str, Any]


@router.get("/mcp/servers")
async def list_mcp_servers():
    """
    List all available MCP servers.
    Returns basic info about each registered server.
    """
    registry = get_mcp_registry()
    return {
        "servers": registry.list_servers(),
        "count": len(registry.servers)
    }


@router.get("/mcp/servers/{server_name}")
async def get_mcp_server(server_name: str):
    """
    Get detailed info about a specific MCP server.
    Returns the server's manifest including all tools.
    """
    registry = get_mcp_registry()
    manifest = registry.get_manifest(server_name)
    
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Server not found: {server_name}")
    
    return manifest


@router.get("/mcp/tools")
async def list_mcp_tools():
    """
    List all available MCP tools across all servers.
    Useful for discovering available capabilities.
    """
    registry = get_mcp_registry()
    return {
        "tools": registry.list_all_tools(),
        "count": len(registry.list_all_tools())
    }


@router.get("/mcp/tools/{server_name}")
async def list_server_tools(server_name: str):
    """
    List tools for a specific MCP server.
    """
    registry = get_mcp_registry()
    tools = registry.get_server_tools(server_name)
    
    if not tools:
        raise HTTPException(status_code=404, detail=f"Server not found or has no tools: {server_name}")
    
    return {
        "server": server_name,
        "tools": tools,
        "count": len(tools)
    }


@router.post("/mcp/call", response_model=MCPToolCallResponse)
async def call_mcp_tool(request: MCPToolCallRequest):
    """
    Call an MCP tool.
    
    Example:
    ```json
    {
        "server": "document_processor",
        "tool": "extract_text",
        "arguments": {
            "file_path": "/path/to/document.pdf"
        }
    }
    ```
    """
    registry = get_mcp_registry()
    
    logger.info(f"MCP tool call: {request.server}/{request.tool}")
    
    try:
        result = await registry.call_tool(
            server_name=request.server,
            tool_name=request.tool,
            arguments=request.arguments
        )
        
        return MCPToolCallResponse(
            success=not result.get("error"),
            server=request.server,
            tool=request.tool,
            result=result
        )
        
    except Exception as e:
        logger.error(f"MCP tool call failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp/batch")
async def batch_mcp_calls(calls: List[MCPToolCallRequest]):
    """
    Execute multiple MCP tool calls in batch.
    Useful for complex workflows that need multiple tools.
    """
    registry = get_mcp_registry()
    results = []
    
    for call in calls:
        try:
            result = await registry.call_tool(
                server_name=call.server,
                tool_name=call.tool,
                arguments=call.arguments
            )
            results.append({
                "server": call.server,
                "tool": call.tool,
                "success": not result.get("error"),
                "result": result
            })
        except Exception as e:
            results.append({
                "server": call.server,
                "tool": call.tool,
                "success": False,
                "result": {"error": str(e)}
            })
    
    return {
        "total": len(calls),
        "successful": sum(1 for r in results if r["success"]),
        "results": results
    }
