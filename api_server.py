"""
Bashira Intelligence — Advanced API Server
==========================================
FastAPI backend with endpoints for:
  1. /api/query — Full pipeline (question → SQL → results → chart)
  2. /api/drill-down — Interactive chart drill-down execution
  3. /api/knowledge-graph — Neo4j schema graph for visualization
  4. /api/health — System health check
  5. /api/schema — Database schema introspection

Designed for three frontend tabs:
  Tab 1: Chat (conversational query interface)
  Tab 2: Decision Studio (Bloomberg-level charts + drill-down)
  Tab 3: Knowledge Graph (Neo4j graph visualization)

Start with:  python api_server.py
Swagger docs: http://localhost:8000/docs
"""

import time
import logging
import datetime
import requests
from contextlib import asynccontextmanager
from typing import Optional, Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bashira.api")


# ── Lazy pipeline initialization ─────────────────────────────────────────
_orchestrator = None


def get_orchestrator():
    """Lazy-load the orchestrator (heavy initialization)."""
    global _orchestrator
    if _orchestrator is None:
        from orchestrator import PipelineOrchestrator
        _orchestrator = PipelineOrchestrator()
    return _orchestrator


# ── Pydantic Models ──────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class DrillDownRequest(BaseModel):
    sql_template: str
    clicked_value: str
    chart_type: Optional[str] = "data_table"


class DrillDownAction(BaseModel):
    level: int
    trigger_column: str
    label: str
    sql_template: str
    chart_type: str
    description: str


class ChartConfig(BaseModel):
    chart_type: str = "data_table"
    title: str = ""
    subtitle: str = ""
    x_axis: str = ""
    y_axis: str = ""
    x_label: str = ""
    y_label: str = ""
    series: list[str] = []
    group_by: str = ""
    color_scheme: str = "bloomberg_dark"
    show_values: bool = True
    show_legend: bool = True
    animate: bool = True
    gradient: bool = True
    glass_effect: bool = True
    drill_downs: list[DrillDownAction] = []
    kpi_value: str = ""
    kpi_unit: str = ""
    kpi_trend: str = ""
    reasoning: str = ""


class ReasoningStep(BaseModel):
    step: str
    status: str
    detail: str
    duration_ms: int = 0
    metadata: dict = {}


class QueryResponse(BaseModel):
    question: str
    sql_query: str = ""
    is_safe: bool = False

    # Chart
    chart_type: str = "data_table"
    chart_config: Optional[ChartConfig] = None

    # Data
    columns: list[str] = []
    rows: list[list[Any]] = []
    total_rows: int = 0
    truncated: bool = False

    # Drill-down actions
    drill_downs: list[DrillDownAction] = []

    # Quality
    confidence: float = 0.0
    reasoning: str = ""
    reasoning_steps: list[ReasoningStep] = []

    # Performance
    execution_time_ms: int = 0

    # Error
    error: Optional[str] = None

    # Schema (for knowledge graph)
    schema_context: str = ""
    retrieval_summary: str = ""


class HealthResponse(BaseModel):
    status: str
    neo4j: bool
    sql_server: bool
    bm25_index: bool
    bm25_documents: int = 0
    agents_loaded: bool
    timestamp: str


class KnowledgeGraphResponse(BaseModel):
    nodes: list[dict] = []
    edges: list[dict] = []
    stats: dict = {}
    error: Optional[str] = None


class SchemaTable(BaseModel):
    name: str
    columns: list[dict] = []


class SchemaResponse(BaseModel):
    tables: list[SchemaTable] = []
    total_tables: int = 0
    total_columns: int = 0


# ── FastAPI App ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize pipeline on startup."""
    log.info("🚀 Starting Bashira Intelligence API...")
    get_orchestrator()  # Trigger initialization
    log.info("✓ Pipeline ready")
    yield
    log.info("Shutting down...")


app = FastAPI(
    title="Bashira Intelligence API",
    description="Bloomberg-level conversational data intelligence platform. "
                "Three tabs: Chat, Decision Studio, Knowledge Graph.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Predictive Analytics Router
try:
    from predict_service import predict_router
    app.include_router(predict_router)
    log.info("✓ Predictive Analytics Sub-Router Mounted Successfully")
except Exception as e:
    log.error(f"Failed to mount predictive analytics module: {e}")



# ── Endpoints ────────────────────────────────────────────────────────────

@app.post("/api/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    """
    🧠 Full pipeline: Question → Intent → Retrieval → SQL → Execute → Chart
    
    Returns SQL results with Bloomberg-level chart configuration and
    drill-down actions for interactive data exploration.
    """
    orchestrator = get_orchestrator()

    try:
        session_id = req.session_id if req.session_id else "default_session"
        result = orchestrator.process(req.question, session_id=session_id)
    except Exception as e:
        log.exception("Pipeline error")
        raise HTTPException(status_code=500, detail=str(e))

    # Build chart config from dict
    chart_config = None
    if result.chart_config:
        try:
            # Extract drill_downs from chart_config for the nested model
            cc = result.chart_config.copy()
            dd_list = cc.pop("drill_downs", [])
            dd_models = [DrillDownAction(**d) for d in dd_list]
            chart_config = ChartConfig(**cc, drill_downs=dd_models)
        except Exception:
            chart_config = None

    # Build drill-down models
    drill_downs = []
    for d in result.drill_downs:
        try:
            drill_downs.append(DrillDownAction(**d))
        except Exception:
            pass

    # Build reasoning steps
    steps = []
    for s in result.reasoning_steps:
        try:
            steps.append(ReasoningStep(**s))
        except Exception:
            pass

    return QueryResponse(
        question=result.question,
        sql_query=result.sql_query,
        is_safe=result.is_safe,
        chart_type=result.chart_type,
        chart_config=chart_config,
        columns=result.columns,
        rows=result.rows,
        total_rows=result.total_rows,
        truncated=result.truncated,
        drill_downs=drill_downs,
        confidence=result.confidence,
        reasoning=result.reasoning,
        reasoning_steps=steps,
        execution_time_ms=result.execution_time_ms,
        error=result.error,
        schema_context=result.schema_context,
        retrieval_summary=result.retrieval_summary,
    )


@app.post("/api/drill-down", response_model=QueryResponse)
def drill_down_endpoint(req: DrillDownRequest):
    """
    🔍 Execute a drill-down query from chart interaction.
    
    When user clicks on a chart element (e.g., a bar in a cluster chart),
    the frontend sends the SQL template + clicked value to drill deeper.
    
    Example flow:
      1. "How many wells in each cluster?" → Bar chart
      2. User clicks "Nimr" bar → Drill to wells in Nimr
      3. User clicks "WELL_ABC" → Drill to full well detail
    """
    orchestrator = get_orchestrator()

    try:
        result = orchestrator.execute_drill_down(
            sql_template=req.sql_template,
            clicked_value=req.clicked_value,
            chart_type=req.chart_type or "data_table",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Build response (same format as query)
    chart_config = None
    if result.chart_config:
        try:
            cc = result.chart_config.copy()
            dd_list = cc.pop("drill_downs", [])
            dd_models = [DrillDownAction(**d) for d in dd_list]
            chart_config = ChartConfig(**cc, drill_downs=dd_models)
        except Exception:
            chart_config = None

    drill_downs = []
    for d in result.drill_downs:
        try:
            drill_downs.append(DrillDownAction(**d))
        except Exception:
            pass

    return QueryResponse(
        question=result.question,
        sql_query=result.sql_query,
        is_safe=result.is_safe,
        chart_type=result.chart_type,
        chart_config=chart_config,
        columns=result.columns,
        rows=result.rows,
        total_rows=result.total_rows,
        drill_downs=drill_downs,
        confidence=result.confidence,
        execution_time_ms=result.execution_time_ms,
        error=result.error,
    )


@app.get("/api/knowledge-graph", response_model=KnowledgeGraphResponse)
def knowledge_graph_endpoint(limit: int = 200):
    """
    🕸️ Fetch the schema knowledge graph for the Knowledge Graph tab.
    
    Returns nodes (Tables, Columns, Wells) and edges (HAS_COLUMN,
    JOINS_ON, REFERENCES_WELL, MIRRORS) for D3/vis.js rendering.
    """
    orchestrator = get_orchestrator()
    return orchestrator.get_knowledge_graph(limit=limit)


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """
    💚 System health check for all subsystems.
    """
    orchestrator = get_orchestrator()
    h = orchestrator.health()

    return HealthResponse(
        status="ok" if all([h["neo4j"], h["sql_server"], h["bm25_index"]]) else "degraded",
        neo4j=h["neo4j"],
        sql_server=h["sql_server"],
        bm25_index=h["bm25_index"],
        bm25_documents=h["bm25_documents"],
        agents_loaded=h["agents_loaded"],
        timestamp=datetime.datetime.now().isoformat(),
    )


@app.get("/api/schema", response_model=SchemaResponse)
async def schema_endpoint():
    """
    📋 Database schema introspection.
    
    Returns all tables and columns from INFORMATION_SCHEMA
    for the Decision Studio metadata panel.
    """
    from database.sql_client import sql_client

    try:
        result = sql_client.execute_query("""
            SELECT t.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, c.IS_NULLABLE
            FROM INFORMATION_SCHEMA.TABLES t
            JOIN INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME
            WHERE t.TABLE_TYPE = 'BASE TABLE'
            ORDER BY t.TABLE_NAME, c.ORDINAL_POSITION
        """, max_rows=5000)

        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        # Group by table
        tables_dict: dict[str, list[dict]] = {}
        for row in result["rows"]:
            table_name = row[0]
            if table_name not in tables_dict:
                tables_dict[table_name] = []
            tables_dict[table_name].append({
                "name": row[1],
                "type": row[2],
                "nullable": row[3] == "YES",
            })

        tables = [
            SchemaTable(name=name, columns=cols)
            for name, cols in tables_dict.items()
        ]

        return SchemaResponse(
            tables=tables,
            total_tables=len(tables),
            total_columns=sum(len(t.columns) for t in tables),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TTSRequest(BaseModel):
    text: str

@app.post("/api/voice/stt")
async def voice_stt(file: UploadFile = File(...)):
    """
    🎤 Speech-to-Text via Sarvam API.
    Receives an audio file (WAV) and returns text.
    """
    from config import settings
    if not settings.SARVAM_API_KEY:
        raise HTTPException(status_code=500, detail="SARVAM_API_KEY is not configured in .env.")
        
    url = "https://api.sarvam.ai/speech-to-text-translate"
    files = {"file": (file.filename, await file.read(), file.content_type or "audio/wav")}
    headers = {"api-subscription-key": settings.SARVAM_API_KEY}
    
    try:
        response = requests.post(url, headers=headers, files=files, data={"prompt": ""})
        if response.status_code != 200:
            log.error(f"Sarvam STT failed: {response.text}")
            raise HTTPException(status_code=500, detail="Sarvam API rejected the request.")
        return response.json()
    except Exception as e:
        log.error("Sarvam STT Error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice/tts")
async def voice_tts(req: TTSRequest):
    """
    🔊 Text-to-Speech via Sarvam API.
    Receives text, returns an audio file stream.
    """
    from config import settings
    import base64

    if not settings.SARVAM_API_KEY:
        log.warning("Sarvam TTS requested but no API key configured. Returning 204.")
        return Response(status_code=204)
        
    url = "https://api.sarvam.ai/text-to-speech"
    payload = {
        "inputs": [req.text],
        "target_language_code": "en-IN",
        "speaker": "amartya",
        "pitch": 0,
        "pace": 1.1,
        "loudness": 1.5,
        "speech_sample_rate": 8000,
        "enable_preprocessing": True,
        "model": "aurora-tts"
    }
    headers = {
        "api-subscription-key": settings.SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            log.error(f"Sarvam TTS failed: {response.text}")
            raise HTTPException(status_code=500, detail="Sarvam API rejected the request.")
            
        data = response.json()
        if "audios" in data and len(data["audios"]) > 0:
            audio_bytes = base64.b64decode(data["audios"][0])
            return Response(content=audio_bytes, media_type="audio/wav")
        else:
            raise HTTPException(status_code=500, detail="No audio returned from Sarvam.")
    except Exception as e:
        log.error("Sarvam TTS Error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print()
    print("=" * 60)
    print("  🧠 BASHIRA INTELLIGENCE — API Server v2.0")
    print("  📊 Bloomberg-level Decision Engine")
    print("=" * 60)
    print()
    print("  Endpoints:")
    print("    POST /api/query        — Ask any question")
    print("    POST /api/drill-down   — Drill into chart data")
    print("    GET  /api/knowledge-graph — Neo4j graph data")
    print("    GET  /api/schema       — Database schema")
    print("    GET  /api/health       — System health")
    print()
    print("  Swagger: http://localhost:8000/docs")
    print("=" * 60)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
