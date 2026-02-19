"""
Service for batch document analysis using Elastic's inference API.
Handles structured extraction of metadata for table view.
"""
import logging
import json
from typing import List, Dict, Any
from datetime import datetime

from services.elastic_inference import get_inference_service
from services.elasticsearch import ElasticsearchService
from services.firestore import FirestoreService

logger = logging.getLogger(__name__)


class TableAnalysisService:
    """Handles batch document analysis for table view using Elastic inference"""
    
    def __init__(self):
        self.inference = get_inference_service()
        self.elasticsearch = ElasticsearchService()
        self.firestore = FirestoreService()
    
    def process_template_batch(
        self,
        job_id: str,
        vault_id: str,
        documents: List[Dict],
        template: str
    ):
        """
        Process all documents with a predefined template.
        This runs synchronously in a background task.
        """
        try:
            logger.info(f"[{job_id}] Starting batch analysis for {len(documents)} documents")
            
            self.firestore.update_analysis_job(job_id, {"status": "processing"})
            
            total = len(documents)
            processed = 0
            failed = 0
            
            for doc in documents:
                try:
                    doc_name = doc.get('name', 'unknown')
                    logger.info(f"[{job_id}] Processing document: {doc_name}")
                    
                    # Get document chunks from Elasticsearch
                    firestore_doc_id = doc.get("firestoreDocId") or doc.get("id")
                    if not firestore_doc_id:
                        logger.warning(f"[{job_id}] No firestoreDocId for document {doc.get('id')}")
                        failed += 1
                        continue
                    
                    # Pass both doc_id and doc_title (name) for fallback search
                    chunks = self._get_document_chunks(firestore_doc_id, doc_name)
                    
                    if not chunks:
                        logger.warning(f"[{job_id}] No chunks found for document {doc.get('id')}")
                        failed += 1
                        continue
                    
                    # Build context from chunks
                    context = self._build_context(chunks, max_chunks=5, max_chars=4000)
                    
                    # Extract metadata using Elastic inference
                    if template == "evidence_discovery":
                        analysis = self._extract_evidence_metadata(context, doc_name)
                    else:
                        logger.warning(f"[{job_id}] Unknown template: {template}")
                        failed += 1
                        continue
                    
                    # Store result in Firestore
                    self.firestore.store_analysis_result({
                        "documentId": doc.get("id"),
                        "vaultId": vault_id,
                        **analysis
                    })
                    
                    processed += 1
                    progress = int((processed / total) * 100)
                    
                    logger.info(f"[{job_id}] Progress: {processed}/{total} ({progress}%)")
                    
                    self.firestore.update_analysis_job(job_id, {
                        "processed_docs": processed,
                        "progress": progress
                    })
                    
                except Exception as e:
                    logger.error(f"[{job_id}] Failed to process document {doc.get('id')}: {e}", exc_info=True)
                    failed += 1
                    continue
            
            logger.info(f"[{job_id}] Batch processing completed. Processed: {processed}, Failed: {failed}")
            self.firestore.update_analysis_job(job_id, {
                "status": "completed",
                "completedAt": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"[{job_id}] Batch processing failed: {e}", exc_info=True)
            self.firestore.update_analysis_job(job_id, {
                "status": "failed",
                "error": str(e)
            })
    
    def process_custom_column(
        self,
        job_id: str,
        vault_id: str,
        documents: List[Dict],
        column_name: str,
        question: str
    ):
        """Process custom column by asking a question about each document"""
        try:
            logger.info(f"[{job_id}] Starting custom column '{column_name}' for {len(documents)} documents")
            
            self.firestore.update_analysis_job(job_id, {"status": "processing"})
            
            total = len(documents)
            processed = 0
            failed = 0
            
            for doc in documents:
                try:
                    doc_name = doc.get("name", "unknown")
                    firestore_doc_id = doc.get("firestoreDocId") or doc.get("id")
                    if not firestore_doc_id:
                        failed += 1
                        continue
                    
                    # Pass both doc_id and doc_title for fallback search
                    chunks = self._get_document_chunks(firestore_doc_id, doc_name)
                    
                    if not chunks:
                        failed += 1
                        continue
                    
                    context = self._build_context(chunks, max_chunks=3, max_chars=3000)
                    
                    # Ask the question using Elastic inference
                    answer = self._ask_question(doc_name, context, question)
                    
                    # Store custom column result
                    self.firestore.update_analysis_custom_column(
                        doc.get("id"),
                        vault_id,
                        column_name,
                        answer.strip()
                    )
                    
                    processed += 1
                    progress = int((processed / total) * 100)
                    
                    logger.info(f"[{job_id}] Progress: {processed}/{total} ({progress}%)")
                    
                    self.firestore.update_analysis_job(job_id, {
                        "processed_docs": processed,
                        "progress": progress
                    })
                    
                except Exception as e:
                    logger.error(f"[{job_id}] Failed to process document {doc.get('id')}: {e}")
                    failed += 1
                    continue
            
            logger.info(f"[{job_id}] Custom column completed. Processed: {processed}, Failed: {failed}")
            self.firestore.update_analysis_job(job_id, {
                "status": "completed",
                "completedAt": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"[{job_id}] Custom column processing failed: {e}", exc_info=True)
            self.firestore.update_analysis_job(job_id, {
                "status": "failed",
                "error": str(e)
            })
    
    def _get_document_chunks(self, doc_id: str, doc_title: str = None) -> List[Dict[str, Any]]:
        """Get document chunks from Elasticsearch by doc_id or doc_title"""
        try:
            # First, try by doc_id
            search_body = {
                "query": {
                    "term": {"doc_id": doc_id}
                },
                "_source": ["text", "page", "doc_title"],
                "size": 10,
                "sort": [{"page": "asc"}]
            }
            
            response = self.elasticsearch.client.search(
                index=self.elasticsearch.index_name,
                body=search_body
            )
            
            hits = response.get("hits", {}).get("hits", [])
            
            # If no results by doc_id, try by doc_title
            if not hits and doc_title:
                logger.info(f"No chunks found by doc_id, trying doc_title: {doc_title}")
                search_body = {
                    "query": {
                        "term": {"doc_title.keyword": doc_title}
                    },
                    "_source": ["text", "page", "doc_title"],
                    "size": 10,
                    "sort": [{"page": "asc"}]
                }
                
                response = self.elasticsearch.client.search(
                    index=self.elasticsearch.index_name,
                    body=search_body
                )
                
                hits = response.get("hits", {}).get("hits", [])
            
            return [hit["_source"] for hit in hits]
            
        except Exception as e:
            logger.error(f"Failed to get chunks for {doc_id} / {doc_title}: {e}")
            return []
    
    def _build_context(self, chunks: List[Dict], max_chunks: int = 5, max_chars: int = 4000) -> str:
        """Build context from chunks with limits"""
        context_parts = []
        total_chars = 0
        
        for chunk in chunks[:max_chunks]:
            text = chunk.get("text", "")
            if total_chars + len(text) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:
                    context_parts.append(text[:remaining] + "...")
                break
            context_parts.append(text)
            total_chars += len(text)
        
        return "\n\n".join(context_parts)
    
    def _extract_evidence_metadata(self, context: str, doc_name: str) -> Dict[str, Any]:
        """
        Extract structured metadata using Elastic's inference API.
        """
        prompt = f"""Analyze this legal document and extract the following information in JSON format:

Document Name: {doc_name}

Document Content:
{context}

Extract:
1. date: The date mentioned in the document (YYYY-MM-DD format, or "Unknown")
2. documentType: Type of document (e.g., "Email", "Contract", "Memo", "Report", "Letter", "Transcript", "Regulation", "Court Filing", etc.)
3. summary: A brief 1-2 sentence summary of the document's main content
4. author: The author or sender of the document ("Unknown" if not clear)
5. personsMentioned: List of person names mentioned in the document (array of strings)
6. language: Language of the document (e.g., "English", "Spanish", etc.)

Return ONLY valid JSON in this exact format:
{{
  "date": "YYYY-MM-DD or Unknown",
  "documentType": "type here",
  "summary": "summary here",
  "author": "author name or Unknown",
  "personsMentioned": ["name1", "name2"],
  "language": "English"
}}

Be specific and accurate. For dates, look for explicit dates like "October 23, 2024" or "2024-10-23". For persons mentioned, only include actual person names, not organizations."""

        system_instruction = "You are a legal document analyzer. Extract metadata accurately from legal documents. Always return valid JSON in the exact format requested. Be thorough and accurate."
        
        try:
            response = self.inference.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_instruction,
                model=".openai-gpt-4.1-mini-chat_completion"  # Use faster model for batch processing
            )
            
            logger.debug(f"Raw inference response: {response[:500]}...")
            
            # Clean response (remove markdown code blocks if present)
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                response = "\n".join(lines)
            
            analysis = json.loads(response)
            
            result = {
                "date": analysis.get("date", "Unknown"),
                "documentType": analysis.get("documentType", "Unknown"),
                "summary": analysis.get("summary", "No summary available"),
                "author": analysis.get("author", "Unknown"),
                "personsMentioned": analysis.get("personsMentioned", []),
                "language": analysis.get("language", "English")
            }
            
            logger.info(f"Successfully extracted metadata for {doc_name}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}\nResponse: {response}")
            return {
                "date": "Unknown",
                "documentType": "Unknown",
                "summary": "Failed to extract metadata",
                "author": "Unknown",
                "personsMentioned": [],
                "language": "Unknown"
            }
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {
                "date": "Unknown",
                "documentType": "Unknown",
                "summary": "Error during extraction",
                "author": "Unknown",
                "personsMentioned": [],
                "language": "Unknown"
            }
    
    def _ask_question(self, doc_name: str, context: str, question: str) -> str:
        """Ask a custom question about a document"""
        prompt = f"""Document: {doc_name}

Content:
{context}

Question: {question}

Provide a concise, factual answer (max 200 characters). If the information is not in the document, say "Not mentioned"."""
        
        try:
            answer = self.inference.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=".openai-gpt-4.1-mini-chat_completion"
            )
            
            answer = answer.strip()
            if len(answer) > 200:
                answer = answer[:197] + "..."
            
            return answer
            
        except Exception as e:
            logger.error(f"Error asking question: {e}")
            return "Error"
