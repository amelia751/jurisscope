"""
JurisScope Backend API - FastAPI Application
Legal AI workbench with Elasticsearch Agent Builder
Built for Elasticsearch Agent Builder Hackathon 2026
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("Starting JurisScope backend API...")
    settings = get_settings()
    
    logger.info(f"✓ API starting on port {settings.api_port}")
    logger.info(f"✓ Elasticsearch endpoint: {settings.elasticsearch_endpoint}")
    
    yield
    
    logger.info("Shutting down JurisScope backend API...")


# Create FastAPI app
app = FastAPI(
    title="JurisScope API",
    description="Legal AI workbench with Elasticsearch Agent Builder - Hackathon 2026",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "jurisscope-api"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "JurisScope API",
        "version": "0.1.0",
        "description": "Legal AI workbench with Elasticsearch Agent Builder",
        "hackathon": "Elasticsearch Agent Builder Hackathon 2026",
        "status": "running",
        "docs": "/docs",
        "health": "/healthz",
        "endpoints": {
            "test_elasticsearch": "/api/test-elasticsearch",
            "upload": "/api/upload",
            "ask": "/api/ask",
            "documents": "/api/documents",
            "agents": {
                "query": "/api/agents/query",
                "compliance": "/api/agents/compliance",
                "analytics": "/api/agents/analytics",
                "list": "/api/agents/list",
                "tools": "/api/agents/tools"
            },
            "mcp": {
                "servers": "/api/mcp/servers",
                "tools": "/api/mcp/tools",
                "call": "/api/mcp/call"
            }
        }
    }


@app.get("/api/test-elasticsearch")
async def test_elasticsearch():
    """Test Elasticsearch connection."""
    try:
        from services.elasticsearch import ElasticsearchService
        es = ElasticsearchService()
        result = es.test_connection()
        
        if result.get("connected"):
            return {
                "status": "success",
                "message": "Elasticsearch connection successful",
                **result
            }
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Elasticsearch connection failed",
                    **result
                }
            )
    except Exception as e:
        logger.error(f"Elasticsearch test failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )


@app.get("/api/elasticsearch/stats")
async def elasticsearch_stats():
    """Get Elasticsearch index statistics."""
    try:
        from services.elasticsearch import ElasticsearchService
        es = ElasticsearchService()
        stats = es.get_index_stats()
        return {"status": "success", **stats}
    except Exception as e:
        logger.error(f"Failed to get ES stats: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@app.post("/api/elasticsearch/ensure-index")
async def ensure_elasticsearch_index():
    """Create the Elasticsearch index if it doesn't exist."""
    try:
        from services.elasticsearch import ElasticsearchService
        es = ElasticsearchService()
        await es.ensure_index()
        return {"status": "success", "message": f"Index {es.index_name} is ready"}
    except Exception as e:
        logger.error(f"Failed to ensure index: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


# Import and include routers
from routes import upload, ask, documents, agents, mcp, browser_upload, table_analysis, a2a

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(browser_upload.router, prefix="/api", tags=["browser-upload"])
app.include_router(ask.router, prefix="/api", tags=["ask"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(agents.router, prefix="/api", tags=["agents"])
app.include_router(mcp.router, prefix="/api", tags=["mcp"])
app.include_router(table_analysis.router, prefix="/api", tags=["table-analysis"])
app.include_router(a2a.router, prefix="/api", tags=["a2a"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
