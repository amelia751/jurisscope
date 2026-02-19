"""
Upload route for document ingestion.
POST /api/upload - Upload and ingest documents locally
"""
import logging
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from services.local_storage import LocalStorageService, LocalMetadataService
from services.ingestion import IngestionService

logger = logging.getLogger(__name__)

router = APIRouter()

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


class UploadResponse(BaseModel):
    """Response model for upload endpoint."""
    doc_id: str
    file_path: str
    status: str
    message: str


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    doc_title: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None
):
    """
    Upload a document and start ingestion.
    """
    try:
        # Generate unique document ID
        doc_id = str(uuid.uuid4())
        
        # Create project directory
        project_dir = UPLOADS_DIR / project_id
        project_dir.mkdir(exist_ok=True)
        
        # Save uploaded file
        file_extension = Path(file.filename).suffix or ".pdf"
        file_path = project_dir / f"{doc_id}{file_extension}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"Saved uploaded file: {file_path}")
        
        # Initialize metadata
        metadata = LocalMetadataService()
        title = doc_title or file.filename
        
        metadata.create_document(
            doc_id=doc_id,
            data={
                "project_id": project_id,
                "title": title,
                "file_path": str(file_path),
                "mime": file.content_type or "application/pdf",
                "status": "pending"
            }
        )
        
        # Start ingestion in background
        if background_tasks:
            background_tasks.add_task(
                run_ingestion,
                doc_id=doc_id,
                file_path=str(file_path),
                project_id=project_id,
                doc_title=title,
                mime_type=file.content_type or "application/pdf"
            )
        
        return UploadResponse(
            doc_id=doc_id,
            file_path=str(file_path),
            status="pending",
            message="File uploaded. Ingestion will start in background."
        )
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_ingestion(doc_id: str, file_path: str, project_id: str, doc_title: str, mime_type: str):
    """Run ingestion in background."""
    try:
        ingestion = IngestionService()
        await ingestion.ingest_document(
            doc_id=doc_id,
            file_path=file_path,
            project_id=project_id,
            doc_title=doc_title,
            mime_type=mime_type
        )
    except Exception as e:
        logger.error(f"Background ingestion failed: {e}")


class LocalUploadRequest(BaseModel):
    """Request for uploading a local file."""
    file_path: str
    project_id: str
    doc_title: str


@router.post("/upload/local")
async def upload_local_file(request: LocalUploadRequest):
    """
    Ingest a local file (for demo-cases).
    """
    try:
        source_path = Path(request.file_path)
        
        if not source_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
        
        # Generate doc ID
        doc_id = str(uuid.uuid4())
        
        # Copy to uploads directory
        project_dir = UPLOADS_DIR / request.project_id
        project_dir.mkdir(exist_ok=True)
        
        dest_path = project_dir / f"{doc_id}{source_path.suffix}"
        shutil.copy2(source_path, dest_path)
        
        logger.info(f"Copied {source_path} to {dest_path}")
        
        # Create metadata
        metadata = LocalMetadataService()
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(source_path))
        mime_type = mime_type or "application/pdf"
        
        metadata.create_document(
            doc_id=doc_id,
            data={
                "project_id": request.project_id,
                "title": request.doc_title,
                "file_path": str(dest_path),
                "mime": mime_type,
                "status": "pending"
            }
        )
        
        # Run ingestion
        ingestion = IngestionService()
        result = await ingestion.ingest_document(
            doc_id=doc_id,
            file_path=str(dest_path),
            project_id=request.project_id,
            doc_title=request.doc_title,
            mime_type=mime_type
        )
        
        return {
            "doc_id": doc_id,
            "file_path": str(dest_path),
            "ingestion_result": result,
            "message": "File ingested successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Local upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/batch")
async def batch_upload_local_files(
    project_id: str,
    directory: str
):
    """
    Batch ingest all files from a directory (for demo-cases).
    """
    try:
        source_dir = Path(directory)
        
        if not source_dir.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {directory}")
        
        results = []
        files = list(source_dir.rglob("*"))
        files = [f for f in files if f.is_file() and f.suffix.lower() in [".pdf", ".txt", ".md"]]
        
        logger.info(f"Found {len(files)} files to ingest")
        
        for file_path in files:
            try:
                doc_title = file_path.stem
                
                result = await upload_local_file(LocalUploadRequest(
                    file_path=str(file_path),
                    project_id=project_id,
                    doc_title=doc_title
                ))
                
                results.append({
                    "file": str(file_path),
                    "status": "success",
                    "doc_id": result["doc_id"]
                })
                
            except Exception as e:
                results.append({
                    "file": str(file_path),
                    "status": "failed",
                    "error": str(e)
                })
        
        successful = len([r for r in results if r["status"] == "success"])
        
        return {
            "total": len(files),
            "successful": successful,
            "failed": len(files) - successful,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
