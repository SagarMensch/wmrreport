import psycopg
import logging

# Configuration
NEON_URI = "postgresql://neondb_owner:npg_NkUoV0R6IgDY@ep-lingering-dawn-apl8j3xh-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require"

def init_neon_db():
    print("Connecting to Neon DB to initialize schemas...")
    try:
        with psycopg.connect(NEON_URI, connect_timeout=15) as conn:
            with conn.cursor() as cur:
                # 1. Enable pgvector
                print("[1/3] Enabling pgvector extension...")
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # 2. Create chat_conversations (from web/src/app/api/history/route.ts)
                print("[2/3] Creating chat_conversations table...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.chat_conversations (
                        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        workspace_id TEXT,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        response_type TEXT DEFAULT 'text',
                        chart_data JSONB,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        embedding vector(384)
                    );
                    CREATE INDEX IF NOT EXISTS idx_conv_session ON chat_conversations(session_id);
                    CREATE INDEX IF NOT EXISTS idx_conv_workspace ON chat_conversations(workspace_id);
                    CREATE INDEX IF NOT EXISTS idx_conv_created ON chat_conversations(created_at);
                """)
                
                # 3. Create workspace_memory (from orchestrator.py)
                print("[3/3] Creating workspace_memory table...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.workspace_memory (
                        id BIGSERIAL PRIMARY KEY,
                        workspace_id TEXT NOT NULL,
                        memory_type TEXT NOT NULL,
                        memory_key TEXT NOT NULL,
                        memory_value TEXT NOT NULL,
                        source_session_id TEXT,
                        confidence DOUBLE PRECISION DEFAULT 0.5,
                        metadata JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        UNIQUE(workspace_id, memory_type, memory_key)
                    );
                    CREATE INDEX IF NOT EXISTS idx_workspace_memory_scope
                        ON public.workspace_memory(workspace_id, memory_type, updated_at DESC);
                """)
                
            conn.commit()
            print("\nSUCCESS: Neon DB initialized with all application tables.")
            
    except Exception as e:
        print(f"\nFATAL: Initialization failed: {e}")

if __name__ == "__main__":
    init_neon_db()
