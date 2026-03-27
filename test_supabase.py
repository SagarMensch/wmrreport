import psycopg

# NEW Project (Singapore)
conninfo = "postgresql://postgres.uqboetjuyfxevzxnwors:PFil9KG4JhwvDtRn@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require"

try:
    print("Testing NEW Singapore Project (uqboetjuyfxevzxnwors) on 5432...")
    with psycopg.connect(conninfo, connect_timeout=15) as conn:
        print("✅ SUCCESS! Connected to the NEW Supabase project.")
        with conn.cursor() as cur:
            cur.execute("SELECT NOW();")
            print(f"Server Time: {cur.fetchone()}")
except Exception as e:
    print(f"❌ FAILED: {e}")
