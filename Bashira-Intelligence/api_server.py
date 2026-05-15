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
Swagger docs: http://localhost:8005/docs
"""

import time
import logging
import datetime
import threading
import base64
import re
from io import BytesIO
import requests

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    from gtts import gTTS
except ImportError:
    gTTS = None
from contextlib import asynccontextmanager
from typing import Optional, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from causal_command_service import CausalCommandService
from command_center_service import CommandCenterService
from data_integrity_service import DataIntegrityService

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bashira.api")


# ── Lazy pipeline initialization ─────────────────────────────────────────
_orchestrator = None
_causal_command_service = None
_data_integrity_service = None
_command_center_service = None
_forecast_engine = None

_orchestrator_lock = threading.Lock()
_causal_command_lock = threading.Lock()
_data_integrity_lock = threading.Lock()
_command_center_lock = threading.Lock()
_forecast_engine_lock = threading.Lock()


def get_orchestrator():
    """Lazy-load the orchestrator (heavy initialization)."""
    global _orchestrator
    if _orchestrator is None:
        with _orchestrator_lock:
            if _orchestrator is None:
                from orchestrator import PipelineOrchestrator
                _orchestrator = PipelineOrchestrator()
    return _orchestrator


def get_causal_command_service():
    global _causal_command_service
    if _causal_command_service is None:
        with _causal_command_lock:
            if _causal_command_service is None:
                _causal_command_service = CausalCommandService()
    return _causal_command_service


def get_data_integrity_service():
    global _data_integrity_service
    if _data_integrity_service is None:
        with _data_integrity_lock:
            if _data_integrity_service is None:
                _data_integrity_service = DataIntegrityService()
    return _data_integrity_service


def get_command_center_service():
    global _command_center_service
    if _command_center_service is None:
        with _command_center_lock:
            if _command_center_service is None:
                _command_center_service = CommandCenterService(
                    forecast_engine_getter=get_forecast_engine,
                    data_integrity_getter=get_data_integrity_service,
                )
    return _command_center_service


def _warm_causal_command_workspace() -> None:
    try:
        get_causal_command_service().build_workspace()
        log.info("✓ Causal Command workspace warmed")
    except Exception:
        log.exception("Causal Command warm-up failed")


def _warm_forecast_workspace() -> None:
    try:
        engine = get_forecast_engine()
        engine.get_well_list()
        engine.get_portfolio_summary()
        log.info("✓ Forecast workspace warmed")
    except Exception:
        log.exception("Forecast workspace warm-up failed")


def _warm_data_integrity_workspace() -> None:
    try:
        get_data_integrity_service().build_workspace(force_refresh=True)
        log.info("✓ Data Integrity workspace warmed")
    except Exception:
        log.exception("Data Integrity warm-up failed")


def _warm_command_center_views() -> None:
    try:
        service = get_command_center_service()
        service.get_portfolio_view()
        service.get_smart_alerts_view()
        service.get_rig_operations_view()
        log.info("✓ Command Center views warmed")
    except Exception:
        log.exception("Command Center warm-up failed")


# ── Pydantic Models ──────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    workspace_id: Optional[str] = None
    chat_history: Optional[list[dict]] = None


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
    response_type: str = "chart"  # text, chart, clarification
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

    # Decision OS (additive)
    response_mode: str = "sql_only"       # sql_only | predictive
    answer_text: str = ""                 # clean public answer for predictive mode
    risk_label: str = ""                  # ON_TRACK | WATCH | AT_RISK | CRITICAL
    predictive_context: dict = {}         # forecast, risk, causal, interventions
    predictive_summary: dict = {}         # structured scan results for frontend card


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
    threading.Thread(target=_warm_causal_command_workspace, daemon=True).start()
    threading.Thread(target=_warm_forecast_workspace, daemon=True).start()
    threading.Thread(target=_warm_data_integrity_workspace, daemon=True).start()
    threading.Thread(target=_warm_command_center_views, daemon=True).start()
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

def get_forecast_engine():
    global _forecast_engine
    if _forecast_engine is None:
        with _forecast_engine_lock:
            if _forecast_engine is None:
                from forecast_engine import ForecastEngine
                _forecast_engine = ForecastEngine()
                log.info("✓ Forecast Engine loaded (Predictive Studio)")
    return _forecast_engine

@app.get("/api/forecast/wells")
def forecast_well_list():
    """List all wells with summary for the Predictive Studio selector."""
    engine = get_forecast_engine()
    wells = engine.get_well_list()
    portfolio = engine.get_portfolio_summary()
    return {"status": "success", "wells": wells, "portfolio": portfolio}

@app.get("/api/forecast/well/{well_id}")
def forecast_well_detail(well_id: str):
    """Deep-dive for a single well: history, Gantt, milestones, forecast, risk."""
    engine = get_forecast_engine()
    detail = engine.get_well_detail(well_id)
    if not detail.get("current_state"):
        raise HTTPException(status_code=404, detail=f"Well '{well_id}' not found")
    return {"status": "success", "data": detail}

@app.get("/api/forecast/portfolio")
def forecast_portfolio():
    """Portfolio-level summary for the Predictive Studio dashboard."""
    engine = get_forecast_engine()
    return {"status": "success", "data": engine.get_portfolio_summary()}


@app.get("/api/command-center/portfolio")
def command_center_portfolio():
    """Executive project portfolio landing view."""
    service = get_command_center_service()
    return {"status": "success", "data": service.get_portfolio_view()}


@app.get("/api/command-center/alerts")
def command_center_alerts():
    """Merged smart alerts hub across schedule, risk, and data integrity."""
    service = get_command_center_service()
    return {"status": "success", "data": service.get_smart_alerts_view()}


@app.get("/api/command-center/rig-operations")
def command_center_rig_operations():
    """Rig control tower view with rig-level summaries and well-level delay status."""
    service = get_command_center_service()
    return {"status": "success", "data": service.get_rig_operations_view()}


@app.get("/api/command-center/location-prep")
def command_center_location_prep():
    """Location readiness and prep progression view."""
    service = get_command_center_service()
    return {"status": "success", "data": service.get_location_prep_view()}


@app.get("/api/command-center/delay-heatmap")
def command_center_delay_heatmap():
    """Weekly delivery variance heatmap derived from job progress snapshots."""
    service = get_command_center_service()
    return {"status": "success", "data": service.get_delay_heatmap_view()}


@app.get("/api/command-center/field-atlas")
def command_center_field_atlas():
    """Spatial field atlas built from live well coordinate coverage."""
    service = get_command_center_service()
    return {"status": "success", "data": service.get_field_atlas_view()}


@app.get("/api/command-center/engineering-timeline")
def command_center_engineering_timeline():
    """Engineering milestone timeline and readiness tracking."""
    service = get_command_center_service()
    return {"status": "success", "data": service.get_engineering_timeline_view()}


@app.get("/api/command-center/watchlist")
def command_center_watchlist():
    """Priority watchlist recommendations for execution teams."""
    service = get_command_center_service()
    return {"status": "success", "data": service.get_watchlist_view()}


@app.get("/api/command-center/data-dictionary")
def command_center_data_dictionary():
    """Client-facing data dictionary and schema governance view."""
    service = get_command_center_service()
    return {"status": "success", "data": service.get_data_dictionary_view()}


@app.get("/api/forecast/well/{well_id}/ensemble")
def forecast_well_ensemble(well_id: str):
    """
    Ensemble prediction for a single well.
    Stacks LightGBM + AutoARIMA + Stan Bayesian + S-Learner CATE
    with conformal prediction intervals.
    """
    engine = get_forecast_engine()
    detail = engine.get_well_detail(well_id)
    ensemble = detail.get("ensemble_prediction", {})
    if not ensemble or ensemble.get("error"):
        raise HTTPException(status_code=404, detail=f"Ensemble unavailable for well '{well_id}'")
    return {"status": "success", "data": ensemble}


@app.get("/api/model/diagnostics")
def model_diagnostics():
    """
    Report Stan MCMC diagnostics, ensemble weights, and conformal coverage.
    Production model health endpoint.
    """
    diagnostics = {}

    # Stan diagnostics
    try:
        from causal_stan_service import StanCounterfactualService
        stan = StanCounterfactualService()
        diagnostics["stan"] = stan.get_diagnostics()
    except Exception as e:
        diagnostics["stan"] = {"error": str(e)}

    # Ensemble status
    try:
        from ensemble_stacker import get_ensemble_stacker
        stacker = get_ensemble_stacker()
        diagnostics["ensemble"] = stacker.get_status()
    except Exception as e:
        diagnostics["ensemble"] = {"error": str(e)}

    # CPU ML Orchestrator health
    try:
        ml_resp = requests.get("http://127.0.0.1:8050/api/health", timeout=1.5)
        diagnostics["cpu_ml_orchestrator"] = ml_resp.json() if ml_resp.status_code == 200 else {"status": "unreachable"}
    except Exception:
        diagnostics["cpu_ml_orchestrator"] = {"status": "unreachable"}

    return {"status": "success", "diagnostics": diagnostics}


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
        result = orchestrator.process(
            req.question,
            session_id=session_id,
            workspace_id=req.workspace_id or session_id,
            chat_history=req.chat_history or [],
        )
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
        response_type=getattr(result, "response_type", "chart"),
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
        # Decision OS (additive)
        response_mode=getattr(result, "response_mode", "sql_only"),
        answer_text=getattr(result, "answer_text", ""),
        risk_label=getattr(result, "risk_label", ""),
        predictive_context=getattr(result, "predictive_context", {}),
        predictive_summary=getattr(result, "predictive_summary", {}),
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


@app.get("/api/causal/command")
def causal_command_endpoint():
    """
    Real causal-command workspace payload.
    Python assembles the live cross-system feature matrix, serves the fast CPU
    decision layer, and merges cached Bayesian counterfactual summaries.
    """
    try:
        service = get_causal_command_service()
        return service.build_workspace()
    except Exception as e:
        log.exception("Causal Command error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data-integrity")
def data_integrity_endpoint():
    """Live data-integrity workspace for Task Daily and Activity Task Plan."""
    try:
        service = get_data_integrity_service()
        return service.build_workspace()
    except Exception as e:
        log.exception("Data Integrity error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data-integrity/rule-view")
def data_integrity_rule_view_endpoint(
    rule_id: str,
    page: int = 1,
    page_size: int = 60,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    format: str = "json",
):
    """Paged SSMS-style evidence view for one integrity rule."""
    try:
        service = get_data_integrity_service()
        if format.lower() == "csv":
            csv_text = service.export_rule_view_csv(
                rule_id=rule_id,
                date_from=date_from,
                date_to=date_to,
            )
            filename = f"{rule_id.lower().replace('-', '')}_violations.csv"
            return Response(
                content=csv_text,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename=\"{filename}\"'
                },
            )
        return service.fetch_rule_view(
            rule_id=rule_id,
            page=page,
            page_size=page_size,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as e:
        log.exception("Data Integrity rule view error")
        raise HTTPException(status_code=500, detail=str(e))

class TTSRequest(BaseModel):
    text: str
    language: str = "en"


class VoiceReplyRequest(BaseModel):
    text: str
    language: str = "en"


VOICE_LANGUAGE_ALIASES = {
    "english": "en",
    "en": "en",
    "en-in": "en",
    "en-us": "en",
    "arabic": "ar",
    "ar": "ar",
    "ar-sa": "ar",
    "hindi": "hi",
    "hi": "hi",
    "hi-in": "hi",
}

VOICE_BROWSER_LANG = {
    "en": "en-US",
    "ar": "ar-SA",
    "hi": "hi-IN",
}

SARVAM_TTS_LANGUAGE = {
    "en": "en-IN",
    "hi": "hi-IN",
}

EDGE_TTS_VOICES = {
    "en": "en-US-AriaNeural",
    "ar": "ar-SA-ZariyahNeural",
    "hi": "hi-IN-SwaraNeural",
}

GTTS_LANGUAGE = {
    "en": "en",
    "ar": "ar",
    "hi": "hi",
}


def _normalize_voice_language(language: str | None) -> str:
    normalized = (language or "en").strip().lower()
    return VOICE_LANGUAGE_ALIASES.get(normalized, "en")


def _clean_voice_text(text: str) -> str:
    cleaned = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"#+\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _prepare_voice_reply_text(text: str) -> str:
    cleaned = _clean_voice_text(text)
    if not cleaned:
        return "Analysis complete."

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    chosen: list[str] = []
    total = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        projected = total + len(sentence) + (1 if chosen else 0)
        if projected > 320 and chosen:
            break
        chosen.append(sentence)
        total = projected
        if len(chosen) >= 2:
            break

    summary = " ".join(chosen).strip() or cleaned[:320].strip()
    return summary[:340]


def _groq_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def _translate_text_with_groq(text: str, target_language: str) -> str:
    from config import settings

    normalized_target = _normalize_voice_language(target_language)
    if normalized_target == "en":
        target_name = "English"
    elif normalized_target == "ar":
        target_name = "Arabic"
    else:
        target_name = "Hindi"

    if not settings.GROQ_API_KEY:
        return text

    payload = {
        "model": settings.GROQ_MODEL,
        "temperature": 0.1,
        "max_tokens": 300,
        "messages": [
            {
                "role": "system",
                "content": f"Translate the user text into {target_name}. Return only the translated text with no explanation.",
            },
            {"role": "user", "content": text},
        ],
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={**_groq_headers(settings.GROQ_API_KEY), "Content-Type": "application/json"},
        json=payload,
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    translated = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    return translated or text


def _transcribe_with_groq(audio_bytes: bytes, filename: str, content_type: str, preferred_language: str) -> tuple[str, str]:
    from config import settings

    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    normalized_language = _normalize_voice_language(preferred_language)
    files = {
        "file": (filename or "voice.webm", audio_bytes, content_type or "audio/webm"),
    }
    data = {
        "model": "whisper-large-v3-turbo",
        "response_format": "verbose_json",
        "temperature": "0",
    }
    if normalized_language in {"en", "ar", "hi"}:
        data["language"] = normalized_language

    response = requests.post(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        headers=_groq_headers(settings.GROQ_API_KEY),
        files=files,
        data=data,
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    transcript = (payload.get("text") or payload.get("transcript") or "").strip()
    detected_language = _normalize_voice_language(payload.get("language") or preferred_language)
    return transcript, detected_language


def _transcribe_with_sarvam(audio_bytes: bytes, filename: str, content_type: str) -> tuple[str, str]:
    from config import settings

    if not settings.SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not configured")

    response = requests.post(
        "https://api.sarvam.ai/speech-to-text-translate",
        headers={"api-subscription-key": settings.SARVAM_API_KEY},
        files={"file": (filename or "voice.wav", audio_bytes, content_type or "audio/wav")},
        data={"prompt": ""},
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    transcript = (payload.get("transcript") or payload.get("text") or "").strip()
    return transcript, "hi"


def _transcribe_voice(audio_bytes: bytes, filename: str, content_type: str, preferred_language: str) -> tuple[str, str]:
    groq_error = None
    try:
        return _transcribe_with_groq(audio_bytes, filename, content_type, preferred_language)
    except Exception as exc:
        groq_error = exc
        log.warning("Groq STT failed, falling back where possible: %s", exc)

    try:
        return _transcribe_with_sarvam(audio_bytes, filename, content_type)
    except Exception as sarvam_exc:
        if groq_error:
            raise RuntimeError(f"Groq STT failed: {groq_error}; Sarvam STT failed: {sarvam_exc}")
        raise RuntimeError(f"Sarvam STT failed: {sarvam_exc}")


def _synthesize_with_sarvam(text: str, language: str) -> bytes:
    from config import settings

    normalized_language = _normalize_voice_language(language)
    target_language_code = SARVAM_TTS_LANGUAGE.get(normalized_language)
    if not settings.SARVAM_API_KEY or not target_language_code:
        raise RuntimeError("Sarvam TTS unavailable for this language")

    payload = {
        "inputs": [text],
        "target_language_code": target_language_code,
        "speaker": "amartya",
        "pitch": 0,
        "pace": 1.05,
        "loudness": 1.4,
        "speech_sample_rate": 8000,
        "enable_preprocessing": True,
        "model": "aurora-tts",
    }

    response = requests.post(
        "https://api.sarvam.ai/text-to-speech",
        headers={
            "api-subscription-key": settings.SARVAM_API_KEY,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    audios = payload.get("audios") or []
    if not audios:
        raise RuntimeError("No audio returned from Sarvam")
    return base64.b64decode(audios[0])


async def _synthesize_with_edge_tts(text: str, language: str) -> tuple[bytes, str]:
    normalized_language = _normalize_voice_language(language)
    voice = EDGE_TTS_VOICES.get(normalized_language)
    if edge_tts is None or not voice:
        raise RuntimeError("Edge TTS unavailable for this language")

    communicate = edge_tts.Communicate(text, voice=voice)
    audio_bytes = bytearray()
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            audio_bytes.extend(chunk.get("data", b""))

    if not audio_bytes:
        raise RuntimeError("No audio returned from Edge TTS")

    return bytes(audio_bytes), "audio/mpeg"


def _synthesize_with_gtts(text: str, language: str) -> tuple[bytes, str]:
    normalized_language = _normalize_voice_language(language)
    gtts_language = GTTS_LANGUAGE.get(normalized_language)
    if gTTS is None or not gtts_language:
        raise RuntimeError("gTTS unavailable for this language")

    buffer = BytesIO()
    tts = gTTS(text=text, lang=gtts_language)
    tts.write_to_fp(buffer)
    audio_bytes = buffer.getvalue()
    if not audio_bytes:
        raise RuntimeError("No audio returned from gTTS")
    return audio_bytes, "audio/mpeg"


async def _build_voice_reply_payload(text: str, language: str) -> dict[str, Any]:
    normalized_language = _normalize_voice_language(language)
    spoken_text = _prepare_voice_reply_text(text)

    if normalized_language != "en":
        try:
            spoken_text = _translate_text_with_groq(spoken_text, normalized_language)
        except Exception as exc:
            log.warning("Voice translation failed, using original English text: %s", exc)

    errors: list[str] = []

    if normalized_language in SARVAM_TTS_LANGUAGE:
        try:
            audio_bytes = _synthesize_with_sarvam(spoken_text, normalized_language)
            return {
                "playback_mode": "audio",
                "spoken_text": spoken_text,
                "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
                "audio_mime_type": "audio/wav",
                "browser_lang": VOICE_BROWSER_LANG[normalized_language],
                "language": normalized_language,
                "provider": "sarvam",
            }
        except Exception as exc:
            errors.append(f"Sarvam: {exc}")

    if normalized_language == "ar":
        try:
            audio_bytes, audio_mime_type = _synthesize_with_gtts(spoken_text, normalized_language)
            return {
                "playback_mode": "audio",
                "spoken_text": spoken_text,
                "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
                "audio_mime_type": audio_mime_type,
                "browser_lang": VOICE_BROWSER_LANG[normalized_language],
                "language": normalized_language,
                "provider": "gtts",
            }
        except Exception as exc:
            errors.append(f"gTTS: {exc}")

    try:
        audio_bytes, audio_mime_type = await _synthesize_with_edge_tts(spoken_text, normalized_language)
        return {
            "playback_mode": "audio",
            "spoken_text": spoken_text,
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "audio_mime_type": audio_mime_type,
            "browser_lang": VOICE_BROWSER_LANG[normalized_language],
            "language": normalized_language,
            "provider": "edge-tts",
        }
    except Exception as exc:
        errors.append(f"EdgeTTS: {exc}")

    try:
        audio_bytes, audio_mime_type = _synthesize_with_gtts(spoken_text, normalized_language)
        return {
            "playback_mode": "audio",
            "spoken_text": spoken_text,
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "audio_mime_type": audio_mime_type,
            "browser_lang": VOICE_BROWSER_LANG[normalized_language],
            "language": normalized_language,
            "provider": "gtts",
        }
    except Exception as exc:
        errors.append(f"gTTS fallback: {exc}")

    log.warning("Server-side TTS unavailable, using browser speech fallback: %s", "; ".join(errors))
    return {
        "playback_mode": "browser",
        "spoken_text": spoken_text,
        "audio_base64": None,
        "audio_mime_type": None,
        "browser_lang": VOICE_BROWSER_LANG[normalized_language],
        "language": normalized_language,
        "provider": "browser",
    }


@app.post("/api/voice/stt")
async def voice_stt(
    file: UploadFile = File(...),
    preferred_language: str = Form("en"),
):
    """Multilingual STT with English-normalized query text for the analytics engine."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    try:
        transcript, detected_language = _transcribe_voice(
            audio_bytes,
            file.filename or "voice.webm",
            file.content_type or "audio/webm",
            preferred_language,
        )
        if not transcript:
            raise HTTPException(status_code=400, detail="Could not understand speech")

        normalized_text = transcript
        if _normalize_voice_language(detected_language) != "en":
            try:
                normalized_text = _translate_text_with_groq(transcript, "en")
            except Exception as exc:
                log.warning("STT normalization fallback used original transcript: %s", exc)
                normalized_text = transcript

        return {
            "transcript": transcript,
            "normalized_text": normalized_text,
            "detected_language": _normalize_voice_language(detected_language),
            "preferred_language": _normalize_voice_language(preferred_language),
        }
    except HTTPException:
        raise
    except Exception as exc:
        log.error("Voice STT error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/voice/reply")
async def voice_reply(req: VoiceReplyRequest):
    try:
        return await _build_voice_reply_payload(req.text, req.language)
    except Exception as exc:
        log.error("Voice reply error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/voice/tts")
async def voice_tts(req: TTSRequest):
    """Compatibility endpoint for existing binary TTS consumers."""
    payload = await _build_voice_reply_payload(req.text, req.language)
    if payload.get("playback_mode") != "audio" or not payload.get("audio_base64"):
        return Response(status_code=204)
    audio_bytes = base64.b64decode(payload["audio_base64"])
    return Response(content=audio_bytes, media_type=payload.get("audio_mime_type") or "audio/wav")

# ── Run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print()
    print("=" * 60)
    print("  BASHIRA INTELLIGENCE - API Server v2.0")
    print("  Bloomberg-level Decision Engine")
    print("=" * 60)
    print()
    print("  Endpoints:")
    print("    POST /api/query        — Ask any question")
    print("    POST /api/drill-down   — Drill into chart data")
    print("    GET  /api/knowledge-graph — Neo4j graph data")
    print("    GET  /api/schema       — Database schema")
    print("    GET  /api/health       — System health")
    print()
    print("  Predictive Analytics (ML):")
    print("    POST /predict/single   — Real-time well forecast")
    print("    POST /predict/refresh  — Nightly batch evaluation")
    print("    POST /predict/full     — GPU retrain trigger")
    print("    GET  /predict/anomalies — Anomaly feed")
    print("    GET  /predict/portfolio — Portfolio risk summary")
    print("    GET  /predict/model-info — Model health status")
    print()
    print("  Swagger: http://localhost:8005/docs")
    print("=" * 60)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8005)
