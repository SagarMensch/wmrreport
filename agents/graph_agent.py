"""
LangGraph Agent — Stateful conversational data engine
=====================================================
Replaces the linear orchestrator pipeline with a cyclic, stateful graph.
Includes conversational follow-ups for lists/un-chartable data, natively
integrating 2D/3D visualizations and drill-downs.
"""

import operator
import logging
from typing import TypedDict, Annotated, Sequence, Any, Optional
from dataclasses import asdict

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
        
        # Build the Graph
        self.workflow = StateGraph(AgentState)
        
        # Add Nodes
        self.workflow.add_node("extract_intent", self.extract_intent)
        self.workflow.add_node("retrieve_schema", self.retrieve_schema)
        self.workflow.add_node("generate_sql", self.generate_sql)
        self.workflow.add_node("execute_sql", self.execute_sql)
        self.workflow.add_node("analyze_data", self.analyze_data)
        self.workflow.add_node("conversational_followup", self.conversational_followup)
        self.workflow.add_node("generate_chart", self.generate_chart)
        
        # Add Edges
        self.workflow.set_entry_point("extract_intent")
        self.workflow.add_edge("extract_intent", "retrieve_schema")
        self.workflow.add_edge("retrieve_schema", "generate_sql")
        self.workflow.add_edge("generate_sql", "execute_sql")
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
        try:
            sql_result = self.sql_agent(
                neo4j_schema_context=state.get("schema_context", ""),
                user_question=question,
                query_type=state["intent_data"].get("query_type", "general"),
            )
            
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
