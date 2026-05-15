import { NextResponse } from "next/server";
import { Pool } from "pg";

const connectionString =
  "postgresql://neondb_owner:npg_NkUoV0R6IgDY@ep-lingering-dawn-apl8j3xh-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require";

const pool = new Pool({
  connectionString,
  ssl: { rejectUnauthorized: false },
});

async function initDB() {
  try {
    await pool.query(`
      CREATE EXTENSION IF NOT EXISTS vector;
      CREATE TABLE IF NOT EXISTS chat_conversations (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        response_type TEXT DEFAULT 'text',
        chart_data JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        embedding vector(384)
      );
      ALTER TABLE chat_conversations
        ADD COLUMN IF NOT EXISTS workspace_id TEXT;
      CREATE INDEX IF NOT EXISTS idx_conv_session ON chat_conversations(session_id);
      CREATE INDEX IF NOT EXISTS idx_conv_workspace ON chat_conversations(workspace_id);
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
    const sessionId = searchParams.get("session_id");
    const workspaceId = searchParams.get("workspace_id");

    if (!sessionId) {
      const workspaceFilter = workspaceId
        ? "WHERE COALESCE(c.workspace_id, c.session_id) = $1"
        : "";
      const params = workspaceId ? [workspaceId] : [];

      const sessionsResult = await pool.query(
        `
          SELECT
            c.session_id,
            MIN(CASE WHEN c.role = 'user' THEN c.content END) AS first_question,
            COUNT(*) AS message_count,
            MAX(c.created_at) AS last_active
          FROM chat_conversations c
          ${workspaceFilter}
          GROUP BY c.session_id
          HAVING COUNT(*) > 0
          ORDER BY MAX(c.created_at) DESC
          LIMIT 30
        `,
        params,
      );

      const sessions = sessionsResult.rows.map((row) => ({
        session_id: row.session_id,
        title: row.first_question
          ? row.first_question.length > 50
            ? `${row.first_question.substring(0, 50)}...`
            : row.first_question
          : "New Conversation",
        message_count: parseInt(row.message_count, 10),
        last_active: row.last_active,
      }));

      return NextResponse.json({ sessions });
    }

    const result = await pool.query(
      `SELECT role, content, response_type, chart_data AS "chartData", created_at
       FROM chat_conversations
       WHERE session_id = $1
       ORDER BY created_at ASC
       LIMIT 100`,
      [sessionId],
    );

    const history = result.rows.map((row) => ({
      id: Math.random().toString(36).substring(7),
      role: row.role,
      content: row.content,
      type: row.response_type,
      chartData: row.chartData || undefined,
      timestamp: row.created_at,
    }));

    return NextResponse.json({ history });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown history error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const { session_id, workspace_id, role, content, type, chartData } =
      await req.json();

    if (!session_id || !role || !content) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 },
      );
    }

    await pool.query(
      `INSERT INTO chat_conversations
        (session_id, workspace_id, role, content, response_type, chart_data)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [
        session_id,
        workspace_id || session_id,
        role,
        content,
        type || "text",
        chartData ? JSON.stringify(chartData) : null,
      ],
    );

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown history error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
