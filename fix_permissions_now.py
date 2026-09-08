"""Quick script to grant database permissions"""
import psycopg2
import sys

# Database connection details
DB_HOST = "/cloudsql/mis-gempundit:asia-south2:flask-crm-db"  # For Cloud SQL Unix socket
DB_NAME = "crm_db"
DB_USER = "postgres"
DB_PASSWORD = "ZkeLqfEnC7uamXQr"

print("Connecting to database...")
print(f"Database: {DB_NAME}")
print(f"User: {DB_USER}")
print()

try:
    # Try Unix socket connection first (for Cloud Run/Cloud Shell)
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print("✓ Connected via Unix socket")
    except:
        # Fallback to TCP connection (for local with Cloud SQL Proxy)
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print("✓ Connected via TCP")

    conn.autocommit = True
    cursor = conn.cursor()

    target_user = "content-username"
    print(f"\nGranting permissions to user: {target_user}")
    print("-" * 60)

    # Grant all privileges on existing tables
    print("\n1. Granting privileges on all tables...")
    cursor.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{target_user}";')
    print("   ✓ Done")

    # Grant all privileges on existing sequences
    print("\n2. Granting privileges on all sequences...")
    cursor.execute(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{target_user}";')
    print("   ✓ Done")

    # Grant schema usage
    print("\n3. Granting schema usage...")
    cursor.execute(f'GRANT USAGE ON SCHEMA public TO "{target_user}";')
    print("   ✓ Done")

    # Set default privileges for future tables
    print("\n4. Setting default privileges for future tables...")
    cursor.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "{target_user}";')
    print("   ✓ Done")

    # Set default privileges for future sequences
    print("\n5. Setting default privileges for future sequences...")
    cursor.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "{target_user}";')
    print("   ✓ Done")

    # Verify tables
    print("\n6. Verifying tables...")
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()
    print(f"   Found {len(tables)} tables:")
    for table in tables:
        print(f"     - {table[0]}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✓ ALL PERMISSIONS GRANTED SUCCESSFULLY!")
    print("=" * 60)

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
