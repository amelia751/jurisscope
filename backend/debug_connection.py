import psycopg2

# Try the exact same connection both ways
DATABASE_URL = "postgresql://postgres:ClauseDB2024SecurePassword@34.133.16.158:5432/clause_db"
VAULT_ID = "cmh0pxohy0007ofnlcpkkm96o"

print("="*80)
print("Testing PostgreSQL Connection")
print("="*80)

# Method 1: Direct psycopg2
print("\n--- Method 1: Direct psycopg2 ---")
conn1 = psycopg2.connect(DATABASE_URL)
cur1 = conn1.cursor()

print(f"Database: {conn1.get_dsn_parameters()['dbname']}")
print(f"Host: {conn1.get_dsn_parameters()['host']}")

cur1.execute("SELECT current_database(), current_schema()")
db, schema = cur1.fetchone()
print(f"Current database: {db}, schema: {schema}")

# Check vault
cur1.execute('SELECT id, "projectId" FROM "Vault" LIMIT 3')
print(f"\nVaults:")
for row in cur1.fetchall():
    print(f"  {row[0]} | {row[1]}")

# Check documents
cur1.execute('SELECT COUNT(*) FROM "Document"')
total_docs = cur1.fetchone()[0]
print(f"\nTotal documents in database: {total_docs}")

cur1.execute('SELECT COUNT(*) FROM "Document" WHERE "vaultId" = %s', (VAULT_ID,))
vault_docs = cur1.fetchone()[0]
print(f"Documents for vault {VAULT_ID}: {vault_docs}")

# Check case sensitivity
cur1.execute('SELECT id FROM "Vault"')
all_vault_ids = [row[0] for row in cur1.fetchall()]
print(f"\nAll vault IDs in database:")
for vid in all_vault_ids:
    print(f"  {vid}")
    if vid == VAULT_ID:
        print(f"    ^ MATCHES target ID")

cur1.close()
conn1.close()
print("\n" + "="*80)

