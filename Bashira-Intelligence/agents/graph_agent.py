"""
LangGraph Agent — Stateful conversational data engine
=====================================================
Replaces the linear orchestrator pipeline with a cyclic, stateful graph.
Includes conversational follow-ups for lists/un-chartable data, natively
integrating 2D/3D visualizations and drill-downs.
"""

import operator
import re
import logging
from datetime import date, timedelta
from typing import TypedDict, Annotated, Sequence, Any, Optional
from dataclasses import asdict

import dspy

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
# If not async, we can use the sync version:
# from langgraph.checkpoint.postgres import PostgresSaver

# Existing agent logic wrappers
from agents.intent_agent import IntentAgent
from agents.retrieval_agent import RetrievalAgent, SchemaContext
from agents.sql_agent import SQLAgent
from agents.validator_agent import ValidatorAgent
from agents.chart_agent import ChartAgent, ChartConfig

# Decision OS agents (additive)
from agents.question_classifier import classify_question
from agents.predictive_scan_agent import PredictiveScanAgent
from agents.public_response_agent import PublicResponseAgent

# Databases
from database.neo4j_client import neo4j_client
from database.sql_client import sql_client

log = logging.getLogger("bashira.graph_agent")

# ── DSPy Signature for Context Resolution ───────────────────────────────

class ContextResolverSignature(dspy.Signature):
    """You are a context-resolution assistant for a database query system.

    Given the conversation history and the user's latest message, determine
    if the latest message is a vague follow-up that needs context.

    If the latest message is vague (e.g., "yes give me these details", "show me that",
    "what about it", "tell me more"), rewrite it as a FULLY SELF-CONTAINED question
    that preserves all entities, table names, and column references from the conversation.

    If the latest message is ALREADY a clear, specific question, return it UNCHANGED.

    RULES:
    1. NEVER add information that wasn't in the conversation.
    2. PRESERVE all specific entity names, cluster names, well IDs exactly as mentioned.
    3. The rewritten question must be answerable by a SQL database query.
    4. Keep the rewritten question concise and direct.
    """

    conversation_history = dspy.InputField(
        desc="The last few messages in the conversation, formatted as 'Role: content'"
    )
    latest_message = dspy.InputField(
        desc="The user's latest message that may need context resolution"
    )
    resolved_question = dspy.OutputField(
        desc="The fully self-contained question. If the original was already clear, return it unchanged."
    )


# Vague follow-up patterns that trigger rewriting
_VAGUE_PATTERNS = re.compile(
    r'\b(yes|yeah|ok|okay|sure|these|this|that|those|it|them|details|more|above|same|previous|show me|give me|tell me)\b',
    re.IGNORECASE
)

_CHART_FOLLOWUP_PATTERNS = re.compile(
    r'\b(chart|graph|plot|visuali[sz]e|dashboard)\b',
    re.IGNORECASE
)

_FOLLOWUP_PREFIX_PATTERNS = re.compile(
    r'^(yes|yeah|ok|okay|sure|please|good|great|fine)\b[\s,.-]*',
    re.IGNORECASE
)

_PROFIT_MARGIN_PATTERNS = re.compile(
    r'\b(profit margin|margin)\b',
    re.IGNORECASE
)

_PROJECT_PATTERNS = re.compile(
    r'\bproject\b',
    re.IGNORECASE
)

_PROJECT_GRAIN_HINTS = re.compile(
    r'\b(rig\s*code|rigcode|category|individual|project\s*name|well\s*/?\s*project\s*name|well\s*name)\b',
    re.IGNORECASE
)

_PROXY_HINTS = re.compile(
    r'\b(proxy|planned\s+vs\s+actual|purpose\s+value|true\s+cost|cost\s+exists)\b',
    re.IGNORECASE
)

_AFFIRMATIVE_REPLY_PATTERNS = re.compile(
    r'^(yes|yeah|yep|yup|sure|ok|okay|fine|do it|go ahead|use it)\b',
    re.IGNORECASE
)

_NEGATIVE_REPLY_PATTERNS = re.compile(
    r'^(no|nope|dont|don\'t|do not|not now|only if true cost)\b',
    re.IGNORECASE
)

_MILESTONE_PATTERNS = re.compile(
    r'\bmilestones?\b',
    re.IGNORECASE
)

_OVERDUE_PATTERNS = re.compile(
    r'\boverdue\b',
    re.IGNORECASE
)

_THIS_WEEK_PATTERNS = re.compile(
    r'\b(this week|current week)\b',
    re.IGNORECASE
)

_CRITICAL_PATH_PATTERNS = re.compile(
    r'\bcritical path\b',
    re.IGNORECASE
)

_ACTIVITY_PATTERNS = re.compile(
    r'\bactivit(y|ies)\b',
    re.IGNORECASE
)

_PORTFOLIO_SCOPE_PATTERNS = re.compile(
    r'\b(portfolio|across the portfolio|all wells|all projects|overall)\b',
    re.IGNORECASE
)

_COST_OVERRUN_PATTERNS = re.compile(
    r'\b((top|highest|largest)\s+)?(cost|budget)\s+overruns?\b|\bover\s+budget\b|\bcost\s+vs\s+budget\b|\bbudget\s+vs\s+actual\b',
    re.IGNORECASE
)

_COST_OVERRUN_FORECAST_PATTERNS = re.compile(
    r'\bcost\s+overrun\s+forecast\b|\bforecast(ed)?\s+cost\s+overrun\b',
    re.IGNORECASE
)

_TIME_WINDOW_HINTS = re.compile(
    r'\b(this month|current month|month[- ]to[- ]date|this quarter|current quarter|quarter[- ]to[- ]date|this year|current year|year[- ]to[- ]date|ytd|cumulative|to date|to-date|overall|all time)\b',
    re.IGNORECASE
)

_DIRECT_CAUSE_ONLY_PATTERNS = re.compile(
    r'\b(no proxy|direct cause only|only direct cause|only direct causes|no operational context)\b',
    re.IGNORECASE
)

_OPERATIONAL_PROXY_PATTERNS = re.compile(
    r'\b(operational context|use proxy|use the proxy|issue text|wellmonitoringreport|reason_if_kpi_not_met|remark_status_area_of_attention_issues_|latest operational context)\b',
    re.IGNORECASE
)

_WHY_PATTERNS = re.compile(
    r'\b(why|reason|reasons|cause|causes)\b',
    re.IGNORECASE
)

_DELIVERY_RISK_PATTERNS = re.compile(
    r'\b(top\s*10\s+risks?\s+impacting\s+delivery|risks?\s+impacting\s+delivery)\b',
    re.IGNORECASE
)

_OPERATIONAL_DELIVERY_PROXY_PATTERNS = re.compile(
    r'\b(operational\s+delivery\s+risk\s+proxy|latest\s+wellmonitoringreport\s+snapshot|at-risk\s+project\s+categories|use\s+operational\s+proxy)\b',
    re.IGNORECASE
)

_KPI_TREND_PATTERNS = re.compile(
    r'\b(trend\s+analysis\s+of\s+performance\s+kpis?|performance\s+kpi\s+trend|kpi\s+trend\s+analysis)\b',
    re.IGNORECASE
)

_KPI_THRESHOLD_PATTERNS = re.compile(
    r'\b(which\s+kpis?\s+are\s+deviating\s+from\s+thresholds?\s+today|kpis?\s+deviating\s+from\s+thresholds?)\b',
    re.IGNORECASE
)

_KPI_THRESHOLD_PROXY_PATTERNS = re.compile(
    r'\b(use\s+the\s+latest\s+operational\s+snapshot|below\s+50%\s+progress|use\s+proxy\s+thresholds?|major\s+phase\s+kpis?\s+below\s+50%)\b',
    re.IGNORECASE
)

_CHANGE_ORDER_PATTERNS = re.compile(
    r'\b(change\s+order\s+cycle\s+time)\b',
    re.IGNORECASE
)

_CONTRACT_RISK_EXPOSURE_PATTERNS = re.compile(
    r'\b(risk\s+exposure\s+per\s+contract)\b',
    re.IGNORECASE
)

_CONTRACT_OBLIGATION_PATTERNS = re.compile(
    r'\b(contractual\s+obligations?\s+at\s+risk)\b',
    re.IGNORECASE
)

_MARGIN_SCENARIO_PATTERNS = re.compile(
    r'\b(scenarios?\s+improve\s+project\s+margin|improve\s+project\s+margin)\b',
    re.IGNORECASE
)

_MANPOWER_SCENARIO_PATTERNS = re.compile(
    r'\bwhat\s+happens?\s+if\s+manpower\s+increases?\s+by\s+\d+%?\b',
    re.IGNORECASE
)

_FORECAST_MANPOWER_PATTERNS = re.compile(
    r'\bforecast(ed)?\s+manpower\s+requirement\b',
    re.IGNORECASE
)

_SKILLS_SHORTAGE_PATTERNS = re.compile(
    r'\bskills?\s+(are\s+in\s+)?shortage\b|\bskills?\s+in\s+shortage\b',
    re.IGNORECASE
)

_SUBCONTRACTOR_MANPOWER_PATTERNS = re.compile(
    r'\bsubcontractor\b.*\bmanpower\b|\bmanpower\b.*\bsubcontractor\b',
    re.IGNORECASE
)

_OVERTIME_COST_PATTERNS = re.compile(
    r'\bovertime\b.*\b(cost|plan)\b|\bovertime\s+cost\s+vs\s+plan\b',
    re.IGNORECASE
)

_ABSENTEEISM_PATTERNS = re.compile(
    r'\babsenteeism\b',
    re.IGNORECASE
)

_PROCUREMENT_CRITICAL_MATERIALS_PATTERNS = re.compile(
    r'\bprocurement\s+status\b.*\bcritical\s+materials\b|\bcritical\s+materials\b',
    re.IGNORECASE
)

_MATERIALS_DELAY_PATTERNS = re.compile(
    r'\bwhich\s+materials\s+are\s+delayed\b|\bdelayed\s+materials\b',
    re.IGNORECASE
)

_LEAD_TIME_VARIANCE_PATTERNS = re.compile(
    r'\blead\s+time\s+variance\b',
    re.IGNORECASE
)

_OVERDUE_PO_PATTERNS = re.compile(
    r'\bwhich\s+pos?\s+are\s+overdue\b|\boverdue\s+pos?\b',
    re.IGNORECASE
)

_VENDOR_PERFORMANCE_PATTERNS = re.compile(
    r'\bvendor\s+performance\s+rating\b',
    re.IGNORECASE
)

_INVENTORY_LEVEL_PATTERNS = re.compile(
    r'\binventory\s+level\s+vs\s+requirement\b',
    re.IGNORECASE
)

_ITEMS_DELAY_PATTERNS = re.compile(
    r'\bwhich\s+items\s+are\s+causing\s+project\s+delays\b|\bitems?\s+causing\s+project\s+delays\b',
    re.IGNORECASE
)

_LOGISTICS_SHIPMENT_PATTERNS = re.compile(
    r'\blogistics\s+status\s+for\s+shipments\b|\bshipment\s+status\b',
    re.IGNORECASE
)

_EXPEDITING_STATUS_PATTERNS = re.compile(
    r'\bexpediting\s+status\b',
    re.IGNORECASE
)

_VENDOR_QUALITY_PATTERNS = re.compile(
    r'\bvendors?\s+have\s+quality\s+issues\b|\bvendor\s+quality\b',
    re.IGNORECASE
)

_EQUIPMENT_PATTERNS = re.compile(
    r'\bequipment\b|\bequipments\b',
    re.IGNORECASE
)

_EQUIPMENT_AVAILABILITY_PATTERNS = re.compile(
    r'\bequipment\s+availability\s+vs\s+requirement\b',
    re.IGNORECASE
)

_EQUIPMENT_IDLE_PATTERNS = re.compile(
    r'\bwhich\s+equipment\s+is\s+idle\b|\bidle\s+equipment\b',
    re.IGNORECASE
)

_EQUIPMENT_UTILIZATION_PATTERNS = re.compile(
    r'\butilization\s+rate\b.*\bequipment\b|\bequipment\s+utilization\b',
    re.IGNORECASE
)

_EQUIPMENT_MAINTENANCE_PATTERNS = re.compile(
    r'\bmaintenance\s+schedule\s+compliance\b|\bbreakdowns?\b|\bfuel\s+consumption\b|\bdowntime\b|\brental\s+vs\s+owned\b|\bequipment\s+cost\b|\bcritical\s+for\s+upcoming\s+work\b',
    re.IGNORECASE
)

_SAFETY_INCIDENT_PATTERNS = re.compile(
    r'\btrir\b|\bincident(s)?\b|\bnear[- ]?miss\b|\bsafety\s+risk\b|\bptw\b|\bpermit\s+to\s+work\b|\bsafety\s+violations?\b|\bsafety\s+training\b|\baudit\b|\binspection\b|\bcorrective\s+actions?\b',
    re.IGNORECASE
)

_CONTRACT_COMMERCIAL_PATTERNS = re.compile(
    r'\bvariation\s+orders?\b|\bclaims?\b|\bcontract\s+utilization\b|\bodc\s+call[- ]?offs?\b|\bbilled\s+vs\s+certified\s+vs\s+paid\b|\bpenalties?\b|\bld\s+risks?\b|\bsubcontractor\s+payment\s+status\b|\bcontracts?\s+nearing\s+completion\b',
    re.IGNORECASE
)

_MANHOUR_PROXY_PATTERNS = re.compile(
    r'\b(manhourforacst|forecast\s+manhours|open\s+workload|activitytaskplan|use\s+proxy)\b',
    re.IGNORECASE
)

_SKILL_PROXY_PATTERNS = re.compile(
    r'\b(crew[_ ]type\s+demand|forecast\s+manhours|activitytaskplan|use\s+proxy|open\s+tasks)\b',
    re.IGNORECASE
)

_SUBCONTRACTOR_PROXY_PATTERNS = re.compile(
    r'\b(crew[- ]count|crew\s+count|productivity\s+proxy|ph_productivity|latest\s+month|use\s+proxy)\b',
    re.IGNORECASE
)


class AgentState(TypedDict):
    """The state passed between graph nodes."""
    # Conversation History
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # Context injected by steps
    intent_data: dict
    schema_context: str
    retrieval_metadata: dict

    # Session context from Supabase for smarter drill-downs
    session_context: dict

    # Generated SQL and Execution
    current_sql: str
    sql_is_safe: bool
    sql_confidence: float
    sql_reasoning: str

    # Results
    columns: list[str]
    rows: list[list[Any]]
    total_rows: int
    execution_error: Optional[str]

    # Explainability Pipeline
    reasoning_steps: Annotated[list[dict], operator.add]

    # Final Output Rendering
    chart_config: dict
    requires_followup: bool
    followup_prompt: str
    response_type: str
    clarification_prompt: str

    # ── Decision OS (additive) ──────────────────────────────────────
    response_mode: str           # "sql_only" | "predictive"
    predictive_context: dict     # forecast, risk, causal, interventions
    answer_text: str             # clean public answer (predictive mode)
    risk_label: str              # ON_TRACK | WATCH | AT_RISK | CRITICAL
    predictive_summary: dict     # structured scan results for frontend card


class BashiraGraphAgent:
    """Stateful LangGraph Agent for Database Querying and Charting."""

    def __init__(self, bm25_index=None):
        self.intent_agent = IntentAgent()
        # Fallback if bm25 not provided, ideally injected by orchestrator
        if bm25_index:
            self.retrieval_agent = RetrievalAgent(bm25_index)

        self.sql_agent = SQLAgent(compile_on_init=True)
        self.validator_agent = ValidatorAgent(self.sql_agent)
        self.chart_agent = ChartAgent()

        # Decision OS agents (additive)
        self.predictive_scan_agent = PredictiveScanAgent()
        self.public_response_agent = PublicResponseAgent()

        # Context resolver (lightweight DSPy call)
        self._context_resolver = dspy.Predict(ContextResolverSignature)

        # Build the Graph
        self.workflow = StateGraph(AgentState)

        # Add Nodes
        self.workflow.add_node("resolve_context", self.resolve_context)
        self.workflow.add_node("extract_intent", self.extract_intent)
        self.workflow.add_node("retrieve_schema", self.retrieve_schema)
        self.workflow.add_node("generate_sql", self.generate_sql)
        self.workflow.add_node("clarification_node", self.clarification_node)
        self.workflow.add_node("execute_sql", self.execute_sql)
        self.workflow.add_node("analyze_data", self.analyze_data)
        self.workflow.add_node("conversational_followup", self.conversational_followup)
        self.workflow.add_node("generate_chart", self.generate_chart)

        # Decision OS nodes (additive)
        self.workflow.add_node("predictive_scan", self.predictive_scan)
        self.workflow.add_node("compose_public_answer", self.compose_public_answer)

        # Add Edges — resolve_context runs FIRST
        self.workflow.set_entry_point("resolve_context")
        self.workflow.add_edge("resolve_context", "extract_intent")
        self.workflow.add_conditional_edges(
            "extract_intent",
            self.route_after_intent,
            {
                "sql_only": "retrieve_schema",
                "predictive": "predictive_scan",
            }
        )
        self.workflow.add_edge("retrieve_schema", "generate_sql")

        # Conditional Edge after SQL Generation (Confidence Gate)
        self.workflow.add_conditional_edges(
            "generate_sql",
            self.route_after_sql,
            {
                "execute": "execute_sql",
                "clarify": "clarification_node",
                "error": END
            }
        )
        self.workflow.add_edge("clarification_node", END)

        # ── Decision OS: Conditional branch after execute_sql ──
        # sql_only → existing analyze_data flow (unchanged)
        # predictive → predictive_scan → compose_public_answer → END
        self.workflow.add_conditional_edges(
            "execute_sql",
            self.route_response,
            {
                "sql_only": "analyze_data",
                "predictive": "predictive_scan",
            }
        )

        self.workflow.add_edge("predictive_scan", "compose_public_answer")
        self.workflow.add_edge("compose_public_answer", END)

        # Conditional Edge after Data Analysis (existing — sql_only path)
        self.workflow.add_conditional_edges(
            "analyze_data",
            self.route_after_analysis,
            {
                "followup": "conversational_followup",
                "chart": "generate_chart",
                "error": END  # If execution failed fundamentally
            }
        )

        self.workflow.add_edge("conversational_followup", "generate_chart")
        self.workflow.add_edge("generate_chart", END)

    def compile(self, checkpointer=None):
        """Compile the workflow with a persistent checkpointer."""
        return self.workflow.compile(checkpointer=checkpointer)

    @staticmethod
    def _is_profit_margin_project_question(text: str) -> bool:
        return bool(_PROFIT_MARGIN_PATTERNS.search(text) and _PROJECT_PATTERNS.search(text))

    @staticmethod
    def _extract_project_grain(text: str) -> str | None:
        lowered = text.lower()
        if "rig code" in lowered or "rigcode" in lowered:
            return "rig code"
        if "category" in lowered:
            return "category"
        if "individual" in lowered or "project name" in lowered or "well/project name" in lowered or "well name" in lowered:
            return "individual project name"
        return None

    @staticmethod
    def _extract_proxy_preference(text: str) -> str | None:
        lowered = text.lower()
        if "no proxy" in lowered or "only if true cost" in lowered or "only answer if true cost" in lowered:
            return "reject"
        if "true cost" in lowered and "proxy" not in lowered and "planned vs actual" not in lowered and "purpose value" not in lowered:
            return "reject"
        if ("planned vs actual" in lowered or "purpose value" in lowered or "use proxy" in lowered
                or "using proxy" in lowered or ("yes" in lowered and "proxy" in lowered)):
            return "accept"
        return None

    def _normalize_profit_margin_question(self, question: str) -> str:
        if not self._is_profit_margin_project_question(question):
            return question

        if self._extract_project_grain(question):
            return question

        # Client/business language uses "project" to mean category unless the
        # user explicitly asks for a different grain such as rig code.
        return (
            f"{question.rstrip('.')} "
            "Use category as the project grain, where Category values include "
            "Nimr Location, Nimr Flowline, Marmul Location, and Marmul Flowline."
        )

    @staticmethod
    def _is_affirmative_reply(text: str) -> bool:
        return bool(_AFFIRMATIVE_REPLY_PATTERNS.search(text.strip()))

    @staticmethod
    def _is_negative_reply(text: str) -> bool:
        return bool(_NEGATIVE_REPLY_PATTERNS.search(text.strip()))

    def _profit_margin_clarification_prompt(self, question: str) -> str | None:
        if not self._is_profit_margin_project_question(question):
            return None

        grain = self._extract_project_grain(question) or "category"
        proxy = self._extract_proxy_preference(question)

        if grain and proxy == "accept":
            return None

        if grain and proxy == "reject":
            return (
                f"True profit margin cannot be calculated exactly for {grain} from the current schema "
                f"because no confirmed project cost field is available. If you want, I can instead "
                f"compute plan-vs-actual purpose value variance at the {grain} level."
            )

        if grain and proxy is None:
            return (
                f"Assuming project means {grain}. True profit margin requires cost "
                f"data, but the current schema only has planned vs actual purpose value in Revenue. "
                f"Should I use planned vs actual purpose value as a proxy and return revenue variance / "
                f"achievement rate at the {grain} level?"
            )

        return (
            "Assuming project means category values such as Nimr Location, Nimr Flowline, "
            "and Marmul Location. True profit margin requires cost data, but the current schema "
            "only exposes planned vs actual purpose value in Revenue. Should I use that as a proxy "
            "and return revenue variance / achievement rate by category instead?"
        )

    @staticmethod
    def _is_weekly_overdue_milestones_question(text: str) -> bool:
        return bool(
            _MILESTONE_PATTERNS.search(text)
            and _OVERDUE_PATTERNS.search(text)
            and _THIS_WEEK_PATTERNS.search(text)
        )

    @staticmethod
    def _extract_milestone_scope(text: str) -> str | None:
        lowered = text.lower()
        if (
            "activitytaskplan" in lowered
            or "schedule milestone" in lowered
            or "schedule task" in lowered
            or "schedule tasks" in lowered
            or "task milestone" in lowered
            or "task milestones" in lowered
        ):
            return "schedule_tasks"
        if (
            "wellmonitoringreport" in lowered
            or "high-level rig" in lowered
            or "rig milestone" in lowered
            or "rig milestones" in lowered
            or "rig on location" in lowered
        ):
            return "rig_milestones"
        return None

    @staticmethod
    def _current_week_window_label() -> str:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        return f"{week_start.isoformat()} to {week_end.isoformat()}"

    def _milestone_overdue_clarification_prompt(self, question: str) -> str | None:
        if not self._is_weekly_overdue_milestones_question(question):
            return None
        if self._extract_milestone_scope(question):
            return None
        return (
            "Do you mean overdue schedule milestones/tasks from ActivityTaskPlan, "
            "or high-level rig milestones from WellMonitoringReport? "
            f"I will use the current week window {self._current_week_window_label()}."
        )

    @staticmethod
    def _is_critical_path_question(text: str) -> bool:
        return bool(_CRITICAL_PATH_PATTERNS.search(text) and _ACTIVITY_PATTERNS.search(text))

    @staticmethod
    def _extract_critical_path_mode(text: str) -> str | None:
        lowered = text.lower()
        if "true critical path only" in lowered or "only if explicitly available" in lowered:
            return "true_only"
        if "proxy" in lowered or "currently critical" in lowered or "critical activities" in lowered:
            return "proxy"
        return None

    @staticmethod
    def _extract_critical_path_scope(text: str) -> str | None:
        lowered = text.lower()
        if _PORTFOLIO_SCOPE_PATTERNS.search(lowered):
            return "portfolio"
        if "cluster" in lowered or "nimr" in lowered or "marmul" in lowered:
            return "cluster"
        if "specific well" in lowered or "for well" in lowered or "well " in lowered or "specific project" in lowered or "for project" in lowered:
            return "specific"
        return None

    def _critical_path_clarification_prompt(self, question: str) -> str | None:
        if not self._is_critical_path_question(question):
            return None

        mode = self._extract_critical_path_mode(question)
        scope = self._extract_critical_path_scope(question)

        if mode == "true_only":
            return (
                "A true critical path is not directly available from the current schema because there is no explicit "
                "critical-path flag or predecessor/successor table. If you want, I can instead use a SQL proxy based on "
                "open activities with overdue target_end, remaining duration, and incomplete progress."
            )

        if mode == "proxy" and scope:
            return None

        return (
            "Do you want the true schedule critical path for a specific well/project, or a SQL proxy for currently "
            "critical open activities? The current schema has activity dates, progress, remaining duration, and hierarchy, "
            "but no explicit critical-path flag or predecessor/successor table. If you want the proxy, should I do it "
            "across the portfolio, for a specific cluster, or for a specific well/project?"
        )

    @staticmethod
    def _is_cost_overrun_question(text: str) -> bool:
        return bool(_COST_OVERRUN_PATTERNS.search(text))

    @staticmethod
    def _cost_overrun_requires_why(text: str) -> bool:
        return bool(_WHY_PATTERNS.search(text))

    @staticmethod
    def _extract_cost_overrun_grain(text: str) -> str | None:
        lowered = text.lower()
        if "project code" in lowered or "rig code" in lowered or "rigcode" in lowered:
            return "project code"
        if "category" in lowered:
            return "category"
        if "well level" in lowered or "by well" in lowered or "well-wise" in lowered or "well wise" in lowered or "well " in lowered:
            return "well"
        return None

    @staticmethod
    def _extract_cost_overrun_window(text: str) -> str | None:
        lowered = text.lower()
        if "this month" in lowered or "current month" in lowered or "month-to-date" in lowered or "month to date" in lowered:
            return "current month"
        if "this quarter" in lowered or "current quarter" in lowered or "quarter-to-date" in lowered or "quarter to date" in lowered:
            return "current quarter"
        if "this year" in lowered or "current year" in lowered or "year-to-date" in lowered or "year to date" in lowered or "ytd" in lowered:
            return "current year"
        if "cumulative" in lowered or "to-date" in lowered or "to date" in lowered or "overall" in lowered or "all time" in lowered:
            return "cumulative-to-date"
        return None

    @staticmethod
    def _extract_cost_overrun_proxy_preference(text: str) -> str | None:
        lowered = text.lower()
        if (
            _DIRECT_CAUSE_ONLY_PATTERNS.search(lowered)
            or "true cost only" in lowered
            or "only if true cost exists" in lowered
            or "no revenue proxy" in lowered
        ):
            return "reject"
        if (
            _OPERATIONAL_PROXY_PATTERNS.search(lowered)
            or "planned vs actual" in lowered
            or "purpose value" in lowered
            or "use revenue" in lowered
            or "budget proxy" in lowered
            or "cost proxy" in lowered
            or "use proxy" in lowered
        ):
            return "accept"
        return None

    def _cost_overrun_clarification_prompt(self, question: str) -> str | None:
        if not self._is_cost_overrun_question(question):
            return None

        grain = self._extract_cost_overrun_grain(question)
        window = self._extract_cost_overrun_window(question)
        proxy = self._extract_cost_overrun_proxy_preference(question)
        needs_why = self._cost_overrun_requires_why(question)

        missing_parts: list[str] = []
        if not grain:
            missing_parts.append("grain")
        if not window:
            missing_parts.append("time_window")
        if proxy is None:
            missing_parts.append("budget_proxy")
        if needs_why and proxy is None:
            missing_parts.append("why_proxy")

        if not missing_parts:
            return None

        prompt = (
            "The current schema does not expose a confirmed cost/budget fact table for management reporting. "
            "Should I use Revenue planned_purpose_value vs actual_purpose_value as a proxy for budget vs actual, "
            "and do you want the answer by well, project code, or category, "
            "for current month, current quarter, current year, or cumulative-to-date?"
        )
        if needs_why:
            prompt += (
                " The current schema has planned and actual values in Revenue, but no direct populated "
                "cost-cause field. Should I attach operational context from the latest WellMonitoringReport "
                "where available as a proxy for why?"
            )
        return prompt

    @staticmethod
    def _is_cost_overrun_forecast_question(text: str) -> bool:
        return bool(_COST_OVERRUN_FORECAST_PATTERNS.search(text))

    def _cost_overrun_forecast_clarification_prompt(self, question: str) -> str | None:
        if not self._is_cost_overrun_forecast_question(question):
            return None

        grain = self._extract_cost_overrun_grain(question)
        window = self._extract_cost_overrun_window(question)
        proxy = self._extract_cost_overrun_proxy_preference(question)

        if grain and window and proxy == "accept":
            return None

        return (
            "The current schema does not expose a confirmed cost-at-completion model. "
            "Should I use Revenue planned_purpose_value vs actual_purpose_value as a proxy for forecasted cost overrun, "
            "and return the projection by well, project code, or category, for current quarter or current year?"
        )

    @staticmethod
    def _is_delivery_risk_question(text: str) -> bool:
        return bool(_DELIVERY_RISK_PATTERNS.search(text))

    @staticmethod
    def _uses_operational_delivery_risk_proxy(text: str) -> bool:
        return bool(_OPERATIONAL_DELIVERY_PROXY_PATTERNS.search(text))

    def _delivery_risk_clarification_prompt(self, question: str) -> str | None:
        if not self._is_delivery_risk_question(question):
            return None
        if self._uses_operational_delivery_risk_proxy(question):
            return None
        return (
            "The current schema does not contain a formal enterprise risk register. "
            "Should I return the top at-risk project categories using an operational delivery-risk proxy "
            "from the latest WellMonitoringReport snapshot?"
        )

    @staticmethod
    def _is_kpi_trend_question(text: str) -> bool:
        return bool(_KPI_TREND_PATTERNS.search(text))

    @staticmethod
    def _is_kpi_threshold_question(text: str) -> bool:
        return bool(_KPI_THRESHOLD_PATTERNS.search(text))

    @staticmethod
    def _uses_kpi_threshold_proxy(text: str) -> bool:
        return bool(_KPI_THRESHOLD_PROXY_PATTERNS.search(text))

    def _kpi_threshold_clarification_prompt(self, question: str) -> str | None:
        if not self._is_kpi_threshold_question(question):
            return None
        if self._uses_kpi_threshold_proxy(question):
            return None
        return (
            "The current schema does not contain a formal KPI-threshold registry. "
            "Should I use the latest operational snapshot and flag major phase KPIs below 50% progress "
            "as threshold deviations?"
        )

    # ── Nodes ────────────────────────────────────────────────────────────

    @staticmethod
    def _is_forecast_manpower_requirement_question(text: str) -> bool:
        return bool(_FORECAST_MANPOWER_PATTERNS.search(text))

    @staticmethod
    def _extract_manpower_requirement_grain(text: str) -> str | None:
        lowered = text.lower()
        if "by well" in lowered or "per well" in lowered or ("well" in lowered and "project" not in lowered and "category" not in lowered):
            return "well"
        if "category" in lowered or "project" in lowered or "across projects" in lowered:
            return "category"
        return None

    @staticmethod
    def _extract_manpower_proxy_preference(text: str) -> str | None:
        lowered = text.lower()
        if "no proxy" in lowered or "only if actual headcount exists" in lowered:
            return "reject"
        if _MANHOUR_PROXY_PATTERNS.search(lowered):
            return "accept"
        return None

    def _forecast_manpower_clarification_prompt(self, question: str) -> str | None:
        if not self._is_forecast_manpower_requirement_question(question):
            return None
        grain = self._extract_manpower_requirement_grain(question)
        proxy = self._extract_manpower_proxy_preference(question)
        if grain and proxy == "accept":
            return None
        return (
            "The current schema does not expose a clean live manpower-headcount forecast by project. "
            "Should I use ActivityTaskPlan.manhourforacst as a proxy for forecast manpower requirement, "
            "and return it by project category or by well for the current open workload?"
        )

    @staticmethod
    def _is_skills_shortage_question(text: str) -> bool:
        return bool(_SKILLS_SHORTAGE_PATTERNS.search(text))

    @staticmethod
    def _extract_skills_proxy_preference(text: str) -> str | None:
        lowered = text.lower()
        if "no proxy" in lowered or "only if actual skill inventory exists" in lowered:
            return "reject"
        if _SKILL_PROXY_PATTERNS.search(lowered):
            return "accept"
        return None

    def _skills_shortage_clarification_prompt(self, question: str) -> str | None:
        if not self._is_skills_shortage_question(question):
            return None
        if self._extract_skills_proxy_preference(question) == "accept":
            return None
        return (
            "The current schema does not contain a normalized skill-demand vs skill-supply model. "
            "If you want, I can use incomplete ActivityTaskPlan crew_type demand ranked by forecast manhours "
            "as a proxy for where skill demand is heaviest."
        )

    @staticmethod
    def _is_subcontractor_manpower_status_question(text: str) -> bool:
        return bool(_SUBCONTRACTOR_MANPOWER_PATTERNS.search(text))

    @staticmethod
    def _extract_subcontractor_proxy_preference(text: str) -> str | None:
        lowered = text.lower()
        if "no proxy" in lowered or "only if headcount exists" in lowered:
            return "reject"
        if _SUBCONTRACTOR_PROXY_PATTERNS.search(lowered):
            return "accept"
        return None

    def _subcontractor_manpower_clarification_prompt(self, question: str) -> str | None:
        if not self._is_subcontractor_manpower_status_question(question):
            return None
        if self._extract_subcontractor_proxy_preference(question) == "accept":
            return None
        return (
            "The current schema has ATNM/Sub Contractor productivity and crew identifiers, but not direct subcontractor manpower headcount. "
            "Should I return a proxy using the latest PH productivity month, grouped by ATNM/Sub Contractor with distinct crew-group counts and average productivity?"
        )

    def _schema_limitation_prompt(self, question: str) -> str | None:
        lowered = question.lower()
        if _CHANGE_ORDER_PATTERNS.search(lowered):
            return (
                "The current client schema does not contain a change-order or variation-order cycle-time fact model, "
                "so change order cycle time cannot be calculated from this database."
            )
        if _CONTRACT_RISK_EXPOSURE_PATTERNS.search(lowered) or _CONTRACT_OBLIGATION_PATTERNS.search(lowered):
            return (
                "The current client schema does not contain contract exposure, contractual-obligation tracking, "
                "or a contract-risk register. I should not fabricate contract-risk analytics from operational progress tables."
            )
        if _EQUIPMENT_AVAILABILITY_PATTERNS.search(lowered):
            return (
                "The current client schema does not contain a populated equipment master with available-vs-required counts by equipment type. "
                "It only has sparse equipment identifiers on a small subset of crews, so true equipment availability vs requirement cannot be calculated from this database."
            )
        if _EQUIPMENT_IDLE_PATTERNS.search(lowered) or _EQUIPMENT_UTILIZATION_PATTERNS.search(lowered) or _EQUIPMENT_MAINTENANCE_PATTERNS.search(lowered):
            return (
                "The current client schema does not contain live equipment status, maintenance logs, breakdown events, fuel, rental/owned flags, or downtime facts. "
                "I should not fabricate equipment analytics from sparse crew equipment IDs."
            )
        if _OVERTIME_COST_PATTERNS.search(lowered):
            return (
                "The current client schema does not contain overtime hours, overtime cost, or labor-cost-plan fields. "
                "If you want, I can instead show planned vs actual manhours by project as a workforce-effort proxy."
            )
        if _ABSENTEEISM_PATTERNS.search(lowered):
            return (
                "The current client schema does not contain attendance or absence facts, so absenteeism rate cannot be calculated from this database."
            )
        if _SAFETY_INCIDENT_PATTERNS.search(lowered):
            return (
                "The current client schema does not contain a direct incident, near-miss, PTW, safety training, audit, inspection, or corrective-action fact table. "
                "So I cannot calculate TRIR, incident counts, incident root causes, safety violations, or safety compliance metrics from this database."
            )
        if _CONTRACT_COMMERCIAL_PATTERNS.search(lowered):
            return (
                "The current client schema does not contain a contract-commercial fact model for variation orders, claims, billed/certified/paid status, penalties, subcontractor payments, or contract closeout status. "
                "I should not invent those metrics from project progress tables."
            )
        if _MARGIN_SCENARIO_PATTERNS.search(lowered):
            return (
                "The current schema does not contain a true project-margin model, and the current CPU predictive stack is built for schedule/progress risk rather than commercial margin simulation. "
                "If you want, I can instead analyze schedule-improvement scenarios or revenue-variance proxies, but not a validated project-margin scenario."
            )
        if _MANPOWER_SCENARIO_PATTERNS.search(lowered):
            return (
                "The current CPU predictive model does not use manpower/headcount as a causal feature, so it cannot reliably simulate the impact of increasing manpower by 10%. "
                "If you want, I can instead show current open-workload manhour demand or analyze schedule-risk drivers from the existing model."
            )
        if _ITEMS_DELAY_PATTERNS.search(lowered):
            return (
                "Do you mean delayed activities/tasks from ActivityTaskPlan, or material items? "
                "The current schema supports activities/tasks, but it does not contain a populated item-level inventory or material-delay fact table."
            )
        if (
            _PROCUREMENT_CRITICAL_MATERIALS_PATTERNS.search(lowered)
            or _MATERIALS_DELAY_PATTERNS.search(lowered)
            or _LEAD_TIME_VARIANCE_PATTERNS.search(lowered)
            or _OVERDUE_PO_PATTERNS.search(lowered)
            or _VENDOR_PERFORMANCE_PATTERNS.search(lowered)
            or _INVENTORY_LEVEL_PATTERNS.search(lowered)
            or _LOGISTICS_SHIPMENT_PATTERNS.search(lowered)
            or _EXPEDITING_STATUS_PATTERNS.search(lowered)
            or _VENDOR_QUALITY_PATTERNS.search(lowered)
        ):
            return (
                "The current client schema does not contain a populated material master, promised delivery dates, inventory balances, shipment tracking, vendor rating, or vendor-quality fact table. "
                "I should not fabricate this. If you want, I can instead use a narrow proxy such as phase-level material readiness or PO-presence status where those fields exist."
            )
        return None

    def resolve_context(self, state: AgentState) -> dict:
        """Rewrite vague follow-ups into self-contained questions.

        SAFE DESIGN:
        - Only activates for SHORT messages (< 12 words) that contain vague references
        - Specific questions pass through UNTOUCHED
        - If rewrite fails, falls back to original question
        """
        messages = state["messages"]
        latest = messages[-1].content.strip()
        if latest.endswith("?") and len(latest.split()) >= 6 and not _FOLLOWUP_PREFIX_PATTERNS.search(latest):
            log.info("--- CONTEXT: Standalone question, skipping resolution ---")
            return {"reasoning_steps": [{"step": "CONTEXT", "status": "success", "detail": "Standalone question - no rewrite needed."}]}
        prior_user_messages = [
            msg.content.strip()
            for msg in messages[:-1]
            if isinstance(msg, HumanMessage) and msg.content.strip()
        ]
        prior_profit_margin_question = ""
        for content in reversed(prior_user_messages):
            if self._is_profit_margin_project_question(content):
                prior_profit_margin_question = content
                break

        prior_cost_overrun_question = ""
        for content in reversed(prior_user_messages):
            if self._is_cost_overrun_question(content):
                prior_cost_overrun_question = content
                break

        prior_forecast_manpower_question = ""
        for content in reversed(prior_user_messages):
            if self._is_forecast_manpower_requirement_question(content):
                prior_forecast_manpower_question = content
                break

        prior_skills_shortage_question = ""
        for content in reversed(prior_user_messages):
            if self._is_skills_shortage_question(content):
                prior_skills_shortage_question = content
                break

        prior_subcontractor_manpower_question = ""
        for content in reversed(prior_user_messages):
            if self._is_subcontractor_manpower_status_question(content):
                prior_subcontractor_manpower_question = content
                break

        prior_delivery_risk_question = ""
        for content in reversed(prior_user_messages):
            if self._is_delivery_risk_question(content):
                prior_delivery_risk_question = content
                break

        prior_kpi_threshold_question = ""
        for content in reversed(prior_user_messages):
            if self._is_kpi_threshold_question(content):
                prior_kpi_threshold_question = content
                break

        prior_cost_overrun_forecast_question = ""
        for content in reversed(prior_user_messages):
            if self._is_cost_overrun_forecast_question(content):
                prior_cost_overrun_forecast_question = content
                break

        prior_delivery_risk_question = ""
        for content in reversed(prior_user_messages):
            if self._is_delivery_risk_question(content):
                prior_delivery_risk_question = content
                break

        prior_kpi_threshold_question = ""
        for content in reversed(prior_user_messages):
            if self._is_kpi_threshold_question(content):
                prior_kpi_threshold_question = content
                break

        prior_cost_overrun_forecast_question = ""
        for content in reversed(prior_user_messages):
            if self._is_cost_overrun_forecast_question(content):
                prior_cost_overrun_forecast_question = content
                break

        cost_overrun_followup = bool(
            prior_cost_overrun_question and (
                self._extract_cost_overrun_grain(latest)
                or self._extract_cost_overrun_window(latest)
                or self._extract_cost_overrun_proxy_preference(latest)
            )
        )

        manpower_forecast_followup = bool(
            prior_forecast_manpower_question and (
                self._extract_manpower_requirement_grain(latest)
                or self._extract_manpower_proxy_preference(latest)
            )
        )

        skills_shortage_followup = bool(
            prior_skills_shortage_question and self._extract_skills_proxy_preference(latest)
        )

        subcontractor_manpower_followup = bool(
            prior_subcontractor_manpower_question and self._extract_subcontractor_proxy_preference(latest)
        )

        delivery_risk_followup = bool(
            prior_delivery_risk_question and (
                self._uses_operational_delivery_risk_proxy(latest) or self._is_affirmative_reply(latest)
            )
        )

        kpi_threshold_followup = bool(
            prior_kpi_threshold_question and (
                self._uses_kpi_threshold_proxy(latest) or self._is_affirmative_reply(latest)
            )
        )

        cost_overrun_forecast_followup = bool(
            prior_cost_overrun_forecast_question and (
                self._extract_cost_overrun_grain(latest)
                or self._extract_cost_overrun_window(latest)
                or self._extract_cost_overrun_proxy_preference(latest)
            )
        )

        # Safety check 1: Only 1 message in history → nothing to resolve, skip
        if len(messages) <= 1:
            log.info("--- CONTEXT: Single message, skipping resolution ---")
            return {"reasoning_steps": [{"step": "CONTEXT", "status": "success", "detail": "Direct question — no history needed."}]}

        # Safety check 2: Long specific question → already clear, skip
        word_count = len(latest.split())
        if word_count > 12 and not (
            (prior_profit_margin_question and (_PROJECT_GRAIN_HINTS.search(latest) or _PROXY_HINTS.search(latest)))
            or cost_overrun_followup
            or cost_overrun_forecast_followup
            or manpower_forecast_followup
            or skills_shortage_followup
            or subcontractor_manpower_followup
            or delivery_risk_followup
            or kpi_threshold_followup
        ):
            log.info(f"--- CONTEXT: Specific question ({word_count} words), passing through ---")
            return {"reasoning_steps": [{"step": "CONTEXT", "status": "success", "detail": f"Clear question ({word_count} words) — no rewrite needed."}]}

        # Safety check 3: Does it contain vague references?
        if not _VAGUE_PATTERNS.search(latest) and not (
            (prior_profit_margin_question and (_PROJECT_GRAIN_HINTS.search(latest) or _PROXY_HINTS.search(latest)))
            or cost_overrun_followup
            or cost_overrun_forecast_followup
            or manpower_forecast_followup
            or skills_shortage_followup
            or subcontractor_manpower_followup
            or delivery_risk_followup
            or kpi_threshold_followup
        ):
            log.info(f"--- CONTEXT: No vague patterns detected, passing through ---")
            return {"reasoning_steps": [{"step": "CONTEXT", "status": "success", "detail": "No vague references — no rewrite needed."}]}

        # Build conversation summary from last 10 messages
        log.info(f"--- CONTEXT: Vague follow-up detected, resolving... ---")

        prior_user_messages = [
            msg.content.strip()
            for msg in messages[:-1]
            if isinstance(msg, HumanMessage) and msg.content.strip()
        ]
        prior_profit_margin_question = ""
        for content in reversed(prior_user_messages):
            if self._is_profit_margin_project_question(content):
                prior_profit_margin_question = content
                break

        prior_cost_overrun_question = ""
        for content in reversed(prior_user_messages):
            if self._is_cost_overrun_question(content):
                prior_cost_overrun_question = content
                break

        prior_forecast_manpower_question = ""
        for content in reversed(prior_user_messages):
            if self._is_forecast_manpower_requirement_question(content):
                prior_forecast_manpower_question = content
                break

        prior_skills_shortage_question = ""
        for content in reversed(prior_user_messages):
            if self._is_skills_shortage_question(content):
                prior_skills_shortage_question = content
                break

        prior_subcontractor_manpower_question = ""
        for content in reversed(prior_user_messages):
            if self._is_subcontractor_manpower_status_question(content):
                prior_subcontractor_manpower_question = content
                break

        last_ai_message = ""
        for msg in reversed(messages[:-1]):
            if isinstance(msg, AIMessage) and msg.content.strip():
                last_ai_message = msg.content.strip()
                break

        if prior_profit_margin_question and "should i use" in last_ai_message.lower() and "proxy" in last_ai_message.lower():
            if self._is_affirmative_reply(latest):
                resolved = f"{prior_profit_margin_question} Use planned vs actual purpose value as a proxy."
                log.info(f"   -> Resolved affirmative proxy follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved short affirmative reply against prior proxy clarification."
                    }]
                }

            if self._is_negative_reply(latest):
                resolved = f"{prior_profit_margin_question} No proxy. Only answer if true cost exists."
                log.info(f"   -> Resolved negative proxy follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved short negative reply against prior proxy clarification."
                    }]
                }

        if prior_profit_margin_question and (_PROJECT_GRAIN_HINTS.search(latest) or _PROXY_HINTS.search(latest)):
            resolved = f"{prior_profit_margin_question} {latest}"
            log.info(f"   â†’ Resolved clarification follow-up: '{latest}' â†’ '{resolved}'")
            return {
                "messages": [HumanMessage(content=resolved)],
                "reasoning_steps": [{
                    "step": "CONTEXT",
                    "status": "success",
                    "detail": f"Resolved clarification reply against prior user question: '{prior_profit_margin_question}'"
                }]
            }

        if prior_cost_overrun_question and (
            "planned and actual values in revenue" in last_ai_message.lower()
            or "top cost overruns by well" in last_ai_message.lower()
            or "cost vs budget" in last_ai_message.lower()
        ):
            if (
                self._extract_cost_overrun_grain(latest)
                or self._extract_cost_overrun_window(latest)
                or self._extract_cost_overrun_proxy_preference(latest)
            ):
                resolved = f"{prior_cost_overrun_question} {latest}"
                log.info(f"   -> Resolved cost-overrun clarification follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved cost-overrun clarification reply against prior user question."
                    }]
                }

        if prior_forecast_manpower_question and "manhourforacst" in last_ai_message.lower():
            if self._extract_manpower_requirement_grain(latest) or self._extract_manpower_proxy_preference(latest):
                resolved = f"{prior_forecast_manpower_question} {latest}"
                log.info(f"   -> Resolved manpower-forecast clarification follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved manpower-forecast clarification reply against prior user question."
                    }]
                }

        if prior_skills_shortage_question and "crew_type demand" in last_ai_message.lower():
            if self._is_affirmative_reply(latest):
                resolved = f"{prior_skills_shortage_question} Use incomplete ActivityTaskPlan crew_type demand as a proxy for shortage."
                log.info(f"   -> Resolved skills-shortage proxy follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved short affirmative reply against prior skills-shortage proxy clarification."
                    }]
                }

            if self._extract_skills_proxy_preference(latest):
                resolved = f"{prior_skills_shortage_question} {latest}"
                log.info(f"   -> Resolved skills-shortage clarification follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved skills-shortage clarification reply against prior user question."
                    }]
                }

        if prior_subcontractor_manpower_question and "atnm/sub contractor" in last_ai_message.lower():
            if self._is_affirmative_reply(latest):
                resolved = f"{prior_subcontractor_manpower_question} Use the latest PH productivity month as a crew-count and productivity proxy."
                log.info(f"   -> Resolved subcontractor-manpower proxy follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved short affirmative reply against prior subcontractor-manpower proxy clarification."
                    }]
                }

            if self._extract_subcontractor_proxy_preference(latest):
                resolved = f"{prior_subcontractor_manpower_question} {latest}"
                log.info(f"   -> Resolved subcontractor-manpower clarification follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved subcontractor-manpower clarification reply against prior user question."
                    }]
                }

        if prior_delivery_risk_question and "operational delivery-risk proxy" in last_ai_message.lower():
            if self._is_affirmative_reply(latest):
                resolved = f"{prior_delivery_risk_question} Use operational delivery risk proxy by project category."
                log.info(f"   -> Resolved delivery-risk proxy follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved short affirmative reply against prior delivery-risk proxy clarification."
                    }]
                }

            if self._uses_operational_delivery_risk_proxy(latest):
                resolved = f"{prior_delivery_risk_question} {latest}"
                log.info(f"   -> Resolved delivery-risk clarification follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved delivery-risk clarification reply against prior user question."
                    }]
                }

        if prior_kpi_threshold_question and "formal kpi-threshold registry" in last_ai_message.lower():
            if self._is_affirmative_reply(latest):
                resolved = f"{prior_kpi_threshold_question} Use the latest operational snapshot and flag major phase KPIs below 50% progress as threshold deviations."
                log.info(f"   -> Resolved KPI-threshold proxy follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved short affirmative reply against prior KPI-threshold clarification."
                    }]
                }

            if self._uses_kpi_threshold_proxy(latest):
                resolved = f"{prior_kpi_threshold_question} {latest}"
                log.info(f"   -> Resolved KPI-threshold clarification follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved KPI-threshold clarification reply against prior user question."
                    }]
                }

        if prior_cost_overrun_forecast_question and "forecasted cost overrun" in last_ai_message.lower():
            if (
                self._extract_cost_overrun_grain(latest)
                or self._extract_cost_overrun_window(latest)
                or self._extract_cost_overrun_proxy_preference(latest)
            ):
                resolved = f"{prior_cost_overrun_forecast_question} {latest}"
                log.info(f"   -> Resolved cost-overrun-forecast clarification follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved cost-overrun-forecast clarification reply against prior user question."
                    }]
                }

        prior_milestone_question = ""
        for content in reversed(prior_user_messages):
            if self._is_weekly_overdue_milestones_question(content):
                prior_milestone_question = content
                break

        if prior_milestone_question and "activitytaskplan" in last_ai_message.lower() and "wellmonitoringreport" in last_ai_message.lower():
            lowered_latest = latest.lower()
            if any(token in lowered_latest for token in [
                "activitytaskplan",
                "schedule milestone",
                "schedule task",
                "schedule tasks",
                "task milestone",
                "task milestones",
                "tasks",
            ]):
                resolved = f"{prior_milestone_question} Use schedule milestones/tasks from ActivityTaskPlan."
                log.info(f"   -> Resolved milestone-scope follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved milestone scope to ActivityTaskPlan schedule tasks."
                    }]
                }

            if any(token in lowered_latest for token in [
                "wellmonitoringreport",
                "high-level rig",
                "rig milestone",
                "rig milestones",
                "rig on location",
            ]):
                resolved = f"{prior_milestone_question} Use high-level rig milestones from WellMonitoringReport."
                log.info(f"   -> Resolved milestone-scope follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved milestone scope to WellMonitoringReport high-level milestones."
                    }]
                }

        prior_critical_path_question = ""
        for content in reversed(prior_user_messages):
            if self._is_critical_path_question(content):
                prior_critical_path_question = content
                break

        if prior_critical_path_question and "critical path" in last_ai_message.lower():
            if self._extract_critical_path_mode(latest) or self._extract_critical_path_scope(latest):
                resolved = f"{prior_critical_path_question} {latest}"
                log.info(f"   -> Resolved critical-path clarification follow-up: '{latest}' -> '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": "Resolved critical-path clarification reply against prior user question."
                    }]
                }

        # Deterministic fast-path for chart follow-ups. This avoids the resolver
        # drifting into assistant-invented column names when the user is simply
        # asking to visualize the previously discussed question.
        if _CHART_FOLLOWUP_PATTERNS.search(latest):
            anchor_question = ""
            for content in reversed(prior_user_messages):
                normalized = content.lower()
                if len(content.split()) >= 4 and not _CHART_FOLLOWUP_PATTERNS.search(normalized):
                    anchor_question = content
                    break

            if anchor_question:
                cleaned_latest = _FOLLOWUP_PREFIX_PATTERNS.sub("", latest).strip(" .,:;")
                action = "Generate a chart"
                if cleaned_latest and cleaned_latest.lower() not in {"chart", "graph", "plot", "dashboard"}:
                    action = cleaned_latest[0].upper() + cleaned_latest[1:]
                resolved = f"{action} for: {anchor_question}"
                log.info(f"   → Resolved chart follow-up: '{latest}' → '{resolved}'")
                return {
                    "messages": [HumanMessage(content=resolved)],
                    "reasoning_steps": [{
                        "step": "CONTEXT",
                        "status": "success",
                        "detail": f"Resolved chart follow-up using prior user question: '{anchor_question}'"
                    }]
                }

        history_lines = []
        for msg in messages[-10:]:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            # Truncate long AI responses to save tokens
            content = msg.content[:300] if role == "Assistant" else msg.content
            history_lines.append(f"{role}: {content}")

        history_text = "\n".join(history_lines)

        try:
            result = self._context_resolver(
                conversation_history=history_text,
                latest_message=latest
            )
            resolved = result.resolved_question.strip()

            # Safety check 4: If resolved question is empty or identical, keep original
            if not resolved or resolved.lower() == latest.lower():
                log.info(f"   → No rewrite needed")
                return {"reasoning_steps": [{"step": "CONTEXT", "status": "success", "detail": "Question was already clear."}]}

            log.info(f"   → Resolved: '{latest}' → '{resolved}'")

            # Replace the last message with the resolved version
            return {
                "messages": [HumanMessage(content=resolved)],
                "reasoning_steps": [{
                    "step": "CONTEXT",
                    "status": "success",
                    "detail": f"Resolved vague follow-up: '{latest}' → '{resolved}'"
                }]
            }
        except Exception as e:
            # FALLBACK: If rewrite fails, use original question — zero impact on accuracy
            log.warning(f"   ! Context resolution failed: {e}. Using original question.")
            return {"reasoning_steps": [{"step": "CONTEXT", "status": "warning", "detail": f"Resolution failed, using original: {e}"}]}

    def route_after_sql(self, state: AgentState) -> str:
        """Route to execution or clarification based on confidence."""
        if state.get("clarification_prompt"):
            return "clarify"
        sql = (state.get("current_sql") or "").strip()
        if not sql:
            return "clarify"
        if "INSUFFICIENT_SCHEMA" in sql.upper():
            return "clarify"
        if not re.match(r"^\s*(SELECT|WITH)\b", sql, re.IGNORECASE):
            return "clarify"

        # The validator/self-healing loop is the real safety net here.
        # Multi-table operational questions often land in the 0.7-0.9 range,
        # so blocking everything below 0.95 causes false clarification loops.
        if state.get("sql_confidence", 0) < 0.60:
            return "clarify"
        return "execute"

    def route_after_intent(self, state: AgentState) -> str:
        """Route immediately after intent extraction.

        Predictive questions should not depend on SQL generation/execution to
        reach the Julia/forecast engines. SQL remains the default path for
        retrieval, KPI, and chart questions.
        """
        mode = state.get("response_mode", "sql_only")
        if mode == "predictive":
            log.info("--- ROUTE: Predictive branch selected at intent step ---")
            return "predictive"
        return "sql_only"

    def clarification_node(self, state: AgentState) -> dict:
        """Handle low-confidence queries conversationally."""
        log.info("--- GRAPH STEP: CLARIFICATION ---")
        clarification_msg = state.get("clarification_prompt")
        if not clarification_msg:
            reasoning = state.get("sql_reasoning", "I'm missing a few details needed to generate this chart.")
            clarification_msg = f"I'm not fully confident I know what metrics to pull for this.\n\n*(Thought process: {reasoning})*\n\nCould you clarify your request?"

        return {
            "response_type": "clarification",
            "messages": [AIMessage(content=clarification_msg)],
            "reasoning_steps": [{
                "step": "CLARIFICATION",
                "status": "warning",
                "detail": f"Confidence was {state.get('sql_confidence', 0):.2f}. Asked user for clarification."
            }]
        }

    def route_response(self, state: AgentState) -> str:
        """Route after execute_sql: sql_only path or predictive path."""
        mode = state.get("response_mode", "sql_only")
        if mode == "predictive":
            log.info("--- ROUTE: Predictive branch (alien tech) ---")
            return "predictive"
        if state.get("execution_error"):
            # SQL-only questions still rely on analyze_data to surface execution
            # errors and avoid chart generation.
            return "sql_only"
        return "sql_only"

    def extract_intent(self, state: AgentState) -> dict:
        """Extract entities and infer column hits + classify response mode."""
        latest_message = state["messages"][-1].content
        session_context = state.get("session_context", {})

        log.info(f"--- GRAPH STEP: EXTRACT INTENT ---")
        log.info(f"Question: {latest_message}")

        # ── Decision OS: Classify question mode ──
        response_mode = classify_question(latest_message)
        log.info(f"   ◆ Response mode: {response_mode}")

        # Use session context to enhance drill-down understanding
        context_hint = ""
        if session_context.get("last_table") and ("drill" in latest_message.lower() or latest_message.replace("Drill down on ", "").isdigit()):
            context_hint = f" Previous query was on table {session_context['last_table']}. "
            log.info(f"   Using context: {session_context.get('last_table')}")

        try:
            intent = self.intent_agent(user_question=context_hint + latest_message)
            log.info(f"   ✓ Intent extracted: {intent.query_type}")
            return {
                "response_mode": response_mode,
                "intent_data": {
                    "query_type": intent.query_type,
                    "entities": intent.entities,
                    "column_hints": intent.column_hints,
                    "expanded_question": intent.expanded_question,
                    "original_question": latest_message
                },
                "reasoning_steps": [{
                    "step": "INTENT",
                    "status": "success",
                    "detail": f"Detected {intent.query_type} query ({response_mode}) with entities: {intent.entities}",
                    "duration_ms": 100
                }]
            }
        except Exception as e:
             return {"response_mode": "sql_only", "reasoning_steps": [{"step": "INTENT", "status": "error", "detail": str(e)}]}

    def retrieve_schema(self, state: AgentState) -> dict:
        """Retrieve Neo4j path schema using names and descriptions."""
        log.info("--- GRAPH STEP: RETRIEVE SCHEMA ---")
        import collections
        # Reconstruct a mock IntentResult object for the existing retrieval agent
        IntentObj = collections.namedtuple('IntentResult', list(state["intent_data"].keys()))
        intent = IntentObj(**state["intent_data"])

        try:
            schema: SchemaContext = self.retrieval_agent.retrieve(intent)

            # If nothing found, we still continue to let the LLM try or fail gracefully
            status = "success" if schema.columns else "warning"

            return {
                "schema_context": schema.schema_text,
                "retrieval_metadata": {
                    "summary": schema.retrieval_summary,
                    "column_count": len(schema.columns) if hasattr(schema, 'columns') else 0
                },
                "reasoning_steps": [{
                    "step": "RETRIEVE",
                    "status": status,
                    "detail": schema.retrieval_summary,
                    "duration_ms": 200
                }]
            }
        except Exception as e:
            return {"reasoning_steps": [{"step": "RETRIEVE", "status": "error", "detail": str(e)}]}

    def generate_sql(self, state: AgentState) -> dict:
        """Generate Read-Only SQL using DSPy."""
        log.info("--- GRAPH STEP: GENERATE SQL ---")
        question = state["messages"][-1].content
        effective_question = self._normalize_profit_margin_question(question)

        # CRITICAL: Always check profit-margin clarification against the ORIGINAL
        # user question, not the resolved/rewritten question which may carry
        # context words from prior turns (e.g. "project" from a previous query).
        original_question = state.get("intent_data", {}).get("original_question", question)
        clarification_prompt = self._critical_path_clarification_prompt(original_question)
        if clarification_prompt:
            return {
                "current_sql": "",
                "sql_confidence": 0.0,
                "sql_reasoning": "Critical-path definition must be clarified before generating SQL.",
                "clarification_prompt": clarification_prompt,
                "reasoning_steps": [{
                    "step": "GENERATE",
                    "status": "warning",
                    "detail": "Detected ambiguous critical-path request without an approved proxy scope."
                }]
            }

        clarification_prompt = self._milestone_overdue_clarification_prompt(original_question)
        if clarification_prompt:
            return {
                "current_sql": "",
                "sql_confidence": 0.0,
                "sql_reasoning": "Milestone source must be clarified before generating SQL.",
                "clarification_prompt": clarification_prompt,
                "reasoning_steps": [{
                    "step": "GENERATE",
                    "status": "warning",
                    "detail": "Detected ambiguous milestone source for overdue-this-week request."
                }]
            }

        clarification_prompt = self._cost_overrun_clarification_prompt(original_question)
        if clarification_prompt:
            return {
                "current_sql": "",
                "sql_confidence": 0.0,
                "sql_reasoning": "Cost/budget proxy, grain, or time window must be clarified before generating SQL.",
                "clarification_prompt": clarification_prompt,
                "reasoning_steps": [{
                    "step": "GENERATE",
                    "status": "warning",
                    "detail": "Detected ambiguous cost/budget question requiring grain, time-window, or proxy clarification."
                }]
            }

        clarification_prompt = self._cost_overrun_forecast_clarification_prompt(original_question)
        if clarification_prompt:
            return {
                "current_sql": "",
                "sql_confidence": 0.0,
                "sql_reasoning": "Forecasted cost-overrun proxy, grain, or time window must be clarified before generating SQL.",
                "clarification_prompt": clarification_prompt,
                "reasoning_steps": [{
                    "step": "GENERATE",
                    "status": "warning",
                    "detail": "Detected forecasted cost-overrun request that requires an approved proxy and forecast scope."
                }]
            }

        clarification_prompt = self._delivery_risk_clarification_prompt(original_question)
        if clarification_prompt:
            return {
                "current_sql": "",
                "sql_confidence": 0.0,
                "sql_reasoning": "Delivery-risk definition must be clarified before generating SQL.",
                "clarification_prompt": clarification_prompt,
                "reasoning_steps": [{
                    "step": "GENERATE",
                    "status": "warning",
                    "detail": "Detected delivery-risk request without an approved operational proxy definition."
                }]
            }

        clarification_prompt = self._kpi_threshold_clarification_prompt(original_question)
        if clarification_prompt:
            return {
                "current_sql": "",
                "sql_confidence": 0.0,
                "sql_reasoning": "KPI-threshold proxy must be clarified before generating SQL.",
                "clarification_prompt": clarification_prompt,
                "reasoning_steps": [{
                    "step": "GENERATE",
                    "status": "warning",
                    "detail": "Detected KPI-threshold request without an approved threshold proxy definition."
                }]
            }

        clarification_prompt = self._forecast_manpower_clarification_prompt(original_question)
        if clarification_prompt:
            return {
                "current_sql": "",
                "sql_confidence": 0.0,
                "sql_reasoning": "Manpower forecast proxy or grain must be clarified before generating SQL.",
                "clarification_prompt": clarification_prompt,
                "reasoning_steps": [{
                    "step": "GENERATE",
                    "status": "warning",
                    "detail": "Detected manpower-forecast request that requires an approved proxy and scope."
                }]
            }

        clarification_prompt = self._skills_shortage_clarification_prompt(original_question)
        if clarification_prompt:
            return {
                "current_sql": "",
                "sql_confidence": 0.0,
                "sql_reasoning": "Skills-shortage proxy must be clarified before generating SQL.",
                "clarification_prompt": clarification_prompt,
                "reasoning_steps": [{
                    "step": "GENERATE",
                    "status": "warning",
                    "detail": "Detected skills-shortage request without an approved proxy definition."
                }]
            }

        clarification_prompt = self._subcontractor_manpower_clarification_prompt(original_question)
        if clarification_prompt:
            return {
                "current_sql": "",
                "sql_confidence": 0.0,
                "sql_reasoning": "Subcontractor manpower proxy must be clarified before generating SQL.",
                "clarification_prompt": clarification_prompt,
                "reasoning_steps": [{
                    "step": "GENERATE",
                    "status": "warning",
                    "detail": "Detected subcontractor-manpower request without an approved proxy definition."
                }]
            }

        clarification_prompt = self._schema_limitation_prompt(original_question)
        if clarification_prompt:
            return {
                "current_sql": "",
                "sql_confidence": 0.0,
                "sql_reasoning": "The current schema lacks the fact fields required for this request.",
                "clarification_prompt": clarification_prompt,
                "reasoning_steps": [{
                    "step": "GENERATE",
                    "status": "warning",
                    "detail": "Detected a request whose required facts are unavailable or unpopulated in the current client schema."
                }]
            }

        clarification_prompt = self._profit_margin_clarification_prompt(original_question)
        if clarification_prompt:
            return {
                "current_sql": "",
                "sql_confidence": 0.0,
                "sql_reasoning": "True-cost availability must be clarified before generating SQL.",
                "clarification_prompt": clarification_prompt,
                "reasoning_steps": [{
                    "step": "GENERATE",
                    "status": "warning",
                    "detail": "Detected unresolved proxy requirement for profit-margin request."
                }]
            }

        # Always include ALL critical columns in schema context - VMB + AppMasterDB
        critical_columns = """

CRITICAL COLUMNS - ALWAYS USE THESE (do not say INSUFFICIENT_SCHEMA):
=============================================================================
TABLE: WellMonitoringReport
  - Column 'well_name_after_spud' (nvarchar): Official well name after spud
  - Column 'pdo_well_id' (nvarchar): Unique PDO well ID - use for counting wells
  - Column 'rig_no' (nvarchar): Drilling rig identifier (e.g., NL0010, NF0010)
  - Column 'well_location' (nvarchar): Geographic location code
  - Column 'Cluster' (nvarchar): Operational cluster - 'Nimr' or 'Marmul'
  - Column 'well_type' (nvarchar): Well type (ESP, OP, WI, PCP)
  - Column 'buffer_status' (nvarchar): CRITICAL WELL STATUS - values: 'drilled', 'ROL', 'Buffer1', 'Buffer2', 'Error', NULL
    * 'ROL' = Rig On Location - well is actively being drilled (HIGH RISK/CRITICAL)
    * 'drilled' = completed
    * 'Buffer1', 'Buffer2' = waiting in queue
    * When user asks "CRITICAL risk wells" -> use: buffer_status = 'ROL'
  - Column 'ohl_progress' (decimal): OHL completion progress (0-100)
  - Column 'over_all_progress_percentages' (decimal): Overall progress 0-1 scale, multiply by 100 for %
  - Column 'moc_raised' (nvarchar): MOC raised status - only use when user asks about MOC explicitly!
  - Column 'moc_approved' (nvarchar): MOC approved status - only use when user asks about MOC explicitly!

  # VMB Date Columns (for KPI calculations):
  - Column 'flaf_issue_date' (date): Date FLAF was issued (NOT IFC!)
  - Column 'actual_rig_on_date' (date): Date rig arrived (Spud date) - USE for spud-related queries
  - Column 'actual_rig_off_date' (date): Date rig departed
  - Column 'actual_start_date' (date): Generic work start date (different from rig_on_date!)
  - Column '[actual_comm._start_date]' (date): IFC date - Initial For Construction / commissioning START
  - Column 'actual_comm_finish_date_with_in_2_days_from_actual_engg_completion_date' (date): Commissioning finish
  - Column 'actual_eng_completion_date' (date): Engineering completion date
  - Column 'wellpad_handover_2_from_hoist_fbu_rsr_off_date' (date): Wellpad handover date
  - Column 'flowline_construction_progress' (decimal): Flowline completion - 0-1 SCALE (0.5 = 50%, NOT 50!)
  - Column '[latest_exp.rig_on_location_sap_data] (date): TENTATIVE rig-on date from SAP (use brackets!)
  - Column 'location_pegged_date' (date): Date location was pegged

  # CRITICAL DATE LOGIC:
  - Spud = actual_rig_on_date (rig arrival)
  - IFC = [actual_comm._start_date] (commissioning start - NOT flaf_issue_date!)

TABLE: Job_Progress_Report_GB
  - Column '[Well ID]' (nvarchar): Well ID with brackets! Join to WellMonitoringReport.pdo_well_id
  - Column '[Well Name / Project Name]' (nvarchar): Well or project name
  - Column '[Week-1 Plan %]' (decimal): Week 1 planned progress
  - Column '[Week-1 Actual %]' (decimal): Week 1 actual progress
  - Column '[Week-2 Plan %]', '[Week-2 Actual %]'
  - Column '[Week-3 Plan %]', '[Week-3 Actual %]'
  - Column '[Week-4 Plan %]', '[Week-4 Actual %]'
  - Column '[Week-5 Plan %]', '[Week-5 Actual %]'
  - Column '[Current Month Plan %]' (decimal): Total month planned
  - Column '[Current Month Actual %]' (decimal): Total month actual
  - Column '[Purpose Value]' (decimal): Monetary purpose value

TABLE: Revenue
  - Column 'Well_ID' (nvarchar): Join to WellMonitoringReport.pdo_well_id
  - Column 'rigcode' (nvarchar): RIG CODE - use for NL0010, NF0010 filtering (NOT well_location!)
  - Column 'planned_purpose_value' (nvarchar): Planned value - CAST to DECIMAL before SUM!
  - Column 'actual_purpose_value' (nvarchar): Actual value - CAST to DECIMAL before SUM!

TABLE: PH_Productivity
  - Column '[PH Name]' (nvarchar): QHSE Supervisor name
  - Column '[Avg_Productivity_Pct]' (decimal): Productivity = (QtyPerHour/Norms)*100

TABLE: vw_JOB_COST
  - Column '[Well ID]' (nvarchar): Well identifier
  - Column '[Project]' (nvarchar): Rig code from Revenue.rigcode
  - Column '[crew code]' (nvarchar): Crew identifier
=============================================================================
"""

        schema_context = state.get("schema_context", "")
        # Always add critical columns (append to ensure they're available)
        schema_context = schema_context + critical_columns

        try:
            sql_result = self.sql_agent(
                neo4j_schema_context=schema_context,
                user_question=effective_question,
                query_type=state["intent_data"].get("query_type", "general"),
            )

            log.info(f"   Generated SQL: {sql_result.sql_query[:200]}")

            return {
                "current_sql": sql_result.sql_query,
                "sql_confidence": sql_result.confidence,
                "sql_reasoning": sql_result.reasoning,
                # CRITICAL: Always clear clarification_prompt so stale state
                # from a prior turn doesn't hijack route_after_sql.
                "clarification_prompt": "",
                "reasoning_steps": [{
                    "step": "GENERATE",
                    "status": "success" if sql_result.confidence > 0.5 else "warning",
                    "detail": f"Sql: {sql_result.sql_query[:100]}...",
                    "duration_ms": 1500
                }]
            }
        except Exception as e:
            # Handle hallucination or failure
            log.error(f"   ! SQL GENERATION FAILED: {e}")
            return {"current_sql": "", "sql_confidence": 0, "reasoning_steps": [
                {"step": "GENERATE", "status": "error", "detail": str(e)}
            ]}

    def execute_sql(self, state: AgentState) -> dict:
        """Validate and execute SQL query securely."""
        log.info("--- GRAPH STEP: EXECUTE SQL ---")
        sql = state.get("current_sql", "")
        if not sql:
            log.warning("   ! No SQL in state")
            return {"execution_error": "No SQL generated."}

        question = state["messages"][-1].content
        try:
            exec_result = self.validator_agent.validate_and_execute(
                sql=sql,
                schema_context=state.get("schema_context", ""),
                original_question=question,
                query_type=state["intent_data"].get("query_type", "general"),
            )

            if exec_result.error:
                 return {
                     "execution_error": exec_result.error,
                     "reasoning_steps": [{
                         "step": "EXECUTE",
                         "status": "error",
                         "detail": exec_result.error
                     }]
                 }

            # Auto-expand: if count is small (<= 25), fetch actual wells
            rows = exec_result.rows
            columns = exec_result.columns
            should_expand = False

            if len(columns) == 1 and len(rows) == 1:
                # Check if this is a count query
                first_col_lower = columns[0].lower() if columns else ""
                if 'count' in first_col_lower or 'wells' in first_col_lower:
                    try:
                        count_val = int(rows[0][0])
                        # If count is small, fetch actual wells
                        if count_val > 0 and count_val <= 25:
                            should_expand = True
                            log.info(f"   ! Small count detected ({count_val}), fetching well details...")
                            # Try to generate a follow-up query to get wells
                            expand_sql = self._generate_well_details_sql(sql, state.get("schema_context", ""))
                            if expand_sql and expand_sql != sql:
                                exp_result = self.validator_agent.validate_and_execute(
                                    sql=expand_sql,
                                    schema_context=state.get("schema_context", ""),
                                    original_question=question,
                                    query_type="single_table",
                                )
                                if not exp_result.error and exp_result.rows:
                                    # Replace single count with well details
                                    rows = exp_result.rows
                                    columns = exp_result.columns
                                    log.info(f"   ! Expanded to {len(rows)} well details")
                    except (ValueError, TypeError):
                        pass

            return {
                "current_sql": exec_result.sql_query, # might be healed
                "columns": columns,
                "rows": rows,
                "total_rows": len(rows),
                "execution_error": None,
                "reasoning_steps": [{
                    "step": "EXECUTE",
                    "status": "success",
                    "detail": f"Returned {len(rows)} rows. Cols: {columns}",
                }]
            }
        except Exception as e:
             return {"execution_error": str(e)}

    def _generate_well_details_sql(self, count_sql: str, schema_context: str) -> str:
        """Generate SQL to fetch actual well details from a count query."""
        import re
        # Extract WHERE clause from count query
        where_match = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)', count_sql, re.IGNORECASE | re.DOTALL)
        where_clause = where_match.group(1) if where_match else ""

        # Find table name
        from_match = re.search(r'FROM\s+\[?(\w+)\]?', count_sql, re.IGNORECASE)
        table_name = from_match.group(1) if from_match else "WellMonitoringReport_Latest"

        # Build well details query
        detail_cols = ["pdo_well_id", "well_name_after_spud", "rig_no", "over_all_progress_percentages"]

        # Check which columns exist in the table
        valid_cols = []
        for col in detail_cols:
            if col.lower() in schema_context.lower() or col in ["pdo_well_id", "well_name_after_spud", "rig_no", "over_all_progress_percentages"]:
                valid_cols.append(col)

        if not valid_cols:
            valid_cols = ["pdo_well_id", "well_name_after_spud"]

        # Use the same WHERE clause but add LIMIT
        detail_sql = f"SELECT TOP 30 {', '.join(['[' + c + ']' for c in valid_cols])} FROM {table_name}"
        if where_clause:
            detail_sql += f" WHERE {where_clause}"

        # Add ORDER BY progress if available
        if 'progress' in valid_cols:
            detail_sql += " ORDER BY over_all_progress_percentages DESC"

        return detail_sql

    def analyze_data(self, state: AgentState) -> dict:
        """Check if data is a 1D list needing follow-up vs standard metric data."""
        log.info("--- GRAPH STEP: ANALYZE DATA ---")
        if state.get("execution_error"):
            log.warning(f"   ! Error found: {state['execution_error']}")
            # Skip analysis if error
            return {"requires_followup": False}

        rows = state.get("rows", [])
        columns = state.get("columns", [])

        # Heuristic for "List" scenario: Single column, multiple rows, string type
        # Or a few columns but mostly identifying info, no aggregations
        requires_followup = False
        followup_prompt = ""

        if len(columns) == 1 and len(rows) > 0 and isinstance(rows[0][0], str):
            requires_followup = True
            followup_prompt = f"Here is the list of {columns[0]}s you requested. Which one would you like to explore further?"

        return {
            "requires_followup": requires_followup,
            "followup_prompt": followup_prompt,
            "reasoning_steps": [{
                "step": "ANALYZE",
                "status": "success",
                "detail": f"Data shape: {len(rows)} by {len(columns)}. Followup Required: {requires_followup}"
            }]
        }

    def route_after_analysis(self, state: AgentState) -> str:
        """Route to chart generator or conversational follow-up."""
        if state.get("execution_error"):
            return "error"
        if state.get("requires_followup"):
            return "followup"
        return "chart"

    def conversational_followup(self, state: AgentState) -> dict:
        """Inject the followup prompt into the graph state and answer."""
        rows = state.get("rows", [])
        # Format the list nicely
        list_str = "\\n".join([f"- {r[0]}" for r in rows[:20]])
        if len(rows) > 20:
             list_str += f"\\n... and {len(rows)-20} more."

        message = f"{state['followup_prompt']}\\n\\n{list_str}"

        return {
            "response_type": "text",
            "messages": [AIMessage(content=message)],
            "reasoning_steps": [{
                "step": "FOLLOWUP",
                "status": "success",
                "detail": "Prompted user for drill-down choice."
            }]
        }

    def generate_chart(self, state: AgentState) -> dict:
        """Use ChartAgent to guarantee a visual output."""
        log.info("--- GRAPH STEP: GENERATE CHART ---")
        if state.get("execution_error"):
            log.warning("   ! Skipping chart due to execution error")
            return {}

        question = state["messages"][-1].content
        try:
            chart_config: ChartConfig = self.chart_agent.forward(
                user_question=question,
                sql_query=state.get("current_sql", ""),
                result_columns=state.get("columns", []),
                row_count=state.get("total_rows", 0)
            )

            # If it requires followup, we still render a table or simple KPI
            # The chart agent will figure this out based on row_count and columns.

            return {
                "response_type": "chart",
                "chart_config": asdict(chart_config),
                "reasoning_steps": [{
                    "step": "CHART",
                    "status": "success",
                    "detail": f"Recommended 2D/3D visualization: {chart_config.chart_type}"
                }]
            }
        except Exception as e:
            log.warning(f"Chart gen failed: {e}")
            return {}

    # ── Decision OS Nodes (additive) ─────────────────────────────────────

    def predictive_scan(self, state: AgentState) -> dict:
        """Run predictive engines (Forecast + Julia) for alien-tech insights."""
        log.info("--- GRAPH STEP: PREDICTIVE SCAN ---")
        question = state["messages"][-1].content

        try:
            context = self.predictive_scan_agent.scan(
                question=question,
                sql_rows=state.get("rows", []),
                sql_columns=state.get("columns", []),
            )
            return {
                "predictive_context": context,
                "reasoning_steps": [{
                    "step": "PREDICTIVE_SCAN",
                    "status": "success" if context.get("scan_status") != "unavailable" else "warning",
                    "detail": f"Scan status: {context.get('scan_status', 'unknown')}",
                }]
            }
        except Exception as e:
            log.warning(f"   ! Predictive scan failed: {e}")
            return {
                "predictive_context": {"scan_status": "unavailable"},
                "reasoning_steps": [{
                    "step": "PREDICTIVE_SCAN",
                    "status": "error",
                    "detail": f"Scan failed: {e}",
                }]
            }

    def compose_public_answer(self, state: AgentState) -> dict:
        """Compose the executive-facing predictive answer."""
        log.info("--- GRAPH STEP: COMPOSE PUBLIC ANSWER ---")
        question = state["messages"][-1].content

        try:
            result = self.public_response_agent.compose_predictive_answer(
                question=question,
                sql_rows=state.get("rows", []),
                sql_columns=state.get("columns", []),
                predictive_context=state.get("predictive_context", {}),
            )

            answer_text = result.get("answer_text", "Analysis complete.")
            risk_label = result.get("risk_label", "WATCH")
            predictive_summary = result.get("predictive_summary", {})

            return {
                "response_type": "predictive",
                "answer_text": answer_text,
                "risk_label": risk_label,
                "predictive_summary": predictive_summary,
                "messages": [AIMessage(content=answer_text)],
                "reasoning_steps": [{
                    "step": "PUBLIC_RESPONSE",
                    "status": "success",
                    "detail": f"Predictive answer composed. Risk: {risk_label}",
                }]
            }
        except Exception as e:
            log.warning(f"   ! Public response failed: {e}")
            fallback = "Predictive analysis complete. Please review the data results."
            return {
                "response_type": "predictive",
                "answer_text": fallback,
                "risk_label": "WATCH",
                "predictive_summary": {},
                "messages": [AIMessage(content=fallback)],
                "reasoning_steps": [{
                    "step": "PUBLIC_RESPONSE",
                    "status": "warning",
                    "detail": f"Fallback used: {e}",
                }]
            }
