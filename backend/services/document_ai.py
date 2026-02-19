"""
Google Document AI service for OCR and layout extraction.
Extracts text with bounding boxes for pixel-perfect citations.
"""
import logging
import os
from typing import Dict, Any, List, Optional
from google.cloud import documentai_v1 as documentai
from google.oauth2 import service_account
from google.auth import default

from config import get_settings

logger = logging.getLogger(__name__)


class DocumentAIService:
    """Document AI operations for OCR and layout extraction."""
    
    def __init__(self):
        """Initialize Document AI client with service account credentials or ADC."""
        settings = get_settings()
        
        # Check if credentials file exists (local dev) or use ADC (Cloud Run)
        credentials_path = str(settings.gcp_credentials_path)
        if os.path.exists(credentials_path):
            logger.info(f"Using service account credentials from: {credentials_path}")
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.client = documentai.DocumentProcessorServiceClient(credentials=credentials)
        else:
            logger.info("Credentials file not found, using Application Default Credentials (ADC)")
            # Use ADC - Cloud Run provides credentials automatically
            self.client = documentai.DocumentProcessorServiceClient()
        
        self.processor_id = settings.document_ai_processor_id
        self.location = settings.document_ai_location
        self.project_id = settings.gcp_project_id
        
        logger.info(f"Document AI client initialized")
    
    def process_document(
        self,
        gcs_uri: str,
        mime_type: str = "application/pdf"
    ) -> documentai.Document:
        """
        Process a document from GCS using Document AI.
        
        Args:
            gcs_uri: GCS URI (gs://bucket/file.pdf)
            mime_type: MIME type of the document
        
        Returns:
            Document AI Document object with text, layout, and bounding boxes
        """
        if not self.processor_id or self.processor_id == "projects/clause-475719/locations/us/processors/YOUR_PROCESSOR_ID":
            raise ValueError(
                "Document AI processor ID not configured. "
                "Please create a processor and update DOCUMENT_AI_PROCESSOR_ID in .env.local"
            )
        
        # Configure the document source
        gcs_document = documentai.GcsDocument(
            gcs_uri=gcs_uri,
            mime_type=mime_type
        )
        
        # Process request - processor_id is already the full path
        request = documentai.ProcessRequest(
            name=self.processor_id,
            gcs_document=gcs_document
        )
        
        try:
            result = self.client.process_document(request=request)
            logger.info(f"Processed document: {gcs_uri}")
            return result.document
        except Exception as e:
            logger.error(f"Document AI processing failed: {e}")
            raise
    
    def extract_text_with_layout(
        self,
        document: documentai.Document
    ) -> Dict[str, Any]:
        """
        Extract text with detailed layout information (pages, bounding boxes).
        
        Returns:
            Dictionary with structured text and layout data:
            {
                "text": str (full document text),
                "pages": [
                    {
                        "page_number": int,
                        "width": float,
                        "height": float,
                        "tokens": [
                            {
                                "text": str,
                                "bbox": [x1, y1, x2, y2],
                                "char_start": int,
                                "char_end": int
                            }
                        ]
                    }
                ]
            }
        """
        full_text = document.text
        pages_data = []
        
        for page_idx, page in enumerate(document.pages):
            page_number = page_idx + 1
            
            # Get page dimensions
            page_width = page.dimension.width
            page_height = page.dimension.height
            
            # Extract tokens with bounding boxes
            tokens = []
            for token in page.tokens:
                # Get text for this token
                token_text = self._get_text_from_layout(token.layout, full_text)
                
                # Get bounding box (normalized coordinates)
                bbox = self._extract_bbox(token.layout.bounding_poly, page_width, page_height)
                
                # Get character offsets
                char_start = token.layout.text_anchor.text_segments[0].start_index if token.layout.text_anchor.text_segments else 0
                char_end = token.layout.text_anchor.text_segments[0].end_index if token.layout.text_anchor.text_segments else 0
                
                tokens.append({
                    "text": token_text,
                    "bbox": bbox,
                    "char_start": char_start,
                    "char_end": char_end
                })
            
            pages_data.append({
                "page_number": page_number,
                "width": page_width,
                "height": page_height,
                "tokens": tokens
            })
        
        return {
            "text": full_text,
            "pages": pages_data,
            "num_pages": len(pages_data)
        }
    
    def _get_text_from_layout(self, layout, full_text: str) -> str:
        """Extract text from layout using text anchors."""
        if not layout.text_anchor.text_segments:
            return ""
        
        # Concatenate all text segments
        text_parts = []
        for segment in layout.text_anchor.text_segments:
            start = segment.start_index
            end = segment.end_index
            text_parts.append(full_text[start:end])
        
        return "".join(text_parts)
    
    def _extract_bbox(
        self,
        bounding_poly,
        page_width: float,
        page_height: float,
        normalized: bool = True
    ) -> List[float]:
        """
        Extract bounding box coordinates.
        
        Args:
            bounding_poly: BoundingPoly object
            page_width: Page width
            page_height: Page height
            normalized: If True, return normalized coordinates (0-1 range)
        
        Returns:
            [x1, y1, x2, y2] coordinates
        """
        if not bounding_poly.vertices and not bounding_poly.normalized_vertices:
            return [0, 0, 0, 0]
        
        # Use normalized vertices if available, otherwise calculate from absolute
        if bounding_poly.normalized_vertices:
            vertices = bounding_poly.normalized_vertices
            x1 = vertices[0].x
            y1 = vertices[0].y
            x2 = vertices[2].x
            y2 = vertices[2].y
            
            if not normalized:
                x1 *= page_width
                y1 *= page_height
                x2 *= page_width
                y2 *= page_height
        else:
            vertices = bounding_poly.vertices
            x1 = vertices[0].x
            y1 = vertices[0].y
            x2 = vertices[2].x
            y2 = vertices[2].y
            
            if normalized:
                x1 /= page_width
                y1 /= page_height
                x2 /= page_width
                y2 /= page_height
        
        return [x1, y1, x2, y2]
    
    def extract_paragraphs(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """
        Extract paragraphs with their text and bounding boxes.
        Useful for creating document chunks at paragraph boundaries.
        """
        paragraphs = []
        full_text = document.text
        
        for page_idx, page in enumerate(document.pages):
            page_number = page_idx + 1
            
            for paragraph in page.paragraphs:
                paragraph_text = self._get_text_from_layout(paragraph.layout, full_text)
                bbox = self._extract_bbox(
                    paragraph.layout.bounding_poly,
                    page.dimension.width,
                    page.dimension.height
                )
                
                char_start = paragraph.layout.text_anchor.text_segments[0].start_index if paragraph.layout.text_anchor.text_segments else 0
                char_end = paragraph.layout.text_anchor.text_segments[0].end_index if paragraph.layout.text_anchor.text_segments else 0
                
                paragraphs.append({
                    "text": paragraph_text,
                    "page": page_number,
                    "bbox": bbox,
                    "char_start": char_start,
                    "char_end": char_end
                })
        
        return paragraphs

