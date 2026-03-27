import { NextResponse } from 'next/server';
import { Pool } from 'pg';

const connectionString = 'postgresql://postgres.uqboetjuyfxevzxnwors:PFil9KG4JhwvDtRn@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres';

const pool = new Pool({
  connectionString,
  ssl: { rejectUnauthorized: false }
});

// Initialize advanced chat tables for Supabase
async function initDB() {
  try {
    await pool.query(`
      CREATE EXTENSION IF NOT EXISTS vector;
      CREATE TABLE IF NOT EXISTS chat_conversations (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,           -- 'user' or 'assistant'
        content TEXT NOT NULL,        -- message text
        response_type TEXT DEFAULT 'text',  -- 'text', 'chart', 'clarification'
        chart_data JSONB,            -- {columns, rows, sql_query, chart_type} if applicable
        created_at TIMESTAMPTZ DEFAULT NOW(),
        embedding vector(384)        -- pgvector for semantic long-term memory
      );
      CREATE INDEX IF NOT EXISTS idx_conv_session ON chat_conversations(session_id);
      CREATE INDEX IF NOT EXISTS idx_conv_created ON chat_conversations(created_at);
    `);
    console.log("Supabase vector schemas checked/created successfully.");
  } catch (err) {
    console.error("Supabase vector init failed:", err);
  }
}

initDB();

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const session_id = searchParams.get('session_id');
    
    // If no session_id → return list of all past sessions (ChatGPT sidebar)
    if (!session_id) {
      const sessionsResult = await pool.query(`
        SELECT 
          c.session_id,
          MIN(CASE WHEN c.role = 'user' THEN c.content END) as first_question,
          COUNT(*) as message_count,
          MAX(c.created_at) as last_active
        FROM chat_conversations c
        GROUP BY c.session_id
        HAVING COUNT(*) > 0
        ORDER BY MAX(c.created_at) DESC
        LIMIT 30
      `);
      
      const sessions = sessionsResult.rows.map(row => ({
        session_id: row.session_id,
        title: row.first_question 
          ? (row.first_question.length > 50 ? row.first_question.substring(0, 50) + '...' : row.first_question)
          : 'New Conversation',
        message_count: parseInt(row.message_count),
        last_active: row.last_active
      }));
      
      return NextResponse.json({ sessions });
    }

    const result = await pool.query(
      'SELECT role, content, response_type, chart_data as "chartData", created_at FROM chat_conversations WHERE session_id = $1 ORDER BY created_at ASC LIMIT 100',
      [session_id]
    );
    
    // Map to frontend expected shape
    const history = result.rows.map(row => ({
      id: Math.random().toString(36).substring(7),
      role: row.role,
      content: row.content,
      type: row.response_type,
      chartData: row.chartData || undefined,
      timestamp: row.created_at
    }));
    
    return NextResponse.json({ history });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const { session_id, role, content, type, chartData } = await req.json();
    
    if (!session_id || !role || !content) {
       return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }
    
    await pool.query(
      'INSERT INTO chat_conversations (session_id, role, content, response_type, chart_data) VALUES ($1, $2, $3, $4, $5)',
      [session_id, role, content, type || 'text', chartData ? JSON.stringify(chartData) : null]
    );
    return NextResponse.json({ success: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
