#!/usr/bin/env python3
"""
Sync document statuses from Firestore to PostgreSQL
Updates PostgreSQL with firestoreDocId and status='completed'
"""
import psycopg2
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from services.firestore import FirestoreService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:ClauseDB2024SecurePassword@34.133.16.158:5432/clause_db"
PROJECT_ID = "cmh0pxnxm0005ofnlntnlpvku"
VAULT_ID = "cmh0pxohy0007ofnlcpkkm96o"

def main():
    logger.info("="*80)
    logger.info("🔄 Syncing Firestore → PostgreSQL Status")
    logger.info("="*80)
    
    # Initialize Firestore
    firestore_service = FirestoreService()
    
    # Get all documents from Firestore for this project
    logger.info(f"\n📋 Fetching Firestore documents for project: {PROJECT_ID}")
    docs_ref = firestore_service.db.collection('documents').where('project_id', '==', PROJECT_ID)
    firestore_docs = docs_ref.stream()
    
    # Connect to PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Get PostgreSQL documents
    cur.execute('SELECT id, name, "originalName", "firestoreDocId", status FROM "Document" WHERE "vaultId" = %s', (VAULT_ID,))
    pg_docs = {row[2]: {'id': row[0], 'name': row[1], 'firestore_id': row[3], 'status': row[4]} for row in cur.fetchall()}
    
    logger.info(f"📊 Found {len(pg_docs)} documents in PostgreSQL")
    
    # Match and update
    updated_count = 0
    for doc in firestore_docs:
        doc_data = doc.to_dict()
        doc_id = doc.id
        doc_title = doc_data.get('title', '')
        doc_status = doc_data.get('status', 'unknown')
        
        # Try to match by title (filename without extension)
        matched = False
        for original_name, pg_doc in pg_docs.items():
            name_without_ext = original_name.rsplit('.', 1)[0]
            if name_without_ext == doc_title or original_name == doc_title:
                # Update PostgreSQL
                cur.execute(
                    'UPDATE "Document" SET "firestoreDocId" = %s, status = %s, "processedAt" = NOW() WHERE id = %s',
                    (doc_id, doc_status, pg_doc['id'])
                )
                logger.info(f"✅ Updated: {original_name} → {doc_id} (status: {doc_status})")
                updated_count += 1
                matched = True
                break
        
        if not matched:
            logger.warning(f"⚠️  No match for Firestore doc: {doc_title}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ Synced {updated_count} documents")
    logger.info(f"{'='*80}")

if __name__ == "__main__":
    main()

