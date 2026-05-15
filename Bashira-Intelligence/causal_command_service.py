"""
Causal Command Service
======================
Builds a real cross-system well dataset from live SQL Server sources and
combines a fast CPU decision layer with a deeper Bayesian counterfactual layer.
"""

from __future__ import annotations

import copy
import datetime as dt
import threading
import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from causal_confidence import compose_action_status, compose_confidence_label
from causal_scenario_catalog import merge_scenario_catalog
from causal_stan_service import StanCounterfactualService
from causal_workspace_contract import build_analysis_status, build_data_health
from config import settings

warnings.filterwarnings(
    "ignore",
    message="pandas only supports SQLAlchemy connectable",
)

import logging as _logging
_log = _logging.getLogger("bashira.causal")


@dataclass
class TableFrame:
    name: str
    frame: pd.DataFrame
    source: str


class CausalCommandService:
    def __init__(self):
        self.today = pd.Timestamp(dt.date.today())
        self.cache_ttl_seconds = 600
        self._cached_workspace: dict[str, Any] | None = None
        self._cached_at: dt.datetime | None = None
        self._workspace_lock = threading.Lock()
        self._cached_bayesian: dict[str, Any] | None = None
        self._bayesian_started_at: dt.datetime | None = None
        self._bayesian_completed_at: dt.datetime | None = None
        self._bayesian_refresh_in_progress = False
        self._refresh_lock = threading.Lock()
        self._stan_service = StanCounterfactualService()

    def build_workspace(self) -> dict[str, Any]:
        now = dt.datetime.now()
        if (
            self._cached_workspace is not None
            and self._cached_at is not None
            and (now - self._cached_at).total_seconds() < self.cache_ttl_seconds
        ):
            return self._materialize_workspace(self._cached_workspace, now)

        with self._workspace_lock:
            now = dt.datetime.now()
            if (
                self._cached_workspace is not None
                and self._cached_at is not None
                and (now - self._cached_at).total_seconds() < self.cache_ttl_seconds
            ):
                return self._materialize_workspace(self._cached_workspace, now)

            tables = self._load_tables()
            dataset, join_coverage = self._build_feature_dataset(tables)
            cpu_analysis = self._run_fast_cpu_analysis(dataset)
            bayesian = self._current_bayesian_payload()
            workspace = self._assemble_workspace(
                tables=tables,
                dataset=dataset,
                join_coverage=join_coverage,
                cpu_analysis=cpu_analysis,
                bayesian=bayesian,
                now=now,
            )
            self._cached_workspace = workspace
            self._cached_at = now
            self._maybe_start_bayesian_refresh(
                dataset=dataset.copy(deep=True),
                tables=tables,
                join_coverage=join_coverage,
                cpu_analysis=cpu_analysis,
            )
            return self._materialize_workspace(workspace, now)

    def _materialize_workspace(
        self,
        workspace: dict[str, Any],
        now: dt.datetime,
    ) -> dict[str, Any]:
        materialized = copy.deepcopy(workspace)
        age_seconds = 0
        if self._cached_at is not None:
            age_seconds = int(max((now - self._cached_at).total_seconds(), 0))
        status = materialized.setdefault("analysis_status", {})
        status["cache_age_seconds"] = age_seconds
        status["refresh_in_progress"] = self._bayesian_refresh_in_progress
        status["last_bayesian_started_at"] = (
            self._bayesian_started_at.isoformat() if self._bayesian_started_at else None
        )
        status["last_bayesian_completed_at"] = (
            self._bayesian_completed_at.isoformat() if self._bayesian_completed_at else None
        )
        if self._bayesian_refresh_in_progress and materialized["bayesian_analysis"]["status"] != "ok":
            materialized["bayesian_analysis"]["status"] = "warming"
            materialized["bayesian_analysis"]["message"] = (
                "Fast CPU decision layer is ready. Bayesian counterfactual summaries are still refreshing in the background."
            )
        return materialized

    def _current_bayesian_payload(self) -> dict[str, Any]:
        if self._cached_bayesian is not None:
            payload = copy.deepcopy(self._cached_bayesian)
            payload["refresh_in_progress"] = self._bayesian_refresh_in_progress
            payload["started_at"] = self._bayesian_started_at.isoformat() if self._bayesian_started_at else None
            payload["completed_at"] = self._bayesian_completed_at.isoformat() if self._bayesian_completed_at else None
            return payload
        return self._stan_service.pending_payload(
            refresh_in_progress=self._bayesian_refresh_in_progress,
            started_at=self._bayesian_started_at,
            completed_at=self._bayesian_completed_at,
        )

    def _maybe_start_bayesian_refresh(
        self,
        dataset: pd.DataFrame,
        tables: dict[str, TableFrame],
        join_coverage: dict[str, float],
        cpu_analysis: dict[str, Any],
    ) -> None:
        with self._refresh_lock:
            if self._bayesian_refresh_in_progress:
                return
            if self._cached_bayesian is not None and self._bayesian_completed_at is not None:
                age = (dt.datetime.now() - self._bayesian_completed_at).total_seconds()
                if age < self.cache_ttl_seconds:
                    return
            self._bayesian_refresh_in_progress = True
            self._bayesian_started_at = dt.datetime.now()

        thread = threading.Thread(
            target=self._refresh_bayesian_worker,
            kwargs={
                "dataset": dataset,
                "tables": tables,
                "join_coverage": join_coverage,
                "cpu_analysis": cpu_analysis,
            },
            daemon=True,
        )
        thread.start()

    def _refresh_bayesian_worker(
        self,
        dataset: pd.DataFrame,
        tables: dict[str, TableFrame],
        join_coverage: dict[str, float],
        cpu_analysis: dict[str, Any],
    ) -> None:
        try:
            bayesian = self._run_bayesian_analysis(
                dataset=dataset,
                cpu_analysis=cpu_analysis,
            )
            bayesian["refresh_in_progress"] = True
            bayesian["started_at"] = (
                self._bayesian_started_at.isoformat() if self._bayesian_started_at else None
            )
            bayesian["completed_at"] = (
                self._bayesian_completed_at.isoformat() if self._bayesian_completed_at else None
            )
            now = dt.datetime.now()
            workspace = self._assemble_workspace(
                tables=tables,
                dataset=dataset,
                join_coverage=join_coverage,
                cpu_analysis=cpu_analysis,
                bayesian=bayesian,
                now=now,
            )
            with self._refresh_lock:
                bayesian["refresh_in_progress"] = False
                bayesian["completed_at"] = now.isoformat()
                self._cached_bayesian = bayesian
                self._cached_workspace = workspace
                self._cached_at = now
                self._bayesian_completed_at = now
        except Exception as exc:
            _log.exception("Bayesian background refresh failed")
            with self._refresh_lock:
                self._cached_bayesian = {
                    "status": "error",
                    "error": str(exc),
                    "engine": "bayesian_counterfactuals",
                    "provider": "stan_execution",
                    "summary": {},
                    "drivers": [],
                    "counterfactuals": [],
                    "root_causes": [],
                    "message": "Bayesian counterfactual refresh failed. Fast CPU decision layer is still available.",
                }
                self._bayesian_completed_at = dt.datetime.now()
        finally:
            with self._refresh_lock:
                self._bayesian_refresh_in_progress = False

    def _assemble_workspace(
        self,
        tables: dict[str, TableFrame],
        dataset: pd.DataFrame,
        join_coverage: dict[str, float],
        cpu_analysis: dict[str, Any],
        bayesian: dict[str, Any],
        now: dt.datetime,
    ) -> dict[str, Any]:
        audit = self._build_audit(tables, join_coverage, dataset, bayesian)
        interactive = self._build_interactive_model(dataset, cpu_analysis, bayesian)

        coverage_cards = [
            {
                "label": "Job Progress Join",
                "coverage_pct": join_coverage["job_progress"],
                "status": "connected",
            },
            {
                "label": "Plan Snapshot Join",
                "coverage_pct": join_coverage["plan_snapshot"],
                "status": "connected",
            },
            {
                "label": "Daily Task Join",
                "coverage_pct": join_coverage["task_daily"],
                "status": "connected",
            },
            {
                "label": "SAP Sequence Join",
                "coverage_pct": join_coverage["sap_drilling"],
                "status": "connected",
            },
            {
                "label": "ActivityTaskPlan Join",
                "coverage_pct": join_coverage["activity_task_plan"],
                "status": "connected",
            },
            {
                "label": "PH Productivity Link",
                "coverage_pct": join_coverage["ph_productivity"],
                "status": "connected" if join_coverage["ph_productivity"] > 0 else "gap",
            },
        ]

        live = tables["wmr_latest"].frame.copy()
        progress = live["current_progress"].fillna(0.0)
        delayed = int((live["target_delay_days"].fillna(0.0) > 0).sum())

        data_health = build_data_health(
            live_wells=int(len(live)),
            historical_wells=int(tables["wmr_full"].frame["well_id"].nunique()),
            mean_progress_pct=round(float(progress.mean() * 100.0), 2),
            delayed_wells=delayed,
            bayesian_runtime=self._stan_service.runtime_label(),
            analysis_mode=cpu_analysis.get("mode", "cpu_operational_model_v1"),
            cpu_model_status=cpu_analysis.get("status", "fallback"),
        )
        analysis_status = build_analysis_status(
            deep_status=bayesian.get("status", "pending"),
            refresh_in_progress=self._bayesian_refresh_in_progress,
            started_at=self._bayesian_started_at,
            completed_at=self._bayesian_completed_at,
        )

        return {
            "generated_at": now.isoformat(),
            "workspace_name": "Causal Command",
            "objective": "Operational root-cause tracing, ranked intervention scenarios, and evidence-led decision support on live Al Tasnim data.",
            "target": "schedule_delay_days",
            "analysis_status": analysis_status,
            "data_health": data_health,
            "coverage_cards": coverage_cards,
            "audit_questions": audit,
            "interactive": interactive,
            "bayesian_analysis": bayesian,
            "gaps": [
                {
                    "label": "ActivityTaskPlan grain",
                    "detail": "ActivityTaskPlan is linked through live WMR project_id. The signal is project-scoped rather than a strict one-task-to-one-well mapping when multiple wells share a project.",
                },
                {
                    "label": "PH linkage grain",
                    "detail": "PH productivity is linked at well level through task_daily supervisor_email to Employee and PH records. The signal is supervisor-scoped and aggregated from the latest productivity rows.",
                },
            ],
        }

    def _feature_lineage(self) -> dict[str, dict[str, str]]:
        return {
            "overdue_daily_tasks": {
                "table": "task_daily",
                "column": "completed + target_end + well_id",
                "meaning": "Open daily tasks whose target end date has already passed.",
            },
            "current_month_gap": {
                "table": "Job_Progress_Report_GB",
                "column": "Current Month Actual % - Current Month Plan %",
                "meaning": "Current month execution gap versus plan.",
            },
            "engg_kpi_days": {
                "table": "WellMonitoringReport_Latest",
                "column": "engg_kpi_after_rig-off_days",
                "meaning": "Engineering lag after rig-off in days.",
            },
            "five_week_plan": {
                "table": "Job_Progress_PlanSnapshot",
                "column": "W1_Plan_frac..W5_Plan_frac",
                "meaning": "Near-term planned work concentration over the next 5 weeks.",
            },
            "avg_move_days": {
                "table": "SAP_DRILLING_SEQUENCE",
                "column": "Move_days",
                "meaning": "Average rig move delay signal for that well's drilling sequence.",
            },
            "daily_task_completion_rate": {
                "table": "task_daily",
                "column": "completed",
                "meaning": "Completion ratio of execution tasks for the mapped well.",
            },
            "overdue_daily_remaining_duration": {
                "table": "task_daily",
                "column": "remaining_duration + target_end + completed",
                "meaning": "Remaining duration tied specifically to overdue unfinished daily tasks.",
            },
            "activity_overdue_tasks": {
                "table": "ActivityTaskPlan",
                "column": "project_id + target_end + actual_end",
                "meaning": "Project-scoped overdue planned tasks linked into the live well through WMR project_id.",
            },
            "activity_remaining_duration_days": {
                "table": "ActivityTaskPlan",
                "column": "remaining_duration + project_id",
                "meaning": "Remaining planned duration across mapped ActivityTaskPlan rows for the live project.",
            },
            "activity_task_completion_rate": {
                "table": "ActivityTaskPlan",
                "column": "progress + project_id",
                "meaning": "Average progress across active ActivityTaskPlan rows linked through the live project.",
            },
            "ph_average_productivity_pct": {
                "table": "PH_PRODUCTIVITY_WEEKLY_REPORT",
                "column": "Average Productivity (%) via supervisor_email -> Employee.Email -> PH Emp ID",
                "meaning": "Supervisor-scoped productivity signal linked to the well through live task supervision records.",
            },
            "const_progress": {
                "table": "WellMonitoringReport_Latest",
                "column": "overall_const._10_100",
                "meaning": "Construction completion signal from the live WMR snapshot.",
            },
            "remaining_progress": {
                "table": "WellMonitoringReport_Latest",
                "column": "over_all_progress_percentages",
                "meaning": "Remaining portfolio execution still to be delivered on the live well.",
            },
            "weekly_velocity": {
                "table": "WMR_Full",
                "column": "current_progress week-over-week delta",
                "meaning": "Latest weekly progress change from the historical WMR signal.",
            },
        }

    def _actionable_feature_specs(self) -> dict[str, dict[str, Any]]:
        return {
            "overdue_daily_tasks": {
                "direction": "decrease",
                "value_kind": "count",
                "label_text": "overdue daily backlog",
                "verb": "Reduce",
                "min_value": 0.0,
            },
            "daily_task_completion_rate": {
                "direction": "increase",
                "value_kind": "fraction_points",
                "label_text": "daily task completion rate",
                "verb": "Lift",
                "min_value": 0.0,
                "max_value": 1.0,
            },
            "overdue_daily_remaining_duration": {
                "direction": "decrease",
                "value_kind": "days",
                "label_text": "overdue remaining duration",
                "verb": "Reduce",
                "min_value": 0.0,
            },
            "activity_overdue_tasks": {
                "direction": "decrease",
                "value_kind": "count",
                "label_text": "overdue planned task backlog",
                "verb": "Reduce",
                "min_value": 0.0,
            },
            "activity_task_completion_rate": {
                "direction": "increase",
                "value_kind": "fraction_points",
                "label_text": "planned task completion rate",
                "verb": "Lift",
                "min_value": 0.0,
                "max_value": 1.0,
            },
            "activity_remaining_duration_days": {
                "direction": "decrease",
                "value_kind": "days",
                "label_text": "planned remaining duration",
                "verb": "Reduce",
                "min_value": 0.0,
            },
            "engg_kpi_days": {
                "direction": "decrease",
                "value_kind": "days",
                "label_text": "engineering lag",
                "verb": "Reduce",
                "min_value": 0.0,
            },
            "current_month_gap": {
                "direction": "increase",
                "value_kind": "raw_points",
                "label_text": "current-month execution gap",
                "verb": "Close",
            },
            "cum_month_gap": {
                "direction": "increase",
                "value_kind": "raw_points",
                "label_text": "cumulative execution gap",
                "verb": "Close",
            },
            "five_week_plan": {
                "direction": "decrease",
                "value_kind": "fraction_points",
                "label_text": "near-term plan pressure",
                "verb": "Release",
                "min_value": 0.0,
            },
            "avg_move_days": {
                "direction": "decrease",
                "value_kind": "days",
                "label_text": "rig move delay",
                "verb": "Reduce",
                "min_value": 0.0,
            },
            "weekly_velocity": {
                "direction": "increase",
                "value_kind": "fraction_points",
                "label_text": "weekly execution velocity",
                "verb": "Lift",
            },
            "ph_average_productivity_pct": {
                "direction": "increase",
                "value_kind": "percentage",
                "label_text": "linked productivity",
                "verb": "Lift",
            },
        }

    def _select_peer_frame(
        self,
        dataset: pd.DataFrame,
        row: pd.Series,
    ) -> tuple[pd.DataFrame, str]:
        peers = dataset.loc[dataset["well_id"] != row["well_id"]].copy()
        if peers.empty:
            return peers, "portfolio peers"

        cluster = str(row.get("cluster", "UNKNOWN"))
        well_type = str(row.get("well_type", "UNKNOWN"))
        min_support = max(4, int(round(np.sqrt(max(len(peers), 1)))))
        candidate_sets = [
            (
                "cluster and well-type peers",
                peers.loc[(peers["cluster"] == cluster) & (peers["well_type"] == well_type)].copy(),
            ),
            ("cluster peers", peers.loc[peers["cluster"] == cluster].copy()),
            ("well-type peers", peers.loc[peers["well_type"] == well_type].copy()),
            ("portfolio peers", peers.copy()),
        ]
        for label, frame in candidate_sets:
            if len(frame) >= min_support:
                return frame, label
        for label, frame in candidate_sets:
            if not frame.empty:
                return frame, label
        return peers, "portfolio peers"

    def _peer_target_value(
        self,
        feature: str,
        row: pd.Series,
        peer_frame: pd.DataFrame,
        spec: dict[str, Any],
    ) -> dict[str, float] | None:
        if feature not in peer_frame.columns:
            return None
        current = float(pd.to_numeric(pd.Series([row.get(feature)]), errors="coerce").fillna(0.0).iloc[0])
        peer_values = pd.to_numeric(peer_frame[feature], errors="coerce").dropna()
        if peer_values.empty:
            return None

        if spec["direction"] == "decrease":
            better = peer_values.loc[peer_values < current]
        else:
            better = peer_values.loc[peer_values > current]
        if better.empty:
            return None

        target = float(better.median())
        if spec["direction"] == "decrease" and target >= current:
            return None
        if spec["direction"] == "increase" and target <= current:
            return None

        return {
            "current": current,
            "target": target,
            "support": float(len(better)),
        }

    def _format_action_change(self, value_kind: str, change: float) -> str:
        magnitude = abs(change)
        if value_kind == "count":
            qty = max(int(round(magnitude)), 1)
            return f"{qty} task" if qty == 1 else f"{qty} tasks"
        if value_kind == "fraction_points":
            pts = magnitude * 100.0
            return f"{pts:.0f} pts" if pts >= 2 else f"{pts:.1f} pts"
        if value_kind == "percentage":
            return f"{magnitude:.1f} pts"
        if value_kind == "days":
            return f"{magnitude:.1f} days"
        return f"{magnitude:.1f} pts"

    def _format_feature_value(self, value_kind: str, value: float) -> str:
        if value_kind == "count":
            return f"{int(round(value))}"
        if value_kind == "fraction_points":
            return f"{value * 100.0:.1f}%"
        if value_kind == "percentage":
            return f"{value:.1f}%"
        if value_kind == "days":
            return f"{value:.1f}d"
        return f"{value:.1f} pts"

    def _build_action_label(
        self,
        spec: dict[str, Any],
        current: float,
        target: float,
    ) -> str:
        if spec["value_kind"] == "count":
            change = current - target if spec["direction"] == "decrease" else target - current
            return f"{spec['verb']} {spec['label_text']} by {self._format_action_change(spec['value_kind'], change)}"
        target_label = self._format_feature_value(spec["value_kind"], target)
        if spec["verb"] == "Close":
            return f"Close {spec['label_text']} toward {target_label}"
        return f"{spec['verb']} {spec['label_text']} to {target_label}"

    def _build_action_description(
        self,
        feature: str,
        spec: dict[str, Any],
        current: float,
        target: float,
        peer_scope: str,
        support_cases: int,
        feature_lineage: dict[str, dict[str, str]],
    ) -> str:
        source = feature_lineage.get(feature, {})
        return (
            f"Shift {spec['label_text']} from {self._format_feature_value(spec['value_kind'], current)} "
            f"toward {self._format_feature_value(spec['value_kind'], target)} using the median of "
            f"{support_cases} better {peer_scope}. Source signal: {source.get('meaning', feature)}"
        )

    def _apply_peer_target_action(
        self,
        frame: pd.DataFrame,
        row: pd.Series,
        feature: str,
        target: float,
        peer_frame: pd.DataFrame,
        spec: dict[str, Any],
    ) -> None:
        if feature not in frame.columns:
            return

        value = target
        if spec.get("min_value") is not None:
            value = max(spec["min_value"], value)
        if spec.get("max_value") is not None:
            value = min(spec["max_value"], value)
        frame.loc[:, feature] = value

        if feature == "overdue_daily_tasks":
            current_tasks = float(max(row.get("overdue_daily_tasks", 0.0), 0.0))
            scale = value / current_tasks if current_tasks > 0 else 0.0
            if "overdue_daily_remaining_duration" in frame.columns:
                current_duration = float(frame["overdue_daily_remaining_duration"].iloc[0])
                frame.loc[:, "overdue_daily_remaining_duration"] = max(0.0, current_duration * scale)
            if "daily_task_completion_rate" in frame.columns and "daily_task_completion_rate" in peer_frame.columns:
                peer_completion = pd.to_numeric(peer_frame["daily_task_completion_rate"], errors="coerce").dropna()
                if not peer_completion.empty:
                    frame.loc[:, "daily_task_completion_rate"] = max(
                        float(frame["daily_task_completion_rate"].iloc[0]),
                        float(peer_completion.median()),
                    )
            return

        if feature == "activity_overdue_tasks":
            current_tasks = float(max(row.get("activity_overdue_tasks", 0.0), 0.0))
            scale = value / current_tasks if current_tasks > 0 else 0.0
            if "activity_remaining_duration_days" in frame.columns:
                current_duration = float(frame["activity_remaining_duration_days"].iloc[0])
                frame.loc[:, "activity_remaining_duration_days"] = max(0.0, current_duration * scale)
            if "activity_task_completion_rate" in frame.columns and "activity_task_completion_rate" in peer_frame.columns:
                peer_completion = pd.to_numeric(peer_frame["activity_task_completion_rate"], errors="coerce").dropna()
                if not peer_completion.empty:
                    frame.loc[:, "activity_task_completion_rate"] = max(
                        float(frame["activity_task_completion_rate"].iloc[0]),
                        float(peer_completion.median()),
                    )
            return

        if feature == "weekly_velocity":
            if "stalled_flag" in frame.columns and value > 0:
                frame.loc[:, "stalled_flag"] = 0.0
            if "regressed_flag" in frame.columns and value >= 0:
                frame.loc[:, "regressed_flag"] = 0.0

    def _build_model_scenarios(
        self,
        dataset: pd.DataFrame,
        row: pd.Series,
        baseline_frame: pd.DataFrame,
        baseline_pred: float,
        baseline_model_delay: float,
        model: Any,
        root_stack: list[dict[str, Any]],
        feature_lineage: dict[str, dict[str, str]],
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]], dict[str, int]]:
        specs = self._actionable_feature_specs()
        peer_frame, peer_scope = self._select_peer_frame(dataset, row)
        ordered_features: list[str] = []
        for item in root_stack:
            feature = item.get("feature")
            if feature in specs and feature not in ordered_features:
                ordered_features.append(feature)
        for feature in specs:
            if feature not in ordered_features:
                ordered_features.append(feature)

        scenario_rows: list[dict[str, Any]] = []
        scenario_catalog: dict[str, dict[str, str]] = {}
        support_cases: dict[str, int] = {}

        for feature in ordered_features:
            if feature not in baseline_frame.columns:
                continue
            spec = specs[feature]
            target_info = self._peer_target_value(feature, row, peer_frame, spec)
            if target_info is None:
                continue

            action_id = f"{feature}__{row['well_id']}"
            current = float(target_info["current"])
            target = float(target_info["target"])
            support = int(target_info["support"])

            modified_frame = baseline_frame.copy()
            self._apply_peer_target_action(modified_frame, row, feature, target, peer_frame, spec)
            scenario_model_delay = float(model.predict(modified_frame)[0])
            modeled_delta = scenario_model_delay - baseline_model_delay
            new_delay = float(max(0.0, baseline_pred + modeled_delta))
            delta_days = float(new_delay - baseline_pred)
            if abs(delta_days) < 0.01:
                continue

            label = self._build_action_label(spec, current, target)
            description = self._build_action_description(
                feature,
                spec,
                current,
                target,
                peer_scope,
                support,
                feature_lineage,
            )
            scenario_rows.append(
                {
                    "scenario": action_id,
                    "label": label,
                    "description": description,
                    "baseline_delay_days": round(baseline_pred, 2),
                    "delta_days": round(delta_days, 2),
                    "new_delay_days": round(new_delay, 2),
                    "support_cases": support,
                    "assumption_note": (
                        f"Trained LightGBM scenario estimate anchored to live SSMS features and the median of "
                        f"{support} better {peer_scope}."
                    ),
                    "engine": "cpu_operational_model_v1",
                }
            )
            scenario_catalog[action_id] = {
                "label": label,
                "description": description,
            }
            support_cases[action_id] = support

        scenario_rows.sort(key=lambda item: (item["new_delay_days"], item["delta_days"]))
        return scenario_rows, scenario_catalog, support_cases

    def _run_fast_cpu_analysis(self, dataset: pd.DataFrame) -> dict[str, Any]:
        feature_lineage = self._feature_lineage()
        feature_cols = [col for col in feature_lineage.keys() if col in dataset.columns]
        work = dataset.copy()
        X = work[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        y = pd.to_numeric(work["target_delay_days"], errors="coerce").fillna(0.0)

        if len(work) < 25 or y.nunique() < 2:
            return self._build_rule_based_cpu_analysis(work, feature_cols, feature_lineage)

        try:
            from lightgbm import LGBMRegressor
            from sklearn.metrics import mean_squared_error, r2_score
        except Exception:
            return self._build_rule_based_cpu_analysis(work, feature_cols, feature_lineage)

        model = LGBMRegressor(
            objective="regression",
            n_estimators=180,
            learning_rate=0.05,
            num_leaves=24,
            min_child_samples=12,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            verbose=-1,
        )
        model.fit(X, y)
        preds = model.predict(X)
        rmse = float(np.sqrt(mean_squared_error(y, preds)))
        r2 = float(r2_score(y, preds))

        shap_values = None
        try:
            import shap

            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X)
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            shap_values = np.asarray(shap_values, dtype=float)
        except Exception:
            shap_values = None

        if shap_values is None or shap_values.shape != X.shape:
            return self._build_rule_based_cpu_analysis(
                work,
                feature_cols,
                feature_lineage,
                preds=preds,
                r2=r2,
                rmse=rmse,
            )

        mean_abs = np.abs(shap_values).mean(axis=0)
        driver_order = np.argsort(mean_abs)[::-1]
        top_drivers = []
        for idx in driver_order[:8]:
            feature = feature_cols[idx]
            top_drivers.append(
                {
                    "feature": feature,
                    "label": feature.replace("_", " "),
                    "std_impact": float(mean_abs[idx]),
                    "unit_impact_days": float(np.nan_to_num(shap_values[:, idx]).mean()),
                    "ten_percent_impact_days": float(np.nanpercentile(np.nan_to_num(shap_values[:, idx]), 90)),
                    "source": feature_lineage.get(
                        feature,
                        {
                            "table": "derived",
                            "column": feature,
                            "meaning": "Derived signal from the fast CPU feature matrix.",
                        },
                    ),
                }
            )

        root_causes_by_well: dict[str, list[dict[str, Any]]] = {}
        scenarios_by_well: dict[str, list[dict[str, Any]]] = {}
        baseline_predictions: dict[str, float] = {}
        support_cases: dict[str, int] = {}
        scenario_catalog: dict[str, dict[str, str]] = {}

        for row_idx, (_, row) in enumerate(work.iterrows()):
            well_id = row["well_id"]
            baseline_pred = float(max(preds[row_idx], row["target_delay_days"], 0.0))
            baseline_predictions[well_id] = baseline_pred

            per_feature = []
            for feat_idx, feature in enumerate(feature_cols):
                contribution = float(shap_values[row_idx, feat_idx])
                if contribution <= 0:
                    continue
                per_feature.append(
                    {
                        "feature": feature,
                        "label": feature.replace("_", " "),
                        "contribution_score": contribution,
                        "source": feature_lineage.get(
                            feature,
                            {
                                "table": "derived",
                                "column": feature,
                                "meaning": "Derived signal from the fast CPU feature matrix.",
                            },
                        ),
                    }
                )
            if not per_feature:
                fallback_features = np.argsort(np.abs(shap_values[row_idx]))[::-1][:3]
                for feat_idx in fallback_features:
                    feature = feature_cols[feat_idx]
                    per_feature.append(
                        {
                            "feature": feature,
                            "label": feature.replace("_", " "),
                            "contribution_score": float(abs(shap_values[row_idx, feat_idx])),
                            "source": feature_lineage.get(
                                feature,
                                {
                                    "table": "derived",
                                    "column": feature,
                                    "meaning": "Derived signal from the fast CPU feature matrix.",
                                },
                            ),
                        }
                    )
            root_causes_by_well[well_id] = sorted(
                per_feature,
                key=lambda item: item["contribution_score"],
                reverse=True,
            )[:3]

            baseline_frame = X.iloc[[row_idx]].copy()
            baseline_model_delay = float(model.predict(baseline_frame)[0])
            scenario_rows, per_well_catalog, per_well_support = self._build_model_scenarios(
                dataset=work,
                row=row,
                baseline_frame=baseline_frame,
                baseline_pred=baseline_pred,
                baseline_model_delay=baseline_model_delay,
                model=model,
                root_stack=root_causes_by_well[well_id],
                feature_lineage=feature_lineage,
            )
            scenarios_by_well[well_id] = scenario_rows
            scenario_catalog.update(per_well_catalog)
            support_cases.update(per_well_support)

        return {
            "status": "ok",
            "mode": "cpu_operational_model_v1",
            "model_name": "LightGBMRegressor",
            "rows": int(len(work)),
            "features": int(len(feature_cols)),
            "r2": round(r2, 3),
            "rmse": round(rmse, 3),
            "top_drivers": top_drivers,
            "root_causes_by_well": root_causes_by_well,
            "scenarios_by_well": scenarios_by_well,
            "baseline_predictions": baseline_predictions,
            "support_cases": support_cases,
            "scenario_catalog": scenario_catalog,
        }

    def _build_rule_based_cpu_analysis(
        self,
        dataset: pd.DataFrame,
        feature_cols: list[str],
        feature_lineage: dict[str, dict[str, str]],
        preds: np.ndarray | None = None,
        r2: float | None = None,
        rmse: float | None = None,
    ) -> dict[str, Any]:
        work = dataset.copy()
        top_drivers = []
        root_causes_by_well: dict[str, list[dict[str, Any]]] = {}
        scenarios_by_well: dict[str, list[dict[str, Any]]] = {}
        baseline_predictions: dict[str, float] = {}

        for feature in feature_cols:
            values = pd.to_numeric(work[feature], errors="coerce").fillna(0.0)
            score = float(values.abs().mean())
            top_drivers.append(
                {
                    "feature": feature,
                    "label": feature.replace("_", " "),
                    "std_impact": score,
                    "unit_impact_days": score,
                    "ten_percent_impact_days": score * 0.1,
                    "source": feature_lineage.get(
                        feature,
                        {
                            "table": "derived",
                            "column": feature,
                            "meaning": "Derived signal from the rule-based operational feature matrix.",
                        },
                    ),
                }
            )

        for row_idx, (_, row) in enumerate(work.iterrows()):
            well_id = row["well_id"]
            baseline_delay = float(max(row["target_delay_days"], preds[row_idx] if preds is not None else 0.0, 0.0))
            baseline_predictions[well_id] = baseline_delay
            burdens = self._row_burdens(row)
            root_causes_by_well[well_id] = sorted(
                [
                    {
                        "feature": feature,
                        "label": feature.replace("_", " "),
                        "contribution_score": float(score),
                        "source": feature_lineage.get(
                            feature,
                            {
                                "table": "derived",
                                "column": feature,
                                "meaning": "Derived signal from the rule-based operational feature matrix.",
                            },
                        ),
                    }
                    for feature, score in burdens.items()
                    if score > 0
                ],
                key=lambda item: item["contribution_score"],
                reverse=True,
            )[:3]
            scenarios_by_well[well_id] = []

        return {
            "status": "fallback",
            "mode": "cpu_operational_rules_v1",
            "model_name": "rule_based",
            "rows": int(len(work)),
            "features": int(len(feature_cols)),
            "r2": round(r2 or 0.0, 3),
            "rmse": round(rmse or 0.0, 3),
            "top_drivers": sorted(top_drivers, key=lambda item: item["std_impact"], reverse=True)[:8],
            "root_causes_by_well": root_causes_by_well,
            "scenarios_by_well": scenarios_by_well,
            "baseline_predictions": baseline_predictions,
            "support_cases": {},
            "scenario_catalog": {},
        }

    def _row_burdens(self, row: pd.Series) -> dict[str, float]:
        return {
            "overdue_daily_tasks": float(max(row.get("overdue_daily_tasks", 0.0), 0.0)),
            "activity_overdue_tasks": float(max(row.get("activity_overdue_tasks", 0.0), 0.0)),
            "engg_kpi_days": float(max(row.get("engg_kpi_days", 0.0), 0.0)),
            "avg_move_days": float(max(row.get("avg_move_days", 0.0), 0.0)),
            "five_week_plan": float(max(row.get("five_week_plan", 0.0), 0.0) * 10.0),
            "remaining_progress": float(max(row.get("remaining_progress", 0.0), 0.0) * 10.0),
            "weekly_velocity": float(max(-row.get("weekly_velocity", 0.0), 0.0) * 25.0),
        }

    def _source_trace(
        self,
        label: str,
        table: str,
        column: str,
        note: str,
        as_of: str,
        kind: str = "fact",
    ) -> dict[str, str]:
        return {
            "label": label,
            "table": table,
            "column": column,
            "note": note,
            "as_of": as_of,
            "kind": kind,
        }

    def _confidence_label(
        self,
        support_cases: int,
        signal_quality: str,
        delta_days: float,
    ) -> str:
        return compose_confidence_label(
            support_cases=support_cases,
            signal_quality=signal_quality,
            delta_days=delta_days,
        )

    def _action_status(
        self,
        support_cases: int,
        delta_days: float,
    ) -> str:
        return compose_action_status(
            support_cases=support_cases,
            delta_days=delta_days,
        )

    def _decision_score(
        self,
        baseline_delay_days: float,
        delta_days: float,
        support_cases: int,
        signal_quality: str,
    ) -> float:
        recoverable = max(-delta_days, 0.0)
        support_factor = min(support_cases / 20.0, 1.0)
        quality_factor = {"high": 1.0, "medium": 0.8, "limited": 0.6}.get(signal_quality, 0.6)
        pressure_factor = 1.0 + min(max(baseline_delay_days, 0.0) / 60.0, 2.0)
        return round(recoverable * support_factor * quality_factor * pressure_factor, 2)

    def _build_primary_issue(self, row: pd.Series, root_stack: list[dict[str, Any]]) -> str:
        if root_stack:
            return root_stack[0]["label"]
        if row.get("overdue_daily_tasks", 0.0) > 0:
            return "Overdue execution backlog"
        if row.get("engg_kpi_days", 0.0) > 0:
            return "Engineering lag after rig-off"
        if row.get("avg_move_days", 0.0) > 0:
            return "Rig move friction"
        return "Execution pressure"

    def _build_why_now(self, row: pd.Series, root_stack: list[dict[str, Any]]) -> str:
        reasons: list[str] = []
        overdue_daily = float(row.get("overdue_daily_tasks", 0.0))
        activity_overdue = float(row.get("activity_overdue_tasks", 0.0))
        engg_days = float(row.get("engg_kpi_days", 0.0))
        move_days = float(row.get("avg_move_days", 0.0))
        five_week_plan = float(row.get("five_week_plan", 0.0))
        velocity = float(row.get("weekly_velocity", 0.0))

        if overdue_daily > 0:
            reasons.append(f"{int(overdue_daily)} overdue daily tasks are still open")
        if activity_overdue > 0:
            reasons.append(f"{int(activity_overdue)} planned tasks are overdue in ActivityTaskPlan")
        if engg_days > 0:
            reasons.append(f"engineering is lagging rig-off by {engg_days:.1f} days")
        if move_days > 0:
            reasons.append(f"rig move friction is averaging {move_days:.1f} days")
        if five_week_plan > 0.5:
            reasons.append(f"near-term plan pressure is concentrated at {five_week_plan * 100.0:.0f}%")
        if velocity <= 0:
            reasons.append("weekly execution velocity is flat or negative")

        if not reasons and root_stack:
            reasons.append(f"the strongest modeled driver is {root_stack[0]['label'].lower()}")
        if not reasons:
            reasons.append("live schedule pressure remains elevated on the current well")
        return "; ".join(reasons[:3]) + "."

    def _build_portfolio_brief(
        self,
        wells: list[dict[str, Any]],
        as_of: str,
    ) -> dict[str, Any]:
        actionable = [well for well in wells if well.get("action_status") == "Act Now"]
        candidates = [well for well in wells if well.get("action_status") == "Candidate"]
        blocked = [well for well in wells if well.get("confidence_label") == "Low"]
        ranked = sorted(wells, key=lambda item: item.get("decision_score", 0.0), reverse=True)
        top = ranked[0] if ranked else None
        top_cluster = None
        if wells:
            cluster_scores: dict[str, float] = {}
            for well in wells:
                cluster = well.get("cluster") or "Unknown"
                cluster_scores[cluster] = cluster_scores.get(cluster, 0.0) + float(well.get("baseline_delay_days", 0.0))
            top_cluster = max(cluster_scores.items(), key=lambda item: item[1])[0]
        recoverable = round(
            sum(max(-(well.get("recommended_delta_days") or 0.0), 0.0) for well in ranked[:10]),
            2,
        )

        message = (
            f"The highest-value move today is {top['recommended_action']} on {top['well_name']}, "
            f"with {max(-(top['recommended_delta_days'] or 0.0), 0.0):.2f} modeled recoverable days "
            f"and {top.get('scenario_support_cases', 0)} comparable support cases."
            if top
            else "No ranked intervention opportunities are currently available."
        )

        cards = [
            {
                "label": "Actionable Wells",
                "value": str(len(actionable)),
                "unit": "wells",
                "accent": "green",
                "source": self._source_trace(
                    "Actionable Wells",
                    "WellMonitoringReport_Latest + CPU decision layer",
                    "target_delay_days + scenario delta",
                    "Wells with decision status Act Now based on live delay and supported scenario recovery.",
                    as_of,
                    "model",
                ),
            },
            {
                "label": "Recoverable Top 10",
                "value": f"{recoverable:.2f}",
                "unit": "days",
                "accent": "blue",
                "source": self._source_trace(
                    "Recoverable Top 10",
                    "CPU decision layer",
                    "recommended_delta_days",
                    "Sum of modeled recoverable delay across the top ten ranked opportunities.",
                    as_of,
                    "model",
                ),
            },
            {
                "label": "Top Risk Cluster",
                "value": top_cluster or "n/a",
                "unit": "",
                "accent": "amber",
                "source": self._source_trace(
                    "Top Risk Cluster",
                    "WellMonitoringReport_Latest",
                    "cluster + target_delay_days",
                    "Cluster with the highest aggregate live delay pressure.",
                    as_of,
                    "fact",
                ),
            },
            {
                "label": "Weak Support",
                "value": str(len(blocked)),
                "unit": "wells",
                "accent": "red",
                "source": self._source_trace(
                    "Weak Support",
                    "CPU decision layer",
                    "support_cases + signal_quality",
                    "Wells whose current recommendation has low support or limited signal quality.",
                    as_of,
                    "model",
                ),
            },
        ]

        return {
            "as_of": as_of,
            "management_message": message,
            "attention_now": len(actionable),
            "candidate_count": len(candidates),
            "blocked_count": len(blocked),
            "cards": cards,
            "top_opportunity": top,
        }

    def _build_intervention_ladder(
        self,
        wells: list[dict[str, Any]],
        as_of: str,
    ) -> list[dict[str, Any]]:
        ranked = sorted(wells, key=lambda item: item.get("decision_score", 0.0), reverse=True)
        ladder = []
        for index, well in enumerate(ranked[:20], start=1):
            ladder.append(
                {
                    "rank": index,
                    "well_id": well["well_id"],
                    "well_name": well["well_name"],
                    "cluster": well.get("cluster", "Unknown"),
                    "rig_no": well["rig_no"],
                    "well_type": well["well_type"],
                    "action_label": well["recommended_action"],
                    "recoverable_days": round(max(-(well.get("recommended_delta_days") or 0.0), 0.0), 2),
                    "decision_score": well.get("decision_score", 0.0),
                    "confidence_label": well.get("confidence_label", "Low"),
                    "action_status": well.get("action_status", "Observe"),
                    "why_now": well.get("why_now", ""),
                    "support_cases": well.get("scenario_support_cases", 0),
                    "source": self._source_trace(
                        "Intervention Opportunity",
                        "WellMonitoringReport_Latest + CPU decision layer",
                        "target_delay_days + scenario delta",
                        "Ranked opportunity using live delay pressure, scenario recovery, and support.",
                        as_of,
                        "model",
                    ),
                }
            )
        return ladder

    def _build_interactive_model(
        self,
        dataset: pd.DataFrame,
        cpu_analysis: dict[str, Any],
        bayesian: dict[str, Any],
    ) -> dict[str, Any]:
        feature_lineage = self._feature_lineage()
        scenario_catalog = merge_scenario_catalog(cpu_analysis.get("scenario_catalog", {}))
        as_of = pd.Timestamp(self.today).strftime("%Y-%m-%d")
        baseline = dataset[
            [
                "well_id",
                "well_name",
                "rig_no",
                "well_type",
                "cluster",
                "current_progress",
                "target_delay_days",
                "engg_kpi_days",
                "overdue_daily_tasks",
                "activity_overdue_tasks",
                "five_week_plan",
                "avg_move_days",
                "weekly_velocity",
                "ph_average_productivity_pct",
            ]
        ].copy()
        baseline["current_progress_pct"] = (baseline["current_progress"] * 100.0).round(1)
        baseline["target_delay_days"] = baseline["target_delay_days"].round(2)

        scenarios_by_well = cpu_analysis.get("scenarios_by_well", {})
        roots_by_well = cpu_analysis.get("root_causes_by_well", {})
        baseline_predictions = cpu_analysis.get("baseline_predictions", {})
        support_cases = cpu_analysis.get("support_cases", {})

        wells = []
        for _, row in baseline.iterrows():
            well_id = row["well_id"]
            scenarios = sorted(
                copy.deepcopy(scenarios_by_well.get(well_id, [])),
                key=lambda item: (item["new_delay_days"], item["delta_days"]),
            )
            best = scenarios[0] if scenarios else None
            root_stack = sorted(
                copy.deepcopy(roots_by_well.get(well_id, [])),
                key=lambda item: item["contribution_score"],
                reverse=True,
            )
            modeled_baseline = float(baseline_predictions.get(well_id, row["target_delay_days"]))
            signal_quality = "high" if len(root_stack) >= 3 else "medium" if len(root_stack) >= 2 else "limited"
            support = int(best["support_cases"]) if best else 0
            action_status = self._action_status(support, float(best["delta_days"]) if best else 0.0)
            confidence_label = self._confidence_label(
                support,
                signal_quality,
                float(best["delta_days"]) if best else 0.0,
            )
            decision_score = self._decision_score(
                float(row["target_delay_days"]),
                float(best["delta_days"]) if best else 0.0,
                support,
                signal_quality,
            )
            primary_issue = self._build_primary_issue(row, root_stack)
            why_now = self._build_why_now(row, root_stack)
            if best and best["delta_days"] < 0:
                recommendation = (
                    f"{best['label']} is the strongest current action. "
                    f"Modeled delay delta {best['delta_days']:.2f} days on a baseline of {modeled_baseline:.2f} days."
                )
            elif best:
                recommendation = (
                    f"{best['label']} is the least-regret action in the current catalog, "
                    f"but the modeled deck is not showing immediate delay relief."
                )
            else:
                recommendation = "No decision-grade scenario is available for this well yet."
            recommendation = (
                recommendation
            )
            source_trace = [
                self._source_trace(
                    "Live Delay",
                    "WellMonitoringReport_Latest",
                    "exp.rig_off_location_sap_data + actual_rig_off_date",
                    "Live schedule delay from expected versus actual rig-off, or overdue expected rig-off when actual rig-off is missing.",
                    as_of,
                    "fact",
                ),
                self._source_trace(
                    "Progress",
                    "WellMonitoringReport_Latest",
                    "over_all_progress_percentages",
                    "Current progress for the selected well.",
                    as_of,
                    "fact",
                ),
                self._source_trace(
                    "Modeled Delay",
                    cpu_analysis.get("model_name", "CPU decision layer"),
                    "joined feature matrix",
                    "Predicted delay from the fast operational decision layer using live joined features.",
                    as_of,
                    "model",
                ),
                self._source_trace(
                    "Best Action",
                    "CPU scenario deck",
                    best["scenario"] if best else "n/a",
                    "Top-ranked governed action for this well based on modeled recovery and comparable support.",
                    as_of,
                    "model",
                ),
            ]
            wells.append(
                {
                    "well_id": well_id,
                    "well_name": row["well_name"],
                    "rig_no": row["rig_no"],
                    "well_type": row["well_type"],
                    "cluster": row["cluster"],
                    "current_progress_pct": float(row["current_progress_pct"]),
                    "baseline_delay_days": float(row["target_delay_days"]),
                    "recommended_action": best["label"] if best else "Unavailable",
                    "recommended_delta_days": best["delta_days"] if best else 0.0,
                    "recommendation": recommendation,
                    "scenarios": scenarios,
                    "root_causes": root_stack[:3],
                    "model_baseline_delay_days": modeled_baseline,
                    "signal_quality": signal_quality,
                    "scenario_support_cases": support,
                    "action_status": action_status,
                    "confidence_label": confidence_label,
                    "decision_score": decision_score,
                    "primary_issue": primary_issue,
                    "why_now": why_now,
                    "source_trace": source_trace,
                }
            )

        wells.sort(
            key=lambda item: (
                item["baseline_delay_days"],
                abs(item["recommended_delta_days"]),
                100 - item["current_progress_pct"],
            ),
            reverse=True,
        )

        return {
            "scenario_catalog": scenario_catalog,
            "feature_lineage": feature_lineage,
            "top_drivers": cpu_analysis.get("top_drivers", []),
            "wells": wells,
            "portfolio_brief": self._build_portfolio_brief(wells, as_of),
            "intervention_ladder": self._build_intervention_ladder(wells, as_of),
            "analysis_basis": {
                "engine": cpu_analysis.get("model_name", "rule_based"),
                "mode": cpu_analysis.get("mode", "cpu_operational_model_v1"),
                "rows": cpu_analysis.get("rows", 0),
                "features": cpu_analysis.get("features", 0),
                "r2": cpu_analysis.get("r2", 0.0),
                "rmse": cpu_analysis.get("rmse", 0.0),
                "support_cases": support_cases,
                "posterior_status": bayesian.get("status", "pending"),
            },
        }

    def _sql_conn(self):
        import pyodbc

        return pyodbc.connect(settings.sql_connection_string, timeout=15)

    def _available_relations(self, conn) -> set[str]:
        cursor = conn.cursor()
        try:
            return {
                str(row[2]).strip()
                for row in cursor.tables()
                if len(row) >= 3 and str(row[2]).strip()
            }
        finally:
            cursor.close()

    def _load_plan_snapshot_frame(
        self,
        conn,
        available_relations: set[str],
    ) -> tuple[pd.DataFrame, str]:
        if "Job_Progress_PlanSnapshot" in available_relations:
            try:
                return (
                    pd.read_sql(
                        """
                        SELECT
                            CAST(Well_ID AS varchar(100)) AS well_id,
                            CAST(project_id AS varchar(100)) AS project_id,
                            CAST([W1_Plan_frac] AS float) AS w1_plan,
                            CAST([W2_Plan_frac] AS float) AS w2_plan,
                            CAST([W3_Plan_frac] AS float) AS w3_plan,
                            CAST([W4_Plan_frac] AS float) AS w4_plan,
                            CAST([W5_Plan_frac] AS float) AS w5_plan,
                            CAST([CurrentMonthPlanFrac] AS float) AS current_month_plan_frac,
                            CAST([CumCurrentMonthPlanFrac] AS float) AS cum_current_month_plan_frac,
                            CreatedOn AS created_on
                        FROM Job_Progress_PlanSnapshot
                        """,
                        conn,
                    ),
                    "Job_Progress_PlanSnapshot",
                )
            except Exception as e:
                _log.warning(f"Failed to read Job_Progress_PlanSnapshot, falling back: {e}")

        if "Job_Progress_Report_GB" in available_relations:
            _log.warning(
                "Job_Progress_PlanSnapshot is missing locally or failed; deriving plan snapshot features from Job_Progress_Report_GB"
            )
            try:
                return (
                    pd.read_sql(
                        """
                        SELECT
                            CAST([Well ID] AS varchar(100)) AS well_id,
                            CAST(NULL AS varchar(100)) AS project_id,
                            CASE
                                WHEN CAST([Week-1 Plan %] AS float) > 1.0 THEN CAST([Week-1 Plan %] AS float) / 100.0
                                ELSE CAST([Week-1 Plan %] AS float)
                            END AS w1_plan,
                            CASE
                                WHEN CAST([Week-2 Plan %] AS float) > 1.0 THEN CAST([Week-2 Plan %] AS float) / 100.0
                                ELSE CAST([Week-2 Plan %] AS float)
                            END AS w2_plan,
                            CASE
                                WHEN CAST([Week-3 Plan %] AS float) > 1.0 THEN CAST([Week-3 Plan %] AS float) / 100.0
                                ELSE CAST([Week-3 Plan %] AS float)
                            END AS w3_plan,
                            CASE
                                WHEN CAST([Week-4 Plan %] AS float) > 1.0 THEN CAST([Week-4 Plan %] AS float) / 100.0
                                ELSE CAST([Week-4 Plan %] AS float)
                            END AS w4_plan,
                            CASE
                                WHEN CAST([Week-5 Plan %] AS float) > 1.0 THEN CAST([Week-5 Plan %] AS float) / 100.0
                                ELSE CAST([Week-5 Plan %] AS float)
                            END AS w5_plan,
                            CASE
                                WHEN CAST([Current Month Plan %] AS float) > 1.0 THEN CAST([Current Month Plan %] AS float) / 100.0
                                ELSE CAST([Current Month Plan %] AS float)
                            END AS current_month_plan_frac,
                            CASE
                                WHEN CAST([Cum-Current Month Plan %] AS float) > 1.0 THEN CAST([Cum-Current Month Plan %] AS float) / 100.0
                                ELSE CAST([Cum-Current Month Plan %] AS float)
                            END AS cum_current_month_plan_frac,
                            GETDATE() AS created_on
                        FROM Job_Progress_Report_GB
                        """,
                        conn,
                    ),
                    "Job_Progress_Report_GB (derived five-week plan fallback)",
                )
            except Exception as e:
                _log.warning(f"Failed to read Job_Progress_Report_GB, falling back: {e}")

        _log.warning(
            "Neither Job_Progress_PlanSnapshot nor Job_Progress_Report_GB is available; plan pressure features will default to zero"
        )
        return (
            pd.DataFrame(
                columns=[
                    "well_id",
                    "project_id",
                    "w1_plan",
                    "w2_plan",
                    "w3_plan",
                    "w4_plan",
                    "w5_plan",
                    "current_month_plan_frac",
                    "cum_current_month_plan_frac",
                    "created_on",
                ]
            ),
            "Job_Progress_PlanSnapshot",
        )

    def _load_tables(self) -> dict[str, TableFrame]:
        conn = self._sql_conn()
        try:
            available_relations = self._available_relations(conn)
            plan_snapshot_frame, plan_snapshot_source = self._load_plan_snapshot_frame(
                conn,
                available_relations,
            )
            tables = {
                "wmr_latest": TableFrame(
                    name="wmr_latest",
                    source="WellMonitoringReport_Latest",
                    frame=pd.read_sql(
                        """
                        SELECT
                            CAST(pdo_well_id AS varchar(100)) AS well_id,
                            well_name_after_spud AS well_name,
                            rig_no,
                            well_type,
                            Cluster AS cluster,
                            CAST(project_id AS varchar(100)) AS project_id,
                            CAST([over_all_progress_percentages] AS float) AS current_progress,
                            CAST([overall_loc._preparation_10_100] AS float) AS loc_prep_progress,
                            CAST([overall_const._10_100] AS float) AS const_progress,
                            CAST([overall_comm_progress_100] AS float) AS comm_progress,
                            CAST([engg_kpi_after_rig-off_days] AS float) AS engg_kpi_days,
                            [exp.rig_off_location_sap_data] AS expected_rig_off_date,
                            actual_rig_off_date
                        FROM WellMonitoringReport_Latest
                        """,
                        conn,
                    ),
                ),
                "wmr_full": TableFrame(
                    name="wmr_full",
                    source="WMR_Full",
                    frame=pd.read_sql(
                        """
                        SELECT
                            CAST(pdo_well_id AS varchar(100)) AS well_id,
                            well_name_after_spud AS well_name,
                            Week_Number AS snapshot_date,
                            CAST([over_all_progress_percentages] AS float) AS current_progress,
                            CAST([overall_loc._preparation_10_100] AS float) AS loc_prep_progress,
                            CAST([overall_const._10_100] AS float) AS const_progress,
                            CAST([overall_comm_progress_100] AS float) AS comm_progress
                        FROM WMR_Full
                        """,
                        conn,
                    ),
                ),
                "job_progress": TableFrame(
                    name="job_progress",
                    source="Job_Progress_Report_GB",
                    frame=pd.read_sql(
                        """
                        SELECT
                            CAST([Well ID] AS varchar(100)) AS well_id,
                            Category AS category,
                            [Well Name / Project Name] AS project_label,
                            CAST([Current Month Plan %] AS float) AS current_month_plan_pct,
                            CAST([Current Month Actual %] AS float) AS current_month_actual_pct,
                            CAST([Cum-Current Month Plan %] AS float) AS cum_month_plan_pct,
                            CAST([Cum-Current Month Actual %] AS float) AS cum_month_actual_pct
                        FROM Job_Progress_Report_GB
                        """,
                        conn,
                    ),
                ),
                "plan_snapshot": TableFrame(
                    name="plan_snapshot",
                    source=plan_snapshot_source,
                    frame=plan_snapshot_frame,
                ),
                "ph_productivity": TableFrame(
                    name="ph_productivity",
                    source="PH_PRODUCTIVITY_WEEKLY_REPORT",
                    frame=pd.read_sql(
                        """
                        SELECT
                            CAST(PH_Emp_ID AS varchar(100)) AS ph_emp_id,
                            ATNM_Sub_Contractor AS contractor_group,
                            Crew_Discipline AS crew_discipline,
                            PH_Name AS ph_name,
                            MonthStart AS month_start,
                            CAST(Average_Productivity AS float) AS average_productivity_pct
                        FROM PH_PRODUCTIVITY_WEEKLY_REPORT
                        """,
                        conn,
                    ),
                ),
                "sap_drilling": TableFrame(
                    name="sap_drilling",
                    source="SAP_DRILLING_SEQUENCE",
                    frame=(lambda c: pd.read_sql(
                        """
                        SELECT
                            CAST(Well_ID AS varchar(100)) AS well_id,
                            Field AS field_name,
                            Well_Category AS well_category,
                            CAST([Move_days] AS float) AS move_days,
                            CAST([Normal_duration] AS float) AS normal_duration_days
                        FROM SAP_DRILLING_SEQUENCE
                        """,
                        c,
                    ) if "SAP_DRILLING_SEQUENCE" in available_relations else pd.DataFrame(columns=['well_id']))(conn),
                ),
                "task_daily": TableFrame(
                    name="task_daily",
                    source="task_daily",
                    frame=(lambda c: pd.read_sql(
                        """
                        SELECT
                            CAST(well_id AS varchar(100)) AS well_id,
                            CAST(project_id AS varchar(100)) AS project_id,
                            task_code,
                            crew_type,
                            supervisor_email,
                            CAST(progress AS float) AS progress_pct,
                            CAST(remaining_duration AS float) AS remaining_duration_days,
                            target_end,
                            completed
                        FROM task_daily
                        """,
                        c,
                    ) if "task_daily" in available_relations else pd.DataFrame(columns=['well_id', 'project_id', 'supervisor_email']))(conn),
                ),
                "activity_task_plan": TableFrame(
                    name="activity_task_plan",
                    source="ActivityTaskPlan",
                    frame=(lambda c: pd.read_sql(
                        """
                        SELECT
                            CAST(Well_ID AS varchar(100)) AS well_id,
                            CAST(project_id AS varchar(100)) AS project_id,
                            crew_type,
                            supervisor_email,
                            [type],
                            CAST(progress AS float) AS progress_pct,
                            CAST(remaining_duration AS float) AS remaining_duration_days,
                            target_end,
                            actual_end
                        FROM ActivityTaskPlan
                        """,
                        c,
                    ) if "ActivityTaskPlan" in available_relations else pd.DataFrame(columns=['well_id', 'project_id', 'supervisor_email', 'type']))(conn),
                ),
                "employee": TableFrame(
                    name="employee",
                    source="Employee",
                    frame=(lambda c: pd.read_sql(
                        """
                        SELECT
                            CAST(UId AS varchar(100)) AS uid,
                            Email AS email,
                            Name AS employee_name
                        FROM Employee
                        """,
                        c,
                    ) if "Employee" in available_relations else pd.DataFrame(columns=['uid', 'email']))(conn),
                ),
            }
        finally:
            conn.close()

        self._normalize_tables(tables)
        return tables

    def _normalize_tables(self, tables: dict[str, TableFrame]) -> None:
        latest = tables["wmr_latest"].frame
        self._ensure_columns(
            latest,
            {
                "well_id": "UNKNOWN",
                "well_name": "UNKNOWN",
                "rig_no": "UNKNOWN",
                "well_type": "UNKNOWN",
                "cluster": "UNKNOWN",
                "project_id": "UNKNOWN",
                "current_progress": 0.0,
                "expected_rig_off_date": pd.NaT,
                "actual_rig_off_date": pd.NaT,
            },
        )
        for col in ["well_id", "well_name", "rig_no", "well_type", "cluster"]:
            latest[col] = latest[col].fillna("UNKNOWN").astype(str).str.strip()
        self._ensure_project_id_column(
            latest,
            well_to_project={},
            candidate_cols=["project", "project_name", "project_label"],
        )
        for col in ["expected_rig_off_date", "actual_rig_off_date"]:
            latest[col] = pd.to_datetime(latest[col], errors="coerce")
        latest["current_progress"] = latest["current_progress"].fillna(0.0)
        latest["target_delay_days"] = latest.apply(self._calc_target_delay, axis=1)
        well_to_project = {
            str(row["well_id"]): str(row["project_id"])
            for _, row in latest.loc[
                latest["well_id"].ne("UNKNOWN") & latest["project_id"].ne("UNKNOWN"),
                ["well_id", "project_id"],
            ].drop_duplicates("well_id").iterrows()
        }

        full = tables["wmr_full"].frame
        self._ensure_columns(
            full,
            {
                "well_id": "UNKNOWN",
                "well_name": "UNKNOWN",
                "snapshot_date": pd.NaT,
            },
        )
        full["well_id"] = full["well_id"].fillna("UNKNOWN").astype(str).str.strip()
        full["well_name"] = full["well_name"].fillna("UNKNOWN").astype(str).str.strip()
        full["snapshot_date"] = pd.to_datetime(full["snapshot_date"], errors="coerce")
        full.sort_values(["well_id", "snapshot_date"], inplace=True)

        job = tables["job_progress"].frame
        self._ensure_columns(
            job,
            {
                "well_id": "UNKNOWN",
                "current_month_actual_pct": 0.0,
                "current_month_plan_pct": 0.0,
                "cum_month_actual_pct": 0.0,
                "cum_month_plan_pct": 0.0,
            },
        )
        job["well_id"] = job["well_id"].fillna("UNKNOWN").astype(str).str.strip()
        job["current_month_gap"] = job["current_month_actual_pct"] - job["current_month_plan_pct"]
        job["cum_month_gap"] = job["cum_month_actual_pct"] - job["cum_month_plan_pct"]

        plan = tables["plan_snapshot"].frame
        self._ensure_columns(
            plan,
            {
                "well_id": "UNKNOWN",
                "project_id": "UNKNOWN",
                "created_on": pd.NaT,
                "w1_plan": 0.0,
                "w2_plan": 0.0,
                "w3_plan": 0.0,
                "w4_plan": 0.0,
                "w5_plan": 0.0,
                "current_month_plan_frac": 0.0,
                "cum_current_month_plan_frac": 0.0,
            },
        )
        plan["well_id"] = plan["well_id"].fillna("UNKNOWN").astype(str).str.strip()
        self._ensure_project_id_column(
            plan,
            well_to_project=well_to_project,
            candidate_cols=["project", "project_name", "project_label"],
        )
        plan["created_on"] = pd.to_datetime(plan["created_on"], errors="coerce")
        plan["five_week_plan"] = plan[["w1_plan", "w2_plan", "w3_plan", "w4_plan", "w5_plan"]].sum(axis=1, min_count=1)
        plan.sort_values(["well_id", "created_on"], inplace=True)

        ph = tables["ph_productivity"].frame
        self._ensure_columns(
            ph,
            {
                "ph_emp_id": "UNKNOWN",
                "crew_discipline": "UNKNOWN",
                "contractor_group": "UNKNOWN",
                "ph_name": "UNKNOWN",
                "month_start": pd.NaT,
                "average_productivity_pct": 0.0,
            },
        )
        ph["ph_emp_id"] = ph["ph_emp_id"].fillna("UNKNOWN").astype(str).str.strip()
        ph["crew_discipline"] = (
            ph["crew_discipline"]
            .fillna("UNKNOWN")
            .astype(str)
            .str.strip()
            .str.replace("\n", " / ", regex=False)
        )
        ph["contractor_group"] = ph["contractor_group"].fillna("UNKNOWN").astype(str).str.strip()
        ph["ph_name"] = ph["ph_name"].fillna("UNKNOWN").astype(str).str.strip()
        ph["month_start"] = pd.to_datetime(ph["month_start"], errors="coerce")

        sap = tables["sap_drilling"].frame
        self._ensure_columns(
            sap,
            {
                "well_id": "UNKNOWN",
                "field_name": "UNKNOWN",
                "well_category": "UNKNOWN",
                "move_days": 0.0,
                "normal_duration_days": 0.0,
            },
        )
        sap["well_id"] = sap["well_id"].fillna("UNKNOWN").astype(str).str.strip()
        sap["field_name"] = sap["field_name"].fillna("UNKNOWN").astype(str).str.strip()
        sap["well_category"] = sap["well_category"].fillna("UNKNOWN").astype(str).str.strip()

        task = tables["task_daily"].frame
        self._ensure_columns(
            task,
            {
                "well_id": "UNKNOWN",
                "project_id": "UNKNOWN",
                "task_code": "",
                "crew_type": "UNKNOWN",
                "supervisor_email": "",
                "progress_pct": 0.0,
                "remaining_duration_days": 0.0,
                "target_end": pd.NaT,
                "completed": False,
            },
        )
        task["well_id"] = task["well_id"].fillna("UNKNOWN").astype(str).str.strip()
        self._ensure_project_id_column(
            task,
            well_to_project=well_to_project,
            candidate_cols=["project", "project_name", "project_label"],
        )
        task["task_code"] = task["task_code"].fillna("").astype(str).str.strip()
        task["crew_type"] = task["crew_type"].fillna("UNKNOWN").astype(str).str.strip()
        task["supervisor_email"] = (
            task["supervisor_email"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )
        task["target_end"] = pd.to_datetime(task["target_end"], errors="coerce")
        task["completed"] = task["completed"].fillna(False).astype(bool)
        task["progress_pct"] = pd.to_numeric(task["progress_pct"], errors="coerce").fillna(0.0)
        task.loc[task["progress_pct"] > 1.0, "progress_pct"] = (
            task.loc[task["progress_pct"] > 1.0, "progress_pct"] / 100.0
        )
        task["is_overdue_open"] = (
            (~task["completed"])
            & task["target_end"].notna()
            & (task["target_end"] < self.today)
        )

        activity = tables["activity_task_plan"].frame
        self._ensure_columns(
            activity,
            {
                "well_id": "UNKNOWN",
                "project_id": "UNKNOWN",
                "crew_type": "UNKNOWN",
                "supervisor_email": "",
                "type": "UNKNOWN",
                "progress_pct": 0.0,
                "remaining_duration_days": 0.0,
                "target_end": pd.NaT,
                "actual_end": pd.NaT,
            },
        )
        activity["well_id"] = activity["well_id"].fillna("UNKNOWN").astype(str).str.strip()
        self._ensure_project_id_column(
            activity,
            well_to_project=well_to_project,
            candidate_cols=["project", "project_name", "project_label"],
        )
        activity["crew_type"] = activity["crew_type"].fillna("UNKNOWN").astype(str).str.strip()
        activity["supervisor_email"] = (
            activity["supervisor_email"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )
        activity["type"] = activity["type"].fillna("UNKNOWN").astype(str).str.strip()
        activity["progress_pct"] = pd.to_numeric(activity["progress_pct"], errors="coerce").fillna(0.0)
        activity.loc[activity["progress_pct"] > 1.0, "progress_pct"] = (
            activity.loc[activity["progress_pct"] > 1.0, "progress_pct"] / 100.0
        )
        activity["target_end"] = pd.to_datetime(activity["target_end"], errors="coerce")
        activity["actual_end"] = pd.to_datetime(activity["actual_end"], errors="coerce")
        activity["is_overdue_open"] = (
            activity["actual_end"].isna()
            & activity["target_end"].notna()
            & (activity["target_end"] < self.today)
        )

        employee = tables["employee"].frame
        self._ensure_columns(
            employee,
            {
                "uid": "UNKNOWN",
                "email": "",
                "employee_name": "UNKNOWN",
            },
        )
        employee["uid"] = employee["uid"].fillna("UNKNOWN").astype(str).str.strip()
        employee["email"] = (
            employee["email"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )
        employee["employee_name"] = employee["employee_name"].fillna("UNKNOWN").astype(str).str.strip()

    def _ensure_project_id_column(
        self,
        frame: pd.DataFrame,
        well_to_project: dict[str, str],
        candidate_cols: list[str] | None = None,
    ) -> None:
        candidate_cols = candidate_cols or []

        if "project_id" in frame.columns:
            project_series = frame["project_id"].copy()
        else:
            project_series = pd.Series(index=frame.index, dtype="object")

        for col in candidate_cols:
            if col not in frame.columns:
                continue
            fallback_series = frame[col]
            project_series = project_series.where(
                project_series.notna()
                & project_series.astype(str).str.strip().ne(""),
                fallback_series,
            )

        if "well_id" in frame.columns and well_to_project:
            mapped = frame["well_id"].map(well_to_project)
            project_series = project_series.where(
                project_series.notna()
                & project_series.astype(str).str.strip().ne(""),
                mapped,
            )

        frame["project_id"] = (
            project_series
            .fillna("UNKNOWN")
            .astype(str)
            .str.strip()
            .replace({"": "UNKNOWN", "nan": "UNKNOWN", "None": "UNKNOWN"})
        )

    def _ensure_columns(
        self,
        frame: pd.DataFrame,
        defaults: dict[str, Any],
    ) -> None:
        for col, default in defaults.items():
            if col not in frame.columns:
                frame[col] = default

    def _calc_target_delay(self, row: pd.Series) -> float:
        expected = row.get("expected_rig_off_date")
        actual = row.get("actual_rig_off_date")
        if pd.notna(expected) and pd.notna(actual):
            return float(max((actual - expected).days, 0))
        if pd.notna(expected) and pd.isna(actual) and expected < self.today:
            return float((self.today - expected).days)
        return 0.0

    def _build_feature_dataset(
        self,
        tables: dict[str, TableFrame],
    ) -> tuple[pd.DataFrame, dict[str, float]]:
        latest = tables["wmr_latest"].frame.copy()
        full = tables["wmr_full"].frame.copy()
        job = tables["job_progress"].frame.copy()
        plan = tables["plan_snapshot"].frame.copy()
        task = tables["task_daily"].frame.copy()
        sap = tables["sap_drilling"].frame.copy()
        activity = tables["activity_task_plan"].frame.copy()
        ph = tables["ph_productivity"].frame.copy()
        employee = tables["employee"].frame.copy()

        last_two = full.groupby("well_id").tail(2)
        history_rows = []
        for well_id, group in last_two.groupby("well_id"):
            group = group.sort_values("snapshot_date")
            current = group.iloc[-1]
            previous = group.iloc[-2] if len(group) > 1 else None
            velocity = 0.0
            regressed_flag = 0.0
            stalled_flag = 0.0
            if previous is not None and pd.notna(previous["current_progress"]) and pd.notna(current["current_progress"]):
                velocity = float(current["current_progress"] - previous["current_progress"])
                if abs(velocity) < 1e-9:
                    stalled_flag = 1.0
                if velocity < 0:
                    regressed_flag = 1.0
            history_rows.append(
                {
                    "well_id": well_id,
                    "weekly_velocity": velocity,
                    "stalled_flag": stalled_flag,
                    "regressed_flag": regressed_flag,
                }
            )
        history = pd.DataFrame(history_rows)

        job_agg = (
            job.groupby("well_id", as_index=False)
            .agg(
                current_month_gap=("current_month_gap", "mean"),
                cum_month_gap=("cum_month_gap", "mean"),
                category=("category", "first"),
                project_label=("project_label", "first"),
            )
        )

        plan_latest = (
            plan.sort_values(["well_id", "created_on"])
            .groupby("well_id", as_index=False)
            .tail(1)[
                [
                    "well_id",
                    "five_week_plan",
                    "current_month_plan_frac",
                    "cum_current_month_plan_frac",
                ]
            ]
        )

        task_agg = (
            task.groupby("well_id", as_index=False)
            .agg(
                overdue_daily_tasks=(
                    "task_code",
                    lambda s: (
                        lambda open_rows: int(open_rows["task_code"].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().nunique())
                        if int(open_rows["task_code"].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().nunique()) > 0
                        else int(open_rows["is_overdue_open"].sum())
                    )(task.loc[s.index].loc[task.loc[s.index, "is_overdue_open"], ["task_code", "is_overdue_open"]])
                ),
                overdue_daily_remaining_duration=("remaining_duration_days", lambda s: float(s[task.loc[s.index, "is_overdue_open"]].fillna(0).sum())),
                daily_task_completion_rate=("completed", "mean"),
            )
        )
        task_agg["daily_task_completion_rate"] = task_agg["daily_task_completion_rate"].fillna(0.0).astype(float)

        activity_active = activity.loc[
            activity["type"].eq("A") & activity["project_id"].ne("UNKNOWN")
        ].copy()
        activity_agg = (
            activity_active.groupby("project_id", as_index=False)
            .agg(
                activity_overdue_tasks=("is_overdue_open", "sum"),
                activity_remaining_duration_days=("remaining_duration_days", "sum"),
                activity_task_completion_rate=("progress_pct", "mean"),
                activity_supervisor_count=("supervisor_email", lambda s: int(s[s.ne("")].nunique())),
            )
        )
        activity_agg["activity_task_completion_rate"] = (
            activity_agg["activity_task_completion_rate"].fillna(0.0).astype(float)
        )

        ph_latest = (
            ph.sort_values(["ph_emp_id", "month_start"])
            .groupby("ph_emp_id", as_index=False)
            .tail(1)[["ph_emp_id", "average_productivity_pct", "crew_discipline", "month_start"]]
        )
        supervisor_bridge = employee.loc[employee["email"].ne(""), ["uid", "email", "employee_name"]].drop_duplicates()
        task_supervisor = task.loc[
            task["supervisor_email"].ne("") & task["well_id"].ne("UNKNOWN"),
            ["well_id", "supervisor_email"],
        ].drop_duplicates()
        task_supervisor = task_supervisor.merge(
            supervisor_bridge,
            how="left",
            left_on="supervisor_email",
            right_on="email",
        )
        task_supervisor = task_supervisor.merge(
            ph_latest,
            how="left",
            left_on="uid",
            right_on="ph_emp_id",
        )
        ph_well = (
            task_supervisor.groupby("well_id", as_index=False)
            .agg(
                ph_average_productivity_pct=("average_productivity_pct", "mean"),
                ph_linked_supervisors=("uid", lambda s: int(s[s.notna()].nunique())),
                ph_latest_month=("month_start", "max"),
            )
        )
        ph_well["ph_average_productivity_pct"] = (
            pd.to_numeric(ph_well["ph_average_productivity_pct"], errors="coerce")
            .fillna(0.0)
            .astype(float)
        )

        sap_agg = (
            sap.groupby("well_id", as_index=False)
            .agg(
                avg_move_days=("move_days", "mean"),
                avg_normal_duration_days=("normal_duration_days", "mean"),
                field_name=("field_name", "first"),
                well_category=("well_category", "first"),
            )
        )

        dataset = latest.merge(history, on="well_id", how="left")
        dataset = dataset.merge(job_agg, on="well_id", how="left")
        dataset = dataset.merge(plan_latest, on="well_id", how="left")
        dataset = dataset.merge(task_agg, on="well_id", how="left")
        dataset = dataset.merge(activity_agg, on="project_id", how="left")
        dataset = dataset.merge(ph_well, on="well_id", how="left")
        dataset = dataset.merge(sap_agg, on="well_id", how="left")

        defaults = {
            "weekly_velocity": 0.0,
            "stalled_flag": 0.0,
            "regressed_flag": 0.0,
            "current_month_gap": 0.0,
            "cum_month_gap": 0.0,
            "five_week_plan": 0.0,
            "current_month_plan_frac": 0.0,
            "cum_current_month_plan_frac": 0.0,
            "overdue_daily_tasks": 0.0,
            "overdue_daily_remaining_duration": 0.0,
            "daily_task_completion_rate": 0.0,
            "activity_overdue_tasks": 0.0,
            "activity_remaining_duration_days": 0.0,
            "activity_task_completion_rate": 0.0,
            "activity_supervisor_count": 0.0,
            "ph_average_productivity_pct": 0.0,
            "ph_linked_supervisors": 0.0,
            "avg_move_days": 0.0,
            "avg_normal_duration_days": 0.0,
            "engg_kpi_days": 0.0,
            "loc_prep_progress": 0.0,
            "const_progress": 0.0,
            "comm_progress": 0.0,
        }
        for col, default in defaults.items():
            dataset[col] = pd.to_numeric(dataset[col], errors="coerce").fillna(default)

        dataset["current_progress"] = pd.to_numeric(dataset["current_progress"], errors="coerce").fillna(0.0)
        dataset["remaining_progress"] = 1.0 - dataset["current_progress"]

        wmr_ids = set(latest.loc[latest["well_id"].ne("UNKNOWN"), "well_id"])
        join_coverage = {
            "job_progress": round(100.0 * len(wmr_ids & set(job_agg["well_id"])) / len(wmr_ids), 1),
            "plan_snapshot": round(100.0 * len(wmr_ids & set(plan_latest["well_id"])) / len(wmr_ids), 1),
            "task_daily": round(100.0 * len(wmr_ids & set(task_agg["well_id"])) / len(wmr_ids), 1),
            "sap_drilling": round(100.0 * len(wmr_ids & set(sap_agg["well_id"])) / len(wmr_ids), 1),
            "activity_task_plan": round(
                100.0
                * len(
                    set(
                        latest.loc[
                            latest["project_id"].isin(set(activity_agg["project_id"])),
                            "well_id",
                        ]
                    )
                )
                / len(wmr_ids),
                1,
            ),
            "ph_productivity": round(
                100.0 * len(wmr_ids & set(ph_well["well_id"])) / len(wmr_ids),
                1,
            ),
        }

        return dataset, join_coverage

    def _run_bayesian_analysis(
        self,
        dataset: pd.DataFrame,
        cpu_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self._stan_service.build_payload(
            dataset,
            cpu_analysis,
            refresh_in_progress=self._bayesian_refresh_in_progress,
            started_at=self._bayesian_started_at,
            completed_at=self._bayesian_completed_at,
        )
        _log.info(
            "Bayesian layer: %s via %s with %s drivers and %s counterfactual groups",
            payload.get("status", "unknown"),
            payload.get("provider", "unknown"),
            len(payload.get("drivers", [])),
            len(payload.get("counterfactuals", [])),
        )
        return payload

    def _build_audit(
        self,
        tables: dict[str, TableFrame],
        join_coverage: dict[str, float],
        dataset: pd.DataFrame,
        bayesian: dict[str, Any],
    ) -> list[dict[str, Any]]:
        latest = tables["wmr_latest"].frame
        full = tables["wmr_full"].frame
        job = tables["job_progress"].frame
        plan = tables["plan_snapshot"].frame
        ph = tables["ph_productivity"].frame
        sap = tables["sap_drilling"].frame
        task = tables["task_daily"].frame

        progress = latest["current_progress"].fillna(0.0)
        past_due = latest[(latest["expected_rig_off_date"].notna()) & (latest["actual_rig_off_date"].isna()) & (latest["expected_rig_off_date"] < self.today)]
        rig_backlog = (
            latest.loc[progress < 1.0]
            .groupby("rig_no")
            .size()
            .sort_values(ascending=False)
        )
        rig_performance = (
            latest.groupby("rig_no")
            .agg(avg_progress=("current_progress", "mean"), wells=("well_id", "count"))
        )
        rig_performance = rig_performance[rig_performance["wells"] >= 5].sort_values("avg_progress", ascending=False)

        full = full.sort_values(["well_id", "snapshot_date"])
        stalled = 0
        regressed = 0
        last_two = full.groupby("well_id").tail(2)
        for _, grp in last_two.groupby("well_id"):
            if len(grp) < 2:
                continue
            vals = grp["current_progress"].tolist()
            if pd.notna(vals[0]) and pd.notna(vals[1]):
                delta = float(vals[1] - vals[0])
                if abs(delta) < 1e-9:
                    stalled += 1
                if delta < 0:
                    regressed += 1

        job["current_month_gap"] = pd.to_numeric(job["current_month_gap"], errors="coerce")
        worst_category = job.groupby("category")["current_month_gap"].mean().dropna().sort_values().head(1)
        worst_entry = job[["project_label", "category", "current_month_gap"]].dropna().sort_values("current_month_gap").head(1)

        plan["five_week_plan"] = pd.to_numeric(plan["five_week_plan"], errors="coerce")
        high_plan = int((plan["five_week_plan"] > 0.5).sum())

        ph_disc = (
            ph.groupby("crew_discipline")
            .agg(avg_prod=("average_productivity_pct", "mean"), count=("ph_name", "count"))
        )
        ph_valid = ph_disc[ph_disc["count"] >= 5]
        ph_low = ph_valid.sort_values("avg_prod").head(1)
        ph_high = ph_valid.sort_values("avg_prod", ascending=False).head(1)

        sap_field = (
            sap.groupby("field_name")
            .agg(avg_move_days=("move_days", "mean"), avg_duration=("normal_duration_days", "mean"), count=("well_id", "count"))
        )
        sap_field = sap_field[sap_field["count"] >= 20]
        slowest_field = sap_field.sort_values("avg_move_days", ascending=False).head(1)

        task_overdue = int(task["is_overdue_open"].sum())
        task_crews = task.loc[task["is_overdue_open"]].groupby("crew_type").size().sort_values(ascending=False).head(3)

        q = []
        def answered(idx: int, question: str, answer: str, source: str) -> None:
            q.append({"id": idx, "status": "answered", "question": question, "answer": answer, "source": source})

        def gap(idx: int, question: str, answer: str, source: str) -> None:
            q.append({"id": idx, "status": "gap", "question": question, "answer": answer, "source": source})

        answered(1, "What is the live ground-truth current-state table for day-one causal operations?", "WellMonitoringReport_Latest is the live current-state surface for the first Causal Command release.", "WellMonitoringReport_Latest")
        answered(2, "What is the ground-truth historical progress source?", f"WMR_Full contains {int(len(full))} weekly history rows across {int(full['well_id'].nunique())} wells.", "WMR_Full")
        answered(3, "How many live wells are in scope right now?", f"{int(len(latest))} live wells are present in WellMonitoringReport_Latest.", "WellMonitoringReport_Latest")
        answered(4, "What is the portfolio's current mean progress?", f"Mean live progress is {progress.mean() * 100.0:.2f}%.", "WellMonitoringReport_Latest")
        answered(5, "How many wells are already past expected rig-off without an actual rig-off date?", f"{int(len(past_due))} live wells are already past expected rig-off with no actual rig-off captured.", "WellMonitoringReport_Latest")
        answered(6, "What is the join coverage from live wells into Job_Progress_Report_GB?", f"{join_coverage['job_progress']:.1f}% of live wells map directly by well ID.", "Job_Progress_Report_GB")
        answered(7, "What is the join coverage from live wells into Job_Progress_PlanSnapshot?", f"{join_coverage['plan_snapshot']:.1f}% of live wells map directly by well ID.", "Job_Progress_PlanSnapshot")
        answered(8, "What is the join coverage from live wells into task_daily?", f"{join_coverage['task_daily']:.1f}% of live wells map directly by well ID.", "task_daily")
        answered(9, "What is the join coverage from live wells into SAP_DRILLING_SEQUENCE?", f"{join_coverage['sap_drilling']:.1f}% of live wells map directly by well ID.", "SAP_DRILLING_SEQUENCE")
        answered(10, "Can ActivityTaskPlan be trusted in the day-one causal feature set?", f"Yes. ActivityTaskPlan now maps to {join_coverage['activity_task_plan']:.1f}% of live wells through WMR project_id, so project-scoped task signals are active in the causal feature set.", "ActivityTaskPlan + WellMonitoringReport_Latest.project_id")
        answered(11, "How many live wells are complete, active, and not started?", f"Complete: {int((progress >= 1.0).sum())}; active: {int(((progress > 0) & (progress < 1.0)).sum())}; not started: {int((progress <= 0).sum())}.", "WellMonitoringReport_Latest")
        if not rig_backlog.empty:
            answered(12, "Which rig carries the highest unfinished backlog?", f"{rig_backlog.index[0]} has the largest unfinished backlog with {int(rig_backlog.iloc[0])} live wells below 100%.", "WellMonitoringReport_Latest")
        else:
            gap(12, "Which rig carries the highest unfinished backlog?", "The local demo dataset does not have enough unfinished rig-linked wells to rank backlog by rig.", "WellMonitoringReport_Latest")
        if not rig_performance.empty:
            answered(13, "Which rig has the strongest average progress among rigs with at least 5 wells?", f"{rig_performance.index[0]} leads at {rig_performance.iloc[0]['avg_progress'] * 100.0:.2f}% average progress across {int(rig_performance.iloc[0]['wells'])} wells.", "WellMonitoringReport_Latest")
        else:
            gap(13, "Which rig has the strongest average progress among rigs with at least 5 wells?", "The local demo dataset does not have enough wells per rig to produce a stable rig performance ranking with the 5-well threshold.", "WellMonitoringReport_Latest")
        answered(14, "How many wells stalled across their last two weekly historical snapshots?", f"{stalled} wells showed zero progress change across the latest two WMR_Full snapshots.", "WMR_Full")
        answered(15, "How many wells regressed across their last two weekly historical snapshots?", f"{regressed} wells lost progress across the latest two WMR_Full snapshots.", "WMR_Full")
        if not worst_category.empty:
            answered(16, "Which job-progress category has the worst current-month actual-vs-plan gap?", f"{worst_category.index[0]} is worst at {worst_category.iloc[0]:.2f} percentage points.", "Job_Progress_Report_GB")
        else:
            gap(16, "Which job-progress category has the worst current-month actual-vs-plan gap?", "The local demo dataset does not contain enough valid category-level actual-vs-plan gap data to rank a worst category.", "Job_Progress_Report_GB")
        if not worst_entry.empty:
            answered(17, "Which single job-progress entry has the largest current-month negative gap?", f"{worst_entry.iloc[0]['project_label']} in {worst_entry.iloc[0]['category']} is at {worst_entry.iloc[0]['current_month_gap']:.2f} points.", "Job_Progress_Report_GB")
        else:
            gap(17, "Which single job-progress entry has the largest current-month negative gap?", "The local demo dataset does not contain a valid negative current-month gap row to single out.", "Job_Progress_Report_GB")
        answered(18, "How much near-term work is concentrated in the 5-week plan window?", f"{high_plan} plan snapshots hold more than 50% of their planned load inside W1-W5.", "Job_Progress_PlanSnapshot")
        answered(19, "What is the overdue execution pressure in task_daily?", f"There are {task_overdue} overdue unfinished daily tasks in task_daily.", "task_daily")
        if not task_crews.empty:
            answered(20, "Which crew types own the most overdue daily work?", "; ".join(f"{crew} ({int(count)})" for crew, count in task_crews.items()) + ".", "task_daily")
        else:
            gap(20, "Which crew types own the most overdue daily work?", "No overdue daily tasks are present in the local demo dataset, so there is no crew-type backlog ranking to report.", "task_daily")
        if not slowest_field.empty:
            answered(21, "Which field has the highest average rig move days among well-covered drilling fields?", f"{slowest_field.index[0]} is highest at {slowest_field.iloc[0]['avg_move_days']:.2f} average move days.", "SAP_DRILLING_SEQUENCE")
        else:
            gap(21, "Which field has the highest average rig move days among well-covered drilling fields?", "The local demo dataset does not have enough SAP drilling rows per field to rank average move days with the current minimum-support threshold.", "SAP_DRILLING_SEQUENCE")
        if not ph_low.empty:
            answered(22, "Which crew discipline is currently lowest on average productivity among disciplines with at least 5 records?", f"{ph_low.index[0]} is lowest at {ph_low.iloc[0]['avg_prod']:.2f}%.", "PH_PRODUCTIVITY_WEEKLY_REPORT")
        else:
            gap(22, "Which crew discipline is currently lowest on average productivity among disciplines with at least 5 records?", "The local demo dataset does not have enough PH productivity rows per discipline to rank the lowest discipline at the current threshold.", "PH_PRODUCTIVITY_WEEKLY_REPORT")
        if not ph_high.empty:
            answered(23, "Which crew discipline is currently highest on average productivity among disciplines with at least 5 records?", f"{ph_high.index[0]} is highest at {ph_high.iloc[0]['avg_prod']:.2f}%.", "PH_PRODUCTIVITY_WEEKLY_REPORT")
        else:
            gap(23, "Which crew discipline is currently highest on average productivity among disciplines with at least 5 records?", "The local demo dataset does not have enough PH productivity rows per discipline to rank the highest discipline at the current threshold.", "PH_PRODUCTIVITY_WEEKLY_REPORT")
        answered(24, "Can PH productivity already be used as a trusted per-well intervention variable?", f"Yes. PH productivity now links to {join_coverage['ph_productivity']:.1f}% of live wells through task_daily supervisor_email, Employee.Email, and PH Emp ID. The current signal is supervisor-scoped at the well level.", "PH_PRODUCTIVITY_WEEKLY_REPORT + Employee + task_daily")
        answered(
            25,
            "Is a fast operational decision layer available before posterior analysis completes?",
            f"Yes. The CPU decision layer is already active on {int(len(dataset))} live joined well rows and remains usable even while Bayesian counterfactual summaries are still refreshing.",
            "Fast CPU decision layer",
        )
        if bayesian.get("status") == "ok":
            top_driver = bayesian.get("drivers", [{}])[0] if bayesian.get("drivers") else {}
            answered(26, "Did the posterior counterfactual layer produce a real day-one sensitivity model on the live feature matrix?", f"Yes. The deep analysis processed {bayesian.get('summary', {}).get('rows', '0')} well rows and ranked {top_driver.get('feature', 'n/a')} as the strongest current driver by standardized impact.", "Bayesian counterfactual layer")
        elif bayesian.get("status") in {"warming", "pending"}:
            gap(26, "Did the posterior counterfactual layer produce a real day-one sensitivity model on the live feature matrix?", "Bayesian counterfactual summaries are still refreshing in the background. The fast CPU decision layer is already active.", "Bayesian counterfactual layer")
        else:
            gap(26, "Did the posterior counterfactual layer produce a real day-one sensitivity model on the live feature matrix?", bayesian.get("error", "Posterior analysis failed."), "Bayesian counterfactual layer")
        return q
