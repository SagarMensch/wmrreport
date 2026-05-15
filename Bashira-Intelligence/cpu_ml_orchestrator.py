"""
Bashira Intelligence - CPU ML Microservice (FastAPI on Port 8050)
Runs native Windows-compatible state-of-the-art CPU ML libraries.
- StatsForecast (Nixtla) for AutoARIMA time-series non-linear trajectory forecasting
- LightGBM + SHAP for extracting hidden targets (Rig efficiency, Stall risk)
"""

import os
import io
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from pydantic import BaseModel
import pyodbc
from fastapi import FastAPI, HTTPException
import uvicorn

import lightgbm as lgb
import shap
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ml_engine")

app = FastAPI(title="Bashira CPU ML Microservice")

# Storage for trained models
_lgb_model = None
_explainer = None
_feature_cols = []
_hist_df = None
_latest_features_df = None
_job_progress_df = None
_risk_model_metrics: Dict[str, Any] = {}
_scenario_panel_df = None
_scenario_models: Dict[str, Any] = {}
_scenario_feature_cols: List[str] = []
_cluster_density_map: Dict[str, float] = {}
_rig_weekly_momentum_map: Dict[str, float] = {}

# S-Learner Causal Meta-Estimator
_causal_s_learner = None
_rig_encoder = None
_loc_encoder = None
_causal_panel_df = None

# SQL Connection Config
from dotenv import load_dotenv
load_dotenv()
CONN_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={os.getenv('SQL_SERVER', '(localdb)\\\\MSSQLLocalDB')};"
    f"DATABASE={os.getenv('SQL_DATABASE', 'AppMasterDB')};"
    "Trusted_Connection=yes;Encrypt=Optional;TrustServerCertificate=yes;Connection Timeout=30;"
)

def build_models():
    """Extract Data from SQL and train core ML Models synchronously on boot."""
    global _lgb_model, _explainer, _feature_cols, _hist_df, _latest_features_df, _job_progress_df
    global _scenario_panel_df, _scenario_models, _scenario_feature_cols
    global _cluster_density_map, _rig_weekly_momentum_map, _risk_model_metrics
    log.info("Connecting to SQL Server ATNM_Dev...")

    try:
        conn = pyodbc.connect(CONN_STRING, timeout=30)
        query = '''
            SELECT pdo_well_id, well_name_after_spud, rig_no, well_location, [buffer_status],
                   over_all_progress_percentages, Week_Number,
                   engineering_actual_start_date, actual_start_date,
                   actual_rig_on_date, actual_rig_off_date, NULL as [exp.rig_off_location_sap_data],
                   flaf_issue_date, NULL as [date_-_material_available_at_site]
            FROM WMR_Full
            WHERE pdo_well_id IS NOT NULL
              AND Week_Number IS NOT NULL
        '''
        df = pd.read_sql(query, conn)
        conn.close()
    except Exception as e:
        log.error(f"SQL Connection Failed. Falling back to local cache: {e}")
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        cache_path = os.path.join(curr_dir, "prediction_data", "wmr_full_history.csv")
        df = pd.read_csv(cache_path, low_memory=False)

    for required_col in [
        'buffer_status',
        'actual_rig_on_date',
        'actual_rig_off_date',
        'exp.rig_off_location_sap_data',
        'engineering_actual_start_date',
        'actual_start_date',
        'flaf_issue_date',
        'date_-_material_available_at_site',
    ]:
        if required_col not in df.columns:
            df[required_col] = np.nan
    if 'Cluster' not in df.columns:
        df['Cluster'] = df['well_location']

    df['Week_Number'] = pd.to_datetime(df['Week_Number'], errors='coerce').dt.tz_localize(None)
    df['over_all_progress_percentages'] = pd.to_numeric(df['over_all_progress_percentages'], errors='coerce')
    df['flaf_issue_date'] = pd.to_datetime(df['flaf_issue_date'], errors='coerce').dt.tz_localize(None)
    df['engineering_actual_start_date'] = pd.to_datetime(df['engineering_actual_start_date'], errors='coerce').dt.tz_localize(None)
    df['actual_start_date'] = pd.to_datetime(df['actual_start_date'], errors='coerce').dt.tz_localize(None)
    df['actual_rig_on_date'] = pd.to_datetime(df['actual_rig_on_date'], errors='coerce').dt.tz_localize(None)
    df['actual_rig_off_date'] = pd.to_datetime(df['actual_rig_off_date'], errors='coerce').dt.tz_localize(None)
    df['exp.rig_off_location_sap_data'] = pd.to_datetime(df['exp.rig_off_location_sap_data'], errors='coerce').dt.tz_localize(None)
    try:
        df['date_-_material_available_at_site'] = pd.to_datetime(df['date_-_material_available_at_site'], errors='coerce').dt.tz_localize(None)
    except Exception:
        df['date_-_material_available_at_site'] = pd.NaT

    df['material_lead_days'] = (df['date_-_material_available_at_site'] - df['flaf_issue_date']).dt.days
    df['material_lead_days'] = df['material_lead_days'].fillna(30)
    df['cluster_key'] = (
        df['Cluster']
        .fillna(df['well_location'])
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .replace({"": "Unknown"})
    )
    df['buffer_status'] = df['buffer_status'].fillna("").astype(str).str.strip()

    df = df.dropna(subset=['Week_Number', 'over_all_progress_percentages'])
    if 'well_name_after_spud' not in df.columns:
        df['well_name_after_spud'] = df['pdo_well_id'].astype(str)
    _hist_df = df.copy()

    log.info(f"Loaded {len(_hist_df)} rows for time-series / model training.")

    curr_dir = os.path.dirname(os.path.abspath(__file__))
    jp_cache_path = os.path.join(curr_dir, "prediction_data", "job_progress_gb.csv")
    if os.path.exists(jp_cache_path):
        try:
            _job_progress_df = pd.read_csv(jp_cache_path, low_memory=False)
        except Exception as e:
            log.warning(f"Failed to load job_progress_gb.csv for category mapping: {e}")
            _job_progress_df = None

    # ----------------------------------------------------
    # FEATURE ENGINEERING (LightGBM Tabular Prep)
    # ----------------------------------------------------
    latest_per_well = df.sort_values('Week_Number').groupby('pdo_well_id').last().reset_index()

    latest_per_well['progress'] = latest_per_well['over_all_progress_percentages']

    # Compute historic Rig Efficiency (average progress)
    rig_eff = latest_per_well.groupby('rig_no')['progress'].mean().to_dict()
    cluster_dens = latest_per_well.groupby('cluster_key')['pdo_well_id'].count().to_dict()
    _cluster_density_map = {str(k): float(v) for k, v in cluster_dens.items()}

    latest_per_well['rig_efficiency'] = latest_per_well['rig_no'].map(rig_eff).fillna(0)
    latest_per_well['cluster_density'] = latest_per_well['cluster_key'].map(cluster_dens).fillna(0)

    first_per_well = df.sort_values('Week_Number').groupby('pdo_well_id').first().reset_index()
    latest_per_well['start_prog'] = latest_per_well['pdo_well_id'].map(first_per_well.set_index('pdo_well_id')['over_all_progress_percentages']).fillna(0)
    latest_per_well['momentum'] = latest_per_well['progress'] - latest_per_well['start_prog']

    log.info("Training governed scenario engine...")
    scenario_panel = df.sort_values(['pdo_well_id', 'Week_Number']).copy()
    scenario_panel['next_progress'] = scenario_panel.groupby('pdo_well_id')['over_all_progress_percentages'].shift(-1)
    scenario_panel['weekly_momentum'] = scenario_panel['next_progress'] - scenario_panel['over_all_progress_percentages']

    progress_delta = scenario_panel.groupby('pdo_well_id')['over_all_progress_percentages'].diff().fillna(0)
    scenario_panel['recent_momentum_3w'] = (
        progress_delta.groupby(scenario_panel['pdo_well_id'])
        .rolling(3, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
        .fillna(0)
    )
    scenario_panel['progress'] = scenario_panel['over_all_progress_percentages'].clip(lower=0, upper=1)
    scenario_panel['has_engineering_started'] = scenario_panel['engineering_actual_start_date'].notna().astype(int)
    scenario_panel['has_location_started'] = scenario_panel['actual_start_date'].notna().astype(int)
    scenario_panel['is_rig_on'] = (
        scenario_panel['actual_rig_on_date'].notna()
        & (scenario_panel['actual_rig_off_date'].isna() | (scenario_panel['buffer_status'].str.upper() == "ROL"))
    ).astype(int)
    scenario_panel['days_to_expected_rig_off'] = (
        scenario_panel['exp.rig_off_location_sap_data'] - scenario_panel['Week_Number']
    ).dt.days.clip(lower=-90, upper=180).fillna(90)
    scenario_panel['cluster_density'] = scenario_panel['cluster_key'].map(cluster_dens).fillna(0)

    actual_start_norm = pd.to_datetime(scenario_panel['actual_start_date'], errors='coerce')
    expected_rig_off_norm = pd.to_datetime(scenario_panel['exp.rig_off_location_sap_data'], errors='coerce')
    elapsed_days = (scenario_panel['Week_Number'] - actual_start_norm).dt.days
    total_days = (expected_rig_off_norm - actual_start_norm).dt.days
    with np.errstate(divide='ignore', invalid='ignore'):
        expected_curve = np.where(
            (total_days > 0) & (~pd.isna(elapsed_days)),
            np.clip(elapsed_days / total_days, 0, 1),
            np.nan,
        )
    scenario_panel['schedule_pressure'] = np.clip(
        np.nan_to_num(expected_curve - scenario_panel['progress'], nan=0.0),
        0,
        1,
    )

    def _stage_label(row: pd.Series) -> str:
        if bool(row.get('is_rig_on', 0)):
            return "drilling"
        if bool(row.get('has_location_started', 0)) and float(row.get('progress', 0) or 0) >= 0.55:
            return "construction"
        if bool(row.get('has_engineering_started', 0)) and float(row.get('progress', 0) or 0) >= 0.15:
            return "engineering"
        if bool(row.get('has_location_started', 0)) or float(row.get('progress', 0) or 0) > 0:
            return "readiness"
        return "prestart"

    scenario_panel['stage'] = scenario_panel.apply(_stage_label, axis=1)
    scenario_panel['progress_bucket'] = (scenario_panel['progress'] * 10).round().clip(lower=0, upper=10) / 10
    scenario_panel = scenario_panel.dropna(subset=['weekly_momentum']).copy()
    scenario_panel = scenario_panel[(scenario_panel['weekly_momentum'] >= 0) & (scenario_panel['weekly_momentum'] <= 0.35)]

    rig_weekly = (
        scenario_panel.groupby('rig_no')['weekly_momentum']
        .median()
        .dropna()
        .to_dict()
    )
    _rig_weekly_momentum_map = {str(k): float(v) for k, v in rig_weekly.items()}
    scenario_panel['rig_efficiency_weekly'] = scenario_panel['rig_no'].map(rig_weekly).fillna(scenario_panel['weekly_momentum'].median())

    _scenario_feature_cols = [
        'progress',
        'recent_momentum_3w',
        'rig_efficiency_weekly',
        'cluster_density',
        'material_lead_days',
        'has_engineering_started',
        'has_location_started',
        'is_rig_on',
        'days_to_expected_rig_off',
        'schedule_pressure',
    ]

    log.info("Training calibrated delay-risk model...")
    latest_snapshot = scenario_panel.sort_values('Week_Number').groupby('pdo_well_id').last().reset_index()
    _latest_features_df = latest_snapshot[[
        'pdo_well_id',
        'well_name_after_spud',
        'rig_no',
        'well_location',
        'progress',
        'recent_momentum_3w',
        'rig_efficiency_weekly',
        'cluster_density',
        'material_lead_days',
        'has_engineering_started',
        'has_location_started',
        'is_rig_on',
        'days_to_expected_rig_off',
        'schedule_pressure',
    ]].copy()
    _feature_cols = list(_scenario_feature_cols)

    risk_panel = scenario_panel.dropna(subset=['exp.rig_off_location_sap_data']).copy()
    final_actual_rig_off = (
        scenario_panel.sort_values('Week_Number')
        .groupby('pdo_well_id')['actual_rig_off_date']
        .last()
        .to_dict()
    )
    risk_panel['final_actual_rig_off'] = risk_panel['pdo_well_id'].map(final_actual_rig_off)
    risk_panel = risk_panel[
        (risk_panel['days_to_expected_rig_off'] <= 28)
        & (risk_panel['days_to_expected_rig_off'] >= -14)
    ].copy()
    risk_panel['miss_target'] = 1
    known_actual = risk_panel['final_actual_rig_off'].notna()
    risk_panel.loc[known_actual, 'miss_target'] = (
        risk_panel.loc[known_actual, 'final_actual_rig_off']
        > risk_panel.loc[known_actual, 'exp.rig_off_location_sap_data']
    ).astype(int)

    _risk_model_metrics = {
        "rows": int(len(risk_panel)),
        "positive_rate": round(float(risk_panel['miss_target'].mean()), 4) if len(risk_panel) else 0.0,
    }

    if len(risk_panel) >= 30 and risk_panel['miss_target'].nunique() > 1:
        X_risk = risk_panel[_feature_cols].fillna(0)
        y_risk = risk_panel['miss_target'].astype(int)
        X_train, X_test, y_train, y_test = train_test_split(
            X_risk,
            y_risk,
            test_size=0.2,
            random_state=42,
            stratify=y_risk,
        )

        calibrated_estimator = CalibratedClassifierCV(
            estimator=lgb.LGBMClassifier(
                n_estimators=260,
                learning_rate=0.04,
                max_depth=6,
                min_child_samples=25,
                subsample=0.9,
                colsample_bytree=0.85,
                random_state=42,
                n_jobs=-1,
                verbose=-1,
            ),
            method="sigmoid",
            cv=3,
        )
        calibrated_estimator.fit(X_train, y_train)
        _lgb_model = calibrated_estimator

        shap_estimator = lgb.LGBMClassifier(
            n_estimators=260,
            learning_rate=0.04,
            max_depth=6,
            min_child_samples=25,
            subsample=0.9,
            colsample_bytree=0.85,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
        shap_estimator.fit(X_risk, y_risk)
        _explainer = shap.TreeExplainer(shap_estimator)

        test_prob = calibrated_estimator.predict_proba(X_test)[:, 1]
        _risk_model_metrics.update({
            "auc": round(float(roc_auc_score(y_test, test_prob)), 4),
            "brier": round(float(brier_score_loss(y_test, test_prob)), 4),
        })
    else:
        _lgb_model = None
        _explainer = None

    _scenario_panel_df = scenario_panel.copy()

    if len(_scenario_panel_df) >= 200:
        X_exec = _scenario_panel_df[_scenario_feature_cols].copy()
        y_exec = _scenario_panel_df['weekly_momentum'].clip(lower=0, upper=0.35)
        _scenario_models = {
            "base": lgb.LGBMRegressor(
                n_estimators=220,
                learning_rate=0.04,
                max_depth=6,
                min_child_samples=25,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
                n_jobs=-1,
                verbose=-1,
            ),
            "q10": lgb.LGBMRegressor(
                objective="quantile",
                alpha=0.1,
                n_estimators=180,
                learning_rate=0.04,
                max_depth=6,
                min_child_samples=20,
                random_state=42,
                n_jobs=-1,
                verbose=-1,
            ),
            "q90": lgb.LGBMRegressor(
                objective="quantile",
                alpha=0.9,
                n_estimators=180,
                learning_rate=0.04,
                max_depth=6,
                min_child_samples=20,
                random_state=42,
                n_jobs=-1,
                verbose=-1,
            ),
        }
        for model in _scenario_models.values():
            model.fit(X_exec, y_exec)
    else:
        _scenario_models = {}

    # ----------------------------------------------------
    # TRAIN GENUINE CAUSAL S-LEARNER (LightGBM Meta-Estimator)
    # CATE = Conditional Average Treatment Effect per well
    # ----------------------------------------------------
    global _causal_s_learner, _rig_encoder, _loc_encoder, _causal_panel_df
    try:
        log.info("Training Genuine Causal S-Learner (CATE Meta-Estimator)...")

        # Prepare temporal panel data for Causal inference
        df_sorted = df.sort_values(['pdo_well_id', 'Week_Number']).copy()
        # Calculate target (Y): Momentum (Progress next week - Progress this week)
        df_sorted['next_progress'] = df_sorted.groupby('pdo_well_id')['over_all_progress_percentages'].shift(-1)
        df_sorted['causal_momentum'] = df_sorted['next_progress'] - df_sorted['over_all_progress_percentages']

        # Drop rows without a valid next week to predict
        causal_panel = df_sorted.dropna(subset=['causal_momentum']).copy()
        # Filter extreme anomalies
        causal_panel = causal_panel[(causal_panel['causal_momentum'] >= 0) & (causal_panel['causal_momentum'] < 0.6)]

        if len(causal_panel) >= 50:
            # Map confounders
            causal_panel['cluster_density'] = causal_panel['well_location'].map(cluster_dens).fillna(0)
            causal_panel['material_lead_days'] = causal_panel.get('material_lead_days', pd.Series(0, index=causal_panel.index)).fillna(0)

            from sklearn.preprocessing import LabelEncoder
            rig_encoder = LabelEncoder()
            causal_panel['rig_no'] = causal_panel['rig_no'].fillna("UNKNOWN_RIG")
            causal_panel['well_location'] = causal_panel['well_location'].fillna("UNKNOWN_LOC")

            causal_panel['rig_encoded'] = rig_encoder.fit_transform(causal_panel['rig_no'].astype(str))

            loc_encoder = LabelEncoder()
            causal_panel['loc_encoded'] = loc_encoder.fit_transform(causal_panel['well_location'].astype(str))

            # S-Learner Features: Confounders (X) + Treatment (T) in single model
            causal_features = ['over_all_progress_percentages', 'cluster_density', 'material_lead_days', 'rig_encoded', 'loc_encoded']
            X_causal = causal_panel[causal_features].copy()
            y_causal = causal_panel['causal_momentum']

            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                s_learner = lgb.LGBMRegressor(
                    n_estimators=150,
                    learning_rate=0.03,
                    max_depth=6,
                    min_child_samples=15,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    random_state=42,
                    n_jobs=-1,
                    verbose=-1,
                )
                s_learner.fit(X_causal, y_causal)

            _causal_s_learner = s_learner
            _rig_encoder = rig_encoder
            _loc_encoder = loc_encoder
            _causal_panel_df = causal_panel
            log.info(f"âœ“ S-Learner CATE trained: {len(causal_panel)} obs, {len(causal_features)} features")
        else:
            log.warning(f"S-Learner skipped: insufficient causal panel rows ({len(causal_panel)} < 50)")
    except Exception as e:
        log.error(f"S-Learner training failed (non-fatal): {e}")

log.info("âœ“ CPU ML Engine Pretrained & Ready.")


def _engineered_feature_component_map(feature_source: Dict[str, Any]) -> Dict[str, float]:
    progress = float(np.clip(float(feature_source.get('progress', 0.0) or 0.0), 0.0, 1.0))
    momentum = float(np.clip(float(feature_source.get('recent_momentum_3w', 0.0) or 0.0), -0.25, 0.35))
    schedule_pressure = float(np.clip(float(feature_source.get('schedule_pressure', 0.0) or 0.0), 0.0, 1.0))
    days_to_expected = float(feature_source.get('days_to_expected_rig_off', 90.0) or 90.0)
    material_lead_days = float(feature_source.get('material_lead_days', 30.0) or 30.0)
    rig_efficiency = float(feature_source.get('rig_efficiency_weekly', 0.02) or 0.02)

    rig_efficiency_baseline = 0.02
    if _latest_features_df is not None and not _latest_features_df.empty and 'rig_efficiency_weekly' in _latest_features_df.columns:
        baseline_series = pd.to_numeric(_latest_features_df['rig_efficiency_weekly'], errors='coerce')
        baseline_median = baseline_series.median()
        if pd.notna(baseline_median):
            rig_efficiency_baseline = float(baseline_median)

    overdue_pressure = float(np.clip(-days_to_expected, 0.0, 28.0) / 28.0)
    material_pressure = float(np.clip(material_lead_days, 0.0, 90.0) / 90.0)
    rig_penalty = float(max(0.0, rig_efficiency_baseline - rig_efficiency))

    return {
        'progress': round((1.0 - progress) * 42.0, 3),
        'recent_momentum_3w': round(np.clip(0.04 - momentum, 0.0, None) * 260.0, 3),
        'rig_efficiency_weekly': round(rig_penalty * 180.0, 3),
        'schedule_pressure': round(schedule_pressure * 22.0, 3),
        'days_to_expected_rig_off': round(overdue_pressure * 18.0, 3),
        'material_lead_days': round(material_pressure * 6.0, 3),
    }


def _engineered_feature_probability_pct(feature_source: Dict[str, Any]) -> float:
    components = _engineered_feature_component_map(feature_source)
    return float(np.clip(sum(components.values()), 6.0, 99.0))


def _latest_prediction_row(well_id: str) -> Optional[Dict[str, Any]]:
    latest = _build_latest_prediction_frame()
    if latest.empty:
        return None

    match = latest[latest['pdo_well_id'].astype(str).str.strip() == str(well_id).strip()]
    if match.empty:
        return None

    row = match.iloc[0].to_dict()
    row['risk_probability_pct'] = float(row.get('risk_probability_pct') or 0.0)
    row['risk_engine'] = str(
        row.get('risk_engine')
        or ("calibrated_lightgbm_delay_risk_v1" if _lgb_model is not None else "engineered_feature_heuristic_fallback")
    )
    return row


def _fallback_risk_narrative(context: Dict[str, Any], feature_source: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    source = feature_source or context
    components = _engineered_feature_component_map(source)
    total_score = max(_engineered_feature_probability_pct(source), 1.0)
    direction_map = {
        'progress': 'below',
        'recent_momentum_3w': 'below',
        'rig_efficiency_weekly': 'below',
        'schedule_pressure': 'above',
        'days_to_expected_rig_off': 'above',
        'material_lead_days': 'above',
    }

    hidden_insights: List[Dict[str, Any]] = []
    risk_drivers: List[Dict[str, Any]] = []
    ranked = sorted(components.items(), key=lambda item: item[1], reverse=True)
    for feature, impact in ranked:
        if impact < 4.0:
            continue
        direction = direction_map.get(feature, 'above')
        label = _risk_feature_label(feature)
        description = _risk_feature_description(feature, direction, context)
        contribution_pct = round((float(impact) / total_score) * min(total_score, 99.0), 1)
        hidden_insights.append(
            {
                "factor": label,
                "description": description,
                "direction": "negative",
            }
        )
        risk_drivers.append(
            {
                "feature": feature,
                "label": label,
                "direction": "negative",
                "contribution_pct": contribution_pct,
                "description": description,
            }
        )
        if len(hidden_insights) >= 3:
            break

    return hidden_insights, risk_drivers


def _build_latest_prediction_frame() -> pd.DataFrame:
    if _latest_features_df is None:
        return pd.DataFrame()

    latest = _latest_features_df.copy()
    if latest.empty:
        return latest

    if _lgb_model is not None:
        X = latest[_feature_cols].copy()
        latest['risk_probability_pct'] = _lgb_model.predict_proba(X)[:, 1] * 100
        latest['risk_engine'] = "calibrated_lightgbm_delay_risk_v1"
    else:
        latest['risk_probability_pct'] = latest.apply(
            lambda row: _engineered_feature_probability_pct(row.to_dict()),
            axis=1,
        )
        latest['risk_engine'] = "engineered_feature_heuristic_fallback"

    latest['stall_probability_pct'] = latest['risk_probability_pct']
    return latest


def _well_category_lookup() -> dict:
    if _job_progress_df is None or _job_progress_df.empty:
        return {}

    jp = _job_progress_df.copy()
    jp['Well ID'] = jp['Well ID'].astype(str).str.strip()
    jp['Category'] = jp['Category'].astype(str).str.strip()
    jp = jp[(jp['Well ID'] != '') & (jp['Category'] != '')]
    return (
        jp.groupby('Well ID')['Category']
        .agg(lambda s: s.dropna().iloc[0] if len(s.dropna()) else None)
        .dropna()
        .to_dict()
    )


def _clip_weekly_momentum(value: float, floor: float = 0.003, ceiling: float = 0.25) -> float:
    return float(np.clip(value, floor, ceiling))


def _completion_days(progress: float, weekly_momentum: float) -> int:
    remaining_progress = max(0.0, 1.0 - float(progress))
    return int(np.ceil((remaining_progress / _clip_weekly_momentum(weekly_momentum)) * 7))


def _stage_from_flags(progress: float, has_engineering_started: bool, has_location_started: bool, is_rig_on: bool) -> str:
    if is_rig_on:
        return "drilling"
    if has_location_started and progress >= 0.55:
        return "construction"
    if has_engineering_started and progress >= 0.15:
        return "engineering"
    if has_location_started or progress > 0:
        return "readiness"
    return "prestart"


def _anchor_date_str(anchor_date: pd.Timestamp, days_forward: int) -> str:
    return (anchor_date + pd.Timedelta(days=int(days_forward))).strftime("%Y-%m-%d")


def _risk_tier_from_probability(probability_pct: float) -> str:
    if probability_pct >= 75:
        return "CRITICAL"
    if probability_pct >= 55:
        return "HIGH_RISK"
    if probability_pct >= 30:
        return "WATCH"
    return "HEALTHY"


def _risk_feature_label(feature: str) -> str:
    labels = {
        "progress": "Current completion level",
        "recent_momentum_3w": "Recent weekly momentum",
        "rig_efficiency_weekly": "Rig execution pace",
        "cluster_density": "Parallel workfront congestion",
        "material_lead_days": "Material lead time",
        "has_engineering_started": "Engineering readiness",
        "has_location_started": "Location readiness",
        "is_rig_on": "Rig-on execution state",
        "days_to_expected_rig_off": "Time to expected rig-off",
        "schedule_pressure": "Gap to expected schedule curve",
    }
    return labels.get(feature, feature.replace("_", " ").title())


def _risk_feature_description(feature: str, direction: str, context: Dict[str, Any]) -> str:
    progress_pct = round(float(context.get("progress", 0.0)) * 100, 1)
    schedule_pressure_pct = round(float(context.get("schedule_pressure", 0.0)) * 100, 1)
    days_to_target = int(round(float(context.get("days_to_expected_rig_off", 0.0))))
    if feature == "progress":
        return f"Current live completion is {progress_pct}%."
    if feature == "recent_momentum_3w":
        return f"Recent three-snapshot execution pace is {direction} the model baseline."
    if feature == "rig_efficiency_weekly":
        return f"Observed rig pace on {context.get('rig_no', 'the assigned rig')} is {direction} the comparable set."
    if feature == "cluster_density":
        return f"Parallel workfront density is {direction} the comparable operating range."
    if feature == "material_lead_days":
        return "Material readiness timing is contributing to delivery risk."
    if feature == "schedule_pressure":
        return f"Live execution is {schedule_pressure_pct} points behind the expected schedule curve."
    if feature == "days_to_expected_rig_off":
        return f"The well is {abs(days_to_target)} days {'past' if days_to_target < 0 else 'from'} expected rig-off."
    if feature == "is_rig_on":
        return "Current rig-on state is materially associated with delay outcomes in comparable history."
    if feature == "has_location_started":
        return "Location start state is affecting risk relative to comparable wells."
    if feature == "has_engineering_started":
        return "Engineering start state is affecting risk relative to comparable wells."
    return f"{_risk_feature_label(feature)} is {direction} the model baseline."


def _get_well_context(well_id: str) -> Optional[Dict[str, Any]]:
    if _hist_df is None or _hist_df.empty:
        return None

    well_data = _hist_df[_hist_df['pdo_well_id'].astype(str).str.strip() == str(well_id).strip()].copy()
    if well_data.empty:
        return None

    well_data = well_data.sort_values('Week_Number')
    latest = well_data.iloc[-1]
    progress = float(pd.to_numeric(latest.get('over_all_progress_percentages'), errors='coerce') or 0.0)
    history_delta = well_data['over_all_progress_percentages'].diff().dropna().clip(lower=0)
    recent_momentum = float(history_delta.tail(3).mean()) if not history_delta.empty else 0.0

    cluster_key = str(latest.get('cluster_key') or latest.get('Cluster') or latest.get('well_location') or "Unknown").strip() or "Unknown"
    rig_no = str(latest.get('rig_no') or "UNKNOWN_RIG").strip() or "UNKNOWN_RIG"
    snapshot_date = pd.to_datetime(latest.get('Week_Number'), errors='coerce')
    expected_rig_off = pd.to_datetime(latest.get('exp.rig_off_location_sap_data'), errors='coerce')
    actual_start = pd.to_datetime(latest.get('actual_start_date'), errors='coerce')
    actual_rig_on = pd.to_datetime(latest.get('actual_rig_on_date'), errors='coerce')
    actual_rig_off = pd.to_datetime(latest.get('actual_rig_off_date'), errors='coerce')

    days_to_expected_rig_off = 90.0
    schedule_pressure = 0.0
    if pd.notna(expected_rig_off):
        days_to_expected_rig_off = float(np.clip((expected_rig_off - snapshot_date).days if pd.notna(snapshot_date) else (expected_rig_off - pd.Timestamp.now()).days, -90, 180))
        if pd.notna(actual_start) and pd.notna(snapshot_date) and expected_rig_off > actual_start:
            elapsed_days = max(0, int((snapshot_date - actual_start).days))
            total_days = max(1, int((expected_rig_off - actual_start).days))
            expected_curve = min(1.0, elapsed_days / total_days)
            schedule_pressure = float(max(0.0, expected_curve - progress))

    has_engineering_started = pd.notna(pd.to_datetime(latest.get('engineering_actual_start_date'), errors='coerce'))
    has_location_started = pd.notna(actual_start)
    is_rig_on = bool(pd.notna(actual_rig_on) and (pd.isna(actual_rig_off) or str(latest.get('buffer_status') or '').upper() == 'ROL'))

    stage = _stage_from_flags(progress, has_engineering_started, has_location_started, is_rig_on)
    cluster_density = float(_cluster_density_map.get(cluster_key, 0.0))
    rig_efficiency_weekly = float(_rig_weekly_momentum_map.get(rig_no, recent_momentum if recent_momentum > 0 else 0.02))
    material_lead_days = float(pd.to_numeric(latest.get('material_lead_days'), errors='coerce') or 30.0)

    return {
        "well_id": str(well_id).strip(),
        "well_name": str(latest.get('well_name_after_spud') or well_id),
        "snapshot_date": snapshot_date if pd.notna(snapshot_date) else pd.Timestamp.now().normalize(),
        "progress": progress,
        "recent_momentum_3w": recent_momentum,
        "rig_no": rig_no,
        "cluster_key": cluster_key,
        "cluster_density": cluster_density,
        "rig_efficiency_weekly": rig_efficiency_weekly,
        "material_lead_days": material_lead_days,
        "has_engineering_started": int(has_engineering_started),
        "has_location_started": int(has_location_started),
        "is_rig_on": int(is_rig_on),
        "days_to_expected_rig_off": days_to_expected_rig_off,
        "schedule_pressure": schedule_pressure,
        "stage": stage,
    }


def _get_comparable_rows(context: Dict[str, Any]) -> Tuple[pd.DataFrame, str]:
    if _scenario_panel_df is None or _scenario_panel_df.empty:
        return pd.DataFrame(), "portfolio"

    panel = _scenario_panel_df.copy()
    progress = float(context['progress'])
    stage = str(context['stage'])
    cluster_key = str(context['cluster_key'])

    base_mask = (
        (panel['stage'] == stage) &
        (np.abs(panel['progress'] - progress) <= 0.15)
    )
    same_cluster = panel[base_mask & (panel['cluster_key'] == cluster_key)]
    if len(same_cluster) >= 20:
        return same_cluster, f"{cluster_key} {stage}"

    stage_peers = panel[base_mask]
    if len(stage_peers) >= 30:
        return stage_peers, f"portfolio {stage}"

    fallback = panel[np.abs(panel['progress'] - progress) <= 0.2]
    return fallback, "portfolio broad"


def _empirical_profile(rows: pd.DataFrame) -> Dict[str, float]:
    if rows is None or rows.empty:
        return {"support_cases": 0, "p10": 0.0, "p50": 0.0, "p90": 0.0}

    momentum = rows['weekly_momentum'].dropna().clip(lower=0, upper=0.35)
    if momentum.empty:
        return {"support_cases": 0, "p10": 0.0, "p50": 0.0, "p90": 0.0}

    return {
        "support_cases": int(len(momentum)),
        "p10": float(momentum.quantile(0.10)),
        "p50": float(momentum.median()),
        "p90": float(momentum.quantile(0.90)),
    }


def _build_feature_frame(context: Dict[str, Any], overrides: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    row = {key: context.get(key, 0.0) for key in _scenario_feature_cols}
    if overrides:
        row.update(overrides)
    return pd.DataFrame([row], columns=_scenario_feature_cols)


def _predict_profile(context: Dict[str, Any], overrides: Optional[Dict[str, float]] = None, empirical_rows: Optional[pd.DataFrame] = None) -> Dict[str, float]:
    empirical = _empirical_profile(empirical_rows if empirical_rows is not None else pd.DataFrame())
    recent_anchor = float(overrides.get('recent_momentum_3w', context['recent_momentum_3w']) if overrides else context['recent_momentum_3w'])

    if _scenario_models:
        feature_row = _build_feature_frame(context, overrides)
        model_p50 = float(_scenario_models['base'].predict(feature_row)[0])
        model_p10 = float(_scenario_models['q10'].predict(feature_row)[0])
        model_p90 = float(_scenario_models['q90'].predict(feature_row)[0])
    else:
        model_p50 = empirical['p50'] or recent_anchor or 0.02
        model_p10 = empirical['p10'] or max(model_p50 * 0.7, 0.003)
        model_p90 = empirical['p90'] or min(model_p50 * 1.3, 0.25)

    if empirical['support_cases'] >= 12:
        p50 = (0.7 * model_p50) + (0.3 * empirical['p50'])
        p10 = (0.7 * model_p10) + (0.3 * empirical['p10'])
        p90 = (0.7 * model_p90) + (0.3 * empirical['p90'])
    else:
        p50, p10, p90 = model_p50, model_p10, model_p90

    if recent_anchor > 0:
        p50 = (0.75 * p50) + (0.25 * recent_anchor)

    p50 = _clip_weekly_momentum(p50)
    p10 = _clip_weekly_momentum(min(p10, p50))
    p90 = _clip_weekly_momentum(max(p90, p50))
    return {
        "support_cases": empirical['support_cases'],
        "p10": round(p10, 4),
        "p50": round(p50, 4),
        "p90": round(p90, 4),
    }


def _material_rows(rows: pd.DataFrame, target_lead: float) -> pd.DataFrame:
    if rows is None or rows.empty:
        return pd.DataFrame()
    return rows[rows['material_lead_days'].fillna(30) <= target_lead + 3]


def _cluster_rows(rows: pd.DataFrame, target_density: float) -> pd.DataFrame:
    if rows is None or rows.empty:
        return pd.DataFrame()
    return rows[rows['cluster_density'].fillna(0) <= target_density]


def _rig_rows(rows: pd.DataFrame, rig_no: str) -> pd.DataFrame:
    if rows is None or rows.empty:
        return pd.DataFrame()
    return rows[rows['rig_no'].astype(str) == str(rig_no)]


def _baseline_and_actions(context: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    comparable_rows, scope = _get_comparable_rows(context)
    baseline_profile = _predict_profile(context, empirical_rows=comparable_rows)
    baseline_days = _completion_days(context['progress'], baseline_profile['p50'])
    baseline = {
        "weekly_momentum_pct": round(baseline_profile['p50'] * 100, 2),
        "expected_completion_date": _anchor_date_str(context['snapshot_date'], baseline_days),
        "support_cases": int(baseline_profile['support_cases']),
        "benchmark_scope": scope,
        "days_to_complete": baseline_days,
        "low_case_completion_date": _anchor_date_str(context['snapshot_date'], _completion_days(context['progress'], baseline_profile['p10'])),
        "high_case_completion_date": _anchor_date_str(context['snapshot_date'], _completion_days(context['progress'], baseline_profile['p90'])),
    }

    actions: List[Dict[str, Any]] = [
        {
            "id": "peer_recovery",
            "label": "Recover to Peer Execution Pace",
            "description": "Lift weekly execution pace to the peer benchmark for wells at the same stage and progress band.",
            "parameter_label": "Recovery Level",
            "default_value": "median",
            "options": [
                {"value": "median", "label": "Peer Median"},
                {"value": "top_quartile", "label": "Peer Top Quartile"},
            ],
        }
    ]

    rig_candidates = (
        comparable_rows.groupby('rig_no')['weekly_momentum']
        .agg(['median', 'count'])
        .reset_index()
        .rename(columns={"median": "median_momentum", "count": "support_cases"})
        if comparable_rows is not None and not comparable_rows.empty
        else pd.DataFrame(columns=['rig_no', 'median_momentum', 'support_cases'])
    )
    current_rig_eff = float(context['rig_efficiency_weekly'])
    rig_candidates = rig_candidates[
        (rig_candidates['support_cases'] >= 8)
        & (rig_candidates['median_momentum'] > current_rig_eff + 0.003)
        & (rig_candidates['rig_no'].astype(str) != str(context['rig_no']))
    ].sort_values('median_momentum', ascending=False)
    if not rig_candidates.empty:
        actions.append({
            "id": "rig_reassignment",
            "label": "Reassign Higher-Efficiency Rig",
            "description": "Test the effect of moving the well onto a stronger historical execution rig for this stage.",
            "parameter_label": "Target Rig",
            "default_value": str(rig_candidates.iloc[0]['rig_no']),
            "options": [
                {
                    "value": str(row['rig_no']),
                    "label": f"{row['rig_no']} ({round(float(row['median_momentum']) * 100, 1)} pts/wk)",
                    "support_cases": int(row['support_cases']),
                }
                for _, row in rig_candidates.head(5).iterrows()
            ],
        })

    if context['material_lead_days'] > 0:
        reductions = [7, 14, 21]
        valid_reductions = [r for r in reductions if context['material_lead_days'] >= r]
        if valid_reductions:
            actions.append({
                "id": "material_expedite",
                "label": "Expedite Material Readiness",
                "description": "Reduce material lead time and estimate the resulting recovery in execution pace.",
                "parameter_label": "Lead Time Reduction",
                "default_value": str(valid_reductions[0]),
                "options": [{"value": str(r), "label": f"{r} day reduction"} for r in valid_reductions],
            })

    if comparable_rows is not None and not comparable_rows.empty and comparable_rows['cluster_density'].nunique() > 1:
        actions.append({
            "id": "decongest_workfront",
            "label": "Decongest Parallel Workfronts",
            "description": "Reduce local workfront congestion to peer-normal or top-quartile operating density.",
            "parameter_label": "Decongestion Level",
            "default_value": "moderate",
            "options": [
                {"value": "moderate", "label": "Peer Median Density"},
                {"value": "aggressive", "label": "Peer Top Quartile Density"},
            ],
        })

    return baseline, actions


def _simulate_action(context: Dict[str, Any], action_id: str, action_value: str) -> Dict[str, Any]:
    baseline, actions = _baseline_and_actions(context)
    action = next((item for item in actions if item['id'] == action_id), None)
    if action is None:
        raise HTTPException(status_code=400, detail="Unsupported scenario action")

    resolved_value = str(action_value or "").strip()
    if not resolved_value:
        resolved_value = str(
            action.get('default_value')
            or (action.get('options') or [{}])[0].get('value')
            or ""
        ).strip()
    if not resolved_value:
        raise HTTPException(status_code=400, detail="Scenario action is missing a valid option value")

    comparable_rows, scope = _get_comparable_rows(context)
    overrides: Dict[str, float] = {}
    empirical_rows = comparable_rows
    assumption = ""

    if action_id == "peer_recovery":
        target_quantile = 0.75 if resolved_value == "top_quartile" else 0.50
        peer_target = float(comparable_rows['weekly_momentum'].quantile(target_quantile)) if comparable_rows is not None and not comparable_rows.empty else context['recent_momentum_3w']
        overrides['recent_momentum_3w'] = max(context['recent_momentum_3w'], peer_target)
        empirical_rows = comparable_rows[comparable_rows['weekly_momentum'] >= peer_target * 0.95] if comparable_rows is not None and not comparable_rows.empty else pd.DataFrame()
        assumption = "Assumes execution blockers are removed and the well performs at the selected peer pace."
    elif action_id == "rig_reassignment":
        rig_choice = resolved_value
        candidate_rows = _rig_rows(comparable_rows, rig_choice)
        if candidate_rows.empty:
            raise HTTPException(status_code=400, detail="Selected rig has insufficient comparable history")
        candidate_eff = float(candidate_rows['weekly_momentum'].median())
        overrides['rig_efficiency_weekly'] = candidate_eff
        empirical_rows = candidate_rows
        assumption = f"Assumes the well can be executed under rig {rig_choice} with comparable historical performance."
    elif action_id == "material_expedite":
        reduction = max(0, int(float(resolved_value)))
        target_lead = max(0.0, float(context['material_lead_days']) - reduction)
        overrides['material_lead_days'] = target_lead
        empirical_rows = _material_rows(comparable_rows, target_lead)
        assumption = f"Assumes material lead time is reduced by {reduction} days and downstream crews can absorb the earlier release."
    elif action_id == "decongest_workfront":
        if comparable_rows is None or comparable_rows.empty:
            raise HTTPException(status_code=400, detail="No comparable rows available for congestion scenario")
        target_density = float(comparable_rows['cluster_density'].quantile(0.25 if resolved_value == "aggressive" else 0.50))
        overrides['cluster_density'] = target_density
        empirical_rows = _cluster_rows(comparable_rows, target_density)
        assumption = "Assumes parallel workfront pressure can be reduced to the selected peer density."

    scenario_profile = _predict_profile(context, overrides=overrides, empirical_rows=empirical_rows)
    baseline_days = int(baseline['days_to_complete'])
    scenario_days = _completion_days(context['progress'], scenario_profile['p50'])
    low_case_days_saved = max(0, baseline_days - _completion_days(context['progress'], scenario_profile['p10']))
    high_case_days_saved = max(0, baseline_days - _completion_days(context['progress'], scenario_profile['p90']))
    days_saved = max(0, baseline_days - scenario_days)

    return {
        "well_id": context['well_id'],
        "action_id": action_id,
        "action_label": action['label'],
        "action_value": resolved_value,
        "benchmark_scope": scope,
        "support_cases": int(scenario_profile['support_cases']),
        "assumption_note": assumption,
        "factual_completion_date": baseline['expected_completion_date'],
        "counterfactual_completion_date": _anchor_date_str(context['snapshot_date'], scenario_days),
        "effect_days": int(days_saved),
        "low_case_days_saved": int(low_case_days_saved),
        "high_case_days_saved": int(high_case_days_saved),
        "baseline_weekly_momentum_pct": round(baseline['weekly_momentum_pct'], 2),
        "scenario_weekly_momentum_pct": round(scenario_profile['p50'] * 100, 2),
        "confidence_band": {
            "conservative_days_saved": int(low_case_days_saved),
            "expected_days_saved": int(days_saved),
            "upside_days_saved": int(high_case_days_saved),
        },
    }


def _build_root_cause_vector(context: Dict[str, Any]) -> Dict[str, Any]:
    baseline, actions = _baseline_and_actions(context)
    root_causes: List[Dict[str, Any]] = []

    if context['schedule_pressure'] > 0.08:
        schedule_delay = max(2, int(round(context['schedule_pressure'] * max(14, baseline['days_to_complete'] * 0.35))))
        root_causes.append({
            "factor": "Execution is behind the planned curve",
            "description": f"Live SSMS schedule pressure is {round(context['schedule_pressure'] * 100, 1)} points against the expected curve.",
            "delay_days": schedule_delay,
            "type": "schedule",
            "support_cases": baseline['support_cases'],
        })

    default_values = {
        "peer_recovery": "top_quartile",
        "decongest_workfront": "moderate",
        "material_expedite": "14",
    }
    for action in actions:
        default_value = action.get('default_value') or default_values.get(action['id']) or (action.get('options') or [{}])[0].get('value')
        if default_value is None:
            continue
        try:
            scenario = _simulate_action(context, action['id'], str(default_value))
        except HTTPException:
            continue
        if scenario['effect_days'] < 2:
            continue

        factor = action['label']
        description = action['description']
        if action['id'] == "peer_recovery":
            factor = "Execution pace is below peer benchmark"
            description = f"Recovering to the selected peer pace would save about {scenario['effect_days']} days."
        elif action['id'] == "rig_reassignment":
            factor = "Rig efficiency gap"
            description = f"A stronger comparable rig could recover about {scenario['effect_days']} days."
        elif action['id'] == "material_expedite":
            factor = "Material readiness lag"
            description = f"Cutting lead time would recover about {scenario['effect_days']} days."
        elif action['id'] == "decongest_workfront":
            factor = "Parallel workfront congestion"
            description = f"Reducing congestion to peer density would recover about {scenario['effect_days']} days."

        root_causes.append({
            "factor": factor,
            "description": description,
            "delay_days": int(scenario['effect_days']),
            "type": action['id'],
            "support_cases": int(scenario['support_cases']),
        })

    root_causes.sort(key=lambda item: item['delay_days'], reverse=True)
    return {
        "methodology": "governed_scenario_engine_v1",
        "baseline": baseline,
        "root_causes": root_causes[:4],
        "interventions_available": {
            "actions": actions,
        },
    }


@app.on_event("startup")
def startup_event():
    build_models()


def _compute_cate(well_id: str) -> Dict[str, Any]:
    """
    Compute Conditional Average Treatment Effect for a well using S-Learner.
    CATE = E[Y|X, T=t'] - E[Y|X, T=t] where T is the treatment (rig assignment).
    """
    if _causal_s_learner is None or _rig_encoder is None or _loc_encoder is None:
        return {"error": "S-Learner not trained", "well_id": well_id}

    context = _get_well_context(well_id)
    if context is None:
        return {"error": "Well not found", "well_id": well_id}

    # Build factual feature vector
    progress = context.get('progress', 0)
    cluster_density = context.get('cluster_density', 0)
    material_lead = context.get('material_lead_days', 0)
    current_rig = str(context.get('rig_no', 'UNKNOWN_RIG'))
    current_loc = str(context.get('well_location', 'UNKNOWN_LOC'))

    # Encode current rig and location
    try:
        rig_enc = _rig_encoder.transform([current_rig])[0]
    except ValueError:
        rig_enc = 0
    try:
        loc_enc = _loc_encoder.transform([current_loc])[0]
    except ValueError:
        loc_enc = 0

    # Factual prediction (what S-Learner predicts with current rig)
    X_factual = pd.DataFrame([{
        'over_all_progress_percentages': progress,
        'cluster_density': cluster_density,
        'material_lead_days': material_lead,
        'rig_encoded': rig_enc,
        'loc_encoded': loc_enc,
    }])
    factual_momentum = float(_causal_s_learner.predict(X_factual)[0])

    # Counterfactual predictions (what if we assigned each rig?)
    rig_effects = []
    all_rigs = _rig_encoder.classes_
    for alt_rig in all_rigs:
        alt_rig_enc = _rig_encoder.transform([alt_rig])[0]
        X_cf = X_factual.copy()
        X_cf['rig_encoded'] = alt_rig_enc
        cf_momentum = float(_causal_s_learner.predict(X_cf)[0])
        cate = cf_momentum - factual_momentum
        rig_effects.append({
            "rig": str(alt_rig),
            "counterfactual_momentum_pct": round(cf_momentum * 100, 3),
            "cate_pct": round(cate * 100, 3),
            "is_current": str(alt_rig) == current_rig,
        })

    # Sort by CATE (best improvement first)
    rig_effects.sort(key=lambda x: x['cate_pct'], reverse=True)

    # Best alternative rig
    best_alt = [r for r in rig_effects if not r['is_current']]
    best_rig = best_alt[0] if best_alt else None

    return {
        "well_id": well_id,
        "well_name": context.get('well_name', ''),
        "current_rig": current_rig,
        "current_progress_pct": round(progress * 100, 1),
        "factual_momentum_pct": round(factual_momentum * 100, 3),
        "best_alternative_rig": best_rig,
        "rig_treatment_effects": rig_effects[:10],  # Top 10 alternatives
        "s_learner_status": "active",
        "methodology": "s_learner_cate_counterfactual_substitution",
        "causal_panel_size": len(_causal_panel_df) if _causal_panel_df is not None else 0,
    }


@app.get("/ml/causal/cate/{well_id}")
def get_cate(well_id: str):
    """
    Compute Conditional Average Treatment Effect (CATE) via S-Learner.
    Returns per-rig counterfactual momentum estimates using causal inference.
    """
    return _compute_cate(well_id)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "models_loaded": _lgb_model is not None,
        "prediction_frame_ready": _latest_features_df is not None,
    }

class SimulateRequest(BaseModel):
    well_id: str
    intervention_type: str
    intervention_value: str

@app.post("/ml/simulate")
def simulate_intervention(req: SimulateRequest):
    """Run a governed scenario on explicit business levers using live SSMS history."""
    context = _get_well_context(req.well_id)
    if context is None:
        return {"error": "Well not found"}

    action_map = {
        "rig": "rig_reassignment",
        "material": "material_expedite",
        "cluster_priority": "decongest_workfront",
        "peer_recovery": "peer_recovery",
        "rig_reassignment": "rig_reassignment",
        "material_expedite": "material_expedite",
        "decongest_workfront": "decongest_workfront",
    }
    action_id = action_map.get(req.intervention_type, req.intervention_type)
    scenario = _simulate_action(context, action_id, str(req.intervention_value or ""))
    scenario["methodology"] = "governed_scenario_engine_v1"
    return scenario

@app.get("/ml/forecast/{well_id}")
def generate_advanced_forecast(well_id: str):
    """
    1. Runs pure AutoARIMA time-series on the well's history to get predictive S-curve mapping.
    2. Runs LightGBM + SHAP to generate localized human-readable 'Hidden Insights'.
    """
    if _hist_df is None:
        return {
            "well_id": well_id,
            "risk_probability_pct": 0.0,
            "stall_probability_pct": 0.0,
            "stats_forecast": [],
            "hidden_insights": [],
            "risk_drivers": [],
            "risk_model": {
                "engine": "history_unavailable",
                "target": "probability_of_missing_expected_rig_off",
                "rows": 0,
                "positive_rate": 0.0,
                "auc": 0.0,
                "brier": 0.0,
            },
            "causal_intelligence": {
                "methodology": "governed_scenario_engine_v1",
                "baseline": {},
                "root_causes": [],
                "interventions_available": {"actions": []},
                "error": "Historical panel unavailable",
            },
        }

    # 1. Fetch Well History
    well_data = _hist_df[_hist_df['pdo_well_id'].astype(str).str.strip() == str(well_id).strip()]
    target_df = pd.DataFrame()
    if len(well_data) >= 2:
        target_df = well_data.dropna(subset=['Week_Number', 'over_all_progress_percentages']).copy()
        target_df = target_df.sort_values('Week_Number')

    # Prep for Nixtla StatsForecast (requires columns: unique_id, ds, y)
    prep_df = pd.DataFrame()
    if not target_df.empty:
        prep_df = pd.DataFrame({
            'unique_id': [str(well_id)] * len(target_df),
            'ds': target_df['Week_Number'],
            'y': target_df['over_all_progress_percentages'] * 100
        })

    # -------------------------------------------------------------------------
    # PART A: AUTO-ARIMA TRAJECTORY FORECASTING via StatsForecast
    # -------------------------------------------------------------------------
    sf_predictions = []
    if not prep_df.empty:
        try:
            sf = StatsForecast(
                models=[AutoARIMA(season_length=4)],
                freq='W' # Weekly frequency
            )
            # Suppress warnings
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                # Predict next 4 weeks with 95% confidence intervals
                forecast = sf.forecast(df=prep_df, h=4, level=[95])

            # Parse Forecast output
            for _, row in forecast.iterrows():
                sf_predictions.append({
                    "week": row.name.strftime('%Y-%m-%d') if hasattr(row.name, 'strftime') else str(row.name),
                    "predicted": round(float(row['AutoARIMA']), 1),
                    "lower": round(max(0, float(row['AutoARIMA-lo-95'])), 1),
                    "upper": round(min(100, float(row['AutoARIMA-hi-95'])), 1)
                })
        except Exception as e:
            log.error(f"StatsForecast failed for well {well_id}: {e}")

    # -------------------------------------------------------------------------
    # PART B: SHAP EXTRACTED HIDDEN INSIGHTS (LightGBM)
    # -------------------------------------------------------------------------
    hidden_insights = []
    risk_prob = 0.0
    risk_drivers = []
    context = _get_well_context(well_id)
    live_prediction = _latest_prediction_row(well_id)
    try:
        if context and _lgb_model is not None:
            X_live = _build_feature_frame(context)
            risk_prob = float(_lgb_model.predict_proba(X_live[_feature_cols])[0][1])
        elif context:
            X_live = pd.DataFrame()
            risk_prob = float(
                (live_prediction or {}).get('risk_probability_pct')
                or _engineered_feature_probability_pct(context)
            ) / 100.0
            hidden_insights, risk_drivers = _fallback_risk_narrative(context, live_prediction or context)
        else:
            X_live = pd.DataFrame()

        if context and _explainer is not None and not X_live.empty:
            shap_values = _explainer.shap_values(X_live[_feature_cols])
            sv = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]

            feature_importance = [(col, float(val)) for col, val in zip(_feature_cols, sv)]
            feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)
            ranked_features = [
                (col, impact) for col, impact in feature_importance[:5] if abs(impact) >= 0.01
            ]
            total_abs_impact = sum(abs(impact) for _, impact in ranked_features) or 1.0

            for col, impact in ranked_features[:3]:
                direction = "above" if impact > 0 else "below"
                color = "negative" if impact > 0 else "positive"
                contribution_pct = round((abs(impact) / total_abs_impact) * (risk_prob * 100), 1)
                label = _risk_feature_label(col)
                description = _risk_feature_description(col, direction, context)

                hidden_insights.append({
                    "factor": label,
                    "description": description,
                    "direction": color
                })
                risk_drivers.append({
                    "feature": col,
                    "label": label,
                    "direction": color,
                    "contribution_pct": contribution_pct,
                    "description": description,
                })
        elif context and not hidden_insights:
            hidden_insights, risk_drivers = _fallback_risk_narrative(context, live_prediction or context)
    except Exception as e:
        log.error(f"SHAP extraction failed for well {well_id}: {e}")
        if context and not hidden_insights:
            hidden_insights, risk_drivers = _fallback_risk_narrative(context, live_prediction or context)

    # -------------------------------------------------------------------------
    # PART C: GOVERNED ROOT-CAUSE VECTOR + SCENARIO CATALOG
    # -------------------------------------------------------------------------
    try:
        causal_intelligence = _build_root_cause_vector(context) if context else {
            "methodology": "governed_scenario_engine_v1",
            "baseline": {},
            "root_causes": [],
            "interventions_available": {"actions": []},
        }
    except Exception as e:
        log.error(f"Scenario engine failed for well {well_id}: {e}")
        causal_intelligence = {
            "methodology": "governed_scenario_engine_v1",
            "baseline": {},
            "root_causes": [],
            "interventions_available": {"actions": []},
            "error": str(e),
        }

    return {
        "well_id": well_id,
        "risk_probability_pct": round(float(risk_prob * 100), 1),
        "stall_probability_pct": round(float(risk_prob * 100), 1),
        "stats_forecast": sf_predictions,
        "hidden_insights": hidden_insights,
        "risk_drivers": risk_drivers,
        "risk_model": {
            "engine": str(
                (live_prediction or {}).get("risk_engine")
                or ("calibrated_lightgbm_delay_risk_v1" if _lgb_model is not None else "engineered_feature_heuristic_fallback")
            ),
            "target": "probability_of_missing_expected_rig_off",
            "rows": int(_risk_model_metrics.get("rows", 0)),
            "positive_rate": float(_risk_model_metrics.get("positive_rate", 0.0)),
            "auc": float(_risk_model_metrics.get("auc", 0.0)),
            "brier": float(_risk_model_metrics.get("brier", 0.0)),
        },
        "causal_intelligence": causal_intelligence
    }


@app.get("/ml/portfolio/live-risk")
def portfolio_live_risk():
    latest = _build_latest_prediction_frame()
    if latest.empty:
        return {
            "rows": [],
            "count": 0,
            "model": "calibrated_lightgbm_delay_risk_v1" if _lgb_model is not None else "engineered_feature_heuristic_fallback",
        }

    latest = latest.copy()
    latest['risk_tier'] = latest['risk_probability_pct'].apply(_risk_tier_from_probability)
    rows = [
        {
            "well_id": str(row['pdo_well_id']).strip(),
            "well_name": str(row.get('well_name_after_spud') or row['pdo_well_id']),
            "risk_probability_pct": round(float(row['risk_probability_pct']), 1),
            "risk_tier": row['risk_tier'],
            "risk_engine": str(row.get('risk_engine') or ("calibrated_lightgbm_delay_risk_v1" if _lgb_model is not None else "engineered_feature_heuristic_fallback")),
        }
        for _, row in latest.iterrows()
    ]
    return {
        "rows": rows,
        "count": len(rows),
        "model": "calibrated_lightgbm_delay_risk_v1" if _lgb_model is not None else "engineered_feature_heuristic_fallback",
        "metrics": _risk_model_metrics,
    }


@app.get("/ml/portfolio/project-delay-probability")
def project_delay_probability():
    """
    Aggregate CPU-ML stall probabilities to the management project/category grain.
    Business default: project = Category from job_progress_gb.csv when available.
    """
    if _lgb_model is None:
        pass # Will gracefully fall back to default EVT intrinsic tracking

    latest = _build_latest_prediction_frame()
    if latest.empty:
        return {"rows": [], "count": 0}

    latest = latest[latest['progress'].notna() & (latest['progress'] < 1.0)].copy()
    latest['pdo_well_id'] = latest['pdo_well_id'].astype(str).str.strip()

    category_lookup = _well_category_lookup()
    latest['project_category'] = latest['pdo_well_id'].map(category_lookup)
    latest['project_category'] = latest['project_category'].fillna(latest['well_location']).fillna("Unknown")

    grouped = (
        latest.groupby('project_category')
        .agg(
            open_wells=('pdo_well_id', 'count'),
            avg_progress_pct=('progress', lambda s: round(float(s.mean() * 100), 1)),
            avg_delay_probability_pct=('risk_probability_pct', lambda s: round(float(s.mean()), 1)),
            max_delay_probability_pct=('risk_probability_pct', lambda s: round(float(s.max()), 1)),
            critical_wells=('risk_probability_pct', lambda s: int((s >= 75).sum())),
        )
        .reset_index()
        .sort_values(['avg_delay_probability_pct', 'critical_wells'], ascending=[False, False])
    )

    rows = []
    np.random.seed(42)  # For reproducible quant pricing

    for _, row in grouped.iterrows():
        open_wells = int(row['open_wells'])
        base_delay_prob = float(row['avg_delay_probability_pct']) / 100.0
        
        # 1. Non-Homogeneous Poisson Process (NHPP) approximation for intensity curve
        # We assume delay intensity scales non-linearly with project density (open wells)
        intensity_lambda = base_delay_prob * np.log1p(open_wells) * 1.5
        
        # 2. Monte Carlo Execution Pricing (MCEP) - Extreme Value Theory (EVT) Upgrade
        # Simulate 10,000 parallel paths for the active well timeline
        M = 10000
        # Draw random delay events from Poisson
        simulated_events = np.random.poisson(intensity_lambda, size=(M, open_wells))
        
        # SOTA Upgrade: Draw severity (days delayed) from a Pareto distribution (Extreme Value Theory)
        # Industrial structural failures exhibit heavy tails (Black Swans) that LogNormal severely under-prices.
        # Pareto shape (a) = 2.5, scale = 3.0 gives standard 5-day delays but allows for catastrophic 40+ day tail risks.
        pareto_shape = 2.5
        pareto_scale = 3.0
        simulated_severity = (np.random.pareto(pareto_shape, size=(M, open_wells)) + 1) * pareto_scale
        
        # Calculate matrix of total delays across all 10,000 parallel universes
        path_delays = np.sum(simulated_events * simulated_severity, axis=1)
        
        # Quant-fund style P99 Extreme Value-at-Risk (EVT tail exposure)
        p95_delay_days = np.percentile(path_delays, 99)
        expected_delay_days = np.mean(path_delays)
        
        # Price the risk in arbitrary units (e.g., $50k per rig delay day)
        risk_price_metric = expected_delay_days * 50000
        
        # Adjust probabilities using the simulated density
        intrinsic_delay_prob = (np.sum(path_delays > 0) / M) * 100.0
        
        rows.append(
            {
                "project": row['project_category'],
                "open_wells": open_wells,
                "avg_progress_pct": float(row['avg_progress_pct']),
                "avg_delay_probability_pct": min(99.0, max(float(row['avg_delay_probability_pct']), intrinsic_delay_prob)),
                "max_delay_probability_pct": float(row['max_delay_probability_pct']),
                "critical_wells": int(row['critical_wells']),
                # Advanced Quant ML metrics:
                "p95_delay_exposure_days": int(p95_delay_days),
                "expected_delay_days": int(expected_delay_days),
                "risk_price": float(risk_price_metric),
                "nhpp_intensity": round(float(intensity_lambda), 3),
            }
        )

    return {"rows": rows, "count": len(rows)}


@app.get("/ml/portfolio/feature-insights")
def portfolio_feature_insights():
    """
    Return portfolio-wide model feature signals using mean absolute SHAP
    across the latest well state, plus high-risk vs low-risk directionality.
    """
    if _lgb_model is None or _explainer is None:
        return {"insights": []}

    latest = _build_latest_prediction_frame()
    if latest.empty:
        return {"insights": []}

    X = latest[_feature_cols].copy()
    probabilities = latest['risk_probability_pct'].to_numpy()

    shap_values = _explainer.shap_values(X)
    if isinstance(shap_values, list):
        shap_matrix = np.array(shap_values[1])
    else:
        shap_matrix = np.array(shap_values)

    mean_abs = np.abs(shap_matrix).mean(axis=0)
    high_cut = np.percentile(probabilities, 75)
    low_cut = np.percentile(probabilities, 25)
    high_mask = probabilities >= high_cut
    low_mask = probabilities <= low_cut

    labels = {
        'progress': 'Current Overall Progress',
        'rig_efficiency': 'Historical Rig Efficiency',
        'cluster_density': 'Cluster Resource Density',
        'momentum': 'Execution Momentum',
    }

    insights = []
    for idx, feature in enumerate(_feature_cols):
        high_mean = float(X.loc[high_mask, feature].mean()) if high_mask.any() else float(X[feature].mean())
        low_mean = float(X.loc[low_mask, feature].mean()) if low_mask.any() else float(X[feature].mean())
        delta = high_mean - low_mean

        if feature == 'progress':
            direction = "lower values are associated with higher delay risk" if delta < 0 else "higher values are associated with higher delay risk"
        elif feature == 'momentum':
            direction = "weaker momentum is associated with higher delay risk" if delta < 0 else "stronger momentum is associated with higher delay risk"
        else:
            direction = "higher values are associated with higher delay risk" if delta > 0 else "lower values are associated with higher delay risk"

        insights.append({
            "feature": feature,
            "label": labels.get(feature, feature),
            "importance": round(float(mean_abs[idx]), 4),
            "direction": direction,
        })

    insights.sort(key=lambda x: x['importance'], reverse=True)
    return {"insights": insights[:4]}

if __name__ == "__main__":
    uvicorn.run("cpu_ml_orchestrator:app", host="127.0.0.1", port=8050, reload=True)

