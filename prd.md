ATNM Intelligence Platform — Product Requirements Document (PRD)
Version: 2.0
Date: 20 March 2026
Author: Sagar (Tech Lead — On-Site at Client)
Classification: CONFIDENTIAL — Internal Team Only
Sprint: 4-Day Delivery (20–23 Mar 2026)
Table of Contents

1. Executive Summary
2. ff SECURITY — Section 1 (Read This First)
3. Architecture Overview
4. Project Structure & Folder Layout
5. Backend Specification (Python FastAPI)
6. Frontend Specification (Next.js)
7. Data Inventory & Schema
8. Neo4j Knowledge Graph Specification
9. DSPy Pipeline Specification
10. Chart Intelligence Specification
11. REST API Contract
12. Team Assignments & Working Model
13. Day-by-Day Execution Plan
14. Risk Register
15. Acceptance Criteria
16. Executive Summary
What We Are Building
An autonomous data intelligence platform for ATNM’s oil & gas operations. A production-grade product with: - Next.js frontend — glassmorphism
dark UI, animated Recharts/D3.js visualizations, real-time streaming - Python
FastAPI backend — DSPy agentic pipeline, Neo4j knowledge graph, MiniLM
embeddings - SQL Server 2022 — native vector storage, read-only access, all
data stays on-premise
Tech Stack
1
Layer Technology Why
Frontend Next.js 15 (App Router)

+ TypeScript
Production React
framework, SSR, API
routes
UI Library Tailwind CSS + Framer
Motion
Glassmorphism dark
theme + smooth
animations
Charts Recharts + D3.js React-native charts,
animated transitions
Backend Python 3.11 + FastAPI Async, fast, auto-docs
(Swagger), WebSocket
support
Agent DSPy
(BootstrapFewShot +
ReAct)
Self-optimizing prompts,
multi-step reasoning
Knowledge Graph Neo4j Aura (schema
only)
Table→Column→Join→Rule
relationships
Embeddings all-MiniLM-L6-v2 (local,
80MB)
5x faster than BERT,
runs offline
Vector Storage SQL Server 2022
VARBINARY(MAX)
Native, zero external
vector DB
Database SQL Server 2022
(ATNM_Dev)
Read-only via
atnm_chatbot user
LLM Azure OpenAI gpt-4o Best text-to-SQL
accuracy
Communication REST (JSON) +
WebSocket (streaming)
FrontendffBackend
Delivery Timeline
Day Date Deliverable
Day 1 Thu 20 Mar SQL done ff + Neo4j
graph + KB
embeddings + FastAPI
skeleton + Next.js
scaffold
Day 2 Fri 21 Mar DSPy pipeline +
agentic reasoner +
REST API endpoints +
25 questions validated
2
Day Date Deliverable
Day 3 Sat 22 Mar Next.js Glass UI +
chart engine +
WebSocket streaming +
100 questions E2E
Day 4 Sun 23 Mar Polish + integration
test + deploy + demo

2. fi SECURITY — Section 1 (Read This First)
[!CAUTION] EVERY TEAM MEMBER MUST READ
THIS SECTION BEFORE WRITING A SINGLE LINE
OF CODE.
We are on a client’s production server. One wrong query can
wipe live data.
2.1 The Golden Rules

# Rule

Consequence of
Violation
1 NEVER connect as
SA/admin in
application code
Instant access to
DROP/DELETE on
production
2 ALWAYS use
atnm_chatbot
credentials in all
backend code
This user has
SELECT-only access
3 NEVER use
AppMasterDB
directly
Use ATNM_Dev — it’s
the isolated dev copy
4 NEVER hardcode
credentials in source
code
Use .env files, excluded
from git
5 NEVER send actual
data rows to Neo4j
Aura (cloud)
Only schema metadata
goes to Neo4j
6 NEVER send actual
data rows to any
LLM API
Only send: question +
schema context.
NEVER query results
3

# Rule

Consequence of
Violation
7 ALL generated SQL
must be read-only
Reject any SQL with
INSERT, UPDATE,
DELETE, DROP,
ALTER, TRUNCATE,
EXEC
8 ALL generated SQL
validated before
execution
Server-side
validate_sql() — no
bypass
9 Log every generated
SQL query
Audit trail for client
10 VPN required for all
database access
No exceptions
11 Frontend NEVER
connects to SQL
Server directly
All DB access goes
through FastAPI only
12 CORS restricted to
known origins
Only localhost:3000
(dev) and internal IP
(prod)
2.2 Credentials & Access
Application Database Credentials (BACKEND .env ONLY)
SQL_SERVER=""
SQL_DATABASE=""
SQL_USER=""
SQL_PASSWORD=""
SQL_DRIVER=""
Permission Matrix (Verified fi — 20 Mar 2026)
Operation
atnm_chatbot on
ATNM_Dev Status
SELECT (all tables) ff ALLOWED Verified
INSERT
(schema_knowledge_base
only)
ff ALLOWED KB population only
UPDATE
(schema_knowledge_base
only)
ff ALLOWED KB updates only
INSERT (any other
table)
ff BLOCKED Verified
4
Operation
atnm_chatbot on
ATNM_Dev Status
UPDATE (any other
table)
ff BLOCKED Verified
DELETE (any table) ff BLOCKED Verified
CREATE TABLE ff BLOCKED Verified
DROP TABLE ff BLOCKED Verified
SA Credentials (SAGAR ONLY — NEVER IN CODE)
• SA access held by Sagar only (on-site)
• Used ONLY for: DB admin, creating users, granting permissions
• Never committed to git, never in Slack/Teams, never in config
2.3 Environment Files
Backend .env (Python — /backend/.env)

# NEVER commit this file

SQL_SERVER=10.100.137.11
SQL_DATABASE=ATNM_Dev
SQL_USER=atnm_chatbot
SQL_PASSWORD=Chatbot_ReadOnly_2026!
SQL_DRIVER=ODBC Driver 18 for SQL Server
NEO4J_URI=neo4j+s://<instance>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<to-be-generated>
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_KEY=<to-be-provided>
AZURE_OPENAI_MODEL=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview
CORS_ORIGINS=<http://localhost:3000,http://10.100.137.11:3000>
Frontend .env.local (Next.js — /frontend/.env.local)

# NEVER commit this file

NEXT_PUBLIC_API_URL=<http://localhost:8000>

# In production: NEXT_PUBLIC_API_URL=<http://10.100.137.11:8000>

[!IMPORTANT] Frontend has NO database credentials. It
only knows the FastAPI URL. All DB/Neo4j/LLM access is serverside in Python.
5
2.4 SQL Injection Prevention — Mandatory Pattern
FORBIDDEN_KEYWORDS = [
'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE',
'EXEC', 'EXECUTE', 'CREATE', 'GRANT', 'REVOKE', 'DENY',
'MERGE', 'BULK', 'OPENROWSET', 'xp_', 'sp_', '--', ';'
]
def validate_sql(sql: str) -> bool:
sql_upper = sql.upper().strip()
if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
return False
for keyword in FORBIDDEN_KEYWORDS:
if keyword.upper() in sql_upper:
return False
return True
2.5 Data Flow Architecture

CLIENT NETWORK (10.100.137.x)
  HTTP/WS
  Next.js  FastAPI Backend
  Frontend  JSON only  (Python 3.11)
  :3000  NO SQL  :8000
   NO creds  
  Renders:
  • Charts    DSPy Agent  
  • Chat UI    SQL Validator  
  • Tables    MiniLM (local 80MB)  

 SELECT only

  SQL Server 2022
  ATNM_Dev  
  (10.100.137.11)
  
 OUTBOUND   SCHEMA ONLY
 (metadata)   NO DATA ROWS

6
 Neo4j Aura   Azure OpenAI
 (schema   (question +
 structure   schema context
 only)   only)

2.6 Security Checklist (Before Every PR)
□ No credentials in any source file (.py, .ts, .tsx, .json)
□ .env and .env.local in .gitignore
□ All SQL goes through validate_sql() before execution
□ LLM prompt contains NO actual data values
□ Neo4j queries contain NO actual data values
□ All database connections use atnm_chatbot user
□ CORS restricted to known origins only
□ Frontend has NO database/LLM credentials
□ Query audit log is active
3. Architecture Overview
System Architecture

NEXT.JS FRONTEND

 Chat Page Chart Comp Data Table Reasoning Panel

 REST + WebSocket

FASTAPI BACKEND

  API Router Layer
  POST /api/query · WS /api/stream · GET /api/history

  Layer 6: AGENTIC REASONER (DSPy ReAct)
  Multi-step · Self-healing · Confidence scoring

  Layer 5: QUERY EXPLAINABILITY
  Reasoning chain · Graph path · Audit log

  Layer 4: NEO4J KNOWLEDGE GRAPH
  Schema → Columns → Joins → Rules → Q&A

  Layer 3: DSPy COMPILER
7
  BootstrapFewShot · ChainOfThought text-to-SQL

  Layer 2: HYBRID RETRIEVAL
  MiniLM (local) + Graph traversal + SQL vectors

  Layer 1: SQL SERVER 2022
  ATNM_Dev · atnm_chatbot · schema_knowledge_base

Request Flow (End-to-End)
sequenceDiagram
participant U as User (Browser)
participant F as Next.js (:3000)
participant B as FastAPI (:8000)
participant N as Neo4j (schema)
participant M as MiniLM (local)
participant L as Azure OpenAI
participant D as SQL Server 2022
U->>F: Types question in chat
F->>B: POST /api/query {question}
B->>M: Embed question (local, 10ms)
M-->>B: 384-dim vector
B->>N: Graph traversal (schema only)
N-->>B: Tables, columns, joins, Q&As
B->>L: Prompt (question + schema context)
Note over L: NO DATA — only schema
L-->>B: Generated SQL
B->>B: validate_sql()
B->>D: Execute SELECT (read-only)
D-->>B: Result rows (on-premise)
B->>B: Auto-select chart type
B-->>F: JSON {data, chart_type, sql, reasoning, confidence}
F->>F: Render chart + table + reasoning
F-->>U: Glassmorphism response card
4. Project Structure & Folder Layout
atnm-intelligence/
 frontend/ # Next.js 15 App
  .env.local # NEXT_PUBLIC_API_URL only (gitignored)
  package.json
  tailwind.config.ts
8
  next.config.ts
  tsconfig.json
  public/
   logo.svg
   favicon.ico
  src/
 app/
  layout.tsx # Root layout — fonts, dark theme
  page.tsx # Main chat page
  globals.css # Glassmorphism tokens + animations
  api/ # Next.js API routes (proxy if needed)
 components/
  chat/
   ChatInput.tsx # Glass input + send button
   ChatMessage.tsx # User/agent message bubbles
   ChatHistory.tsx # Scrollable conversation
  charts/
   ChartRenderer.tsx # Dynamic chart component
   BarChart.tsx
   LineChart.tsx
   ScatterChart.tsx
   DonutChart.tsx
   HeatmapChart.tsx
   GanttChart.tsx
   TreemapChart.tsx
  ui/
   GlassCard.tsx # Reusable glass panel
   GlassButton.tsx
   ConfidenceBadge.tsx
   LoadingSpinner.tsx
   StreamingText.tsx # Token-by-token text render
  data/
   DataTable.tsx # Sortable/filterable table
   ExportButtons.tsx # CSV + Excel download
  reasoning/
 ReasoningPanel.tsx # Collapsible reasoning steps
 SQLViewer.tsx # Syntax-highlighted SQL
 hooks/
  useQuery.ts # API call hook
  useWebSocket.ts # WebSocket streaming hook
  useQueryHistory.ts # Local storage for history
 lib/
  api.ts # FastAPI client functions
  types.ts # TypeScript interfaces
 styles/
 glassmorphism.css # Glass theme variables
9
 backend/ # Python FastAPI
  .env # All secrets (gitignored)
  requirements.txt
  main.py # FastAPI app entry point
  config.py # Environment config loader
  routers/
   query.py # POST /api/query
   stream.py # WS /api/stream
   history.py # GET /api/history
   health.py # GET /api/health
  agent/
   pipeline.py # ATNMAgent (DSPy Module)
   compiler.py # DSPy compilation script
   signatures.py # DSPy signatures
   react_agent.py # ReAct multi-step agent
  retrieval/
   neo4j_client.py # Neo4j graph queries
   embedder.py # MiniLM embedding
   vector_search.py # NumPy cosine similarity
   hybrid_retriever.py # Graph + dense combined
  database/
   connection.py # SQL Server connection pool
   executor.py # execute_safe_sql()
   validator.py # validate_sql()
  knowledge/
   graph_builder.py # Populate Neo4j from DDLs
   kb_loader.py # Load 100 Q&As into KB
   schema_reader.py # Read DDLs from SQL Server
  models/
   schemas.py # Pydantic request/response models
   chart_selector.py # Auto chart type selection
  middleware/
   security.py # CORS + SQL validation middleware
   logging.py # Query audit logging
  tests/
 test_validator.py # SQL validation tests
 test_permissions.py # DB permission tests
 test_pipeline.py # E2E pipeline tests
 scripts/
  setup_neo4j.py # One-time Neo4j graph population
  embed_knowledge_base.py # One-time KB embedding
  compile_dspy.py # One-time DSPy compilation
  test_readonly_permissions.py # Permission verification
10
 docs/
  ATNM_PRD_v2.md # This document
  API_REFERENCE.md # Full API docs
  DEPLOY_GUIDE.md # Deployment instructions
 .gitignore
 docker-compose.yml # (optional) For containerized deploy
 README.md
5. Backend Specification (Python FastAPI)
5.1 FastAPI App Entry Point

# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import query, stream, history, health
from config import settings
app = FastAPI(
title="ATNM Intelligence API",
version="1.0.0",
docs_url="/docs", # Swagger UI at /docs
redoc_url="/redoc", # ReDoc at /redoc
)
app.add_middleware(
CORSMiddleware,
allow_origins=settings.CORS_ORIGINS.split(","),
allow_credentials=True,
allow_methods=["GET", "POST"], # No PUT/DELETE
allow_headers=["*"],
)
app.include_router(query.router, prefix="/api")
app.include_router(stream.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(health.router, prefix="/api")
5.2 Core Dependencies

# backend/requirements.txt

fastapi==0.115.0
uvicorn[standard]==0.32.0
pyodbc==5.3.0
11
pandas==2.2.0
numpy==1.26.0
python-dotenv==1.0.0
pydantic==2.9.0
dspy-ai==2.5.0
sentence-transformers==3.3.0
neo4j==5.26.0
websockets==13.0
openpyxl==3.1.0 # For Excel export
5.3 Request/Response Models

# backend/models/schemas.py

from pydantic import BaseModel
from typing import List, Optional, Any
class QueryRequest(BaseModel):
question: str
session_id: Optional[str] = None
class ReasoningStep(BaseModel):
step: int
action: str # "CLASSIFY", "RETRIEVE", "GENERATE", "VALIDATE", "EXECUTE", "SELF_HEALdetail: str
duration_ms: int
class ChartData(BaseModel):
chart_type: str # "bar", "line", "scatter", etc.
data: List[dict] # Serialized DataFrame rows
x_column: Optional[str]
y_column: Optional[str]
title: str
class QueryResponse(BaseModel):
answer: str # Natural language answer
sql_query: str # Generated SQL (display-only)
chart: Optional[ChartData]
table_data: List[dict] # Raw rows for DataTable
columns: List[str]
reasoning: List[ReasoningStep]
confidence: float # 0.0 to 1.0
execution_time_ms: int
question_type: str # "single_table", "multi_table", "cross_report"
tables_used: List[str]
class HealthResponse(BaseModel):
12
status: str
sql_server: bool
neo4j: bool
embedder: bool
version: str
5.4 Key Endpoints
Method Path Description Auth
POST /api/query Main query
endpoint —
returns data +
chart +
reasoning
—
WS /api/stream WebSocket for
streaming
responses
—
GET /api/history?session_id=X Get query history
for session
—
GET /api/health Health check —
DB, Neo4j,
embedder status
—
GET /api/export/{query_id}?format=csv Export query
results
—
GET /docs Swagger UI
(auto-generated)
—
6. Frontend Specification (Next.js)
6.1 Technology Choices
Technology Version Purpose
Next.js 15 (App Router) Framework — SSR, routing, TypeScript
TypeScript 5.x Type safety across all components
Tailwind CSS 4.x Utility classes + glassmorphism custom theme
Framer Motion 11.x Smooth animations, page transitions
Recharts 2.x React-native charts (bar, line, scatter, pie)
D3.js 7.x Advanced charts (Gantt, heatmap, treemap)
Lucide React latest Premium icon set
React Syntax Highlighter latest SQL syntax highlighting
13
6.2 Design System — Glassmorphism Dark
Color Tokens (Tailwind)
/*frontend/src/app/globals.css*/
:root {
--bg-primary: #0A0A1E;
--bg-glass: rgba(255, 255, 255, 0.04);
--bg-glass-hover: rgba(255, 255, 255, 0.08);
--border-glass: rgba(255, 255, 255, 0.08);
--text-primary: #E8E8FF;
--text-secondary: #8888AA;
--accent-cyan: #00D4FF;
--accent-purple: #7B61FF;
--accent-green: #00E676;
--accent-red: #FF4757;
--accent-amber: #FFD93D;
--glass-blur: 20px;
--transition: 400ms cubic-bezier(0.4, 0, 0.2, 1);
}
Glass Card Component Pattern
// GlassCard — reusable across all panels
<div className="
bg-white/[0.04]
backdrop-blur-xl
border border-white/[0.08]
rounded-2xl
shadow-2xl
shadow-black/20
transition-all duration-400
hover:bg-white/[0.08]
hover:border-white/[0.12]
hover:shadow-cyan-500/5
">
6.3 Page Layout

  ATNM  Data Intelligence  •••
  Logo  Platform  Menu
  
14
  Query   MAIN CHAT AREA
  History

  • Q1...    User: "Show me wells..."  
  • Q2...
  • Q3...

     Agent Response:  
       
       ANIMATED CHART   
      (auto-selected)   
       
     Answer text...  
         
      SQL   Table   CSV   
         
      Reasoning   
     Confidence: 94%   
     
    
     
      Ask a question... []  
     
  
6.4 Key Component Specs
Component File Description
ChatInput chat/ChatInput.tsx Glass input, keyboard
shortcut (Enter),
loading state with pulse
animation
ChatMessage chat/ChatMessage.tsx Distinct user/agent
styling, animated mount
with Framer Motion
ChartRenderer charts/ChartRenderer.tsxReceives chart_type +
data → renders correct
chart
DataTable data/DataTable.tsx Sort by clicking headers,
column filtering,
alternating row opacity
ReasoningPanel reasoning/ReasoningPanel.tsx Accordion with
step-by-step agent trace,
timing info
15
Component File Description
SQLViewer reasoning/SQLViewer.tsxSyntax-highlighted SQL
with copy-to-clipboard
ConfidenceBadge ui/ConfidenceBadge.tsx Green (>80%), amber
(50-80%), red (<50%)
ExportButtons data/ExportButtons.tsx Download CSV/Excel,
calls /api/export/
GlassCard ui/GlassCard.tsx Reusable glassmorphism
container
6.5 TypeScript Interfaces (Shared Types)
// frontend/src/lib/types.ts
interface QueryRequest {
question: string;
session_id?: string;
}
interface ReasoningStep {
step: number;
action: 'CLASSIFY' | 'RETRIEVE' | 'GENERATE' | 'VALIDATE' | 'EXECUTE' | 'SELF_HEAL';
detail: string;
duration_ms: number;
}
interface ChartData {
chart_type: 'bar' | 'line' | 'scatter' | 'donut' | 'heatmap' |
'gantt' | 'treemap' | 'histogram' | 'grouped_bar' | 'table_only';
data: Record<string, any>[];
x_column?: string;
y_column?: string;
title: string;
}
interface QueryResponse {
answer: string;
sql_query: string;
chart?: ChartData;
table_data: Record<string, any>[];
columns: string[];
reasoning: ReasoningStep[];
confidence: number;
execution_time_ms: number;
question_type: string;
tables_used: string[];
16
}
7. Data Inventory & Schema
7.1 Database Details
Property Value
Server 10.100.137.11 (SAPROUTER)
SQL Server Version 2022 (native vector support)
Production DB AppMasterDB (DO NOT TOUCH)
Development DB ATNM_Dev (our workspace)
Application User atnm_chatbot (SELECT-only)
7.2 Core Tables
Table Purpose Rows Key Columns
WellMonitoringReport Weekly well
progress
~260 well_name,
overall_progress,
report_date,
area
Job_Progress_Report_GB Plan vs actual ~5K well_name,
plan_pct,
actual_pct,
week_number
Revenue Revenue by
activity
~3K well_name,
activity,
amount, period
PH_PRODUCTIVITY_WEEKLY_REPORT Crew
productivity
~2K rig_name, crew,
productive_hours,
week
WMR_Full Historical
monitoring
~18K Full history
schema_knowledge_base Vector KB (our
table)
~141 chunk_text,
embedding,
chunk_type
8. Neo4j Knowledge Graph Specification
[!WARNING] ZERO actual data rows go into Neo4j. Only
structural metadata (table names, column names, joins, rules).
17
Node Types
Label Properties Count
Table name, purpose, row_count ~12
Column name, type, business_meaning, is_key ~80
Rule text, category ~20
Question text, sql_template, chart_type, category 100
Relationship Types
Relationship From → To Properties
HAS_COLUMN Table → Column —
JOINS_WITH Table → Table on, type (INNER/LEFT)
GOVERNED_BY Column → Rule —
USES_TABLE Question → Table —
USES_COLUMN Question → Column —
SIMILAR_TO Question → Question score
9. DSPy Pipeline Specification
Core Module
class ATNMAgent(dspy.Module):

# Steps: classify → retrieve → generate_sql → validate → execute → (self_heal)

# Output: sql, chart_type, reasoning, confidence

Compilation
Parameter Value
Compiler BootstrapFewShotWithRandomSearch
Training data 100 Q&A pairs
Metric SQL execution accuracy
Max demos 4
Candidates 16
10. Chart Intelligence Specification
Auto-Selection Matrix
18
Question Pattern Chart Type Library
“Average X by Y” Horizontal bar Recharts <BarChart>
“X over time” / “trend” Line with gradient Recharts <AreaChart>
“Compare A vs B” Grouped bar Recharts <BarChart>
“Distribution of X” Histogram D3.js custom
“Top/Bottom N” Ranked bar Recharts <BarChart>
“X vs Y correlation” Scatter + regression Recharts
<ScatterChart>
“Schedule by well” Gantt D3.js custom
“% breakdown” Donut Recharts <PieChart>
“Multi-dimension” Heatmap D3.js custom
“By area/region” Treemap Recharts <Treemap>
Chart Styling (All Charts)
const CHART_THEME = {
background: "transparent",
fontFamily: "Inter",
textColor: "#E0E0FF",
gridColor: "rgba(255,255,255,0.05)",
colors: ["#00D4FF", "#7B61FF", "#00E676", "#FFD93D", "#FF4757"],
animationDuration: 800,
animationEasing: "ease-in-out",
};
11. REST API Contract
POST /api/query
Request: { question: string, session_id?: string }
Response: QueryResponse (see Section 6.5)
Example:
POST /api/query
{
"question": "What is the average progress for Nimr wells?",
"session_id": "abc123"
}
Response 200:
{
"answer": "The average overall progress for Nimr wells is 78.3%",
"sql_query": "SELECT AVG(overall_progress) as avg_progress FROM WellMonitoringReport WHERE"chart": {
19
"chart_type": "bar",
"data": [{"area": "Nimr", "avg_progress": 78.3}],
"x_column": "area",
"y_column": "avg_progress",
"title": "Average Progress by Area"
},
"table_data": [{"area": "Nimr", "avg_progress": 78.3}],
"columns": ["area", "avg_progress"],
"reasoning": [
{"step": 1, "action": "CLASSIFY", "detail": "Single-table aggregation", "duration_ms": 5{"step": 2, "action": "RETRIEVE", "detail": "Found WellMonitoringReport via graph", "dur{"step": 3, "action": "GENERATE", "detail": "Generated SELECT AVG query", "duration_ms"{"step": 4, "action": "VALIDATE", "detail": "SQL validated —
SELECT only", "duration_ms": 1},
{"step": 5, "action": "EXECUTE", "detail": "1 row returned", "duration_ms": 180}
],
"confidence": 0.95,
"execution_time_ms": 2451,
"question_type": "single_table",
"tables_used": ["WellMonitoringReport"]
}
WS /api/stream
// WebSocket for streaming responses (token-by-token)
Connect: ws://localhost:8000/api/stream
Send: { "question": "...", "session_id": "..." }
Receive (multiple messages):
{ "type": "thinking", "content": "Classifying question..." }
{ "type": "thinking", "content": "Retrieving schema context..." }
{ "type": "sql", "content": "SELECT AVG(overall..." }
{ "type": "executing", "content": "Running query..." }
{ "type": "result", "content": <full QueryResponse> }
GET /api/health
Response 200:
{
"status": "healthy",
"sql_server": true,
"neo4j": true,
"embedder": true,
"version": "1.0.0"
}
20
GET /api/export/{query_id}?format=csv|xlsx
Response: File download (CSV or Excel)
12. Team Assignments & Working Model
Team Structure
Role Person Location Responsibility
Tech Lead Sagar On-site (client) Architecture,
SQL admin,
security,
deployment,
client demos
Backend Dev TBD Remote FastAPI, DSPy
pipeline, Neo4j,
retrieval engine
Frontend Dev TBD Remote Next.js UI,
charts, Framer
Motion
animations, data
tables
ML Engineer TBD Remote MiniLM
embeddings, KB
population,
DSPy
compilation
Working Model
Rule Detail
VPN Mandatory for all DB access
Git Private repo, PRs only — no direct push to main
Code review All code touching SQL/Neo4j/LLM reviewed by Sagar
Deployment Sagar only deploys to SAPROUTER
Standups 10 AM IST (async) + 6 PM IST (call)
Frontend credentials NONE — frontend only knows FastAPI URL
13. Day-by-Day Execution Plan
Day 1 — Thu 20 Mar (Foundation)
21
Task Owner Status
SQL Server setup
(ATNM_Dev,
permissions,
schema_knowledge_base)
Sagar ff Done
Git repo + .gitignore +
folder structure
Sagar
npx create-next-app
with Tailwind +
TypeScript
Frontend Dev
FastAPI skeleton
(main.py, routers,
config)
Backend Dev
Neo4j Aura instance +
graph population script
Backend Dev
MiniLM embedding
pipeline + KB loader
ML Engineer
Day 2 — Fri 21 Mar (Core Pipeline + API)
Task Owner Status
DSPy ATNMAgent module Backend Dev
POST /api/query endpoint (full pipeline) Backend Dev
validate_sql() + execute_safe_sql() Backend Dev
Self-healing loop (error → fix → retry) Backend Dev
Chat page layout + glass theme Frontend Dev
ChatInput + ChatMessage components Frontend Dev
Test Q1–Q25 via API Sagar + Backend
Day 3 — Sat 22 Mar (UI + Charts + E2E)
Task Owner Status
ChartRenderer + all 10 chart types Frontend Dev
DataTable with sort/filter Frontend Dev
ReasoningPanel + SQLViewer Frontend Dev
WS /api/stream WebSocket streaming Backend Dev
Frontend WebSocket integration Frontend Dev
Export endpoints (CSV/Excel) Backend Dev
Test all 100 questions E2E All
Day 4 — Sun 23 Mar (Polish + Deploy)
22
Task Owner Status
Conversation memory (multi-turn) Backend Dev
Framer Motion animations polish Frontend Dev
Performance: cache embeddings + frequent queries ML Engineer
Security audit (permissions, creds, CORS) Sagar
next build + FastAPI production config Sagar
Deploy on SAPROUTER (internal IP) Sagar
3-minute demo video for client Sagar
14. Risk Register
Risk Impact Prob. Mitigation
LLM generates
harmful SQL
CRITICAL Low validate_sql()

+ atnm_chatbot
read-only (double
protection)
Data leak to
cloud
CRITICAL Low Schema-only to
Neo4j/LLM.
Results stay
on-premise.
Frontend has no
DB creds
VPN issues for
remote team
High Medium Sagar on-site as
fallback. Mock
data for frontend
dev without VPN
Next.js/FastAPI
integration issues
Medium Medium Well-defined API
contract (Section
11). Frontend/backend
work
independently
DSPy
compilation fails
Medium Low Fallback: manual
few-shot prompts
4-day timeline
too tight
High Medium P0 features first:
10 flawless
questions > 100
mediocre
23

15. Acceptance Criteria
P0 — Must Ship
□ Full Next.js frontend with glassmorphism dark theme
□ FastAPI backend with /api/query endpoint
□ 30/100 questions → correct SQL → correct data → correct chart
□ ALL SQL validated (SELECT-only) before execution
□ Zero client data sent to any external service
□ Charts render with premium styling (not default themes)
□ Deployed on client internal IP
P1 — Should Ship
□ 70/100 questions work
□ WebSocket streaming (token-by-token)
□ 7+ chart types with auto-selection
□ Reasoning panel with confidence scores
□ Data export (CSV/Excel)
□ Query history sidebar
P2 — Nice to Have
□ 100/100 questions
□ Framer Motion page transitions
□ Multi-turn conversation memory
□ Anomaly detection in results
□ Mobile responsive layout
[!IMPORTANT] TEAM: Read Section 2 (Security) FIRST.
Set up your .env. Then start coding. Security violations =
immediate code review escalation. When in doubt, DON’T
execute — ASK Sagar.
PRD v2.0 — Next.js + FastAPI Architecture. This is a living document. Updates via Git PRs.
24
