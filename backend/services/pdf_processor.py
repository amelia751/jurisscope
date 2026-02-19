"""
PDF processing service for JurisScope.
Extracts text from PDFs using pdfplumber.
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import pdfplumber

logger = logging.getLogger(__name__)


class PDFProcessorService:
    """Extract text and metadata from PDF documents."""
    
    def process_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Process a PDF and extract text with page information.
        
        Returns:
            Dict with 'text', 'num_pages', 'pages' (list of page data)
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")
        
        if path.suffix.lower() != ".pdf":
            # Handle text files
            if path.suffix.lower() in [".txt", ".md"]:
                return self._process_text_file(path)
            raise ValueError(f"Unsupported file type: {path.suffix}")
        
        try:
            pages = []
            full_text = ""
            char_offset = 0
            
            with pdfplumber.open(path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ""
                    
                    # Get page dimensions
                    width = page.width
                    height = page.height
                    
                    # Extract words with bounding boxes
                    words = page.extract_words() or []
                    tokens = []
                    
                    for word in words:
                        token_data = {
                            "text": word.get("text", ""),
                            "char_start": char_offset + page_text.find(word.get("text", "")),
                            "char_end": char_offset + page_text.find(word.get("text", "")) + len(word.get("text", "")),
                            "bbox": [
                                word.get("x0", 0) / width,  # Normalize to 0-1
                                word.get("top", 0) / height,
                                word.get("x1", 0) / width,
                                word.get("bottom", 0) / height
                            ]
                        }
                        tokens.append(token_data)
                    
                    pages.append({
                        "page_number": page_num,
                        "text": page_text,
                        "width": width,
                        "height": height,
                        "tokens": tokens,
                        "char_start": char_offset,
                        "char_end": char_offset + len(page_text)
                    })
                    
                    full_text += page_text + "\n"
                    char_offset += len(page_text) + 1
                
                result = {
                    "text": full_text.strip(),
                    "num_pages": len(pdf.pages),
                    "pages": pages
                }
                
                logger.info(f"Processed PDF: {path.name} ({len(pdf.pages)} pages, {len(full_text)} chars)")
                return result
                
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise
    
    def _process_text_file(self, path: Path) -> Dict[str, Any]:
        """Process a text file."""
        text = path.read_text(encoding="utf-8", errors="replace")
        
        return {
            "text": text,
            "num_pages": 1,
            "pages": [{
                "page_number": 1,
                "text": text,
                "width": 1,
                "height": 1,
                "tokens": [{
                    "text": text,
                    "char_start": 0,
                    "char_end": len(text),
                    "bbox": [0, 0, 1, 1]
                }],
                "char_start": 0,
                "char_end": len(text)
            }]
        }
    
    def get_page_text(self, file_path: str, page_num: int) -> Optional[str]:
        """Get text from a specific page."""
        try:
            with pdfplumber.open(file_path) as pdf:
                if 0 < page_num <= len(pdf.pages):
                    return pdf.pages[page_num - 1].extract_text()
        except Exception as e:
            logger.error(f"Failed to get page text: {e}")
        return None
