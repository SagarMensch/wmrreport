"""
Predictive Scan Agent
=====================
ONLY runs when response_mode == "predictive".
For sql_only questions, this node is skipped entirely.

Uses the CPU ML stack first:
  - ForecastEngine for portfolio/well forecast + operational risk context
  - CPU ML microservice on port 8050 for delay probabilities, SHAP insights,
    and per-well causal intervention hints

Julia is intentionally not used in the default predictive path right now.
"""

import logging
from collections import Counter
from typing import Any

import requests

log = logging.getLogger("bashira.predictive_scan")

ML_SERVICE_BASE = "http://127.0.0.1:8050"
ML_REQUEST_TIMEOUT_SECONDS = 20


class PredictiveScanAgent:
    """Collects predictive intelligence from the CPU ML stack."""

    def __init__(self):
        self._forecast_engine = None

    def _get_forecast_engine(self):
        """Lazy-load ForecastEngine (same process)."""
        if self._forecast_engine is None:
            try:
                from forecast_engine import ForecastEngine
                self._forecast_engine = ForecastEngine()
                log.info("   ✓ ForecastEngine loaded for predictive scan")
            except Exception as e:
                log.warning(f"   ! ForecastEngine unavailable: {e}")
        return self._forecast_engine

    @staticmethod
    def _question_family(question: str) -> str:
        q = question.strip().lower()
        if "probability of delay" in q and "project" in q:
            return "delay_probability"
        if "immediate intervention" in q or "need immediate" in q:
            return "immediate_intervention"
        if "actions should management take today" in q or "management take today" in q:
            return "management_actions"
        if "predictive insights" in q or "past projects" in q:
            return "predictive_insights"
        if "key drivers" in q or "root causes" in q or "drivers of delay" in q:
            return "delay_drivers"
        return "generic"

    @staticmethod
    def _risk_label_from_value(value: float) -> str:
        if value >= 70:
            return "CRITICAL"
        if value >= 55:
            return "AT_RISK"
        if value >= 35:
            return "WATCH"
        return "ON_TRACK"

    def _call_ml_json(self, path: str) -> dict | None:
        try:
            response = requests.get(
                f"{ML_SERVICE_BASE}{path}",
                timeout=ML_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log.warning(f"   ! CPU ML request failed for {path}: {e}")
            return None

    def _collect_top_well_ml_insights(self, at_risk_wells: list[dict]) -> dict[str, Any]:
        causal_counter: Counter[str] = Counter()
        causal_delay: dict[str, float] = {}
        insight_counter: Counter[str] = Counter()
        interventions: list[dict[str, Any]] = []
        well_details: list[dict[str, Any]] = []

        for well in at_risk_wells[:3]:
            well_id = str(well.get("well_id", "")).strip()
            if not well_id:
                continue

            payload = self._call_ml_json(f"/ml/forecast/{well_id}")
            if not payload or payload.get("error"):
                continue

            hidden_insights = payload.get("hidden_insights", []) or []
            causal_intelligence = payload.get("causal_intelligence", {}) or {}
            root_causes = causal_intelligence.get("root_causes", []) or []
            interventions_available = causal_intelligence.get("interventions_available", {}) or {}

            for insight in hidden_insights:
                factor = insight.get("factor", "").strip()
                if factor:
                    insight_counter[factor] += 1

            for cause in root_causes:
                factor = cause.get("factor", "").strip()
                if not factor:
                    continue
                causal_counter[factor] += 1
                causal_delay[factor] = max(
                    float(causal_delay.get(factor, 0)),
                    float(cause.get("delay_days", 0) or 0),
                )

            top_rigs = interventions_available.get("rigs", []) or []
            if top_rigs:
                interventions.append({
                    "well_name": well.get("well_name", ""),
                    "action": f"Prioritize strong rig support from {top_rigs[0]}",
                    "delta_days": -max(float(causal_delay.get(next(iter(causal_delay), ""), 0)), 2.0),
                })
            if interventions_available.get("can_expedite"):
                interventions.append({
                    "well_name": well.get("well_name", ""),
                    "action": "Expedite material availability",
                    "delta_days": -3.0,
                })

            well_details.append({
                "well_id": well_id,
                "well_name": well.get("well_name", ""),
                "progress": well.get("progress", 0),
                "delay": well.get("delay_days", 0),
                "best_action": interventions[0]["action"] if interventions else "",
                "root_causes": [c.get("factor", "") for c in root_causes[:2]],
            })

        causal = [
            {
                "feature": factor,
                "impact_days": round(causal_delay.get(factor, 0), 1),
                "source_table": "CPU_ML",
                "meaning": "Model-derived causal signal",
            }
            for factor, _ in causal_counter.most_common(3)
        ]
        if not causal:
            causal = [
                {
                    "feature": factor,
                    "impact_days": 0.0,
                    "source_table": "CPU_ML",
                    "meaning": "Model-derived hidden insight",
                }
                for factor, _ in insight_counter.most_common(3)
            ]

        return {
            "causal": causal[:3],
            "interventions": interventions[:3],
            "wells_detail": well_details[:5],
        }

    def _build_deterministic_predictive_answer(self, context: dict[str, Any]) -> tuple[str, str, dict[str, str]]:
        family = context.get("family", "generic")
        forecast = context.get("forecast", {})
        risk = context.get("risk", {})
        project_risks = context.get("project_risks", []) or []
        feature_insights = context.get("feature_insights", []) or []
        causal = context.get("causal", []) or []
        interventions = context.get("interventions", []) or []

        summary = {
            "forecast_line": "",
            "risk_line": "",
            "causal_line": "",
            "intervention_line": "",
        }

        if forecast:
            summary["forecast_line"] = (
                f"{forecast.get('avg_progress', 0):.0f}% avg progress across {forecast.get('total_wells', 0)} wells · "
                f"{forecast.get('delayed_wells', 0)} delayed"
            )
        if risk:
            top = (risk.get("top_at_risk") or [{}])[0]
            summary["risk_line"] = (
                f"{risk.get('at_risk_count', 0)} wells at risk · Worst: "
                f"{top.get('well_name', '?')} ({top.get('delay_days', 0):.0f}d delay)"
            )
        if causal:
            summary["causal_line"] = (
                f"Top driver: {causal[0].get('feature', '?')} "
                f"({causal[0].get('impact_days', 0):.1f}d impact)"
            )
        if interventions:
            summary["intervention_line"] = (
                f"Best fix: {interventions[0].get('action', '?')} "
                f"→ saves {abs(interventions[0].get('delta_days', 0)):.1f} days"
            )

        if family == "delay_probability" and project_risks:
            top_projects = ", ".join(
                f"{p.get('project')} ({p.get('avg_delay_probability_pct', 0):.1f}%)"
                for p in project_risks[:3]
            )
            risk_value = float(project_risks[0].get("avg_delay_probability_pct", 0))
            answer = (
                f"Using the CPU delay-risk model across open wells, the highest project-level delay probabilities are "
                f"{top_projects}. This view uses management project category as the default project grain and summarizes "
                f"modeled stall probability across each category's open wells."
            )
            return answer, self._risk_label_from_value(risk_value), summary

        if family == "immediate_intervention" and project_risks:
            top_projects = ", ".join(
                f"{p.get('project')} ({p.get('critical_wells', 0)} critical wells, {p.get('avg_delay_probability_pct', 0):.1f}% avg probability)"
                for p in project_risks[:3]
            )
            top_signal = feature_insights[0].get("label", "Current Overall Progress") if feature_insights else "Current Overall Progress"
            answer = (
                f"Immediate intervention is needed in {top_projects}. The model is currently most sensitive to "
                f"{top_signal.lower()}, so management should focus first on those high-risk categories and the worst affected wells."
            )
            return answer, self._risk_label_from_value(float(project_risks[0].get("avg_delay_probability_pct", 0))), summary

        if family == "management_actions":
            top_projects = ", ".join(
                p.get('project') for p in project_risks[:3]
            ) if project_risks else "the highest-risk project categories"
            top_actions = "; ".join(
                i.get("action", "") for i in interventions[:2] if i.get("action")
            )
            if not top_actions and feature_insights:
                top_actions = f"decongest dense clusters and stabilize weak execution momentum in {top_projects}"
            answer = (
                f"Management should act today on {top_projects}. Based on the current CPU risk model, the most practical moves are "
                f"{top_actions}. These actions target the categories and wells with the highest modeled delay pressure."
            )
            risk_anchor = float(project_risks[0].get("avg_delay_probability_pct", 0)) if project_risks else 55.0
            return answer, self._risk_label_from_value(risk_anchor), summary

        if family == "predictive_insights" and feature_insights:
            insights_text = ", ".join(
                f"{item.get('label')} ({item.get('direction')})"
                for item in feature_insights[:3]
            )
            answer = (
                f"Across the historical portfolio used by the CPU model, the strongest predictive signals are {insights_text}. "
                f"These are the factors the model finds most informative when separating higher-risk wells from lower-risk wells."
            )
            return answer, "WATCH", summary

        if family == "delay_drivers" and causal:
            drivers = ", ".join(
                f"{item.get('feature')} ({item.get('impact_days', 0):.1f}d)"
                for item in causal[:3]
            )
            answer = (
                f"The main modeled delay drivers across the current at-risk wells are {drivers}. "
                f"These signals come from the CPU ML stack using well-level risk, hidden insights, and intervention analysis."
            )
            return answer, "WATCH", summary

        answer = (
            f"Portfolio average progress is {forecast.get('avg_progress', 0):.0f}% across {forecast.get('total_wells', 0)} wells, "
            f"with {forecast.get('delayed_wells', 0)} wells currently delayed."
        )
        return answer, self._risk_label_from_value(float(risk.get("at_risk_count", 0) * 10)), summary

    def scan(self, question: str, sql_rows: list = None, sql_columns: list = None) -> dict[str, Any]:
        """
        Run predictive scan and return enriched context.

        Returns a dict with keys:
            forecast:      Portfolio forecast summary (from ForecastEngine)
            risk:          Risk-scored wells (from ForecastEngine)
            causal:        Top model-derived drivers (from CPU ML)
            interventions: Ranked intervention actions (from CPU ML)
            scan_status:   'full' | 'partial' | 'unavailable'
        """
        log.info("--- PREDICTIVE SCAN: Running CPU ML engines ---")
        context = {
            "forecast": {},
            "risk": {},
            "causal": [],
            "interventions": [],
            "wells_detail": [],
            "project_risks": [],
            "feature_insights": [],
            "scan_status": "unavailable",
        }

        family = self._question_family(question)
        context["family"] = family
        scan_parts = 0

        engine = self._get_forecast_engine()
        at_risk = []
        if engine:
            try:
                portfolio = engine.get_portfolio_summary()
                if portfolio:
                    context["forecast"] = {
                        "total_wells": portfolio.get("total_wells", 0),
                        "avg_progress": portfolio.get("avg_progress", 0),
                        "delayed_wells": portfolio.get("delayed_wells", 0),
                        "on_track_wells": portfolio.get("on_track_wells", 0),
                        "risk_summary": portfolio.get("risk_summary", {}),
                    }
                    scan_parts += 1
                    log.info(f"   ✓ Forecast: {portfolio.get('total_wells', 0)} wells scanned")

                if portfolio:
                    at_risk = list(portfolio.get("at_risk_wells", []) or [])

                if not at_risk:
                    well_list = engine.get_well_list()
                    if well_list:
                        at_risk = sorted(
                            [
                                w for w in well_list
                                if str(w.get("risk_tier", "")).upper() in {"CRITICAL", "HIGH_RISK"}
                            ],
                            key=lambda w: float(w.get("risk_score", 0) or 0),
                            reverse=True,
                        )[:5]

                if at_risk:
                    context["risk"] = {
                        "at_risk_count": len(at_risk),
                        "top_at_risk": [
                            {
                                "well_id": w.get("well_id", w.get("pdo_well_id", "")),
                                "well_name": w.get("well_name", ""),
                                "progress": w.get("progress", w.get("progress_pct", 0)),
                                "delay_days": w.get("delay_days", 0),
                                "risk_tier": str(
                                    w.get(
                                        "risk_tier",
                                        "critical" if w.get("delay_days", 0) > 10 else "watch",
                                    )
                                ).lower(),
                            }
                            for w in at_risk
                        ],
                    }
                    scan_parts += 1
                    log.info(f"   ✓ Risk: {len(at_risk)} wells at risk")
            except Exception as e:
                log.warning(f"   ! Forecast scan failed: {e}")

        if family in {"delay_probability", "immediate_intervention", "management_actions"}:
            project_risk_payload = self._call_ml_json("/ml/portfolio/project-delay-probability")
            if project_risk_payload and project_risk_payload.get("rows"):
                context["project_risks"] = project_risk_payload.get("rows", [])
                scan_parts += 1
                log.info(f"   ✓ Project risk: {len(context['project_risks'])} project categories scored")

        if family in {"predictive_insights", "immediate_intervention", "management_actions", "delay_drivers"}:
            insight_payload = self._call_ml_json("/ml/portfolio/feature-insights")
            if insight_payload and insight_payload.get("insights"):
                context["feature_insights"] = insight_payload.get("insights", [])
                scan_parts += 1
                log.info(f"   ✓ Feature insights: {len(context['feature_insights'])} portfolio signals")

        if family in {"delay_drivers", "immediate_intervention", "management_actions"} and at_risk:
            well_ml = self._collect_top_well_ml_insights(at_risk)
            context["causal"] = well_ml.get("causal", [])
            context["interventions"] = well_ml.get("interventions", [])
            context["wells_detail"] = well_ml.get("wells_detail", [])
            if context["causal"] or context["interventions"]:
                scan_parts += 1
                log.info(
                    "   ✓ Top-well ML insights: %s drivers, %s interventions",
                    len(context["causal"]),
                    len(context["interventions"]),
                )

        if scan_parts >= 3:
            context["scan_status"] = "full"
        elif scan_parts >= 1:
            context["scan_status"] = "partial"
        else:
            context["scan_status"] = "unavailable"

        answer_text, risk_label, summary = self._build_deterministic_predictive_answer(context)
        context["deterministic_answer"] = answer_text
        context["deterministic_risk_label"] = risk_label
        context["summary_lines"] = summary

        log.info(f"   ◆ SCAN COMPLETE: status={context['scan_status']}, parts={scan_parts}/4")
        return context
