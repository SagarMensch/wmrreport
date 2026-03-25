"""
Pipeline Orchestrator — The brain of Bashira Intelligence
=========================================================
Coordinates all 5 agents in a sequential pipeline:

  Intent → Retrieval → SQL → Validation/Execution → Chart

Each step is tracked as a ReasoningStep for full explainability.
Supports drill-down execution for interactive chart exploration.

This is the single entry point for the API layer.
"""

import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Any

import dspy
from config import settings

# Agents
from agents.intent_agent import IntentAgent, IntentResult
from agents.retrieval_agent import RetrievalAgent, SchemaContext
from agents.sql_agent import SQLAgent, SQLResult
from agents.validator_agent import ValidatorAgent, ExecutionResult
from agents.chart_agent import ChartAgent, ChartConfig, DrillDownAction

# Retrieval
from retrieval.bm25_index import ColumnBM25Index

# Database
from database.neo4j_client import neo4j_client
from database.sql_client import sql_client

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from contextlib import contextmanager

try:
    import psycopg
    from psycopg_pool import ConnectionPool
    from langgraph.checkpoint.postgres import PostgresSaver
    HAS_POSTGRES_SAVER = True
except ImportError:
    HAS_POSTGRES_SAVER = False

from agents.graph_agent import BashiraGraphAgent

log = logging.getLogger("bashira.orchestrator")


# ── Data Classes ─────────────────────────────────────────────────────────

@dataclass
class ReasoningStep:
    """One step in the pipeline — tracked for explainability."""
    step: str           # INTENT, RETRIEVE, GENERATE, VALIDATE, EXECUTE, CHART
    status: str         # success, warning, error
    detail: str
    duration_ms: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Complete result from the orchestrator pipeline."""
    # Input
    question: str

    # SQL
    sql_query: str = ""
    is_safe: bool = False

    # Chart
    chart_type: str = "data_table"
    chart_config: dict = field(default_factory=dict)

    # Results
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    total_rows: int = 0
    truncated: bool = False

    # Drill-down
    drill_downs: list[dict] = field(default_factory=list)

    # Quality
    confidence: float = 0.0
    reasoning: str = ""
    reasoning_steps: list[dict] = field(default_factory=list)

    # Performance
    execution_time_ms: int = 0

    # Errors
    error: Optional[str] = None

    # Schema hint (for Knowledge Graph tab)
    schema_context: str = ""
    retrieval_summary: str = ""


# ── Pipeline Orchestrator ────────────────────────────────────────────────

class PipelineOrchestrator:
    """
    The central brain — coordinates all agents.

    Initialization:
      1. Configures DSPy with Groq LLM
      2. Connects to Neo4j and SQL Server
      3. Builds BM25 index from columns.csv
      4. Compiles SQL Agent with training examples
      5. Initializes all agents
    """

    def __init__(self):
        log.info("=" * 60)
        log.info("Initializing Bashira Intelligence Pipeline")
        log.info("=" * 60)

        # ── Configure DSPy ───────────────────────────────────────────────
        # Use Mistral as primary, Groq as fallback
        try:
            mistral_lm = dspy.LM(
                model=settings.MISTRAL_MODEL,
                api_key=settings.MISTRAL_API_KEY,
                api_base="https://api.mistral.ai/v1"
            )
            dspy.configure(lm=mistral_lm)
            log.info("OK: DSPy configured with Mistral (%s)", settings.MISTRAL_MODEL)
        except Exception as e:
            log.warning(f"Mistral failed: {e}, falling back to Groq...")
            groq_lm = dspy.LM(
                model=settings.GROQ_MODEL,
                api_key=settings.GROQ_API_KEY_2 or settings.GROQ_API_KEY,
            )
            dspy.configure(lm=groq_lm)
            log.info("OK: DSPy configured with Groq (%s)", settings.GROQ_MODEL)

        # ── Connect databases ────────────────────────────────────────────
        neo4j_client.connect()
        sql_client.connect()

        # ── Build BM25 index ─────────────────────────────────────────────
        self._bm25_index = ColumnBM25Index(settings.columns_csv_path)

        # ── Initialize agents ────────────────────────────────────────────
        log.info("Initializing Graph Agent...")
        self.graph_agent_module = BashiraGraphAgent(bm25_index=self._bm25_index)
        
        # ── Initialize Checkpointer (Supabase / Memory) ──────────────────
        self._pool = None
        self._checkpointer = MemorySaver()
        self._use_supabase = False
        self.graph = self.graph_agent_module.compile(checkpointer=self._checkpointer)
        self.is_async_graph = False
        
        if settings.SUPABASE_DB_URI and HAS_POSTGRES_SAVER:
            try:
                log.info("Connecting to Supabase PostGres Checkpointer...")
                self._pool = ConnectionPool(settings.SUPABASE_DB_URI, kwargs={"autocommit": True})
                self._checkpointer = PostgresSaver(self._pool)
                self._checkpointer.setup()
                self.graph = self.graph_agent_module.compile(checkpointer=self._checkpointer)
                self._use_supabase = True
                log.info("OK: Supabase Checkpointer Ready.")
            except Exception as e:
                log.error(f"Failed to connect to Supabase: {e}. Falling back to MemorySaver.")

        log.info("OK: Graph Agent initialized")
        log.info("=" * 60)

    def _store_chat_history(self, session_id: str, question: str, sql_query: str, result_summary: str) -> None:
        """Store chat history in Supabase for memory."""
        if not self._use_supabase:
            return
        try:
            with self._pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO chat_history (question, created_at) VALUES (%s, NOW())",
                        (f"{question} | SQL: {sql_query[:200]} | Result: {result_summary[:100]}",)
                    )
                    conn.commit()
        except Exception as e:
            log.warning(f"Failed to store chat history: {e}")

    def _get_session_context(self, session_id: str) -> dict:
        """Get context from previous queries in session for smarter drill-downs."""
        if not self._use_supabase:
            return {}
        try:
            config = {"configurable": {"thread_id": session_id}}
            checkpoint = self._checkpointer.get(config)
            if checkpoint and checkpoint.get("channel_values"):
                state = checkpoint["channel_values"]
                return {
                    "last_table": self._extract_table_name(state.get("current_sql", "")),
                    "last_columns": state.get("columns", []),
                    "last_sql": state.get("current_sql", ""),
                }
        except Exception as e:
            log.warning(f"Failed to get session context: {e}")
        return {}

    def _extract_table_name(self, sql: str) -> str:
        """Extract table name from SQL query."""
        import re
        match = re.search(r'FROM\s+\[?(\w+)\]?', sql, re.IGNORECASE)
        return match.group(1) if match else ""

    def __del__(self):
        if hasattr(self, '_pool') and self._pool:
            self._pool.close()

    def process(self, question: str, session_id: str = "default_session") -> PipelineResult:
        """
        Execute the LangGraph pipeline: question → SQL → results → chart.
        """
        start = time.perf_counter()
        
        log.info(f"Processing session {session_id} - Q: {question}")
        
        try:
            # Get session context for smarter drill-downs
            session_context = self._get_session_context(session_id)
            
            config = {"configurable": {"thread_id": session_id}}
            
            # Send the new message to the state graph
            inputs = {
                "messages": [HumanMessage(content=question)],
                "session_context": session_context  # For smarter drill-downs
            }
            
            # Invoke the graph synchronously
            final_state = self.graph.invoke(inputs, config=config)
            
            # Extract final results from state
            total_ms = int((time.perf_counter() - start) * 1000)
            
            sql_query = final_state.get("current_sql", "")
            columns = final_state.get("columns", [])
            rows = final_state.get("rows", [])
            total_rows = final_state.get("total_rows", 0)
            chart_config = final_state.get("chart_config", {})
            chart_type = chart_config.get("chart_type", "data_table") if chart_config else "data_table"
            drill_downs = chart_config.get("drill_downs", []) if chart_config else []
            reasoning_steps = final_state.get("reasoning_steps", [])
            execution_error = final_state.get("execution_error")
            
            # If followup is requested, the answer is the last AI message
            if final_state.get("requires_followup"):
                reasoning = final_state["messages"][-1].content
            else:
                reasoning = final_state.get("sql_reasoning", "")
            
            # Store chat history in Supabase for memory
            result_summary = f"{total_rows} rows, {columns}"
            self._store_chat_history(session_id, question, sql_query, result_summary)
            
            return PipelineResult(
                question=question,
                sql_query=sql_query,
                is_safe=True,
                chart_type=chart_type,
                chart_config=chart_config,
                columns=columns,
                rows=rows,
                total_rows=total_rows,
                truncated=False,  
                drill_downs=drill_downs,
                confidence=final_state.get("sql_confidence", 0.0),
                reasoning=reasoning,
                reasoning_steps=reasoning_steps,
                execution_time_ms=total_ms,
                error=execution_error,
                schema_context=final_state.get("schema_context", ""),
                retrieval_summary=final_state.get("retrieval_metadata", {}).get("summary", ""),
            )

        except Exception as e:
            log.exception("Pipeline error: %s", e)
            total_ms = int((time.perf_counter() - start) * 1000)
            return PipelineResult(
                question=question,
                error=f"Pipeline error: {str(e)}",
                reasoning_steps=[],
                execution_time_ms=total_ms,
            )

    # ── Drill-Down Execution ─────────────────────────────────────────────

    def execute_drill_down(
        self,
        sql_template: str,
        clicked_value: str,
        chart_type: str = "data_table",
    ) -> PipelineResult:
        """
        Execute a drill-down query triggered by chart interaction.

        The SQL template has a {clicked_value} placeholder that
        gets filled with the value the user clicked on.
        """
        # Sanitize clicked_value (prevent injection)
        safe_value = clicked_value.replace("'", "''").replace(";", "").replace("--", "")
        sql = sql_template.replace("{clicked_value}", safe_value)

        log.info("Drill-down: %s → %s", safe_value, sql[:100])

        # Execute directly (already validated templates)
        result = sql_client.execute_query(sql)

        if result.get("error"):
            return PipelineResult(
                question=f"Drill-down: {clicked_value}",
                sql_query=sql,
                error=result["error"],
            )

        # Generate chart for drill-down result
        chart = self.graph_agent_module.chart_agent.forward(
            user_question=f"Details for {clicked_value}",
            sql_query=sql,
            result_columns=result["columns"],
            row_count=result.get("total_rows", len(result["rows"])),
        )

        return PipelineResult(
            question=f"Drill-down: {clicked_value}",
            sql_query=sql,
            is_safe=True,
            chart_type=chart.chart_type,
            chart_config=asdict(chart),
            columns=result["columns"],
            rows=result["rows"],
            total_rows=result.get("total_rows", len(result["rows"])),
            truncated=result.get("truncated", False),
            drill_downs=[asdict(d) for d in chart.drill_downs],
            confidence=0.95,
        )

    # ── Knowledge Graph Data ─────────────────────────────────────────────

    def get_knowledge_graph(self, limit: int = 2000) -> dict:
        """
        Fetch the schema knowledge graph for visualization.
        Returns nodes and edges for the Knowledge Graph tab.
        """
        try:
            with neo4j_client._fresh_session() as session:
                normalized_limit = max(1, min(limit, 5000))

                # Fetch a stable node set first, then derive edges only within it.
                node_result = session.run("""
                    MATCH (n)
                    WHERE n:Table OR n:Column OR n:Well
                    WITH n
                    ORDER BY CASE
                        WHEN n:Well THEN 0
                        WHEN n:Table THEN 1
                        ELSE 2
                    END,
                    coalesce(n.name, n.wellId, n.tableName, '')
                    LIMIT $limit
                    RETURN elementId(n) AS id, labels(n) AS labels,
                           coalesce(n.name, n.wellId, '') AS name,
                           coalesce(n.description, '') AS description,
                           coalesce(n.tableName, '') AS tableName,
                           coalesce(n.dataType, '') AS dataType
                    ORDER BY name
                """, limit=normalized_limit)
                nodes = [dict(r) for r in node_result]
                node_ids = [node["id"] for node in nodes]

                edge_result = session.run("""
                    MATCH (a)-[r]->(b)
                    WHERE elementId(a) IN $node_ids
                      AND elementId(b) IN $node_ids
                    RETURN elementId(r) AS id,
                           elementId(a) AS source,
                           elementId(b) AS target,
                           type(r) AS type,
                           coalesce(r.description, '') AS description
                    ORDER BY type(r), source, target
                """, node_ids=node_ids)
                edges = [dict(r) for r in edge_result]

            return {
                "nodes": nodes,
                "edges": edges,
                "stats": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "requested_limit": normalized_limit,
                },
            }
        except Exception as e:
            log.error("Knowledge graph fetch failed: %s", e)
            return {"nodes": [], "edges": [], "error": str(e)}

    # ── Health ───────────────────────────────────────────────────────────

    def health(self) -> dict:
        """Full system health check."""
        return {
            "neo4j": neo4j_client.health_check(),
            "sql_server": sql_client.health_check(),
            "bm25_index": self._bm25_index.document_count > 0,
            "bm25_documents": self._bm25_index.document_count,
            "agents_loaded": True,
        }
