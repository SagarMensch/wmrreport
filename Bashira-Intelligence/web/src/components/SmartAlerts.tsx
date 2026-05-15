"use client";

import dynamic from "next/dynamic";
import { AnimatePresence, motion } from "framer-motion";
import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { useCommandCenterData } from "@/components/useCommandCenterData";

const Plot = dynamic(() => import("./PlotlyClient"), { ssr: false });

type Tone = "critical" | "warning" | "positive" | "neutral";
type Metric = { label: string; value: number | string; detail: string; accent: string };
type SummaryCard = { label: string; count: number; accent: string };
type Flag = { title: string; count: number; tone: Tone; detail: string };
type Insight = { title: string; message: string; action: string };
type Breakdown = { key: string; label: string; value: number };
type Timeline = { label: string; plan: number; actual: number; gap: number };
type Stage = { label: string; value_pct: number; gap_pct: number };
type Action = { label: string; owner: string; impact_days: number; detail: string };

type Alert = {
  id: string;
  severity: string;
  source: string;
  title: string;
  summary: string;
  confidence_pct: number;
  owner_hint: string;
  action_label: string;
  well_name: string;
  project: string;
  cluster: string;
  timestamp: string;
  rig_no: string;
  risk_score: number;
  model_score: number;
  progress_pct: number;
  delay_days: number;
  rig_on_delay_days?: number;
  current_month_gap_pct: number;
  current_month_plan_pct?: number;
  current_month_actual_pct?: number;
  velocity_pct: number;
  score_breakdown: Breakdown[];
  timeline: Timeline[];
  stage_metrics: Stage[];
  affected_wells: string[];
  evidence: string[];
  actions: Action[];
  expected_rig_off?: string | null;
  actual_rig_off?: string | null;
  badges?: string[];
};

type Payload = {
  generated_at?: string;
  engine_label?: string;
  model_note?: string;
  headline_metrics: Metric[];
  summary_cards: SummaryCard[];
  system_flags: Flag[];
  insights: Insight[];
  alerts: Alert[];
};

type PlotSpec = { data: any[]; layout: any; config?: any };
type ExtrudedBar = { label: string; value: number; color: string };
type ExtrudedGroup = { label: string; bars: ExtrudedBar[] };

const EMPTY: Payload = {
  headline_metrics: [],
  summary_cards: [],
  system_flags: [],
  insights: [],
  alerts: [],
};

const INK = "#111111";
const PAPER = "#FFFFFF";
const PANEL = "#F7F7F8";
const HAIRLINE = "#D6D8DD";
const SOFT = "#ECEEF2";
const MUTED = "#6F7279";
const IBM_BLUE = "#0F62FE";
const ROBINHOOD_GREEN = "#00C805";
const SOLID_YELLOW = "#F1C21B";
const DARK_RED = "#8E1B1B";

const SEVERITY_META: Record<string, { tone: Tone; label: string; accent: string; tint: string }> = {
  critical: { tone: "critical", label: "Critical", accent: DARK_RED, tint: "#FBE9E9" },
  high: { tone: "warning", label: "High Risk", accent: SOLID_YELLOW, tint: "#FFF7D6" },
  medium: { tone: "neutral", label: "Watch", accent: IBM_BLUE, tint: "#EAF1FF" },
  low: { tone: "positive", label: "Healthy", accent: ROBINHOOD_GREEN, tint: "#E8FAED" },
};

const BREAKDOWN_COLORS: Record<string, string> = {
  delay_trend: DARK_RED,
  progress_slope: IBM_BLUE,
  stage_stall: SOLID_YELLOW,
  scope_risk: INK,
  data_quality: ROBINHOOD_GREEN,
};

function normalizeSeverity(severity: string) {
  return String(severity || "").trim().toLowerCase();
}

function severityMeta(severity: string) {
  return SEVERITY_META[normalizeSeverity(severity)] || {
    tone: "neutral" as const,
    label: String(severity || "Signal"),
    accent: IBM_BLUE,
    tint: "#EAF1FF",
  };
}

function formatMetric(value: number | string) {
  if (typeof value !== "number") return value;
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(1);
}

function formatDate(value?: string | null) {
  if (!value) return "Live";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

function baseLayout(height: number) {
  return {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    height,
    margin: { t: 14, r: 14, b: 30, l: 14 },
    font: { family: "Figtree, system-ui, sans-serif", color: MUTED, size: 12 },
    showlegend: false,
  };
}

function plotConfig() {
  return { displayModeBar: false, responsive: true };
}

function MonoLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
      {children}
    </div>
  );
}

function IsoGlyph({ accent, secondary, label }: { accent: string; secondary: string; label: string }) {
  return (
    <svg width="38" height="38" viewBox="0 0 38 38" aria-hidden="true" role="img">
      <title>{label}</title>
      <path d="M19 3L31 10V24L19 31L7 24V10L19 3Z" fill={accent} stroke={INK} strokeWidth="1.5" />
      <path d="M19 3L31 10L19 17L7 10L19 3Z" fill={secondary} stroke={INK} strokeWidth="1.5" />
      <path d="M19 17V31" stroke={INK} strokeWidth="1.5" />
      <path d="M31 10L19 17L7 10" stroke={INK} strokeWidth="1.5" />
      <circle cx="19" cy="19" r="3.25" fill={PAPER} stroke={INK} strokeWidth="1.5" />
    </svg>
  );
}

function SurfacePanel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-[24px] border bg-white shadow-[0_16px_42px_rgba(17,17,17,0.06)] ${className}`} style={{ borderColor: HAIRLINE }}>
      {children}
    </section>
  );
}

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] transition-colors"
      style={{ fontFamily: "IBM Plex Mono, monospace", backgroundColor: active ? INK : PAPER, color: active ? PAPER : INK, borderColor: active ? INK : HAIRLINE }}
    >
      {label}
    </button>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const meta = severityMeta(severity);
  return (
    <div
      className="inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em]"
      style={{ borderColor: meta.accent, backgroundColor: meta.tint, color: meta.accent, fontFamily: "IBM Plex Mono, monospace" }}
    >
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: meta.accent }} />
      {meta.label}
    </div>
  );
}

function MetricTile({ metric }: { metric: Metric }) {
  return (
    <SurfacePanel className="min-h-[92px] px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <MonoLabel>{metric.label}</MonoLabel>
          <div className="text-[28px] font-semibold tracking-[-0.05em] text-[#111111]">{formatMetric(metric.value)}</div>
        </div>
        <div className="scale-[0.88] origin-top-right">
          <IsoGlyph accent={metric.accent || IBM_BLUE} secondary="#DDE7FF" label={metric.label} />
        </div>
      </div>
      <div className="mt-3 h-[3px] rounded-full bg-[#ECEEF2]">
        <div className="h-full rounded-full" style={{ width: "72%", backgroundColor: metric.accent || IBM_BLUE }} />
      </div>
    </SurfacePanel>
  );
}

function MetaChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="inline-flex items-center gap-3 rounded-full border bg-[#FCFCFD] px-3.5 py-2" style={{ borderColor: SOFT }}>
      <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
        {label}
      </span>
      <span className="text-[13px] font-semibold text-[#111111]">{value}</span>
    </div>
  );
}

function TopStat({ label, value, accent = INK }: { label: string; value: string; accent?: string }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border bg-[#FCFCFD] px-3 py-1.5" style={{ borderColor: SOFT }}>
      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
        {label}
      </span>
      <span className="text-[12px] font-semibold" style={{ color: accent }}>
        {value}
      </span>
    </div>
  );
}

function mixHex(hex: string, target: string, ratio: number) {
  const safeHex = hex.replace("#", "");
  const safeTarget = target.replace("#", "");
  const rgb = [0, 2, 4].map((index) => parseInt(safeHex.slice(index, index + 2), 16));
  const targetRgb = [0, 2, 4].map((index) => parseInt(safeTarget.slice(index, index + 2), 16));
  const mixed = rgb.map((value, index) => Math.round(value + (targetRgb[index] - value) * ratio));
  return `#${mixed.map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function ExtrudedBarsChart({ groups, maxValue }: { groups: ExtrudedGroup[]; maxValue?: number }) {
  const chartGroups = groups.length ? groups : [{ label: "N/A", bars: [{ label: "Signal", value: 0, color: IBM_BLUE }] }];
  const barsPerGroup = Math.max(...chartGroups.map((group) => Math.max(group.bars.length, 1)));
  const width = Math.max(520, chartGroups.length * (barsPerGroup * 42 + 42) + 100);
  const height = 250;
  const baseline = 186;
  const dx = 10;
  const dy = 8;
  const groupWidth = barsPerGroup * 42 + 34;
  const peak = Math.max(maxValue || 0, ...chartGroups.flatMap((group) => group.bars.map((bar) => bar.value)), 1);

  return (
    <div className="h-full w-full overflow-hidden">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full">
        <rect x="0" y="0" width={width} height={height} fill="#FCFCFD" />
        <line x1="28" x2={width - 18} y1={baseline + 0.5} y2={baseline + 0.5} stroke={HAIRLINE} strokeWidth="1.5" />
        {chartGroups.map((group, groupIndex) => {
          const groupStart = 42 + groupIndex * groupWidth;
          return (
            <g key={group.label}>
              {group.bars.map((bar, barIndex) => {
                const barHeight = Math.max(8, (Math.max(bar.value, 0) / peak) * 120);
                const x = groupStart + barIndex * 42;
                const y = baseline - barHeight;
                const front = bar.color;
                const top = mixHex(bar.color, "#ffffff", 0.28);
                const side = mixHex(bar.color, "#000000", 0.2);
                return (
                  <g key={`${group.label}-${bar.label}`}>
                    <polygon points={`${x},${y} ${x + 26},${y} ${x + 36},${y - dy} ${x + 10},${y - dy}`} fill={top} stroke={INK} strokeWidth="1.1" />
                    <rect x={x} y={y} width="26" height={barHeight} fill={front} stroke={INK} strokeWidth="1.1" />
                    <polygon points={`${x + 26},${y} ${x + 36},${y - dy} ${x + 36},${baseline - dy} ${x + 26},${baseline}`} fill={side} stroke={INK} strokeWidth="1.1" />
                    <text x={x + 13} y={y - 12} textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="700" fill={INK}>
                      {bar.value.toFixed(1)}
                    </text>
                  </g>
                );
              })}
              <text x={groupStart + ((group.bars.length - 1) * 42 + 26) / 2} y={224} textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="700" fill={MUTED}>
                {group.label.toUpperCase()}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function summary2D(summary: SummaryCard[]): PlotSpec {
  return {
    data: [{
      type: "bar",
      orientation: "h",
      x: summary.map((item) => item.count),
      y: summary.map((item) => item.label.toUpperCase()),
      marker: { color: summary.map((item) => item.accent), line: { color: INK, width: 1.1 } },
      text: summary.map((item) => item.count),
      textposition: "outside",
      cliponaxis: false,
      hovertemplate: "%{y}: %{x}<extra></extra>",
    }],
    layout: {
      ...baseLayout(226),
      margin: { t: 8, r: 24, b: 20, l: 72 },
      xaxis: { gridcolor: SOFT, zerolinecolor: HAIRLINE, tickfont: { family: "IBM Plex Mono, monospace", size: 11, color: MUTED } },
      yaxis: { tickfont: { family: "IBM Plex Mono, monospace", size: 11, color: INK } },
    },
    config: plotConfig(),
  };
}

function summary3D(summary: SummaryCard[]): PlotSpec {
  const labels = summary.map((item) => item.label.toUpperCase());
  const counts = summary.map((item) => item.count);
  const ticks = summary.map((_, index) => index);
  return {
    data: [
      {
        type: "scatter3d",
        mode: "lines",
        x: ticks.flatMap((value) => [value, value, null]),
        y: ticks.flatMap(() => [0, 0, null]),
        z: counts.flatMap((value) => [0, value, null]),
        line: { color: summary.flatMap((item) => [item.accent, item.accent, item.accent]), width: 12 },
        hoverinfo: "skip",
      },
      {
        type: "scatter3d",
        mode: "markers+text",
        x: ticks,
        y: new Array(summary.length).fill(0),
        z: counts,
        text: counts.map(String),
        textposition: "top center",
        textfont: { family: "IBM Plex Mono, monospace", color: INK, size: 12 },
        marker: { size: counts.map((value) => 16 + value * 4), color: summary.map((item) => item.accent), line: { color: INK, width: 1.5 }, symbol: "diamond" },
        hovertemplate: labels.map((label, index) => `${label}: ${counts[index]}<extra></extra>`),
      },
    ],
    layout: {
      ...baseLayout(226),
      margin: { t: 6, r: 8, b: 6, l: 8 },
      scene: {
        bgcolor: "transparent",
        camera: { eye: { x: 1.45, y: 1.2, z: 0.85 } },
        xaxis: { tickvals: ticks, ticktext: labels, tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: MUTED }, showgrid: false, zeroline: false, showline: true, linecolor: HAIRLINE },
        yaxis: { showticklabels: false, showgrid: false, zeroline: false, showline: false, range: [-0.75, 0.75] },
        zaxis: { rangemode: "tozero", gridcolor: SOFT, zeroline: false, tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: MUTED } },
      },
    },
    config: plotConfig(),
  };
}

function breakdown2D(alert: Alert): PlotSpec {
  const ordered = [...alert.score_breakdown].sort((left, right) => right.value - left.value);
  return {
    data: [{
      type: "bar",
      orientation: "h",
      x: ordered.map((item) => Number(item.value.toFixed(1))),
      y: ordered.map((item) => item.label.toUpperCase()),
      marker: { color: ordered.map((item) => BREAKDOWN_COLORS[item.key] || IBM_BLUE), line: { color: INK, width: 1.1 } },
      text: ordered.map((item) => item.value.toFixed(1)),
      textposition: "outside",
      cliponaxis: false,
      hovertemplate: "%{y}: %{x}<extra></extra>",
    }],
    layout: {
      ...baseLayout(238),
      margin: { t: 8, r: 24, b: 20, l: 112 },
      xaxis: { range: [0, 10.8], gridcolor: SOFT, zerolinecolor: HAIRLINE, tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: MUTED } },
      yaxis: { tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: INK } },
    },
    config: plotConfig(),
  };
}

function breakdown3D(alert: Alert): PlotSpec {
  const ordered = [...alert.score_breakdown].sort((left, right) => right.value - left.value);
  const ticks = ordered.map((_, index) => index);
  const labels = ordered.map((item) => item.label.toUpperCase());
  const values = ordered.map((item) => Number(item.value.toFixed(1)));
  return {
    data: [
      {
        type: "scatter3d",
        mode: "lines",
        x: ticks.flatMap((value) => [value, value, null]),
        y: ticks.flatMap(() => [0, 0, null]),
        z: values.flatMap((value) => [0, value, null]),
        line: { color: ordered.flatMap((item) => { const color = BREAKDOWN_COLORS[item.key] || IBM_BLUE; return [color, color, color]; }), width: 14 },
        hoverinfo: "skip",
      },
      {
        type: "scatter3d",
        mode: "markers+text",
        x: ticks,
        y: new Array(ordered.length).fill(0),
        z: values,
        text: values.map((value) => value.toFixed(1)),
        textposition: "top center",
        textfont: { family: "IBM Plex Mono, monospace", color: INK, size: 11 },
        marker: { size: values.map((value) => 14 + value * 3), color: ordered.map((item) => BREAKDOWN_COLORS[item.key] || IBM_BLUE), line: { color: INK, width: 1.4 }, symbol: "diamond" },
        hovertemplate: labels.map((label, index) => `${label}: ${values[index]}<extra></extra>`),
      },
    ],
    layout: {
      ...baseLayout(238),
      margin: { t: 4, r: 8, b: 4, l: 8 },
      scene: {
        bgcolor: "transparent",
        camera: { eye: { x: 1.35, y: 1.2, z: 0.95 } },
        xaxis: { tickvals: ticks, ticktext: labels, tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: MUTED }, showgrid: false, zeroline: false, showline: true, linecolor: HAIRLINE },
        yaxis: { showticklabels: false, showgrid: false, zeroline: false, showline: false, range: [-0.8, 0.8] },
        zaxis: { rangemode: "tozero", gridcolor: SOFT, zeroline: false, tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: MUTED } },
      },
    },
    config: plotConfig(),
  };
}

function timeline2D(alert: Alert): PlotSpec {
  const timeline = alert.timeline.length
    ? alert.timeline
    : [{ label: "W1", plan: alert.current_month_plan_pct || 0, actual: alert.current_month_actual_pct || alert.progress_pct, gap: alert.current_month_gap_pct }];
  return {
    data: [
      { type: "scatter", mode: "lines+markers", x: timeline.map((point) => point.label), y: timeline.map((point) => point.plan), line: { color: SOLID_YELLOW, width: 2, dash: "dash" }, marker: { color: SOLID_YELLOW, size: 6, line: { color: INK, width: 1 } }, name: "Plan" },
      { type: "scatter", mode: "lines+markers", x: timeline.map((point) => point.label), y: timeline.map((point) => point.actual), line: { color: IBM_BLUE, width: 3 }, marker: { color: IBM_BLUE, size: 7, line: { color: INK, width: 1 } }, name: "Actual" },
      { type: "bar", x: timeline.map((point) => point.label), y: timeline.map((point) => point.gap), marker: { color: DARK_RED, line: { color: INK, width: 1.1 } }, opacity: 0.28, name: "Gap" },
    ],
    layout: {
      ...baseLayout(238),
      barmode: "overlay",
      margin: { t: 16, r: 16, b: 28, l: 38 },
      legend: { orientation: "h", y: 1.12, x: 0, font: { family: "IBM Plex Mono, monospace", size: 10, color: MUTED } },
      showlegend: true,
      xaxis: { tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: MUTED }, showgrid: false },
      yaxis: { gridcolor: SOFT, zerolinecolor: HAIRLINE, tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: MUTED }, ticksuffix: "%" },
    },
    config: plotConfig(),
  };
}

function timeline3D(alert: Alert): PlotSpec {
  const timeline = alert.timeline.length
    ? alert.timeline
    : [{ label: "W1", plan: alert.current_month_plan_pct || 0, actual: alert.current_month_actual_pct || alert.progress_pct, gap: alert.current_month_gap_pct }];
  const ticks = timeline.map((_, index) => index);
  return {
    data: [
      { type: "scatter3d", mode: "lines+markers", x: ticks, y: new Array(timeline.length).fill(0), z: timeline.map((point) => point.plan), line: { color: SOLID_YELLOW, width: 6 }, marker: { color: SOLID_YELLOW, size: 4, line: { color: INK, width: 1 } }, name: "Plan" },
      { type: "scatter3d", mode: "lines+markers", x: ticks, y: new Array(timeline.length).fill(1), z: timeline.map((point) => point.actual), line: { color: IBM_BLUE, width: 8 }, marker: { color: IBM_BLUE, size: 4, line: { color: INK, width: 1 } }, name: "Actual" },
      { type: "scatter3d", mode: "lines+markers", x: ticks, y: new Array(timeline.length).fill(2), z: timeline.map((point) => point.gap), line: { color: DARK_RED, width: 6 }, marker: { color: DARK_RED, size: 4, line: { color: INK, width: 1 } }, name: "Gap" },
    ],
    layout: {
      ...baseLayout(238),
      margin: { t: 4, r: 8, b: 4, l: 8 },
      scene: {
        bgcolor: "transparent",
        camera: { eye: { x: 1.3, y: 1.5, z: 0.9 } },
        xaxis: { tickvals: ticks, ticktext: timeline.map((point) => point.label), tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: MUTED }, showgrid: false, zeroline: false, showline: true, linecolor: HAIRLINE },
        yaxis: { tickvals: [0, 1, 2], ticktext: ["PLAN", "ACTUAL", "GAP"], tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: MUTED }, showgrid: false, zeroline: false },
        zaxis: { rangemode: "tozero", gridcolor: SOFT, zeroline: false, tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: MUTED }, ticksuffix: "%" },
      },
      showlegend: false,
    },
    config: plotConfig(),
  };
}

function ChartCard({
  eyebrow,
  title,
  subtitle,
  view2d,
  view3d,
  view2dNode,
  view3dNode,
  height = 238,
  fill = false,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  view2d?: PlotSpec;
  view3d?: PlotSpec;
  view2dNode?: React.ReactNode;
  view3dNode?: React.ReactNode;
  height?: number;
  fill?: boolean;
}) {
  const [mode, setMode] = useState<"2d" | "3d">("2d");
  const activeNode = mode === "2d" ? view2dNode : view3dNode;
  const activePlot = mode === "2d" ? view2d : view3d;
  const activeLayout = useMemo(() => {
    if (!activePlot) return null;
    const layout = { ...activePlot.layout };
    if (fill) {
      delete layout.height;
      layout.autosize = true;
    }
    return layout;
  }, [activePlot, fill]);
  return (
    <SurfacePanel className={`flex min-h-0 flex-col overflow-hidden ${fill ? "h-full" : ""}`}>
      <div className="flex items-start justify-between gap-4 border-b px-4 py-3" style={{ borderColor: SOFT }}>
        <div className="space-y-1.5">
          <MonoLabel>{eyebrow}</MonoLabel>
          <div className="text-[16px] font-semibold tracking-[-0.03em] text-[#111111]">{title}</div>
          {subtitle ? <div className="max-w-[420px] text-[12px] text-[#4A4E57]">{subtitle}</div> : null}
        </div>
        <div className="inline-flex rounded-full border p-1" style={{ borderColor: HAIRLINE }}>
          <FilterChip label="2D" active={mode === "2d"} onClick={() => setMode("2d")} />
          <FilterChip label="3D" active={mode === "3d"} onClick={() => setMode("3d")} />
        </div>
      </div>
      <div className="min-h-0 flex-1 px-2 pb-2 pt-1">
        <div className="h-full rounded-[18px] border bg-[#FCFCFD]" style={{ borderColor: SOFT }}>
          {activeNode ? (
            activeNode
          ) : activePlot ? (
            <Plot data={activePlot.data} layout={activeLayout || activePlot.layout} config={{ ...plotConfig(), ...(activePlot.config || {}) }} style={{ width: "100%", height: fill ? "100%" : height }} useResizeHandler />
          ) : null}
        </div>
      </div>
    </SurfacePanel>
  );
}

function AlertRow({ alert, selected, onSelect }: { alert: Alert; selected: boolean; onSelect: () => void }) {
  const meta = severityMeta(alert.severity);
  const badgeText = alert.badges?.[0] || alert.action_label;
  return (
    <motion.button
      layout
      onClick={onSelect}
      className="w-full rounded-[18px] border px-3 py-3 text-left transition-colors"
      style={{ borderColor: selected ? INK : HAIRLINE, backgroundColor: selected ? PANEL : PAPER, boxShadow: selected ? "0 12px 32px rgba(17,17,17,0.08)" : "0 8px 20px rgba(17,17,17,0.03)" }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.18 }}
    >
      <div className="flex items-start gap-3">
        <div className="mt-1 h-3 w-3 shrink-0 rounded-full border" style={{ backgroundColor: meta.accent, borderColor: INK }} />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <SeverityBadge severity={alert.severity} />
                <span className="rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em]" style={{ fontFamily: "IBM Plex Mono, monospace", color: INK, borderColor: SOFT, backgroundColor: "#F1F3F5" }}>
                  {badgeText}
                </span>
              </div>
              <div className="mt-2 truncate text-[14px] font-semibold tracking-[-0.02em] text-[#111111]">{alert.title}</div>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-[#4A4E57]">
                <span>{alert.well_name}</span><span className="h-1 w-1 rounded-full bg-[#B2B6BD]" /><span>{alert.rig_no}</span><span className="h-1 w-1 rounded-full bg-[#B2B6BD]" /><span>{alert.owner_hint}</span>
              </div>
            </div>
            <div className="shrink-0 text-right">
              <div className="text-[22px] font-semibold tracking-[-0.05em] text-[#111111]">{alert.model_score.toFixed(0)}</div>
              <div className="text-[10px] uppercase tracking-[0.16em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>Score</div>
            </div>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: SOFT, color: INK }}>Delay {alert.delay_days}d</span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: SOFT, color: INK }}>Gap {alert.current_month_gap_pct.toFixed(1)}</span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: SOFT, color: INK }}>Velocity {alert.velocity_pct.toFixed(1)}</span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: SOFT, color: INK }}>{alert.project}</span>
          </div>
        </div>
      </div>
    </motion.button>
  );
}

function ActionRail({ actions }: { actions: Action[] }) {
  return (
    <div className="space-y-3">
      {actions.map((action, index) => (
        <div key={`${action.label}-${index}`} className="rounded-[18px] border bg-white px-4 py-4" style={{ borderColor: SOFT }}>
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-2">
              <div className="text-[15px] font-semibold tracking-[-0.02em] text-[#111111]">{action.label}</div>
              <div className="text-[13px] leading-6 text-[#4A4E57]">{action.detail}</div>
            </div>
            <div className="rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em]" style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: IBM_BLUE, backgroundColor: "#EAF1FF", color: IBM_BLUE }}>
              {action.impact_days}d
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between text-[12px] text-[#4A4E57]"><span>Owner</span><span className="font-semibold text-[#111111]">{action.owner}</span></div>
        </div>
      ))}
    </div>
  );
}

function StageMatrix({ stages }: { stages: Stage[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {stages.slice(0, 6).map((stage) => (
        <div key={stage.label} className="rounded-[16px] border bg-white px-4 py-3" style={{ borderColor: SOFT }}>
          <div className="flex items-center justify-between gap-3">
            <div className="text-[10px] uppercase tracking-[0.18em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>{stage.label}</div>
            <div className="text-[14px] font-semibold text-[#111111]">{stage.value_pct.toFixed(1)}%</div>
          </div>
          <div className="mt-2 h-[7px] rounded-full bg-[#ECEEF2]">
            <div className="h-full rounded-full" style={{ width: `${Math.max(stage.value_pct, 4)}%`, backgroundColor: stage.value_pct < 25 ? DARK_RED : stage.value_pct < 60 ? SOLID_YELLOW : ROBINHOOD_GREEN }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function SmartAlerts() {
  const { data, loading, error, refresh } = useCommandCenterData<Payload>("alerts", EMPTY);
  const [severityFilter, setSeverityFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [selectedAlertId, setSelectedAlertId] = useState("");
  const [centerView, setCenterView] = useState<"exposure" | "drivers" | "timeline" | "playbook" | "evidence" | "impact">("exposure");
  const deferredSearch = useDeferredValue(search);

  const filteredAlerts = useMemo(() => {
    const query = deferredSearch.trim().toLowerCase();
    return data.alerts.filter((alert) => {
      const severity = normalizeSeverity(alert.severity);
      const matchesSeverity =
        severityFilter === "all" ||
        (severityFilter === "critical" && severity === "critical") ||
        (severityFilter === "high" && severity === "high") ||
        (severityFilter === "watch" && severity === "medium") ||
        (severityFilter === "healthy" && severity === "low");
      const matchesQuery =
        !query ||
        [alert.title, alert.well_name, alert.project, alert.rig_no, alert.owner_hint, alert.cluster].join(" ").toLowerCase().includes(query);
      return matchesSeverity && matchesQuery;
    });
  }, [data.alerts, deferredSearch, severityFilter]);

  useEffect(() => {
    if (!filteredAlerts.length) {
      setSelectedAlertId("");
      return;
    }
    if (!filteredAlerts.some((alert) => alert.id === selectedAlertId)) {
      setSelectedAlertId(filteredAlerts[0].id);
    }
  }, [filteredAlerts, selectedAlertId]);

  const selectedAlert = filteredAlerts.find((alert) => alert.id === selectedAlertId) || filteredAlerts[0] || null;
  const summary2DSpec = useMemo(() => summary2D(data.summary_cards), [data.summary_cards]);
  const summary3DNode = useMemo(
    () => (
      <ExtrudedBarsChart
        groups={data.summary_cards.map((item) => ({
          label: item.label,
          bars: [{ label: item.label, value: item.count, color: item.accent }],
        }))}
        maxValue={Math.max(...data.summary_cards.map((item) => item.count), 1)}
      />
    ),
    [data.summary_cards],
  );
  const breakdown2DSpec = useMemo(() => (selectedAlert ? breakdown2D(selectedAlert) : breakdown2D({ id: "empty", severity: "medium", source: "", title: "", summary: "", confidence_pct: 0, owner_hint: "", action_label: "", well_name: "", project: "", cluster: "", timestamp: "", rig_no: "", risk_score: 0, model_score: 0, progress_pct: 0, delay_days: 0, current_month_gap_pct: 0, velocity_pct: 0, score_breakdown: [], timeline: [], stage_metrics: [], affected_wells: [], evidence: [], actions: [] })), [selectedAlert]);
  const breakdown3DNode = useMemo(
    () =>
      selectedAlert ? (
        <ExtrudedBarsChart
          groups={[...selectedAlert.score_breakdown]
            .sort((left, right) => right.value - left.value)
            .map((item) => ({
              label: item.label,
              bars: [{ label: item.label, value: item.value, color: BREAKDOWN_COLORS[item.key] || IBM_BLUE }],
            }))}
            maxValue={10}
        />
      ) : null,
    [selectedAlert],
  );
  const timeline2DSpec = useMemo(() => (selectedAlert ? timeline2D(selectedAlert) : timeline2D({ id: "empty", severity: "medium", source: "", title: "", summary: "", confidence_pct: 0, owner_hint: "", action_label: "", well_name: "", project: "", cluster: "", timestamp: "", rig_no: "", risk_score: 0, model_score: 0, progress_pct: 0, delay_days: 0, current_month_gap_pct: 0, velocity_pct: 0, score_breakdown: [], timeline: [], stage_metrics: [], affected_wells: [], evidence: [], actions: [] })), [selectedAlert]);
  const timeline3DNode = useMemo(
    () =>
      selectedAlert ? (
        <ExtrudedBarsChart
          groups={(selectedAlert.timeline.length
            ? selectedAlert.timeline
            : [{ label: "W1", plan: selectedAlert.current_month_plan_pct || 0, actual: selectedAlert.current_month_actual_pct || selectedAlert.progress_pct, gap: selectedAlert.current_month_gap_pct }]
          ).map((point) => ({
            label: point.label,
            bars: [
              { label: "Plan", value: point.plan, color: SOLID_YELLOW },
              { label: "Actual", value: point.actual, color: IBM_BLUE },
              { label: "Gap", value: point.gap, color: DARK_RED },
            ],
          }))}
          maxValue={100}
        />
      ) : null,
    [selectedAlert],
  );

  return (
    <div className="overflow-x-hidden bg-white text-[#111111]" style={{ fontFamily: "Figtree, system-ui, sans-serif", backgroundImage: "linear-gradient(to right, rgba(17,17,17,0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(17,17,17,0.03) 1px, transparent 1px)", backgroundSize: "32px 32px" }}>
      <div className="flex flex-col gap-3 px-4 py-4 xl:px-5">
        <SurfacePanel className="shrink-0 px-4 py-3">
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-3 2xl:flex-row 2xl:items-center 2xl:justify-between">
              <div className="flex min-w-0 items-center gap-3">
                <IsoGlyph accent={IBM_BLUE} secondary="#DDE7FF" label="Smart Alerts" />
                <div className="min-w-0">
                  <MonoLabel>Smart Alerts</MonoLabel>
                  <h1 className="truncate text-[24px] font-semibold tracking-[-0.05em] text-[#111111]">Escalation Board</h1>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {[
                  ["all", "All"],
                  ["critical", "Critical"],
                  ["high", "High"],
                  ["watch", "Watch"],
                  ["healthy", "Healthy"],
                ].map(([value, label]) => (
                  <FilterChip key={value} label={label} active={severityFilter === value} onClick={() => setSeverityFilter(value)} />
                ))}
              </div>
              <div className="flex flex-1 flex-wrap items-center justify-end gap-2 2xl:max-w-[460px]">
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search alert, well, rig, or owner"
                  className="h-9 min-w-[220px] flex-1 rounded-full border bg-[#FCFCFD] px-4 text-[13px] text-[#111111] outline-none"
                  style={{ borderColor: HAIRLINE }}
                />
                <button onClick={() => void refresh()} className="h-9 rounded-full border px-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#111111]" style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: INK }}>
                  Refresh
                </button>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 border-t pt-3" style={{ borderColor: SOFT }}>
              {data.headline_metrics.slice(0, 4).map((metric) => (
                <TopStat key={metric.label} label={metric.label} value={String(formatMetric(metric.value))} accent={metric.accent || INK} />
              ))}
              <TopStat label="As Of" value={formatDate(data.generated_at)} />
              <TopStat label="Loaded" value={String(filteredAlerts.length)} accent={IBM_BLUE} />
            </div>
          </div>
        </SurfacePanel>

        {loading ? (
          <SurfacePanel className="flex min-h-0 flex-1 items-center justify-center"><div className="flex items-center gap-4"><IsoGlyph accent={IBM_BLUE} secondary="#DDE7FF" label="Synchronizing" /><div><MonoLabel>System state</MonoLabel><div className="mt-2 text-[18px] font-semibold tracking-[-0.03em] text-[#111111]">Synchronizing alert intelligence</div></div></div></SurfacePanel>
        ) : error ? (
          <SurfacePanel className="flex min-h-0 flex-1 items-center justify-center px-8"><div className="max-w-[760px] text-center"><MonoLabel>Command failure</MonoLabel><div className="mt-3 text-[24px] font-semibold tracking-[-0.04em] text-[#111111]">Smart Alerts could not load from the command-center backend.</div><div className="mt-3 text-[14px] leading-6 text-[#4A4E57]">{error}</div></div></SurfacePanel>
        ) : (
          <div className="flex items-start gap-3 max-lg:flex-col">
            <SurfacePanel className="flex min-h-0 w-full shrink-0 flex-col overflow-hidden lg:h-full lg:w-[320px]">
              <div className="flex items-center justify-between border-b px-4 py-3" style={{ borderColor: SOFT }}>
                <div>
                  <MonoLabel>Alert ledger</MonoLabel>
                  <div className="mt-1 text-[17px] font-semibold tracking-[-0.04em] text-[#111111]">Intervention queue</div>
                </div>
                <div className="rounded-full bg-[#111111] px-3 py-1 text-[10px] uppercase tracking-[0.16em] text-white" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
                  {filteredAlerts.length}
                </div>
              </div>
              <div className="min-h-0 flex-1 space-y-2 overflow-y-auto overscroll-contain px-3 py-3">
                {filteredAlerts.map((alert) => (
                  <AlertRow key={alert.id} alert={alert} selected={alert.id === selectedAlert?.id} onSelect={() => setSelectedAlertId(alert.id)} />
                ))}
                {!filteredAlerts.length ? (
                  <div className="rounded-[20px] border bg-white px-5 py-10 text-center" style={{ borderColor: SOFT }}>
                    <MonoLabel>No results</MonoLabel>
                    <div className="mt-3 text-[18px] font-semibold tracking-[-0.03em] text-[#111111]">No alert matches this slice.</div>
                  </div>
                ) : null}
              </div>
            </SurfacePanel>

            <SurfacePanel className="min-w-0 flex-1 overflow-hidden">
              <div className="border-b px-4 py-3" style={{ borderColor: SOFT }}>
                <AnimatePresence mode="wait">
                  {selectedAlert ? (
                    <motion.div key={selectedAlert.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.18 }} className="space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <SeverityBadge severity={selectedAlert.severity} />
                        <span className="rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em]" style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: IBM_BLUE, backgroundColor: "#EAF1FF", color: IBM_BLUE }}>
                          {selectedAlert.source}
                        </span>
                        {(selectedAlert.badges || []).slice(0, 2).map((badge) => (
                          <span key={badge} className="rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em]" style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: SOFT, backgroundColor: "#F1F3F5", color: INK }}>
                            {badge}
                          </span>
                        ))}
                      </div>
                      <div className="flex flex-col gap-3 2xl:flex-row 2xl:items-start 2xl:justify-between">
                        <div className="min-w-0">
                          <div className="truncate text-[22px] font-semibold tracking-[-0.05em] text-[#111111]">{selectedAlert.title}</div>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-[12px] text-[#4A4E57]">
                            <span>{selectedAlert.well_name}</span><span className="h-1 w-1 rounded-full bg-[#B2B6BD]" /><span>{selectedAlert.project}</span><span className="h-1 w-1 rounded-full bg-[#B2B6BD]" /><span>{selectedAlert.rig_no}</span><span className="h-1 w-1 rounded-full bg-[#B2B6BD]" /><span>{selectedAlert.owner_hint}</span>
                          </div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          {[["Model", selectedAlert.model_score.toFixed(1)], ["Delay", `${selectedAlert.delay_days}d`], ["Gap", `${selectedAlert.current_month_gap_pct.toFixed(1)}`], ["Action", selectedAlert.action_label]].map(([label, value]) => (
                            <TopStat key={label} label={label} value={value} accent={label === "Action" ? IBM_BLUE : INK} />
                          ))}
                        </div>
                      </div>
                    </motion.div>
                  ) : null}
                </AnimatePresence>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {[
                    ["exposure", "Exposure"],
                    ["drivers", "Drivers"],
                    ["timeline", "Timeline"],
                    ["playbook", "Playbook"],
                    ["evidence", "Evidence"],
                    ["impact", "Impact"],
                  ].map(([value, label]) => (
                    <FilterChip key={value} label={label} active={centerView === value} onClick={() => setCenterView(value as "exposure" | "drivers" | "timeline" | "playbook" | "evidence" | "impact")} />
                  ))}
                </div>
              </div>
              <div className="p-2">
                {centerView === "exposure" ? (
                  <ChartCard eyebrow="Portfolio exposure" title="Severity mix" subtitle="2D and 3D column views of live alert pressure." view2d={summary2DSpec} view3dNode={summary3DNode} height={320} />
                ) : null}
                {selectedAlert && centerView === "drivers" ? (
                  <ChartCard eyebrow="Signal model" title="Driver stack" subtitle="2D and 3D column views of the active alert." view2d={breakdown2DSpec} view3dNode={breakdown3DNode} height={320} />
                ) : null}
                {selectedAlert && centerView === "timeline" ? (
                  <ChartCard eyebrow="Plan divergence" title="Plan vs actual" subtitle="Weekly schedule structure with flat and extruded columns." view2d={timeline2DSpec} view3dNode={timeline3DNode} height={320} />
                ) : null}
                {selectedAlert && centerView === "playbook" ? (
                  <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
                    <div className="px-2 py-1">
                      <ActionRail actions={selectedAlert.actions} />
                    </div>
                    <div className="space-y-3 px-2 py-1">
                      {data.insights.slice(0, 4).map((insight, index) => (
                        <div key={`${insight.title}-${index}`} className="rounded-[18px] border bg-[#FCFCFD] px-4 py-4" style={{ borderColor: SOFT }}>
                          <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
                            Directive
                          </div>
                          <div className="mt-2 text-[15px] font-semibold tracking-[-0.02em] text-[#111111]">{insight.title}</div>
                          <div className="mt-2 text-[13px] leading-6 text-[#4A4E57]">{insight.message}</div>
                          <div className="mt-3 inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em]" style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: INK, color: INK }}>
                            {insight.action}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
                {selectedAlert && centerView === "evidence" ? (
                  <div className="space-y-3 px-2 py-1">
                    <SurfacePanel className="px-4 py-4">
                      <div className="space-y-3">
                        <div>
                          <MonoLabel>Stage progression</MonoLabel>
                          <div className="mt-2 text-[18px] font-semibold tracking-[-0.03em] text-[#111111]">Execution stage coverage</div>
                        </div>
                        <StageMatrix stages={selectedAlert.stage_metrics} />
                      </div>
                    </SurfacePanel>
                    <div className="space-y-3">
                      {selectedAlert.evidence.map((line, index) => (
                        <div key={`${line}-${index}`} className="rounded-[16px] border bg-white px-4 py-3 text-[13px] leading-6 text-[#4A4E57]" style={{ borderColor: SOFT }}>
                          <div className="mb-2 flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: IBM_BLUE }} />
                            <span className="text-[10px] uppercase tracking-[0.16em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
                              Evidence {index + 1}
                            </span>
                          </div>
                          {line}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
                {selectedAlert && centerView === "impact" ? (
                  <div className="grid gap-3 xl:grid-cols-[360px_minmax(0,1fr)]">
                    <div className="space-y-3 px-2 py-1">
                      {[["Affected wells", String(selectedAlert.affected_wells.length)], ["Rig-on delay", `${selectedAlert.rig_on_delay_days || 0}d`], ["Plan", `${(selectedAlert.current_month_plan_pct || 0).toFixed(1)}%`], ["Actual", `${(selectedAlert.current_month_actual_pct || 0).toFixed(1)}%`], ["Expected rig-off", formatDate(selectedAlert.expected_rig_off)], ["Actual rig-off", formatDate(selectedAlert.actual_rig_off)]].map(([label, value]) => (
                        <div key={label} className="flex items-center justify-between rounded-[16px] border bg-white px-4 py-3" style={{ borderColor: SOFT }}>
                          <span className="text-[10px] uppercase tracking-[0.18em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>{label}</span>
                          <span className="text-[14px] font-semibold text-[#111111]">{value}</span>
                        </div>
                      ))}
                    </div>
                    <div className="space-y-3 px-2 py-1">
                      <div className="grid gap-3 xl:grid-cols-2">
                        {data.system_flags.slice(0, 4).map((flag) => {
                          const toneColor = flag.tone === "critical" ? DARK_RED : flag.tone === "warning" ? SOLID_YELLOW : flag.tone === "positive" ? ROBINHOOD_GREEN : IBM_BLUE;
                          return (
                            <div key={flag.title} className="rounded-[18px] border bg-[#FCFCFD] px-4 py-4" style={{ borderColor: SOFT }}>
                              <div className="flex items-start justify-between gap-3">
                                <div>
                                  <div className="text-[15px] font-semibold tracking-[-0.02em] text-[#111111]">{flag.title}</div>
                                  <div className="mt-2 text-[13px] leading-6 text-[#4A4E57]">{flag.detail}</div>
                                </div>
                                <div className="rounded-full border px-3 py-1 text-[11px] font-semibold" style={{ borderColor: toneColor, color: toneColor, fontFamily: "IBM Plex Mono, monospace" }}>
                                  {flag.count}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      <div className="rounded-[18px] border bg-white px-4 py-4" style={{ borderColor: SOFT }}>
                        <div className="mb-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
                          Affected wells
                        </div>
                        <div className="grid gap-2 xl:grid-cols-2">
                          {(selectedAlert.affected_wells || []).map((well) => (
                            <div key={well} className="rounded-[14px] border bg-[#FCFCFD] px-3 py-2 text-[13px] font-semibold text-[#111111]" style={{ borderColor: SOFT }}>
                              {well}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </SurfacePanel>
          </div>
        )}
      </div>
    </div>
  );
}
