"""
Table analysis routes for batch document processing.
Provides endpoints for running batch analysis with templates or custom questions.
Uses Elastic's inference API for LLM analysis.
"""
import logging
import time
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from services.firestore import FirestoreService
from services.table_analysis import TableAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalysisRequest(BaseModel):
    """Request to start batch analysis with a template"""
    vault_id: str
    template: str  # "evidence_discovery"
    documents: Optional[List[Dict[str, Any]]] = None  # Documents from frontend


class CustomColumnRequest(BaseModel):
    """Request to add a custom column with AI"""
    vault_id: str
    column_name: str
    question: str
    documents: Optional[List[Dict[str, Any]]] = None  # Documents from frontend


class AnalysisResponse(BaseModel):
    """Response for analysis request"""
    job_id: str
    status: str
    message: str
    total_docs: int


@router.post("/table/batch-analyze", response_model=AnalysisResponse)
async def batch_analyze(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Start batch analysis of all documents in a vault using a template.
    Runs asynchronously in background.
    
    Templates:
    - evidence_discovery: Extracts Date, Document Type, Summary, Author, Persons Mentioned, Language
    """
    try:
        logger.info(f"Batch analyze request: vault={request.vault_id}, template={request.template}")
        
        firestore = FirestoreService()
        
        # Get documents from request or fallback to Firestore
        if request.documents:
            documents = request.documents
            logger.info(f"Using {len(documents)} documents from request")
        else:
            documents = firestore.get_documents_by_project(request.vault_id)
            logger.info(f"Fetched {len(documents)} documents from Firestore")
        
        if not documents:
            raise HTTPException(status_code=404, detail="No documents found in vault")
        
        # Filter to only completed/indexed documents (accept both statuses)
        valid_statuses = ["indexed", "completed", "processed"]
        completed_docs = [d for d in documents if d.get("status") in valid_statuses]
        
        if not completed_docs:
            statuses = [d.get("status") for d in documents]
            logger.warning(f"Document statuses: {statuses}")
            raise HTTPException(
                status_code=400,
                detail=f"No indexed/completed documents found. {len(documents)} documents have statuses: {set(statuses)}"
            )
        
        logger.info(f"Found {len(completed_docs)} indexed documents to analyze")
        
        # Create job ID
        job_id = f"job_{request.vault_id}_{int(time.time())}"
        
        # Create job in Firestore
        firestore.create_analysis_job({
            "job_id": job_id,
            "vault_id": request.vault_id,
            "type": "template",
            "template": request.template,
            "status": "pending",
            "total_docs": len(completed_docs),
            "processed_docs": 0,
            "progress": 0,
        })
        
        logger.info(f"Created analysis job: {job_id}")
        
        # Start background processing
        analysis_service = TableAnalysisService()
        background_tasks.add_task(
            analysis_service.process_template_batch,
            job_id,
            request.vault_id,
            completed_docs,
            request.template
        )
        
        return AnalysisResponse(
            job_id=job_id,
            status="pending",
            message=f"Started analysis of {len(completed_docs)} documents",
            total_docs=len(completed_docs)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/table/custom-column", response_model=AnalysisResponse)
async def add_custom_column(request: CustomColumnRequest, background_tasks: BackgroundTasks):
    """
    Add a custom column by asking a question about all documents.
    The AI will answer the question for each document.
    """
    try:
        logger.info(f"Custom column request: vault={request.vault_id}, column={request.column_name}")
        
        firestore = FirestoreService()
        
        # Get documents from request or fallback to Firestore
        if request.documents:
            documents = request.documents
            logger.info(f"Using {len(documents)} documents from request")
        else:
            documents = firestore.get_documents_by_project(request.vault_id)
            logger.info(f"Fetched {len(documents)} documents from Firestore")
        
        if not documents:
            raise HTTPException(status_code=404, detail="No documents found")
        
        # Filter to only completed/indexed documents
        valid_statuses = ["indexed", "completed", "processed"]
        completed_docs = [d for d in documents if d.get("status") in valid_statuses]
        
        if not completed_docs:
            statuses = [d.get("status") for d in documents]
            logger.warning(f"Document statuses: {statuses}")
            raise HTTPException(
                status_code=400,
                detail=f"No indexed/completed documents found. {len(documents)} documents have statuses: {set(statuses)}"
            )
        
        # Create job ID
        job_id = f"col_{request.vault_id}_{int(time.time())}"
        
        # Create job in Firestore
        firestore.create_analysis_job({
            "job_id": job_id,
            "vault_id": request.vault_id,
            "type": "custom_column",
            "column_name": request.column_name,
            "question": request.question,
            "status": "pending",
            "total_docs": len(completed_docs),
            "processed_docs": 0,
            "progress": 0,
        })
        
        logger.info(f"Created custom column job: {job_id}")
        
        # Start background processing
        analysis_service = TableAnalysisService()
        background_tasks.add_task(
            analysis_service.process_custom_column,
            job_id,
            request.vault_id,
            completed_docs,
            request.column_name,
            request.question
        )
        
        return AnalysisResponse(
            job_id=job_id,
            status="pending",
            message=f"Processing {len(completed_docs)} documents for column '{request.column_name}'",
            total_docs=len(completed_docs)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Custom column failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/table/job/{job_id}")
async def get_job_status(job_id: str):
    """
    Get status of an analysis job.
    """
    try:
        firestore = FirestoreService()
        
        job = firestore.get_analysis_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/table/results/{vault_id}")
async def get_analysis_results(vault_id: str):
    """
    Get all analysis results for a vault.
    """
    try:
        firestore = FirestoreService()
        
        results = firestore.get_analysis_results(vault_id)
        
        logger.info(f"Returning {len(results)} analysis results for vault: {vault_id}")
        
        output = []
        for r in results:
            output.append({
                "id": r.get("documentId"),
                "analysis": {
                    "date": r.get("date"),
                    "documentType": r.get("documentType"),
                    "summary": r.get("summary"),
                    "author": r.get("author"),
                    "personsMentioned": r.get("personsMentioned", []),
                    "language": r.get("language"),
                    "customColumns": r.get("customColumns", {})
                }
            })
        
        return output
        
    except Exception as e:
        logger.error(f"Failed to get results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/table/results/{vault_id}")
async def delete_analysis_results(vault_id: str):
    """
    Delete all analysis results for a vault.
    """
    try:
        firestore = FirestoreService()
        
        count = firestore.delete_analysis_results(vault_id)
        
        return {
            "message": f"Deleted {count} analysis results",
            "vault_id": vault_id
        }
        
    except Exception as e:
        logger.error(f"Failed to delete results: {e}")
        raise HTTPException(status_code=500, detail=str(e))
