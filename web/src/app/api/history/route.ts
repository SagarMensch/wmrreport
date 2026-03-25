import { NextResponse } from 'next/server';
import { Pool } from 'pg';

const connectionString = 'postgresql://postgres.uqboetjuyfxevzxnwors:PFil9KG4JhwvDtRn@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres';

const pool = new Pool({
  connectionString,
  ssl: { rejectUnauthorized: false }
});

// Initialize table if not exists
async function initDB() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS chat_history (
      id SERIAL PRIMARY KEY,
      question TEXT NOT NULL,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
  `);
}

initDB().catch(console.error);

export async function GET() {
  try {
    const result = await pool.query('SELECT question FROM chat_history ORDER BY created_at DESC LIMIT 50');
    const history = result.rows.map(row => row.question);
    return NextResponse.json({ history });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const { question } = await req.json();
    if (!question) return NextResponse.json({ error: 'Missing question' }, { status: 400 });
    
    await pool.query('INSERT INTO chat_history (question) VALUES ($1)', [question]);
    return NextResponse.json({ success: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
