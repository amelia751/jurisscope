"""
Local storage service for JurisScope.
Replaces GCS for hackathon - stores files locally.
"""
import os
import shutil
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
PROCESSED_DIR = BASE_DIR / "processed"
METADATA_DIR = BASE_DIR / "metadata"


class LocalStorageService:
    """Local file storage (replaces GCS for hackathon)."""
    
    def __init__(self):
        """Initialize local storage directories."""
        UPLOADS_DIR.mkdir(exist_ok=True)
        PROCESSED_DIR.mkdir(exist_ok=True)
        logger.info(f"Local storage initialized: {UPLOADS_DIR}")
    
    def save_file(self, source_path: str, project_id: str, doc_id: str) -> str:
        """
        Save a file to local storage.
        
        Returns:
            Local file path
        """
        source = Path(source_path)
        dest_dir = UPLOADS_DIR / project_id
        dest_dir.mkdir(exist_ok=True)
        
        dest_path = dest_dir / f"{doc_id}{source.suffix}"
        shutil.copy2(source, dest_path)
        
        logger.info(f"Saved file to: {dest_path}")
        return str(dest_path)
    
    def get_file_path(self, project_id: str, doc_id: str, extension: str = ".pdf") -> Path:
        """Get the path to a stored file."""
        return UPLOADS_DIR / project_id / f"{doc_id}{extension}"
    
    def file_exists(self, project_id: str, doc_id: str, extension: str = ".pdf") -> bool:
        """Check if a file exists."""
        return self.get_file_path(project_id, doc_id, extension).exists()
    
    def delete_file(self, project_id: str, doc_id: str, extension: str = ".pdf"):
        """Delete a file."""
        path = self.get_file_path(project_id, doc_id, extension)
        if path.exists():
            path.unlink()
            logger.info(f"Deleted file: {path}")


class LocalMetadataService:
    """Local metadata storage (replaces Firestore for hackathon)."""
    
    def __init__(self):
        """Initialize metadata storage."""
        METADATA_DIR.mkdir(exist_ok=True)
        self.documents_file = METADATA_DIR / "documents.json"
        self.projects_file = METADATA_DIR / "projects.json"
        self.spans_file = METADATA_DIR / "spans.json"
        self.queries_file = METADATA_DIR / "queries.json"
        
        # Initialize files if they don't exist
        for file in [self.documents_file, self.projects_file, self.spans_file, self.queries_file]:
            if not file.exists():
                file.write_text("{}")
        
        logger.info(f"Local metadata initialized: {METADATA_DIR}")
    
    def _load_json(self, file: Path) -> Dict:
        """Load JSON from file."""
        try:
            return json.loads(file.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_json(self, file: Path, data: Dict):
        """Save JSON to file."""
        file.write_text(json.dumps(data, indent=2, default=str))
    
    # Document methods
    def create_document(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a document record."""
        docs = self._load_json(self.documents_file)
        docs[doc_id] = {
            **data,
            "id": doc_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self._save_json(self.documents_file, docs)
        logger.info(f"Created document: {doc_id}")
        return docs[doc_id]
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        docs = self._load_json(self.documents_file)
        return docs.get(doc_id)
    
    def update_document_status(self, doc_id: str, status: str, **kwargs):
        """Update document status."""
        docs = self._load_json(self.documents_file)
        if doc_id in docs:
            docs[doc_id]["status"] = status
            docs[doc_id]["updated_at"] = datetime.now().isoformat()
            docs[doc_id].update(kwargs)
            self._save_json(self.documents_file, docs)
            logger.info(f"Updated document {doc_id} status to: {status}")
    
    def list_documents(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List documents, optionally filtered by project."""
        docs = self._load_json(self.documents_file)
        result = list(docs.values())
        if project_id:
            result = [d for d in result if d.get("project_id") == project_id]
        return result
    
    # Project methods
    def create_project(self, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a project."""
        projects = self._load_json(self.projects_file)
        projects[project_id] = {
            **data,
            "id": project_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self._save_json(self.projects_file, projects)
        return projects[project_id]
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a project by ID."""
        projects = self._load_json(self.projects_file)
        return projects.get(project_id)
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects."""
        projects = self._load_json(self.projects_file)
        return list(projects.values())
    
    # Span map methods
    def save_span_map(self, doc_id: str, span_map: Dict):
        """Save span map for a document."""
        spans = self._load_json(self.spans_file)
        spans[doc_id] = span_map
        self._save_json(self.spans_file, spans)
    
    def get_span_map(self, doc_id: str) -> Optional[Dict]:
        """Get span map for a document."""
        spans = self._load_json(self.spans_file)
        return spans.get(doc_id)
    
    # Query logging
    def log_query(self, query_id: str, query_text: str, project_id: str, results: Dict):
        """Log a query for traceability."""
        queries = self._load_json(self.queries_file)
        queries[query_id] = {
            "id": query_id,
            "query_text": query_text,
            "project_id": project_id,
            "results": results,
            "created_at": datetime.now().isoformat()
        }
        self._save_json(self.queries_file, queries)
    
    def get_query_log(self, query_id: str) -> Optional[Dict]:
        """Get query log by ID."""
        queries = self._load_json(self.queries_file)
        return queries.get(query_id)
