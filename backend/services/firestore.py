"""
Local JSON-based storage service (replacing Firestore for hackathon).
Data model:
- projects/{projectId}
- documents/{docId}
- spans/{docId}
- queries/{queryId}
"""
import logging
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from config import get_settings

logger = logging.getLogger(__name__)


class FirestoreService:
    """Local file-based storage for metadata management (replacing Firestore)."""
    
    def __init__(self):
        """Initialize local storage directory."""
        settings = get_settings()
        
        # Use a local data directory
        self.data_dir = Path(settings.local_data_dir if hasattr(settings, 'local_data_dir') else "data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create collections directories
        self.collections = ["projects", "documents", "spans", "queries", "analysis_jobs", "analysis_results"]
        for collection in self.collections:
            (self.data_dir / collection).mkdir(exist_ok=True)
        
        logger.info(f"Local storage initialized at: {self.data_dir.resolve()}")
    
    def _get_collection_path(self, collection: str) -> Path:
        return self.data_dir / collection
    
    def _get_doc_path(self, collection: str, doc_id: str) -> Path:
        return self._get_collection_path(collection) / f"{doc_id}.json"
    
    def _read_doc(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        path = self._get_doc_path(collection, doc_id)
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return None
    
    def _write_doc(self, collection: str, doc_id: str, data: Dict[str, Any]):
        path = self._get_doc_path(collection, doc_id)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    def _delete_doc(self, collection: str, doc_id: str):
        path = self._get_doc_path(collection, doc_id)
        if path.exists():
            os.remove(path)
    
    def _list_docs(self, collection: str) -> List[Dict[str, Any]]:
        path = self._get_collection_path(collection)
        docs = []
        if path.exists():
            for file in path.glob("*.json"):
                with open(file, "r") as f:
                    data = json.load(f)
                    docs.append({"id": file.stem, **data})
        return docs
    
    def _now(self) -> str:
        return datetime.utcnow().isoformat()
    
    # ========== Project Operations ==========
    
    def create_project(self, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project."""
        now = self._now()
        project_data = {
            "name": data.get("name", "Untitled Project"),
            "description": data.get("description", ""),
            "created_at": now,
            "updated_at": now,
            "document_count": 0,
            "tags": data.get("tags", [])
        }
        self._write_doc("projects", project_id, project_data)
        logger.info(f"Created project: {project_id}")
        return {"id": project_id, **project_data}
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID."""
        data = self._read_doc("projects", project_id)
        if data:
            return {"id": project_id, **data}
        return None
    
    def list_projects(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all projects."""
        projects = self._list_docs("projects")
        return projects[:limit]
    
    def update_project(self, project_id: str, data: Dict[str, Any]):
        """Update project metadata."""
        existing = self._read_doc("projects", project_id)
        if existing:
            existing.update(data)
            existing["updated_at"] = self._now()
            self._write_doc("projects", project_id, existing)
            logger.info(f"Updated project: {project_id}")
    
    def delete_project(self, project_id: str):
        """Delete a project."""
        self._delete_doc("projects", project_id)
        logger.info(f"Deleted project: {project_id}")
    
    # ========== Document Operations ==========
    
    def create_document(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document metadata entry."""
        now = self._now()
        doc_data = {
            "project_id": data.get("project_id"),
            "title": data.get("title", "Untitled Document"),
            "file_path": data.get("file_path") or data.get("gcs_uri"),
            "mime": data.get("mime", "application/pdf"),
            "status": "pending",
            "es_index": data.get("es_index", ""),
            "num_pages": 0,
            "num_chunks": 0,
            "section_tree": {},
            "created_at": now,
            "updated_at": now,
            "error_message": None
        }
        self._write_doc("documents", doc_id, doc_data)
        logger.info(f"Created document: {doc_id}")
        return {"id": doc_id, **doc_data}
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        data = self._read_doc("documents", doc_id)
        if data:
            return {"id": doc_id, **data}
        return None
    
    def get_documents_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a project."""
        all_docs = self._list_docs("documents")
        return [d for d in all_docs if d.get("project_id") == project_id]
    
    def list_documents(self, project_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List documents, optionally filtered by project."""
        docs = self._list_docs("documents")
        if project_id:
            docs = [d for d in docs if d.get("project_id") == project_id]
        # Sort by created_at descending
        docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return docs[:limit]
    
    def update_document_status(
        self,
        doc_id: str,
        status: str,
        num_pages: Optional[int] = None,
        num_chunks: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Update document processing status."""
        existing = self._read_doc("documents", doc_id)
        if existing:
            existing["status"] = status
            existing["updated_at"] = self._now()
            if num_pages is not None:
                existing["num_pages"] = num_pages
            if num_chunks is not None:
                existing["num_chunks"] = num_chunks
            if error_message is not None:
                existing["error_message"] = error_message
            self._write_doc("documents", doc_id, existing)
            logger.info(f"Updated document {doc_id} status to: {status}")
    
    def update_document(self, doc_id: str, data: Dict[str, Any]):
        """Update a document."""
        existing = self._read_doc("documents", doc_id)
        if existing:
            existing.update(data)
            existing["updated_at"] = self._now()
            self._write_doc("documents", doc_id, existing)
            logger.info(f"Updated document: {doc_id}")
    
    def delete_document(self, doc_id: str):
        """Delete a document."""
        self._delete_doc("documents", doc_id)
        logger.info(f"Deleted document: {doc_id}")
    
    # ========== Span Map Operations ==========
    
    def save_span_map(self, doc_id: str, span_map: Dict[str, Any]):
        """Save the span map for a document."""
        self._write_doc("spans", doc_id, {
            "doc_id": doc_id,
            "span_map": span_map,
            "updated_at": self._now()
        })
        logger.info(f"Saved span map for document: {doc_id}")
    
    def get_span_map(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get span map for a document."""
        data = self._read_doc("spans", doc_id)
        if data:
            return data.get("span_map", {})
        return None
    
    def delete_span_map(self, doc_id: str):
        """Delete span map for a document."""
        self._delete_doc("spans", doc_id)
        logger.info(f"Deleted span map for document: {doc_id}")
    
    # ========== Query Logging ==========
    
    def log_query(
        self,
        query_id: str,
        query_text: str,
        project_id: str,
        results: Dict[str, Any]
    ):
        """Log a query for traceability."""
        self._write_doc("queries", query_id, {
            "query_text": query_text,
            "project_id": project_id,
            "num_hits": results.get("num_hits", 0),
            "latency_ms": results.get("latency_ms", 0),
            "agent_path": results.get("agent_path", []),
            "created_at": self._now()
        })
        logger.info(f"Logged query: {query_id}")
    
    def get_query_log(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Get query log by ID."""
        data = self._read_doc("queries", query_id)
        if data:
            return {"id": query_id, **data}
        return None
    
    # ========== Analysis Job Operations ==========
    
    def create_analysis_job(self, job_data: Dict[str, Any]):
        """Create a new analysis job."""
        job_id = job_data["job_id"]
        job_data["created_at"] = self._now()
        self._write_doc("analysis_jobs", job_id, job_data)
        logger.info(f"Created analysis job: {job_id}")
    
    def update_analysis_job(self, job_id: str, updates: Dict[str, Any]):
        """Update an analysis job."""
        existing = self._read_doc("analysis_jobs", job_id)
        if existing:
            existing.update(updates)
            self._write_doc("analysis_jobs", job_id, existing)
            logger.debug(f"Updated analysis job: {job_id}")
    
    def get_analysis_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get an analysis job by ID."""
        data = self._read_doc("analysis_jobs", job_id)
        if data:
            return {"id": job_id, **data}
        return None
    
    def store_analysis_result(self, analysis_data: Dict[str, Any]):
        """Store analysis result for a document."""
        document_id = analysis_data["documentId"]
        
        existing = self._read_doc("analysis_results", document_id)
        if existing:
            existing_custom = existing.get("customColumns", {})
            new_custom = analysis_data.get("customColumns", {})
            merged_custom = {**existing_custom, **new_custom}
            analysis_data["customColumns"] = merged_custom
        
        analysis_data["updated_at"] = self._now()
        self._write_doc("analysis_results", document_id, analysis_data)
        logger.info(f"Stored analysis result for document: {document_id}")
    
    def update_analysis_custom_column(
        self,
        document_id: str,
        vault_id: str,
        column_name: str,
        value: str
    ):
        """Update a custom column for a document's analysis."""
        field_key = column_name.replace(" ", "_").replace("-", "_").lower()
        
        existing = self._read_doc("analysis_results", document_id)
        if existing:
            custom_columns = existing.get("customColumns", {})
            custom_columns[field_key] = value
            existing["customColumns"] = custom_columns
            existing["updated_at"] = self._now()
            self._write_doc("analysis_results", document_id, existing)
        else:
            self._write_doc("analysis_results", document_id, {
                "documentId": document_id,
                "vaultId": vault_id,
                "customColumns": {field_key: value},
                "updated_at": self._now()
            })
        
        logger.debug(f"Updated custom column '{column_name}' for document: {document_id}")
    
    def get_analysis_results(self, vault_id: str) -> List[Dict[str, Any]]:
        """Get all analysis results for a vault."""
        all_results = self._list_docs("analysis_results")
        results = [r for r in all_results if r.get("vaultId") == vault_id]
        logger.debug(f"Retrieved {len(results)} analysis results for vault: {vault_id}")
        return results
    
    def delete_analysis_results(self, vault_id: str) -> int:
        """Delete all analysis results for a vault."""
        all_results = self._list_docs("analysis_results")
        count = 0
        for r in all_results:
            if r.get("vaultId") == vault_id:
                self._delete_doc("analysis_results", r["id"])
                count += 1
        logger.info(f"Deleted {count} analysis results for vault: {vault_id}")
        return count
    
    def get_documents_by_vault(self, vault_id: str) -> List[Dict[str, Any]]:
        """Get all documents in a vault."""
        all_docs = self._list_docs("documents")
        documents = [d for d in all_docs if d.get("vaultId") == vault_id]
        logger.debug(f"Retrieved {len(documents)} documents for vault: {vault_id}")
        return documents
