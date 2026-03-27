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
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("forecast_engine")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prediction_data")

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


class ForecastEngine:
    """Production CPU inference engine for well-level forecasting."""

    def __init__(self):
        self.history_df: Optional[pd.DataFrame] = None
        self.latest_df: Optional[pd.DataFrame] = None
        self.job_progress_df: Optional[pd.DataFrame] = None
        self._load_data()

    def _load_data(self):
        """Load pre-extracted CSV data."""
        hist_path = os.path.join(DATA_DIR, "wmr_full_history.csv")
        latest_path = os.path.join(DATA_DIR, "wmr_latest.csv")
        jp_path = os.path.join(DATA_DIR, "job_progress_gb.csv")

        if os.path.exists(hist_path):
            self.history_df = pd.read_csv(hist_path, low_memory=False)
            # Parse dates
            for c in self.history_df.columns:
                if 'date' in c.lower() or c == 'Week_Number':
                    self.history_df[c] = pd.to_datetime(self.history_df[c], errors='coerce')
            # Parse progress columns
            prog_cols = [c for c in self.history_df.columns 
                        if 'progress' in c.lower() or c.endswith('_5') or c.endswith('_60') 
                        or c.endswith('_20') or c.endswith('_100')]
            for c in prog_cols:
                self.history_df[c] = pd.to_numeric(self.history_df[c], errors='coerce')
            logger.info(f"[FE] Loaded history: {len(self.history_df)} rows, "
                       f"{self.history_df['pdo_well_id'].nunique()} wells")

        if os.path.exists(latest_path):
            self.latest_df = pd.read_csv(latest_path, low_memory=False)
            for c in self.latest_df.columns:
                if 'date' in c.lower() or c == 'Week_Number':
                    self.latest_df[c] = pd.to_datetime(self.latest_df[c], errors='coerce')
            logger.info(f"[FE] Loaded latest: {len(self.latest_df)} wells")

        if os.path.exists(jp_path):
            self.job_progress_df = pd.read_csv(jp_path, low_memory=False)
            logger.info(f"[FE] Loaded job progress: {len(self.job_progress_df)} rows")

    # ── WELL LIST ─────────────────────────────────────────────────────────

    def get_well_list(self) -> List[Dict]:
        """Return summary list of all wells for the selector."""
        if self.latest_df is None:
            return []
        
        wells = []
        for _, row in self.latest_df.iterrows():
            prog = pd.to_numeric(row.get('over_all_progress_percentages'), errors='coerce')
            prog_pct = round(float(prog * 100), 1) if pd.notna(prog) else 0.0
            
            # Determine status
            if prog_pct >= 100:
                status = "COMPLETED"
            elif row.get('buffer_status') == 'ROL':
                status = "DRILLING"
            elif prog_pct > 0:
                status = "IN_PROGRESS"
            else:
                status = "NOT_STARTED"
            
            # Risk tier
            risk = self._compute_risk(prog if pd.notna(prog) else 0)
            
            wells.append({
                "pdo_well_id": str(row.get('pdo_well_id', '')),
                "well_name": str(row.get('well_name_after_spud', '')),
                "rig_no": str(row.get('rig_no', '')),
                "well_type": str(row.get('well_type', '')),
                "cluster": str(row.get('Cluster', '')),
                "progress_pct": prog_pct,
                "status": status,
                "risk_tier": risk['tier'],
                "risk_score": risk['score'],
                "buffer_status": str(row.get('buffer_status', '') or ''),
            })
        
        # Sort: critical first, then by progress ascending
        tier_order = {"CRITICAL": 0, "HIGH_RISK": 1, "WATCH": 2, "HEALTHY": 3}
        wells.sort(key=lambda w: (tier_order.get(w['risk_tier'], 4), w['progress_pct']))
        return wells

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
        }

        # 1. Current state from latest
        if self.latest_df is not None:
            match = self.latest_df[
                self.latest_df['pdo_well_id'].astype(str).str.strip() == str(well_id).strip()
            ]
            if not match.empty:
                row = match.iloc[0]
                result["current_state"] = self._build_current_state(row)
                result["gantt"] = self._build_gantt(row)
                result["milestones"] = self._build_milestones(row)

        # 2. Historical time-series
        if self.history_df is not None:
            hist = self.history_df[
                self.history_df['pdo_well_id'].astype(str).str.strip() == str(well_id).strip()
            ].sort_values('Week_Number')
            
            if not hist.empty:
                result["history"] = self._build_history(hist)
                result["forecast"] = self._build_forecast(hist)

        # 3. Plan vs Actual from Job Progress
        if self.job_progress_df is not None:
            jp_match = self.job_progress_df[
                self.job_progress_df['Well ID'].astype(str).str.strip() == str(well_id).strip()
            ]
            if not jp_match.empty:
                result["plan_vs_actual"] = self._build_plan_vs_actual(jp_match)

        # 4. Risk / ML Hooks via Orhestrator
        prog = result["current_state"].get("progress", 0) / 100.0
        hist_data = result.get("history", [])
        
        # Call the new Advanced CPU ML Pipeline (Sync call)
        import requests
        try:
            ml_resp = requests.get(f"http://127.0.0.1:8050/ml/forecast/{well_id}", timeout=2.5)
            if ml_resp.status_code == 200:
                ml_data = ml_resp.json()
                result["ml_intelligence"] = ml_data
                result["risk"] = {
                    "score": ml_data.get("stall_probability_pct", 0),
                    "tier": "CRITICAL" if ml_data.get("stall_probability_pct", 0) >= 70 else 
                            "HIGH_RISK" if ml_data.get("stall_probability_pct", 0) >= 40 else 
                            "WATCH" if ml_data.get("stall_probability_pct", 0) >= 20 else "HEALTHY"
                }
                # Inject StatsForecast logic directly into 'forecast' mapping
                if ml_data.get("stats_forecast"):
                    result["forecast"] = ml_data.get("stats_forecast")
            else:
                velocity = 0
                if len(hist_data) >= 2:
                    velocity = (hist_data[-1].get("progress", 0) - hist_data[-2].get("progress", 0)) / 100.0
                result["risk"] = self._compute_risk_detailed(prog, velocity)
                result["ml_intelligence"] = {"hidden_insights": [], "error": "ML Orchestrator unreachable on port 8050"}
        except requests.exceptions.RequestException:
            # Fallback to math if ML Server is off
            velocity = 0
            if len(hist_data) >= 2:
                velocity = (hist_data[-1].get("progress", 0) - hist_data[-2].get("progress", 0)) / 100.0
            result["risk"] = self._compute_risk_detailed(prog, velocity)
            result["ml_intelligence"] = {"hidden_insights": [], "error": "ML Orchestrator unreachable on port 8050"}

        return result

    def _build_current_state(self, row) -> Dict:
        """Extract current state from latest WMR row."""
        def safe_float(v, mult=100):
            v = pd.to_numeric(v, errors='coerce')
            return round(float(v * mult), 1) if pd.notna(v) else None

        def safe_date(v):
            v = pd.to_datetime(v, errors='coerce')
            return v.strftime('%Y-%m-%d') if pd.notna(v) else None

        return {
            "well_name": str(row.get('well_name_after_spud', '')),
            "pdo_well_id": str(row.get('pdo_well_id', '')),
            "rig_no": str(row.get('rig_no', '')),
            "well_type": str(row.get('well_type', '')),
            "cluster": str(row.get('Cluster', '')),
            "buffer_status": str(row.get('buffer_status', '') or ''),
            "progress": safe_float(row.get('over_all_progress_percentages')),
            "loc_prep_progress": safe_float(row.get('overall_loc._preparation_10_100')),
            "engg_progress": safe_float(row.get('overall_engg._10_100')),
            "const_progress": safe_float(row.get('overall_const._10_100')),
            "comm_progress": safe_float(row.get('overall_comm_progress_100')),
            "ohl_progress": safe_float(row.get('ohl_progress')),
            "flowline_progress": safe_float(row.get('flowline_construction_progress')),
            "actual_start": safe_date(row.get('actual_start_date')),
            "actual_finish": safe_date(row.get('actual_finish_date')),
            "rig_on": safe_date(row.get('actual_rig_on_date')),
            "rig_off": safe_date(row.get('actual_rig_off_date')),
            "engg_start": safe_date(row.get('engineering_actual_start_date')),
            "engg_finish": safe_date(row.get('engineering_actual_finish_date')),
            "const_start": safe_date(row.get('const._actual_start_date')),
            "const_finish": safe_date(row.get('const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date')),
            "comm_start": safe_date(row.get('actual_comm._start_date')),
            "comm_finish": safe_date(row.get('actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date')),
            "flaf_issue": safe_date(row.get('flaf_issue_date')),
            "moc_raised": str(row.get('moc_raised', '') or ''),
            "moc_approved": str(row.get('moc_approved', '') or ''),
            "engg_kpi_days": int(row.get('engg_kpi_after_rig-off_days') or 0) if pd.notna(row.get('engg_kpi_after_rig-off_days')) else None,
        }

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
        """Build milestone timeline (what happened, when). Dynamically adjusts tense."""
        events = []
        
        # Format: (Past Tense, Future Tense, Database Column)
        milestone_definitions = [
            ("FLAF Issued", "Target FLAF Issue", "flaf_issue_date"),
            ("Engineering Started", "Planned Eng. Start", "engineering_actual_start_date"),
            ("Engineering Completed", "Planned Eng. Finish", "engineering_actual_finish_date"),
            ("Location Prep Started", "Scheduled Loc Prep Start", "actual_start_date"),
            ("Location Prep Completed", "Scheduled Loc Prep Finish", "actual_finish_date"),
            ("Construction Started", "Planned Const. Start", "const._actual_start_date"),
            ("Construction Completed", "Planned Const. Finish", "const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date"),
            ("Rig On", "Scheduled Rig On", "actual_rig_on_date"),
            ("Rig Off", "Scheduled Rig Off", "actual_rig_off_date"),
            ("WLCTF Acceptance", "Target WLCTF Acceptance", "wlctf_acceptanceapproval_from_production"),
            ("Hoist/FBU On", "Scheduled Hoist On", "actual_hoist_fbu_rsr_on_date"),
            ("Hoist/FBU Off", "Scheduled Hoist Off", "actual_hoist_fbu_rsr_off_date"),
            ("Commissioning Started", "Planned Comm. Start", "actual_comm._start_date"),
            ("Commissioning Completed", "Planned Comm. Finish", "actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date"),
        ]
        
        now = pd.Timestamp.now()
        
        for past_label, future_label, col in milestone_definitions:
            dt = pd.to_datetime(row.get(col), errors='coerce')
            if pd.notna(dt):
                # If date is in the future, use the predictive language
                is_future = dt > now
                events.append({
                    "label": future_label if is_future else past_label,
                    "date": dt.strftime('%Y-%m-%d'),
                    "timestamp": int(dt.timestamp() * 1000),
                    "is_future": bool(is_future)
                })
        
        events.sort(key=lambda e: e["timestamp"])
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
            ]:
                v = pd.to_numeric(row.get(col), errors='coerce')
                record[key] = round(float(v * 100), 1) if pd.notna(v) else None
            
            records.append(record)
        return records

    def _build_forecast(self, hist_df: pd.DataFrame) -> List[Dict]:
        """
        Generate 4-week progress forecast using linear extrapolation
        with confidence bands. Falls back gracefully if insufficient data.
        """
        prog_col = 'over_all_progress_percentages'
        hist_df = hist_df.dropna(subset=[prog_col, 'Week_Number']).copy()
        hist_df['prog_pct'] = pd.to_numeric(hist_df[prog_col], errors='coerce') * 100
        hist_df = hist_df.dropna(subset=['prog_pct'])
        
        if len(hist_df) < 2:
            return []
        
        # Calculate velocity from recent data (last 4 weeks if available)
        recent = hist_df.tail(min(4, len(hist_df)))
        velocities = recent['prog_pct'].diff().dropna()
        
        if len(velocities) == 0:
            return []
        
        avg_velocity = float(velocities.mean())
        vel_std = float(velocities.std()) if len(velocities) > 1 else abs(avg_velocity * 0.3)
        
        last_prog = float(hist_df['prog_pct'].iloc[-1])
        last_week = hist_df['Week_Number'].iloc[-1]
        
        forecast = []
        for i in range(1, 5):
            pred = min(100.0, max(0.0, last_prog + avg_velocity * i))
            lower = min(100.0, max(0.0, pred - 1.96 * vel_std * np.sqrt(i)))
            upper = min(100.0, max(0.0, pred + 1.96 * vel_std * np.sqrt(i)))
            
            forecast_date = last_week + timedelta(weeks=i) if pd.notna(last_week) else None
            
            forecast.append({
                "week": forecast_date.strftime('%Y-%m-%d') if forecast_date else f"+{i}w",
                "predicted": round(pred, 1),
                "lower": round(lower, 1),
                "upper": round(upper, 1),
                "is_forecast": True,
            })
        
        # Estimate completion
        if avg_velocity > 0:
            weeks_to_100 = max(0, (100 - last_prog) / avg_velocity)
            completion_date = last_week + timedelta(weeks=weeks_to_100) if pd.notna(last_week) else None
            if completion_date:
                forecast.append({
                    "estimated_completion": completion_date.strftime('%Y-%m-%d'),
                    "weeks_remaining": round(weeks_to_100, 1),
                    "confidence": "HIGH" if vel_std < 2 else "MEDIUM" if vel_std < 5 else "LOW",
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

    # ── PORTFOLIO SUMMARY ─────────────────────────────────────────────────

    def get_portfolio_summary(self) -> Dict:
        """Aggregate portfolio-level metrics."""
        if self.latest_df is None:
            return {}
        
        df = self.latest_df.copy()
        df['prog'] = pd.to_numeric(df['over_all_progress_percentages'], errors='coerce')
        
        total = len(df)
        completed = int((df['prog'] >= 1.0).sum())
        active = int(((df['prog'] > 0) & (df['prog'] < 1.0)).sum())
        not_started = int((df['prog'].isna() | (df['prog'] == 0)).sum())
        
        # Tier distribution
        tiers = {"CRITICAL": 0, "HIGH_RISK": 0, "WATCH": 0, "HEALTHY": 0}
        for _, row in df.iterrows():
            r = self._compute_risk(row['prog'] if pd.notna(row['prog']) else 0)
            tiers[r['tier']] += 1
        
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
            "avg_progress": round(float(df['prog'].mean() * 100), 1) if not df['prog'].isna().all() else 0,
            "tier_distribution": tiers,
            "rig_performance": rig_perf.head(15).to_dict('records'),
        }
