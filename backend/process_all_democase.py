#!/usr/bin/env python3
"""
Process all demo-case documents through the complete pipeline
"""
import os
import sys
import uuid
import time
from pathlib import Path
from typing import List
from PyPDF2 import PdfReader, PdfWriter

sys.path.insert(0, os.path.dirname(__file__))

from services.gcs import GCSService
from services.firestore import FirestoreService
from services.document_ai import DocumentAIService
from services.vertex_ai import VertexAIService
from services.elasticsearch import ElasticsearchService
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = "cmh0pxnxm0005ofnlntnlpvku"
DEMO_CASE_PATH = "/Users/anhlam/Downloads/demo-case"

def split_pdf(pdf_path: str, max_pages: int = 10) -> List[str]:
    """Split PDF into chunks"""
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    if total_pages <= max_pages:
        return [pdf_path]
    
    logger.info(f"  Splitting {total_pages} pages into {max_pages}-page chunks...")
    chunks = []
    temp_dir = Path("/tmp/pdf_chunks")
    temp_dir.mkdir(exist_ok=True)
    
    for i in range(0, total_pages, max_pages):
        writer = PdfWriter()
        end_page = min(i + max_pages, total_pages)
        
        for page_num in range(i, end_page):
            writer.add_page(reader.pages[page_num])
        
        chunk_path = temp_dir / f"{Path(pdf_path).stem}_chunk_{i//max_pages}.pdf"
        with open(chunk_path, 'wb') as f:
            writer.write(f)
        
        chunks.append(str(chunk_path))
    
    return chunks

def process_file(file_path: Path, relative_path: str, services: dict) -> dict:
    """Process a single file through the pipeline"""
    gcs_service = services['gcs']
    firestore_service = services['firestore']
    docai_service = services['docai']
    vertex_service = services['vertex']
    es_service = services['es']
    
    file_name = file_path.name
    doc_title = file_path.stem
    is_pdf = file_path.suffix.lower() == '.pdf'
    
    logger.info(f"\n{'='*80}")
    logger.info(f"📄 {file_name} ({relative_path})")
    
    try:
        # Create Firestore ID
        firestore_doc_id = str(uuid.uuid4())
        
        # Upload to GCS
        gcs_path = f"{PROJECT_ID}/{relative_path}/{file_name}"
        gcs_uri = f"gs://{gcs_service.bucket_raw_name}/{gcs_path}"
        gcs_service.upload_file(str(file_path), gcs_path)
        logger.info(f"  ✅ Uploaded to GCS")
        
        # Create Firestore document
        firestore_service.create_document(
            doc_id=firestore_doc_id,
            data={
                "project_id": PROJECT_ID,
                "title": doc_title,
                "gcs_uri": gcs_uri,
                "mime": "application/pdf" if is_pdf else "text/plain",
                "status": "processing",
                "es_index": "clause-documents",
                "num_pages": 1
            }
        )
        logger.info(f"  ✅ Firestore: {firestore_doc_id}")
        
        # Process based on type
        es_doc_ids = []
        
        if not is_pdf:
            # Text file
            with open(file_path, 'r') as f:
                text = f.read()[:4000]  # Limit to 4000 chars
            
            embedding = vertex_service.generate_query_embedding(text)
            
            es_doc = {
                'doc_id': firestore_doc_id,
                'doc_title': doc_title,
                'project_id': PROJECT_ID,
                'text': text,
                'tokens': len(text.split()),
                'page': 1,
                'char_start': 0,
                'char_end': len(text),
                'section_path': relative_path,
                'bbox_list': [],
                'vector': embedding
            }
            
            es_doc_id = f"{firestore_doc_id}_chunk_0"
            es_service.index_document(es_doc_id, es_doc)
            es_doc_ids.append(es_doc_id)
            logger.info(f"  ✅ Indexed text (1 chunk)")
            
        else:
            # PDF file
            logger.info(f"  📄 Processing PDF with Document AI...")
            pdf_chunks = split_pdf(str(file_path), max_pages=10)
            
            for chunk_idx, chunk_path in enumerate(pdf_chunks):
                # Upload chunk if split
                if len(pdf_chunks) > 1:
                    chunk_gcs_path = f"{PROJECT_ID}/chunks/{firestore_doc_id}_chunk_{chunk_idx}.pdf"
                    chunk_gcs_uri = f"gs://{gcs_service.bucket_raw_name}/{chunk_gcs_path}"
                    gcs_service.upload_file(chunk_path, chunk_gcs_path)
                else:
                    chunk_gcs_uri = gcs_uri
                
                # Process with Document AI
                try:
                    document = docai_service.process_document(chunk_gcs_uri, "application/pdf")
                    full_text = document.text
                    
                    # Split into 1000-char chunks with 200-char overlap
                    chunk_size = 1000
                    overlap = 200
                    
                    for i in range(0, len(full_text), chunk_size - overlap):
                        text_chunk = full_text[i:i + chunk_size]
                        if len(text_chunk) < 50:
                            continue
                        
                        embedding = vertex_service.generate_query_embedding(text_chunk)
                        
                        es_doc = {
                            'doc_id': firestore_doc_id,
                            'doc_title': doc_title,
                            'project_id': PROJECT_ID,
                            'text': text_chunk,
                            'tokens': len(text_chunk.split()),
                            'page': chunk_idx + 1,
                            'char_start': i,
                            'char_end': i + len(text_chunk),
                            'section_path': relative_path,
                            'bbox_list': [{'x1': 0.1, 'y1': 0.1, 'x2': 0.9, 'y2': 0.9}],
                            'vector': embedding
                        }
                        
                        es_doc_id = f"{firestore_doc_id}_chunk_{chunk_idx}_{i}"
                        es_service.index_document(es_doc_id, es_doc)
                        es_doc_ids.append(es_doc_id)
                    
                    logger.info(f"    Chunk {chunk_idx + 1}: {len(range(0, len(full_text), chunk_size - overlap))} text chunks indexed")
                    
                except Exception as e:
                    logger.warning(f"    Document AI failed for chunk {chunk_idx}: {e}")
                    continue
            
            logger.info(f"  ✅ Indexed PDF ({len(es_doc_ids)} total chunks)")
        
        # Update Firestore status
        firestore_service.update_document(firestore_doc_id, {"status": "indexed"})
        
        logger.info(f"  ✅ COMPLETED")
        return {
            'success': True,
            'firestore_id': firestore_doc_id,
            'es_doc_ids': es_doc_ids,
            'file': file_name
        }
        
    except Exception as e:
        logger.error(f"  ❌ FAILED: {e}")
        return {
            'success': False,
            'error': str(e),
            'file': file_name
        }

def main():
    logger.info("="*80)
    logger.info("🚀 Processing All Demo-Case Documents")
    logger.info("="*80)
    
    # Initialize services
    logger.info("\n📦 Initializing services...")
    services = {
        'gcs': GCSService(),
        'firestore': FirestoreService(),
        'docai': DocumentAIService(),
        'vertex': VertexAIService(),
        'es': ElasticsearchService()
    }
    logger.info("✅ All services initialized")
    
    # Scan demo-case directory
    demo_path = Path(DEMO_CASE_PATH)
    files_to_process = []
    
    for root, dirs, files in os.walk(demo_path):
        for file in files:
            if file.startswith('.') or file == '.DS_Store':
                continue
            file_path = Path(root) / file
            relative_path = str(file_path.parent.relative_to(demo_path))
            files_to_process.append((file_path, relative_path))
    
    logger.info(f"\n📋 Found {len(files_to_process)} files to process\n")
    
    # Process each file
    results = []
    for idx, (file_path, relative_path) in enumerate(files_to_process, 1):
        logger.info(f"\n[{idx}/{len(files_to_process)}]")
        result = process_file(file_path, relative_path, services)
        results.append(result)
        time.sleep(1)  # Rate limiting
    
    # Summary
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    logger.info(f"\n{'='*80}")
    logger.info("📊 PROCESSING SUMMARY")
    logger.info("="*80)
    logger.info(f"✅ Successful: {len(successful)}")
    logger.info(f"❌ Failed: {len(failed)}")
    logger.info(f"📊 Total: {len(results)}")
    
    if failed:
        logger.info(f"\n❌ Failed files:")
        for r in failed:
            logger.info(f"  - {r['file']}: {r['error']}")
    
    logger.info("="*80)
    
    # Save results
    import json
    with open('/tmp/processing_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    logger.info("\n💾 Results saved to /tmp/processing_results.json")

if __name__ == "__main__":
    main()

