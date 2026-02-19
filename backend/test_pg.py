import psycopg2

DATABASE_URL = "postgresql://postgres:ClauseDB2024SecurePassword@34.133.16.158:5432/clause_db"
PROJECT_ID = "cmh0pxnxm0005ofnlntnlpvku"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Check vault
cur.execute('''
    SELECT id, "projectId", name 
    FROM "Vault" 
    WHERE "projectId" = %s
''', (PROJECT_ID,))

print(f"Vaults:")
for row in cur.fetchall():
    print(f"  ID: {row[0]}")
    print(f"  ProjectID: {row[1]}")
    print(f"  Name: {row[2]}")
    VAULT_ID = row[0]

# Check documents for this vault
cur.execute('''
    SELECT id, name, status, "vaultId"
    FROM "Document" 
    WHERE "vaultId" = %s
    LIMIT 10
''', (VAULT_ID,))

print(f"\nDocuments (vaultId={VAULT_ID}):")
rows = cur.fetchall()
print(f"  Found {len(rows)} documents")
for row in rows:
    print(f"  {row[1]} | {row[2]}")

cur.close()
conn.close()

