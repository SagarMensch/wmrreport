import psycopg

uri = "postgresql://neondb_owner:npg_NkUoV0R6IgDY@ep-lingering-dawn-apl8j3xh-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require"
try:
    with psycopg.connect(uri, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            print("CONNECTION SUCCESS:", cur.fetchone()[0])
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            tables = [r[0] for r in cur.fetchall()]
            if tables:
                print(f"Public tables: {tables}")
            else:
                print("Public tables: (none - fresh database)")
    print("Neon DB is HEALTHY")
except Exception as e:
    print(f"CONNECTION FAILED: {e}")
