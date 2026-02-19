"""
Document ingestion service for JurisScope.
Orchestrates: PDF Processing → Chunking → Embeddings → ES Indexing
"""
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from services.pdf_processor import PDFProcessorService
from services.embeddings import EmbeddingService
from services.elasticsearch import ElasticsearchService
from services.firestore import FirestoreService

logger = logging.getLogger(__name__)


class IngestionService:
    """Document ingestion pipeline orchestrator."""
    
    def __init__(self):
        """Initialize services."""
        self.pdf_processor = PDFProcessorService()
        self.embeddings = EmbeddingService()
        self.elasticsearch = ElasticsearchService()
        self.firestore = FirestoreService()
        
        # Chunking parameters
        self.chunk_size = 512
        self.chunk_overlap = 50
        
        logger.info("Ingestion service initialized")
    
    async def ingest_document(
        self,
        doc_id: str,
        file_path: str,
        project_id: str,
        doc_title: str,
        mime_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """
        Complete document ingestion pipeline.
        
        Args:
            doc_id: Unique document ID
            file_path: Path to the document file
            project_id: Project ID
            doc_title: Document title
            mime_type: MIME type
        
        Returns:
            Ingestion results
        """
        logger.info(f"Starting ingestion for document: {doc_id}")
        
        try:
            # Update status to processing
            self.firestore.update_document_status(doc_id, "processing")
            
            # Step 1: Process document
            logger.info(f"[{doc_id}] Step 1/4: Processing document...")
            doc_data = self.pdf_processor.process_pdf(file_path)
            full_text = doc_data["text"]
            num_pages = doc_data["num_pages"]
            pages = doc_data["pages"]
            
            logger.info(f"[{doc_id}] Extracted {len(full_text)} chars from {num_pages} pages")
            
            # Step 2: Chunk the document
            logger.info(f"[{doc_id}] Step 2/4: Chunking document...")
            chunks = self._chunk_document(
                doc_data=doc_data,
                doc_id=doc_id,
                doc_title=doc_title,
                project_id=project_id
            )
            logger.info(f"[{doc_id}] Created {len(chunks)} chunks")
            
            # Step 3: Generate embeddings
            logger.info(f"[{doc_id}] Step 3/4: Generating embeddings...")
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = self.embeddings.generate_embeddings(chunk_texts)
            
            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk["vector"] = embedding
            
            logger.info(f"[{doc_id}] Generated {len(embeddings)} embeddings")
            
            # Step 4: Ensure index exists and index to Elasticsearch
            logger.info(f"[{doc_id}] Step 4/4: Indexing to Elasticsearch...")
            await self.elasticsearch.ensure_index()
            index_result = self.elasticsearch.bulk_index_documents(chunks)
            logger.info(f"[{doc_id}] Indexed {index_result['success']} chunks")
            
            # Save span map
            span_map = self._build_span_map(chunks)
            self.firestore.save_span_map(doc_id, span_map)
            
            # Update document status
            self.firestore.update_document_status(
                doc_id,
                "indexed",
                num_pages=num_pages,
                num_chunks=len(chunks)
            )
            
            logger.info(f"[{doc_id}] ✓ Ingestion complete")
            
            return {
                "doc_id": doc_id,
                "status": "indexed",
                "num_pages": num_pages,
                "num_chunks": len(chunks),
                "num_chars": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"[{doc_id}] ✗ Ingestion failed: {e}", exc_info=True)
            self.firestore.update_document_status(
                doc_id,
                "failed",
                error_message=str(e)
            )
            raise
    
    def _chunk_document(
        self,
        doc_data: Dict[str, Any],
        doc_id: str,
        doc_title: str,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Chunk document while preserving page info."""
        full_text = doc_data["text"]
        pages = doc_data["pages"]
        
        # Build character to page mapping
        char_to_page = {}
        for page in pages:
            for char_idx in range(page["char_start"], page["char_end"]):
                char_to_page[char_idx] = page["page_number"]
        
        # Chunk the text
        raw_chunks = self.embeddings.chunk_text(
            full_text,
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap
        )
        
        chunks = []
        for raw_chunk in raw_chunks:
            # Determine primary page
            chunk_pages = []
            for char_idx in range(raw_chunk["char_start"], min(raw_chunk["char_end"], len(full_text))):
                if char_idx in char_to_page:
                    chunk_pages.append(char_to_page[char_idx])
            
            primary_page = max(set(chunk_pages), key=chunk_pages.count) if chunk_pages else 1
            
            # Get bbox from page data
            bbox_list = []
            for page in pages:
                if page["page_number"] == primary_page:
                    # Sample a few tokens for bbox
                    for token in page.get("tokens", [])[:3]:
                        bbox_list.append({
                            "x1": token["bbox"][0],
                            "y1": token["bbox"][1],
                            "x2": token["bbox"][2],
                            "y2": token["bbox"][3]
                        })
                    break
            
            chunk_id = f"{doc_id}_chunk_{raw_chunk['chunk_index']}"
            chunk = {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "doc_title": doc_title,
                "project_id": project_id,
                "text": raw_chunk["text"],
                "char_start": raw_chunk["char_start"],
                "char_end": raw_chunk["char_end"],
                "page": primary_page,
                "bbox_list": bbox_list,
                "section_path": "",
                "tags": [],
                "created_at": datetime.now().isoformat()
            }
            chunks.append(chunk)
        
        return chunks
    
    def _build_span_map(self, chunks: List[Dict[str, Any]]) -> Dict:
        """Build span map for citation highlighting."""
        span_map = {}
        for chunk in chunks:
            span_map[chunk["chunk_id"]] = {
                "page": chunk["page"],
                "bbox_list": chunk["bbox_list"],
                "char_range": [chunk["char_start"], chunk["char_end"]]
            }
        return span_map
