from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, roc_auc_score


def ensure_catboost():
    try:
        from catboost import CatBoostClassifier, CatBoostRegressor, Pool  # type: ignore

        return CatBoostClassifier, CatBoostRegressor, Pool
    except Exception:
        import subprocess
        import sys

        subprocess.check_call([sys.executable, "-m", "pip", "install", "catboost"])
        from catboost import CatBoostClassifier, CatBoostRegressor, Pool  # type: ignore

        return CatBoostClassifier, CatBoostRegressor, Pool


def ensure_xgboost():
    try:
        from xgboost import XGBClassifier, XGBRegressor  # type: ignore

        return XGBClassifier, XGBRegressor
    except Exception:
        import subprocess
        import sys

        subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost"])
        from xgboost import XGBClassifier, XGBRegressor  # type: ignore

        return XGBClassifier, XGBRegressor


def ensure_matplotlib():
    try:
        import matplotlib
    except Exception:
        import subprocess
        import sys

        subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib"])
        import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def ensure_lifelines():
    try:
        from lifelines import CoxPHFitter, KaplanMeierFitter  # type: ignore
        from lifelines.utils import concordance_index  # type: ignore

        return CoxPHFitter, KaplanMeierFitter, concordance_index
    except Exception:
        import subprocess
        import sys

        subprocess.check_call([sys.executable, "-m", "pip", "install", "lifelines"])
        from lifelines import CoxPHFitter, KaplanMeierFitter  # type: ignore
        from lifelines.utils import concordance_index  # type: ignore

        return CoxPHFitter, KaplanMeierFitter, concordance_index


def normalize_column(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    seen: dict[str, int] = {}
    cleaned: list[str] = []
    for raw_col in out.columns:
        base = normalize_column(str(raw_col))
        seen[base] = seen.get(base, 0) + 1
        cleaned.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    out.columns = cleaned
    return out


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


def to_dt(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    if hasattr(parsed.dt, "tz_convert"):
        parsed = parsed.dt.tz_convert(None)
    return parsed


def clamp_progress(series: pd.Series) -> pd.Series:
    values = to_num(series)
    big_mask = values > 1
    values.loc[big_mask] = values.loc[big_mask] / 100.0
    return values.clip(0, 1)


def find_input_file(file_name: str, input_dir: Path | None) -> Path:
    candidates: list[Path] = []
    if input_dir:
        candidates.append(input_dir / file_name)
    candidates.append(Path.cwd() / file_name)

    kaggle_input = Path("/kaggle/input")
    if kaggle_input.exists():
        candidates.extend(kaggle_input.rglob(file_name))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not find required input file: {file_name}")


def first_not_blank(values: Iterable[object]) -> object | None:
    for value in values:
        if pd.notna(value) and str(value).strip() != "":
            return value
    return None


def first_matching_column(columns: Iterable[str], prefix: str) -> str | None:
    for column in columns:
        if column == prefix or column.startswith(f"{prefix}_"):
            return column
    return None


@dataclass
class EnsembleMember:
    name: str
    model: object
    backend: str
    weight: float
    category_maps: dict[str, dict[str, int]] | None = None
    numeric_fill: dict[str, float] | None = None


@dataclass
class PlattCalibrator:
    model: LogisticRegression

    def transform(self, probabilities: np.ndarray | pd.Series) -> np.ndarray:
        probs = np.asarray(probabilities, dtype=float)
        logits = np.log(np.clip(probs, 1e-6, 1 - 1e-6) / np.clip(1.0 - probs, 1e-6, 1 - 1e-6))
        return self.model.predict_proba(logits.reshape(-1, 1))[:, 1]


@dataclass
class ModelArtifacts:
    progress_models: list[EnsembleMember]
    weeks_models: list[EnsembleMember]
    risk_models: list[EnsembleMember]
    calibrator: PlattCalibrator
    progress_features: list[str]
    cat_features: list[str]
    best_model_name: str
    progress_metrics: dict[str, float]
    risk_metrics: dict[str, float]
    weeks_residual_q10: float
    weeks_residual_q90: float
    tier_thresholds: dict[str, float]
    leaderboard_rows: list[dict[str, object]]
    progress_validation_actual: list[float]
    progress_validation_predicted: list[float]
    weeks_validation_actual: list[float]
    weeks_validation_predicted: list[float]
    risk_validation_actual: list[int]
    risk_validation_probability: list[float]
    progress_shap_frame: pd.DataFrame
    risk_shap_frame: pd.DataFrame


def load_inputs(input_dir: Path | None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    wmr_full = pd.read_csv(find_input_file("wmr_full.csv", input_dir), low_memory=False)
    wmr_latest = pd.read_csv(find_input_file("wmr_latest.csv", input_dir), low_memory=False)
    plan_snapshot = pd.read_csv(find_input_file("plan_snapshot.csv", input_dir), low_memory=False)
    report_gb = pd.read_csv(find_input_file("job_progress_report_gb.csv", input_dir), low_memory=False)
    sap = pd.read_csv(find_input_file("sap_drilling_sequence.csv", input_dir), low_memory=False)
    return wmr_full, wmr_latest, plan_snapshot, report_gb, sap


def prepare_plan_snapshot(plan_snapshot: pd.DataFrame) -> pd.DataFrame:
    plan = clean_columns(plan_snapshot)
    if "well_id" not in plan.columns:
        raise KeyError("plan_snapshot.csv is missing Well_ID")
    plan["well_id"] = plan["well_id"].astype(str).str.strip()
    if "createdon" in plan.columns:
        plan["createdon"] = to_dt(plan["createdon"])
        plan = (
            plan.sort_values(["well_id", "createdon"])
            .groupby("well_id", as_index=False)
            .tail(1)
        )
    if "latest_target_end" in plan.columns:
        plan["latest_target_end"] = to_dt(plan["latest_target_end"])
    for col in [
        "cum_prior_plan_frac",
        "w1_plan_frac",
        "w2_plan_frac",
        "w3_plan_frac",
        "w4_plan_frac",
        "w5_plan_frac",
        "currentmonthplanfrac",
        "cumcurrentmonthplanfrac",
    ]:
        if col in plan.columns:
            plan[col] = to_num(plan[col])
    keep = [
        "well_id",
        "project_id",
        "latest_target_end",
        "cum_prior_plan_frac",
        "w1_plan_frac",
        "w2_plan_frac",
        "w3_plan_frac",
        "w4_plan_frac",
        "w5_plan_frac",
        "currentmonthplanfrac",
        "cumcurrentmonthplanfrac",
    ]
    keep = [col for col in keep if col in plan.columns]
    return plan[keep].copy()


def prepare_report_gb(report_gb: pd.DataFrame) -> pd.DataFrame:
    report = clean_columns(report_gb)
    if "well_id" not in report.columns:
        raise KeyError("job_progress_report_gb.csv is missing Well ID")
    report["well_id"] = report["well_id"].astype(str).str.strip()
    actual_col = first_matching_column(report.columns, "current_month_actual")
    plan_col = first_matching_column(report.columns, "current_month_plan")
    if actual_col and plan_col:
        report["current_month_gap"] = to_num(report[actual_col]) - to_num(
            report[plan_col]
        )
    else:
        report["current_month_gap"] = np.nan
    grouped = (
        report.groupby("well_id", as_index=False)
        .agg(
            project_name=("category", first_not_blank),
            project_display_name=("well_name_project_name", first_not_blank),
            current_month_gap=("current_month_gap", "mean"),
        )
    )
    grouped["project_name"] = grouped["project_name"].fillna(
        grouped["project_display_name"]
    )
    return grouped[["well_id", "project_name", "current_month_gap"]].copy()


def prepare_sap(sap_df: pd.DataFrame) -> pd.DataFrame:
    sap = clean_columns(sap_df)
    if "well_id" not in sap.columns:
        raise KeyError("sap_drilling_sequence.csv is missing Well_ID")
    sap["well_id"] = sap["well_id"].astype(str).str.strip()
    if "move_days" in sap.columns:
        sap["move_days"] = to_num(sap["move_days"])
    sap_agg = (
        sap.groupby("well_id", as_index=False)
        .agg(
            move_days_max=("move_days", "max"),
            move_days_mean=("move_days", "mean"),
            field=("field", first_not_blank),
            work_center=("work_center", first_not_blank),
            pdo_well_type=("pdo_well_type", first_not_blank),
        )
    )
    if "work_center" in sap.columns:
        rig_load = (
            sap.groupby("work_center")["well_id"]
            .nunique()
            .rename("rig_load")
            .reset_index()
        )
        sap_agg = sap_agg.merge(rig_load, on="work_center", how="left")
    else:
        sap_agg["rig_load"] = np.nan
    return sap_agg


def add_snapshot_date(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "week_number" not in out.columns:
        raise KeyError("WMR data is missing Week_Number")
    parsed = to_dt(out["week_number"])
    if parsed.notna().mean() < 0.80:
        numeric = to_num(out["week_number"])
        base = pd.Timestamp("2000-01-01")
        parsed = base + pd.to_timedelta(numeric.fillna(0) * 7, unit="D")
    out["snapshot_date"] = parsed
    return out


def normalize_wmr(df: pd.DataFrame) -> pd.DataFrame:
    out = clean_columns(df)
    if "pdo_well_id" not in out.columns:
        raise KeyError("WMR data is missing pdo_well_id")
    out["pdo_well_id"] = out["pdo_well_id"].astype(str).str.strip()
    out = add_snapshot_date(out)
    out["over_all_progress_percentages"] = clamp_progress(
        out["over_all_progress_percentages"]
    )
    numeric_candidates = [
        "engg_kpi_after_rig_off_days",
        "last_week_cum_progress",
        "cum_progress_for_this_week",
        "access_road_5",
        "earth_work_60",
        "cellar_20",
        "beam_pump_base_esp_pcp_foundation_5",
        "water_2",
        "waste_water_2",
        "pe_fussion_pull_20",
        "flowline_construction_progress",
        "flow_line_test_pack_completion_progress",
        "overall_loc_preparation_10_100",
        "overall_engg_10_100",
        "overall_const_10_100",
        "overall_comm_progress_100",
        "ohl_progress",
        "overall_ohl_progr_100",
    ]
    for col in numeric_candidates:
        if col in out.columns:
            out[col] = to_num(out[col])
    for date_col in [
        "actual_start_date",
        "actual_finish_date",
        "actual_rig_on_date",
        "actual_rig_off_date",
        "exp_rig_off_location_sap_data",
        "engineering_actual_finish_date",
    ]:
        if date_col in out.columns:
            out[date_col] = to_dt(out[date_col])
    return out


def build_history_frame(
    wmr_full: pd.DataFrame,
    plan_latest: pd.DataFrame,
    report_map: pd.DataFrame,
    sap_agg: pd.DataFrame,
) -> pd.DataFrame:
    history = normalize_wmr(wmr_full)
    history = history.merge(
        plan_latest.add_prefix("plan_"),
        left_on="pdo_well_id",
        right_on="plan_well_id",
        how="left",
    )
    history = history.merge(
        report_map.add_prefix("report_"),
        left_on="pdo_well_id",
        right_on="report_well_id",
        how="left",
    )
    history = history.merge(
        sap_agg.add_prefix("sap_"),
        left_on="pdo_well_id",
        right_on="sap_well_id",
        how="left",
    )

    history["expected_target_date"] = history.get("exp_rig_off_location_sap_data")
    if "plan_latest_target_end" in history.columns:
        history["expected_target_date"] = history["expected_target_date"].fillna(
            history["plan_latest_target_end"]
        )

    history["project_name"] = history.get("report_project_name")
    if "project_name" not in history.columns:
        history["project_name"] = np.nan
    if "well_location" in history.columns:
        history["project_name"] = history["project_name"].fillna(history["well_location"])
    if "project_id" in history.columns:
        history["project_name"] = history["project_name"].fillna(history["project_id"])

    completeness_cols = [
        "over_all_progress_percentages",
        "rig_no",
        "well_type",
        "expected_target_date",
        "plan_w1_plan_frac",
        "plan_w2_plan_frac",
        "plan_w3_plan_frac",
        "plan_w4_plan_frac",
        "plan_w5_plan_frac",
        "sap_move_days_max",
        "sap_field",
        "report_current_month_gap",
    ]
    available = [col for col in completeness_cols if col in history.columns]
    history["completeness_score"] = history[available].notna().sum(axis=1)
    history = history.sort_values(
        ["pdo_well_id", "snapshot_date", "completeness_score", "over_all_progress_percentages"]
    )
    history = history.drop_duplicates(["pdo_well_id", "snapshot_date"], keep="last")

    history = history.sort_values(["pdo_well_id", "snapshot_date"]).reset_index(drop=True)
    grp = history.groupby("pdo_well_id")["over_all_progress_percentages"]
    history["progress_lag1"] = grp.shift(1)
    history["progress_lag2"] = grp.shift(2)
    history["progress_lag4"] = grp.shift(4)
    history["progress_rolling3w"] = grp.transform(
        lambda x: x.rolling(3, min_periods=1).mean()
    )
    history["progress_velocity"] = (
        history["over_all_progress_percentages"] - history["progress_lag1"]
    )
    history["progress_accel"] = history["progress_velocity"] - (
        history["progress_lag1"] - history["progress_lag2"]
    )
    history["remaining_to_complete"] = 1.0 - history["over_all_progress_percentages"]
    history["plan_5w_total"] = history[
        [col for col in [
            "plan_w1_plan_frac",
            "plan_w2_plan_frac",
            "plan_w3_plan_frac",
            "plan_w4_plan_frac",
            "plan_w5_plan_frac",
        ] if col in history.columns]
    ].sum(axis=1)
    history["days_to_target"] = (
        history["expected_target_date"] - history["snapshot_date"]
    ).dt.days
    if "plan_cumcurrentmonthplanfrac" in history.columns:
        history["plan_curve_gap"] = (
            history["over_all_progress_percentages"] - history["plan_cumcurrentmonthplanfrac"]
        )
    else:
        history["plan_curve_gap"] = np.nan
    history["overdue_target_days"] = np.clip(-history["days_to_target"], 0, None)
    history["is_overdue_target"] = (history["days_to_target"] < 0).astype(float)
    history["stall_1w_flag"] = history["progress_velocity"].abs().lt(0.005).astype(float)
    history["stall_4w_flag"] = (
        history["over_all_progress_percentages"] - history["progress_lag4"]
    ).abs().lt(0.01).astype(float)
    phase_cols = [
        col
        for col in [
            "overall_loc_preparation_10_100",
            "overall_engg_10_100",
            "overall_const_10_100",
            "overall_comm_progress_100",
            "flowline_construction_progress",
            "overall_ohl_progr_100",
            "ohl_progress",
        ]
        if col in history.columns
    ]
    if phase_cols:
        history["phase_mean_progress"] = history[phase_cols].mean(axis=1)
        history["phase_min_progress"] = history[phase_cols].min(axis=1)
        history["phase_max_progress"] = history[phase_cols].max(axis=1)
        history["phase_std_progress"] = history[phase_cols].std(axis=1).fillna(0)
        history["phase_alignment_gap"] = (
            history["over_all_progress_percentages"] - history["phase_mean_progress"]
        )
    else:
        history["phase_mean_progress"] = np.nan
        history["phase_min_progress"] = np.nan
        history["phase_max_progress"] = np.nan
        history["phase_std_progress"] = np.nan
        history["phase_alignment_gap"] = np.nan
    return history


def attach_future_targets(history: pd.DataFrame) -> pd.DataFrame:
    max_snapshot = history["snapshot_date"].max()

    def per_well(group: pd.DataFrame) -> pd.DataFrame:
        g = group.sort_values("snapshot_date").copy()
        g["future_progress_4w"] = g["over_all_progress_percentages"].shift(-4)
        g["is_complete"] = (
            g["over_all_progress_percentages"] >= 0.95
        ) | g.get("actual_finish_date", pd.Series(index=g.index)).notna()

        complete_dates = g.loc[g["is_complete"], "snapshot_date"].to_numpy(dtype="datetime64[ns]")
        snap = g["snapshot_date"].to_numpy(dtype="datetime64[ns]")
        g["observed_completion_date"] = pd.NaT
        if len(complete_dates):
            positions = np.searchsorted(complete_dates, snap, side="left")
            valid = positions < len(complete_dates)
            if valid.any():
                g.loc[valid, "observed_completion_date"] = pd.to_datetime(
                    complete_dates[positions[valid]]
                )
        g["weeks_remaining_actual"] = (
            g["observed_completion_date"] - g["snapshot_date"]
        ).dt.days / 7.0

        eligible = g["expected_target_date"].notna() & (
            g["expected_target_date"] <= max_snapshot
        )
        completion_or_censor = g["observed_completion_date"].fillna(max_snapshot)
        g["miss_target_observed"] = np.where(
            eligible,
            (completion_or_censor > g["expected_target_date"]).astype(float),
            np.nan,
        )
        return g

    parts = [per_well(group) for _, group in history.groupby("pdo_well_id", sort=False)]
    return pd.concat(parts, ignore_index=False)


def fit_catboost_with_fallback(model_cls, params: dict[str, object], train_pool, valid_pool):
    try:
        model = model_cls(**params)
        model.fit(train_pool, eval_set=valid_pool, use_best_model=True)
        return model, "GPU"
    except Exception as exc:
        fallback = dict(params)
        fallback["task_type"] = "CPU"
        model = model_cls(**fallback)
        model.fit(train_pool, eval_set=valid_pool, use_best_model=True)
        print(f"[warn] GPU training failed, fell back to CPU: {exc}")
        return model, "CPU"


def fit_xgboost_with_fallback(model_cls, params: dict[str, object], X_train, y_train, X_valid, y_valid):
    try:
        model = model_cls(**params)
        model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)
        return model, "GPU"
    except Exception as exc:
        fallback = dict(params)
        fallback["device"] = "cpu"
        fallback["tree_method"] = "hist"
        model = model_cls(**fallback)
        model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)
        print(f"[warn] XGBoost GPU training failed, fell back to CPU: {exc}")
        return model, "CPU"


def safe_mape(actual: pd.Series | np.ndarray, predicted: np.ndarray, floor: float = 0.05) -> float:
    actual_values = np.asarray(actual, dtype=float)
    pred_values = np.asarray(predicted, dtype=float)
    mask = np.abs(actual_values) >= floor
    if mask.any():
        denom = np.clip(np.abs(actual_values[mask]), floor, None)
        return float(np.mean(np.abs((actual_values[mask] - pred_values[mask]) / denom)) * 100.0)
    return float(np.mean(np.abs(actual_values - pred_values)) * 100.0)


def normalize_weights(raw_scores: list[float], higher_is_better: bool) -> list[float]:
    values = np.asarray(raw_scores, dtype=float)
    if higher_is_better:
        shifted = np.clip(values - np.nanmin(values) + 1e-6, 1e-6, None)
        weights = shifted / shifted.sum()
    else:
        inv = 1.0 / np.clip(values, 1e-6, None)
        weights = inv / inv.sum()
    return weights.tolist()


def weighted_average(predictions: list[np.ndarray], weights: list[float]) -> np.ndarray:
    stacked = np.vstack(predictions)
    return np.average(stacked, axis=0, weights=np.asarray(weights, dtype=float))


def prepare_xgb_frames(
    train_df: pd.DataFrame,
    frames: list[pd.DataFrame],
    feature_cols: list[str],
    cat_cols: list[str],
) -> tuple[pd.DataFrame, list[pd.DataFrame], dict[str, dict[str, int]], dict[str, float]]:
    category_maps: dict[str, dict[str, int]] = {}
    numeric_fill: dict[str, float] = {}

    encoded_train = pd.DataFrame(index=train_df.index)
    encoded_frames = [pd.DataFrame(index=frame.index) for frame in frames]

    for col in feature_cols:
        if col in cat_cols:
            train_values = (
                train_df[col]
                .astype(str)
                .replace({"nan": "Unknown", "None": "Unknown"})
                .fillna("Unknown")
            )
            unique_values = pd.Index(train_values).drop_duplicates().tolist()
            category_maps[col] = {value: idx for idx, value in enumerate(unique_values)}
            encoded_train[col] = train_values.map(category_maps[col]).fillna(-1).astype(np.int32)
            for idx, frame in enumerate(frames):
                values = (
                    frame[col]
                    .astype(str)
                    .replace({"nan": "Unknown", "None": "Unknown"})
                    .fillna("Unknown")
                )
                encoded_frames[idx][col] = values.map(category_maps[col]).fillna(-1).astype(np.int32)
        else:
            train_values = to_num(train_df[col])
            fill_value = float(train_values.median()) if train_values.notna().any() else 0.0
            if not np.isfinite(fill_value):
                fill_value = 0.0
            numeric_fill[col] = fill_value
            encoded_train[col] = train_values.fillna(fill_value).astype(np.float32)
            for idx, frame in enumerate(frames):
                encoded_frames[idx][col] = to_num(frame[col]).fillna(fill_value).astype(np.float32)

    return encoded_train, encoded_frames, category_maps, numeric_fill


def predict_ensemble(models: list[EnsembleMember], df: pd.DataFrame, feature_cols: list[str], cat_cols: list[str], proba: bool) -> np.ndarray:
    outputs: list[np.ndarray] = []
    weights = [member.weight for member in models]
    catboost_frame = fill_model_frame(df, feature_cols, cat_cols)

    for member in models:
        if member.name.startswith("CatBoost"):
            if proba:
                outputs.append(member.model.predict_proba(catboost_frame)[:, 1])
            else:
                outputs.append(np.asarray(member.model.predict(catboost_frame), dtype=float))
        else:
            if member.category_maps is None or member.numeric_fill is None:
                raise ValueError(f"Ensemble member {member.name} is missing XGBoost encoders")
            encoded = pd.DataFrame(index=df.index)
            for col in feature_cols:
                if col in cat_cols:
                    values = (
                        df[col]
                        .astype(str)
                        .replace({"nan": "Unknown", "None": "Unknown"})
                        .fillna("Unknown")
                    )
                    encoded[col] = values.map(member.category_maps[col]).fillna(-1).astype(np.int32)
                else:
                    encoded[col] = to_num(df[col]).fillna(member.numeric_fill[col]).astype(np.float32)
            if proba:
                outputs.append(member.model.predict_proba(encoded)[:, 1])
            else:
                outputs.append(np.asarray(member.model.predict(encoded), dtype=float))
    return weighted_average(outputs, weights)


def build_platt_calibrator(raw_probabilities: np.ndarray, labels: pd.Series | np.ndarray) -> PlattCalibrator:
    clipped = np.clip(np.asarray(raw_probabilities, dtype=float), 1e-6, 1 - 1e-6)
    logits = np.log(clipped / (1.0 - clipped)).reshape(-1, 1)
    model = LogisticRegression(max_iter=1000)
    model.fit(logits, np.asarray(labels, dtype=int))
    return PlattCalibrator(model=model)


def derive_tier_thresholds(validation_probabilities: np.ndarray) -> dict[str, float]:
    values = np.clip(np.asarray(validation_probabilities, dtype=float), 0, 1) * 100.0
    unique_values = np.unique(np.round(values, 4))

    if unique_values.size >= 4:
        model = KMeans(n_clusters=4, n_init=10, random_state=42)
        model.fit(values.reshape(-1, 1))
        centers = np.sort(model.cluster_centers_.ravel())
        thresholds = (centers[:-1] + centers[1:]) / 2.0
        return {
            "watch": float(thresholds[0]),
            "high_risk": float(thresholds[1]),
            "critical": float(thresholds[2]),
        }

    quantiles = np.quantile(values, [0.50, 0.75, 0.90])
    return {
        "watch": float(quantiles[0]),
        "high_risk": float(quantiles[1]),
        "critical": float(quantiles[2]),
    }


def build_current_frame(
    wmr_latest: pd.DataFrame,
    history: pd.DataFrame,
    plan_latest: pd.DataFrame,
    report_map: pd.DataFrame,
    sap_agg: pd.DataFrame,
) -> pd.DataFrame:
    current = normalize_wmr(wmr_latest)
    current = current.sort_values(["pdo_well_id", "snapshot_date"]).drop_duplicates(
        ["pdo_well_id"], keep="last"
    )

    latest_history = history.sort_values(["pdo_well_id", "snapshot_date"]).groupby(
        "pdo_well_id", as_index=False
    ).tail(1)
    lag_cols = [
        "pdo_well_id",
        "progress_lag1",
        "progress_lag2",
        "progress_lag4",
        "progress_rolling3w",
        "progress_velocity",
        "progress_accel",
        "remaining_to_complete",
    ]
    current = current.merge(latest_history[lag_cols], on="pdo_well_id", how="left")
    current = current.merge(
        plan_latest.add_prefix("plan_"),
        left_on="pdo_well_id",
        right_on="plan_well_id",
        how="left",
    )
    current = current.merge(
        report_map.add_prefix("report_"),
        left_on="pdo_well_id",
        right_on="report_well_id",
        how="left",
    )
    current = current.merge(
        sap_agg.add_prefix("sap_"),
        left_on="pdo_well_id",
        right_on="sap_well_id",
        how="left",
    )

    current["expected_target_date"] = current.get("exp_rig_off_location_sap_data")
    if "plan_latest_target_end" in current.columns:
        current["expected_target_date"] = current["expected_target_date"].fillna(
            current["plan_latest_target_end"]
        )
    current["project_name"] = current.get("report_project_name")
    if "project_name" not in current.columns:
        current["project_name"] = np.nan
    if "well_location" in current.columns:
        current["project_name"] = current["project_name"].fillna(current["well_location"])
    if "project_id" in current.columns:
        current["project_name"] = current["project_name"].fillna(current["project_id"])

    current["plan_5w_total"] = current[
        [col for col in [
            "plan_w1_plan_frac",
            "plan_w2_plan_frac",
            "plan_w3_plan_frac",
            "plan_w4_plan_frac",
            "plan_w5_plan_frac",
        ] if col in current.columns]
    ].sum(axis=1)
    current["days_to_target"] = (
        current["expected_target_date"] - current["snapshot_date"]
    ).dt.days
    if "plan_cumcurrentmonthplanfrac" in current.columns:
        current["plan_curve_gap"] = (
            current["over_all_progress_percentages"] - current["plan_cumcurrentmonthplanfrac"]
        )
    else:
        current["plan_curve_gap"] = np.nan
    current["overdue_target_days"] = np.clip(-current["days_to_target"], 0, None)
    current["is_overdue_target"] = (current["days_to_target"] < 0).astype(float)
    current["stall_1w_flag"] = current["progress_velocity"].abs().lt(0.005).astype(float)
    current["stall_4w_flag"] = (
        current["over_all_progress_percentages"] - current["progress_lag4"]
    ).abs().lt(0.01).astype(float)
    phase_cols = [
        col
        for col in [
            "overall_loc_preparation_10_100",
            "overall_engg_10_100",
            "overall_const_10_100",
            "overall_comm_progress_100",
            "flowline_construction_progress",
            "overall_ohl_progr_100",
            "ohl_progress",
        ]
        if col in current.columns
    ]
    if phase_cols:
        current["phase_mean_progress"] = current[phase_cols].mean(axis=1)
        current["phase_min_progress"] = current[phase_cols].min(axis=1)
        current["phase_max_progress"] = current[phase_cols].max(axis=1)
        current["phase_std_progress"] = current[phase_cols].std(axis=1).fillna(0)
        current["phase_alignment_gap"] = (
            current["over_all_progress_percentages"] - current["phase_mean_progress"]
        )
    else:
        current["phase_mean_progress"] = np.nan
        current["phase_min_progress"] = np.nan
        current["phase_max_progress"] = np.nan
        current["phase_std_progress"] = np.nan
        current["phase_alignment_gap"] = np.nan
    if "remaining_to_complete" not in current.columns or current["remaining_to_complete"].isna().all():
        current["remaining_to_complete"] = 1.0 - current["over_all_progress_percentages"]
    return current


def choose_feature_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    numeric_features = [
        "over_all_progress_percentages",
        "progress_lag1",
        "progress_lag2",
        "progress_lag4",
        "progress_rolling3w",
        "progress_velocity",
        "progress_accel",
        "remaining_to_complete",
        "access_road_5",
        "earth_work_60",
        "cellar_20",
        "beam_pump_base_esp_pcp_foundation_5",
        "water_2",
        "pe_fussion_pull_20",
        "overall_loc_preparation_10_100",
        "overall_engg_10_100",
        "overall_const_10_100",
        "overall_comm_progress_100",
        "flowline_construction_progress",
        "ohl_progress",
        "overall_ohl_progr_100",
        "engg_kpi_after_rig_off_days",
        "report_current_month_gap",
        "sap_move_days_max",
        "sap_move_days_mean",
        "sap_rig_load",
        "plan_w1_plan_frac",
        "plan_w2_plan_frac",
        "plan_w3_plan_frac",
        "plan_w4_plan_frac",
        "plan_w5_plan_frac",
        "plan_5w_total",
        "plan_cumcurrentmonthplanfrac",
        "plan_curve_gap",
        "days_to_target",
        "overdue_target_days",
        "is_overdue_target",
        "stall_1w_flag",
        "stall_4w_flag",
        "phase_mean_progress",
        "phase_min_progress",
        "phase_max_progress",
        "phase_std_progress",
        "phase_alignment_gap",
    ]
    categorical_features = [
        "rig_no",
        "well_type",
        "buffer_status",
        "sap_field",
        "sap_work_center",
        "sap_pdo_well_type",
        "project_name",
    ]
    features = [col for col in numeric_features + categorical_features if col in df.columns]
    cats = [col for col in categorical_features if col in features]
    return features, cats


def fill_model_frame(df: pd.DataFrame, feature_cols: list[str], cat_cols: list[str]) -> pd.DataFrame:
    out = df[feature_cols].copy()
    for col in feature_cols:
        if col in cat_cols:
            out[col] = out[col].astype(str).replace({"nan": "Unknown", "None": "Unknown"}).fillna("Unknown")
        else:
            out[col] = to_num(out[col]).fillna(out[col].median())
    return out


def make_time_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = sorted(date for date in df["snapshot_date"].dropna().unique())
    if len(dates) < 8:
        raise ValueError("Not enough time points for a time-based validation split.")
    split_idx = max(1, int(len(dates) * 0.8))
    cutoff = pd.Timestamp(dates[split_idx - 1])
    train = df[df["snapshot_date"] < cutoff].copy()
    valid = df[df["snapshot_date"] >= cutoff].copy()
    if train.empty or valid.empty:
        raise ValueError("Time split produced an empty train or validation set.")
    return train, valid


def train_models(history: pd.DataFrame) -> ModelArtifacts:
    CatBoostClassifier, CatBoostRegressor, Pool = ensure_catboost()
    XGBClassifier, XGBRegressor = ensure_xgboost()
    feature_cols, cat_cols = choose_feature_columns(history)

    reg_params = {
        "loss_function": "RMSE",
        "eval_metric": "RMSE",
        "iterations": 3200,
        "learning_rate": 0.025,
        "depth": 8,
        "l2_leaf_reg": 5.0,
        "verbose": 200,
        "od_type": "Iter",
        "od_wait": 250,
        "allow_writing_files": False,
        "task_type": "GPU",
    }
    clf_params = {
        "loss_function": "Logloss",
        "eval_metric": "AUC",
        "iterations": 2600,
        "learning_rate": 0.025,
        "depth": 8,
        "l2_leaf_reg": 5.0,
        "verbose": 200,
        "od_type": "Iter",
        "od_wait": 250,
        "allow_writing_files": False,
        "task_type": "GPU",
    }
    xgb_reg_params = {
        "objective": "reg:squarederror",
        "n_estimators": 2200,
        "learning_rate": 0.025,
        "max_depth": 8,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "reg_lambda": 1.5,
        "reg_alpha": 0.05,
        "min_child_weight": 2.0,
        "tree_method": "hist",
        "device": "cuda",
        "random_state": 42,
    }
    xgb_clf_params = {
        "objective": "binary:logistic",
        "eval_metric": "auc",
        "n_estimators": 2200,
        "learning_rate": 0.025,
        "max_depth": 8,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "reg_lambda": 1.5,
        "reg_alpha": 0.05,
        "min_child_weight": 2.0,
        "tree_method": "hist",
        "device": "cuda",
        "random_state": 42,
    }

    # 4-week future progress ensemble
    progress_df = history.dropna(subset=["future_progress_4w", "snapshot_date"]).copy()
    train_progress, valid_progress = make_time_split(progress_df)
    X_train_progress_cb = fill_model_frame(train_progress, feature_cols, cat_cols)
    X_valid_progress_cb = fill_model_frame(valid_progress, feature_cols, cat_cols)
    y_train_progress = train_progress["future_progress_4w"]
    y_valid_progress = valid_progress["future_progress_4w"]
    progress_train_pool = Pool(X_train_progress_cb, y_train_progress, cat_features=cat_cols)
    progress_valid_pool = Pool(X_valid_progress_cb, y_valid_progress, cat_features=cat_cols)
    X_train_progress_xgb, [X_valid_progress_xgb], progress_cat_maps, progress_num_fill = prepare_xgb_frames(
        train_progress,
        [valid_progress],
        feature_cols,
        cat_cols,
    )

    progress_members: list[EnsembleMember] = []
    progress_val_predictions: list[np.ndarray] = []
    progress_member_scores: list[float] = []
    leaderboard_rows: list[dict[str, object]] = []

    for seed in [42, 84]:
        cat_model, backend = fit_catboost_with_fallback(
            CatBoostRegressor,
            {**reg_params, "random_seed": seed},
            progress_train_pool,
            progress_valid_pool,
        )
        cat_pred = np.clip(cat_model.predict(X_valid_progress_cb), 0, 1)
        progress_members.append(
            EnsembleMember(
                name=f"CatBoostRegressor_seed{seed}",
                model=cat_model,
                backend=backend,
                weight=0.0,
            )
        )
        progress_val_predictions.append(cat_pred)
        progress_member_scores.append(float(np.sqrt(mean_squared_error(y_valid_progress, cat_pred))))
        leaderboard_rows.append(
            {
                "model": f"CatBoostRegressor_seed{seed}",
                "target": "future_progress_4w",
                "backend": backend,
                "weight": 0.0,
                "rmse": float(np.sqrt(mean_squared_error(y_valid_progress, cat_pred))),
                "mae": float(mean_absolute_error(y_valid_progress, cat_pred)),
                "r2": float(r2_score(y_valid_progress, cat_pred)),
                "auc": np.nan,
                "brier": np.nan,
            }
        )

    xgb_progress_model, xgb_progress_backend = fit_xgboost_with_fallback(
        XGBRegressor,
        xgb_reg_params,
        X_train_progress_xgb,
        y_train_progress,
        X_valid_progress_xgb,
        y_valid_progress,
    )
    xgb_progress_pred = np.clip(xgb_progress_model.predict(X_valid_progress_xgb), 0, 1)
    progress_members.append(
        EnsembleMember(
            name="XGBoostRegressor",
            model=xgb_progress_model,
            backend=xgb_progress_backend,
            weight=0.0,
            category_maps=progress_cat_maps,
            numeric_fill=progress_num_fill,
        )
    )
    progress_val_predictions.append(xgb_progress_pred)
    progress_member_scores.append(float(np.sqrt(mean_squared_error(y_valid_progress, xgb_progress_pred))))
    leaderboard_rows.append(
        {
            "model": "XGBoostRegressor",
            "target": "future_progress_4w",
            "backend": xgb_progress_backend,
            "weight": 0.0,
            "rmse": float(np.sqrt(mean_squared_error(y_valid_progress, xgb_progress_pred))),
            "mae": float(mean_absolute_error(y_valid_progress, xgb_progress_pred)),
            "r2": float(r2_score(y_valid_progress, xgb_progress_pred)),
            "auc": np.nan,
            "brier": np.nan,
        }
    )

    progress_weights = normalize_weights(progress_member_scores, higher_is_better=False)
    for member, weight in zip(progress_members, progress_weights):
        member.weight = weight
    progress_pred = np.clip(weighted_average(progress_val_predictions, progress_weights), 0, 1)
    progress_metrics = {
        "rmse": float(np.sqrt(mean_squared_error(y_valid_progress, progress_pred))),
        "mae": float(mean_absolute_error(y_valid_progress, progress_pred)),
        "r2": float(r2_score(y_valid_progress, progress_pred)),
        "mape_valid": safe_mape(y_valid_progress, progress_pred),
    }
    leaderboard_rows.append(
        {
            "model": "DecisionStudio_Progress_Ensemble",
            "target": "future_progress_4w",
            "backend": "GPU/CPU mixed",
            "weight": 1.0,
            "rmse": progress_metrics["rmse"],
            "mae": progress_metrics["mae"],
            "r2": progress_metrics["r2"],
            "auc": np.nan,
            "brier": np.nan,
        }
    )

    # Weeks-to-completion ensemble
    weeks_df = history.dropna(subset=["weeks_remaining_actual", "snapshot_date"]).copy()
    weeks_df = weeks_df[weeks_df["weeks_remaining_actual"] >= 0]
    train_weeks, valid_weeks = make_time_split(weeks_df)
    X_train_weeks_cb = fill_model_frame(train_weeks, feature_cols, cat_cols)
    X_valid_weeks_cb = fill_model_frame(valid_weeks, feature_cols, cat_cols)
    y_train_weeks = train_weeks["weeks_remaining_actual"]
    y_valid_weeks = valid_weeks["weeks_remaining_actual"]
    weeks_train_pool = Pool(X_train_weeks_cb, y_train_weeks, cat_features=cat_cols)
    weeks_valid_pool = Pool(X_valid_weeks_cb, y_valid_weeks, cat_features=cat_cols)
    X_train_weeks_xgb, [X_valid_weeks_xgb], weeks_cat_maps, weeks_num_fill = prepare_xgb_frames(
        train_weeks,
        [valid_weeks],
        feature_cols,
        cat_cols,
    )

    weeks_members: list[EnsembleMember] = []
    weeks_val_predictions: list[np.ndarray] = []
    weeks_member_scores: list[float] = []

    for seed in [42, 84]:
        cat_model, backend = fit_catboost_with_fallback(
            CatBoostRegressor,
            {**reg_params, "random_seed": seed},
            weeks_train_pool,
            weeks_valid_pool,
        )
        cat_pred = np.clip(cat_model.predict(X_valid_weeks_cb), 0, None)
        weeks_members.append(
            EnsembleMember(
                name=f"CatBoostWeeks_seed{seed}",
                model=cat_model,
                backend=backend,
                weight=0.0,
            )
        )
        weeks_val_predictions.append(cat_pred)
        weeks_member_scores.append(float(np.sqrt(mean_squared_error(y_valid_weeks, cat_pred))))
        leaderboard_rows.append(
            {
                "model": f"CatBoostWeeks_seed{seed}",
                "target": "weeks_remaining_actual",
                "backend": backend,
                "weight": 0.0,
                "rmse": float(np.sqrt(mean_squared_error(y_valid_weeks, cat_pred))),
                "mae": float(mean_absolute_error(y_valid_weeks, cat_pred)),
                "r2": float(r2_score(y_valid_weeks, cat_pred)),
                "auc": np.nan,
                "brier": np.nan,
            }
        )

    xgb_weeks_model, xgb_weeks_backend = fit_xgboost_with_fallback(
        XGBRegressor,
        xgb_reg_params,
        X_train_weeks_xgb,
        y_train_weeks,
        X_valid_weeks_xgb,
        y_valid_weeks,
    )
    xgb_weeks_pred = np.clip(xgb_weeks_model.predict(X_valid_weeks_xgb), 0, None)
    weeks_members.append(
        EnsembleMember(
            name="XGBoostWeeks",
            model=xgb_weeks_model,
            backend=xgb_weeks_backend,
            weight=0.0,
            category_maps=weeks_cat_maps,
            numeric_fill=weeks_num_fill,
        )
    )
    weeks_val_predictions.append(xgb_weeks_pred)
    weeks_member_scores.append(float(np.sqrt(mean_squared_error(y_valid_weeks, xgb_weeks_pred))))
    leaderboard_rows.append(
        {
            "model": "XGBoostWeeks",
            "target": "weeks_remaining_actual",
            "backend": xgb_weeks_backend,
            "weight": 0.0,
            "rmse": float(np.sqrt(mean_squared_error(y_valid_weeks, xgb_weeks_pred))),
            "mae": float(mean_absolute_error(y_valid_weeks, xgb_weeks_pred)),
            "r2": float(r2_score(y_valid_weeks, xgb_weeks_pred)),
            "auc": np.nan,
            "brier": np.nan,
        }
    )

    weeks_weights = normalize_weights(weeks_member_scores, higher_is_better=False)
    for member, weight in zip(weeks_members, weeks_weights):
        member.weight = weight
    weeks_pred_valid = np.clip(weighted_average(weeks_val_predictions, weeks_weights), 0, None)
    weeks_residuals = y_valid_weeks - weeks_pred_valid
    weeks_residual_q10, weeks_residual_q90 = np.quantile(weeks_residuals, [0.10, 0.90])
    leaderboard_rows.append(
        {
            "model": "DecisionStudio_Weeks_Ensemble",
            "target": "weeks_remaining_actual",
            "backend": "GPU/CPU mixed",
            "weight": 1.0,
            "rmse": float(np.sqrt(mean_squared_error(y_valid_weeks, weeks_pred_valid))),
            "mae": float(mean_absolute_error(y_valid_weeks, weeks_pred_valid)),
            "r2": float(r2_score(y_valid_weeks, weeks_pred_valid)),
            "auc": np.nan,
            "brier": np.nan,
        }
    )

    # Risk ensemble with Platt calibration and percentile-based tiering
    risk_df = history.dropna(subset=["miss_target_observed", "snapshot_date"]).copy()
    risk_df["miss_target_observed"] = risk_df["miss_target_observed"].astype(int)
    train_risk, valid_risk = make_time_split(risk_df)
    X_train_risk_cb = fill_model_frame(train_risk, feature_cols, cat_cols)
    X_valid_risk_cb = fill_model_frame(valid_risk, feature_cols, cat_cols)
    y_train_risk = train_risk["miss_target_observed"]
    y_valid_risk = valid_risk["miss_target_observed"]
    risk_train_pool = Pool(X_train_risk_cb, y_train_risk, cat_features=cat_cols)
    risk_valid_pool = Pool(X_valid_risk_cb, y_valid_risk, cat_features=cat_cols)
    X_train_risk_xgb, [X_valid_risk_xgb], risk_cat_maps, risk_num_fill = prepare_xgb_frames(
        train_risk,
        [valid_risk],
        feature_cols,
        cat_cols,
    )

    risk_members: list[EnsembleMember] = []
    risk_val_predictions: list[np.ndarray] = []
    risk_member_scores: list[float] = []

    for seed in [42, 84]:
        cat_model, backend = fit_catboost_with_fallback(
            CatBoostClassifier,
            {**clf_params, "random_seed": seed},
            risk_train_pool,
            risk_valid_pool,
        )
        cat_prob = cat_model.predict_proba(X_valid_risk_cb)[:, 1]
        risk_members.append(
            EnsembleMember(
                name=f"CatBoostClassifier_seed{seed}",
                model=cat_model,
                backend=backend,
                weight=0.0,
            )
        )
        risk_val_predictions.append(cat_prob)
        risk_member_scores.append(float(roc_auc_score(y_valid_risk, cat_prob)))
        leaderboard_rows.append(
            {
                "model": f"CatBoostClassifier_seed{seed}",
                "target": "miss_target_observed",
                "backend": backend,
                "weight": 0.0,
                "rmse": np.nan,
                "mae": np.nan,
                "r2": np.nan,
                "auc": float(roc_auc_score(y_valid_risk, cat_prob)),
                "brier": float(np.mean((y_valid_risk - cat_prob) ** 2)),
            }
        )

    xgb_risk_model, xgb_risk_backend = fit_xgboost_with_fallback(
        XGBClassifier,
        xgb_clf_params,
        X_train_risk_xgb,
        y_train_risk,
        X_valid_risk_xgb,
        y_valid_risk,
    )
    xgb_risk_prob = xgb_risk_model.predict_proba(X_valid_risk_xgb)[:, 1]
    risk_members.append(
        EnsembleMember(
            name="XGBoostClassifier",
            model=xgb_risk_model,
            backend=xgb_risk_backend,
            weight=0.0,
            category_maps=risk_cat_maps,
            numeric_fill=risk_num_fill,
        )
    )
    risk_val_predictions.append(xgb_risk_prob)
    risk_member_scores.append(float(roc_auc_score(y_valid_risk, xgb_risk_prob)))
    leaderboard_rows.append(
        {
            "model": "XGBoostClassifier",
            "target": "miss_target_observed",
            "backend": xgb_risk_backend,
            "weight": 0.0,
            "rmse": np.nan,
            "mae": np.nan,
            "r2": np.nan,
            "auc": float(roc_auc_score(y_valid_risk, xgb_risk_prob)),
            "brier": float(np.mean((y_valid_risk - xgb_risk_prob) ** 2)),
        }
    )

    risk_weights = normalize_weights(risk_member_scores, higher_is_better=True)
    for member, weight in zip(risk_members, risk_weights):
        member.weight = weight

    risk_raw_valid = np.clip(weighted_average(risk_val_predictions, risk_weights), 1e-6, 1 - 1e-6)
    calibrator = build_platt_calibrator(risk_raw_valid, y_valid_risk)
    valid_risk_prob = np.clip(calibrator.transform(risk_raw_valid), 0, 1)
    tier_thresholds = derive_tier_thresholds(valid_risk_prob)
    risk_metrics = {
        "auc": float(roc_auc_score(y_valid_risk, valid_risk_prob)),
        "brier": float(np.mean((y_valid_risk - valid_risk_prob) ** 2)),
    }
    leaderboard_rows.append(
        {
            "model": "DecisionStudio_Risk_Ensemble",
            "target": "miss_target_observed",
            "backend": "GPU/CPU mixed",
            "weight": 1.0,
            "rmse": np.nan,
            "mae": np.nan,
            "r2": np.nan,
            "auc": risk_metrics["auc"],
            "brier": risk_metrics["brier"],
        }
    )

    for row in leaderboard_rows:
        model_name = str(row["model"])
        weight = 0.0
        for members in [progress_members, weeks_members, risk_members]:
            for member in members:
                if member.name == model_name:
                    weight = member.weight
                    break
        if weight:
            row["weight"] = weight

    return ModelArtifacts(
        progress_models=progress_members,
        weeks_models=weeks_members,
        risk_models=risk_members,
        calibrator=calibrator,
        progress_features=feature_cols,
        cat_features=cat_cols,
        best_model_name="DecisionStudio_Ensemble_CatBoost_XGBoost",
        progress_metrics=progress_metrics,
        risk_metrics=risk_metrics,
        weeks_residual_q10=float(weeks_residual_q10),
        weeks_residual_q90=float(weeks_residual_q90),
        tier_thresholds=tier_thresholds,
        leaderboard_rows=leaderboard_rows,
        progress_validation_actual=y_valid_progress.tolist(),
        progress_validation_predicted=progress_pred.tolist(),
        weeks_validation_actual=y_valid_weeks.tolist(),
        weeks_validation_predicted=weeks_pred_valid.tolist(),
        risk_validation_actual=y_valid_risk.astype(int).tolist(),
        risk_validation_probability=valid_risk_prob.tolist(),
        progress_shap_frame=X_valid_progress_cb.sample(
            n=min(400, len(X_valid_progress_cb)),
            random_state=42,
        ).copy(),
        risk_shap_frame=X_valid_risk_cb.sample(
            n=min(400, len(X_valid_risk_cb)),
            random_state=42,
        ).copy(),
    )


def classify_tier(score_value: pd.Series, thresholds: dict[str, float]) -> pd.Series:
    def _tier(value: float) -> str:
        if value >= thresholds["critical"]:
            return "CRITICAL"
        if value >= thresholds["high_risk"]:
            return "HIGH_RISK"
        if value >= thresholds["watch"]:
            return "WATCH"
        return "HEALTHY"

    return score_value.apply(_tier)


def score_current(current: pd.DataFrame, artifacts: ModelArtifacts) -> tuple[pd.DataFrame, pd.DataFrame]:
    progress_4w_pred = np.clip(
        predict_ensemble(
            artifacts.progress_models,
            current,
            artifacts.progress_features,
            artifacts.cat_features,
            proba=False,
        ),
        0,
        1,
    )
    weeks_pred = np.clip(
        predict_ensemble(
            artifacts.weeks_models,
            current,
            artifacts.progress_features,
            artifacts.cat_features,
            proba=False,
        ),
        0,
        None,
    )
    risk_raw = np.clip(
        predict_ensemble(
            artifacts.risk_models,
            current,
            artifacts.progress_features,
            artifacts.cat_features,
            proba=True,
        ),
        1e-6,
        1 - 1e-6,
    )
    risk_prob = np.clip(artifacts.calibrator.transform(risk_raw), 0, 1)

    current = current.copy()
    current["progress_4w_pred"] = progress_4w_pred
    current["weeks_remaining_predicted"] = weeks_pred
    current["risk_probability"] = (risk_prob * 100.0).round(1)
    current["risk_score"] = current["risk_probability"]
    current["risk_tier"] = classify_tier(pd.Series(current["risk_score"]), artifacts.tier_thresholds)

    current["predicted_completion_date"] = current["snapshot_date"] + pd.to_timedelta(
        np.round(current["weeks_remaining_predicted"] * 7).astype(int), unit="D"
    )
    current["completion_date_early"] = current["snapshot_date"] + pd.to_timedelta(
        np.round(np.clip(current["weeks_remaining_predicted"] + artifacts.weeks_residual_q10, 0, None) * 7).astype(int),
        unit="D",
    )
    current["completion_date_late"] = current["snapshot_date"] + pd.to_timedelta(
        np.round(np.clip(current["weeks_remaining_predicted"] + artifacts.weeks_residual_q90, 0, None) * 7).astype(int),
        unit="D",
    )

    current["current_progress_pct"] = (
        current["over_all_progress_percentages"].fillna(0) * 100.0
    ).round(1)
    current["project_name"] = current["project_name"].fillna("Unknown")
    current["rig_no"] = current["rig_no"].fillna("UNKNOWN")
    current["well_type"] = current["well_type"].fillna("UNKNOWN")

    risk_scores = current[
        [
            "pdo_well_id",
            "well_name_after_spud",
            "project_name",
            "rig_no",
            "well_type",
            "over_all_progress_percentages",
            "progress_velocity",
            "days_to_target",
            "predicted_completion_date",
            "completion_date_early",
            "completion_date_late",
            "weeks_remaining_predicted",
            "risk_probability",
            "risk_score",
            "risk_tier",
        ]
    ].copy()

    priority = current[
        [
            "pdo_well_id",
            "well_name_after_spud",
            "project_name",
            "rig_no",
            "well_type",
            "current_progress_pct",
            "risk_score",
            "risk_tier",
            "predicted_completion_date",
            "completion_date_early",
            "completion_date_late",
            "weeks_remaining_predicted",
        ]
    ].copy()
    priority = priority.sort_values(
        ["risk_score", "weeks_remaining_predicted", "current_progress_pct"],
        ascending=[False, False, True],
    )
    return risk_scores, priority


def build_feature_importance(history: pd.DataFrame, artifacts: ModelArtifacts) -> pd.DataFrame:
    _, _, Pool = ensure_catboost()
    base = history.dropna(subset=["future_progress_4w"]).copy()
    catboost_frame = fill_model_frame(base, artifacts.progress_features, artifacts.cat_features)
    pool = Pool(
        catboost_frame,
        base["future_progress_4w"],
        cat_features=artifacts.cat_features,
    )
    parts: list[pd.DataFrame] = []

    for member in artifacts.progress_models:
        if member.name.startswith("CatBoost"):
            raw_importance = np.asarray(member.model.get_feature_importance(pool), dtype=float)
        else:
            raw_importance = np.asarray(member.model.feature_importances_, dtype=float)
        normalized = raw_importance / np.clip(raw_importance.sum(), 1e-6, None)
        parts.append(
            pd.DataFrame(
                {
                    "feature": artifacts.progress_features,
                    "importance_component": normalized,
                    "model": member.name,
                    "weight": member.weight,
                }
            )
        )

    combined = pd.concat(parts, ignore_index=True)
    combined["weighted_importance"] = combined["importance_component"] * combined["weight"]
    out = (
        combined.groupby("feature", as_index=False)["weighted_importance"]
        .sum()
        .rename(columns={"weighted_importance": "importance"})
        .sort_values("importance", ascending=False)
    )
    out["importance"] = out["importance"] / np.clip(out["importance"].sum(), 1e-6, None)
    return out.reset_index(drop=True)


def humanize_feature(name: str) -> str:
    return str(name).replace("_", " ").replace("pdo", "PDO").strip().title()


def build_leaderboard_frame(artifacts: ModelArtifacts) -> pd.DataFrame:
    leaderboard = pd.DataFrame(artifacts.leaderboard_rows)
    if leaderboard.empty:
        return leaderboard
    preferred = [
        "target",
        "model",
        "backend",
        "weight",
        "rmse",
        "mae",
        "r2",
        "auc",
        "brier",
    ]
    existing = [col for col in preferred if col in leaderboard.columns]
    return leaderboard[existing].sort_values(["target", "model"]).reset_index(drop=True)


def build_feature_importance_chart(feature_importance: pd.DataFrame, output_path: Path) -> None:
    plt = ensure_matplotlib()
    top = feature_importance.head(15).iloc[::-1].copy()
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    ax.barh(
        [humanize_feature(v) for v in top["feature"]],
        top["importance"],
        color="#E87722",
        alpha=0.9,
    )
    ax.set_title("Ensemble Feature Importance", fontsize=13, fontweight="bold")
    ax.set_xlabel("Normalized importance")
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_progress_diagnostics_chart(artifacts: ModelArtifacts, output_path: Path) -> None:
    plt = ensure_matplotlib()
    actual = np.asarray(artifacts.progress_validation_actual, dtype=float)
    predicted = np.asarray(artifacts.progress_validation_predicted, dtype=float)
    residuals = actual - predicted

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
    axes[0].scatter(actual, predicted, s=11, alpha=0.55, color="#2563EB", edgecolors="none")
    min_val = float(min(actual.min(), predicted.min()))
    max_val = float(max(actual.max(), predicted.max()))
    axes[0].plot([min_val, max_val], [min_val, max_val], linestyle="--", color="#DC2626", linewidth=1.2)
    axes[0].set_title("Actual vs predicted 4-week progress")
    axes[0].set_xlabel("Actual progress")
    axes[0].set_ylabel("Predicted progress")
    axes[0].grid(alpha=0.2)

    axes[1].hist(residuals, bins=35, color="#16A34A", alpha=0.75, edgecolor="white")
    axes[1].axvline(float(np.mean(residuals)), color="#DC2626", linestyle="--", linewidth=1.2)
    axes[1].set_title("Residual distribution")
    axes[1].set_xlabel("Residual (actual - predicted)")
    axes[1].set_ylabel("Rows")
    axes[1].grid(alpha=0.2)

    fig.suptitle("Decision Studio diagnostics", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_completion_forecast_chart(
    risk_scores: pd.DataFrame,
    reference_date: pd.Timestamp,
    output_path: Path,
) -> None:
    plt = ensure_matplotlib()
    chart_df = risk_scores.copy()
    for col in [
        "predicted_completion_date",
        "completion_date_early",
        "completion_date_late",
    ]:
        chart_df[col] = pd.to_datetime(chart_df[col], errors="coerce")
    chart_df = chart_df.dropna(subset=["predicted_completion_date"]).sort_values("predicted_completion_date").head(20)
    if chart_df.empty:
        return

    chart_df["median_days"] = (chart_df["predicted_completion_date"] - reference_date).dt.days
    chart_df["early_days"] = (chart_df["completion_date_early"] - reference_date).dt.days
    chart_df["late_days"] = (chart_df["completion_date_late"] - reference_date).dt.days
    chart_df = chart_df.iloc[::-1]
    y = np.arange(len(chart_df))

    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    ax.hlines(y, chart_df["early_days"], chart_df["late_days"], color="#93C5FD", linewidth=6, alpha=0.9)
    ax.scatter(chart_df["median_days"], y, color="#DC2626", s=28, zorder=3, label="Median estimate")
    ax.axvline(0, color="#9CA3AF", linestyle="--", linewidth=1.1, label="Reference date")
    ax.set_yticks(y)
    ax.set_yticklabels(chart_df["well_name_after_spud"], fontsize=8)
    ax.set_xlabel(f"Days from snapshot ({reference_date.strftime('%Y-%m-%d')})")
    ax.set_title("Predicted completion dates with 80% confidence interval")
    ax.grid(axis="x", alpha=0.2)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_rig_performance_chart(risk_scores: pd.DataFrame, output_path: Path) -> None:
    plt = ensure_matplotlib()
    rig_perf = (
        risk_scores.groupby("rig_no", as_index=False)
        .agg(
            avg_progress=("over_all_progress_percentages", "mean"),
            wells=("pdo_well_id", "nunique"),
            mean_risk=("risk_score", "mean"),
        )
        .dropna(subset=["rig_no"])
        .sort_values(["avg_progress", "wells"], ascending=[False, False])
        .head(12)
    )
    if rig_perf.empty:
        return

    rig_perf["avg_progress_pct"] = rig_perf["avg_progress"] * 100.0
    rig_perf = rig_perf.iloc[::-1]

    fig, ax1 = plt.subplots(figsize=(11, 6.3))
    ax1.barh(rig_perf["rig_no"], rig_perf["avg_progress_pct"], color="#2563EB", alpha=0.8, label="Avg progress %")
    ax1.set_xlabel("Average progress (%)")
    ax1.grid(axis="x", alpha=0.2)

    ax2 = ax1.twiny()
    ax2.plot(rig_perf["mean_risk"], rig_perf["rig_no"], color="#E87722", marker="o", linewidth=1.6, label="Mean risk")
    ax2.set_xlabel("Mean risk score")

    fig.suptitle("Rig fleet performance", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def get_catboost_shap(member: EnsembleMember, frame: pd.DataFrame, cat_features: list[str]) -> tuple[np.ndarray, list[str]]:
    _, _, Pool = ensure_catboost()
    pool = Pool(frame, cat_features=cat_features)
    raw = np.asarray(member.model.get_feature_importance(pool, type="ShapValues"), dtype=float)
    if raw.ndim == 3:
        raw = raw[0]
    shap_values = raw[:, :-1] if raw.shape[1] == frame.shape[1] + 1 else raw
    return shap_values, frame.columns.tolist()


def build_shap_beeswarm_chart(
    shap_values: np.ndarray,
    frame: pd.DataFrame,
    output_path: Path,
    title: str,
) -> None:
    plt = ensure_matplotlib()
    if shap_values.size == 0:
        return
    mean_abs = np.mean(np.abs(shap_values), axis=0)
    top_idx = np.argsort(mean_abs)[::-1][:12]
    fig, ax = plt.subplots(figsize=(11.5, 7.2))
    cmap = plt.get_cmap("coolwarm")

    for rank, feature_idx in enumerate(top_idx):
        feature = frame.iloc[:, feature_idx]
        values = pd.to_numeric(feature, errors="coerce")
        if values.isna().all():
            values = pd.Series(pd.factorize(feature.astype(str))[0], index=feature.index, dtype=float)
        values = values.fillna(float(values.median()) if values.notna().any() else 0.0)
        vmin = float(values.min())
        vmax = float(values.max())
        denom = max(vmax - vmin, 1e-6)
        colors = (values - vmin) / denom
        y_base = len(top_idx) - rank - 1
        jitter = np.random.default_rng(42 + rank).normal(0, 0.11, size=len(values))
        ax.scatter(
            shap_values[:, feature_idx],
            np.full(len(values), y_base) + jitter,
            c=colors,
            cmap=cmap,
            s=13,
            alpha=0.7,
            edgecolors="none",
        )

    ax.axvline(0, color="#A3A3A3", linestyle="--", linewidth=1.0)
    ax.set_yticks(np.arange(len(top_idx)))
    ax.set_yticklabels([humanize_feature(frame.columns[idx]) for idx in top_idx[::-1]])
    ax.set_xlabel("SHAP value")
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.15)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_shap_importance_chart(
    shap_values: np.ndarray,
    frame: pd.DataFrame,
    output_path: Path,
    title: str,
) -> None:
    plt = ensure_matplotlib()
    importance = pd.DataFrame(
        {
            "feature": frame.columns,
            "importance": np.mean(np.abs(shap_values), axis=0),
        }
    ).sort_values("importance", ascending=False).head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10.8, 6.3))
    ax.barh(
        [humanize_feature(v) for v in importance["feature"]],
        importance["importance"],
        color="#2563EB",
        alpha=0.9,
    )
    ax.set_xlabel("Mean |SHAP value|")
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_signed_shap_chart(
    shap_values: np.ndarray,
    frame: pd.DataFrame,
    output_path: Path,
    title: str,
) -> None:
    plt = ensure_matplotlib()
    signed = pd.DataFrame(
        {
            "feature": frame.columns,
            "signed_shap": np.mean(shap_values, axis=0),
            "abs_importance": np.mean(np.abs(shap_values), axis=0),
        }
    ).sort_values("abs_importance", ascending=False).head(12).iloc[::-1]
    colors = ["#DC2626" if val > 0 else "#16A34A" for val in signed["signed_shap"]]
    fig, ax = plt.subplots(figsize=(10.8, 6.3))
    ax.barh(
        [humanize_feature(v) for v in signed["feature"]],
        signed["signed_shap"],
        color=colors,
        alpha=0.9,
    )
    ax.axvline(0, color="#A3A3A3", linestyle="--", linewidth=1.0)
    ax.set_xlabel("Average SHAP contribution")
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_survival_training_frame(history: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, group in history.sort_values(["pdo_well_id", "snapshot_date"]).groupby("pdo_well_id", sort=False):
        anchor = group.iloc[0]
        start_date = pd.to_datetime(anchor["snapshot_date"], errors="coerce")
        completion_dates = pd.to_datetime(group["observed_completion_date"], errors="coerce").dropna()
        completion_date = completion_dates.min() if not completion_dates.empty else pd.NaT
        censor_date = pd.to_datetime(group["snapshot_date"], errors="coerce").max()
        end_date = completion_date if pd.notna(completion_date) else censor_date
        if pd.isna(start_date) or pd.isna(end_date):
            continue
        duration_weeks = max((end_date - start_date).days / 7.0, 0.1)
        row = {
            "pdo_well_id": anchor["pdo_well_id"],
            "rig_no": anchor.get("rig_no", "UNKNOWN"),
            "duration_weeks": duration_weeks,
            "event_observed": int(pd.notna(completion_date)),
            "over_all_progress_percentages": anchor.get("over_all_progress_percentages"),
            "progress_velocity": anchor.get("progress_velocity"),
            "overall_const_10_100": anchor.get("overall_const_10_100"),
            "engg_kpi_after_rig_off_days": anchor.get("engg_kpi_after_rig_off_days"),
            "overall_loc_preparation_10_100": anchor.get("overall_loc_preparation_10_100"),
            "remaining_to_complete": anchor.get("remaining_to_complete"),
            "days_to_target": anchor.get("days_to_target"),
            "plan_curve_gap": anchor.get("plan_curve_gap"),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def _prune_survival_features(
    cox_df: pd.DataFrame,
    feature_cols: list[str],
    variance_floor: float = 1e-6,
    corr_threshold: float = 0.995,
) -> list[str]:
    stable: list[str] = []
    for col in feature_cols:
        series = to_num(cox_df[col])
        if series.notna().sum() < 10:
            continue
        if series.nunique(dropna=True) <= 1:
            continue
        if float(series.std()) <= variance_floor:
            continue
        stable.append(col)

    if len(stable) <= 1:
        return stable

    corr = cox_df[stable].apply(to_num).corr().abs().fillna(0.0)
    keep: list[str] = []
    for col in stable:
        if all(corr.loc[col, kept] < corr_threshold for kept in keep):
            keep.append(col)
    return keep


def _fit_cox_with_fallbacks(CoxPHFitter, cox_df: pd.DataFrame, feature_cols: list[str]):
    if not feature_cols:
        raise ValueError("No stable Cox features available")

    variances = {
        col: float(to_num(cox_df[col]).var()) if to_num(cox_df[col]).notna().any() else 0.0
        for col in feature_cols
    }
    ordered = sorted(feature_cols, key=lambda col: variances.get(col, 0.0), reverse=True)
    feature_sets: list[list[str]] = []
    feature_sets.append(ordered)
    for width in [6, 5, 4, 3, 2, 1]:
        subset = ordered[: min(width, len(ordered))]
        if subset and subset not in feature_sets:
            feature_sets.append(subset)

    last_error: Exception | None = None
    for features in feature_sets:
        fit_frame = cox_df[["duration_weeks", "event_observed"] + features].copy()
        for penalizer in [0.12, 0.25, 0.5, 1.0, 2.0, 5.0]:
            try:
                model = CoxPHFitter(penalizer=penalizer)
                model.fit(
                    fit_frame,
                    duration_col="duration_weeks",
                    event_col="event_observed",
                )
                partial_hazard = model.predict_partial_hazard(cox_df[features])
                return model, features, partial_hazard, penalizer
            except Exception as exc:
                last_error = exc
    if last_error is None:
        raise RuntimeError("Unable to fit Cox model")
    raise last_error


def build_survival_outputs(
    history: pd.DataFrame,
    current: pd.DataFrame,
    output_dir: Path,
) -> dict[str, float]:
    plt = ensure_matplotlib()
    CoxPHFitter, KaplanMeierFitter, concordance_index = ensure_lifelines()
    survival_df = build_survival_training_frame(history)
    if survival_df.empty:
        return {"c_index": float("nan")}

    cox_features = [
        col
        for col in [
            "over_all_progress_percentages",
            "progress_velocity",
            "overall_const_10_100",
            "engg_kpi_after_rig_off_days",
            "overall_loc_preparation_10_100",
            "remaining_to_complete",
            "days_to_target",
            "plan_curve_gap",
        ]
        if col in survival_df.columns
    ]
    cox_df = survival_df[["duration_weeks", "event_observed", "pdo_well_id", "rig_no"] + cox_features].copy()
    for col in cox_features:
        cox_df[col] = to_num(cox_df[col])
        fill_value = float(cox_df[col].median()) if cox_df[col].notna().any() else 0.0
        if not np.isfinite(fill_value):
            fill_value = 0.0
        cox_df[col] = cox_df[col].fillna(fill_value)

    cox_features = _prune_survival_features(cox_df, cox_features)
    cox_model, cox_features_used, partial_hazard, penalizer_used = _fit_cox_with_fallbacks(
        CoxPHFitter,
        cox_df,
        cox_features,
    )
    c_index = float(
        concordance_index(
            cox_df["duration_weeks"],
            -np.asarray(partial_hazard).reshape(-1),
            cox_df["event_observed"],
        )
    )

    # Kaplan-Meier by rig tier
    rig_perf = (
        current.groupby("rig_no")["over_all_progress_percentages"]
        .mean()
        .sort_values(ascending=False)
    )
    top_rigs = set(rig_perf.head(3).index.tolist())
    bottom_rigs = set(rig_perf.tail(3).index.tolist())
    kmf = KaplanMeierFitter()
    fig, ax = plt.subplots(figsize=(10.8, 6.2))
    kmf.fit(cox_df["duration_weeks"], event_observed=cox_df["event_observed"], label="All wells")
    kmf.plot_survival_function(ax=ax, ci_show=True, color="#2563EB")

    if top_rigs:
        top_mask = cox_df["rig_no"].isin(top_rigs)
        if top_mask.any():
            kmf.fit(cox_df.loc[top_mask, "duration_weeks"], event_observed=cox_df.loc[top_mask, "event_observed"], label="Top 3 rigs")
            kmf.plot_survival_function(ax=ax, ci_show=True, color="#16A34A")
    if bottom_rigs:
        bottom_mask = cox_df["rig_no"].isin(bottom_rigs)
        if bottom_mask.any():
            kmf.fit(cox_df.loc[bottom_mask, "duration_weeks"], event_observed=cox_df.loc[bottom_mask, "event_observed"], label="Bottom 3 rigs")
            kmf.plot_survival_function(ax=ax, ci_show=True, color="#DC2626")

    ax.set_title("Kaplan-Meier - probability of well still being incomplete")
    ax.set_xlabel("Weeks observed")
    ax.set_ylabel("Probability well still incomplete")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_dir / "survival_kaplan_meier.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Cox hazard plot
    cox_summary = cox_model.summary.reset_index().rename(columns={"covariate": "feature"})
    if "feature" not in cox_summary.columns:
        cox_summary = cox_summary.rename(columns={cox_summary.columns[0]: "feature"})
    cox_summary = cox_summary.sort_values("exp(coef)")
    fig, ax = plt.subplots(figsize=(10.8, 6.0))
    y = np.arange(len(cox_summary))
    hazard = cox_summary["exp(coef)"].to_numpy(dtype=float)
    lower = cox_summary["exp(coef) lower 95%"].to_numpy(dtype=float)
    upper = cox_summary["exp(coef) upper 95%"].to_numpy(dtype=float)
    ax.errorbar(
        hazard,
        y,
        xerr=[hazard - lower, upper - hazard],
        fmt="o",
        color="#111827",
        ecolor="#6B7280",
        capsize=3,
    )
    ax.axvline(1.0, color="#DC2626", linestyle="--", linewidth=1.1)
    ax.set_yticks(y)
    ax.set_yticklabels([humanize_feature(v) for v in cox_summary["feature"]])
    ax.set_xlabel("Hazard ratio")
    ax.set_title("Cox PH hazard ratios")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_dir / "survival_cox_hazard.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Current survival predictions
    current_cov = current[["pdo_well_id", "well_name_after_spud", "rig_no"] + cox_features_used].copy()
    for col in cox_features_used:
        current_cov[col] = to_num(current_cov[col]).fillna(float(cox_df[col].median()))
    times = np.array([4, 8, 12, 16, 20, 24, 26], dtype=float)
    survival_fn = cox_model.predict_survival_function(current_cov[cox_features_used], times=times)
    survival_predictions = current_cov[["pdo_well_id", "well_name_after_spud", "rig_no"]].copy()
    for week in times:
        survival_predictions[f"incomplete_prob_w{int(week)}"] = survival_fn.loc[week].to_numpy(dtype=float)
        survival_predictions[f"completion_prob_w{int(week)}"] = 1.0 - survival_fn.loc[week].to_numpy(dtype=float)
    survival_predictions.to_csv(output_dir / "survival_predictions.csv", index=False)
    return {
        "c_index": c_index,
        "cox_features_used": cox_features_used,
        "cox_penalizer": float(penalizer_used),
    }


def save_outputs(
    output_dir: Path,
    risk_scores: pd.DataFrame,
    priority: pd.DataFrame,
    feature_importance: pd.DataFrame,
    artifacts: ModelArtifacts,
    history: pd.DataFrame,
    current: pd.DataFrame,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    def date_only(series: pd.Series) -> pd.Series:
        return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d")

    risk_scores_out = risk_scores.copy()
    priority_out = priority.copy()

    for frame in [risk_scores_out, priority_out]:
        for col in [
            "predicted_completion_date",
            "completion_date_early",
            "completion_date_late",
        ]:
            frame[col] = date_only(frame[col])

    risk_scores_out.to_csv(output_dir / "risk_scores.csv", index=False)
    priority_out.to_csv(output_dir / "priority_wells_final.csv", index=False)
    feature_importance.to_csv(output_dir / "feature_importance.csv", index=False)
    build_leaderboard_frame(artifacts).to_csv(output_dir / "ag_leaderboard.csv", index=False)

    build_feature_importance_chart(feature_importance, output_dir / "feature_importance.png")
    build_progress_diagnostics_chart(artifacts, output_dir / "ag_diagnostics.png")
    build_completion_forecast_chart(
        risk_scores_out,
        pd.to_datetime(current["snapshot_date"], errors="coerce").max(),
        output_dir / "completion_forecast.png",
    )
    build_rig_performance_chart(risk_scores_out, output_dir / "rig_performance.png")

    # Real SHAP diagnostics from the trained CatBoost ensemble members.
    progress_shap_member = next(
        (member for member in artifacts.progress_models if member.name.startswith("CatBoost")),
        None,
    )
    if progress_shap_member is not None and not artifacts.progress_shap_frame.empty:
        progress_shap_values, _ = get_catboost_shap(
            progress_shap_member,
            artifacts.progress_shap_frame,
            artifacts.cat_features,
        )
        build_shap_beeswarm_chart(
            progress_shap_values,
            artifacts.progress_shap_frame,
            output_dir / "shap_beeswarm.png",
            "SHAP beeswarm - progress model",
        )
        build_shap_importance_chart(
            progress_shap_values,
            artifacts.progress_shap_frame,
            output_dir / "shap_importance.png",
            "SHAP importance - progress model",
        )

    risk_shap_member = next(
        (member for member in artifacts.risk_models if member.name.startswith("CatBoost")),
        None,
    )
    if risk_shap_member is not None and not artifacts.risk_shap_frame.empty:
        risk_shap_values, _ = get_catboost_shap(
            risk_shap_member,
            artifacts.risk_shap_frame,
            artifacts.cat_features,
        )
        build_signed_shap_chart(
            risk_shap_values,
            artifacts.risk_shap_frame,
            output_dir / "shap_risk_drivers.png",
            "Average SHAP direction - risk model",
        )

    survival_metrics = build_survival_outputs(history, current, output_dir)

    metrics = {
        "best_model": artifacts.best_model_name,
        "rmse": artifacts.progress_metrics["rmse"],
        "mae": artifacts.progress_metrics["mae"],
        "r2": artifacts.progress_metrics["r2"],
        "mape_valid": artifacts.progress_metrics["mape_valid"],
        "c_index": survival_metrics.get("c_index"),
        "auc": artifacts.risk_metrics["auc"],
        "brier": artifacts.risk_metrics["brier"],
    }
    (output_dir / "ag_metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    manifest = {
        "generated_files": [
            "ag_metrics.json",
            "risk_scores.csv",
            "feature_importance.csv",
            "priority_wells_final.csv",
            "training_manifest.json",
            "ag_leaderboard.csv",
            "survival_predictions.csv",
            "ag_diagnostics.png",
            "feature_importance.png",
            "completion_forecast.png",
            "rig_performance.png",
            "shap_beeswarm.png",
            "shap_importance.png",
            "shap_risk_drivers.png",
            "survival_kaplan_meier.png",
            "survival_cox_hazard.png",
        ],
        "training_rows": int(len(history)),
        "deduped_well_week_rows": int(
            history[["pdo_well_id", "snapshot_date"]].drop_duplicates().shape[0]
        ),
        "unique_wells": int(history["pdo_well_id"].nunique()),
        "tier_thresholds": artifacts.tier_thresholds,
        "risk_metrics": artifacts.risk_metrics,
        "survival_metrics": survival_metrics,
        "best_model": artifacts.best_model_name,
        "progress_ensemble_members": [
            {"name": member.name, "backend": member.backend, "weight": member.weight}
            for member in artifacts.progress_models
        ],
        "weeks_ensemble_members": [
            {"name": member.name, "backend": member.backend, "weight": member.weight}
            for member in artifacts.weeks_models
        ],
        "risk_ensemble_members": [
            {"name": member.name, "backend": member.backend, "weight": member.weight}
            for member in artifacts.risk_models
        ],
    }
    (output_dir / "training_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the corrected Decision Studio Kaggle output package."
    )
    parser.add_argument(
        "--input-dir",
        default="",
        help="Directory containing the exported CSV inputs. If omitted, the script searches local and /kaggle/input paths.",
    )
    parser.add_argument(
        "--output-dir",
        default="/kaggle/working/wmr_results",
        help="Directory where the Decision Studio output package should be written.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve() if args.input_dir else None
    output_dir = Path(args.output_dir).resolve()

    wmr_full, wmr_latest, plan_snapshot, report_gb, sap = load_inputs(input_dir)
    plan_latest = prepare_plan_snapshot(plan_snapshot)
    report_map = prepare_report_gb(report_gb)
    sap_agg = prepare_sap(sap)

    history = build_history_frame(wmr_full, plan_latest, report_map, sap_agg)
    history = attach_future_targets(history)
    current = build_current_frame(wmr_latest, history, plan_latest, report_map, sap_agg)

    artifacts = train_models(history)
    feature_importance = build_feature_importance(history, artifacts)
    risk_scores, priority = score_current(current, artifacts)
    save_outputs(output_dir, risk_scores, priority, feature_importance, artifacts, history, current)

    print("[saved] Decision Studio package written to", output_dir)
    print("[metrics]", json.dumps(artifacts.progress_metrics, indent=2))
    print("[risk_metrics]", json.dumps(artifacts.risk_metrics, indent=2))
    print("[thresholds]", json.dumps(artifacts.tier_thresholds, indent=2))


if __name__ == "__main__":
    main()
