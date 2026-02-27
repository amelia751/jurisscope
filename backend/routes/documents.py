"""
Documents route for document management.
Handles CRUD operations for documents and projects with full persistence.
"""
import logging
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid

from services.firestore import FirestoreService
from services.elasticsearch import ElasticsearchService

logger = logging.getLogger(__name__)

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"


class DocumentResponse(BaseModel):
    """Document metadata response."""
    id: str
    project_id: str
    title: str
    status: str
    num_pages: Optional[int] = None
    num_chunks: Optional[int] = None
    created_at: Optional[str] = None


# ==================== DOCUMENT ENDPOINTS ====================

@router.get("/documents")
@router.get("/documents")
async def list_documents(project_id: Optional[str] = None):
    """List all documents, optionally filtered by project.
    
    First tries local storage, then falls back to Elasticsearch aggregation.
    This ensures documents are found even when local storage is ephemeral (Cloud Run).
    """
    try:
        # Try local storage first
        firestore = FirestoreService()
        documents = firestore.list_documents(project_id=project_id)
        
        # If no documents found locally, try Elasticsearch
        if not documents and project_id:
            logger.info(f"No local documents found for project {project_id}, querying Elasticsearch...")
            try:
                es = ElasticsearchService()
                es_docs = es.list_documents_by_project(project_id)
                if es_docs:
                    documents = es_docs
                    logger.info(f"Found {len(documents)} documents in Elasticsearch for project {project_id}")
            except Exception as es_error:
                logger.warning(f"Elasticsearch query failed: {es_error}")
        
        return {"documents": documents, "total": len(documents)}
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/doc/{doc_id}")
async def get_document(doc_id: str):
    """Get document metadata by ID."""
    try:
        firestore = FirestoreService()
        doc = firestore.get_document(doc_id)
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/doc/{doc_id}/file")
async def get_document_file(doc_id: str):
    """Get the actual document file."""
    try:
        firestore = FirestoreService()
        doc = firestore.get_document(doc_id)
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        file_path = doc.get("file_path")
        if not file_path or not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=file_path,
            filename=Path(file_path).name,
            media_type=doc.get("mime", "application/pdf")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/doc/{doc_id}/spans")
async def get_document_spans(doc_id: str):
    """Get span map for document (for citation highlighting)."""
    try:
        firestore = FirestoreService()
        span_map = firestore.get_span_map(doc_id)
        
        if not span_map:
            return {"doc_id": doc_id, "spans": {}}
        
        return {"doc_id": doc_id, "spans": span_map}
    except Exception as e:
        logger.error(f"Failed to get spans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/doc/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete a document completely:
    - Remove from Elasticsearch index
    - Remove from local storage
    - Remove metadata from Firestore
    """
    try:
        firestore = FirestoreService()
        es = ElasticsearchService()
        
        # Get document info first
        doc = firestore.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        file_path = doc.get("file_path")
        
        # 1. Delete from Elasticsearch
        try:
            es.client.delete_by_query(
                index=es.index_name,
                query={"term": {"doc_id": doc_id}},
                refresh=True
            )
            logger.info(f"Deleted ES chunks for document: {doc_id}")
        except Exception as es_err:
            logger.warning(f"ES delete failed (may not exist): {es_err}")
        
        # 2. Delete local file
        if file_path and Path(file_path).exists():
            Path(file_path).unlink()
            logger.info(f"Deleted file: {file_path}")
        
        # 3. Delete span map
        try:
            firestore.delete_span_map(doc_id)
        except:
            pass
        
        # 4. Delete document metadata
        firestore.delete_document(doc_id)
        
        logger.info(f"Document {doc_id} deleted completely")
        
        return {
            "success": True,
            "message": f"Document {doc_id} deleted successfully",
            "doc_id": doc_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PROJECT ENDPOINTS ====================

@router.get("/projects")
async def list_projects():
    """List all projects with document counts."""
    try:
        firestore = FirestoreService()
        projects = firestore.list_projects()
        
        # Enrich with document counts
        for project in projects:
            docs = firestore.list_documents(project_id=project.get("id"))
            project["document_count"] = len(docs)
        
        return {"projects": projects, "total": len(projects)}
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CreateProjectRequest(BaseModel):
    """Request to create a project."""
    name: str
    description: Optional[str] = None


@router.post("/projects")
async def create_project(request: CreateProjectRequest):
    """Create a new project."""
    try:
        firestore = FirestoreService()
        project_id = str(uuid.uuid4())
        
        project = firestore.create_project(
            project_id=project_id,
            data={
                "name": request.name,
                "description": request.description or "",
                "document_count": 0
            }
        )
        
        # Create uploads directory for this project
        project_uploads_dir = UPLOADS_DIR / project_id
        project_uploads_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created project: {project_id}")
        return project
        
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project by ID with document list."""
    try:
        firestore = FirestoreService()
        project = firestore.get_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Include documents
        documents = firestore.list_documents(project_id=project_id)
        project["documents"] = documents
        project["document_count"] = len(documents)
        
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """
    Delete a project and ALL its documents:
    - Delete all documents (from ES, storage, metadata)
    - Delete project directory
    - Delete project metadata
    """
    try:
        firestore = FirestoreService()
        es = ElasticsearchService()
        
        # Get project
        project = firestore.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all documents in project
        documents = firestore.list_documents(project_id=project_id)
        
        # 1. Delete all documents from ES
        try:
            result = es.client.delete_by_query(
                index=es.index_name,
                query={"term": {"project_id": project_id}},
                refresh=True
            )
            deleted_count = result.get("deleted", 0)
            logger.info(f"Deleted {deleted_count} ES chunks for project: {project_id}")
        except Exception as es_err:
            logger.warning(f"ES bulk delete failed: {es_err}")
        
        # 2. Delete all document files and metadata
        for doc in documents:
            doc_id = doc.get("id")
            file_path = doc.get("file_path")
            
            # Delete file
            if file_path and Path(file_path).exists():
                Path(file_path).unlink()
            
            # Delete span map
            try:
                firestore.delete_span_map(doc_id)
            except:
                pass
            
            # Delete document metadata
            firestore.delete_document(doc_id)
        
        # 3. Delete project upload directory
        project_dir = UPLOADS_DIR / project_id
        if project_dir.exists():
            shutil.rmtree(project_dir)
            logger.info(f"Deleted project directory: {project_dir}")
        
        # 4. Delete project metadata
        firestore.delete_project(project_id)
        
        logger.info(f"Project {project_id} and {len(documents)} documents deleted")
        
        return {
            "success": True,
            "message": f"Project deleted with {len(documents)} documents",
            "project_id": project_id,
            "documents_deleted": len(documents)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class UpdateProjectRequest(BaseModel):
    """Request to update a project."""
    name: Optional[str] = None
    description: Optional[str] = None


@router.put("/projects/{project_id}")
async def update_project(project_id: str, request: UpdateProjectRequest):
    """Update project metadata."""
    try:
        firestore = FirestoreService()
        
        project = firestore.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Build update data
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        
        if update_data:
            firestore.update_project(project_id, update_data)
        
        # Return updated project
        return firestore.get_project(project_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update project: {e}")
        raise HTTPException(status_code=500, detail=str(e))
