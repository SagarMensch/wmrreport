"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

type Topic = {
  id: string;
  label: string;
  family: string;
  status: "ready" | "queued";
  accent: string;
  source: string;
  summary: string;
  why: string;
  stages: string[];
  outputs: string[];
  storyboard: string[];
  videoSrc?: string;
};

const TOPICS: Topic[] = [
  {
    id: "shap-driver-attribution",
    label: "SHAP Driver Attribution",
    family: "Explainability",
    status: "ready",
    accent: "#1D4ED8",
    source: "cpu_ml_orchestrator.py:233-264, 319-331, 1263-1317, 1483-1524",
    summary: "A simple lesson on how Bashira decides whether one well looks safer or more delayed, and how SHAP explains that decision.",
    why: "This is the right first sample because it teaches one machine-learning idea slowly: the model makes a class prediction, then SHAP explains why.",
    stages: [
      "Train a dedicated LightGBM estimator and build `shap.TreeExplainer`.",
      "Build `X_live` from well context with the exact 10 scenario feature columns.",
      "Select the positive-class SHAP vector and zip it back to `_feature_cols`.",
      "Sort impacts, threshold noise, then emit `hidden_insights` and `risk_drivers`.",
    ],
    outputs: [
      "Per-well `hidden_insights`",
      "Per-well `risk_drivers` with `contribution_pct`",
      "Portfolio mean-absolute SHAP signals",
    ],
    storyboard: [
      "Risk panel becomes `X_risk`, `y_risk`, a calibrated probability model, and a separate SHAP estimator.",
      "The live explainer only sees the 10 scenario features defined in `_scenario_feature_cols`.",
      "`_build_feature_frame(context)` feeds `predict_proba` first, so SHAP is tied to the actual live risk score.",
      "Bashira selects class-1 SHAP values, ranks absolute impacts, and turns the top features into business text.",
      "The same explainer also powers portfolio-wide mean-absolute SHAP for fleet signals.",
    ],
    videoSrc: "/demo-videos/shap-driver-attribution-approval.mp4",
  },
  {
    id: "scenario-feature-frame",
    label: "Scenario Feature Dimensions",
    family: "Feature Space",
    status: "ready",
    accent: "#2563EB",
    source: "cpu_ml_orchestrator.py:233-264, 771-775",
    summary: "The 10 live feature dimensions used by the CPU ML risk model and SHAP.",
    why: "This should be the next video if you want to show where each live model input actually comes from.",
    stages: [
      "Define `_scenario_feature_cols`.",
      "Build `_latest_features_df` from the newest well snapshot.",
      "Map context into one aligned feature row.",
      "Reuse the same column order for risk and SHAP.",
    ],
    outputs: ["`_feature_cols` contract", "Aligned live feature row", "Stable input order"],
    storyboard: [
      "Why progress, momentum, readiness, congestion, and schedule pressure are grouped together.",
      "How the latest row per well becomes the live inference frame.",
      "How `_build_feature_frame` keeps the feature order deterministic.",
      "Why both `predict_proba` and SHAP use the same aligned columns.",
    ],
    videoSrc: "/demo-videos/scenario-feature-dimensions-approval.mp4",
  },
  {
    id: "autogluon-progress-forecast",
    label: "AutoGluon 4-Week Forecast",
    family: "Forecasting",
    status: "ready",
    accent: "#0F62FE",
    source: "feature_engine.py:7-10, 156-172, 493-507, 651-675",
    summary: "How the trained AutoGluon predictor turns 58 engineered features into a forward progress forecast.",
    why: "This is the main near-term progress path in the trained predictive stack.",
    stages: ["Load model artifact.", "Engineer the exact 58-feature frame.", "Predict the next 4-week path.", "Attach the result to the downstream stack."],
    outputs: ["Near-term progress forecast", "Reusable downstream signal", "Model-backed movement path"],
    storyboard: [
      "Where the trained AutoGluon model is loaded from disk.",
      "How the 58 engineered columns are assembled before prediction.",
      "How the predictor returns next-stage progress movement.",
      "How this forecast becomes part of the broader decision surface.",
    ],
    videoSrc: "/demo-videos/autogluon-progress-forecast-approval.mp4",
  },
  {
    id: "feature-engineering-58",
    label: "58-Feature Engineering",
    family: "Feature Engineering",
    status: "ready",
    accent: "#1E40AF",
    source: "feature_engine.py:328-490; predictive-studio-tab-working.html:538-573",
    summary: "How Bashira derives lag, readiness, and schedule-gap features from raw SQL monitoring rows.",
    why: "This is the foundational topic if you want to explain where predictive signal quality comes from.",
    stages: ["Land raw WMR rows.", "Derive lag and pace signals.", "Encode readiness and identifiers.", "Freeze the 58-column schema."],
    outputs: ["58-column model frame", "Lag and momentum signals", "Readiness and schedule-gap features"],
    storyboard: [
      "Which raw columns are lifted from the monitoring feed.",
      "Why lag windows and rolling pace features matter more than static values.",
      "How engineering, location, and material states become model inputs.",
      "How the service guarantees the exact 58 features expected by the trained stack.",
    ],
    videoSrc: "/demo-videos/feature-engineering-58-approval.mp4",
  },
  {
    id: "random-survival-forest",
    label: "Random Survival Forest",
    family: "Time-To-Event",
    status: "ready",
    accent: "#2E7D32",
    source: "feature_engine.py:217-315, 515-568; predictive-studio-tab-working.html:581-595",
    summary: "How Bashira estimates completion timing and uncertainty instead of one hard finish date.",
    why: "This is the right topic when timing probability matters more than a single risk score.",
    stages: ["Train RSF from engineered history.", "Build the survival frame.", "Read quantile windows.", "Publish timing outputs."],
    outputs: ["Median completion estimate", "P10/P50/P90 window", "Time-aware uncertainty"],
    storyboard: [
      "Why Bashira uses time-to-event logic instead of a single deterministic date.",
      "How historical wells become event-plus-duration training rows for survival learning.",
      "How three hundred trees learn timing patterns from progress, pace, remaining work, and readiness signals.",
      "How percentile timing outputs are read directly from the survival curve.",
      "How Bashira turns the curve into early, median, and late completion windows.",
    ],
    videoSrc: "/demo-videos/random-survival-forest-approval.mp4",
  },
  {
    id: "kaggle-risk-formula",
    label: "Exact Kaggle Risk Formula",
    family: "Risk Composition",
    status: "ready",
    accent: "#ED6C02",
    source: "feature_engine.py:84-107, 570-625; predictive-studio-tab-working.html:478-490",
    summary: "The weighted risk equation that combines progress, velocity, schedule, and gap risk into one score.",
    why: "This is the cleanest formula-first topic because the weights are explicit in both code and docs.",
    stages: ["Compute four component risks.", "Apply the Kaggle-derived weights.", "Normalize to 0-100.", "Map to risk tiers."],
    outputs: ["Composite risk score", "Risk tier", "Formula-backed explanation path"],
    storyboard: [
      "How progress, velocity, schedule pressure, and progress gap are each converted into risk components.",
      "Why the formula gives thirty five percent to incompletion and twenty five percent to weekly pace.",
      "How Bashira adds the weighted pieces, bounds the score, and rounds it into a dashboard number.",
      "How numeric thresholds turn the score into healthy, watch, high risk, or critical.",
    ],
    videoSrc: "/demo-videos/kaggle-risk-formula-approval.mp4",
  },
  {
    id: "nightly-refresh-anomalies",
    label: "Nightly Refresh And Anomalies",
    family: "Operations Refresh",
    status: "ready",
    accent: "#B91C1C",
    source: "predict_service.py:312-360, 387-444",
    summary: "The nightly batch path that re-scores wells, detects tier shifts, and updates anomaly tracking.",
    why: "This is the best topic for explaining how predictive outputs stay live instead of becoming stale dashboards.",
    stages: ["Fetch active wells.", "Run the predictive stack.", "Compare old versus new tier.", "Sync the anomaly tracker."],
    outputs: ["Updated risk tiers", "Tier-change anomalies", "Refreshed portfolio state"],
    storyboard: [
      "How Bashira selects only unfinished wells for the overnight pass.",
      "How each active well is pushed back through feature engineering, forecast, survival, and risk scoring.",
      "How the tracker compares yesterday's tier with today's tier and writes an anomaly only on drift.",
      "How the refreshed state and anomaly feed are ready for the morning portfolio view.",
    ],
    videoSrc: "/demo-videos/nightly-refresh-anomalies-approval.mp4",
  },
  {
    id: "calibrated-lightgbm-risk",
    label: "Calibrated LightGBM Delay Risk",
    family: "Classification",
    status: "ready",
    accent: "#1E3A8A",
    source: "cpu_ml_orchestrator.py:291-345",
    summary: "The calibrated LightGBM probability path used for live delay-risk scoring.",
    why: "This is the actual probability engine that SHAP is explaining.",
    stages: ["Build the supervised risk panel.", "Split train and test.", "Fit LightGBM with sigmoid calibration.", "Score live delay probability."],
    outputs: ["Calibrated risk probability", "AUC/Brier health signals", "Stable base for SHAP"],
    storyboard: [
      "How Bashira builds a labeled delay panel from actual-versus-expected rig-off outcomes.",
      "How ten live features feed a LightGBM classifier and why the split is stratified.",
      "Why sigmoid calibration sits on top of the tree model before probabilities are trusted.",
      "How predict_proba becomes the live delay percent and then feeds SHAP explanations.",
    ],
    videoSrc: "/demo-videos/calibrated-lightgbm-risk-approval.mp4",
  },
  {
    id: "statsforecast-trajectory",
    label: "StatsForecast Trajectory",
    family: "Time Series",
    status: "ready",
    accent: "#0284C7",
    source: "cpu_ml_orchestrator.py:1191-1262; ensemble_stacker.py:9-12; ml-algorithms-and-terms-master.html:137",
    summary: "The temporal forecast path that extends Bashira beyond tabular snapshots into trajectory modeling.",
    why: "This is the right topic when you want to show how history itself is forecast, not just current-state risk.",
    stages: ["Use ordered well history.", "Fit AutoARIMA-style temporal logic.", "Read the projected path.", "Merge into the deeper stack."],
    outputs: ["Projected trajectory", "Temporal evidence", "Ensemble input member"],
    storyboard: [
      "Why Bashira treats ordered progress history as a genuine time series instead of another snapshot row.",
      "How the well history is repacked into unique_id, ds, and y for the StatsForecast engine.",
      "How AutoARIMA with weekly frequency and a four-step horizon produces a forward trajectory with bounds.",
      "How the resulting trajectory becomes the temporal evidence member inside the broader ensemble stack.",
    ],
    videoSrc: "/demo-videos/statsforecast-trajectory-approval.mp4",
  },
  {
    id: "ensemble-stacking",
    label: "Ensemble Stacking",
    family: "Model Fusion",
    status: "ready",
    accent: "#6D28D9",
    source: "ensemble_stacker.py:2-16, 123-375",
    summary: "How Bashira blends calibrated risk, AutoARIMA trajectory, Stan signals, and S-Learner CATE into one output.",
    why: "This is the institutional-grade model fusion topic because it shows weighting, calibration, and disagreement handling together.",
    stages: ["Collect base members.", "Apply weighted fusion.", "Calibrate with isotonic and conformal logic.", "Return the ensemble output."],
    outputs: ["Unified ensemble risk", "Conformal interval", "Per-member contribution view"],
    storyboard: [
      "How LightGBM, StatsForecast, Stan, and S-Learner enter the stack as separate evidence channels.",
      "How Bashira converts different model outputs into comparable risk signals and fuses them with active weights only.",
      "How isotonic calibration and conformal logic sit on top of the raw weighted stack before the final percent is trusted.",
      "How agreement and online weight updates stop the ensemble from hiding disagreement or staying frozen forever.",
    ],
    videoSrc: "/demo-videos/ensemble-stacking-approval.mp4",
  },
  {
    id: "conformal-intervals",
    label: "Conformal Prediction Intervals",
    family: "Uncertainty",
    status: "ready",
    accent: "#7E22CE",
    source: "ensemble_stacker.py:38-113, 182-198, 336-375",
    summary: "The split-conformal wrapper that converts point predictions into distribution-free intervals.",
    why: "This is the clean uncertainty topic because it is a self-contained method in the ensemble layer.",
    stages: ["Reserve residuals.", "Estimate conformal quantile.", "Wrap the base prediction.", "Return lower and upper bounds."],
    outputs: ["Distribution-free interval", "Interval method metadata", "Defensible uncertainty band"],
    storyboard: [
      "How Bashira stores absolute residuals and only fits conformal logic after enough evidence exists.",
      "Why the later slice of history is reserved for interval calibration instead of reusing all data blindly.",
      "How q-hat is read from the empirical residual distribution and wrapped around the point prediction.",
      "How fallback logic and interval metadata make the uncertainty band honest and usable.",
    ],
    videoSrc: "/demo-videos/conformal-intervals-approval.mp4",
  },
  {
    id: "s-learner-cate",
    label: "S-Learner CATE",
    family: "Scenario Modeling",
    status: "ready",
    accent: "#0F766E",
    source: "cpu_ml_orchestrator.py:389-435, 1068-1141; ml-algorithms-and-terms-master.html:141",
    summary: "How Bashira estimates intervention lift and alternative-rig opportunity with a CATE member.",
    why: "This is the right topic when the client asks how Bashira moves from risk scoring into action ranking.",
    stages: ["Read the factual state.", "Score alternatives.", "Compute context-specific treatment effect.", "Rank the best intervention."],
    outputs: ["Best alternative action", "Context-specific treatment effect", "Intervention-aware ensemble input"],
    storyboard: [
      "How the problem shifts from passive prediction into intervention effect.",
      "How Bashira trains one S-Learner on treatment plus confounders in the same model.",
      "How factual and counterfactual rig assignments are compared to compute well-specific CATE.",
      "How the top non-current rig becomes the intervention recommendation.",
    ],
    videoSrc: "/demo-videos/s-learner-cate-approval.mp4",
  },
  {
    id: "bayesian-counterfactuals",
    label: "Bayesian Counterfactuals",
    family: "Deep Causal Layer",
    status: "ready",
    accent: "#9333EA",
    source: "causal_stan_service.py:2-11, 78-90, 418-535, 740-830",
    summary: "How the Stan service produces posterior counterfactual summaries for intervention analysis.",
    why: "This is the strongest institutional-depth topic because it adds posterior uncertainty and hierarchy.",
    stages: ["Prepare Stan data.", "Run CmdStan or Laplace path.", "Extract posterior effects.", "Aggregate counterfactual scenarios."],
    outputs: ["Posterior effect summaries", "Counterfactual options", "Bayesian uncertainty narrative"],
    storyboard: [
      "How Bashira checks CmdStan and toolchain state before the deep path runs.",
      "How the causal model estimates uncertainty-aware effects.",
      "How rig, cluster, well type, and progress bands enter the hierarchy.",
      "How posterior delta days become action-facing scenario summaries.",
    ],
    videoSrc: "/demo-videos/bayesian-counterfactuals-approval.mp4",
  },
  {
    id: "isolation-forest-anomalies",
    label: "IsolationForest Anomalies",
    family: "Monitoring",
    status: "ready",
    accent: "#DC2626",
    source: "command_center_service.py:18-25, 340-356, 1559-1689; ml-algorithms-and-terms-master.html:179",
    summary: "How Bashira scores operational outliers against current fleet execution patterns.",
    why: "This is the strongest monitoring topic because it catches unusual behavior before a KPI threshold alone would.",
    stages: ["Assemble feature rows.", "Fit IsolationForest.", "Score outliers.", "Attach the evidence to operations views."],
    outputs: ["Anomaly score", "Anomaly flag", "Operational evidence for monitoring surfaces"],
    storyboard: [
      "Why Bashira uses anomaly logic even when labels are sparse.",
      "How unusual wells are isolated faster than normal fleet patterns.",
      "How anomaly hits strengthen downstream pressure scoring.",
      "How the anomaly flag becomes plain-language operational evidence.",
    ],
    videoSrc: "/demo-videos/isolation-forest-anomalies-approval.mp4",
  },
  {
    id: "spatial-pressure",
    label: "Spatial Pressure And Clusters",
    family: "Spatial Intelligence",
    status: "ready",
    accent: "#0EA5E9",
    source: "command_center_service.py:1983-2065, 2117-2235, 2238-2418",
    summary: "How Bashira uses neighborhood pressure and DBSCAN-style clustering in the atlas layer.",
    why: "This is the best topic when you want to show that predictive pressure is geographic, not only per-well.",
    stages: ["Map coordinates.", "Measure nearest-neighbor pressure.", "Form density clusters.", "Project zone-level risk."],
    outputs: ["Neighborhood pressure", "Operational zones", "Geographic risk context"],
    storyboard: [
      "Why location and neighbor count change operational behavior.",
      "How local pressure is measured geometrically.",
      "Why density-based clustering fits oilfield geography better than fixed cluster counts.",
      "How zone pressure becomes a map-ready decision surface.",
    ],
    videoSrc: "/demo-videos/spatial-pressure-clusters-approval.mp4",
  },
];

export default function PredictiveAlgorithmDemoPanel() {
  const [activeTopicId, setActiveTopicId] = useState("shap-driver-attribution");
  const [sceneIndex, setSceneIndex] = useState(0);

  const activeTopic = useMemo(
    () => TOPICS.find((topic) => topic.id === activeTopicId) ?? TOPICS[0],
    [activeTopicId],
  );

  const counts = useMemo(
    () => ({
      total: TOPICS.length,
      ready: TOPICS.filter((topic) => topic.status === "ready").length,
      queued: TOPICS.filter((topic) => topic.status === "queued").length,
    }),
    [],
  );

  useEffect(() => {
    if (!activeTopic) return;
    setSceneIndex(0);
  }, [activeTopic]);

  useEffect(() => {
    if (!activeTopic) return;
    const handle = window.setInterval(() => {
      setSceneIndex((current) => (current + 1) % activeTopic.storyboard.length);
    }, 3600);
    return () => window.clearInterval(handle);
  }, [activeTopic]);

  if (!activeTopic) return null;

  return (
    <section
      style={{
        borderRadius: "26px",
        border: "1px solid rgba(148, 163, 184, 0.18)",
        background: "linear-gradient(180deg, rgba(15, 23, 42, 0.96) 0%, rgba(15, 23, 42, 0.9) 100%)",
        boxShadow: "0 24px 60px rgba(2, 6, 23, 0.22)",
        padding: "28px",
        color: "#E2E8F0",
      }}
    >
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.3fr) minmax(0, 0.7fr)", gap: "18px", marginBottom: "22px" }}>
        <div>
          <div style={{ display: "inline-flex", padding: "8px 14px", borderRadius: "999px", background: "rgba(59, 130, 246, 0.14)", color: "#BFDBFE", fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "16px" }}>
            Predictive Topic Approval Board
          </div>
          <h2 style={{ margin: 0, fontSize: "34px", lineHeight: 1.1, color: "#F8FAFC", fontWeight: 700 }}>
            One real topic first, then the rest.
          </h2>
          <p style={{ margin: "14px 0 0", fontSize: "15px", lineHeight: 1.8, color: "#CBD5E1", maxWidth: "760px" }}>
            This panel lists the top predictive topics pulled from Bashira code and module docs. Only the SHAP topic has a recorded approval MP4. Every other topic stays queued until that format is approved.
          </p>
        </div>

        <div style={{ borderRadius: "22px", border: "1px solid rgba(148, 163, 184, 0.16)", background: "rgba(15, 23, 42, 0.72)", padding: "18px", display: "grid", gap: "12px" }}>
          {[
            { label: "Topics Found", value: counts.total },
            { label: "Videos Ready", value: counts.ready },
            { label: "Queued", value: counts.queued },
          ].map((metric) => (
            <div key={metric.label} style={{ display: "flex", justifyContent: "space-between", gap: "12px", paddingBottom: "10px", borderBottom: "1px solid rgba(148, 163, 184, 0.12)" }}>
              <span style={{ color: "#94A3B8", fontSize: "13px", fontWeight: 600 }}>{metric.label}</span>
              <span style={{ color: "#F8FAFC", fontSize: "16px", fontWeight: 700 }}>{metric.value}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 360px) minmax(0, 1fr)", gap: "20px" }}>
        <aside style={{ borderRadius: "24px", border: "1px solid rgba(148, 163, 184, 0.16)", background: "rgba(15, 23, 42, 0.74)", padding: "18px", display: "grid", gap: "12px", alignContent: "start", maxHeight: "980px", overflowY: "auto" }}>
          <div style={{ fontSize: "11px", color: "#93C5FD", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>
            Top 15 Candidate Videos
          </div>
          {TOPICS.map((topic, index) => {
            const selected = topic.id === activeTopic.id;
            return (
              <button
                key={topic.id}
                type="button"
                onClick={() => setActiveTopicId(topic.id)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  borderRadius: "18px",
                  border: selected ? `1px solid ${topic.accent}` : "1px solid rgba(148, 163, 184, 0.16)",
                  background: selected ? `${topic.accent}18` : "rgba(15, 23, 42, 0.52)",
                  padding: "14px",
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: "10px", marginBottom: "8px" }}>
                  <span style={{ color: "#64748B", fontSize: "11px", fontWeight: 700 }}>{String(index + 1).padStart(2, "0")}</span>
                  <span style={{ padding: "4px 10px", borderRadius: "999px", background: topic.status === "ready" ? "rgba(34, 197, 94, 0.16)" : "rgba(148, 163, 184, 0.16)", color: topic.status === "ready" ? "#BBF7D0" : "#CBD5E1", fontSize: "10px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                    {topic.status}
                  </span>
                </div>
                <div style={{ color: "#F8FAFC", fontSize: "15px", fontWeight: 700, marginBottom: "4px" }}>{topic.label}</div>
                <div style={{ color: topic.accent, fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>{topic.family}</div>
                <div style={{ color: "#CBD5E1", fontSize: "13px", lineHeight: 1.6 }}>{topic.summary}</div>
              </button>
            );
          })}
        </aside>

        <div style={{ display: "grid", gap: "18px" }}>
          <div style={{ borderRadius: "24px", border: "1px solid rgba(148, 163, 184, 0.16)", background: "rgba(15, 23, 42, 0.74)", padding: "22px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", flexWrap: "wrap", marginBottom: "14px" }}>
              <div>
                <div style={{ fontSize: "12px", color: activeTopic.accent, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "8px" }}>{activeTopic.family}</div>
                <h3 style={{ margin: 0, fontSize: "28px", color: "#F8FAFC", fontWeight: 700 }}>{activeTopic.label}</h3>
              </div>
              <div style={{ alignSelf: "start", padding: "8px 12px", borderRadius: "999px", background: activeTopic.status === "ready" ? "rgba(34, 197, 94, 0.16)" : "rgba(148, 163, 184, 0.16)", color: activeTopic.status === "ready" ? "#BBF7D0" : "#CBD5E1", fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                {activeTopic.status === "ready" ? "Approval sample ready" : "Queued after approval"}
              </div>
            </div>
            <p style={{ margin: 0, fontSize: "15px", lineHeight: 1.8, color: "#CBD5E1" }}>{activeTopic.why}</p>
            <div style={{ marginTop: "16px", borderRadius: "18px", background: "rgba(2, 6, 23, 0.38)", border: "1px solid rgba(148, 163, 184, 0.14)", padding: "14px" }}>
              <div style={{ fontSize: "11px", color: "#93C5FD", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "8px" }}>Code Source</div>
              <div style={{ color: "#E2E8F0", fontSize: "14px", lineHeight: 1.7 }}>{activeTopic.source}</div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.05fr) minmax(0, 0.95fr)", gap: "18px" }}>
            <div style={{ borderRadius: "24px", border: "1px solid rgba(148, 163, 184, 0.16)", background: "rgba(15, 23, 42, 0.74)", padding: "18px", display: "grid", gap: "14px" }}>
              <div style={{ fontSize: "11px", color: "#93C5FD", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>Approval Video</div>
              {activeTopic.videoSrc ? (
                <>
                  <video
                    key={activeTopic.videoSrc}
                    src={activeTopic.videoSrc}
                    controls
                    autoPlay
                    loop
                    muted
                    playsInline
                    preload="metadata"
                    style={{ width: "100%", display: "block", borderRadius: "18px", background: "#020617", border: `1px solid ${activeTopic.accent}55` }}
                  />
                  <div style={{ fontSize: "13px", lineHeight: 1.7, color: "#CBD5E1" }}>
                    This is the only recorded sample right now. It is meant to feel like a simple classroom lesson: what the model is, what class 0 and class 1 mean, what the clues are, and how SHAP explains the final answer.
                  </div>
                </>
              ) : (
                <div style={{ borderRadius: "18px", border: "1px dashed rgba(148, 163, 184, 0.3)", background: "rgba(15, 23, 42, 0.48)", padding: "22px", color: "#CBD5E1", fontSize: "14px", lineHeight: 1.8 }}>
                  Only `web/public/demo-videos/shap-driver-attribution-approval.mp4` is generated right now. The rest stay queued so the screen does not pretend those videos already exist.
                </div>
              )}
            </div>

            <div style={{ borderRadius: "24px", border: "1px solid rgba(148, 163, 184, 0.16)", background: "rgba(15, 23, 42, 0.74)", padding: "18px", display: "grid", gap: "12px" }}>
              <div style={{ fontSize: "11px", color: "#93C5FD", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>Topic Outputs</div>
              {activeTopic.outputs.map((output) => (
                <div key={output} style={{ borderRadius: "16px", border: "1px solid rgba(148, 163, 184, 0.14)", background: "rgba(30, 41, 59, 0.5)", padding: "12px 14px", color: "#E2E8F0", fontSize: "14px", lineHeight: 1.6 }}>
                  {output}
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 0.95fr) minmax(0, 1.05fr)", gap: "18px" }}>
            <div style={{ borderRadius: "24px", border: "1px solid rgba(148, 163, 184, 0.16)", background: "rgba(15, 23, 42, 0.74)", padding: "18px", display: "grid", gap: "12px" }}>
              <div style={{ fontSize: "11px", color: "#93C5FD", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>Code Path Stages</div>
              {activeTopic.stages.map((stage, index) => (
                <div key={stage} style={{ display: "grid", gridTemplateColumns: "34px minmax(0, 1fr)", gap: "10px" }}>
                  <div style={{ width: "34px", height: "34px", borderRadius: "999px", background: `${activeTopic.accent}26`, border: `1px solid ${activeTopic.accent}55`, display: "grid", placeItems: "center", color: "#F8FAFC", fontSize: "13px", fontWeight: 700 }}>
                    {index + 1}
                  </div>
                  <div style={{ borderRadius: "16px", border: "1px solid rgba(148, 163, 184, 0.14)", background: "rgba(30, 41, 59, 0.5)", padding: "12px 14px", color: "#CBD5E1", fontSize: "14px", lineHeight: 1.7 }}>
                    {stage}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ borderRadius: "24px", border: "1px solid rgba(148, 163, 184, 0.16)", background: "rgba(15, 23, 42, 0.74)", padding: "18px", display: "grid", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: "11px", color: "#93C5FD", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" }}>Storyboard Preview</div>
                  <div style={{ fontSize: "14px", color: "#CBD5E1" }}>
                    Scene {sceneIndex + 1} of {activeTopic.storyboard.length}
                  </div>
                </div>
                <div style={{ padding: "8px 12px", borderRadius: "999px", background: `${activeTopic.accent}22`, color: activeTopic.accent, fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Auto-play
                </div>
              </div>

              <AnimatePresence mode="wait">
                <motion.div
                  key={`${activeTopic.id}-${sceneIndex}`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.2 }}
                  style={{ borderRadius: "18px", border: "1px solid rgba(148, 163, 184, 0.14)", background: "linear-gradient(180deg, rgba(30, 41, 59, 0.56) 0%, rgba(15, 23, 42, 0.7) 100%)", padding: "18px", minHeight: "180px" }}
                >
                  <div style={{ fontSize: "12px", color: activeTopic.accent, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "10px" }}>
                    {activeTopic.label}
                  </div>
                  <div style={{ color: "#F8FAFC", fontSize: "15px", lineHeight: 1.8 }}>{activeTopic.storyboard[sceneIndex]}</div>
                </motion.div>
              </AnimatePresence>

              <div style={{ display: "grid", gridTemplateColumns: `repeat(${activeTopic.storyboard.length}, minmax(0, 1fr))`, gap: "8px" }}>
                {activeTopic.storyboard.map((scene, index) => {
                  const selected = index === sceneIndex;
                  return (
                    <button
                      key={scene}
                      type="button"
                      onClick={() => setSceneIndex(index)}
                      style={{
                        minHeight: "62px",
                        textAlign: "left",
                        borderRadius: "14px",
                        border: selected ? `1px solid ${activeTopic.accent}` : "1px solid rgba(148, 163, 184, 0.14)",
                        background: selected ? `${activeTopic.accent}18` : "rgba(15, 23, 42, 0.42)",
                        padding: "10px",
                        cursor: "pointer",
                        color: selected ? "#F8FAFC" : "#CBD5E1",
                        fontSize: "12px",
                        lineHeight: 1.5,
                      }}
                    >
                      Scene {index + 1}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
