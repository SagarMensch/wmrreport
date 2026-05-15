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
import re
import json
import logging
import threading
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

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from contextlib import contextmanager

try:
    import psycopg
    from psycopg_pool import ConnectionPool
    from langgraph.checkpoint.postgres import PostgresSaver
    HAS_POSTGRES_SAVER = True
except ImportError:
    psycopg = None
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
    response_type: str = "chart"

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

    # Decision OS (additive)
    response_mode: str = "sql_only"       # sql_only | predictive
    answer_text: str = ""                 # clean public answer for predictive mode
    risk_label: str = ""                  # ON_TRACK | WATCH | AT_RISK | CRITICAL
    predictive_context: dict = field(default_factory=dict)
    predictive_summary: dict = field(default_factory=dict)
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
        self._checkpointer_lock = threading.Lock()
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

        self._setup_workspace_memory_store()

        log.info("OK: Graph Agent initialized")
        log.info("=" * 60)

    def _activate_memory_checkpointer(self, reason: str = "") -> None:
        """Switch the graph back to an in-memory checkpointer."""
        with self._checkpointer_lock:
            if not self._use_supabase and isinstance(self._checkpointer, MemorySaver):
                return

            if reason:
                log.warning("Falling back to MemorySaver checkpointer: %s", reason)
            else:
                log.warning("Falling back to MemorySaver checkpointer.")

            try:
                if self._pool is not None:
                    self._pool.close()
            except Exception as pool_error:
                log.warning("Failed to close Supabase pool cleanly: %s", pool_error)

            self._pool = None
            self._checkpointer = MemorySaver()
            self.graph = self.graph_agent_module.compile(checkpointer=self._checkpointer)
            self._use_supabase = False

    def _restore_supabase_checkpointer(self) -> None:
        """Attempt to restore the durable Supabase-backed checkpointer."""
        if self._use_supabase or not settings.SUPABASE_DB_URI or not HAS_POSTGRES_SAVER:
            return

        with self._checkpointer_lock:
            if self._use_supabase:
                return

            try:
                log.info("Attempting to restore Supabase Postgres checkpointer...")
                new_pool = ConnectionPool(settings.SUPABASE_DB_URI, kwargs={"autocommit": True})
                new_checkpointer = PostgresSaver(new_pool)
                new_checkpointer.setup()
                self._pool = new_pool
                self._checkpointer = new_checkpointer
                self.graph = self.graph_agent_module.compile(checkpointer=self._checkpointer)
                self._use_supabase = True
                log.info("OK: Supabase checkpointer restored.")
            except Exception as error:
                log.warning("Supabase checkpointer restore failed: %s", error)

    def _setup_workspace_memory_store(self) -> None:
        """Create the reflective workspace-memory store if Supabase is available."""
        if not settings.SUPABASE_DB_URI or psycopg is None:
            return

        try:
            with psycopg.connect(settings.SUPABASE_DB_URI, connect_timeout=10) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
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
                        """
                    )
                conn.commit()
        except Exception as error:
            log.warning("Workspace memory store setup failed: %s", error)

    @staticmethod
    def _normalize_memory_key(value: str, fallback: str) -> str:
        normalized = re.sub(r"[^a-z0-9_]+", "_", (value or "").lower()).strip("_")
        return normalized[:96] or fallback

    @staticmethod
    def _extract_memory_entities(*texts: str) -> list[str]:
        patterns = [
            r"\b[A-Z]{2,}(?:[_-][A-Z0-9]+){1,}\b",
            r"\b[A-Z]{3,}\d{2,}\b",
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b",
        ]
        seen: set[str] = set()
        entities: list[str] = []

        for text in texts:
            for pattern in patterns:
                for match in re.findall(pattern, text or ""):
                    token = match.strip()
                    token_lower = token.lower()
                    if token_lower in seen or len(token) < 4:
                        continue
                    seen.add(token_lower)
                    entities.append(token)
                    if len(entities) >= 12:
                        return entities
        return entities

    @staticmethod
    def _extract_sql_tables(sql: str) -> list[str]:
        table_candidates = re.findall(r"\b(?:FROM|JOIN)\s+\[?([A-Za-z0-9_]+)\]?", sql or "", re.IGNORECASE)
        unique_tables: list[str] = []
        seen: set[str] = set()
        for table in table_candidates:
            lowered = table.lower()
            if lowered not in seen:
                seen.add(lowered)
                unique_tables.append(table)
        return unique_tables[:8]

    @staticmethod
    def _extract_user_preferences(text: str) -> dict[str, str]:
        text_lower = (text or "").lower()
        preferences: dict[str, str] = {}

        if "ssms" in text_lower:
            preferences["view_mode"] = "ssms"
        elif "sql" in text_lower or "code" in text_lower:
            preferences["view_mode"] = "code"
        elif any(token in text_lower for token in ("chart", "visual", "graph", "plot")):
            preferences["view_mode"] = "visual"

        if "3d" in text_lower:
            preferences["chart_dimension"] = "3d"
        elif "2d" in text_lower:
            preferences["chart_dimension"] = "2d"

        if "portfolio" in text_lower:
            preferences["analysis_scope"] = "portfolio"
        elif "well" in text_lower:
            preferences["analysis_scope"] = "well"
        elif "rig" in text_lower:
            preferences["analysis_scope"] = "rig"

        return preferences

    @staticmethod
    def _build_reflective_summary(
        question: str,
        response_type: str,
        sql_query: str,
        total_rows: int,
        response_text: str,
        risk_label: str = "",
    ) -> str:
        tables = re.findall(r"\b(?:FROM|JOIN)\s+\[?([A-Za-z0-9_]+)\]?", sql_query or "", re.IGNORECASE)
        unique_tables: list[str] = []
        seen: set[str] = set()
        for table in tables:
            lowered = table.lower()
            if lowered not in seen:
                seen.add(lowered)
                unique_tables.append(table)

        question_snippet = (question or "").strip()[:120]
        answer_snippet = re.sub(r"\s+", " ", (response_text or "").strip())[:150]
        table_snippet = ", ".join(unique_tables[:3]) if unique_tables else "no table detected"
        row_snippet = f"{total_rows} row(s)" if total_rows else "no rows returned"
        risk_snippet = f" Risk: {risk_label}." if risk_label else ""
        return (
            f"Question: {question_snippet}. "
            f"Mode: {response_type}. "
            f"Tables: {table_snippet}. "
            f"Result: {row_snippet}. "
            f"Outcome: {answer_snippet}.{risk_snippet}"
        )[:420]

    def _upsert_workspace_memory(
        self,
        workspace_id: str,
        memory_type: str,
        memory_key: str,
        memory_value: str,
        source_session_id: str,
        confidence: float = 0.5,
        metadata: Optional[dict] = None,
    ) -> None:
        if not workspace_id or not settings.SUPABASE_DB_URI or psycopg is None or not memory_value.strip():
            return

        try:
            with psycopg.connect(settings.SUPABASE_DB_URI, connect_timeout=10) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO public.workspace_memory (
                            workspace_id,
                            memory_type,
                            memory_key,
                            memory_value,
                            source_session_id,
                            confidence,
                            metadata,
                            updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, NOW())
                        ON CONFLICT (workspace_id, memory_type, memory_key)
                        DO UPDATE SET
                            memory_value = EXCLUDED.memory_value,
                            source_session_id = EXCLUDED.source_session_id,
                            confidence = GREATEST(public.workspace_memory.confidence, EXCLUDED.confidence),
                            metadata = EXCLUDED.metadata,
                            updated_at = NOW()
                        """,
                        (
                            workspace_id,
                            memory_type,
                            memory_key,
                            memory_value.strip(),
                            source_session_id,
                            confidence,
                            json.dumps(metadata or {}),
                        ),
                    )
                conn.commit()
        except Exception as error:
            log.warning("Workspace memory upsert failed: %s", error)

    def _get_existing_workspace_summary(self, workspace_id: str) -> str:
        if not workspace_id or not settings.SUPABASE_DB_URI or psycopg is None:
            return ""

        try:
            with psycopg.connect(settings.SUPABASE_DB_URI, connect_timeout=10) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT memory_value
                        FROM public.workspace_memory
                        WHERE workspace_id = %s
                          AND memory_type = 'summary'
                          AND memory_key = 'recent_turns'
                        LIMIT 1
                        """,
                        (workspace_id,),
                    )
                    row = cur.fetchone()
                    return row[0] if row else ""
        except Exception as error:
            log.warning("Workspace summary lookup failed: %s", error)
            return ""

    def _capture_reflective_memory(
        self,
        workspace_id: str,
        session_id: str,
        question: str,
        final_state: dict,
    ) -> None:
        if not workspace_id:
            return

        response_type = final_state.get("response_type", "chart")
        sql_query = final_state.get("current_sql", "")
        total_rows = final_state.get("total_rows", 0)
        risk_label = final_state.get("risk_label", "")

        if response_type in ("clarification", "text") and final_state.get("messages"):
            response_text = final_state["messages"][-1].content
        elif final_state.get("answer_text"):
            response_text = final_state.get("answer_text", "")
        else:
            response_text = final_state.get("sql_reasoning", "")

        summary_item = self._build_reflective_summary(
            question=question,
            response_type=response_type,
            sql_query=sql_query,
            total_rows=total_rows,
            response_text=response_text,
            risk_label=risk_label,
        )

        existing_summary = self._get_existing_workspace_summary(workspace_id)
        summary_lines = [line.strip() for line in existing_summary.split("\n") if line.strip()]
        summary_lines.append(f"- {summary_item}")
        summary_lines = summary_lines[-4:]
        merged_summary = "\n".join(summary_lines)
        self._upsert_workspace_memory(
            workspace_id=workspace_id,
            memory_type="summary",
            memory_key="recent_turns",
            memory_value=merged_summary,
            source_session_id=session_id,
            confidence=0.75,
            metadata={"response_type": response_type},
        )

        for pref_key, pref_value in self._extract_user_preferences(question).items():
            self._upsert_workspace_memory(
                workspace_id=workspace_id,
                memory_type="preference",
                memory_key=pref_key,
                memory_value=pref_value,
                source_session_id=session_id,
                confidence=0.92,
                metadata={"source": "question"},
            )

        combined_text = " ".join(
            [
                question or "",
                response_text or "",
                " ".join(self._extract_sql_tables(sql_query)),
                " ".join(final_state.get("columns", [])[:8]),
            ]
        )
        for entity in self._extract_memory_entities(combined_text):
            self._upsert_workspace_memory(
                workspace_id=workspace_id,
                memory_type="entity",
                memory_key=self._normalize_memory_key(entity, "entity"),
                memory_value=entity,
                source_session_id=session_id,
                confidence=0.65,
                metadata={"source": "turn"},
            )

        for table in self._extract_sql_tables(sql_query):
            self._upsert_workspace_memory(
                workspace_id=workspace_id,
                memory_type="fact",
                memory_key=f"table_{self._normalize_memory_key(table, 'table')}",
                memory_value=f"Frequently used table: {table}",
                source_session_id=session_id,
                confidence=0.6,
                metadata={"source": "sql"},
            )

        if risk_label:
            self._upsert_workspace_memory(
                workspace_id=workspace_id,
                memory_type="fact",
                memory_key="latest_risk_label",
                memory_value=f"Most recent predictive risk label: {risk_label}",
                source_session_id=session_id,
                confidence=0.7,
                metadata={"source": "predictive"},
            )

    def _build_reflective_context(self, workspace_id: str, question: str) -> str:
        if not workspace_id or not settings.SUPABASE_DB_URI or psycopg is None:
            return ""

        try:
            with psycopg.connect(settings.SUPABASE_DB_URI, connect_timeout=10) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT memory_type, memory_key, memory_value, confidence, updated_at
                        FROM public.workspace_memory
                        WHERE workspace_id = %s
                        ORDER BY updated_at DESC
                        LIMIT 80
                        """,
                        (workspace_id,),
                    )
                    rows = cur.fetchall()
        except Exception as error:
            log.warning("Reflective memory lookup failed: %s", error)
            return ""

        if not rows:
            return ""

        question_tokens = self._tokenize_memory_text(question)
        selected_preferences: list[str] = []
        selected_summary = ""
        scored_items: list[tuple[float, str, str]] = []

        for memory_type, memory_key, memory_value, confidence, _ in rows:
            memory_value = (memory_value or "").strip()
            if not memory_value:
                continue

            if memory_type == "summary" and not selected_summary:
                selected_summary = memory_value
                continue

            if memory_type == "preference":
                selected_preferences.append(f"{memory_key}: {memory_value}")
                continue

            item_tokens = self._tokenize_memory_text(f"{memory_key} {memory_value}")
            overlap = len(question_tokens & item_tokens)
            base_score = overlap / max(len(question_tokens), 1)
            type_bonus = 0.08 if memory_type == "entity" else 0.04
            score = base_score + type_bonus + min(float(confidence or 0.0), 1.0) * 0.2
            if score > 0.08:
                scored_items.append((score, memory_type, memory_value))

        scored_items = sorted(scored_items, key=lambda item: item[0], reverse=True)[:6]

        sections: list[str] = []
        if selected_preferences:
            sections.append(
                "Preferences:\n" + "\n".join(f"- {item}" for item in selected_preferences[:4])
            )
        if selected_summary:
            sections.append("Recent workspace summary:\n" + selected_summary[:700])
        if scored_items:
            sections.append(
                "Relevant durable memory:\n"
                + "\n".join(f"- [{memory_type}] {memory_value}" for _, memory_type, memory_value in scored_items)
            )

        if not sections:
            return ""

        return (
            "Persistent workspace memory. Use this only as supporting context; "
            "current user intent and current data always win.\n\n"
            + "\n\n".join(sections)
        )[:1400]

    def _is_checkpointer_connection_error(self, error: Exception) -> bool:
        message = str(error).lower()
        return any(
            token in message
            for token in (
                "consuming input failed",
                "server closed the connection unexpectedly",
                "connection unexpectedly",
                "terminat",
                "broken pipe",
                "ssl connection has been closed unexpectedly",
            )
        )

    def _store_chat_history(self, session_id: str, question: str, sql_query: str, result_summary: str) -> None:
        """Deprecated: Frontend now handles storing conversation threads."""
        pass

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
        match = re.search(r'FROM\s+\[?(\w+)\]?', sql, re.IGNORECASE)
        return match.group(1) if match else ""

    @staticmethod
    def _tokenize_memory_text(text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9_]+", (text or "").lower())
            if len(token) > 2
        }

    def _get_workspace_memory(
        self,
        workspace_id: str,
        session_id: str,
        question: str,
        max_messages: int = 8,
    ) -> list:
        """Retrieve durable cross-session memory for the active workspace."""
        if not workspace_id or not settings.SUPABASE_DB_URI or psycopg is None:
            return []

        try:
            with psycopg.connect(settings.SUPABASE_DB_URI, connect_timeout=10) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT session_id, role, content, created_at
                        FROM public.chat_conversations
                        WHERE COALESCE(workspace_id, session_id) = %s
                          AND session_id <> %s
                        ORDER BY created_at DESC
                        LIMIT 80
                        """,
                        (workspace_id, session_id),
                    )
                    rows = cur.fetchall()
        except Exception as error:
            log.warning("Workspace memory lookup failed: %s", error)
            return []

        if not rows:
            return []

        question_tokens = self._tokenize_memory_text(question)
        scored_rows: list[tuple[float, int, str, str, Any]] = []

        for recency_rank, row in enumerate(rows):
            _, role, content, created_at = row
            text = (content or "").strip()
            if not text:
                continue

            content_tokens = self._tokenize_memory_text(text)
            overlap = len(question_tokens & content_tokens)
            overlap_score = overlap / max(len(question_tokens), 1)
            recency_score = max(0.0, 1.0 - (recency_rank / 80.0)) * 0.35
            exact_phrase_bonus = 0.15 if question.lower() in text.lower() else 0.0
            role_bonus = 0.05 if role == "user" else 0.0
            score = overlap_score + recency_score + exact_phrase_bonus + role_bonus

            scored_rows.append((score, recency_rank, role, text, created_at))

        if not scored_rows:
            return []

        selected = [row for row in scored_rows if row[0] >= 0.18]
        if not selected:
            selected = scored_rows[: min(4, len(scored_rows))]

        selected = sorted(selected, key=lambda item: (-item[0], item[1]))[:max_messages]
        selected = sorted(selected, key=lambda item: item[4])

        memory_messages = []
        for _, _, role, text, _ in selected:
            clipped = text[:400]
            if role == "assistant":
                memory_messages.append(AIMessage(content=clipped))
            else:
                memory_messages.append(HumanMessage(content=clipped))

        return memory_messages

    @staticmethod
    def _latest_turn_reasoning_steps(reasoning_steps: list[dict]) -> list[dict]:
        """Return only the reasoning steps for the current turn.

        The graph state is checkpointed per session and reasoning_steps are
        accumulated with an additive reducer. For UI/debug display we only want
        the latest query's trace, which reliably starts at the last CONTEXT step.
        """
        if not reasoning_steps:
            return []

        last_context_idx = 0
        for idx, step in enumerate(reasoning_steps):
            if str(step.get("step", "")).upper() == "CONTEXT":
                last_context_idx = idx

        return reasoning_steps[last_context_idx:]

    def __del__(self):
        if hasattr(self, '_pool') and self._pool:
            self._pool.close()

    def process(
        self,
        question: str,
        session_id: str = "default_session",
        workspace_id: Optional[str] = None,
        chat_history: list = None,
    ) -> PipelineResult:
        """
        Execute the LangGraph pipeline: question → SQL → results → chart.
        chat_history: list of {"role": "user"|"assistant", "content": "..."} from frontend
        """
        start = time.perf_counter()
        workspace_id = workspace_id or session_id

        log.info(f"Processing session {session_id} - Q: {question}")

        try:
            self._restore_supabase_checkpointer()

            # Get session context for smarter drill-downs
            session_context = self._get_session_context(session_id)
            reflective_context = self._build_reflective_context(
                workspace_id=workspace_id,
                question=question,
            )
            workspace_memory = self._get_workspace_memory(
                workspace_id=workspace_id,
                session_id=session_id,
                question=question,
            )

            config = {"configurable": {"thread_id": session_id}}

            # Build message list: inject durable workspace memory, recent chat,
            # then the new question.
            prior_messages = []
            if reflective_context:
                prior_messages.append(AIMessage(content=reflective_context))
            if workspace_memory and (not chat_history or len(chat_history) < 4):
                prior_messages.extend(workspace_memory)
                log.info(
                    "   Injected %s workspace memory messages for durable context",
                    len(workspace_memory),
                )
            if chat_history:
                # Only inject last 10 messages for efficiency
                for msg in chat_history[-10:]:
                    if msg.get("role") == "user":
                        prior_messages.append(HumanMessage(content=msg["content"]))
                    elif msg.get("role") == "assistant":
                        # Truncate long AI responses to save tokens
                        prior_messages.append(AIMessage(content=msg["content"][:400]))
                log.info(f"   Injected {len(prior_messages)} history messages for context")

            # Add the new question
            prior_messages.append(HumanMessage(content=question))

            # Reset transient turn-level state so prior clarification/chart data
            # from the checkpoint cannot leak into the current question.
            inputs = {
                "messages": prior_messages,
                "session_context": session_context,
                "current_sql": "",
                "sql_is_safe": False,
                "sql_confidence": 0.0,
                "sql_reasoning": "",
                "columns": [],
                "rows": [],
                "total_rows": 0,
                "execution_error": None,
                "chart_config": {},
                "requires_followup": False,
                "followup_prompt": "",
                "response_type": "",
                "clarification_prompt": "",
                # Decision OS (additive)
                "response_mode": "sql_only",
                "predictive_context": {},
                "answer_text": "",
                "risk_label": "",
                "predictive_summary": {},
            }

            # Invoke the graph synchronously. If the remote Postgres checkpointer
            # drops mid-request, retry once with MemorySaver so the user query
            # still completes.
            try:
                final_state = self.graph.invoke(inputs, config=config)
            except Exception as invoke_error:
                if self._use_supabase and self._is_checkpointer_connection_error(invoke_error):
                    log.warning(
                        "Supabase checkpointer failed during invoke; retrying this turn with ephemeral MemorySaver. Error: %s",
                        invoke_error,
                    )
                    temp_graph = self.graph_agent_module.compile(checkpointer=MemorySaver())
                    final_state = temp_graph.invoke(inputs, config=config)
                else:
                    raise

            # Extract final results from state
            total_ms = int((time.perf_counter() - start) * 1000)

            sql_query = final_state.get("current_sql", "")
            columns = final_state.get("columns", [])
            rows = final_state.get("rows", [])
            total_rows = final_state.get("total_rows", 0)
            chart_config = final_state.get("chart_config", {})
            chart_type = chart_config.get("chart_type", "data_table") if chart_config else "data_table"
            drill_downs = chart_config.get("drill_downs", []) if chart_config else []
            reasoning_steps = self._latest_turn_reasoning_steps(
                final_state.get("reasoning_steps", [])
            )
            execution_error = final_state.get("execution_error")
            response_type = final_state.get("response_type", "chart")

            # Conversational graph outputs should surface the last AI message,
            # not the internal sql_reasoning string.
            if response_type in ("clarification", "text") and final_state.get("messages"):
                reasoning = final_state["messages"][-1].content
            elif final_state.get("requires_followup"):
                reasoning = final_state["messages"][-1].content
            else:
                reasoning = final_state.get("sql_reasoning", "")

            # Store chat history in Supabase for memory
            result_summary = f"{total_rows} rows, {columns}"
            self._store_chat_history(session_id, question, sql_query, result_summary)
            self._capture_reflective_memory(
                workspace_id=workspace_id,
                session_id=session_id,
                question=question,
                final_state=final_state,
            )

            return PipelineResult(
                question=question,
                sql_query=sql_query,
                is_safe=True,
                response_type=response_type,
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
                # Decision OS (additive)
                response_mode=final_state.get("response_mode", "sql_only"),
                answer_text=final_state.get("answer_text", ""),
                risk_label=final_state.get("risk_label", ""),
                predictive_context=final_state.get("predictive_context", {}),
                predictive_summary=final_state.get("predictive_summary", {}),
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
