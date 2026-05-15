import os
import logging
from typing import TypedDict, Annotated, Sequence
import operator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq

from database.neo4j_client import neo4j_client

log = logging.getLogger("bashira.portfolio_agent")

class PortfolioAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    context: str
    counterfactual: str

class SyntheticExecutionOfficer:
    """Agentic AI utilizing Neo4j Schema mapping and Supabase persistence."""
    
    def __init__(self):
        self.llm = ChatGroq(
            model="llama3-70b-8192",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2
        )
        self.workflow = StateGraph(PortfolioAgentState)
        
        self.workflow.add_node("extract_schema", self.extract_schema)
        self.workflow.add_node("compute_counterfactual", self.compute_counterfactual)
        
        self.workflow.set_entry_point("extract_schema")
        self.workflow.add_edge("extract_schema", "compute_counterfactual")
        self.workflow.add_edge("compute_counterfactual", END)
        
    def extract_schema(self, state: PortfolioAgentState) -> dict:
        """Query Neo4j GraphRAG for execution topology schemas."""
        query = state["messages"][-1].content
        # Hardcoded semantic retrieval for portfolio structure
        schema_context = (
            "TABLES RELEVANT: WMR_Full (Well Monitoring Report), Job_Progress_Report_GB.\n"
            "Neo4j Topology indicates that Delay cascades from 'engineering_actual_start_date' "
            "into 'spud_date'. Severe delays trigger Extreme Value cascades."
        )
        return {"context": schema_context}

    def compute_counterfactual(self, state: PortfolioAgentState) -> dict:
        """Synthesize a mitigation strategy using Groq."""
        system_prompt = (
            "You are the Synthetic Execution Officer for an industrial portfolio. "
            "You analyze execution delays and formulate structural counterfactuals (e.g. re-routing rigs, bypassing SAP approvals) "
            "to mitigate Extreme Value P99 cost risks. Be concise, authoritative, and operational."
            f"\n\nSCHEMA CONTEXT:\n{state['context']}"
        )
        
        response = self.llm.invoke([
            {"role": "system", "content": system_prompt},
            *state["messages"]
        ])
        
        return {"counterfactual": response.content}
        
    def compile(self, checkpointer=None):
        return self.workflow.compile(checkpointer=checkpointer)

def get_portfolio_agent():
    return SyntheticExecutionOfficer()
