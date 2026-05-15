"""
Public Response Composer — Executive-facing answer builder
==========================================================
Composes clean, non-technical answers from SQL results + predictive context.

For sql_only questions: existing reasoning pipeline handles it (no change).
For predictive questions: builds the "alien reasoning" answer card content.

Never exposes chain-of-thought, internal SQL, or debugging info.
"""

import logging
import dspy

log = logging.getLogger("bashira.public_response")


class PredictiveAnswerSignature(dspy.Signature):
    """Compose an executive-facing predictive intelligence briefing."""
    question: str = dspy.InputField(desc="The user's original question")
    sql_summary: str = dspy.InputField(desc="Summary of SQL query results (data from database)")
    forecast_data: str = dspy.InputField(desc="Forecast engine output: portfolio summary, progress, delays")
    causal_data: str = dspy.InputField(desc="Causal analysis: root cause drivers and their impact")
    intervention_data: str = dspy.InputField(desc="Ranked interventions: best actions and expected delta")

    answer_text: str = dspy.OutputField(desc="A 3-5 sentence executive briefing answering the question. Use specific numbers. Never mention SQL, tables, or internal systems.")
    risk_label: str = dspy.OutputField(desc="One of: ON_TRACK, WATCH, AT_RISK, CRITICAL")


class PublicResponseAgent:
    """Composes public answers from SQL results + predictive context."""

    def __init__(self):
        self._composer = dspy.Predict(PredictiveAnswerSignature)

    def compose_predictive_answer(
        self,
        question: str,
        sql_rows: list = None,
        sql_columns: list = None,
        predictive_context: dict = None,
    ) -> dict:
        """
        Build the predictive answer card content.

        Returns:
            answer_text: Executive briefing text
            risk_label: ON_TRACK | WATCH | AT_RISK | CRITICAL
            predictive_summary: Structured scan results for the frontend card
        """
        log.info("--- PUBLIC RESPONSE: Composing predictive answer ---")

        pc = predictive_context or {}

        if pc.get("deterministic_answer"):
            summary_lines = pc.get("summary_lines", {}) or {}
            return {
                "answer_text": pc.get("deterministic_answer", "Analysis complete."),
                "risk_label": pc.get("deterministic_risk_label", "WATCH"),
                "predictive_summary": {
                    "forecast_line": summary_lines.get("forecast_line", ""),
                    "risk_line": summary_lines.get("risk_line", ""),
                    "causal_line": summary_lines.get("causal_line", ""),
                    "intervention_line": summary_lines.get("intervention_line", ""),
                    "scan_status": pc.get("scan_status", "partial"),
                },
            }

        # Build SQL summary from rows
        sql_summary = self._build_sql_summary(sql_rows, sql_columns)

        # Build forecast string
        forecast = pc.get("forecast", {})
        forecast_str = (
            f"Total wells: {forecast.get('total_wells', 'N/A')}. "
            f"Avg progress: {forecast.get('avg_progress', 'N/A')}%. "
            f"Delayed wells: {forecast.get('delayed_wells', 'N/A')}. "
            f"On track: {forecast.get('on_track_wells', 'N/A')}."
        ) if forecast else "Forecast data unavailable."

        # Build causal string
        causal_drivers = pc.get("causal", [])
        causal_str = "; ".join([
            f"{d.get('feature', '?')} ({d.get('impact_days', 0):.1f} days impact)"
            for d in causal_drivers
        ]) if causal_drivers else "Causal analysis unavailable."

        # Build intervention string
        interventions = pc.get("interventions", [])
        intervention_str = "; ".join([
            f"{i.get('action', '?')} on {i.get('well_name', '?')} (saves {abs(i.get('delta_days', 0)):.1f} days)"
            for i in interventions
        ]) if interventions else "No interventions ranked."

        try:
            result = self._composer(
                question=question,
                sql_summary=sql_summary,
                forecast_data=forecast_str,
                causal_data=causal_str,
                intervention_data=intervention_str,
            )

            answer_text = result.answer_text.strip()
            risk_label = result.risk_label.strip().upper()

            # Validate risk_label
            if risk_label not in ("ON_TRACK", "WATCH", "AT_RISK", "CRITICAL"):
                risk_label = "WATCH"

            log.info(f"   ✓ Answer composed, risk: {risk_label}")

        except Exception as e:
            log.warning(f"   ! LLM composition failed: {e}. Using template fallback.")
            answer_text = self._template_fallback(question, forecast, causal_drivers, interventions)
            risk_label = "WATCH"

        # Build structured predictive summary for the frontend card
        predictive_summary = {
            "forecast_line": self._build_forecast_line(forecast),
            "risk_line": self._build_risk_line(pc.get("risk", {})),
            "causal_line": self._build_causal_line(causal_drivers),
            "intervention_line": self._build_intervention_line(interventions),
            "scan_status": pc.get("scan_status", "unavailable"),
        }

        return {
            "answer_text": answer_text,
            "risk_label": risk_label,
            "predictive_summary": predictive_summary,
        }

    def _build_sql_summary(self, rows: list, columns: list) -> str:
        """Summarize SQL results into a readable string."""
        if not rows or not columns:
            return "No SQL data available."

        if len(rows) == 1 and len(columns) >= 1:
            parts = [f"{columns[i]}: {rows[0][i]}" for i in range(min(4, len(columns)))]
            return ". ".join(parts)

        return f"{len(rows)} records across {len(columns)} dimensions: {', '.join(columns[:5])}"

    def _build_forecast_line(self, forecast: dict) -> str:
        if not forecast:
            return ""
        progress = forecast.get("avg_progress", 0)
        delayed = forecast.get("delayed_wells", 0)
        total = forecast.get("total_wells", 0)
        return f"{progress:.0f}% avg progress across {total} wells · {delayed} delayed"

    def _build_risk_line(self, risk: dict) -> str:
        if not risk:
            return ""
        count = risk.get("at_risk_count", 0)
        top = risk.get("top_at_risk", [])
        if top:
            worst = top[0]
            return f"{count} wells at risk · Worst: {worst.get('well_name', '?')} ({worst.get('delay_days', 0):.0f}d delay)"
        return f"{count} wells at risk"

    def _build_causal_line(self, causal: list) -> str:
        if not causal:
            return ""
        top = causal[0]
        return f"Top driver: {top.get('feature', '?')} ({top.get('impact_days', 0):.1f}d impact)"

    def _build_intervention_line(self, interventions: list) -> str:
        if not interventions:
            return ""
        best = interventions[0]
        return f"Best fix: {best.get('action', '?')} → saves {abs(best.get('delta_days', 0)):.1f} days"

    def _template_fallback(self, question: str, forecast: dict, causal: list, interventions: list) -> str:
        """Deterministic template when LLM fails."""
        parts = []
        if forecast:
            parts.append(
                f"Portfolio tracking at {forecast.get('avg_progress', 0):.0f}% average progress "
                f"across {forecast.get('total_wells', 0)} wells."
            )
            if forecast.get("delayed_wells", 0) > 0:
                parts.append(f"{forecast['delayed_wells']} wells are currently delayed.")

        if causal:
            top = causal[0]
            parts.append(f"The primary delay driver is {top.get('feature', 'unknown')} "
                         f"({top.get('impact_days', 0):.1f} days impact per unit).")

        if interventions:
            best = interventions[0]
            parts.append(f"Recommended action: {best.get('action', 'N/A')} on "
                         f"{best.get('well_name', 'N/A')} to recover "
                         f"{abs(best.get('delta_days', 0)):.1f} days.")

        return " ".join(parts) if parts else "Predictive analysis complete. Review the scan details below."
