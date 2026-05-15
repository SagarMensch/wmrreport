# Bashira Intelligence — Predictive Modeling: Complete Technical Documentation

> Al Tasnim Enterprises LLC | Well Construction Intelligence Platform | Version 1.0

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Data Sources & Feature Engineering](#3-data-sources--feature-engineering)
4. [Model 1: AutoGluon Tabular Ensemble (GPU)](#4-model-1-autogluon-tabular-ensemble)
5. [Model 2: LightGBM Calibrated Delay-Risk Classifier (CPU)](#5-model-2-lightgbm-calibrated-delay-risk-classifier)
6. [Model 3: Random Survival Forest (Completion Timeline)](#6-model-3-random-survival-forest)
7. [Model 4: Kaplan-Meier & Cox Proportional Hazards](#7-model-4-kaplan-meier--cox-proportional-hazards)
8. [Model 5: StatsForecast AutoARIMA (Time-Series)](#8-model-5-statsforecast-autoarima)
9. [Model 6: Google TimeSFM Foundation Model](#9-model-6-google-timesfm-foundation-model)
10. [Model 7: LSTM Fallback Forecaster](#10-model-7-lstm-fallback-forecaster)
11. [Model 8: S-Learner Causal Meta-Estimator (CATE)](#11-model-8-s-learner-causal-meta-estimator)
12. [Model 9: Bayesian Counterfactual Engine (Stan/Laplace)](#12-model-9-bayesian-counterfactual-engine)
13. [Model 10: Ensemble Stacker with Conformal Prediction](#13-model-10-ensemble-stacker-with-conformal-prediction)
14. [Composite Risk Scoring Engine](#14-composite-risk-scoring-engine)
15. [SHAP Explainability Layer](#15-shap-explainability-layer)
16. [Anomaly Detection & Tier Tracking](#16-anomaly-detection--tier-tracking)
17. [Causal Command Service (Scenario Simulator)](#17-causal-command-service)
18. [Production API Endpoints](#18-production-api-endpoints)
19. [Kaggle GPU Pipelines](#19-kaggle-gpu-pipelines)
20. [Model Performance Summary](#20-model-performance-summary)
21. [File Reference Map](#21-file-reference-map)

---

## 1. Executive Summary

Bashira Intelligence is an AI-powered predictive analytics platform for Al Tasnim's well construction operations. It uses **10 distinct predictive models** across GPU and CPU runtimes, combined via a meta-ensemble with conformal prediction intervals, to deliver:

- **4-week ahead progress forecasting** per well
- **Delay risk classification** with calibrated probabilities
- **Completion date prediction** with confidence intervals (survival analysis)
- **Causal counterfactual analysis** (what-if rig reassignment, material expedite, decongestion)
- **Portfolio-level risk ranking** (0–100 scale, 4 risk tiers)
- **Explainability** via SHAP feature importance per prediction

All models are trained on real data from `AppMasterDB` (SQL Server). No simulation or hardcoding is used anywhere in the pipeline.

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     KAGGLE GPU PIPELINE (Monthly)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ AutoGluon   │  │ Cox PH +     │  │ TimeSFM /   │  │ SHAP     │ │
│  │ Tabular     │  │ Random       │  │ LSTM        │  │ Tree/    │ │
│  │ Ensemble    │  │ Survival     │  │ Forecast    │  │ Kernel   │ │
│  │ (GPU, T4)   │  │ Forest       │  │ (GPU)       │  │ Explainer│ │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └────┬─────┘ │
│         │                │                  │               │        │
│         v                v                  v               v        │
│  wmr_results/ artifacts (CSV, JSON, PNG)                            │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               v
┌──────────────────────────────────────────────────────────────────────┐
│                     CPU PRODUCTION MICROSERVICES                     │
│                                                                      │
│  Port 8050: cpu_ml_orchestrator.py                                   │
│  ├─ LightGBM CalibratedClassifier (delay risk)                      │
│  ├─ LightGBM Quantile Regressors (p10/p50/p90 momentum)             │
│  ├─ StatsForecast AutoARIMA (per-well trajectory)                   │
│  ├─ S-Learner CATE (LightGBM causal meta-estimator)                │
│  └─ SHAP TreeExplainer (risk driver attribution)                    │
│                                                                      │
│  Port 8000+: predict_service.py (FastAPI)                            │
│  ├─ FeatureEngine (58-feature AutoGluon replication)                │
│  ├─ Random Survival Forest (on-CPU retrain from CSV)                │
│  └─ Risk Scoring (exact Kaggle formula)                             │
│                                                                      │
│  Port 8005: causal_command_service.py                                │
│  ├─ StanCounterfactualService (CmdStan MCMC / Laplace)             │
│  ├─ Scenario Simulator (peer recovery, rig swap, material, decongest)│
│  └─ Causal Workspace Builder (cross-table SQL joins)                │
│                                                                      │
│  EnsembleStacker (singleton, shared across services)                 │
│  ├─ Isotonic regression calibration                                 │
│  ├─ Conformal prediction intervals                                  │
│  ├─ Online weight adjustment by accuracy                            │
│  └─ Model disagreement detection                                   │
│                                                                      │
│  AnomalyTracker (SQLite / SQL Server / memory)                       │
│  └─ Risk tier transition detection & persistence                    │
│                                                                      │
│  ForecastEngine (forecast_engine.py)                                 │
│  ├─ Well lifecycle Gantt / milestone tracking                       │
│  ├─ Linear trend 4-week forecast with CI                             │
│  ├─ Hybrid risk scoring (schedule variance + overdue + stagnation)  │
│  └─ Portfolio risk map aggregation                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Sources & Feature Engineering

### 3.1 Primary Data Tables

| Table | Rows | Purpose |
|---|---|---|
| `WMR_Full` | ~18,969 | Historical weekly progress snapshots (training) |
| `WellMonitoringReport_Latest` | ~169 | Current week snapshot (scoring) |
| `Job_Progress_Report_GB` | Derived | Plan vs actual percentages per well/week |
| `Job_Progress_PlanSnapshot` | ~439 | Weekly plan fractions W1–W5 per well |
| `Revenue` | ~21,566 | Planned and actual purpose value (OMR) |
| `PH_PRODUCTIVITY_WEEKLY_REPORT` | ~510 | Crew supervisor productivity scores |
| `SAP_DRILLING_SEQUENCE` | ~6,159 | Rig assignments, move days, field data |

### 3.2 Feature Engineering Pipeline (58 Features)

The feature engineering replicates the exact Kaggle pipeline and is implemented in `feature_engine.py`. Features are grouped into:

**Calendar Features (5)**
- `days_since_start` — days from actual_start_date to ref date (2024-01-01)
- `start_month` — month of actual start
- `start_quarter` — quarter of actual start
- `rig_duration_days` — days between rig-on and rig-off
- `days_to_rig_off_exp` — days from current week to expected rig-off

**Geographic Features (3)**
- `dist_from_centroid` — Euclidean distance from northing/easting median
- `geo_quadrant` — quadrant code (0–3) based on northing/easting vs median
- `geo_angle` — atan2 angle from centroid

**Location Preparation Composite (1)**
- `loc_prep_composite` — weighted sum of 12 sub-phase scores:
  - access_road_5 (0.05), earth_work_60 (0.06), cellar_20 (0.02),
  - beam_pump_base (0.05), earthing_1 (0.01), water_2 (0.02),
  - hdpe_liner (0.04), sleeper_pre_cast (0.015), cs_pipe_welding (0.10),
  - pe_fussion_pull_20 (0.02), final_hydro_t_3 (0.03), mechani_60 (0.06)

**Time-Series Lag Features (8)**
- `progress_lag1`, `progress_lag2`, `progress_lag4` — shifted progress values
- `progress_velocity_1w` — 1-week velocity (current − lag1)
- `progress_velocity_2w` — 2-week velocity (current − lag2)
- `progress_accel` — acceleration (velocity1 − velocity1_prev)
- `progress_rolling3w` — 3-week rolling mean
- `remaining_to_complete` — 1.0 − current_progress

**Momentum Score (1)**
- `momentum_score` = 0.5 × velocity_1w + 0.3 × velocity_2w + 0.2 × accel

**Target Encodings (10)**
- `rig_no_te`, `rig_no_cnt`, `project_id_te`, `project_id_cnt`,
- `project_code_te`, `project_code_cnt`, `well_type_te`, `well_type_cnt`,
- `completion_type_rig_fbu_or_rsr_hoist_te`, `completion_type_rig_fbu_or_rsr_hoist_cnt`

**Weekly History Aggregates (2)**
- `week_hist_mean`, `week_hist_std` — aggregate progress stats per week

**Label Encodings (8)**
- `rig_no_enc`, `well_type_enc`, `project_code_enc`, `project_name_enc`,
- `fl_dia_enc`, `completion_type_..._enc`, `flow_line_status_enc`,
- `physical_tie_in_port_enc`, `location_preparation_status_enc`

**Raw Numerics (20+)**
- northing, easting, scr_no, ohl_length_meter, ohl_progress,
- engg_kpi_after_rig-off_days, and 12 location-prep sub-scores

### 3.3 Zero-Leakage Design

- Entity key = `well_name_after_spud` + `__` + `project_id`
- Forecast target = `target_lead_4w` = progress shifted 4 weeks forward
- Train/test split is temporal — no future data leaks into training features
- Missing values filled with training medians (not test-set statistics)

---

## 4. Model 1: AutoGluon Tabular Ensemble (GPU)

**File:** `wmr_advanced_pipeline.ipynb` (Cell 005), `ATNM_Decision_Studio_Kaggle_GPU.ipynb` (Block 5)

### Configuration
- **Preset:** `best_quality`
- **Problem type:** Regression (target: `target_lead_4w`)
- **Eval metric:** RMSE
- **Bagging:** 8 folds × 2 sets
- **Stacking:** 2 levels
- **Refit full:** True
- **GPU:** Enabled (T4 / P100)

### Base Models Trained (per hyperparameter config)

| Model Family | Variants | GPU Acceleration |
|---|---|---|
| LightGBM (`GBM`) | 2 configs: (500 rounds, lr=0.05, leaves=63) + (1000 rounds, lr=0.02, leaves=127, extra_trees) | `device=gpu` |
| XGBoost (`XGB`) | 2 configs: (500 est, lr=0.05, depth=6) + (1000 est, lr=0.02, depth=8) | `tree_method=gpu_hist` |
| CatBoost (`CAT`) | 2 configs: (700 iter, lr=0.05, depth=8) + (1200 iter, lr=0.02, depth=10, L2=5) | `task_type=GPU` |
| Random Forest (`RF`) | 1 config: 500 estimators, sqrt max_features, min_samples_leaf=3 | CPU |
| Extra Trees (`XT`) | 1 config | CPU |
| Neural Network (`NN_TORCH`) | AutoGluon default MLP | GPU |
| Weighted Ensemble (`ENS_MODELS`) | Stacking over all above | Automatic |

### Three-Target Architecture (ATNM Decision Studio)

The Decision Studio notebook trains **3 separate AutoGluon predictors**:

| Predictor | Target | Problem Type | Eval Metric | Time Limit |
|---|---|---|---|---|
| Model A: Delay Risk | `delay_risk` (0/1, engg_kpi > 2 days) | Binary classification | `roc_auc` | 3 hours |
| Model B: Progress % | `over_all_progress_percentages` (0–1) | Regression | `r2` | 3 hours |
| Model C: 5-Week Completion | `will_complete_5w` (0/1, projected ≥ 95%) | Binary classification | `roc_auc` | 2 hours |

### Performance

From `ag_metrics.json`:
- **Best model:** `RandomForest_BAG_L3`
- **R²:** 0.9873
- **RMSE:** 0.0410
- **MAE:** 0.0173
- **MAPE:** 7.09%

### Production Loading
- Model artifacts saved to `wmr_results/ag_model/`
- Loaded at runtime via `TabularPredictor.load()` in `feature_engine.py:156`
- Used for `predict_progress()` and `predict_well()` endpoints

---

## 5. Model 2: LightGBM Calibrated Delay-Risk Classifier (CPU)

**File:** `cpu_ml_orchestrator.py` (lines 246–337)

### Purpose
Binary classification: will a well miss its expected rig-off date? Trained on rows where `days_to_expected_rig_off` is within ±28/−14 days of target.

### Architecture
```
CalibratedClassifierCV(
    estimator=LGBMClassifier(
        n_estimators=260, learning_rate=0.04, max_depth=6,
        min_child_samples=25, subsample=0.9, colsample_bytree=0.85
    ),
    method="sigmoid",    ← Platt scaling calibration
    cv=3                  ← 3-fold cross-validated calibration
)
```

### Features (10)
`progress`, `recent_momentum_3w`, `rig_efficiency_weekly`, `cluster_density`, `material_lead_days`, `has_engineering_started`, `has_location_started`, `is_rig_on`, `days_to_expected_rig_off`, `schedule_pressure`

### Metrics
- **AUC:** Tracked via `roc_auc_score` on held-out test set
- **Brier Score:** Tracked via `brier_score_loss`
- Stored in `_risk_model_metrics` dict

### SHAP Explainer
A separate `LGBMClassifier` (same hyperparams) is trained on the full risk panel for SHAP `TreeExplainer`, producing per-feature risk driver attribution.

### Heuristic Fallback
When calibration training data < 30 rows, the system falls back to an engineered-feature heuristic that computes risk from 6 weighted components:
- `(1 - progress) × 42` → progress risk
- `clip(0.04 - momentum, 0) × 260` → velocity risk
- `rig_penalty × 180` → rig efficiency risk
- `schedule_pressure × 22` → schedule pressure
- `overdue_pressure × 18` → overdue risk
- `material_pressure × 6` → material readiness

---

## 6. Model 3: Random Survival Forest (Completion Timeline)

**File:** `wmr_advanced_pipeline.ipynb` (Cell 007), `feature_engine.py` (lines 215–311)

### Purpose
Predict WHEN each well will reach 100% completion, with confidence intervals.

### Architecture (Kaggle)
```python
RandomSurvivalForest(
    n_estimators=200, random_state=42, n_jobs=-1
)
```
- Event = well reached 95%+ progress
- Duration = weeks observed
- Features: last_progress, progress_velocity, remaining, loc_prep, const_progress, engg_kpi

### Architecture (CPU Production — feature_engine.py)
```python
RandomSurvivalForest(
    n_estimators=300, min_samples_split=5,
    min_samples_leaf=3, max_features="sqrt",
    n_jobs=-1, random_state=42
)
```
- Trained on-CPU at startup from `risk_scores.csv` (~3 seconds)
- Pickled for faster subsequent loads (`rsf_model.pkl`)

### Output
- **Median completion week** — 50% survival probability point
- **Early completion week** — 75% survival probability (optimistic)
- **Late completion week** — 25% survival probability (pessimistic)
- Converted to calendar dates from current date
- **C-index:** 0.993 (on training data)

### Kaplan-Meier Curves
The Kaggle pipeline also fits `KaplanMeierFitter` and `CoxPHFitter` from `lifelines` for visual survival curves and hazard ratio interpretation.

---

## 7. Model 4: Kaplan-Meier & Cox Proportional Hazards

**File:** `wmr_advanced_pipeline.ipynb` (Cell 007)

### Kaplan-Meier Estimator
- Non-parametric survival curve estimation
- Stratified by well type (showing different survival patterns)
- Produces `survival_kaplan_meier.png`

### Cox Proportional Hazards Model
- Semi-parametric regression for hazard ratios
- Features: progress_velocity, remaining, loc_prep, const_progress, engg_kpi
- Produces `survival_cox_hazard.png`
- C-index reported alongside RSF

---

## 8. Model 5: StatsForecast AutoARIMA (Time-Series)

**File:** `cpu_ml_orchestrator.py` (line 27–28 import)

### Library
`statsforecast` by Nixtla — state-of-the-art CPU time-series forecasting.

### Model
`AutoARIMA` — automatically selects optimal (p,d,q)(P,D,Q) parameters via AIC/BIC.

### Usage
Per-well weekly progress time-series → 4-week ahead forecast with prediction intervals. Called via the `/ml/forecast/{well_id}` endpoint. When available, the forecast replaces the heuristic linear trend in `forecast_engine.py`.

---

## 9. Model 6: Google TimeSFM Foundation Model

**File:** `ATNM_Decision_Studio_Kaggle_GPU.ipynb` (Block 7)

### Architecture
```python
timesfm.TimesFm(
    context_len=32,        # 32-week lookback window
    horizon_len=5,         # 5-week forecast horizon
    input_patch_len=32,
    output_patch_len=128,
    num_layers=20,
    model_dims=1280,
    backend='gpu'
)
```
- Pre-trained checkpoint: `google/timesfm-1.0-200m`
- **Zero-shot** — no fine-tuning on well data required
- Produces point forecasts + quantile forecasts (p10, p90) per well

### Output per well
- `forecast_w1` through `forecast_w5` — predicted progress %
- `ci_low_w5` / `ci_high_w5` — 80% confidence interval (p10/p90)
- `completion_prob_tsf` — probability of reaching ≥95% in forecast window

---

## 10. Model 7: LSTM Fallback Forecaster

**File:** `ATNM_Decision_Studio_Kaggle_GPU.ipynb` (Block 7, fallback path)

### When Used
When `timesfm` package is unavailable (no GPU or install failure).

### Architecture
```python
class WellLSTM(nn.Module):
    LSTM(input=1, hidden=64, layers=2, dropout=0.2, batch_first=True)
    FC(hidden=64 → output=5)   # 5-week horizon
```

### Training
- **Window:** 8 weeks input → 5 weeks output
- **Optimizer:** Adam, lr=1e-3
- **Loss:** MSELoss
- **Epochs:** 50
- **Batch size:** 256
- **Device:** CUDA if available, else CPU
- Confidence interval: heuristic ±10% around prediction

---

## 11. Model 8: S-Learner Causal Meta-Estimator (CATE)

**File:** `cpu_ml_orchestrator.py` (lines 391–450)

### Purpose
Estimate the **Conditional Average Treatment Effect** (CATE) of rig assignment on well progress momentum. Answers: "What would this well's progress be if we assigned a different rig?"

### Architecture
```python
LGBMRegressor(
    n_estimators=150, learning_rate=0.03, max_depth=6,
    min_child_samples=15, subsample=0.85, colsample_bytree=0.85
)
```

### Methodology
**S-Learner (single-model) approach:**
1. Train one model with treatment (rig_encoded) as a feature alongside confounders
2. Factual prediction: predict with current rig encoding
3. Counterfactual: predict with each alternative rig encoding
4. CATE = counterfactual prediction − factual prediction

### Confounders (X)
`over_all_progress_percentages`, `cluster_density`, `material_lead_days`, `rig_encoded`, `loc_encoded`

### Treatment (T)
`rig_encoded` — LabelEncoder-transformed rig identifier

### Outcome (Y)
`causal_momentum` — week-over-week progress change (next_week − this_week)

### Output per well
- Factual momentum with current rig
- Per-rig counterfactual momentum
- CATE per rig (effect of switching)
- Best alternative rig recommendation
- Top 10 rig alternatives ranked by CATE

### API Endpoint
`GET /ml/causal/cate/{well_id}`

---

## 12. Model 9: Bayesian Counterfactual Engine (Stan/Laplace)

**File:** `causal_stan_service.py` (928 lines)

### Purpose
Institutional-grade Bayesian hierarchical model for delay driver attribution and counterfactual analysis with full posterior uncertainty quantification.

### Priority Order
1. **CmdStan MCMC** (4 chains × 500 warmup × 500 sampling = 2000 posterior draws)
2. **Laplace Approximation** (Hessian-based uncertainty when CmdStan unavailable)

### Stan Model: Horseshoe Hierarchical Student-t
- **Location:** `stan_models/causal_effects.stan`
- **Features (K):** Up to 21 (current_progress, loc_prep, const_progress, comm_progress, engg_kpi_days, weekly_velocity, stalled_flag, regressed_flag, monthly gaps, plan fractions, overdue tasks, PH productivity, move days, etc.)
- **Group effects:** rig_no (R), cluster (C), well_type (W), progress_band (B)
- **Horseshoe prior** for sparse variable selection (kappa inclusion probabilities)

### CmdStan Path
```python
fit = model.sample(
    data=stan_data, chains=4, parallel_chains=4,
    iter_warmup=500, iter_sampling=500, seed=42
)
```

### MCMC Diagnostics
- **R-hat** — convergence (target < 1.05)
- **ESS (N_Eff)** — effective sample size
- **Divergences** — Hamiltonian Monte Carlo health
- **LOO-CV** via ArviZ — leave-one-out cross-validation for model comparison
  - elpd_loo, se, p_loo, warning flag

### Laplace Fallback
When CmdStan is unavailable (no C++ toolchain on Windows):
1. Standardize features
2. Optimize regularization λ via Generalized Cross-Validation (GCV) over 20 grid points
3. Compute MAP estimate: β = (X'X + λI)⁻¹X'y
4. Hessian-based posterior variance: Σ = σ²(X'X + λI)⁻¹
5. Horseshoe-like inclusion probability: κ = sigmoid(|β|/SE − 2)
6. James-Stein shrinkage for group effects

### Output
- Per-feature β with 80% credible intervals
- Inclusion probabilities (variable selection)
- Group effects (rig, cluster, well_type, progress_band) with uncertainty
- Counterfactual scenario aggregation
- Root cause decomposition per well

### Auto-Install
CmdStan auto-installs on first use (~500MB) if `cmdstanpy` is available.

---

## 13. Model 10: Ensemble Stacker with Conformal Prediction

**File:** `ensemble_stacker.py` (479 lines)

### Purpose
Meta-learner that combines all base model predictions into a single calibrated prediction with distribution-free uncertainty intervals.

### Level 0 — Base Models

| Model | Weight | Signal |
|---|---|---|
| LightGBM Calibrated Delay Risk | 0.35 | Risk probability (%) |
| StatsForecast AutoARIMA | 0.20 | Implied risk from trajectory gap |
| Stan Bayesian Posterior | 0.25 | Top driver impact normalized to [0,1] |
| S-Learner CATE | 0.20 | Momentum risk (1 − momentum/3%) |

### Level 1 — Meta-Learner

**Isotonic Regression Calibration**
- `IsotonicRegression(out_of_bounds="clip")`
- Calibrated from historical prediction vs actual delay outcomes
- Monotonically maps raw stacked risk → calibrated risk

**Conformal Prediction (Split Conformal)**
- Nonconformity scores = |y_true − y_pred| on calibration split (last 30%)
- Prediction interval: ŷ ± q_hat, where q_hat = quantile of nonconformity scores at (1−α) level
- Guaranteed marginal coverage: P(Y ∈ interval) ≥ 1−α
- Produces 90% coverage intervals by default

**Model Agreement Score**
- Agreement = 1 − coefficient_of_variation(risk_estimates)
- When agreement < 50%, high disagreement flag is raised

**Online Weight Update**
- Weights adjusted inversely proportional to per-model mean absolute error
- Triggered when ≥10 outcome observations are available
- Rolling window of last 500 predictions

### Risk Tier Mapping
| Stacked Risk | Tier |
|---|---|
| ≥ 75% | CRITICAL |
| ≥ 55% | HIGH_RISK |
| ≥ 35% | WATCH |
| < 35% | HEALTHY |

---

## 14. Composite Risk Scoring Engine

**File:** `wmr_advanced_pipeline.ipynb` (Cell 008), `feature_engine.py` (lines 564–622), `forecast_engine.py` (lines 932–1200)

### Kaggle Formula (Cell 008)
```
risk_score = 0.35 × risk_prog + 0.25 × risk_vel + 0.20 × risk_schedule + 0.20 × risk_gap
```

Where:
- `risk_prog` = 1 − progress (low progress = high risk)
- `risk_vel` = 1 − min(velocity, 0.1)/0.1 (slow velocity = high risk)
- `risk_schedule` = 1 − (days_to_exp + 100)/200 (overdue = high risk)
- `risk_gap` = max(expected_linear − actual, 0) (behind schedule = risk)

### Hybrid Risk Scoring (forecast_engine.py)
6-component risk decomposition:

| Component | Weight | Trigger |
|---|---|---|
| Schedule Variance Risk | up to 35 | Progress behind expected linear curve |
| Overdue Deadline Risk | up to 40 | Expected rig-off date passed |
| Stagnation Risk | 20 | Velocity ≤ 0 and progress < 90% |
| Readiness Risk | variable | Engineering/location not started |
| Drilling Execution Risk | variable | Rig-on but no rig-off recorded |
| Governance Risk | variable | MOC not raised/approved |

Plus ML-injected risk from the CPU ML service (delay_risk probability scaled to 0–100).

---

## 15. SHAP Explainability Layer

### Usage Points

| Context | Explainer | File |
|---|---|---|
| AutoGluon best model | `TreeExplainer` (fallback: `KernelExplainer`) | `wmr_advanced_pipeline.ipynb` (Cell 006) |
| LightGBM delay-risk | `TreeExplainer` | `cpu_ml_orchestrator.py` (line 331) |
| AutoGluon progress regressor | `KernelExplainer` (200 sample bg) | `ATNM_Decision_Studio_Kaggle_GPU.ipynb` (Block 8) |

### Outputs
- **SHAP Feature Importance** (bar chart) — mean |SHAP| per feature
- **SHAP Beeswarm** — shows direction and magnitude of each feature's impact
- **SHAP Risk Drivers** (per well) — top 5 features driving that well's prediction
- **SHAP Values CSV** — raw values for all test rows
- **Feature Importance CSV** — aggregated ranking

---

## 16. Anomaly Detection & Tier Tracking

**File:** `anomaly_tracker.py` (434 lines)

### Purpose
Track risk tier transitions across nightly evaluations and persist anomalies.

### Backends (priority order)
1. **SQL Server** — tables `bashira_anomalies` and `bashira_well_state` in `dbo` schema
2. **SQLite** — local `anomalies.db` (when allowed via env var)
3. **In-memory** — dict-based fallback

### Tier Transition Detection
On each `sync_well_state(well, score, tier)` call:
1. Look up current tier in well_state table
2. If tier changed → record anomaly with severity (P1/P2/P3)
3. Update well_state with new tier and score

### Severity Levels
| Jump | Severity |
|---|---|
| ≥ 2 tier jump (e.g., HEALTHY → CRITICAL) | P1 |
| 1 tier jump (e.g., WATCH → HIGH_RISK) | P2 |
| Improvement (tier decreased) | P3 |

---

## 17. Causal Command Service (Scenario Simulator)

**File:** `causal_command_service.py` (2316 lines)

### Purpose
Build cross-system dataset from live SQL, combine fast CPU layer + deep Bayesian layer for "what-if" analysis.

### Scenario Actions

| Action ID | Label | What It Simulates |
|---|---|---|
| `peer_recovery` | Recover to Peer Execution Pace | Lift momentum to peer median or top quartile |
| `rig_reassignment` | Reassign Higher-Efficiency Rig | Swap to a rig with better historical momentum |
| `material_expedite` | Expedite Material Readiness | Reduce material lead time by 7/14/21 days |
| `decongest_workfront` | Decongest Parallel Workfronts | Reduce cluster density to peer-normal level |

### Each Scenario Returns
- Factual completion date (current trajectory)
- Counterfactual completion date (with intervention)
- Days saved (expected, conservative, upside)
- Support cases (comparable historical wells)
- Assumption note

### Governed Scenario Engine
- Momentum prediction: `LightGBMRegressor` (base) + quantile models (p10, p90)
- Empirical blending: 70% model + 30% peer benchmark when ≥12 comparable cases
- Recent anchor blending: 75% model + 25% recent momentum

---

## 18. Production API Endpoints

### predict_service.py (Port 8000+)

| Endpoint | Method | Description |
|---|---|---|
| `/predict/single` | POST | Real-time single well forecast (AutoGluon + RSF + risk) |
| `/predict/refresh` | POST | Nightly batch evaluation + anomaly detection |
| `/predict/full` | POST | Full pipeline retrain trigger (queues GPU job) |
| `/predict/anomalies` | GET | Live anomaly feed (tier transitions) |
| `/predict/portfolio` | GET | Portfolio-level risk summary |
| `/predict/model-info` | GET | Model metadata, artifacts, training metrics |

### cpu_ml_orchestrator.py (Port 8050)

| Endpoint | Method | Description |
|---|---|---|
| `/ml/forecast/{well_id}` | GET | Per-well forecast (ARIMA + LightGBM risk + insights) |
| `/ml/causal/cate/{well_id}` | GET | S-Learner CATE per well |
| `/ml/simulate` | POST | Run scenario simulation |
| `/ml/portfolio/live-risk` | GET | Portfolio-wide risk scoring |
| `/api/health` | GET | Service health check |

### causal_command_service.py (Port 8005)

| Endpoint | Method | Description |
|---|---|---|
| `/api/causal/command` | GET | Full causal workspace (CPU + Bayesian layers) |

---

## 19. Kaggle GPU Pipelines

### Pipeline 1: wmr_advanced_pipeline.ipynb
**Runtime:** ~8 hours on T4 GPU

| Cell | Task | Time |
|---|---|---|
| 000–003 | Install, imports, load data | ~5 min |
| 004 | Feature engineering (62 features) | ~2 min |
| 005 | AutoGluon best_quality (8-fold bag, 2-level stack) | ~4 hr |
| 006 | SHAP explainability | ~30 min |
| 007 | Survival analysis (KM + Cox + RSF) | ~30 min |
| 008 | Risk scoring (0–100) | ~1 min |
| 009 | 12 visualization charts | ~5 min |
| 010 | Business output (priority CSV + executive summary) | ~1 min |

### Pipeline 2: ATNM_Decision_Studio_Kaggle_GPU.ipynb
**Runtime:** ~22 hours on T4 GPU (30-hour budget)

| Block | Task | Time |
|---|---|---|
| 1 | Install & imports | ~10 min |
| 2 | Load & validate 6 CSVs | ~5 min |
| 3 | Feature engineering + joins | ~15 min |
| 4 | Portfolio metrics (rule-based) | ~1 min |
| 5 | 3× AutoGluon models (delay, progress, completion) | ~8 hr |
| 6 | Random Survival Forest + Cox | ~1 hr |
| 7 | TimeSFM / LSTM forecast | ~4 hr |
| 8 | SHAP explainability | ~2 hr |
| 9 | Rig performance (rule-based) | ~1 min |
| 10 | Merge all results | ~2 min |
| 11 | 8 Plotly charts | ~5 min |
| 12 | HTML report render (Jinja2) | ~1 min |

---

## 20. Model Performance Summary

| Model | Metric | Value | Source |
|---|---|---|---|
| AutoGluon Tabular (Regression) | R² | 0.9873 | `ag_metrics.json` |
| AutoGluon Tabular (Regression) | RMSE | 0.0410 | `ag_metrics.json` |
| AutoGluon Tabular (Regression) | MAE | 0.0173 | `ag_metrics.json` |
| Random Survival Forest (CPU) | C-index | 0.993 | `feature_engine.py` training log |
| LightGBM Calibrated Delay Risk | AUC | varies by data | `cpu_ml_orchestrator.py` |
| LightGBM Calibrated Delay Risk | Brier Score | varies by data | `cpu_ml_orchestrator.py` |
| Stan Bayesian MCMC | R-hat | <1.05 target | `causal_stan_service.py` |
| Stan Bayesian MCMC | LOO-CV elpd | varies | ArviZ output |

---

## 21. File Reference Map

| File | Lines | Role |
|---|---|---|
| `wmr_advanced_pipeline.ipynb` | 111 | Kaggle GPU pipeline #1 (AutoGluon + SHAP + Survival + Risk) |
| `ATNM_Decision_Studio_Kaggle_GPU.ipynb` | 1639 | Kaggle GPU pipeline #2 (3-target AG + TimeSFM + Report) |
| `Bashira-Intelligence/feature_engine.py` | 779 | 58-feature engineering + AutoGluon/RSF CPU inference |
| `Bashira-Intelligence/predict_service.py` | 572 | FastAPI predictive analytics endpoints |
| `Bashira-Intelligence/cpu_ml_orchestrator.py` | ~1200 | CPU ML microservice (LightGBM + ARIMA + S-Learner + SHAP) |
| `Bashira-Intelligence/forecast_engine.py` | ~1500 | Well lifecycle forecasting + hybrid risk scoring |
| `Bashira-Intelligence/ensemble_stacker.py` | 479 | Meta-ensemble with isotonic calibration + conformal prediction |
| `Bashira-Intelligence/causal_stan_service.py` | 928 | CmdStan MCMC / Laplace Bayesian counterfactuals |
| `Bashira-Intelligence/causal_command_service.py` | 2316 | Causal workspace builder + scenario simulator |
| `Bashira-Intelligence/anomaly_tracker.py` | 434 | Risk tier transition tracker (SQL Server/SQLite/memory) |
| `Bashira-Intelligence/causal_confidence.py` | — | Confidence label composition |
| `Bashira-Intelligence/causal_scenario_catalog.py` | — | Scenario catalog merging |
| `Bashira-Intelligence/causal_workspace_contract.py` | — | Workspace status/health contracts |
| `wmr_results (1)/ag_metrics.json` | 7 | AutoGluon training metrics |
| `wmr_results (1)/priority_wells_final.csv` | — | Pre-computed ML predictions for all wells |
| `wmr_results (1)/risk_scores.csv` | — | Per-well risk scores |
| `wmr_results (1)/survival_predictions.csv` | — | Survival model completion dates |
| `wmr_results (1)/feature_importance.csv` | — | SHAP-based feature importance |
| `wmr_results (1)/shap_values.csv` | — | Raw SHAP values per well |
| `wmr_results (1)/ag_leaderboard.csv` | — | AutoGluon model leaderboard |

---

*End of Document — Generated from full codebase analysis*
