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
        
        # Add Edges — resolve_context runs FIRST
        self.workflow.set_entry_point("resolve_context")
        self.workflow.add_edge("resolve_context", "extract_intent")
        self.workflow.add_edge("extract_intent", "retrieve_schema")
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
        self.workflow.add_edge("execute_sql", "analyze_data")
        
        # Conditional Edge after Data Analysis
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

    # ── Nodes ────────────────────────────────────────────────────────────

    def resolve_context(self, state: AgentState) -> dict:
        """Rewrite vague follow-ups into self-contained questions.
        
        SAFE DESIGN:
        - Only activates for SHORT messages (< 12 words) that contain vague references
        - Specific questions pass through UNTOUCHED
        - If rewrite fails, falls back to original question
        """
        messages = state["messages"]
        latest = messages[-1].content.strip()
        
        # Safety check 1: Only 1 message in history → nothing to resolve, skip
        if len(messages) <= 1:
            log.info("--- CONTEXT: Single message, skipping resolution ---")
            return {"reasoning_steps": [{"step": "CONTEXT", "status": "success", "detail": "Direct question — no history needed."}]}
        
        # Safety check 2: Long specific question → already clear, skip
        word_count = len(latest.split())
        if word_count > 12:
            log.info(f"--- CONTEXT: Specific question ({word_count} words), passing through ---")
            return {"reasoning_steps": [{"step": "CONTEXT", "status": "success", "detail": f"Clear question ({word_count} words) — no rewrite needed."}]}
        
        # Safety check 3: Does it contain vague references?
        if not _VAGUE_PATTERNS.search(latest):
            log.info(f"--- CONTEXT: No vague patterns detected, passing through ---")
            return {"reasoning_steps": [{"step": "CONTEXT", "status": "success", "detail": "No vague references — no rewrite needed."}]}
        
        # Build conversation summary from last 10 messages
        log.info(f"--- CONTEXT: Vague follow-up detected, resolving... ---")
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
        if state.get("sql_confidence", 0) < 0.95:
            return "clarify"
        return "execute"

    def clarification_node(self, state: AgentState) -> dict:
        """Handle low-confidence queries conversationally."""
        log.info("--- GRAPH STEP: CLARIFICATION ---")
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

    def extract_intent(self, state: AgentState) -> dict:
        """Extract entities and infer column hits."""
        latest_message = state["messages"][-1].content
        session_context = state.get("session_context", {})
        
        log.info(f"--- GRAPH STEP: EXTRACT INTENT ---")
        log.info(f"Question: {latest_message}")
        
        # Use session context to enhance drill-down understanding
        context_hint = ""
        if session_context.get("last_table") and ("drill" in latest_message.lower() or latest_message.replace("Drill down on ", "").isdigit()):
            context_hint = f" Previous query was on table {session_context['last_table']}. "
            log.info(f"   Using context: {session_context.get('last_table')}")
        
        try:
            intent = self.intent_agent(user_question=context_hint + latest_message)
            log.info(f"   ✓ Intent extracted: {intent.query_type}")
            return {
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
                    "detail": f"Detected {intent.query_type} query with entities: {intent.entities}",
                    "duration_ms": 100
                }]
            }
        except Exception as e:
             return {"reasoning_steps": [{"step": "INTENT", "status": "error", "detail": str(e)}]}

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
                user_question=question,
                query_type=state["intent_data"].get("query_type", "general"),
            )
            
            log.info(f"   Generated SQL: {sql_result.sql_query[:200]}")
            
            return {
                "current_sql": sql_result.sql_query,
                "sql_confidence": sql_result.confidence,
                "sql_reasoning": sql_result.reasoning,
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
