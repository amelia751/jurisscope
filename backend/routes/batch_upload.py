"""
Batch upload endpoint with smart parallel processing.
Uses intelligent batching: large files processed individually, small files grouped together.
"""
import logging
import asyncio
import os
from typing import List, Tuple
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.ingestion import IngestionService

logger = logging.getLogger(__name__)

router = APIRouter()


class FileUploadItem(BaseModel):
    """Single file upload item."""
    file_path: str
    project_id: str
    doc_title: str


class BatchUploadRequest(BaseModel):
    """Batch upload request."""
    files: List[FileUploadItem]
    max_concurrent: int = 5  # Max concurrent processing slots


class BatchUploadResponse(BaseModel):
    """Batch upload response."""
    total: int
    successful: int
    failed: int
    results: List[dict]
    strategy: str  # Description of batching strategy used


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def batch_upload(request: BatchUploadRequest):
    """
    Upload multiple files with smart batching.
    
    Strategy:
    - Large files (>500KB or regulation PDFs): Processed individually
    - Small/Medium files: Grouped together (up to 5 at a time)
    - This prevents large files from blocking small files
    """
    from services.gcs import GCSService
    from services.firestore import FirestoreService
    import uuid
    import mimetypes
    
    logger.info(f"Starting smart batch upload of {len(request.files)} files")
    
    results = []
    successful = 0
    failed = 0
    
    # Initialize services
    gcs_service = GCSService()
    firestore_service = FirestoreService()
    ingestion_service = IngestionService()
    
    def classify_file(file_item: FileUploadItem) -> Tuple[str, int]:
        """Classify file as 'small', 'medium', or 'large' based on size and name."""
        try:
            file_size = os.path.getsize(file_item.file_path)
            file_name = file_item.doc_title.lower()
            
            # Regulation files are always large (complex processing)
            if any(reg in file_name for reg in ['gdpr', 'regulation', 'act', 'dma', 'digital_markets']):
                return 'large', file_size
            
            # Classify by file size
            if file_size > 500_000:  # >500KB
                return 'large', file_size
            elif file_size > 100_000:  # 100-500KB
                return 'medium', file_size
            else:  # <100KB
                return 'small', file_size
        except:
            return 'medium', 0
    
    # Classify all files
    file_classifications = []
    for file_item in request.files:
        size_class, file_size = classify_file(file_item)
        file_classifications.append({
            'item': file_item,
            'class': size_class,
            'size': file_size
        })
    
    # Separate into large and small/medium
    large_files = [f for f in file_classifications if f['class'] == 'large']
    small_medium_files = [f for f in file_classifications if f['class'] in ['small', 'medium']]
    
    logger.info(f"📊 Classification: {len(large_files)} large, {len(small_medium_files)} small/medium")
    
    async def process_file(file_item: FileUploadItem):
        """Process a single file."""
        try:
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Get filename and extension
            filename = Path(file_item.file_path).name
            file_extension = Path(file_item.file_path).suffix.lstrip(".")
            
            # Create blob name
            blob_name = f"{file_item.project_id}/{doc_id}.{file_extension}"
            
            # Detect mime type
            mime_type, _ = mimetypes.guess_type(file_item.file_path)
            if not mime_type:
                mime_type = "application/pdf" if file_extension == "pdf" else "text/plain"
            
            # Upload to GCS
            gcs_uri = gcs_service.upload_file(
                source_file_path=file_item.file_path,
                destination_blob_name=blob_name,
                content_type=mime_type
            )
            
            logger.info(f"[{file_item.doc_title}] Uploaded to {gcs_uri}")
            
            # Create document metadata
            firestore_service.create_document(
                doc_id=doc_id,
                data={
                    "project_id": file_item.project_id,
                    "title": file_item.doc_title,
                    "gcs_uri": gcs_uri,
                    "mime": mime_type,
                    "status": "pending"
                }
            )
            
            # Start ingestion
            result = await ingestion_service.ingest_document(
                doc_id=doc_id,
                gcs_uri=gcs_uri,
                project_id=file_item.project_id,
                doc_title=file_item.doc_title,
                mime_type=mime_type
            )
            
            return {
                "file": file_item.doc_title,
                "status": "success",
                "doc_id": doc_id,
                "chunks": result.get("num_chunks", 0)
            }
            
        except Exception as e:
            logger.error(f"[{file_item.doc_title}] Failed: {e}")
            return {
                "file": file_item.doc_title,
                "status": "failed",
                "error": str(e)
            }
    
    # Create smart batches
    batches = []
    
    # Strategy 1: Process large files individually (1 per batch)
    for large_file in large_files:
        batches.append([large_file['item']])
    
    # Strategy 2: Group small/medium files together (5 per batch)
    for i in range(0, len(small_medium_files), 5):
        batch = [f['item'] for f in small_medium_files[i:i+5]]
        batches.append(batch)
    
    logger.info(f"🎯 Created {len(batches)} smart batches")
    
    # Process batches with controlled concurrency
    batch_num = 0
    while batch_num < len(batches):
        # Take up to max_concurrent batches at once
        current_batches = batches[batch_num:batch_num + request.max_concurrent]
        
        # Flatten to get all files in current wave
        files_in_wave = [file for batch in current_batches for file in batch]
        
        logger.info(f"🚀 Wave {batch_num//request.max_concurrent + 1}: Processing {len(files_in_wave)} files across {len(current_batches)} batches")
        
        # Process all files in this wave concurrently
        batch_results = await asyncio.gather(
            *[process_file(file_item) for file_item in files_in_wave],
            return_exceptions=True
        )
        
        for result in batch_results:
            if isinstance(result, Exception):
                failed += 1
                results.append({
                    "file": "unknown",
                    "status": "failed",
                    "error": str(result)
                })
            elif result["status"] == "success":
                successful += 1
                results.append(result)
            else:
                failed += 1
                results.append(result)
        
        batch_num += len(current_batches)
    
    strategy_description = f"Smart batching: {len(large_files)} large files individually, {len(small_medium_files)} small/medium files in groups of 5"
    logger.info(f"✅ Batch upload complete: {successful} successful, {failed} failed")
    
    return BatchUploadResponse(
        total=len(request.files),
        successful=successful,
        failed=failed,
        results=results,
        strategy=strategy_description
    )

