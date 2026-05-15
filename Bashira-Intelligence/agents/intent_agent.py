"""
Intent Agent — Entity extraction + query classification
========================================================
Lightweight DSPy module that extracts entities, identifies
required columns, and classifies query type BEFORE retrieval.
This guides downstream agents for more targeted results.
"""

import re
import dspy
import logging
from dataclasses import dataclass, field
from retrieval.abbreviation_map import expand_query, get_column_name_hints

log = logging.getLogger("bashira.intent")


# ── Data Classes ─────────────────────────────────────────────────────────

@dataclass
class IntentResult:
    """Structured intent extracted from user question."""
    original_question: str
    expanded_question: str
    entities: list[str] = field(default_factory=list)
    column_hints: list[str] = field(default_factory=list)
    query_type: str = "single_table"
    reasoning: str = ""


# ── DSPy Signature ───────────────────────────────────────────────────────

class IntentSignature(dspy.Signature):
    """Analyze a well monitoring question to extract entities and classify the query type.
    You are an expert in oil & gas well monitoring databases."""

    user_question = dspy.InputField(
        desc="The user's natural language question about well monitoring data."
    )
    available_tables = dspy.InputField(
        desc="List of available database tables for context."
    )

    entities = dspy.OutputField(
        desc="Comma-separated list of key entities mentioned "
             "(well names, clusters, rig numbers, dates, metrics). "
             "Example: 'Nimr cluster, rig 702, SCR number, progress'"
    )
    query_type = dspy.OutputField(
        desc="Exactly one of: single_table, multi_table_join, aggregation, trend, ranking, comparison"
    )
    target_tables = dspy.OutputField(
        desc="Comma-separated list of most likely target table names from the available tables."
    )


# ── Agent ────────────────────────────────────────────────────────────────

AVAILABLE_TABLES = (
    "WellMonitoringReport, WellMonitoringReport_Latest, WMR_Full, "
    "Job_Progress_Report_GB, ActivityTaskPlan, task_daily, Revenue, "
    "Employee, PH_PRODUCTIVITY_WEEKLY_REPORT, SAP_DRILLING_SEQUENCE, "
    "WBS_Master_Tracker_, ProjectIDs, schema_metadata"
)


class IntentAgent(dspy.Module):
    """Extract structured intent from user question."""

    def __init__(self):
        super().__init__()
        self.classify = dspy.ChainOfThought(IntentSignature)

    def forward(self, user_question: str) -> IntentResult:
        """
        Analyze the question and return structured IntentResult.
        Combines DSPy classification with rule-based abbreviation expansion.
        """
        # 1. Expand abbreviations
        expanded = expand_query(user_question)
        column_hints = get_column_name_hints(user_question)

        # 2. DSPy classification
        try:
            pred = self.classify(
                user_question=user_question,
                available_tables=AVAILABLE_TABLES,
            )

            entities = [e.strip() for e in pred.entities.split(",") if e.strip()]
            query_type = pred.query_type.strip().lower()
            valid_types = {
                "single_table", "multi_table_join", "aggregation",
                "trend", "ranking", "comparison",
            }
            if query_type not in valid_types:
                query_type = "single_table"

            return IntentResult(
                original_question=user_question,
                expanded_question=expanded,
                entities=entities,
                column_hints=column_hints,
                query_type=query_type,
                reasoning=getattr(pred, "rationale", ""),
            )

        except Exception as e:
            log.warning("Intent classification failed: %s. Using defaults.", e)
            return IntentResult(
                original_question=user_question,
                expanded_question=expanded,
                column_hints=column_hints,
                query_type="single_table",
                reasoning=f"Fallback: {e}",
            )
