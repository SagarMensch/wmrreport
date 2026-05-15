import psycopg

conninfo = "postgresql://neondb_owner:npg_NkUoV0R6IgDY@ep-lingering-dawn-apl8j3xh-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require"

def test_persistence():
    print("Testing Neon Persistence (LangGraph Checkpointer Simulation)...")
    try:
        with psycopg.connect(conninfo, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                # Check if tables exist
                cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                tables = [r[0] for r in cur.fetchall()]
                print(f"Detected tables: {tables}")
                
                if "chat_conversations" in tables:
                    print("OK: chat_conversations table detected.")
                if "workspace_memory" in tables:
                    print("OK: workspace_memory table detected.")
                    
    except Exception as e:
        print(f"Persistence test failed: {e}")

if __name__ == "__main__":
    test_persistence()
