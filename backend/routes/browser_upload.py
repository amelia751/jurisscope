"""
Browser file upload endpoint - accepts files directly from frontend.
Updated for JurisScope hackathon (local storage + Elastic embeddings).
Processes documents SYNCHRONOUSLY so frontend can show real-time progress.
"""
import logging
import uuid
import tempfile
import os
import json
from typing import List
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.local_storage import LocalStorageService
from services.firestore import FirestoreService
from services.ingestion import IngestionService

logger = logging.getLogger(__name__)

router = APIRouter()


class BrowserUploadResponse(BaseModel):
    """Response for browser upload."""
    doc_id: str
    filename: str
    status: str
    num_chunks: int = 0


@router.post("/upload/browser", response_model=List[BrowserUploadResponse])
async def upload_from_browser(
    files: List[UploadFile] = File(...),
    project_id: str = Form(...),
    folder_paths: str = Form("{}")  # JSON string of folder paths
):
    """
    Upload files directly from browser.
    Processes documents SYNCHRONOUSLY so vault shows real-time status.
    """
    logger.info(f"Browser upload: {len(files)} files for project {project_id}")
    
    # Parse folder paths
    try:
        folder_map = json.loads(folder_paths)
    except:
        folder_map = {}
    
    # Initialize services
    storage_service = LocalStorageService()
    firestore_service = FirestoreService()
    ingestion_service = IngestionService()
    
    # Ensure project exists in firestore
    project = firestore_service.get_project(project_id)
    if not project:
        firestore_service.create_project(project_id, {
            "name": f"Project {project_id[:8]}",
            "description": "Created from browser upload"
        })
    
    results = []
    
    for i, upload_file in enumerate(files):
        filename = upload_file.filename or f"document_{i}"
        logger.info(f"[{i+1}/{len(files)}] Processing: {filename}")
        
        try:
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Get file extension
            file_extension = filename.split('.')[-1] if '.' in filename else 'pdf'
            
            # Detect mime type
            mime_type = upload_file.content_type or "application/pdf"
            
            # Save to temp file first
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp_file:
                content = await upload_file.read()
                tmp_file.write(content)
                tmp_file.flush()
                temp_path = tmp_file.name
            
            # Save to local storage
            saved_path = storage_service.save_file(temp_path, project_id, doc_id)
            
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
            
            logger.info(f"[{filename}] Saved to {saved_path}")
            
            # Create document record with "processing" status
            firestore_service.create_document(
                doc_id=doc_id,
                data={
                    "project_id": project_id,
                    "title": filename.rsplit('.', 1)[0],
                    "file_path": str(saved_path),
                    "mime": mime_type,
                    "status": "processing"
                }
            )
            
            # Process SYNCHRONOUSLY (not in background)
            try:
                ingestion_result = await ingestion_service.ingest_document(
                    doc_id=doc_id,
                    file_path=str(saved_path),
                    project_id=project_id,
                    doc_title=filename.rsplit('.', 1)[0],
                    mime_type=mime_type
                )
                
                num_chunks = ingestion_result.get("num_chunks", 0)
                logger.info(f"[{filename}] ✓ Processed: {num_chunks} chunks")
                
                results.append(BrowserUploadResponse(
                    doc_id=doc_id,
                    filename=filename,
                    status="completed",
                    num_chunks=num_chunks
                ))
                
            except Exception as ing_error:
                logger.error(f"[{filename}] Ingestion failed: {ing_error}")
                firestore_service.update_document_status(doc_id, "failed", error_message=str(ing_error))
                results.append(BrowserUploadResponse(
                    doc_id=doc_id,
                    filename=filename,
                    status="failed",
                    num_chunks=0
                ))
                    
        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}", exc_info=True)
            results.append(BrowserUploadResponse(
                doc_id="",
                filename=filename,
                status="failed",
                num_chunks=0
            ))
    
    success_count = len([r for r in results if r.status == 'completed'])
    logger.info(f"Browser upload complete: {success_count}/{len(files)} successful")
    
    return results


@router.post("/upload/browser/stream")
async def upload_from_browser_stream(
    files: List[UploadFile] = File(...),
    project_id: str = Form(...),
    folder_paths: str = Form("{}")
):
    """
    Upload with Server-Sent Events for real-time progress.
    Frontend can display which file is currently being processed.
    """
    async def generate():
        storage_service = LocalStorageService()
        firestore_service = FirestoreService()
        ingestion_service = IngestionService()
        
        # Ensure project exists
        project = firestore_service.get_project(project_id)
        if not project:
            firestore_service.create_project(project_id, {
                "name": f"Project {project_id[:8]}",
                "description": "Created from browser upload"
            })
        
        total = len(files)
        
        for i, upload_file in enumerate(files):
            filename = upload_file.filename or f"document_{i}"
            doc_id = str(uuid.uuid4())
            
            # Send "processing" event
            yield f"data: {json.dumps({'event': 'processing', 'index': i, 'total': total, 'filename': filename, 'doc_id': doc_id})}\n\n"
            
            try:
                file_extension = filename.split('.')[-1] if '.' in filename else 'pdf'
                mime_type = upload_file.content_type or "application/pdf"
                
                # Save file
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp_file:
                    content = await upload_file.read()
                    tmp_file.write(content)
                    tmp_file.flush()
                    temp_path = tmp_file.name
                
                saved_path = storage_service.save_file(temp_path, project_id, doc_id)
                os.unlink(temp_path)
                
                # Create record
                firestore_service.create_document(
                    doc_id=doc_id,
                    data={
                        "project_id": project_id,
                        "title": filename.rsplit('.', 1)[0],
                        "file_path": str(saved_path),
                        "mime": mime_type,
                        "status": "processing"
                    }
                )
                
                # Process
                result = await ingestion_service.ingest_document(
                    doc_id=doc_id,
                    file_path=str(saved_path),
                    project_id=project_id,
                    doc_title=filename.rsplit('.', 1)[0],
                    mime_type=mime_type
                )
                
                # Send "completed" event
                yield f"data: {json.dumps({'event': 'completed', 'index': i, 'total': total, 'filename': filename, 'doc_id': doc_id, 'num_chunks': result.get('num_chunks', 0)})}\n\n"
                
            except Exception as e:
                logger.error(f"[{filename}] Failed: {e}")
                yield f"data: {json.dumps({'event': 'failed', 'index': i, 'total': total, 'filename': filename, 'error': str(e)})}\n\n"
        
        # Send "done" event
        yield f"data: {json.dumps({'event': 'done', 'total': total})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
