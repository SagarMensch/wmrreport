"use client";

import dynamic from "next/dynamic";
import type { PlotParams } from "react-plotly.js";
import { useEffect, useMemo, useState } from "react";

type SourceTrace = {
  label: string;
  table: string;
  column: string;
  note: string;
  as_of: string;
  kind: string;
};

type FeatureLineage = {
  table: string;
  column: string;
  meaning: string;
};

type ScenarioCatalogItem = {
  label: string;
  description: string;
};

type Driver = {
  feature: string;
  label: string;
  std_impact?: number;
  unit_impact_days?: number;
  ten_percent_impact_days?: number;
  source?: FeatureLineage;
};

type RootCause = {
  feature: string;
  label: string;
  contribution_score: number;
  source: FeatureLineage;
};

type Scenario = {
  scenario: string;
  label: string;
  description: string;
  baseline_delay_days: number;
  delta_days: number;
  new_delay_days: number;
  support_cases: number;
  assumption_note: string;
  engine: string;
};

type WellDecision = {
  well_id: string;
  well_name: string;
  rig_no: string;
  well_type: string;
  cluster: string;
  current_progress_pct: number;
  baseline_delay_days: number;
  recommended_action: string;
  recommended_delta_days: number;
  recommendation: string;
  scenarios: Scenario[];
  root_causes: RootCause[];
  model_baseline_delay_days: number;
  signal_quality: string;
  scenario_support_cases: number;
  action_status: string;
  confidence_label: string;
  decision_score: number;
  primary_issue: string;
  why_now: string;
  source_trace: SourceTrace[];
};

type PortfolioCard = {
  label: string;
  value: string;
  unit: string;
  accent: string;
  source: SourceTrace;
};

type PortfolioBrief = {
  as_of: string;
  management_message: string;
  attention_now: number;
  candidate_count: number;
  blocked_count: number;
  cards: PortfolioCard[];
  top_opportunity?: WellDecision;
};

type InterventionLadderItem = {
  rank: number;
  well_id: string;
  well_name: string;
  cluster: string;
  rig_no: string;
  well_type: string;
  action_label: string;
  recoverable_days: number;
  decision_score: number;
  confidence_label: string;
  action_status: string;
  why_now: string;
  support_cases: number;
  source: SourceTrace;
};

type AnalysisBasis = {
  engine: string;
  mode: string;
  rows: number;
  features: number;
  r2: number;
  rmse: number;
  support_cases: Record<string, number>;
  posterior_status: string;
};

type InteractiveModel = {
  scenario_catalog: Record<string, ScenarioCatalogItem>;
  feature_lineage: Record<string, FeatureLineage>;
  top_drivers: Driver[];
  wells: WellDecision[];
  portfolio_brief: PortfolioBrief;
  intervention_ladder: InterventionLadderItem[];
  analysis_basis: AnalysisBasis;
};

type CoverageCard = {
  label: string;
  coverage_pct: number;
  status: string;
};

type DataHealth = {
  live_wells: number;
  historical_wells: number;
  mean_progress_pct: number;
  delayed_wells: number;
  bayesian_runtime: string;
  analysis_mode: string;
  cpu_model_status: string;
};

type AuditQuestion = {
  id?: string;
  question?: string;
  answer?: string;
  status?: string;
};

type AnalysisStatus = {
  headline: string;
  detail: string;
  mode: string;
  cache_age_seconds: number;
  refresh_in_progress: boolean;
  last_bayesian_started_at?: string | null;
  last_bayesian_completed_at?: string | null;
};

type BayesianAnalysis = {
  status: string;
  message?: string;
  refresh_in_progress?: boolean;
  started_at?: string | null;
  completed_at?: string | null;
};

type WorkspaceResponse = {
  generated_at: string;
  workspace_name: string;
  objective: string;
  target: string;
  analysis_status: AnalysisStatus;
  data_health: DataHealth;
  coverage_cards: CoverageCard[];
  audit_questions: AuditQuestion[];
  interactive: InteractiveModel;
  bayesian_analysis: BayesianAnalysis;
  gaps: Array<{ label: string; detail: string }>;
};

type ViewMode = "command" | "evidence" | "model";
type PlotFigure = {
  data: PlotParams["data"];
  layout: PlotParams["layout"];
  config?: PlotParams["config"];
};

type MinimalInteractive = Partial<InteractiveModel> & {
  wells?: WellDecision[];
  portfolio_brief?: PortfolioBrief;
  intervention_ladder?: InterventionLadderItem[];
};

const QUICK_COMMANDS = [
  "highest delay well",
  "best action",
  "act now",
  "weak support",
  "open support",
];

const Plot = dynamic(() => import("./PlotlyClient"), {
  ssr: false,
  loading: () => (
    <div className="plot-loading">Rendering decision surface...</div>
  ),
});

const numberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
});

function getCausalEndpoint(): string {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://127.0.0.1:8005/api/causal/command";
    }
  }
  return "/api/causal";
}

async function fetchWithTimeout(
  url: string,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });
  } finally {
    window.clearTimeout(timeout);
  }
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return "n/a";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDays(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return "n/a";
  }
  return `${numberFormatter.format(value)}d`;
}

function formatPct(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return "n/a";
  }
  return `${numberFormatter.format(value)}%`;
}

function formatCoverage(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return "n/a";
  }
  return `${Math.round(value)}%`;
}

function humanizeToken(value?: string | null): string {
  if (!value) {
    return "n/a";
  }
  const mapping: Record<string, string> = {
    schedule_delay_days: "Schedule delay",
    cpu_operational_model_v1: "Operational decision model",
    cpu_plus_bayesian: "Decision workspace",
    LightGBMRegressor: "LightGBM",
    ph_average_productivity_pct: "Linked productivity",
    overdue_daily_tasks: "Overdue daily backlog",
    overdue_daily_remaining_duration: "Overdue remaining duration",
    daily_task_completion_rate: "Daily task completion rate",
    activity_overdue_tasks: "Overdue planned backlog",
    activity_task_completion_rate: "Planned task completion rate",
    activity_remaining_duration_days: "Planned remaining duration",
    current_month_gap: "Current-month execution gap",
    cum_month_gap: "Cumulative execution gap",
    five_week_plan: "Near-term plan pressure",
    avg_move_days: "Rig move delay",
    weekly_velocity: "Weekly execution velocity",
    engg_kpi_days: "Engineering lag",
  };
  if (mapping[value]) {
    return mapping[value];
  }
  return value
    .replaceAll("_", " ")
    .replaceAll("pct", "%")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function primaryStatusLabel(status: AnalysisStatus): string {
  return status.mode === "cpu_plus_bayesian"
    ? "Decision deck current"
    : "Decision deck live";
}

function secondaryStatusLabel(status: AnalysisStatus): string {
  return status.refresh_in_progress
    ? "Extended analysis updating"
    : "Analysis current";
}

function statusSummary(status: AnalysisStatus): string {
  return status.refresh_in_progress
    ? "Management view is current. Additional diagnostics are refreshing in the background."
    : "Management view is current and ready for action.";
}

function tabLabel(mode: ViewMode): string {
  if (mode === "command") {
    return "Command";
  }
  if (mode === "evidence") {
    return "Trace";
  }
  return "Engine";
}

function kindLabel(kind: string): string {
  if (kind === "fact") {
    return "Fact";
  }
  if (kind === "model") {
    return "Model";
  }
  return "Derived";
}

function accentClass(accent: string): string {
  if (accent === "green") {
    return "accent-green";
  }
  if (accent === "red") {
    return "accent-red";
  }
  if (accent === "amber") {
    return "accent-amber";
  }
  return "accent-blue";
}

function buildScenarioTrace(
  scenario: Scenario | undefined,
  lineage: Record<string, FeatureLineage>,
  asOf: string,
): SourceTrace[] {
  if (!scenario) {
    return [];
  }

  const featureMap: Record<string, string[]> = {
    task_relief_minus_5: [
      "overdue_daily_tasks",
      "overdue_daily_remaining_duration",
      "daily_task_completion_rate",
    ],
    plan_relief_minus_10_pct: ["five_week_plan"],
    move_minus_1_day: ["avg_move_days"],
    velocity_plus_10_pct: ["weekly_velocity"],
    ph_plus_10_pct: ["ph_average_productivity_pct"],
  };

  const scenarioKey = scenario.scenario.split("__")[0];
  const features = featureMap[scenarioKey] ?? [scenarioKey];
  return features
    .map((feature) => {
      const item = lineage[feature];
      if (!item) {
        return null;
      }
      return {
        label: `Scenario lever: ${feature.replaceAll("_", " ")}`,
        table: item.table,
        column: item.column,
        note: item.meaning,
        as_of: asOf,
        kind: "model",
      };
    })
    .filter((item): item is SourceTrace => item !== null);
}

function selectedWellFromWorkspace(
  workspace: WorkspaceResponse | null,
  selectedWellId: string | null,
): WellDecision | undefined {
  if (!workspace) {
    return undefined;
  }
  const interactive = workspace.interactive as MinimalInteractive | undefined;
  const wells = interactive?.wells ?? [];
  if (!wells.length) {
    return undefined;
  }
  if (!selectedWellId) {
    return interactive?.portfolio_brief?.top_opportunity ?? wells[0];
  }
  return wells.find((well) => well.well_id === selectedWellId) ?? wells[0];
}

function actionColor(status?: string | null): string {
  const token = String(status ?? "").toLowerCase();
  if (token === "act now") {
    return "#d93b34";
  }
  if (token === "candidate") {
    return "#0f6cbd";
  }
  if (token === "observe") {
    return "#6e7785";
  }
  return "#1f2937";
}

function confidenceColor(label?: string | null): string {
  const token = String(label ?? "").toLowerCase();
  if (token === "high") {
    return "#10b981";
  }
  if (token === "medium") {
    return "#f59e0b";
  }
  if (token === "low") {
    return "#ef4444";
  }
  return "#94a3b8";
}

function shortChartLabel(value?: string | null, max = 18): string {
  const label = humanizeToken(value ?? "");
  if (label.length <= max) {
    return label;
  }
  return `${label.slice(0, max - 1)}…`;
}

function buildSceneLayout(
  _title: string,
  axisLabels: { x: string; y: string; z: string },
): PlotParams["layout"] {
  return {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 0, r: 0, t: 8, b: 0 },
    scene: {
      bgcolor: "rgba(0,0,0,0)",
      camera: { eye: { x: 1.58, y: 1.24, z: 0.86 } },
      xaxis: {
        title: axisLabels.x,
        titlefont: { size: 9, color: "#667085" },
        tickfont: { size: 9, color: "#667085" },
        gridcolor: "rgba(17,19,24,0.05)",
        zerolinecolor: "rgba(17,19,24,0.05)",
        showbackground: true,
        backgroundcolor: "rgba(250,251,253,0.86)",
      },
      yaxis: {
        title: axisLabels.y,
        titlefont: { size: 9, color: "#667085" },
        tickfont: { size: 9, color: "#667085" },
        gridcolor: "rgba(17,19,24,0.05)",
        zerolinecolor: "rgba(17,19,24,0.05)",
        showbackground: true,
        backgroundcolor: "rgba(250,251,253,0.86)",
      },
      zaxis: {
        title: axisLabels.z,
        titlefont: { size: 9, color: "#667085" },
        tickfont: { size: 9, color: "#667085" },
        gridcolor: "rgba(17,19,24,0.05)",
        zerolinecolor: "rgba(17,19,24,0.05)",
        showbackground: true,
        backgroundcolor: "rgba(245,247,250,0.92)",
      },
    },
    showlegend: false,
  } as PlotParams["layout"];
}

function buildPortfolioPressureFigure(
  wells: WellDecision[],
  selectedWellId?: string | null,
): PlotFigure | null {
  if (!wells.length) {
    return null;
  }

  const ranked = [...wells]
    .sort(
      (left, right) =>
        (right.decision_score ?? 0) - (left.decision_score ?? 0) ||
        (right.baseline_delay_days ?? 0) - (left.baseline_delay_days ?? 0),
    )
    .slice(0, 40);

  const x = ranked.map((well) => well.current_progress_pct ?? 0);
  const y = ranked.map((well) => Math.max(well.baseline_delay_days ?? 0, 0));
  const z = ranked.map((well) => well.decision_score ?? 0);
  const xMin = Math.max(0, Math.min(...x) - 5);
  const xMax = Math.max(...x) + 5;
  const yMin = Math.max(0, Math.min(...y) - 5);
  const yMax = Math.max(...y) + 5;
  const gridX = Array.from(
    { length: 18 },
    (_item, index) => xMin + ((xMax - xMin) * index) / 17,
  );
  const gridY = Array.from(
    { length: 16 },
    (_item, index) => yMin + ((yMax - yMin) * index) / 15,
  );
  const sigmaX = Math.max((xMax - xMin) / 5.5, 6);
  const sigmaY = Math.max((yMax - yMin) / 5.5, 6);
  const maxScore = Math.max(...z, 1);
  const surfaceZ = gridY.map((delay) =>
    gridX.map((progress) => {
      let value = 0;
      ranked.forEach((well) => {
        const px = well.current_progress_pct ?? 0;
        const py = Math.max(well.baseline_delay_days ?? 0, 0);
        const pz = well.decision_score ?? 0;
        const dx = progress - px;
        const dy = delay - py;
        value +=
          pz *
          Math.exp(
            -(
              (dx * dx) / (2 * sigmaX * sigmaX) +
              (dy * dy) / (2 * sigmaY * sigmaY)
            ),
          );
      });
      return value;
    }),
  );
  const surfacePeak = Math.max(...surfaceZ.flatMap((row) => row), maxScore);
  const scaledSurface = surfaceZ.map((row) =>
    row.map((value) => (value / surfacePeak) * maxScore),
  );
  const markerSize = ranked.map(
    (well) =>
      7 +
      Math.min(Math.max(Math.abs(well.recommended_delta_days ?? 0), 0), 90) *
        0.12,
  );
  const markerColor = ranked.map((well) => actionColor(well.action_status));
  const spotlight = ranked.slice(0, 8);

  const selected = ranked.find((well) => well.well_id === selectedWellId);

  const data = [
    {
      type: "surface",
      x: gridX,
      y: gridY,
      z: scaledSurface,
      opacity: 0.96,
      showscale: false,
      colorscale: [
        [0, "#d8e6fb"],
        [0.2, "#a8c6f2"],
        [0.45, "#5d97df"],
        [0.72, "#0f6cbd"],
        [1, "#0b2547"],
      ],
      contours: {
        z: {
          show: true,
          usecolormap: false,
          color: "rgba(17,19,24,0.22)",
          width: 1,
        },
      },
      hovertemplate:
        "Progress %{x:.1f}%<br>Live delay %{y:.1f}d<br>Pressure %{z:.1f}<extra></extra>",
    },
    {
      type: "scatter3d",
      mode: "markers",
      x: spotlight.map((well) => well.current_progress_pct ?? 0),
      y: spotlight.map((well) => Math.max(well.baseline_delay_days ?? 0, 0)),
      z: spotlight.map((well) => well.decision_score ?? 0),
      text: spotlight.map(
        (well) =>
          `${well.well_name}<br>${well.recommended_action}<br>Recovery ${formatDays(Math.max(-(well.recommended_delta_days ?? 0), 0))}`,
      ),
      hovertemplate:
        "<b>%{text}</b><br>Progress %{x:.1f}%<br>Live delay %{y:.1f}d<br>Decision score %{z:.1f}<extra></extra>",
      marker: {
        size: markerSize.slice(0, spotlight.length),
        color: markerColor.slice(0, spotlight.length),
        opacity: 0.95,
        line: { color: "rgba(255,255,255,0.9)", width: 1.4 },
      },
    },
  ] as unknown as PlotParams["data"];

  if (selected) {
    data.push({
      type: "scatter3d",
      mode: "markers",
      x: [selected.current_progress_pct ?? 0],
      y: [Math.max(selected.baseline_delay_days ?? 0, 0)],
      z: [selected.decision_score ?? 0],
      marker: {
        size: 18,
        color: "#111318",
        line: { color: "#ffffff", width: 3 },
        symbol: "diamond",
      },
      hovertemplate:
        "<b>" +
        selected.well_name +
        "</b><br>Selected focus<br>Progress %{x:.1f}%<br>Live delay %{y:.1f}d<extra></extra>",
    } as unknown as PlotParams["data"][number]);
  }

  const layout = buildSceneLayout("Portfolio Pressure Map", {
    x: "Progress %",
    y: "Live delay days",
    z: "Pressure score",
  });
  if (layout?.scene) {
    (layout.scene as Plotly.Layout["scene"]).camera = {
      eye: { x: 1.72, y: 1.58, z: 0.9 },
    };
  }
  return {
    data: data as PlotParams["data"],
    layout,
    config: { displayModeBar: false, responsive: true },
  };
}

function buildScenarioFrontierFigure(
  well?: WellDecision,
  selectedScenarioId?: string | null,
): PlotFigure | null {
  if (!well?.scenarios.length) {
    return null;
  }

  const scenarios = [...well.scenarios].sort(
    (left, right) =>
      Math.max(-(right.delta_days ?? 0), 0) -
      Math.max(-(left.delta_days ?? 0), 0),
  );
  const baselineSupport = Math.max(
    ...scenarios.map((scenario) => scenario.support_cases || 0),
    1,
  );
  const selected =
    scenarios.find((scenario) => scenario.scenario === selectedScenarioId) ??
    scenarios[0];

  const recovery = scenarios.map((scenario) =>
    Math.max(-(scenario.delta_days ?? 0), 0),
  );
  const scenarioDelay = scenarios.map((scenario) =>
    Math.max(scenario.new_delay_days ?? 0, 0),
  );
  const support = scenarios.map((scenario) => scenario.support_cases ?? 0);
  const curtainX = [recovery, recovery];
  const curtainY = [
    scenarioDelay,
    Array(scenarios.length).fill(Math.max(well.baseline_delay_days ?? 0, 0)),
  ];
  const curtainZ = [
    support,
    Array(scenarios.length).fill(Math.max(baselineSupport * 0.25, 1)),
  ];
  const baselineLineX = [0, Math.max(...recovery, 1)];
  const baselineLineY = Array(2).fill(
    Math.max(well.baseline_delay_days ?? 0, 0),
  );
  const baselineLineZ = Array(2).fill(Math.max(baselineSupport * 0.25, 1));

  const layout = buildSceneLayout("Scenario Frontier", {
    x: "Recoverable days",
    y: "Scenario delay",
    z: "Support cases",
  });
  if (layout?.scene) {
    (layout.scene as Plotly.Layout["scene"]).camera = {
      eye: { x: 1.52, y: 1.48, z: 0.82 },
    };
  }

  return {
    data: [
      ...(scenarios.length >= 3
        ? ([
            {
              type: "surface",
              x: curtainX,
              y: curtainY,
              z: curtainZ,
              opacity: 0.88,
              showscale: false,
              colorscale: [
                [0, "#dce9fb"],
                [0.38, "#9fc1ee"],
                [0.72, "#4d91e8"],
                [1, "#173f73"],
              ],
              contours: {
                x: { show: true, color: "rgba(17,19,24,0.14)", width: 1 },
                y: { show: true, color: "rgba(17,19,24,0.14)", width: 1 },
                z: { show: true, color: "rgba(17,19,24,0.18)", width: 1 },
              },
              hoverinfo: "skip",
            },
          ] as unknown as PlotParams["data"])
        : []),
      {
        type: "scatter3d",
        mode: "lines",
        x: baselineLineX,
        y: baselineLineY,
        z: baselineLineZ,
        line: { color: "rgba(17,19,24,0.35)", width: 6 },
        hovertemplate: "<b>Baseline</b><br>Live delay %{y:.1f}d<extra></extra>",
      },
      {
        type: "scatter3d",
        mode: "markers",
        x: recovery,
        y: scenarioDelay,
        z: support,
        text: scenarios.map(
          (scenario) =>
            `${scenario.label}<br>Recovery ${formatDays(Math.max(-(scenario.delta_days ?? 0), 0))}<br>Support ${scenario.support_cases}`,
        ),
        hovertemplate:
          "<b>%{text}</b><br>Recovery %{x:.1f}d<br>Scenario delay %{y:.1f}d<br>Support %{z:.0f}<extra></extra>",
        marker: {
          size: scenarios.map(
            (scenario) => 10 + Math.min((scenario.support_cases ?? 0) / 8, 12),
          ),
          color: scenarios.map((scenario) =>
            scenario.scenario === selected.scenario ? "#111318" : "#0f6cbd",
          ),
          opacity: 0.95,
          line: { color: "#ffffff", width: 1.6 },
        },
      },
    ] as unknown as PlotParams["data"],
    layout,
    config: { displayModeBar: false, responsive: true },
  };
}

function buildDriverGeometryFigure(drivers: Driver[]): PlotFigure | null {
  const top = drivers.slice(0, 8);
  if (!top.length) {
    return null;
  }

  const x = top.map((driver) =>
    Math.abs(driver.unit_impact_days ?? driver.std_impact ?? 0),
  );
  const y = top.map((_driver, index) => top.length - index);
  const z = top.map((driver) => Math.abs(driver.ten_percent_impact_days ?? 0));
  const ridgeX = top.map((driver) => [
    0,
    Math.abs(driver.unit_impact_days ?? driver.std_impact ?? 0),
  ]);
  const ridgeY = top.map((_driver, index) => {
    const rank = top.length - index;
    return [rank, rank];
  });
  const ridgeZ = top.map((driver) => [
    0,
    Math.abs(driver.ten_percent_impact_days ?? 0),
  ]);

  const layout = buildSceneLayout("Driver Geometry", {
    x: "Unit delay effect",
    y: "Driver rank",
    z: "10% move effect",
  });
  if (layout?.scene) {
    const scene = layout.scene as Plotly.Layout["scene"];
    scene.camera = { eye: { x: 1.64, y: 1.35, z: 0.9 } };
    if (scene.yaxis) {
      scene.yaxis.tickvals = y;
      scene.yaxis.ticktext = top.map((driver) =>
        shortChartLabel(driver.feature || driver.label, 16),
      );
    }
  }

  return {
    data: [
      {
        type: "surface",
        x: ridgeX,
        y: ridgeY,
        z: ridgeZ,
        opacity: 0.96,
        showscale: false,
        colorscale: [
          [0, "#d8f5eb"],
          [0.3, "#8ce0c4"],
          [0.68, "#15b79e"],
          [1, "#0b5c52"],
        ],
        contours: {
          z: {
            show: true,
            color: "rgba(17,19,24,0.22)",
            width: 1,
          },
        },
        hoverinfo: "skip",
      },
      {
        type: "scatter3d",
        mode: "markers",
        x,
        y,
        z,
        text: top.map((driver) =>
          humanizeToken(driver.feature || driver.label),
        ),
        hovertemplate:
          "<b>%{text}</b><br>Unit effect %{x:.1f}d<br>10% move %{z:.1f}d<extra></extra>",
        marker: {
          size: top.map((_driver, index) => 12 - Math.min(index, 5)),
          color: "#10b981",
          opacity: 0.95,
          line: { color: "#ffffff", width: 1.6 },
        },
      },
    ] as unknown as PlotParams["data"],
    layout,
    config: { displayModeBar: false, responsive: true },
  };
}

function fallbackSourceTrace(
  label: string,
  note: string,
  asOf: string,
  kind: string = "model",
): SourceTrace {
  return {
    label,
    table: "CPU decision layer",
    column: "derived from live well deck",
    note,
    as_of: asOf,
    kind,
  };
}

function buildFallbackPortfolioBrief(
  wells: WellDecision[],
  asOf: string,
): PortfolioBrief {
  const ranked = [...wells].sort(
    (left, right) =>
      (right.decision_score ?? 0) - (left.decision_score ?? 0) ||
      (right.baseline_delay_days ?? 0) - (left.baseline_delay_days ?? 0),
  );
  const top = ranked[0];
  const actionable = ranked.filter((well) => well.action_status === "Act Now");
  const candidates = ranked.filter(
    (well) => well.action_status === "Candidate",
  );
  const blocked = ranked.filter((well) => well.confidence_label === "Low");
  const recoverable = ranked
    .slice(0, 10)
    .reduce(
      (sum, well) => sum + Math.max(-(well.recommended_delta_days ?? 0), 0),
      0,
    );

  return {
    as_of: asOf,
    management_message: top
      ? `${top.recommended_action} on ${top.well_name} is the current highest-value move, with ${formatDays(Math.max(-(top.recommended_delta_days ?? 0), 0))} of modeled recovery.`
      : "No decision-grade opportunity is available in the current deck.",
    attention_now: actionable.length,
    candidate_count: candidates.length,
    blocked_count: blocked.length,
    cards: [
      {
        label: "Actionable Wells",
        value: String(actionable.length),
        unit: "wells",
        accent: "green",
        source: fallbackSourceTrace(
          "Actionable Wells",
          "Count of wells with Act Now decision status in the live well deck.",
          asOf,
        ),
      },
      {
        label: "Recoverable Top 10",
        value: numberFormatter.format(recoverable),
        unit: "days",
        accent: "blue",
        source: fallbackSourceTrace(
          "Recoverable Top 10",
          "Sum of modeled recoverable days across the top ten ranked wells.",
          asOf,
        ),
      },
      {
        label: "Candidates",
        value: String(candidates.length),
        unit: "wells",
        accent: "amber",
        source: fallbackSourceTrace(
          "Candidates",
          "Count of wells with Candidate decision status in the live well deck.",
          asOf,
        ),
      },
      {
        label: "Weak Support",
        value: String(blocked.length),
        unit: "wells",
        accent: "red",
        source: fallbackSourceTrace(
          "Weak Support",
          "Count of wells where the current recommendation has low confidence.",
          asOf,
        ),
      },
    ],
    top_opportunity: top,
  };
}

function buildFallbackInterventionLadder(
  wells: WellDecision[],
  asOf: string,
): InterventionLadderItem[] {
  return [...wells]
    .sort(
      (left, right) =>
        (right.decision_score ?? 0) - (left.decision_score ?? 0) ||
        (right.baseline_delay_days ?? 0) - (left.baseline_delay_days ?? 0),
    )
    .slice(0, 20)
    .map((well, index) => ({
      rank: index + 1,
      well_id: well.well_id,
      well_name: well.well_name,
      cluster: well.cluster,
      rig_no: well.rig_no,
      well_type: well.well_type,
      action_label: well.recommended_action,
      recoverable_days: Math.max(-(well.recommended_delta_days ?? 0), 0),
      decision_score: well.decision_score,
      confidence_label: well.confidence_label,
      action_status: well.action_status,
      why_now: well.why_now,
      support_cases: well.scenario_support_cases,
      source: fallbackSourceTrace(
        "Intervention Opportunity",
        "Fallback ladder built from the live well decision deck.",
        asOf,
      ),
    }));
}

export default function CausalCommand() {
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedWellId, setSelectedWellId] = useState<string | null>(null);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(
    null,
  );
  const [viewMode, setViewMode] = useState<ViewMode>("command");
  const [commandText, setCommandText] = useState("");
  const [commandFeedback, setCommandFeedback] = useState(
    "Decision workspace is ready.",
  );

  const selectedWell = useMemo(
    () => selectedWellFromWorkspace(workspace, selectedWellId),
    [workspace, selectedWellId],
  );

  const selectedScenario = useMemo(() => {
    if (!selectedWell?.scenarios.length) {
      return undefined;
    }
    if (!selectedScenarioId) {
      return selectedWell.scenarios[0];
    }
    return (
      selectedWell.scenarios.find(
        (item) => item.scenario === selectedScenarioId,
      ) ?? selectedWell.scenarios[0]
    );
  }, [selectedWell, selectedScenarioId]);

  const scenarioTrace = useMemo(() => {
    if (!workspace?.interactive?.feature_lineage) {
      return [];
    }
    return buildScenarioTrace(
      selectedScenario,
      workspace.interactive.feature_lineage,
      workspace.interactive.portfolio_brief?.as_of ?? "n/a",
    );
  }, [selectedScenario, workspace]);

  useEffect(() => {
    if (!selectedWell?.scenarios.length) {
      setSelectedScenarioId(null);
      return;
    }
    const stillExists = selectedWell.scenarios.some(
      (scenario) => scenario.scenario === selectedScenarioId,
    );
    if (!selectedScenarioId || !stillExists) {
      setSelectedScenarioId(selectedWell.scenarios[0].scenario);
    }
  }, [selectedScenarioId, selectedWell]);

  useEffect(() => {
    let cancelled = false;

    const loadWorkspace = async (silent = false) => {
      if (!silent) {
        setLoading(true);
      }
      setError(null);
      const primary = getCausalEndpoint();
      const endpoints =
        primary === "/api/causal" ? [primary] : [primary, "/api/causal"];
      let lastError = "Failed to load Causal Command.";

      for (const endpoint of endpoints) {
        try {
          const response = await fetchWithTimeout(endpoint, 180000);
          if (!response.ok) {
            lastError = `Backend error: ${response.status}`;
            continue;
          }
          const data = (await response.json()) as WorkspaceResponse;
          if (cancelled) {
            return;
          }
          setWorkspace(data);
          setCommandFeedback(
            data.analysis_status?.detail ?? "Operational deck received.",
          );
          setSelectedWellId((current) => {
            const nextWell =
              selectedWellFromWorkspace(data, current)?.well_id ??
              data.interactive?.portfolio_brief?.top_opportunity?.well_id ??
              data.interactive?.wells?.[0]?.well_id ??
              null;
            return nextWell;
          });
          return;
        } catch (fetchError) {
          if (fetchError instanceof Error) {
            lastError = fetchError.message;
          }
        }
      }

      if (!cancelled) {
        setError(lastError);
      }
    };

    void loadWorkspace();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!workspace?.analysis_status.refresh_in_progress) {
      return;
    }

    const interval = window.setInterval(async () => {
      const primary = getCausalEndpoint();
      const endpoints =
        primary === "/api/causal" ? [primary] : [primary, "/api/causal"];

      for (const endpoint of endpoints) {
        try {
          const response = await fetchWithTimeout(endpoint, 30000);
          if (!response.ok) {
            continue;
          }
          const data = (await response.json()) as WorkspaceResponse;
          setWorkspace(data);
          return;
        } catch {
          continue;
        }
      }
    }, 15000);

    return () => window.clearInterval(interval);
  }, [workspace?.analysis_status.refresh_in_progress]);

  useEffect(() => {
    if (!loading) {
      return;
    }
    if (workspace || error) {
      setLoading(false);
    }
  }, [error, loading, workspace]);

  const runCommand = (rawInput?: string) => {
    const input = (rawInput ?? commandText).trim().toLowerCase();
    if (!workspace?.interactive || !input) {
      return;
    }

    const wells = workspace.interactive.wells ?? [];
    const ladder = workspace.interactive.intervention_ladder ?? [];
    let targetWell: WellDecision | undefined;

    if (
      input.includes("system view") ||
      input.includes("supporting detail") ||
      input.includes("methodology")
    ) {
      setViewMode("model");
      setCommandFeedback("Opened system view for model state and coverage.");
      return;
    }

    if (
      input.includes("source") ||
      input.includes("evidence") ||
      input.includes("support")
    ) {
      setViewMode("evidence");
      setCommandFeedback("Opened support trace for the selected opportunity.");
      return;
    }

    if (input.includes("best action") || input.includes("highest delay")) {
      targetWell =
        workspace.interactive.portfolio_brief?.top_opportunity ?? wells[0];
    } else if (input.includes("act now")) {
      targetWell = wells.find((well) => well.action_status === "Act Now");
    } else if (input.includes("weak support") || input.includes("blocked")) {
      targetWell = wells.find((well) => well.confidence_label === "Low");
    } else {
      targetWell =
        (wells.find((well) => {
          const haystack = [
            well.well_id,
            well.well_name,
            well.cluster,
            well.rig_no,
            well.well_type,
          ]
            .join(" ")
            .toLowerCase();
          return haystack.includes(input);
        }) ??
        ladder.find((item) =>
          [item.well_id, item.well_name, item.cluster, item.rig_no]
            .join(" ")
            .toLowerCase()
            .includes(input),
        ))
          ? wells.find((well) =>
              [well.well_id, well.well_name, well.cluster, well.rig_no]
                .join(" ")
                .toLowerCase()
                .includes(input),
            )
          : undefined;
    }

    if (!targetWell) {
      setCommandFeedback(
        "No decision object matched that command. Try a well name, cluster, or a quick action chip.",
      );
      return;
    }

    setSelectedWellId(targetWell.well_id);
    setViewMode("command");
    setCommandFeedback(
      `Focused ${targetWell.well_name}. ${targetWell.recommended_action} remains the current lead action with ${targetWell.scenario_support_cases} support cases.`,
    );
  };

  const interactive = workspace?.interactive as MinimalInteractive | undefined;
  const fallbackAsOf = workspace?.generated_at ?? new Date().toISOString();
  const derivedBrief =
    interactive?.portfolio_brief ??
    buildFallbackPortfolioBrief(interactive?.wells ?? [], fallbackAsOf);
  const derivedLadder =
    interactive?.intervention_ladder ??
    buildFallbackInterventionLadder(interactive?.wells ?? [], fallbackAsOf);
  const isWorkspaceWarm =
    !!workspace &&
    !!interactive &&
    Array.isArray(interactive.wells) &&
    interactive.wells.length > 0;

  if ((loading && !workspace) || (!!workspace && !isWorkspaceWarm && !error)) {
    return (
      <div className="causal-shell">
        <div className="causal-loading-card">
          <div className="loading-spinner" />
          <p className="eyebrow">Causal Command</p>
          <h2>Preparing decision workspace</h2>
          <p className="subtle">Loading the current management view.</p>
          {workspace?.analysis_status?.detail ? (
            <p className="subtle loading-detail">
              {statusSummary(workspace.analysis_status)}
            </p>
          ) : null}
        </div>
        <style jsx>{styles}</style>
      </div>
    );
  }

  if (error || !workspace || !interactive || !selectedWell) {
    return (
      <div className="causal-shell">
        <div className="causal-error-card">
          <p className="eyebrow">Causal Command</p>
          <h2>Decision workspace unavailable</h2>
          <p className="subtle">
            {error ?? "No data returned from the backend."}
          </p>
        </div>
        <style jsx>{styles}</style>
      </div>
    );
  }

  const brief = derivedBrief;
  const ladder = derivedLadder;
  const top_drivers = interactive.top_drivers ?? [];
  const analysis_basis = interactive.analysis_basis ?? {
    engine: "n/a",
    mode: "n/a",
    rows: 0,
    features: 0,
    r2: 0,
    rmse: 0,
    support_cases: {},
    posterior_status: "pending",
  };
  const portfolioFigure = buildPortfolioPressureFigure(
    interactive.wells ?? [],
    selectedWell.well_id,
  );
  const scenarioFigure = buildScenarioFrontierFigure(
    selectedWell,
    selectedScenario?.scenario,
  );
  const driverFigure = buildDriverGeometryFigure(top_drivers);
  const rootCausePreview = selectedWell.root_causes.slice(0, 3);
  const spotlightWells = [...(interactive.wells ?? [])]
    .sort(
      (left, right) =>
        (right.decision_score ?? 0) - (left.decision_score ?? 0) ||
        (right.baseline_delay_days ?? 0) - (left.baseline_delay_days ?? 0),
    )
    .slice(0, 6);
  const driverRail = top_drivers.slice(0, 8);
  return (
    <div className="causal-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <div className="hero-kicker">
            <p className="eyebrow">Causal Command</p>
            <span className="hero-kicker-line" />
            <p className="hero-tag">Management Decision Surface</p>
          </div>
          <h1>{workspace.workspace_name}</h1>
          <p className="hero-objective">{workspace.objective}</p>
          <div className="hero-meta">
            <div>
              <span className="meta-label">Generated</span>
              <strong>{formatDateTime(workspace.generated_at)}</strong>
            </div>
            <div>
              <span className="meta-label">Cache age</span>
              <strong>{workspace.analysis_status.cache_age_seconds}s</strong>
            </div>
            <div>
              <span className="meta-label">Live target</span>
              <strong>{humanizeToken(workspace.target)}</strong>
            </div>
          </div>
          <div className="status-ribbon">
            <span
              className={`status-pill ${workspace.analysis_status.mode === "cpu_plus_bayesian" ? "status-good" : "status-warming"}`}
            >
              {primaryStatusLabel(workspace.analysis_status)}
            </span>
            <span
              className={`status-pill ${workspace.analysis_status.refresh_in_progress ? "status-warming" : "status-neutral"}`}
            >
              {secondaryStatusLabel(workspace.analysis_status)}
            </span>
          </div>
        </div>

        <div className="hero-brief">
          <div className="decision-call-card">
            <p className="eyebrow">Portfolio brief</p>
            <h3>{brief.management_message}</h3>
          </div>

          <div className="brief-grid">
            {brief.cards.map((card) => (
              <div
                key={card.label}
                className={`brief-card ${accentClass(card.accent)}`}
              >
                <span className="brief-label">{card.label}</span>
                <strong>
                  {card.value}
                  {card.unit ? (
                    <span className="brief-unit"> {card.unit}</span>
                  ) : null}
                </strong>
                <span className="trace-chip">
                  {kindLabel(card.source.kind)} | {card.source.table}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="command-panel">
        <div className="command-input-wrap">
          <p className="eyebrow">Command bar</p>
          <div className="command-row">
            <input
              className="command-input"
              value={commandText}
              onChange={(event) => setCommandText(event.target.value)}
              placeholder='Try "highest delay well", "Marmul", or a well id'
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  runCommand();
                }
              }}
            />
            <button className="primary-button" onClick={() => runCommand()}>
              Run command
            </button>
          </div>
          <div className="chip-row">
            {QUICK_COMMANDS.map((chip) => (
              <button
                key={chip}
                className="quick-chip"
                onClick={() => {
                  setCommandText(chip);
                  runCommand(chip);
                }}
              >
                {chip}
              </button>
            ))}
          </div>
          <p className="command-feedback">{commandFeedback}</p>
        </div>

        <div className="view-toggle-shell">
          <p className="eyebrow">View</p>
          <div className="view-toggle">
            {(["command", "evidence", "model"] as ViewMode[]).map((mode) => (
              <button
                key={mode}
                className={`toggle-pill ${viewMode === mode ? "toggle-active" : ""}`}
                onClick={() => setViewMode(mode)}
              >
                {tabLabel(mode)}
              </button>
            ))}
          </div>
        </div>
      </section>

      {viewMode === "command" ? (
        <section className="execution-grid">
          <aside className="ladder-panel">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Intervention ladder</p>
                <h3>Priority book</h3>
              </div>
              <span className="panel-meta">
                {ladder.length} decision objects
              </span>
            </div>
            <div className="ladder-list">
              {ladder.map((item) => {
                const isActive = item.well_id === selectedWell.well_id;
                return (
                  <button
                    key={`${item.rank}-${item.well_id}`}
                    className={`ladder-item ${isActive ? "ladder-item-active" : ""}`}
                    onClick={() => {
                      setSelectedWellId(item.well_id);
                      setViewMode("command");
                    }}
                  >
                    <div className="ladder-top">
                      <span className="ladder-rank">Rank {item.rank}</span>
                      <strong className="ladder-recovery">
                        {formatDays(item.recoverable_days)}
                      </strong>
                    </div>
                    <h4>{item.well_name}</h4>
                    <p className="ladder-meta">
                      {item.rig_no} | {item.cluster} | {item.well_type || "n/a"}
                    </p>
                    <p className="ladder-action">{item.action_label}</p>
                    <div className="ladder-badges">
                      <span
                        className={`mini-badge badge-${item.action_status.toLowerCase().replaceAll(" ", "-")}`}
                      >
                        {item.action_status}
                      </span>
                      <span className="mini-badge badge-neutral">
                        {item.confidence_label}
                      </span>
                    </div>
                    <p className="ladder-why">{item.why_now}</p>
                  </button>
                );
              })}
            </div>
          </aside>

          <div className="command-stage">
            <section className="decision-memo panel">
              <div className="panel-head">
                <div>
                  <p className="eyebrow">Selected well</p>
                  <h2>{selectedWell.well_name}</h2>
                  <p className="memo-subtitle">
                    ID {selectedWell.well_id} | {selectedWell.rig_no} |{" "}
                    {selectedWell.cluster} | {selectedWell.well_type || "n/a"}
                  </p>
                </div>
                <div className="memo-badges">
                  <span
                    className={`status-pill status-${selectedWell.action_status.toLowerCase().replaceAll(" ", "-")}`}
                  >
                    {selectedWell.action_status}
                  </span>
                  <span className="status-pill status-neutral">
                    {selectedWell.confidence_label}
                  </span>
                  <span className="status-pill status-neutral">
                    {selectedWell.signal_quality} signal
                  </span>
                </div>
              </div>

              <div className="metric-grid command-metric-grid">
                <div className="metric-card metric-red">
                  <span>Live delay</span>
                  <strong>
                    {formatDays(selectedWell.baseline_delay_days)}
                  </strong>
                  <small>Current schedule pressure</small>
                </div>
                <div className="metric-card metric-blue">
                  <span>Decision score</span>
                  <strong>
                    {numberFormatter.format(selectedWell.decision_score)}
                  </strong>
                  <small>Ranking strength on the deck</small>
                </div>
                <div className="metric-card metric-green">
                  <span>Current progress</span>
                  <strong>
                    {formatPct(selectedWell.current_progress_pct)}
                  </strong>
                  <small>Live position on the well</small>
                </div>
                <div className="metric-card metric-gold">
                  <span>Best recovery</span>
                  <strong>
                    {formatDays(
                      Math.max(-selectedWell.recommended_delta_days, 0),
                    )}
                  </strong>
                  <small>
                    {selectedWell.scenario_support_cases} support cases
                  </small>
                </div>
                <div className="metric-card metric-dark">
                  <span>Lead action</span>
                  <strong>{selectedWell.recommended_action}</strong>
                  <small>{selectedWell.recommendation}</small>
                </div>
                <div className="metric-card metric-slate">
                  <span>Primary issue</span>
                  <strong>{selectedWell.primary_issue}</strong>
                  <small>{selectedWell.why_now}</small>
                </div>
              </div>

              <div className="signal-ribbon">
                {rootCausePreview.map((cause) => (
                  <div key={cause.feature} className="signal-chip-card">
                    <span className="signal-chip-label">{cause.label}</span>
                    <strong>
                      {numberFormatter.format(cause.contribution_score)}
                    </strong>
                    <small>{cause.source.table}</small>
                  </div>
                ))}
              </div>
            </section>

            <section className="quant-grid">
              <div className="surface-panel panel">
                <div className="panel-head compact-head">
                  <div>
                    <p className="eyebrow">3D pressure surface</p>
                    <h3>Portfolio pressure map</h3>
                  </div>
                  <span className="panel-meta">
                    Top {Math.min((interactive.wells ?? []).length, 40)} wells
                  </span>
                </div>
                {portfolioFigure ? (
                  <div className="surface-body">
                    <div className="plot-frame">
                      <Plot
                        data={portfolioFigure.data}
                        layout={portfolioFigure.layout}
                        config={portfolioFigure.config}
                        style={{ width: "100%", height: "100%" }}
                      />
                    </div>
                    <div className="surface-rail">
                      <p className="surface-rail-title">Pressure board</p>
                      {spotlightWells.slice(0, 6).map((well) => (
                        <div key={well.well_id} className="surface-rail-row">
                          <div>
                            <strong>{well.well_name}</strong>
                            <small>{well.recommended_action}</small>
                          </div>
                          <div className="surface-rail-metric">
                            <span>{formatDays(well.baseline_delay_days)}</span>
                            <small>
                              {numberFormatter.format(well.decision_score)}
                            </small>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="plot-empty">
                    No portfolio surface available.
                  </div>
                )}
              </div>

              <div className="surface-panel panel">
                <div className="panel-head compact-head">
                  <div>
                    <p className="eyebrow">3D scenario surface</p>
                    <h3>Scenario frontier</h3>
                  </div>
                  <span className="panel-meta">
                    {selectedWell.scenarios.length} actions
                  </span>
                </div>
                {scenarioFigure ? (
                  <div className="surface-body">
                    <div className="plot-frame">
                      <Plot
                        data={scenarioFigure.data}
                        layout={scenarioFigure.layout}
                        config={scenarioFigure.config}
                        style={{ width: "100%", height: "100%" }}
                      />
                    </div>
                    <div className="surface-rail">
                      <p className="surface-rail-title">Scenario sheet</p>
                      {selectedWell.scenarios.slice(0, 6).map((scenario) => {
                        const isActive =
                          selectedScenario?.scenario === scenario.scenario;
                        return (
                          <div
                            key={scenario.scenario}
                            className={`surface-rail-row ${isActive ? "surface-rail-row-active" : ""}`}
                          >
                            <div>
                              <strong>{scenario.label}</strong>
                              <small>{scenario.support_cases} cases</small>
                            </div>
                            <div className="surface-rail-metric">
                              <span>
                                {formatDays(
                                  Math.max(-(scenario.delta_days ?? 0), 0),
                                )}
                              </span>
                              <small>
                                {formatDays(scenario.new_delay_days)}
                              </small>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="plot-empty">
                    No scenario frontier available.
                  </div>
                )}
              </div>

              <div className="surface-panel panel surface-panel-wide">
                <div className="panel-head compact-head">
                  <div>
                    <p className="eyebrow">3D driver geometry</p>
                    <h3>Driver geometry</h3>
                  </div>
                  <span className="panel-meta">
                    {Math.min(top_drivers.length, 8)} signals
                  </span>
                </div>
                {driverFigure ? (
                  <div className="surface-body surface-body-wide">
                    <div className="plot-frame plot-frame-wide">
                      <Plot
                        data={driverFigure.data}
                        layout={driverFigure.layout}
                        config={driverFigure.config}
                        style={{ width: "100%", height: "100%" }}
                      />
                    </div>
                    <div className="surface-rail surface-rail-wide">
                      <p className="surface-rail-title">Signal ladder</p>
                      {driverRail.slice(0, 6).map((driver, index) => (
                        <div key={driver.feature} className="surface-rail-row">
                          <div>
                            <strong>
                              {index + 1}.{" "}
                              {humanizeToken(driver.feature || driver.label)}
                            </strong>
                            <small>{driver.source?.table ?? "Model"}</small>
                          </div>
                          <div className="surface-rail-metric">
                            <span>
                              {formatDays(
                                Math.abs(
                                  driver.unit_impact_days ??
                                    driver.std_impact ??
                                    0,
                                ),
                              )}
                            </span>
                            <small>
                              {formatDays(
                                Math.abs(driver.ten_percent_impact_days ?? 0),
                              )}
                            </small>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="plot-empty">
                    No driver geometry available.
                  </div>
                )}
              </div>
            </section>

            <section className="panel scenario-panel">
              <div className="panel-head">
                <div>
                  <p className="eyebrow">Action book</p>
                  <h3>Governed scenario deck</h3>
                </div>
                <span className="panel-meta">
                  {selectedWell.scenarios.length} supported actions
                </span>
              </div>
              <div className="scenario-table">
                <div className="scenario-table-head">
                  <span>Scenario</span>
                  <span>Baseline</span>
                  <span>Scenario</span>
                  <span>Delta</span>
                  <span>Support</span>
                </div>
                {selectedWell.scenarios.map((scenario) => {
                  const isActive =
                    selectedScenario?.scenario === scenario.scenario;
                  return (
                    <button
                      key={scenario.scenario}
                      className={`scenario-row ${isActive ? "scenario-row-active" : ""}`}
                      onClick={() => setSelectedScenarioId(scenario.scenario)}
                    >
                      <div className="scenario-primary">
                        <strong>{scenario.label}</strong>
                        <small>
                          {shortChartLabel(
                            scenario.description || scenario.assumption_note,
                            92,
                          )}
                        </small>
                      </div>
                      <div className="scenario-metric">
                        <strong>
                          {formatDays(scenario.baseline_delay_days)}
                        </strong>
                      </div>
                      <div className="scenario-metric">
                        <strong>{formatDays(scenario.new_delay_days)}</strong>
                      </div>
                      <div className="scenario-metric">
                        <strong
                          className={
                            scenario.delta_days < 0
                              ? "delta-good"
                              : "delta-flat"
                          }
                        >
                          {formatDays(scenario.delta_days)}
                        </strong>
                      </div>
                      <div className="scenario-metric">
                        <strong>{scenario.support_cases}</strong>
                      </div>
                    </button>
                  );
                })}
              </div>
              {selectedScenario ? (
                <div className="scenario-footnote scenario-footnote-compact">
                  <span className="scenario-note-kicker">
                    Selected action note
                  </span>
                  <strong>{selectedScenario.label}</strong>
                  <p>
                    {shortChartLabel(selectedScenario.assumption_note, 180)}
                  </p>
                </div>
              ) : null}
            </section>
          </div>
        </section>
      ) : null}

      {viewMode === "evidence" ? (
        <section className="evidence-grid">
          <div className="panel">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Support trace</p>
                <h3>Visible facts and support items</h3>
              </div>
              <span className="panel-meta">
                {selectedWell.source_trace.length + scenarioTrace.length} trace
                items
              </span>
            </div>
            <div className="trace-list">
              {[...selectedWell.source_trace, ...scenarioTrace].map(
                (trace, index) => (
                  <div key={`${trace.label}-${index}`} className="trace-row">
                    <div className="trace-head">
                      <strong>{trace.label}</strong>
                      <span className={`trace-kind trace-kind-${trace.kind}`}>
                        {kindLabel(trace.kind)}
                      </span>
                    </div>
                    <p className="trace-meta">
                      {trace.table} | {trace.column} | as of {trace.as_of}
                    </p>
                    <p>{trace.note}</p>
                  </div>
                ),
              )}
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Root-cause stack</p>
                <h3>Highest-contribution live signals</h3>
              </div>
              <span className="panel-meta">
                {selectedWell.root_causes.length} ranked contributors
              </span>
            </div>
            <div className="root-list">
              {selectedWell.root_causes.map((cause) => (
                <div key={cause.feature} className="root-card">
                  <div className="root-top">
                    <strong>{cause.label}</strong>
                    <span>
                      {numberFormatter.format(cause.contribution_score)}
                    </span>
                  </div>
                  <p>{cause.source.meaning}</p>
                  <small>
                    {cause.source.table} | {cause.source.column}
                  </small>
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {viewMode === "model" ? (
        <section className="model-grid">
          <div className="panel">
            <div className="panel-head">
              <div>
                <p className="eyebrow">System view</p>
                <h3>Decision basis</h3>
              </div>
            </div>
            <div className="basis-grid">
              <div className="basis-card">
                <span>Decision engine</span>
                <strong>{humanizeToken(analysis_basis.engine)}</strong>
              </div>
              <div className="basis-card">
                <span>Wells in scope</span>
                <strong>{numberFormatter.format(analysis_basis.rows)}</strong>
              </div>
              <div className="basis-card">
                <span>Signals in use</span>
                <strong>
                  {numberFormatter.format(analysis_basis.features)}
                </strong>
              </div>
              <div className="basis-card">
                <span>Typical error</span>
                <strong>{formatDays(analysis_basis.rmse)}</strong>
              </div>
            </div>
            <p className="model-summary">
              This view shows the operating basis behind the current decision
              deck. Detailed lineage stays in Support.
            </p>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Lead signals</p>
                <h3>Portfolio pressure signals</h3>
              </div>
            </div>
            <div className="driver-list">
              {top_drivers.slice(0, 6).map((driver) => (
                <div key={driver.feature} className="driver-card">
                  <div className="driver-top">
                    <strong>
                      {humanizeToken(driver.feature || driver.label)}
                    </strong>
                    <span>
                      {formatDays(
                        driver.unit_impact_days ?? driver.std_impact ?? 0,
                      )}
                    </span>
                  </div>
                  <p>
                    Estimated delay effect for a standard move:{" "}
                    {formatDays(driver.ten_percent_impact_days ?? 0)}
                  </p>
                  <small>Detailed source available in Support</small>
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <style jsx>{styles}</style>
    </div>
  );
}

const styles = `
  .causal-shell {
    width: 100%;
    height: 100%;
    padding: 28px;
    overflow-y: auto;
    box-sizing: border-box;
    font-size: 78%;
    background:
      linear-gradient(rgba(17, 19, 24, 0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(17, 19, 24, 0.04) 1px, transparent 1px),
      radial-gradient(circle at top left, rgba(62, 102, 255, 0.08), transparent 24%),
      radial-gradient(circle at top right, rgba(9, 178, 109, 0.05), transparent 22%),
      #f6f4ee;
    background-size: 28px 28px, 28px 28px, auto, auto, auto;
    color: #111318;
  }

  .hero-panel,
  .command-panel,
  .panel,
  .causal-loading-card,
  .causal-error-card {
    border: 1px solid rgba(17, 19, 24, 0.08);
    background: rgba(255, 255, 255, 0.88);
    backdrop-filter: blur(18px);
    box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
  }

  .hero-panel {
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(360px, 0.95fr);
    gap: 20px;
    padding: 24px;
    border-radius: 24px;
  }

  .hero-kicker {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 6px;
  }

  .hero-kicker-line {
    width: 48px;
    height: 1px;
    background: rgba(17, 19, 24, 0.18);
  }

  .hero-tag {
    margin: 0;
    color: rgba(17, 19, 24, 0.54);
    font-size: 0.84rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .hero-copy h1 {
    margin: 6px 0 10px;
    font-size: clamp(1.9rem, 3.4vw, 3.1rem);
    line-height: 0.98;
    letter-spacing: -0.05em;
  }

  .hero-objective {
    max-width: 760px;
    margin: 0 0 14px;
    font-size: 0.92rem;
    line-height: 1.5;
    color: rgba(17, 19, 24, 0.78);
  }

  .eyebrow {
    margin: 0 0 6px;
    font-size: 0.68rem;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: rgba(17, 19, 24, 0.56);
  }

  .hero-meta {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin: 0 0 14px;
  }

  .hero-meta > div {
    min-width: 140px;
    padding: 12px 14px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(17, 19, 24, 0.06);
  }

  .meta-label {
    display: block;
    margin-bottom: 4px;
    font-size: 0.66rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: rgba(17, 19, 24, 0.45);
  }

  .status-ribbon {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 600;
    border: 1px solid rgba(17, 19, 24, 0.08);
    background: #ffffff;
  }

  .status-good {
    color: #066c43;
    border-color: rgba(6, 108, 67, 0.18);
    background: rgba(9, 178, 109, 0.1);
  }

  .status-warming {
    color: #7a4c00;
    border-color: rgba(223, 162, 18, 0.22);
    background: rgba(252, 195, 46, 0.14);
  }

  .status-neutral {
    color: #0f172a;
    background: rgba(15, 23, 42, 0.04);
  }

  .status-act-now,
  .badge-act-now {
    color: #7f1d1d;
    background: rgba(220, 38, 38, 0.12);
    border-color: rgba(220, 38, 38, 0.2);
  }

  .status-candidate,
  .badge-candidate {
    color: #1d4ed8;
    background: rgba(37, 99, 235, 0.1);
    border-color: rgba(37, 99, 235, 0.18);
  }

  .status-observe,
  .badge-observe {
    color: #475569;
    background: rgba(71, 85, 105, 0.08);
    border-color: rgba(71, 85, 105, 0.16);
  }

  .hero-brief {
    display: grid;
    gap: 12px;
  }

  .decision-call-card {
    padding: 18px;
    border-radius: 20px;
    background: linear-gradient(145deg, rgba(17, 19, 24, 0.98), rgba(24, 31, 46, 0.94));
    color: #f8fafc;
  }

  .decision-call-card .eyebrow,
  .decision-call-card .subtle {
    color: rgba(248, 250, 252, 0.7);
  }

  .decision-call-card h3 {
    margin: 0;
    font-size: 1.05rem;
    line-height: 1.4;
    letter-spacing: -0.02em;
  }

  .subtle {
    color: rgba(17, 19, 24, 0.62);
  }

  .brief-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .brief-card {
    padding: 14px;
    border-radius: 16px;
    border: 1px solid rgba(17, 19, 24, 0.08);
    background: #ffffff;
  }

  .brief-label {
    display: block;
    margin-bottom: 6px;
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: rgba(17, 19, 24, 0.52);
  }

  .brief-card strong {
    display: block;
    font-size: 1.22rem;
    letter-spacing: -0.04em;
  }

  .brief-unit {
    font-size: 0.82rem;
    letter-spacing: 0;
    color: rgba(17, 19, 24, 0.58);
  }

  .trace-chip {
    display: none;
    margin-top: 10px;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(17, 19, 24, 0.05);
    font-size: 0.78rem;
    color: rgba(17, 19, 24, 0.66);
  }

  .accent-green {
    box-shadow: inset 0 0 0 1px rgba(9, 178, 109, 0.15);
  }

  .accent-red {
    box-shadow: inset 0 0 0 1px rgba(220, 38, 38, 0.15);
  }

  .accent-blue {
    box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.15);
  }

  .accent-amber {
    box-shadow: inset 0 0 0 1px rgba(217, 119, 6, 0.15);
  }

  .command-panel {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 18px;
    margin-top: 20px;
    padding: 18px;
    border-radius: 20px;
    align-items: end;
  }

  .command-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
  }

  .command-input {
    width: 100%;
    height: 48px;
    border-radius: 14px;
    border: 1px solid rgba(17, 19, 24, 0.1);
    padding: 0 14px;
    font-size: 0.9rem;
    background: #ffffff;
    color: #111318;
  }

  .primary-button,
  .quick-chip,
  .toggle-pill,
  .ladder-item,
  .scenario-row {
    transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
  }

  .primary-button {
    height: 48px;
    padding: 0 18px;
    border-radius: 14px;
    border: 0;
    background: #111318;
    color: #ffffff;
    font-size: 0.88rem;
    font-weight: 700;
    cursor: pointer;
  }

  .primary-button:hover,
  .quick-chip:hover,
  .toggle-pill:hover,
  .ladder-item:hover,
  .scenario-row:hover {
    transform: translateY(-1px);
  }

  .chip-row,
  .view-toggle,
  .ladder-badges,
  .memo-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .view-toggle-shell {
    display: grid;
    gap: 10px;
    justify-items: end;
  }

  .quick-chip,
  .toggle-pill {
    padding: 8px 12px;
    border-radius: 999px;
    border: 1px solid rgba(17, 19, 24, 0.1);
    background: #ffffff;
    color: #111318;
    cursor: pointer;
    font-size: 0.8rem;
  }

  .toggle-active {
    background: #111318;
    color: #ffffff;
    border-color: #111318;
  }

  .command-feedback {
    margin: 10px 0 0;
    color: rgba(17, 19, 24, 0.7);
    font-size: 0.84rem;
  }

  .execution-grid,
  .evidence-grid,
  .model-grid {
    display: grid;
    gap: 16px;
    margin-top: 16px;
  }

  .execution-grid {
    grid-template-columns: minmax(320px, 0.9fr) minmax(0, 1.6fr);
    align-items: start;
  }

  .command-stage {
    display: grid;
    gap: 16px;
  }

  .evidence-grid,
  .model-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .panel {
    padding: 18px;
    border-radius: 20px;
  }

  .panel-head {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: flex-start;
    margin-bottom: 14px;
  }

  .panel-head h2,
  .panel-head h3 {
    margin: 0;
    letter-spacing: -0.03em;
  }

  .ladder-panel {
    position: sticky;
    top: 16px;
    align-self: start;
  }

  .panel-meta {
    color: rgba(17, 19, 24, 0.56);
    font-size: 0.8rem;
  }

  .model-summary {
    margin: 14px 0 0;
    color: rgba(17, 19, 24, 0.62);
    line-height: 1.55;
  }

  .ladder-list,
  .trace-list,
  .driver-list,
  .lineage-list,
  .coverage-list,
  .gap-list {
    display: grid;
    gap: 10px;
  }

  .ladder-item,
  .root-card,
  .trace-row,
  .driver-card,
  .lineage-row,
  .gap-row {
    width: 100%;
    text-align: left;
    border-radius: 16px;
    border: 1px solid rgba(17, 19, 24, 0.08);
    background: #ffffff;
    padding: 12px;
  }

  .ladder-item {
    cursor: pointer;
    position: relative;
    overflow: hidden;
  }

  .ladder-item-active {
    background: linear-gradient(180deg, rgba(17, 19, 24, 0.98), rgba(17, 19, 24, 0.92));
    color: #ffffff;
    box-shadow: 0 20px 34px rgba(15, 23, 42, 0.22);
  }

  .ladder-item-active .ladder-meta,
  .ladder-item-active .ladder-action,
  .ladder-item-active .ladder-why,
  .ladder-item-active .ladder-rank {
    color: rgba(248, 250, 252, 0.76);
  }

  .ladder-top,
  .root-top,
  .driver-top,
  .trace-head,
  .coverage-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
  }

  .ladder-rank {
    font-size: 0.75rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: rgba(17, 19, 24, 0.5);
  }

  .ladder-recovery,
  .delta-good {
    color: #059669;
  }

  .ladder-item h4 {
    margin: 8px 0 6px;
    font-size: 1rem;
    letter-spacing: -0.03em;
  }

  .ladder-meta,
  .ladder-action,
  .ladder-why,
  .memo-subtitle,
  .trace-meta {
    color: rgba(17, 19, 24, 0.62);
  }

  .ladder-action {
    margin: 8px 0 0;
    padding: 8px 10px;
    border-radius: 12px;
    background: rgba(17, 19, 24, 0.04);
    font-weight: 600;
    color: #111318;
  }

  .ladder-item-active .ladder-action {
    background: rgba(248, 250, 252, 0.08);
    color: #f8fafc;
  }

  .ladder-why {
    margin-top: 10px;
    line-height: 1.45;
    font-size: 0.84rem;
  }

  .mini-badge {
    display: inline-flex;
    padding: 5px 8px;
    border-radius: 999px;
    border: 1px solid rgba(17, 19, 24, 0.08);
    font-size: 0.68rem;
    font-weight: 600;
  }

  .badge-neutral {
    color: #475569;
    background: rgba(71, 85, 105, 0.08);
    border-color: rgba(71, 85, 105, 0.14);
  }

  .memo-column {
    display: grid;
    gap: 16px;
  }

  .quant-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .surface-panel-wide {
    grid-column: 1 / -1;
  }

  .compact-head {
    margin-bottom: 10px;
  }

  .surface-body {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    align-items: stretch;
  }

  .surface-body-wide {
    grid-template-columns: 1fr;
  }

  .surface-rail {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    align-content: start;
    gap: 8px;
  }

  .surface-rail-wide {
    max-height: none;
    overflow: visible;
  }

  .surface-rail-title {
    display: none;
  }

  .surface-rail-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    align-items: start;
    min-height: 84px;
    padding: 10px 11px;
    border-radius: 12px;
    border: 1px solid rgba(17, 19, 24, 0.08);
    background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98));
    box-shadow: 0 10px 18px rgba(15, 23, 42, 0.03);
  }

  .surface-rail-row-active {
    border-color: rgba(15, 108, 189, 0.25);
    box-shadow:
      inset 0 0 0 1px rgba(15, 108, 189, 0.12),
      0 12px 24px rgba(37, 99, 235, 0.08);
  }

  .surface-rail-row strong {
    display: block;
    font-size: 0.8rem;
    line-height: 1.24;
    letter-spacing: -0.01em;
  }

  .surface-rail-row small {
    display: block;
    margin-top: 5px;
    color: rgba(17, 19, 24, 0.54);
    line-height: 1.28;
    font-size: 0.73rem;
  }

  .surface-rail-metric {
    text-align: right;
  }

  .surface-rail-metric span {
    display: block;
    font-weight: 700;
    font-size: 0.86rem;
    letter-spacing: -0.02em;
  }

   .surface-rail-metric small {
    margin-top: 2px;
   }

  .decision-memo {
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(247, 249, 252, 0.98)),
      #ffffff;
  }

  .plot-frame,
  .plot-frame-wide {
    min-height: 340px;
    border-radius: 18px;
    border: 1px solid rgba(17, 19, 24, 0.07);
    background:
      radial-gradient(circle at top, rgba(255,255,255,0.98), rgba(241,244,248,0.92)),
      #ffffff;
    overflow: hidden;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
  }

  .plot-frame-wide {
    min-height: 390px;
  }

  .plot-empty,
  .plot-loading {
    min-height: 280px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    border-radius: 18px;
    border: 1px dashed rgba(17, 19, 24, 0.16);
    color: rgba(17, 19, 24, 0.58);
    background: rgba(255, 255, 255, 0.82);
    font-size: 0.88rem;
    letter-spacing: 0.02em;
  }

  .focus-strip {
    display: grid;
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
    gap: 10px;
    margin-bottom: 12px;
  }

  .focus-card {
    padding: 14px 16px;
    border-radius: 16px;
    border: 1px solid rgba(17, 19, 24, 0.08);
    background: rgba(255, 255, 255, 0.82);
  }

  .focus-card-dark {
    background: linear-gradient(145deg, rgba(17, 19, 24, 0.98), rgba(31, 41, 55, 0.94));
    color: #f8fafc;
    box-shadow: 0 18px 34px rgba(15, 23, 42, 0.18);
  }

  .focus-label {
    display: block;
    margin-bottom: 8px;
    color: rgba(17, 19, 24, 0.5);
    font-size: 0.78rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }

  .focus-card-dark .focus-label {
    color: rgba(248, 250, 252, 0.66);
  }

  .focus-card strong {
    display: block;
    font-size: 1.02rem;
    letter-spacing: -0.03em;
  }

  .focus-card p {
    margin: 8px 0 0;
    line-height: 1.45;
    color: rgba(17, 19, 24, 0.68);
    font-size: 0.84rem;
  }

  .focus-card-dark p {
    color: rgba(248, 250, 252, 0.76);
  }

  .metric-grid,
  .memo-grid,
  .basis-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }

  .command-metric-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .metric-card,
  .basis-card {
    padding: 12px;
    border-radius: 16px;
    border: 1px solid rgba(17, 19, 24, 0.08);
    background: #ffffff;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
  }

  .metric-card span,
  .basis-card span {
    display: block;
    margin-bottom: 6px;
    color: rgba(17, 19, 24, 0.52);
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .metric-card strong,
  .basis-card strong {
    display: block;
    font-size: 1.34rem;
    letter-spacing: -0.05em;
  }

  .metric-card small,
  .basis-card small {
    color: rgba(17, 19, 24, 0.56);
    font-size: 0.78rem;
  }

  .metric-red strong {
    color: #dc2626;
  }

  .metric-blue strong {
    color: #2563eb;
  }

  .metric-green strong {
    color: #059669;
  }

  .metric-gold strong {
    color: #ca8a04;
  }

  .metric-dark {
    background: linear-gradient(145deg, rgba(17, 19, 24, 0.98), rgba(31, 41, 55, 0.94));
    color: #f8fafc;
  }

  .metric-dark span,
  .metric-dark small,
  .metric-dark strong {
    color: #f8fafc;
  }

  .metric-dark small {
    opacity: 0.76;
  }

  .metric-slate {
    background: linear-gradient(180deg, rgba(243, 246, 250, 0.95), rgba(255, 255, 255, 0.98));
  }

  .memo-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-top: 10px;
  }

  .signal-ribbon {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin-top: 10px;
  }

  .signal-chip-card {
    padding: 12px 14px;
    border-radius: 16px;
    border: 1px solid rgba(17, 19, 24, 0.08);
    background: rgba(255, 255, 255, 0.9);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
  }

  .signal-chip-label {
    display: block;
    margin-bottom: 8px;
    color: rgba(17, 19, 24, 0.54);
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .signal-chip-card strong {
    display: block;
    font-size: 1.1rem;
    letter-spacing: -0.04em;
  }

  .signal-chip-card small {
    display: block;
    margin-top: 8px;
    color: rgba(17, 19, 24, 0.52);
  }

  .memo-block {
    padding: 14px;
    border-radius: 16px;
    border: 1px solid rgba(17, 19, 24, 0.08);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.98));
  }

  .memo-block h4 {
    margin: 0 0 8px;
    font-size: 0.98rem;
    letter-spacing: -0.02em;
  }

  .scenario-table {
    display: grid;
    gap: 8px;
  }

  .scenario-table-head {
    display: grid;
    grid-template-columns: minmax(220px, 1.5fr) repeat(4, minmax(0, 0.6fr));
    gap: 10px;
    padding: 0 12px 4px;
    color: rgba(17, 19, 24, 0.44);
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  .scenario-row {
    display: grid;
    grid-template-columns: minmax(220px, 1.5fr) repeat(4, minmax(0, 0.6fr));
    gap: 10px;
    align-items: center;
    width: 100%;
    text-align: left;
    border-radius: 16px;
    border: 1px solid rgba(17, 19, 24, 0.08);
    background: #ffffff;
    padding: 12px;
    cursor: pointer;
    box-shadow: 0 10px 18px rgba(15, 23, 42, 0.03);
  }

  .scenario-row-active {
    border-color: rgba(37, 99, 235, 0.28);
    box-shadow:
      inset 0 0 0 1px rgba(37, 99, 235, 0.16),
      0 12px 24px rgba(37, 99, 235, 0.08);
    background: linear-gradient(180deg, rgba(37, 99, 235, 0.06), rgba(255, 255, 255, 0.96));
  }

  .scenario-primary strong {
    display: block;
    margin-bottom: 4px;
    line-height: 1.24;
  }

  .scenario-primary small,
  .scenario-footnote p {
    display: block;
    margin: 0;
    color: rgba(17, 19, 24, 0.58);
    line-height: 1.35;
    font-size: 0.78rem;
  }

  .scenario-metric strong {
    font-size: 0.92rem;
    display: block;
  }

  .delta-flat {
    color: #475569;
  }

  .scenario-footnote {
    margin-top: 12px;
    padding: 10px 12px;
    border-radius: 14px;
    background: rgba(15, 23, 42, 0.04);
    border: 1px solid rgba(17, 19, 24, 0.08);
  }

  .scenario-footnote-compact {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .scenario-note-kicker {
    color: rgba(17, 19, 24, 0.48);
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .trace-kind {
    padding: 5px 8px;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 600;
  }

  .trace-kind-fact {
    color: #1d4ed8;
    background: rgba(37, 99, 235, 0.12);
  }

  .trace-kind-model {
    color: #7c3aed;
    background: rgba(124, 58, 237, 0.12);
  }

  .trace-row {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.94));
  }

  .root-list {
    display: grid;
    gap: 12px;
  }

  .root-card p,
  .driver-card p,
  .lineage-row p,
  .gap-row p,
  .trace-row p {
    margin: 8px 0 0;
    line-height: 1.6;
  }

  .root-card small,
  .driver-card small,
  .lineage-row small {
    display: block;
    margin-top: 10px;
    color: rgba(17, 19, 24, 0.52);
  }

  .driver-list,
  .basis-grid,
  .lineage-list {
    max-height: 520px;
    overflow: auto;
  }

  .driver-card {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.94));
  }

  .coverage-row,
  .gap-row {
    padding: 14px 16px;
    border-radius: 18px;
    border: 1px solid rgba(17, 19, 24, 0.08);
    background: #ffffff;
  }

  .causal-loading-card,
  .causal-error-card {
    padding: 28px;
    border-radius: 24px;
  }

  .causal-loading-card {
    display: grid;
    gap: 12px;
    min-height: calc(100vh - 180px);
    place-items: center;
    text-align: center;
  }

  .loading-spinner {
    width: 48px;
    height: 48px;
    border-radius: 999px;
    border: 4px solid rgba(17, 19, 24, 0.1);
    border-top-color: #2563eb;
    animation: causal-spin 0.9s linear infinite;
  }

  .loading-detail {
    margin-top: 2px;
    max-width: 520px;
  }

  @keyframes causal-spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 1240px) {
    .hero-panel,
    .execution-grid,
    .evidence-grid,
    .model-grid,
    .quant-grid,
    .command-panel,
    .metric-grid,
    .memo-grid,
    .basis-grid,
    .signal-ribbon {
      grid-template-columns: 1fr;
    }

    .surface-body,
    .surface-body-wide {
      grid-template-columns: 1fr;
    }

    .scenario-row {
      grid-template-columns: 1fr;
    }

    .scenario-table-head {
      display: none;
    }

    .focus-strip,
    .hero-meta {
      grid-template-columns: 1fr;
    }

    .view-toggle-shell {
      justify-items: start;
    }

    .ladder-panel {
      position: static;
    }
  }

  @media (max-width: 720px) {
    .causal-shell {
      padding: 16px;
    }

    .hero-panel,
    .command-panel,
    .panel {
      padding: 18px;
      border-radius: 20px;
    }

    .brief-grid {
      grid-template-columns: 1fr;
    }

    .command-row {
      grid-template-columns: 1fr;
    }

    .plot-frame,
    .plot-frame-wide {
      min-height: 280px;
    }
  }
`;
