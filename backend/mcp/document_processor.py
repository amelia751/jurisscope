"""
Document Processor MCP Server
Provides document processing tools via Model Context Protocol.
"""
import logging
import json
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentProcessorMCP:
    """
    MCP Server for document processing operations.
    
    Tools provided:
    - extract_text: Extract text from PDF documents
    - chunk_document: Split document into semantic chunks
    - extract_metadata: Extract document metadata
    - get_page_layout: Get page layout and structure
    """
    
    name = "document_processor"
    version = "1.0.0"
    description = "Document processing tools for legal documents"
    
    def __init__(self):
        from services.pdf_processor import PDFProcessorService
        self.pdf_processor = PDFProcessorService()
        logger.info("Document Processor MCP initialized")
    
    def get_manifest(self) -> Dict[str, Any]:
        """Return MCP server manifest."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tools": self.get_tools(),
            "resources": [],
            "prompts": []
        }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return list of tools provided by this MCP server."""
        return [
            {
                "name": "extract_text",
                "description": "Extract all text from a PDF document",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the PDF file"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "chunk_document",
                "description": "Split a document into semantic chunks suitable for indexing",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the document file"
                        },
                        "chunk_size": {
                            "type": "integer",
                            "description": "Target size of each chunk in tokens",
                            "default": 1000
                        },
                        "overlap": {
                            "type": "integer",
                            "description": "Overlap between chunks in tokens",
                            "default": 200
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "extract_metadata",
                "description": "Extract metadata from a document (title, author, dates, etc.)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the document file"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "get_page_layout",
                "description": "Get the layout structure of a specific page",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the PDF file"
                        },
                        "page_number": {
                            "type": "integer",
                            "description": "Page number (1-indexed)"
                        }
                    },
                    "required": ["file_path", "page_number"]
                }
            }
        ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given arguments."""
        logger.info(f"MCP tool call: {tool_name}")
        
        try:
            if tool_name == "extract_text":
                return await self._extract_text(arguments)
            elif tool_name == "chunk_document":
                return await self._chunk_document(arguments)
            elif tool_name == "extract_metadata":
                return await self._extract_metadata(arguments)
            elif tool_name == "get_page_layout":
                return await self._get_page_layout(arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"MCP tool error: {e}")
            return {"error": str(e)}
    
    async def _extract_text(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text from a PDF."""
        file_path = args.get("file_path")
        if not file_path:
            return {"error": "file_path is required"}
        
        result = self.pdf_processor.process_pdf(file_path)
        return {
            "success": True,
            "text": result.get("text", ""),
            "num_pages": result.get("num_pages", 0),
            "char_count": len(result.get("text", ""))
        }
    
    async def _chunk_document(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Chunk a document into smaller pieces."""
        import tiktoken
        
        file_path = args.get("file_path")
        chunk_size = args.get("chunk_size", 1000)
        overlap = args.get("overlap", 200)
        
        if not file_path:
            return {"error": "file_path is required"}
        
        # Extract text first
        result = self.pdf_processor.process_pdf(file_path)
        text = result.get("text", "")
        
        # Tokenize and chunk
        tokenizer = tiktoken.get_encoding("cl100k_base")
        tokens = tokenizer.encode(text)
        
        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = tokenizer.decode(chunk_tokens)
            
            chunks.append({
                "index": len(chunks),
                "text": chunk_text,
                "token_count": len(chunk_tokens),
                "char_start": start,
                "char_end": end
            })
            
            start += chunk_size - overlap
        
        return {
            "success": True,
            "num_chunks": len(chunks),
            "chunks": chunks
        }
    
    async def _extract_metadata(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Extract document metadata."""
        import pdfplumber
        
        file_path = args.get("file_path")
        if not file_path:
            return {"error": "file_path is required"}
        
        try:
            with pdfplumber.open(file_path) as pdf:
                metadata = pdf.metadata or {}
                return {
                    "success": True,
                    "metadata": {
                        "title": metadata.get("Title", Path(file_path).stem),
                        "author": metadata.get("Author", "Unknown"),
                        "subject": metadata.get("Subject", ""),
                        "creator": metadata.get("Creator", ""),
                        "producer": metadata.get("Producer", ""),
                        "creation_date": metadata.get("CreationDate", ""),
                        "modification_date": metadata.get("ModDate", ""),
                        "num_pages": len(pdf.pages)
                    }
                }
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_page_layout(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get page layout information."""
        import pdfplumber
        
        file_path = args.get("file_path")
        page_number = args.get("page_number", 1)
        
        if not file_path:
            return {"error": "file_path is required"}
        
        try:
            with pdfplumber.open(file_path) as pdf:
                if page_number < 1 or page_number > len(pdf.pages):
                    return {"error": f"Invalid page number. Document has {len(pdf.pages)} pages."}
                
                page = pdf.pages[page_number - 1]
                
                # Extract layout elements
                tables = page.extract_tables() or []
                
                return {
                    "success": True,
                    "page_number": page_number,
                    "width": page.width,
                    "height": page.height,
                    "text": page.extract_text() or "",
                    "num_tables": len(tables),
                    "tables": [
                        {"rows": len(t), "cols": len(t[0]) if t else 0}
                        for t in tables
                    ]
                }
        except Exception as e:
            return {"error": str(e)}
