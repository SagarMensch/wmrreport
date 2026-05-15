"""
Bashira Predictive Forecasting Engine
======================================
SOTA per-well forecasting using StatsForecast (AutoARIMA/AutoETS)
+ XGBoost ensemble. CPU-optimized for production.

Provides:
  - Per-well progress time-series forecast (4-week horizon)
  - Phase milestone Gantt data
  - Historical drill-down (what happened, when, at what stage)
  - Risk scoring with driver attribution
"""

import os
import json
import logging
import numpy as np
import pandas as pd
import pyodbc
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from config import settings

logger = logging.getLogger("forecast_engine")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prediction_data")
LATEST_SQL_REFRESH_TTL_SECONDS = 300
JOB_PROGRESS_SQL_REFRESH_TTL_SECONDS = 900
PORTFOLIO_RISK_REFRESH_TTL_SECONDS = 120
WELL_LIST_REFRESH_TTL_SECONDS = 120

# ═══════════════════════════════════════════════════════════════════════════
# WELL LIFECYCLE PHASES — defines the Gantt structure
# ═══════════════════════════════════════════════════════════════════════════
PHASES = [
    {
        "id": "engineering",
        "label": "Engineering",
        "start_col": "engineering_actual_start_date",
        "end_col": "engineering_actual_finish_date",
        "progress_col": "overall_engg._10_100",
        "color": "#6366f1",
    },
    {
        "id": "loc_prep",
        "label": "Location Preparation",
        "start_col": "actual_start_date",
        "end_col": "actual_finish_date",
        "progress_col": "overall_loc._preparation_10_100",
        "color": "#8b5cf6",
    },
    {
        "id": "construction",
        "label": "Flowline Construction",
        "start_col": "const._actual_start_date",
        "end_col": "const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date",
        "progress_col": "overall_const._10_100",
        "color": "#06b6d4",
    },
    {
        "id": "drilling",
        "label": "Drilling (Rig On → Off)",
        "start_col": "actual_rig_on_date",
        "end_col": "actual_rig_off_date",
        "progress_col": None,
        "color": "#f59e0b",
    },
    {
        "id": "commissioning",
        "label": "Commissioning",
        "start_col": "actual_comm._start_date",
        "end_col": "actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date",
        "progress_col": "overall_comm_progress_100",
        "color": "#10b981",
    },
]

MILESTONE_DEFINITIONS = [
    {
        "label": "FLAF Issued",
        "planned_label": "Target FLAF Issue",
        "column": "flaf_issue_date",
        "phase_id": "engineering",
    },
    {
        "label": "Engineering Started",
        "planned_label": "Planned Eng. Start",
        "column": "engineering_actual_start_date",
        "phase_id": "engineering",
    },
    {
        "label": "Engineering Completed",
        "planned_label": "Planned Eng. Finish",
        "column": "engineering_actual_finish_date",
        "phase_id": "engineering",
    },
    {
        "label": "Location Prep Started",
        "planned_label": "Scheduled Loc Prep Start",
        "column": "actual_start_date",
        "phase_id": "loc_prep",
    },
    {
        "label": "Location Prep Completed",
        "planned_label": "Scheduled Loc Prep Finish",
        "column": "actual_finish_date",
        "phase_id": "loc_prep",
    },
    {
        "label": "Construction Started",
        "planned_label": "Planned Const. Start",
        "column": "const._actual_start_date",
        "phase_id": "construction",
    },
    {
        "label": "Construction Completed",
        "planned_label": "Planned Const. Finish",
        "column": "const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date",
        "phase_id": "construction",
    },
    {
        "label": "Rig On",
        "planned_label": "Scheduled Rig On",
        "column": "actual_rig_on_date",
        "phase_id": "drilling",
    },
    {
        "label": "Rig Off",
        "planned_label": "Scheduled Rig Off",
        "column": "actual_rig_off_date",
        "planned_column": "exp.rig_off_location_sap_data",
        "phase_id": "drilling",
    },
    {
        "label": "WLCTF Acceptance",
        "planned_label": "Target WLCTF Acceptance",
        "column": "wlctf_acceptanceapproval_from_production",
        "phase_id": "drilling",
    },
    {
        "label": "Hoist/FBU On",
        "planned_label": "Scheduled Hoist On",
        "column": "actual_hoist_fbu_rsr_on_date",
        "phase_id": "commissioning",
    },
    {
        "label": "Hoist/FBU Off",
        "planned_label": "Scheduled Hoist Off",
        "column": "actual_hoist_fbu_rsr_off_date",
        "phase_id": "commissioning",
    },
    {
        "label": "Commissioning Started",
        "planned_label": "Planned Comm. Start",
        "column": "actual_comm._start_date",
        "phase_id": "commissioning",
        "respect_placeholder": True,
    },
    {
        "label": "Commissioning Completed",
        "planned_label": "Planned Comm. Finish",
        "column": "actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date",
        "phase_id": "commissioning",
        "respect_placeholder": True,
    },
]


class ForecastEngine:
    """Production CPU inference engine for well-level forecasting."""

    def __init__(self):
        self.history_df: Optional[pd.DataFrame] = None
        self.latest_df: Optional[pd.DataFrame] = None
        self.job_progress_df: Optional[pd.DataFrame] = None
        self._latest_loaded_from = "uninitialized"
        self._history_loaded_from = "uninitialized"
        self._job_progress_loaded_from = "uninitialized"
        self._latest_refreshed_at: Optional[datetime] = None
        self._job_progress_refreshed_at: Optional[datetime] = None
        self._portfolio_risk_cache: Dict[str, Dict[str, Any]] = {}
        self._portfolio_risk_refreshed_at: Optional[datetime] = None
        self._well_list_cache: List[Dict[str, Any]] = []
        self._well_list_refreshed_at: Optional[datetime] = None
        self._load_data()

    def _load_data(self):
        """Load pre-extracted CSV data."""
        hist_path = os.path.join(DATA_DIR, "wmr_full_history.csv")
        latest_path = os.path.join(DATA_DIR, "wmr_latest.csv")
        jp_path = os.path.join(DATA_DIR, "job_progress_gb.csv")

        if os.path.exists(hist_path):
            self.history_df = pd.read_csv(hist_path, low_memory=False)
            self.history_df = self._normalize_dataframe_types(self.history_df)
            self._history_loaded_from = "csv_fallback"
            logger.info(f"[FE] Loaded history: {len(self.history_df)} rows, "
                       f"{self.history_df['pdo_well_id'].nunique()} wells")

        if os.path.exists(latest_path):
            self.latest_df = pd.read_csv(latest_path, low_memory=False)
            self.latest_df = self._normalize_snapshot_df(self.latest_df)
            self._latest_loaded_from = "csv_fallback"
            logger.info(f"[FE] Loaded latest: {len(self.latest_df)} wells")

        if os.path.exists(jp_path):
            self.job_progress_df = pd.read_csv(jp_path, low_memory=False)
            self._job_progress_loaded_from = "csv_fallback"
            logger.info(f"[FE] Loaded job progress: {len(self.job_progress_df)} rows")

        # Prefer live SSMS data when available; keep CSVs only as a fallback.
        self._refresh_latest_from_sql(force=True)
        self._refresh_job_progress_from_sql(force=True)

    def _get_sql_connection(self) -> Optional[pyodbc.Connection]:
        try:
            return pyodbc.connect(settings.sql_connection_string, timeout=10)
        except Exception as exc:
            logger.warning("[FE] Live SQL connection unavailable, using cached data: %s", exc)
            return None

    def _query_dataframe(self, query: str, params: Optional[List[Any]] = None) -> Optional[pd.DataFrame]:
        conn = self._get_sql_connection()
        if conn is None:
            return None

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return pd.DataFrame.from_records(rows, columns=columns)
        except Exception as exc:
            logger.warning("[FE] Live SQL query failed, using cached data: %s", exc)
            return None
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                conn.close()

    def _normalize_dataframe_types(self, df: Optional[pd.DataFrame]) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame() if df is None else df

        normalized = df.copy()
        for column in normalized.columns:
            if 'date' in column.lower() or column == 'Week_Number':
                normalized[column] = pd.to_datetime(normalized[column], errors='coerce')

        progress_columns = [
            column for column in normalized.columns
            if 'progress' in column.lower()
            or column.endswith('_5')
            or column.endswith('_20')
            or column.endswith('_60')
            or column.endswith('_100')
        ]
        for column in progress_columns:
            normalized[column] = pd.to_numeric(normalized[column], errors='coerce')

        return normalized

    def _normalize_snapshot_df(self, df: pd.DataFrame) -> pd.DataFrame:
        normalized = self._normalize_dataframe_types(df)
        if normalized.empty or 'pdo_well_id' not in normalized.columns:
            return normalized

        if 'Week_Number' in normalized.columns:
            normalized = normalized.sort_values('Week_Number', ascending=False)

        normalized['pdo_well_id'] = normalized['pdo_well_id'].astype(str).str.strip()
        normalized = normalized.drop_duplicates(subset=['pdo_well_id'], keep='first')
        return normalized.reset_index(drop=True)

    def _refresh_latest_from_sql(self, force: bool = False) -> bool:
        now = datetime.utcnow()
        if (
            not force
            and self.latest_df is not None
            and self._latest_refreshed_at is not None
            and (now - self._latest_refreshed_at).total_seconds() < LATEST_SQL_REFRESH_TTL_SECONDS
        ):
            return True

        df = self._query_dataframe("SELECT * FROM WellMonitoringReport")
        if df is None or df.empty:
            return self.latest_df is not None

        self.latest_df = self._normalize_snapshot_df(df)
        self._latest_loaded_from = "live_sql"
        self._latest_refreshed_at = now
        self._well_list_cache = []
        self._well_list_refreshed_at = None
        logger.info("[FE] Refreshed latest snapshot from live SQL: %d wells", len(self.latest_df))
        return True

    def _refresh_job_progress_from_sql(self, force: bool = False) -> bool:
        now = datetime.utcnow()
        if (
            not force
            and self.job_progress_df is not None
            and self._job_progress_refreshed_at is not None
            and (now - self._job_progress_refreshed_at).total_seconds() < JOB_PROGRESS_SQL_REFRESH_TTL_SECONDS
        ):
            return True

        df = self._query_dataframe("SELECT * FROM Job_Progress_Report_GB")
        if df is None or df.empty:
            return self.job_progress_df is not None

        self.job_progress_df = self._normalize_dataframe_types(df)
        self._job_progress_loaded_from = "live_sql"
        self._job_progress_refreshed_at = now
        logger.info("[FE] Refreshed job progress from live SQL: %d rows", len(self.job_progress_df))
        return True

    def _get_live_current_row(self, well_id: str) -> Optional[pd.Series]:
        df = self._query_dataframe(
            """
            SELECT TOP 1 *
            FROM WellMonitoringReport
            WHERE TRY_CONVERT(nvarchar(50), pdo_well_id) = ?
            ORDER BY TRY_CONVERT(date, Week_Number) DESC
            """,
            [str(well_id).strip()],
        )
        if df is None or df.empty:
            return None

        normalized = self._normalize_snapshot_df(df)
        if normalized.empty:
            return None
        return normalized.iloc[0]

    def _get_live_history_df(self, well_id: str) -> Optional[pd.DataFrame]:
        df = self._query_dataframe(
            """
            SELECT
                TRY_CONVERT(nvarchar(50), pdo_well_id) AS pdo_well_id,
                well_name_after_spud,
                Week_Number,
                over_all_progress_percentages,
                [overall_loc._preparation_10_100],
                [overall_engg._10_100],
                [overall_const._10_100],
                [overall_comm_progress_100],
                [overall_ohl_progr_100] AS ohl_progress,
                flowline_construction_progress
            FROM WMR_Full
            WHERE TRY_CONVERT(nvarchar(50), pdo_well_id) = ?
            ORDER BY TRY_CONVERT(date, Week_Number) ASC
            """,
            [str(well_id).strip()],
        )
        if df is None or df.empty:
            return None
        return self._clean_history_df(df)

    def _get_live_job_progress_df(self, well_id: str) -> Optional[pd.DataFrame]:
        df = self._query_dataframe(
            """
            SELECT *
            FROM Job_Progress_Report_GB
            WHERE TRY_CONVERT(nvarchar(50), [Well ID]) = ?
            """,
            [str(well_id).strip()],
        )
        if df is None or df.empty:
            return None
        return self._normalize_dataframe_types(df)

    def _clean_history_df(self, hist_df: pd.DataFrame, canonical_name: Optional[str] = None) -> pd.DataFrame:
        cleaned = self._normalize_dataframe_types(hist_df)
        if cleaned.empty:
            return cleaned

        if 'Week_Number' not in cleaned.columns:
            return cleaned.sort_index()

        cleaned = cleaned.dropna(subset=['Week_Number']).copy()
        cleaned['Week_Number'] = pd.to_datetime(cleaned['Week_Number'], errors='coerce').dt.normalize()
        cleaned = cleaned.dropna(subset=['Week_Number'])
        cleaned = cleaned.sort_values('Week_Number')

        numeric_progress_columns = [
            column for column in [
                'over_all_progress_percentages',
                'overall_loc._preparation_10_100',
                'overall_engg._10_100',
                'overall_const._10_100',
                'overall_comm_progress_100',
                'ohl_progress',
                'flowline_construction_progress',
            ]
            if column in cleaned.columns
        ]

        aggregations = {
            'pdo_well_id': 'first',
            'well_name_after_spud': 'last',
        }
        for column in numeric_progress_columns:
            aggregations[column] = 'max'

        cleaned = cleaned.groupby('Week_Number', as_index=False).agg(aggregations)

        for column in numeric_progress_columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors='coerce').cummax()

        if canonical_name:
            cleaned['well_name_after_spud'] = canonical_name

        return cleaned.sort_values('Week_Number').reset_index(drop=True)

    # ── WELL LIST ─────────────────────────────────────────────────────────

    def get_well_list(self) -> List[Dict]:
        """Return summary list of all wells for the selector."""
        now = datetime.utcnow()
        if (
            self._well_list_cache
            and self._well_list_refreshed_at is not None
            and (now - self._well_list_refreshed_at).total_seconds() < WELL_LIST_REFRESH_TTL_SECONDS
        ):
            return [dict(row) for row in self._well_list_cache]

        self._refresh_latest_from_sql()
        if self.latest_df is None:
            return []

        wells = []
        risk_map = self._get_portfolio_risk_map()
        for _, row in self.latest_df.iterrows():
            prog = pd.to_numeric(row.get('over_all_progress_percentages'), errors='coerce')
            prog_pct = round(float(prog * 100), 1) if pd.notna(prog) else 0.0
            risk_row = risk_map.get(str(row.get('pdo_well_id', '')))
            risk_score = round(float((risk_row or {}).get('risk_probability_pct') or 0.0), 1)
            risk_tier = str((risk_row or {}).get('risk_tier') or self._risk_tier_from_score(risk_score))

            # Determine status
            if prog_pct >= 100:
                status = "COMPLETED"
            elif row.get('buffer_status') == 'ROL':
                status = "DRILLING"
            elif prog_pct > 0:
                status = "IN_PROGRESS"
            else:
                status = "NOT_STARTED"

            wells.append({
                "pdo_well_id": str(row.get('pdo_well_id', '')),
                "well_name": str(row.get('well_name_after_spud', '')),
                "rig_no": str(row.get('rig_no', '')),
                "well_type": str(row.get('well_type', '')),
                "cluster": str(row.get('Cluster', '')),
                "progress_pct": prog_pct,
                "status": status,
                "risk_tier": risk_tier,
                "risk_score": risk_score,
                "buffer_status": str(row.get('buffer_status', '') or ''),
            })

        # Sort: critical first, then by progress ascending
        tier_order = {"CRITICAL": 0, "HIGH_RISK": 1, "WATCH": 2, "HEALTHY": 3}
        wells.sort(
            key=lambda w: (
                tier_order.get(w['risk_tier'], 4),
                -float(w.get('risk_score', 0) or 0),
                w['progress_pct'],
            )
        )
        self._well_list_cache = [dict(row) for row in wells]
        self._well_list_refreshed_at = now
        return [dict(row) for row in self._well_list_cache]

    # ── WELL DETAIL (DEEP DIVE) ──────────────────────────────────────────

    def get_well_detail(self, well_id: str) -> Dict:
        """Full deep-dive for a single well: history, phases, forecast."""
        result = {
            "well_id": well_id,
            "current_state": {},
            "history": [],
            "gantt": [],
            "forecast": [],
            "milestones": [],
            "risk": {},
            "plan_vs_actual": {},
            "data_lineage": {},
        }
        current_state_source = self._latest_loaded_from
        history_source = self._history_loaded_from
        plan_vs_actual_source = self._job_progress_loaded_from
        forecast_source = "heuristic_fallback"
        risk_source = "risk_model_service"

        # 1. Current state from live latest snapshot when available.
        row = self._get_live_current_row(well_id)
        if row is not None:
            current_state_source = "live_sql"
            result["current_state"] = self._build_current_state(row)
            result["gantt"] = self._build_gantt(row)
            result["milestones"] = self._build_milestones(row)
        elif self.latest_df is not None:
            match = self.latest_df[
                self.latest_df['pdo_well_id'].astype(str).str.strip() == str(well_id).strip()
            ]
            if not match.empty:
                row = match.iloc[0]
                result["current_state"] = self._build_current_state(row)
                result["gantt"] = self._build_gantt(row)
                result["milestones"] = self._build_milestones(row)

        canonical_name = result["current_state"].get("well_name")

        # 2. Historical time-series from live WMR_Full with dedupe / smoothing.
        hist = self._get_live_history_df(well_id)
        if hist is not None and not hist.empty:
            history_source = "live_sql_wmr_full_cleaned"
            hist = self._clean_history_df(hist, canonical_name)
            result["history"] = self._build_history(hist)
            result["forecast"] = self._build_forecast(hist)
        elif self.history_df is not None:
            hist = self.history_df[
                self.history_df['pdo_well_id'].astype(str).str.strip() == str(well_id).strip()
            ]
            hist = self._clean_history_df(hist, canonical_name)
            if not hist.empty:
                result["history"] = self._build_history(hist)
                result["forecast"] = self._build_forecast(hist)

        # 3. Plan vs Actual from live job progress when available.
        jp_match = self._get_live_job_progress_df(well_id)
        if jp_match is not None and not jp_match.empty:
            plan_vs_actual_source = "live_sql"
            result["plan_vs_actual"] = self._build_plan_vs_actual(jp_match)
        elif self.job_progress_df is not None:
            jp_match = self.job_progress_df[
                self.job_progress_df['Well ID'].astype(str).str.strip() == str(well_id).strip()
            ]
            if not jp_match.empty:
                result["plan_vs_actual"] = self._build_plan_vs_actual(jp_match)

        # 4. Risk / ML Hooks via Orchestrator + Ensemble Stacking
        prog = result["current_state"].get("progress", 0) / 100.0
        hist_data = result.get("history", [])

        # Call the Advanced CPU ML Pipeline (Sync call)
        import requests
        ml_data = None
        cate_data = None
        try:
            ml_resp = requests.get(f"http://127.0.0.1:8050/ml/forecast/{well_id}", timeout=2.5)
            if ml_resp.status_code == 200:
                ml_data = ml_resp.json()
                result["ml_intelligence"] = ml_data
                forecast_source = "cpu_ml_service"
                result["risk"] = self._compute_model_risk(ml_data)
                risk_source = str(
                    (ml_data.get("risk_model") or {}).get("engine")
                    or "calibrated_delay_risk_model"
                )
                # Inject StatsForecast logic directly into 'forecast' mapping
                if ml_data.get("stats_forecast"):
                    result["forecast"] = ml_data.get("stats_forecast")
            else:
                result["risk"] = self._unavailable_risk(
                    "Risk model service did not return a valid response.",
                )
                risk_source = "risk_model_unavailable"
                result["ml_intelligence"] = {"hidden_insights": [], "error": "ML Orchestrator unreachable on port 8050"}
        except requests.exceptions.RequestException:
            result["risk"] = self._unavailable_risk(
                "Risk model service is unavailable.",
            )
            risk_source = "risk_model_unavailable"
            result["ml_intelligence"] = {"hidden_insights": [], "error": "ML Orchestrator unreachable on port 8050"}

        # Fetch S-Learner CATE data
        try:
            cate_resp = requests.get(f"http://127.0.0.1:8050/ml/causal/cate/{well_id}", timeout=2.0)
            if cate_resp.status_code == 200:
                cate_data = cate_resp.json()
                result["causal_cate"] = cate_data
        except Exception:
            cate_data = None

        # 5. Ensemble Stacking — combine all base model predictions
        try:
            from ensemble_stacker import get_ensemble_stacker
            stacker = get_ensemble_stacker()

            # Gather Stan Bayesian data from causal command cache (if available)
            stan_posterior = None
            try:
                from causal_stan_service import StanCounterfactualService
                # Stan data is populated via background refresh in causal_command_service
                # We read whatever is available from the API
                stan_resp = requests.get("http://127.0.0.1:8005/api/causal/command", timeout=1.5)
                if stan_resp.status_code == 200:
                    causal_ws = stan_resp.json()
                    stan_posterior = causal_ws.get("bayesian_counterfactuals")
            except Exception:
                stan_posterior = None

            ensemble_result = stacker.stack_predictions(
                lightgbm_risk_prob=float(ml_data.get("risk_probability_pct", 0)) if ml_data else None,
                arima_forecast=ml_data.get("stats_forecast") if ml_data else None,
                stan_posterior=stan_posterior,
                s_learner_cate=cate_data,
                well_id=well_id,
                current_progress=prog,
            )
            result["ensemble_prediction"] = ensemble_result
        except Exception as exc:
            logger.warning(f"Ensemble stacking failed for {well_id}: {exc}")
            result["ensemble_prediction"] = {"error": str(exc), "active_models": 0}

        result["data_lineage"] = {
            "current_state_source": current_state_source,
            "current_snapshot_date": result["current_state"].get("snapshot_date"),
            "history_source": history_source,
            "history_points": len(result.get("history", [])),
            "plan_vs_actual_source": plan_vs_actual_source,
            "forecast_source": forecast_source,
            "risk_source": risk_source,
            "ensemble_active": "ensemble_prediction" in result and result["ensemble_prediction"].get("active_models", 0) > 0,
        }
        return self._json_safe(result)

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [self._json_safe(item) for item in value]
        if isinstance(value, pd.Timestamp):
            return value.strftime('%Y-%m-%d')
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, np.generic):
            return value.item()
        return value

    def _build_current_state(self, row) -> Dict:
        """Extract current state from latest WMR row."""
        def safe_float(v, mult=100):
            v = pd.to_numeric(v, errors='coerce')
            return round(float(v * mult), 1) if pd.notna(v) else None

        def safe_date(v):
            v = pd.to_datetime(v, errors='coerce')
            return v.strftime('%Y-%m-%d') if pd.notna(v) else None

        comm_progress_raw = safe_float(row.get('overall_comm_progress_100'))
        commissioning_placeholder = self._is_commissioning_placeholder(row, comm_progress_raw)

        return {
            "well_name": str(row.get('well_name_after_spud', '')),
            "pdo_well_id": str(row.get('pdo_well_id', '')),
            "snapshot_date": safe_date(row.get('Week_Number')),
            "rig_no": str(row.get('rig_no', '')),
            "well_type": str(row.get('well_type', '')),
            "cluster": str(row.get('Cluster', '')),
            "buffer_status": str(row.get('buffer_status', '') or ''),
            "progress": safe_float(row.get('over_all_progress_percentages')),
            "loc_prep_progress": safe_float(row.get('overall_loc._preparation_10_100')),
            "engg_progress": safe_float(row.get('overall_engg._10_100')),
            "const_progress": safe_float(row.get('overall_const._10_100')),
            "comm_progress": None if commissioning_placeholder else comm_progress_raw,
            "comm_progress_raw": comm_progress_raw,
            "commissioning_placeholder": commissioning_placeholder,
            "ohl_progress": safe_float(row.get('ohl_progress') if pd.notna(row.get('ohl_progress')) else row.get('overall_ohl_progr_100')),
            "flowline_progress": safe_float(row.get('flowline_construction_progress')),
            "actual_start": safe_date(row.get('actual_start_date')),
            "actual_finish": safe_date(row.get('actual_finish_date')),
            "rig_on": safe_date(row.get('actual_rig_on_date')),
            "rig_off": safe_date(row.get('actual_rig_off_date')),
            "expected_rig_off": safe_date(row.get('exp.rig_off_location_sap_data')),
            "engg_start": safe_date(row.get('engineering_actual_start_date')),
            "engg_finish": safe_date(row.get('engineering_actual_finish_date')),
            "const_start": safe_date(row.get('const._actual_start_date')),
            "const_finish": safe_date(row.get('const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date')),
            "comm_start": safe_date(row.get('actual_comm._start_date')),
            "comm_finish": safe_date(row.get('actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date')),
            "flaf_issue": safe_date(row.get('flaf_issue_date')),
            "moc_raised": str(row.get('moc_raised', '') or ''),
            "moc_approved": str(row.get('moc_approved', '') or ''),
            "engg_kpi_days": (
                int(float(pd.to_numeric(row.get('engg_kpi_after_rig-off_days'), errors='coerce')))
                if pd.notna(pd.to_numeric(row.get('engg_kpi_after_rig-off_days'), errors='coerce'))
                else None
            ),
        }

    def _is_commissioning_placeholder(self, row, comm_progress_pct: Optional[float]) -> bool:
        comm_start = pd.to_datetime(row.get('actual_comm._start_date'), errors='coerce')
        comm_finish = pd.to_datetime(
            row.get('actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date'),
            errors='coerce'
        )
        overall_progress = pd.to_numeric(row.get('over_all_progress_percentages'), errors='coerce')

        return (
            comm_progress_pct is not None
            and float(comm_progress_pct) >= 100.0
            and pd.isna(comm_start)
            and pd.isna(comm_finish)
            and (pd.isna(overall_progress) or float(overall_progress) < 1.0)
        )

    def _build_gantt(self, row) -> List[Dict]:
        """Build Gantt chart data from phase milestones."""
        gantt = []
        for phase in PHASES:
            start = pd.to_datetime(row.get(phase["start_col"]), errors='coerce')
            end = pd.to_datetime(row.get(phase["end_col"]), errors='coerce')

            prog = None
            if phase["progress_col"]:
                p = pd.to_numeric(row.get(phase["progress_col"]), errors='coerce')
                prog = round(float(p * 100), 1) if pd.notna(p) else None

            if phase["id"] == "commissioning" and self._is_commissioning_placeholder(row, prog):
                if pd.notna(end):
                    prog = 100.0
                elif pd.notna(start):
                    prog = 50.0
                else:
                    prog = 0.0

            # For drilling, progress is binary (rig_on exists = started, rig_off = done)
            if phase["id"] == "drilling":
                if pd.notna(end):
                    prog = 100.0
                elif pd.notna(start):
                    prog = 50.0
                else:
                    prog = 0.0

            # Determine status
            if prog is not None and prog >= 100:
                status = "DONE"
            elif pd.notna(start):
                status = "IN_PROGRESS"
            else:
                status = "NOT_STARTED"

            gantt.append({
                "phase_id": phase["id"],
                "label": phase["label"],
                "start": start.strftime('%Y-%m-%d') if pd.notna(start) else None,
                "end": end.strftime('%Y-%m-%d') if pd.notna(end) else None,
                "progress": prog,
                "status": status,
                "color": phase["color"],
                "duration_days": (end - start).days if pd.notna(start) and pd.notna(end) else None,
            })
        return gantt

    def _build_milestones(self, row) -> List[Dict]:
        """Build an ordered milestone ledger with completed, scheduled, overdue, and pending states."""
        events = []
        now = pd.Timestamp.now().normalize()
        commissioning_placeholder = self._is_commissioning_placeholder(
            row,
            pd.to_numeric(row.get('overall_comm_progress_100'), errors='coerce') * 100
            if pd.notna(pd.to_numeric(row.get('overall_comm_progress_100'), errors='coerce'))
            else None,
        )

        for sequence, definition in enumerate(MILESTONE_DEFINITIONS, start=1):
            actual_dt = pd.to_datetime(row.get(definition["column"]), errors='coerce')
            planned_dt = pd.to_datetime(row.get(definition.get("planned_column")), errors='coerce')

            if definition.get("respect_placeholder") and commissioning_placeholder:
                actual_dt = pd.NaT

            status = "PENDING"
            label = definition["label"]
            date_value = None
            timestamp = None
            source_kind = "missing"

            if pd.notna(actual_dt):
                date_value = actual_dt
                timestamp = int(actual_dt.timestamp() * 1000)
                if actual_dt.normalize() > now:
                    status = "SCHEDULED"
                    label = definition["planned_label"]
                    source_kind = "future_actual"
                else:
                    status = "COMPLETED"
                    source_kind = "actual"
            elif pd.notna(planned_dt):
                date_value = planned_dt
                timestamp = int(planned_dt.timestamp() * 1000)
                label = definition["planned_label"]
                if planned_dt.normalize() < now:
                    status = "OVERDUE"
                    source_kind = "planned_overdue"
                else:
                    status = "SCHEDULED"
                    source_kind = "planned"

            events.append({
                "sequence": sequence,
                "label": label,
                "base_label": definition["label"],
                "phase_id": definition.get("phase_id"),
                "date": date_value.strftime('%Y-%m-%d') if date_value is not None and pd.notna(date_value) else None,
                "timestamp": timestamp,
                "status": status,
                "is_future": status == "SCHEDULED",
                "is_completed": status == "COMPLETED",
                "date_kind": source_kind,
            })

        return events

    def _build_history(self, hist_df: pd.DataFrame) -> List[Dict]:
        """Build weekly progress time-series."""
        records = []
        for _, row in hist_df.iterrows():
            wn = row.get('Week_Number')
            prog = pd.to_numeric(row.get('over_all_progress_percentages'), errors='coerce')

            record = {
                "week": wn.strftime('%Y-%m-%d') if pd.notna(wn) else None,
                "progress": round(float(prog * 100), 1) if pd.notna(prog) else None,
            }

            # Add sub-phase progress if available
            for col, key in [
                ('overall_loc._preparation_10_100', 'loc_prep'),
                ('overall_engg._10_100', 'engineering'),
                ('overall_const._10_100', 'construction'),
                ('overall_comm_progress_100', 'commissioning'),
                ('ohl_progress', 'ohl'),
                ('flowline_construction_progress', 'flowline'),
            ]:
                v = pd.to_numeric(row.get(col), errors='coerce')
                record[key] = round(float(v * 100), 1) if pd.notna(v) else None

            records.append(record)
        return records

    def _build_forecast(self, hist_df: pd.DataFrame) -> List[Dict]:
        """
        Generate a 4-week progress forecast using a robust trend on cleaned
        live history. Falls back gracefully if insufficient data.
        """
        prog_col = 'over_all_progress_percentages'
        hist_df = hist_df.dropna(subset=[prog_col, 'Week_Number']).copy()
        hist_df['prog_pct'] = pd.to_numeric(hist_df[prog_col], errors='coerce') * 100
        hist_df = hist_df.dropna(subset=['prog_pct'])

        if len(hist_df) < 2:
            return []

        recent = hist_df.tail(min(14, len(hist_df))).copy()
        recent['day_index'] = (
            pd.to_datetime(recent['Week_Number'], errors='coerce') - pd.to_datetime(recent['Week_Number'], errors='coerce').min()
        ).dt.days.astype(float)
        recent = recent.dropna(subset=['day_index'])

        if recent['day_index'].nunique() < 2:
            return []

        slope_per_day, intercept = np.polyfit(recent['day_index'], recent['prog_pct'], 1)
        slope_per_day = max(0.0, float(slope_per_day))
        residuals = recent['prog_pct'] - (intercept + slope_per_day * recent['day_index'])
        residual_std = float(residuals.std()) if len(recent) > 2 else 2.5
        slope_per_week = slope_per_day * 7.0

        last_prog = float(hist_df['prog_pct'].iloc[-1])
        last_week = hist_df['Week_Number'].iloc[-1]

        forecast = []
        for i in range(1, 5):
            pred = min(100.0, max(0.0, last_prog + slope_per_week * i))
            interval = 1.96 * max(1.0, residual_std) * np.sqrt(i)
            lower = min(100.0, max(0.0, pred - interval))
            upper = min(100.0, max(0.0, pred + interval))

            forecast_date = last_week + timedelta(weeks=i) if pd.notna(last_week) else None

            forecast.append({
                "week": forecast_date.strftime('%Y-%m-%d') if forecast_date else f"+{i}w",
                "predicted": float(round(pred, 1)),
                "lower": float(round(lower, 1)),
                "upper": float(round(upper, 1)),
                "is_forecast": True,
            })

        # Estimate completion
        if slope_per_week > 0.1:
            weeks_to_100 = max(0, (100 - last_prog) / slope_per_week)
            completion_date = None
            if pd.notna(last_week) and weeks_to_100 <= 260:
                completion_date = last_week + timedelta(weeks=float(weeks_to_100))
            if completion_date is not None:
                forecast.append({
                    "estimated_completion": completion_date.strftime('%Y-%m-%d'),
                    "weeks_remaining": round(weeks_to_100, 1),
                    "confidence": "HIGH" if residual_std < 2 else "MEDIUM" if residual_std < 5 else "LOW",
                })

        return forecast

    def _build_plan_vs_actual(self, jp_df: pd.DataFrame) -> Dict:
        """Build plan vs actual comparison from Job_Progress_Report_GB."""
        rows = []
        for _, row in jp_df.iterrows():
            entry = {
                "category": str(row.get('Category', '')),
                "well_name": str(row.get('Well Name / Project Name', '')),
            }
            for w in range(1, 6):
                entry[f"w{w}_plan"] = float(row.get(f'Week-{w} Plan %', 0) or 0)
                entry[f"w{w}_actual"] = float(row.get(f'Week-{w} Actual %', 0) or 0)
            entry["cum_plan"] = float(row.get('Cum-Current Month Plan %', 0) or 0)
            entry["cum_actual"] = float(row.get('Cum-Current Month Actual %', 0) or 0)
            entry["target_end"] = str(row.get('Target End', ''))
            rows.append(entry)
        return {"entries": rows}

    # ── RISK SCORING ──────────────────────────────────────────────────────

    def _compute_risk(self, progress: float) -> Dict:
        """Quick risk tier from progress."""
        progress = float(progress) if pd.notna(progress) else 0
        score = max(0, min(100, (1.0 - progress) * 100))
        if score >= 75: tier = "CRITICAL"
        elif score >= 55: tier = "HIGH_RISK"
        elif score >= 35: tier = "WATCH"
        else: tier = "HEALTHY"
        return {"score": round(score, 1), "tier": tier}

    def _compute_risk_detailed(self, progress: float, velocity: float = 0) -> Dict:
        """Detailed risk scoring with component breakdown."""
        progress = max(0, min(1, float(progress)))
        risk_prog = (1.0 - progress) * 35
        risk_vel = max(0, (0.05 - velocity) / 0.05) * 25 if velocity < 0.05 else 0
        risk_stall = 20 if velocity <= 0 and progress < 0.9 else 0

        total = min(100, risk_prog + risk_vel + risk_stall)

        if total >= 75: tier = "CRITICAL"
        elif total >= 55: tier = "HIGH_RISK"
        elif total >= 35: tier = "WATCH"
        else: tier = "HEALTHY"

        drivers = []
        if risk_prog > 15:
            drivers.append({"factor": "Low Overall Progress", "impact": round(risk_prog, 1), "direction": "negative"})
        if risk_vel > 10:
            drivers.append({"factor": "Slow Velocity", "impact": round(risk_vel, 1), "direction": "negative"})
        if risk_stall > 0:
            drivers.append({"factor": "Progress Stalled", "impact": round(risk_stall, 1), "direction": "negative"})
        if velocity > 0.03:
            drivers.append({"factor": "Strong Momentum", "impact": round(velocity * 100, 1), "direction": "positive"})

        return {
            "score": round(total, 1),
            "tier": tier,
            "components": {
                "progress_risk": round(risk_prog, 1),
                "velocity_risk": round(risk_vel, 1),
                "stall_risk": round(risk_stall, 1),
            },
            "drivers": drivers,
        }

    def _risk_tier_from_score(self, score: float) -> str:
        if score >= 70:
            return "CRITICAL"
        if score >= 40:
            return "HIGH_RISK"
        if score >= 20:
            return "WATCH"
        return "HEALTHY"

    def _unavailable_risk(self, message: str) -> Dict[str, Any]:
        return {
            "score": 0.0,
            "tier": "UNAVAILABLE",
            "components": {},
            "drivers": [
                {
                    "factor": "Risk model unavailable",
                    "impact": 0.0,
                    "direction": "neutral",
                    "description": message,
                }
            ],
        }

    def _compute_model_risk(self, ml_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not ml_data:
            return self._unavailable_risk("No model output was returned for this well.")

        score = float(
            ml_data.get("risk_probability_pct")
            or ml_data.get("delay_risk_pct")
            or ml_data.get("stall_probability_pct")
            or 0.0
        )
        raw_drivers = ml_data.get("risk_drivers") or []
        components: Dict[str, float] = {}
        drivers: List[Dict[str, Any]] = []
        for driver in raw_drivers[:5]:
            feature = str(driver.get("feature") or "model_signal")
            impact = round(abs(float(driver.get("contribution_pct") or driver.get("impact") or 0.0)), 1)
            if impact <= 0:
                continue
            components[feature] = impact
            drivers.append({
                "factor": str(driver.get("label") or feature.replace("_", " ")),
                "impact": impact,
                "direction": str(driver.get("direction") or "negative"),
                "description": str(driver.get("description") or ""),
            })

        if not drivers and ml_data.get("risk_model"):
            drivers.append({
                "factor": "Calibrated delay-risk model",
                "impact": round(score, 1),
                "direction": "negative",
                "description": "Probability is estimated from live historical snapshots near expected rig-off.",
            })

        return {
            "score": round(score, 1),
            "tier": self._risk_tier_from_score(score),
            "components": components,
            "drivers": drivers,
        }

    def _get_portfolio_risk_map(self) -> Dict[str, Dict[str, Any]]:
        now = datetime.utcnow()
        if (
            self._portfolio_risk_cache
            and self._portfolio_risk_refreshed_at is not None
            and (now - self._portfolio_risk_refreshed_at).total_seconds() < PORTFOLIO_RISK_REFRESH_TTL_SECONDS
        ):
            return self._portfolio_risk_cache

        seed_rows: Dict[str, Dict[str, Any]] = {}
        try:
            import requests

            resp = requests.get("http://127.0.0.1:8050/ml/portfolio/live-risk", timeout=3.0)
            resp.raise_for_status()
            payload = resp.json()
            rows = payload.get("rows", [])
            seed_rows = {
                str(row.get("well_id")): row for row in rows if row.get("well_id") is not None
            }
        except Exception:
            seed_rows = {}

        local_risk_map = self._build_local_portfolio_risk_map(seed_rows=seed_rows)
        combined_map = dict(local_risk_map)
        combined_map.update(seed_rows)
        self._portfolio_risk_cache = combined_map
        self._portfolio_risk_refreshed_at = now
        return self._portfolio_risk_cache

    def _history_velocity(self, history: List[Dict[str, Any]]) -> float:
        if len(history) < 2:
            return 0.0
        recent_progress = [float(item.get("progress") or 0.0) for item in history[-4:]]
        deltas = [
            max(0.0, recent_progress[index] - recent_progress[index - 1])
            for index in range(1, len(recent_progress))
        ]
        if not deltas:
            return 0.0
        return round(float(sum(deltas) / len(deltas)), 2)

    def _build_local_portfolio_risk_map(self, seed_rows: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        self._refresh_latest_from_sql()
        if self.latest_df is None or self.latest_df.empty:
            return {}

        history_lookup: Dict[str, pd.DataFrame] = {}
        if self.history_df is not None and not self.history_df.empty and 'pdo_well_id' in self.history_df.columns:
            history_frame = self.history_df.copy()
            history_frame["__well_id"] = history_frame["pdo_well_id"].astype(str).str.strip()
            history_lookup = {
                str(well_id): group.drop(columns=["__well_id"])
                for well_id, group in history_frame.groupby("__well_id")
                if str(well_id).strip()
            }

        local_map: Dict[str, Dict[str, Any]] = {}
        for _, row in self.latest_df.iterrows():
            well_id = str(row.get("pdo_well_id", "")).strip()
            if not well_id:
                continue

            current_state = self._build_current_state(row)
            history_df = history_lookup.get(well_id)
            history: List[Dict[str, Any]] = []
            if history_df is not None and not history_df.empty:
                cleaned_history = self._clean_history_df(history_df, current_state.get("well_name"))
                if not cleaned_history.empty:
                    history = self._build_history(cleaned_history)

            seeded = (seed_rows or {}).get(well_id, {})
            ml_data = None
            if seeded:
                ml_data = {
                    "stall_probability_pct": float(seeded.get("risk_probability_pct") or 0.0),
                }

            risk = self._compute_hybrid_risk(
                current_state,
                history,
                ml_data=ml_data,
                fallback_velocity=self._history_velocity(history),
            )
            local_map[well_id] = {
                "well_id": well_id,
                "well_name": current_state.get("well_name"),
                "risk_probability_pct": round(float(risk.get("score") or 0.0), 1),
                "risk_tier": str(risk.get("tier") or "HEALTHY"),
                "risk_engine": "local_hybrid_schedule_risk_v1",
                "drivers": risk.get("drivers", []),
                "components": risk.get("components", {}),
            }

        return local_map

    def _compute_hybrid_risk(
        self,
        current_state: Dict[str, Any],
        history: List[Dict[str, Any]],
        ml_data: Optional[Dict[str, Any]] = None,
        fallback_velocity: float = 0.0,
    ) -> Dict[str, Any]:
        progress_pct = float(current_state.get("progress") or 0.0)
        components: Dict[str, float] = {
            "schedule_variance_risk": 0.0,
            "overdue_deadline_risk": 0.0,
            "stagnation_risk": 0.0,
            "readiness_risk": 0.0,
            "drilling_execution_risk": 0.0,
            "governance_risk": 0.0,
        }
        drivers: List[Dict[str, Any]] = []
        score = 0.0
        today = pd.Timestamp.today().normalize()

        def add_driver(factor: str, impact: float, description: str, direction: str = "negative"):
            if impact <= 0:
                return
            drivers.append({
                "factor": factor,
                "impact": round(float(impact), 1),
                "direction": direction,
                    "description": description,
            })

        actual_start = pd.to_datetime(
            current_state.get("actual_start") or current_state.get("engg_start") or current_state.get("const_start"),
            errors='coerce',
        )
        expected_rig_off = pd.to_datetime(current_state.get("expected_rig_off"), errors='coerce')
        actual_rig_off = pd.to_datetime(current_state.get("rig_off"), errors='coerce')
        if pd.notna(actual_start) and pd.notna(expected_rig_off) and pd.isna(actual_rig_off):
            total_days = max(1, int((expected_rig_off.normalize() - actual_start.normalize()).days))
            elapsed_days = max(0, min(total_days, int((today - actual_start.normalize()).days)))
            expected_progress_pct = min(100.0, (elapsed_days / total_days) * 100.0)
            schedule_variance_pct = max(0.0, expected_progress_pct - progress_pct)
            if schedule_variance_pct > 0:
                variance_impact = min(35.0, schedule_variance_pct * 0.6)
                components["schedule_variance_risk"] = round(variance_impact, 1)
                score += variance_impact
                add_driver(
                    "Behind expected schedule curve",
                    variance_impact,
                    f"Live progress is {round(schedule_variance_pct, 1)} points behind the expected schedule curve.",
                )

        if pd.notna(expected_rig_off) and pd.isna(actual_rig_off):
            days_delta = int((expected_rig_off.normalize() - today).days)
            if days_delta < 0:
                overdue_impact = min(40.0, 18.0 + abs(days_delta) * 1.4)
                components["overdue_deadline_risk"] = round(overdue_impact, 1)
                score += overdue_impact
                add_driver(
                    "Expected rig-off date is overdue",
                    overdue_impact,
                    f"Rig-off target missed by {abs(days_delta)} days with no actual rig-off recorded.",
                )
            elif days_delta <= 14 and progress_pct < 85:
                near_term_impact = min(20.0, round((14 - days_delta) * 0.9 + max(0.0, 85 - progress_pct) * 0.08, 1))
                components["overdue_deadline_risk"] = max(components["overdue_deadline_risk"], near_term_impact)
                score += near_term_impact
                add_driver(
                    "Near-term schedule pressure",
                    near_term_impact,
                    f"Expected rig-off is within {days_delta} days while progress is {round(progress_pct,1)}%.",
                )

        has_started = any([
            current_state.get("actual_start"),
            current_state.get("engg_start"),
            current_state.get("const_start"),
            current_state.get("rig_on"),
        ])
        if progress_pct == 0.0:
            if pd.notna(expected_rig_off):
                days_to_target = int((expected_rig_off.normalize() - today).days)
                if days_to_target <= 30:
                    readiness_impact = 24.0
                elif days_to_target <= 90:
                    readiness_impact = 14.0
                else:
                    readiness_impact = 6.0
            else:
                readiness_impact = 18.0 if has_started else 8.0
            if has_started:
                readiness_impact = max(readiness_impact, 18.0)
            components["readiness_risk"] = readiness_impact
            score += readiness_impact
            add_driver(
                "No measurable execution progress",
                readiness_impact,
                "Latest live snapshot shows 0% overall progress.",
            )

        hist_progress = [float(point["progress"]) for point in history if point.get("progress") is not None]
        if len(hist_progress) >= 4:
            recent = hist_progress[-4:]
            delta = recent[-1] - recent[0]
            if progress_pct > 0 and delta < 1.0:
                stagnation_impact = 20.0 if progress_pct < 95 else 10.0
                components["stagnation_risk"] = stagnation_impact
                score += stagnation_impact
                add_driver(
                    "Progress stagnation",
                    stagnation_impact,
                    f"Progress moved only {round(delta, 1)} points across the last {len(recent)} history points.",
                )
        elif fallback_velocity <= 0 and progress_pct > 0:
            components["stagnation_risk"] = 15.0
            score += 15.0
            add_driver(
                "Flat recent velocity",
                15.0,
                "Fallback velocity estimate is flat or negative.",
            )

        if str(current_state.get("buffer_status") or "").upper() == "ROL" and progress_pct < 60:
            drilling_impact = 18.0
            components["drilling_execution_risk"] = drilling_impact
            score += drilling_impact
            add_driver(
                "Drilling with low completion",
                drilling_impact,
                "Well is rig-on-location with low overall completion.",
            )

        moc_raised = str(current_state.get("moc_raised") or "").strip().upper()
        moc_approved = str(current_state.get("moc_approved") or "").strip().upper()
        if moc_raised in {"YES", "Y", "TRUE"} and moc_approved not in {"YES", "Y", "TRUE"}:
            governance_impact = 10.0
            components["governance_risk"] = governance_impact
            score += governance_impact
            add_driver(
                "Pending MOC governance",
                governance_impact,
                "MOC has been raised but not approved in the latest live snapshot.",
            )

        # ML signal is kept as supporting evidence only, not part of the official score.
        ml_signal = float((ml_data or {}).get("stall_probability_pct") or 0.0)
        if ml_signal > 0:
            components["ml_early_warning_signal"] = round(ml_signal, 1)
            add_driver(
                "ML early-warning signal",
                round(min(ml_signal, 25.0), 1),
                "Secondary model signal only; not used in the official headline score.",
            )

        score = round(float(min(100.0, max(0.0, score))), 1)
        return {
            "score": score,
            "tier": self._risk_tier_from_score(score),
            "components": components,
            "drivers": drivers[:5],
        }

    # ── PORTFOLIO SUMMARY ─────────────────────────────────────────────────

    def get_portfolio_summary(self) -> Dict:
        """Aggregate portfolio-level metrics."""
        self._refresh_latest_from_sql()
        if self.latest_df is None:
            return {}

        df = self.latest_df.copy()
        df['prog'] = pd.to_numeric(df['over_all_progress_percentages'], errors='coerce')

        total = len(df)
        completed = int((df['prog'] >= 1.0).sum())
        active = int(((df['prog'] > 0) & (df['prog'] < 1.0)).sum())
        not_started = int((df['prog'].isna() | (df['prog'] == 0)).sum())

        # ── Schedule delay: expected rig-off passed but no actual rig-off ──
        delayed_wells = 0
        on_track_wells = 0
        at_risk_detail = []
        today = pd.Timestamp.today().normalize()

        exp_col = None
        for c in df.columns:
            if 'exp' in c.lower() and 'rig_off' in c.lower():
                exp_col = c
                break

        if exp_col:
            df['_exp_rig_off'] = pd.to_datetime(df[exp_col], errors='coerce')
            df['_act_rig_off'] = pd.to_datetime(
                df.get('actual_rig_off_date', pd.Series(dtype='datetime64[ns]')),
                errors='coerce'
            )

            # Delayed: expected date passed, no actual rig-off
            mask_delayed = (df['_exp_rig_off'] < today) & (df['_act_rig_off'].isna())
            delayed_wells = int(mask_delayed.sum())
            on_track_wells = active - delayed_wells

            # Top at-risk wells (biggest delay)
            delayed_df = df[mask_delayed].copy()
            if len(delayed_df) > 0:
                delayed_df['_delay_days'] = (today - delayed_df['_exp_rig_off']).dt.days
                delayed_df = delayed_df.sort_values('_delay_days', ascending=False)
                for _, row in delayed_df.head(10).iterrows():
                    well_name = row.get('well_name_after_spud', row.get('pdo_well_id', ''))
                    at_risk_detail.append({
                        "well_id": str(row.get('pdo_well_id', '')),
                        "well_name": str(well_name),
                        "progress": round(float(row['prog'] * 100), 1) if pd.notna(row['prog']) else 0,
                        "delay_days": int(row['_delay_days']),
                        "rig_no": str(row.get('rig_no', '')),
                        "cluster": str(row.get('Cluster', '')),
                    })

        # Tier distribution
        tiers = {"CRITICAL": 0, "HIGH_RISK": 0, "WATCH": 0, "HEALTHY": 0}
        risk_map = self._get_portfolio_risk_map()
        for _, row in df.iterrows():
            risk_row = risk_map.get(str(row.get('pdo_well_id', '')))
            tier = str((risk_row or {}).get('risk_tier') or "HEALTHY")
            if tier in tiers:
                tiers[tier] += 1

        # Rig performance
        rig_perf = df.groupby('rig_no')['prog'].agg(['mean', 'count']).reset_index()
        rig_perf.columns = ['rig_no', 'avg_progress', 'well_count']
        rig_perf['avg_progress'] = (rig_perf['avg_progress'] * 100).round(1)
        rig_perf = rig_perf.sort_values('avg_progress', ascending=False)

        return {
            "total_wells": total,
            "completed": completed,
            "active": active,
            "not_started": not_started,
            "delayed_wells": delayed_wells,
            "on_track_wells": on_track_wells,
            "at_risk_wells": at_risk_detail,
            "avg_progress": round(float(df['prog'].mean() * 100), 1) if not df['prog'].isna().all() else 0,
            "risk_summary": tiers,
            "tier_distribution": tiers,
            "rig_performance": rig_perf.head(15).to_dict('records'),
        }
