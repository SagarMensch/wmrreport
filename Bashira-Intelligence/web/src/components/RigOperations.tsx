"use client";

import dynamic from "next/dynamic";
import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { useCommandCenterData } from "@/components/useCommandCenterData";

const Plot = dynamic(() => import("@/components/PlotlyClient"), { ssr: false });

type ChartMode = "2d" | "3d";
type FilterMode = "all" | "critical" | "high" | "watch" | "healthy";
type WorkspaceView = "pressure" | "drivers" | "stages" | "queue" | "playbook";
type DossierView = "quant" | "stages" | "evidence" | "actions" | "timing";
type FocusOverlay = null | "chart" | "brief" | "roster" | "wells";

type StageMetric = { label: string; value_pct: number; gap_pct: number };
type ScoreBreakdown = { key: string; label: string; value: number };
type ActionRow = { label: string; owner: string; impact_days: number; detail: string };

interface RigWell {
  well_id: string;
  well_name: string;
  project: string;
  rig_no: string;
  rig_status: string;
  progress_pct: number;
  delay_days: number;
  rig_on_delay_days: number;
  expected_rig_on?: string | null;
  actual_rig_on?: string | null;
  expected_rig_off?: string | null;
  actual_rig_off?: string | null;
  current_month_gap_pct: number;
  velocity_pct: number;
  queue_exposure: number;
  missing_fields: number;
  anomaly_flag: boolean;
  ops_risk_score: number;
  ops_risk_tier: string;
  recovery_confidence_pct: number;
  dominant_bottleneck: string;
  stage_metrics: StageMetric[];
  score_breakdown: ScoreBreakdown[];
  evidence: string[];
  actions: ActionRow[];
  badges: string[];
}

interface RigCard {
  rig_no: string;
  active_wells: number;
  critical_wells: number;
  anomaly_count: number;
  pressure_score: number;
  queue_exposure: number;
  recovery_confidence_pct: number;
  dominant_bottleneck: string;
  status: string;
  pressure_rank: number;
  top_actions: ActionRow[];
  wells: RigWell[];
}

interface RigPayload {
  generated_at?: string;
  engine_label?: string;
  summary: {
    critical_rigs?: number;
    high_risk_rigs?: number;
    avg_pressure_score?: number;
    queue_exposed_wells?: number;
    anomaly_wells?: number;
    planned_or_active_wells?: number;
  };
  rigs: RigCard[];
}

type ExtrudedGroup = {
  label: string;
  bars: { label: string; value: number; color: string }[];
};

const EMPTY_DATA: RigPayload = { summary: {}, rigs: [] };

const INK = "#111111";
const PAPER = "#FFFFFF";
const SOFT = "#ECEEF2";
const HAIRLINE = "#D6D8DD";
const MUTED = "#6F7279";
const IBM_BLUE = "#0F62FE";
const ROBINHOOD_GREEN = "#00C805";
const SOLID_YELLOW = "#F1C21B";
const DARK_RED = "#8E1B1B";
const STAGE_ORDER = ["Location Prep", "Engineering", "Construction", "OHL", "Flowline", "Commissioning"];

function normalizeToken(value: string) {
  return String(value || "").trim().toUpperCase().replace(/\s+/g, "_");
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function formatNumber(value: number | null | undefined, digits = 1) {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) return "0.0";
  return numeric.toFixed(digits);
}

function formatDateLabel(value?: string | null) {
  if (!value) return "Awaiting";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(parsed);
}

function formatTimestamp(value?: string) {
  if (!value) return "Live";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function shortenLabel(value: string, max = 16) {
  return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}

function matchesRigFilter(rig: RigCard, mode: FilterMode) {
  if (mode === "all") return true;
  if (mode === "critical") return normalizeToken(rig.status) === "CRITICAL";
  if (mode === "high") return normalizeToken(rig.status) === "HIGH_RISK";
  if (mode === "watch") return normalizeToken(rig.status) === "WATCH";
  return normalizeToken(rig.status) === "HEALTHY";
}

function tierMeta(value: string) {
  const normalized = normalizeToken(value);
  if (normalized === "CRITICAL") return { label: "Critical", accent: DARK_RED, tint: "#FBE9E9" };
  if (normalized === "HIGH_RISK") return { label: "High Risk", accent: SOLID_YELLOW, tint: "#FFF7D6" };
  if (normalized === "WATCH") return { label: "Watch", accent: IBM_BLUE, tint: "#EAF1FF" };
  return { label: "Healthy", accent: ROBINHOOD_GREEN, tint: "#E8FAED" };
}

function aggregateStages(wells: RigWell[]) {
  const stageMap = new Map<string, { value: number; gap: number; count: number }>();
  for (const well of wells) {
    for (const metric of well.stage_metrics || []) {
      const current = stageMap.get(metric.label) || { value: 0, gap: 0, count: 0 };
      current.value += Number(metric.value_pct || 0);
      current.gap += Number(metric.gap_pct || 0);
      current.count += 1;
      stageMap.set(metric.label, current);
    }
  }
  return STAGE_ORDER.filter((label) => stageMap.has(label)).map((label) => {
    const metric = stageMap.get(label)!;
    return {
      label,
      value_pct: Number((metric.value / Math.max(metric.count, 1)).toFixed(1)),
      gap_pct: Number((metric.gap / Math.max(metric.count, 1)).toFixed(1)),
    };
  });
}

function aggregateBreakdowns(wells: RigWell[]) {
  const breakdownMap = new Map<string, { label: string; total: number; count: number }>();
  for (const well of wells) {
    for (const breakdown of well.score_breakdown || []) {
      const current = breakdownMap.get(breakdown.key) || { label: breakdown.label, total: 0, count: 0 };
      current.total += Number(breakdown.value || 0);
      current.count += 1;
      breakdownMap.set(breakdown.key, current);
    }
  }
  return Array.from(breakdownMap.entries())
    .map(([key, item]) => ({
      key,
      label: item.label,
      value: Number((item.total / Math.max(item.count, 1)).toFixed(1)),
    }))
    .sort((left, right) => right.value - left.value);
}

function baseLayout(height: number) {
  return {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    height,
    margin: { t: 12, r: 18, b: 32, l: 20 },
    font: { family: "Figtree, system-ui, sans-serif", color: MUTED, size: 12 },
    showlegend: true,
    legend: {
      orientation: "h",
      x: 0,
      y: 1.12,
      font: { family: "IBM Plex Mono, monospace", size: 10, color: MUTED },
      bgcolor: "rgba(0,0,0,0)",
    },
  };
}

function plotConfig() {
  return { displayModeBar: false, responsive: true };
}

function mixHex(hex: string, target: string, ratio: number) {
  const start = hex.replace("#", "");
  const end = target.replace("#", "");
  const startRgb = [0, 2, 4].map((index) => parseInt(start.slice(index, index + 2), 16));
  const endRgb = [0, 2, 4].map((index) => parseInt(end.slice(index, index + 2), 16));
  const mixed = startRgb.map((value, index) => Math.round(value + (endRgb[index] - value) * ratio));
  return `#${mixed.map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function MonoLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
      {children}
    </div>
  );
}

function SurfacePanel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-[24px] border bg-white shadow-[0_18px_42px_rgba(17,17,17,0.06)] ${className}`} style={{ borderColor: HAIRLINE }}>
      {children}
    </section>
  );
}

function FilterChip({ label, active, accent, onClick }: { label: string; active: boolean; accent?: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors"
      style={{
        fontFamily: "IBM Plex Mono, monospace",
        borderColor: active ? accent || INK : HAIRLINE,
        backgroundColor: active ? accent || INK : PAPER,
        color: active ? PAPER : INK,
      }}
    >
      {label}
    </button>
  );
}

function SeverityPill({ value }: { value: string }) {
  const meta = tierMeta(value);
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

function MetaChip({ label, value, accent = INK }: { label: string; value: string; accent?: string }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border bg-[#FCFCFD] px-3 py-2" style={{ borderColor: SOFT }}>
      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
        {label}
      </span>
      <span className="text-[12px] font-semibold" style={{ color: accent }}>
        {value}
      </span>
    </div>
  );
}

function SummaryChip({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="inline-flex items-center gap-3 rounded-full border bg-white px-3.5 py-2 shadow-[0_4px_14px_rgba(17,17,17,0.04)]" style={{ borderColor: SOFT }}>
      <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
        {label}
      </span>
      <span className="text-[15px] font-semibold" style={{ color: accent }}>
        {value}
      </span>
    </div>
  );
}

function DossierMetric({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="rounded-[16px] border bg-[#FCFCFD] px-3 py-3" style={{ borderColor: SOFT }}>
      <MonoLabel>{label}</MonoLabel>
      <div className="mt-2 text-[23px] font-semibold tracking-[-0.04em]" style={{ color: accent }}>
        {value}
      </div>
    </div>
  );
}

function StageCell({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="rounded-[14px] border bg-white px-3 py-3" style={{ borderColor: SOFT }}>
      <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>
        {label}
      </div>
      <div className="mt-2 text-[18px] font-semibold tracking-[-0.03em]" style={{ color: accent }}>
        {value}
      </div>
    </div>
  );
}

function IsoGlyph({ accent, secondary, label }: { accent: string; secondary: string; label: string }) {
  return (
    <svg width="42" height="42" viewBox="0 0 42 42" aria-hidden="true" role="img">
      <title>{label}</title>
      <path d="M21 4L35 12V28L21 36L7 28V12L21 4Z" fill={accent} stroke={INK} strokeWidth="1.6" />
      <path d="M21 4L35 12L21 20L7 12L21 4Z" fill={secondary} stroke={INK} strokeWidth="1.6" />
      <path d="M21 20V36" stroke={INK} strokeWidth="1.6" />
      <path d="M35 12L21 20L7 12" stroke={INK} strokeWidth="1.6" />
      <rect x="17" y="16.4" width="8" height="8" rx="1.3" fill={PAPER} stroke={INK} strokeWidth="1.5" />
    </svg>
  );
}

function ExtrudedBarsChart({ groups, maxValue }: { groups: ExtrudedGroup[]; maxValue?: number }) {
  const chartGroups = groups.length ? groups : [{ label: "None", bars: [{ label: "Signal", value: 0, color: IBM_BLUE }] }];
  const peak = Math.max(maxValue || 0, ...chartGroups.flatMap((group) => group.bars.map((bar) => Math.max(bar.value, 0))), 1);
  const barsPerGroup = Math.max(...chartGroups.map((group) => Math.max(group.bars.length, 1)));
  const width = Math.max(620, chartGroups.length * (barsPerGroup * 44 + 48) + 120);
  const height = 278;
  const baseline = 194;
  const groupWidth = barsPerGroup * 44 + 34;

  return (
    <div className="h-full w-full overflow-hidden rounded-[18px] border bg-[#FCFCFD] p-3" style={{ borderColor: SOFT }}>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full">
        <rect x="0" y="0" width={width} height={height} fill="#FCFCFD" />
        <line x1="30" x2={width - 18} y1={baseline + 0.5} y2={baseline + 0.5} stroke={HAIRLINE} strokeWidth="1.5" />
        {chartGroups.map((group, groupIndex) => {
          const groupStart = 44 + groupIndex * groupWidth;
          return (
            <g key={`${group.label}-${groupIndex}`}>
              {group.bars.map((bar, barIndex) => {
                const heightValue = Math.max(10, (Math.max(bar.value, 0) / peak) * 126);
                const x = groupStart + barIndex * 44;
                const y = baseline - heightValue;
                const top = mixHex(bar.color, "#ffffff", 0.3);
                const side = mixHex(bar.color, "#000000", 0.18);
                return (
                  <g key={`${group.label}-${groupIndex}-${bar.label}-${barIndex}`}>
                    <polygon points={`${x},${y} ${x + 28},${y} ${x + 40},${y - 9} ${x + 12},${y - 9}`} fill={top} stroke={INK} strokeWidth="1.1" />
                    <rect x={x} y={y} width="28" height={heightValue} fill={bar.color} stroke={INK} strokeWidth="1.1" />
                    <polygon points={`${x + 28},${y} ${x + 40},${y - 9} ${x + 40},${baseline - 9} ${x + 28},${baseline}`} fill={side} stroke={INK} strokeWidth="1.1" />
                    <text x={x + 14} y={y - 12} textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="700" fill={INK}>
                      {bar.value.toFixed(1)}
                    </text>
                  </g>
                );
              })}
              <text x={groupStart + ((group.bars.length - 1) * 44 + 28) / 2} y={246} textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="700" fill={MUTED}>
                {shortenLabel(group.label, 14).toUpperCase()}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function RigOperations() {
  const { data, loading, error, refresh } = useCommandCenterData<RigPayload>("rig_operations", EMPTY_DATA);
  const [search, setSearch] = useState("");
  const [filterMode, setFilterMode] = useState<FilterMode>("all");
  const [selectedRigId, setSelectedRigId] = useState("");
  const [selectedWellId, setSelectedWellId] = useState("");
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>("pressure");
  const [chartMode, setChartMode] = useState<ChartMode>("2d");
  const [dossierView, setDossierView] = useState<DossierView>("quant");
  const [focusOverlay, setFocusOverlay] = useState<FocusOverlay>(null);
  const deferredSearch = useDeferredValue(search);

  const filteredRigs = useMemo(() => {
    const query = deferredSearch.trim().toLowerCase();
    return data.rigs.filter((rig) => {
      if (!matchesRigFilter(rig, filterMode)) return false;
      if (!query) return true;
      const rigMatch =
        rig.rig_no.toLowerCase().includes(query) ||
        rig.dominant_bottleneck.toLowerCase().includes(query) ||
        rig.status.toLowerCase().includes(query);
      const wellMatch = rig.wells.some((well) =>
        [well.well_name, well.project, well.dominant_bottleneck, ...(well.badges || [])]
          .join(" ")
          .toLowerCase()
          .includes(query),
      );
      return rigMatch || wellMatch;
    });
  }, [data.rigs, deferredSearch, filterMode]);

  useEffect(() => {
    if (!filteredRigs.length) {
      setSelectedRigId("");
      return;
    }
    setSelectedRigId((current) => (filteredRigs.some((rig) => rig.rig_no === current) ? current : filteredRigs[0].rig_no));
  }, [filteredRigs]);

  const selectedRig = useMemo(
    () => filteredRigs.find((rig) => rig.rig_no === selectedRigId) || filteredRigs[0] || null,
    [filteredRigs, selectedRigId],
  );

  const visibleWells = useMemo(() => {
    if (!selectedRig) return [];
    const query = deferredSearch.trim().toLowerCase();
    return [...selectedRig.wells]
      .filter((well) => {
        if (!query) return true;
        return [well.well_name, well.project, well.dominant_bottleneck, ...(well.badges || []), ...(well.evidence || [])]
          .join(" ")
          .toLowerCase()
          .includes(query);
      })
      .sort((left, right) => {
        const rightDelay = right.delay_days + right.rig_on_delay_days;
        const leftDelay = left.delay_days + left.rig_on_delay_days;
        return right.ops_risk_score - left.ops_risk_score || rightDelay - leftDelay;
      });
  }, [selectedRig, deferredSearch]);

  useEffect(() => {
    if (!visibleWells.length) {
      setSelectedWellId("");
      return;
    }
    setSelectedWellId((current) => (visibleWells.some((well) => well.well_id === current) ? current : visibleWells[0].well_id));
  }, [visibleWells]);

  const selectedWell = useMemo(
    () => visibleWells.find((well) => well.well_id === selectedWellId) || visibleWells[0] || null,
    [visibleWells, selectedWellId],
  );

  const stageAggregate = useMemo(() => aggregateStages(selectedRig?.wells || []), [selectedRig]);
  const breakdownAggregate = useMemo(() => aggregateBreakdowns(selectedRig?.wells || []), [selectedRig]);
  const pressureRows = useMemo(() => [...visibleWells].sort((left, right) => right.ops_risk_score - left.ops_risk_score).slice(0, 10), [visibleWells]);
  const delayRows = useMemo(
    () =>
      [...visibleWells]
        .sort((left, right) => right.delay_days + right.rig_on_delay_days - (left.delay_days + left.rig_on_delay_days))
        .slice(0, 10)
        .map((well) => ({
          label: well.well_name,
          arrival: Number(well.rig_on_delay_days || 0),
          stay: Number(well.delay_days || 0),
          tier: well.ops_risk_tier,
        })),
    [visibleWells],
  );

  const summaryChips = [
    { label: "Fleet Pressure", value: formatNumber(data.summary.avg_pressure_score, 1), accent: IBM_BLUE },
    { label: "Critical Rigs", value: `${data.summary.critical_rigs ?? 0}`, accent: DARK_RED },
    { label: "High Risk", value: `${data.summary.high_risk_rigs ?? 0}`, accent: SOLID_YELLOW },
    { label: "Queue Spill", value: `${data.summary.queue_exposed_wells ?? 0}`, accent: IBM_BLUE },
    { label: "Anomalies", value: `${data.summary.anomaly_wells ?? 0}`, accent: DARK_RED },
    { label: "Active Wells", value: `${data.summary.planned_or_active_wells ?? 0}`, accent: ROBINHOOD_GREEN },
  ];

  const rigAvgGap = useMemo(() => {
    if (!selectedRig?.wells.length) return 0;
    return selectedRig.wells.reduce((sum, well) => sum + Number(well.current_month_gap_pct || 0), 0) / selectedRig.wells.length;
  }, [selectedRig]);

  const rigAvgVelocity = useMemo(() => {
    if (!selectedRig?.wells.length) return 0;
    return selectedRig.wells.reduce((sum, well) => sum + Number(well.velocity_pct || 0), 0) / selectedRig.wells.length;
  }, [selectedRig]);

  const rigAvgSlip = useMemo(() => {
    if (!selectedRig?.wells.length) return 0;
    return (
      selectedRig.wells.reduce((sum, well) => sum + Number(well.delay_days || 0) + Number(well.rig_on_delay_days || 0), 0) /
      selectedRig.wells.length
    );
  }, [selectedRig]);

  const getBreakdownValue = (key: string) => breakdownAggregate.find((item) => item.key === key)?.value ?? 0;

  const rigQuantChips = [
    { label: "Slip", value: `${formatNumber(rigAvgSlip, 1)}d`, accent: DARK_RED },
    { label: "Plan Gap", value: `${formatNumber(rigAvgGap, 1)}%`, accent: IBM_BLUE },
    { label: "Stage Stall", value: formatNumber(getBreakdownValue("stage_stall"), 1), accent: SOLID_YELLOW },
    { label: "Contagion", value: `${selectedRig?.queue_exposure ?? 0}`, accent: IBM_BLUE },
    { label: "Outliers", value: `${selectedRig?.anomaly_count ?? 0}`, accent: DARK_RED },
    { label: "Velocity", value: `${formatNumber(rigAvgVelocity, 1)}%`, accent: rigAvgVelocity < 0 ? DARK_RED : ROBINHOOD_GREEN },
  ];

  const selectedWellRank = useMemo(() => {
    if (!selectedWell) return 0;
    const index = visibleWells.findIndex((well) => well.well_id === selectedWell.well_id);
    return index >= 0 ? index + 1 : 0;
  }, [selectedWell, visibleWells]);

  const selectedRigMeta = selectedRig ? tierMeta(selectedRig.status) : null;
  useEffect(() => {
    if (typeof document === "undefined") return;
    const previous = document.body.style.overflow;
    if (focusOverlay) document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [focusOverlay]);

  const workspaceSpec = useMemo(() => {
    if (workspaceView === "pressure") {
      return {
        title: "Rig pressure skyline",
        caption: "Top wells ranked by operating pressure and recovery loss.",
        twoD: {
          data: [{
            type: "bar",
            orientation: "h",
            x: pressureRows.map((row) => row.ops_risk_score),
            y: pressureRows.map((row) => shortenLabel(row.well_name, 22)),
            marker: { color: pressureRows.map((row) => tierMeta(row.ops_risk_tier).accent), line: { color: INK, width: 1.1 } },
            text: pressureRows.map((row) => row.ops_risk_score.toFixed(1)),
            textposition: "outside",
            cliponaxis: false,
          }],
          layout: { ...baseLayout(300), margin: { t: 8, r: 26, b: 26, l: 116 }, xaxis: { range: [0, 100], gridcolor: SOFT }, yaxis: { automargin: true, tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: INK } } },
          config: plotConfig(),
        },
        threeD: pressureRows.map((row) => ({ label: shortenLabel(row.well_name, 12), bars: [{ label: "Pressure", value: row.ops_risk_score, color: tierMeta(row.ops_risk_tier).accent }, { label: "Recovery", value: Math.max(0, 100 - row.recovery_confidence_pct), color: IBM_BLUE }] })),
      };
    }
    if (workspaceView === "drivers") {
      return {
        title: "Model driver split",
        caption: "Average contribution of schedule, stall, contagion, and confidence drivers.",
        twoD: {
          data: [{
            type: "bar",
            orientation: "h",
            x: breakdownAggregate.map((row) => row.value),
            y: breakdownAggregate.map((row) => row.label),
            marker: { color: breakdownAggregate.map((row) => row.key === "delay_trend" ? DARK_RED : row.key === "progress_slope" ? IBM_BLUE : row.key === "stage_stall" ? SOLID_YELLOW : row.key === "scope_risk" ? INK : ROBINHOOD_GREEN), line: { color: INK, width: 1.1 } },
            text: breakdownAggregate.map((row) => row.value.toFixed(1)),
            textposition: "outside",
            cliponaxis: false,
          }],
          layout: { ...baseLayout(300), margin: { t: 8, r: 26, b: 26, l: 150 }, xaxis: { gridcolor: SOFT }, yaxis: { automargin: true, tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: INK } } },
          config: plotConfig(),
        },
        threeD: breakdownAggregate.map((row) => ({ label: row.label, bars: [{ label: row.label, value: row.value, color: row.key === "delay_trend" ? DARK_RED : row.key === "progress_slope" ? IBM_BLUE : row.key === "stage_stall" ? SOLID_YELLOW : row.key === "scope_risk" ? INK : ROBINHOOD_GREEN }] })),
      };
    }
    if (workspaceView === "stages") {
      return {
        title: "Stage completion profile",
        caption: "Average stage completion versus residual gap across the selected rig queue.",
        twoD: {
          data: [
            { type: "bar", x: stageAggregate.map((row) => row.label), y: stageAggregate.map((row) => row.value_pct), name: "Completion", marker: { color: IBM_BLUE, line: { color: INK, width: 1.1 } } },
            { type: "bar", x: stageAggregate.map((row) => row.label), y: stageAggregate.map((row) => row.gap_pct), name: "Gap", marker: { color: SOLID_YELLOW, line: { color: INK, width: 1.1 } } },
          ],
          layout: { ...baseLayout(300), barmode: "group", margin: { t: 8, r: 18, b: 40, l: 44 }, xaxis: { tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: INK } }, yaxis: { range: [0, 100], gridcolor: SOFT, ticksuffix: "%" } },
          config: plotConfig(),
        },
        threeD: stageAggregate.map((row) => ({ label: row.label, bars: [{ label: "Complete", value: row.value_pct, color: IBM_BLUE }, { label: "Gap", value: row.gap_pct, color: SOLID_YELLOW }] })),
      };
    }
    if (workspaceView === "queue") {
      return {
        title: "Rig queue slip profile",
        caption: "Arrival delay and rig-off slip ranked by downstream disruption risk.",
        twoD: {
          data: [
            { type: "bar", x: delayRows.map((row) => shortenLabel(row.label, 18)), y: delayRows.map((row) => row.arrival), name: "Rig-On Delay", marker: { color: DARK_RED, line: { color: INK, width: 1.1 } } },
            { type: "bar", x: delayRows.map((row) => shortenLabel(row.label, 18)), y: delayRows.map((row) => row.stay), name: "Rig-Off Slip", marker: { color: IBM_BLUE, line: { color: INK, width: 1.1 } } },
          ],
          layout: { ...baseLayout(300), barmode: "group", margin: { t: 8, r: 18, b: 46, l: 40 }, xaxis: { tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: INK } }, yaxis: { gridcolor: SOFT } },
          config: plotConfig(),
        },
        threeD: delayRows.map((row) => ({ label: shortenLabel(row.label, 12), bars: [{ label: "Arrival", value: row.arrival, color: DARK_RED }, { label: "Stay", value: row.stay, color: IBM_BLUE }] })),
      };
    }
    return {
      title: "Intervention ladder",
      caption: "Highest-impact directives pulled from the live rig playbook.",
      twoD: {
        data: [{
          type: "bar",
          orientation: "h",
          x: (selectedRig?.top_actions || []).map((row) => row.impact_days),
          y: (selectedRig?.top_actions || []).map((row) => shortenLabel(row.label, 28)),
          marker: { color: (selectedRig?.top_actions || []).map((_, index) => [IBM_BLUE, SOLID_YELLOW, DARK_RED, ROBINHOOD_GREEN][index % 4]), line: { color: INK, width: 1.1 } },
          text: (selectedRig?.top_actions || []).map((row) => `${row.impact_days}d`),
          textposition: "outside",
          cliponaxis: false,
        }],
        layout: { ...baseLayout(300), margin: { t: 8, r: 26, b: 26, l: 160 }, xaxis: { gridcolor: SOFT }, yaxis: { automargin: true, tickfont: { family: "IBM Plex Mono, monospace", size: 10, color: INK } } },
        config: plotConfig(),
      },
      threeD: (selectedRig?.top_actions || []).map((row, index) => ({ label: shortenLabel(row.label, 14), bars: [{ label: row.owner, value: row.impact_days, color: [IBM_BLUE, SOLID_YELLOW, DARK_RED, ROBINHOOD_GREEN][index % 4] }] })),
    };
  }, [breakdownAggregate, delayRows, pressureRows, selectedRig, stageAggregate, workspaceView]);

  if (loading) return <div className="h-[calc(100vh-32px)]" />;
  if (error) return <div className="h-[calc(100vh-32px)]" />;

  return (
    <div
      className="min-h-[calc(100vh-32px)] overflow-y-auto bg-[#FAFAFA] text-[#111111]"
      style={{ fontFamily: "Figtree, system-ui, sans-serif" }}
    >
      <div className="mx-auto flex w-full max-w-[1820px] flex-col gap-4 px-6 py-5 lg:px-8">
        <SurfacePanel className="px-6 py-5">
          <div className="flex items-start gap-4">
            <IsoGlyph accent={IBM_BLUE} secondary="#DDE7FF" label="Rig Operations" />
            <div className="space-y-1">
              <div className="text-[24px] font-semibold tracking-[-0.04em] text-[#111111]">RIGOPS COMMAND</div>
              <MonoLabel>Institutional Rig Pressure Engine</MonoLabel>
            </div>
          </div>

          <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_auto_auto]">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search rig, well, project, or bottleneck"
              className="h-12 rounded-full border bg-white px-5 text-[15px] text-[#111111] outline-none transition-colors placeholder:text-[#8A8D94] focus:border-[#0F62FE]"
              style={{ borderColor: HAIRLINE }}
            />
            <div className="relative">
              <select
                value={selectedRig?.rig_no || ""}
                onChange={(event) => {
                  setSelectedRigId(event.target.value);
                  setFocusOverlay(null);
                }}
                disabled={!filteredRigs.length}
                className="h-12 w-full appearance-none rounded-full border bg-white pl-5 pr-10 text-[12px] font-semibold uppercase tracking-[0.16em] text-[#111111] outline-none transition-colors focus:border-[#0F62FE] disabled:cursor-not-allowed disabled:text-[#8A8D94]"
                style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: HAIRLINE }}
              >
                {filteredRigs.length ? (
                  filteredRigs.map((rig) => (
                    <option key={rig.rig_no} value={rig.rig_no}>
                      {rig.rig_no}
                    </option>
                  ))
                ) : (
                  <option value="">No rigs</option>
                )}
              </select>
              <span
                className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-[12px] font-semibold uppercase tracking-[0.12em] text-[#6F7279]"
                style={{ fontFamily: "IBM Plex Mono, monospace" }}
              >
                v
              </span>
            </div>
            <button
              onClick={() => setFocusOverlay("roster")}
              className="h-12 rounded-full border px-5 text-[12px] font-semibold uppercase tracking-[0.18em] transition-colors hover:bg-[#111111] hover:text-white"
              style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: HAIRLINE }}
            >
              Rig Matrix
            </button>
            <button
              onClick={() => void refresh()}
              className="h-12 rounded-full border px-5 text-[12px] font-semibold uppercase tracking-[0.18em] transition-colors hover:bg-[#111111] hover:text-white"
              style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: INK }}
            >
              Refresh
            </button>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2 border-t pt-3" style={{ borderColor: SOFT }}>
            <MetaChip label="Engine" value={data.engine_label || "Hybrid pressure"} accent={IBM_BLUE} />
            <MetaChip label="As Of" value={formatTimestamp(data.generated_at)} accent={INK} />
            <MetaChip label="Rigs" value={`${filteredRigs.length}/${data.rigs.length}`} accent={INK} />
            <div className="mx-1 hidden h-5 w-px bg-[#D6D8DD] lg:block" />
            <FilterChip label="All" active={filterMode === "all"} onClick={() => setFilterMode("all")} />
            <FilterChip label="Critical" active={filterMode === "critical"} accent={DARK_RED} onClick={() => setFilterMode("critical")} />
            <FilterChip label="High" active={filterMode === "high"} accent={SOLID_YELLOW} onClick={() => setFilterMode("high")} />
            <FilterChip label="Watch" active={filterMode === "watch"} accent={IBM_BLUE} onClick={() => setFilterMode("watch")} />
            <FilterChip label="Healthy" active={filterMode === "healthy"} accent={ROBINHOOD_GREEN} onClick={() => setFilterMode("healthy")} />
            <div className="mx-1 hidden h-5 w-px bg-[#D6D8DD] lg:block" />
            {summaryChips.slice(0, 2).map((chip) => (
              <SummaryChip key={chip.label} label={chip.label} value={chip.value} accent={chip.accent} />
            ))}
            {selectedRig ? (
              <SummaryChip
                label="Selected Rig"
                value={selectedRig.rig_no}
                accent={selectedRigMeta?.accent || INK}
              />
            ) : null}
            <button
              onClick={() => setFocusOverlay("brief")}
              className="rounded-full border px-3.5 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors hover:bg-[#111111] hover:text-white"
              style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: HAIRLINE }}
            >
              Metrics
            </button>
            {selectedRig ? (
              <button
                onClick={() => setFocusOverlay("brief")}
                className="rounded-full border px-3.5 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors hover:bg-[#111111] hover:text-white"
                style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: HAIRLINE }}
              >
                Model Stack
              </button>
            ) : null}
          </div>
        </SurfacePanel>
        {selectedRig ? (
          <>
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.22fr)_360px]">
              <SurfacePanel className="overflow-hidden">
                <div className="border-b px-6 py-5" style={{ borderColor: SOFT }}>
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                    <div className="space-y-2">
                      <MonoLabel>RigOps Command</MonoLabel>
                      <div className="text-[30px] font-semibold uppercase tracking-[-0.04em] text-[#111111]">Institutional Rig Pressure Engine</div>
                      <div className="text-[13px] text-[#6F7279]">{selectedRig.rig_no} | {selectedRig.dominant_bottleneck} | chart-led rig command surface</div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <SeverityPill value={selectedRig.status} />
                      <MetaChip label="Rig" value={selectedRig.rig_no} accent={INK} />
                      <MetaChip label="Queue" value={`${selectedRig.queue_exposure}`} accent={IBM_BLUE} />
                      <MetaChip label="Bottleneck" value={selectedRig.dominant_bottleneck} accent={IBM_BLUE} />
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap items-center gap-2">
                    {(["pressure", "drivers", "stages", "queue", "playbook"] as WorkspaceView[]).map((view) => (
                      <FilterChip key={view} label={view} active={workspaceView === view} onClick={() => setWorkspaceView(view)} />
                    ))}
                    <div className="mx-1 hidden h-5 w-px bg-[#D6D8DD] lg:block" />
                    <div className="flex items-center gap-2 rounded-full border bg-white p-1" style={{ borderColor: SOFT }}>
                      <FilterChip label="2D" active={chartMode === "2d"} onClick={() => setChartMode("2d")} />
                      <FilterChip label="3D" active={chartMode === "3d"} onClick={() => setChartMode("3d")} />
                    </div>
                    <div className="mx-1 hidden h-5 w-px bg-[#D6D8DD] lg:block" />
                    <button
                      onClick={() => setFocusOverlay("chart")}
                      className="rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors hover:bg-[#111111] hover:text-white"
                      style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: HAIRLINE }}
                    >
                      Focus Chart
                    </button>
                    <button
                      onClick={() => setFocusOverlay("wells")}
                      className="rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors hover:bg-[#111111] hover:text-white"
                      style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: HAIRLINE }}
                    >
                      Well Queue
                    </button>
                    <button
                      onClick={() => setFocusOverlay("brief")}
                      className="rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors hover:bg-[#111111] hover:text-white"
                      style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: HAIRLINE }}
                    >
                      Quant Brief
                    </button>
                  </div>
                </div>

                <div className="p-6">
                  <div className="overflow-hidden rounded-[24px] border bg-white p-4" style={{ borderColor: SOFT }}>
                    <div className="min-w-0 overflow-hidden">
                      {chartMode === "2d" ? (
                        // @ts-ignore
                        <Plot data={workspaceSpec.twoD.data} layout={{ ...workspaceSpec.twoD.layout, height: 560 }} config={workspaceSpec.twoD.config} style={{ width: "100%", height: "100%" }} useResizeHandler />
                      ) : (
                        <div className="h-[560px]">
                          <ExtrudedBarsChart groups={workspaceSpec.threeD} maxValue={100} />
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-4">
                    <DossierMetric label="Pressure" value={formatNumber(selectedRig.pressure_score, 1)} accent={selectedRigMeta?.accent || INK} />
                    <DossierMetric label="Recovery" value={`${selectedRig.recovery_confidence_pct}%`} accent={ROBINHOOD_GREEN} />
                    <DossierMetric label="Avg Gap" value={`${formatNumber(rigAvgGap, 1)}%`} accent={IBM_BLUE} />
                    <DossierMetric label="Avg Slip" value={`${formatNumber(rigAvgSlip, 1)}d`} accent={DARK_RED} />
                  </div>
                </div>
              </SurfacePanel>

              <div className="space-y-4">
                <SurfacePanel className="overflow-hidden">
                  <div className="border-b px-5 py-4" style={{ borderColor: SOFT }}>
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <MonoLabel>Monitoring Rail</MonoLabel>
                        <div className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-[#111111]">Selected well</div>
                      </div>
                      {selectedWell ? <SeverityPill value={selectedWell.ops_risk_tier} /> : null}
                    </div>
                  </div>
                  <div className="space-y-4 px-5 py-5">
                    <div>
                      <div className="text-[24px] font-semibold tracking-[-0.04em] text-[#111111]">{selectedWell?.well_name || 'Awaiting well'}</div>
                      {selectedWell ? <div className="mt-1 text-[13px] text-[#6F7279]">{selectedWell.project} | {selectedWell.rig_status}</div> : null}
                    </div>

                    {selectedWell ? (
                      <>
                        <div className="grid grid-cols-2 gap-3">
                          <DossierMetric label="Rig-On" value={`${selectedWell.rig_on_delay_days}d`} accent={selectedWell.rig_on_delay_days > 0 ? DARK_RED : INK} />
                          <DossierMetric label="Rig-Off" value={`${selectedWell.delay_days}d`} accent={selectedWell.delay_days > 0 ? DARK_RED : INK} />
                          <DossierMetric label="Gap" value={`${formatNumber(selectedWell.current_month_gap_pct, 1)}%`} accent={IBM_BLUE} />
                          <DossierMetric label="Velocity" value={`${formatNumber(selectedWell.velocity_pct, 1)}%`} accent={selectedWell.velocity_pct < 0 ? DARK_RED : ROBINHOOD_GREEN} />
                        </div>

                        <div className="space-y-2">
                          {(selectedWell.evidence || []).slice(0, 3).map((item, index) => (
                            <div key={`${item}-${index}`} className="rounded-[16px] border bg-white px-4 py-3 text-[13px] leading-6 text-[#343741]" style={{ borderColor: SOFT }}>
                              <span className="mr-2 inline-flex rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em]" style={{ backgroundColor: index === 0 ? '#FBE9E9' : '#EAF1FF', color: index === 0 ? DARK_RED : IBM_BLUE, fontFamily: 'IBM Plex Mono, monospace' }}>
                                {`Signal ${index + 1}`}
                              </span>
                              {item}
                            </div>
                          ))}
                        </div>

                        <div className="flex flex-wrap gap-2">
                          <MetaChip label="Queue" value={`${selectedWell.queue_exposure}`} accent={IBM_BLUE} />
                          <MetaChip label="Rank" value={`#${selectedWellRank}/${visibleWells.length}`} accent={INK} />
                          {selectedWell.anomaly_flag ? <MetaChip label="Anomaly" value="Flagged" accent={DARK_RED} /> : null}
                          {selectedWell.missing_fields > 0 ? <MetaChip label="Data" value={`${selectedWell.missing_fields} gap`} accent={SOLID_YELLOW} /> : null}
                        </div>
                      </>
                    ) : (
                      <div className="rounded-[16px] border bg-white px-4 py-4 text-[13px] text-[#6F7279]" style={{ borderColor: SOFT }}>
                        Open the well queue when you want record-level drill down.
                      </div>
                    )}
                  </div>
                </SurfacePanel>

                <SurfacePanel className="overflow-hidden">
                  <div className="border-b px-5 py-4" style={{ borderColor: SOFT }}>
                    <MonoLabel>Quick Actions</MonoLabel>
                    <div className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-[#111111]">Command shortcuts</div>
                  </div>
                  <div className="grid gap-3 px-5 py-5">
                    <button
                      onClick={() => { setWorkspaceView("stages"); setFocusOverlay("chart"); }}
                      className="flex items-center justify-between rounded-[16px] border bg-white px-4 py-4 text-left transition-colors hover:bg-[#111111] hover:text-white"
                      style={{ borderColor: SOFT }}
                    >
                      <span className="text-[14px] font-semibold tracking-[-0.02em]">Open stage pulse</span>
                      <span className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ fontFamily: 'IBM Plex Mono, monospace' }}>chart</span>
                    </button>
                    <button
                      onClick={() => { setWorkspaceView("playbook"); setFocusOverlay("chart"); }}
                      className="flex items-center justify-between rounded-[16px] border bg-white px-4 py-4 text-left transition-colors hover:bg-[#111111] hover:text-white"
                      style={{ borderColor: SOFT }}
                    >
                      <span className="text-[14px] font-semibold tracking-[-0.02em]">Open intervention playbook</span>
                      <span className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ fontFamily: 'IBM Plex Mono, monospace' }}>action</span>
                    </button>
                    <button
                      onClick={() => setFocusOverlay("wells")}
                      className="flex items-center justify-between rounded-[16px] border bg-white px-4 py-4 text-left transition-colors hover:bg-[#111111] hover:text-white"
                      style={{ borderColor: SOFT }}
                    >
                      <span className="text-[14px] font-semibold tracking-[-0.02em]">Open well queue</span>
                      <span className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ fontFamily: 'IBM Plex Mono, monospace' }}>drill</span>
                    </button>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        onClick={() => setFocusOverlay("roster")}
                        className="rounded-[16px] border bg-white px-4 py-4 text-left text-[13px] font-semibold tracking-[-0.02em] transition-colors hover:bg-[#111111] hover:text-white"
                        style={{ borderColor: SOFT }}
                      >
                        Rig Matrix
                      </button>
                      <button
                        onClick={() => setFocusOverlay("brief")}
                        className="rounded-[16px] border bg-white px-4 py-4 text-left text-[13px] font-semibold tracking-[-0.02em] transition-colors hover:bg-[#111111] hover:text-white"
                        style={{ borderColor: SOFT }}
                      >
                        Quant Brief
                      </button>
                    </div>
                  </div>
                </SurfacePanel>

                <SurfacePanel className="overflow-hidden">
                  <div className="border-b px-5 py-4" style={{ borderColor: SOFT }}>
                    <MonoLabel>Model Visibility</MonoLabel>
                    <div className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-[#111111]">What the engine is using</div>
                  </div>
                  <div className="space-y-3 px-5 py-5 text-[13px]">
                    <div className="flex items-center justify-between gap-4"><span className="text-[#6F7279]">Engine</span><span className="font-semibold text-[#0F62FE]">{data.engine_label || 'Hybrid pressure'}</span></div>
                    <div className="flex items-center justify-between gap-4"><span className="text-[#6F7279]">Outlier layer</span><span className="font-semibold text-[#8E1B1B]">CPU Isolation Forest</span></div>
                    {rigQuantChips.map((chip) => (
                      <div key={`line-${chip.label}`} className="flex items-center justify-between gap-4"><span className="text-[#6F7279]">{chip.label}</span><span className="font-semibold" style={{ color: chip.accent }}>{chip.value}</span></div>
                    ))}
                  </div>
                </SurfacePanel>
              </div>
            </div>

            <SurfacePanel className="overflow-hidden">
              <div className="flex items-center justify-between gap-4 border-b px-6 py-5" style={{ borderColor: SOFT }}>
                <div>
                  <MonoLabel>Rig Deck</MonoLabel>
                  <div className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-[#111111]">Pressure-ranked selection strip</div>
                </div>
                <button
                  onClick={() => setFocusOverlay("roster")}
                  className="rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors hover:bg-[#111111] hover:text-white"
                  style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: HAIRLINE }}
                >
                  Full Rig Matrix
                </button>
              </div>
              <div className="overflow-x-auto px-5 py-5">
                {filteredRigs.length ? (
                  <div className="flex min-w-max gap-3 pr-4">
                    {filteredRigs.slice(0, 8).map((rig) => {
                      const selected = rig.rig_no === selectedRig.rig_no;
                      const meta = tierMeta(rig.status);
                      return (
                        <button
                          key={`strip-${rig.rig_no}`}
                          onClick={() => setSelectedRigId(rig.rig_no)}
                          className="w-[248px] rounded-[20px] border px-4 py-4 text-left transition-colors hover:bg-[#FCFCFD]"
                          style={{ borderColor: selected ? meta.accent : SOFT, backgroundColor: selected ? meta.tint : PAPER }}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <MonoLabel>{`Rank ${rig.pressure_rank}`}</MonoLabel>
                              <div className="mt-2 text-[22px] font-semibold tracking-[-0.05em] text-[#111111]">{rig.rig_no}</div>
                            </div>
                            <SeverityPill value={rig.status} />
                          </div>
                          <div className="mt-4 grid grid-cols-2 gap-2">
                            <DossierMetric label="Pressure" value={formatNumber(rig.pressure_score, 1)} accent={meta.accent} />
                            <DossierMetric label="Recovery" value={`${rig.recovery_confidence_pct}%`} accent={ROBINHOOD_GREEN} />
                          </div>
                        </button>
                      )
                    })}
                  </div>
                ) : (
                  <div className="rounded-[20px] border border-dashed bg-[#FCFCFD] px-4 py-6 text-[13px] text-[#6F7279]" style={{ borderColor: SOFT }}>
                    No rigs match the current scope.
                  </div>
                )}
              </div>
            </SurfacePanel>
          </>
        ) : (
          <SurfacePanel className="px-8 py-16">
            <div className="text-center text-[14px] text-[#6F7279]">No rig data available for the current scope.</div>
          </SurfacePanel>
        )}
        {focusOverlay === "roster" ? (
          <div className="fixed inset-0 z-50 bg-[rgba(15,23,42,0.56)] px-6 py-6">
            <div className="mx-auto flex h-full w-full max-w-[1480px] flex-col rounded-[28px] border bg-white shadow-[0_24px_64px_rgba(17,17,17,0.18)]" style={{ borderColor: HAIRLINE }}>
              <div className="flex items-start justify-between gap-4 border-b px-6 py-5" style={{ borderColor: SOFT }}>
                <div>
                  <MonoLabel>Rig Matrix</MonoLabel>
                  <div className="mt-2 text-[28px] font-semibold tracking-[-0.05em] text-[#111111]">Direct rig selection</div>
                  <div className="mt-1 text-[13px] text-[#6F7279]">Choose a rig first, then move into pressure, drivers, stages, queue, and actions.</div>
                </div>
                <button
                  onClick={() => setFocusOverlay(null)}
                  className="rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors hover:bg-[#111111] hover:text-white"
                  style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: INK }}
                >
                  Close
                </button>
              </div>

              <div className="grid min-h-0 flex-1 gap-4 p-6 lg:grid-cols-12">
                <div className="lg:col-span-8 min-h-0 overflow-y-auto">
                  <div className="grid gap-3 lg:grid-cols-2">
                    {filteredRigs.map((rig) => {
                      const meta = tierMeta(rig.status);
                      const selected = rig.rig_no === selectedRig?.rig_no;
                      return (
                        <button
                          key={`overlay-${rig.rig_no}`}
                          onClick={() => {
                            setSelectedRigId(rig.rig_no);
                            setFocusOverlay(null);
                          }}
                          className="rounded-[22px] border px-5 py-4 text-left transition-colors hover:bg-[#FCFCFD]"
                          style={{ borderColor: selected ? meta.accent : SOFT, backgroundColor: selected ? meta.tint : PAPER }}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <MonoLabel>{`Rank ${rig.pressure_rank}`}</MonoLabel>
                              <div className="mt-2 text-[24px] font-semibold tracking-[-0.05em] text-[#111111]">{rig.rig_no}</div>
                            </div>
                            <SeverityPill value={rig.status} />
                          </div>
                          <div className="mt-4 grid grid-cols-2 gap-3">
                            <DossierMetric label="Pressure" value={formatNumber(rig.pressure_score, 1)} accent={meta.accent} />
                            <DossierMetric label="Recovery" value={`${rig.recovery_confidence_pct}%`} accent={ROBINHOOD_GREEN} />
                          </div>
                          <div className="mt-4 flex flex-wrap gap-2">
                            <MetaChip label="Queue" value={`${rig.queue_exposure}`} accent={IBM_BLUE} />
                            <MetaChip label="Critical" value={`${rig.critical_wells}`} accent={DARK_RED} />
                            <MetaChip label="Active" value={`${rig.active_wells}`} accent={INK} />
                            <MetaChip label="Bottleneck" value={rig.dominant_bottleneck} accent={SOLID_YELLOW} />
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="lg:col-span-4 min-h-0 overflow-y-auto space-y-4">
                  {selectedRig ? (
                    <>
                      <div className="rounded-[22px] border bg-[#FCFCFD] px-5 py-5" style={{ borderColor: SOFT }}>
                        <MonoLabel>Current Rig</MonoLabel>
                        <div className="mt-2 text-[26px] font-semibold tracking-[-0.05em] text-[#111111]">{selectedRig.rig_no}</div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <MetaChip label="Pressure" value={formatNumber(selectedRig.pressure_score, 1)} accent={selectedRigMeta?.accent || INK} />
                          <MetaChip label="Queue" value={`${selectedRig.queue_exposure}`} accent={IBM_BLUE} />
                          <MetaChip label="Recovery" value={`${selectedRig.recovery_confidence_pct}%`} accent={ROBINHOOD_GREEN} />
                        </div>
                      </div>
                      <div className="rounded-[22px] border bg-[#FCFCFD] px-5 py-5" style={{ borderColor: SOFT }}>
                        <MonoLabel>Quant Surface</MonoLabel>
                        <div className="mt-4 flex flex-wrap gap-2">
                          {rigQuantChips.map((chip) => (
                            <MetaChip key={`overlay-${chip.label}`} label={chip.label} value={chip.value} accent={chip.accent} />
                          ))}
                        </div>
                      </div>
                      <div className="rounded-[22px] border bg-[#FCFCFD] px-5 py-5" style={{ borderColor: SOFT }}>
                        <MonoLabel>Drill Down</MonoLabel>
                        <div className="mt-3 space-y-3 text-[13px] text-[#4A4E57]">
                          <div className="rounded-[16px] border bg-white px-4 py-3" style={{ borderColor: SOFT }}>
                            Select a rig here, then use the center workspace for charts and the right dossier for evidence.
                          </div>
                          <div className="rounded-[16px] border bg-white px-4 py-3" style={{ borderColor: SOFT }}>
                            Open <span className="font-semibold text-[#111111]">Model Stack</span> to explain the quant layer, then <span className="font-semibold text-[#111111]">Focus</span> for chart detail.
                          </div>
                        </div>
                      </div>
                    </>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {focusOverlay === "wells" && selectedRig ? (
          <div className="fixed inset-0 z-50 bg-[rgba(15,23,42,0.56)] px-6 py-6">
            <div className="mx-auto flex h-full w-full max-w-[1480px] flex-col rounded-[28px] border bg-white shadow-[0_24px_64px_rgba(17,17,17,0.18)]" style={{ borderColor: HAIRLINE }}>
              <div className="flex items-start justify-between gap-4 border-b px-6 py-5" style={{ borderColor: SOFT }}>
                <div>
                  <MonoLabel>Well Queue</MonoLabel>
                  <div className="mt-2 text-[28px] font-semibold tracking-[-0.05em] text-[#111111]">{selectedRig.rig_no} live roster</div>
                  <div className="mt-1 text-[13px] text-[#6F7279]">Choose a well here. The main cockpit stays focused on the chart.</div>
                </div>
                <button
                  onClick={() => setFocusOverlay(null)}
                  className="rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors hover:bg-[#111111] hover:text-white"
                  style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: INK }}
                >
                  Close
                </button>
              </div>

              <div className="grid min-h-0 flex-1 gap-4 p-6 lg:grid-cols-12">
                <div className="min-h-0 overflow-hidden rounded-[22px] border bg-[#FCFCFD] lg:col-span-8" style={{ borderColor: SOFT }}>
                  <div className="grid grid-cols-[minmax(0,1.3fr)_110px_90px_84px_96px_140px] gap-3 border-b px-5 py-4 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: SOFT }}>
                    <div>Well</div>
                    <div>Tier</div>
                    <div>Pressure</div>
                    <div>Progress</div>
                    <div>Delay</div>
                    <div>Bottleneck</div>
                  </div>
                  <div className="min-h-0 h-[calc(100%-56px)] overflow-y-auto px-4 py-3">
                    <div className="space-y-2">
                      {visibleWells.map((well) => {
                        const selected = selectedWell?.well_id === well.well_id;
                        const meta = tierMeta(well.ops_risk_tier);
                        const delay = well.delay_days + well.rig_on_delay_days;
                        return (
                          <button
                            key={`queue-${well.well_id}`}
                            onClick={() => {
                              setSelectedWellId(well.well_id);
                              setFocusOverlay(null);
                            }}
                            className="grid w-full grid-cols-[minmax(0,1.3fr)_110px_90px_84px_96px_140px] items-center gap-3 rounded-[18px] border px-3 py-3 text-left transition-colors hover:bg-white"
                            style={{ borderColor: selected ? meta.accent : SOFT, backgroundColor: selected ? meta.tint : PAPER }}
                          >
                            <div className="min-w-0">
                              <div className="truncate text-[15px] font-semibold tracking-[-0.03em] text-[#111111]">{well.well_name}</div>
                              <div className="mt-1 truncate text-[12px] text-[#6F7279]">{well.project}</div>
                            </div>
                            <div><SeverityPill value={well.ops_risk_tier} /></div>
                            <div className="text-[15px] font-semibold text-[#111111]">{formatNumber(well.ops_risk_score, 1)}</div>
                            <div className="text-[15px] font-semibold text-[#111111]">{Math.round(well.progress_pct)}%</div>
                            <div className="text-[15px] font-semibold" style={{ color: delay > 0 ? DARK_RED : ROBINHOOD_GREEN }}>{delay > 0 ? `+${delay}d` : "Track"}</div>
                            <div className="truncate text-[13px] font-medium text-[#4A4E57]">{well.dominant_bottleneck}</div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <div className="min-h-0 overflow-y-auto space-y-4 lg:col-span-4">
                  {selectedWell ? (
                    <div className="rounded-[22px] border bg-[#FCFCFD] px-5 py-5" style={{ borderColor: SOFT }}>
                      <MonoLabel>Selected Well</MonoLabel>
                      <div className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-[#111111]">{selectedWell.well_name}</div>
                      <div className="mt-1 text-[13px] text-[#6F7279]">{selectedWell.project} | {selectedWell.rig_no}</div>
                      <div className="mt-4 grid grid-cols-2 gap-3">
                        <DossierMetric label="Pressure" value={formatNumber(selectedWell.ops_risk_score, 1)} accent={tierMeta(selectedWell.ops_risk_tier).accent} />
                        <DossierMetric label="Recovery" value={`${selectedWell.recovery_confidence_pct}%`} accent={ROBINHOOD_GREEN} />
                        <DossierMetric label="Gap" value={`${formatNumber(selectedWell.current_month_gap_pct, 1)}%`} accent={IBM_BLUE} />
                        <DossierMetric label="Queue" value={`${selectedWell.queue_exposure}`} accent={IBM_BLUE} />
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {focusOverlay === "chart" && selectedRig ? (
          <div className="fixed inset-0 z-50 bg-[rgba(15,23,42,0.56)] px-6 py-6">
            <div className="mx-auto flex h-full w-full max-w-[1480px] flex-col rounded-[28px] border bg-white shadow-[0_24px_64px_rgba(17,17,17,0.18)]" style={{ borderColor: HAIRLINE }}>
              <div className="flex items-start justify-between gap-4 border-b px-6 py-5" style={{ borderColor: SOFT }}>
                <div>
                  <MonoLabel>Focus Surface</MonoLabel>
                  <div className="mt-2 text-[28px] font-semibold tracking-[-0.05em] text-[#111111]">{workspaceSpec.title}</div>
                  <div className="mt-1 text-[13px] text-[#6F7279]">{selectedRig.rig_no} • {workspaceSpec.caption}</div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-2 rounded-full border bg-white p-1" style={{ borderColor: SOFT }}>
                    <FilterChip label="2D" active={chartMode === "2d"} onClick={() => setChartMode("2d")} />
                    <FilterChip label="3D" active={chartMode === "3d"} onClick={() => setChartMode("3d")} />
                  </div>
                  <button
                    onClick={() => setFocusOverlay(null)}
                    className="rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors hover:bg-[#111111] hover:text-white"
                    style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: INK }}
                  >
                    Close
                  </button>
                </div>
              </div>

              <div className="grid min-h-0 flex-1 gap-4 p-6 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="min-h-0 overflow-hidden rounded-[22px] border bg-[#FCFCFD] p-4" style={{ borderColor: SOFT }}>
                  <div className="h-full min-w-0 overflow-hidden">
                    {chartMode === "2d" ? (
                      // @ts-ignore
                      <Plot data={workspaceSpec.twoD.data} layout={{ ...workspaceSpec.twoD.layout, height: 640 }} config={workspaceSpec.twoD.config} style={{ width: "100%", height: "100%" }} useResizeHandler />
                    ) : (
                      <ExtrudedBarsChart groups={workspaceSpec.threeD} maxValue={100} />
                    )}
                  </div>
                </div>

                <div className="min-h-0 overflow-y-auto space-y-3">
                  <div className="rounded-[20px] border bg-[#FCFCFD] px-4 py-4" style={{ borderColor: SOFT }}>
                    <MonoLabel>Selected Rig</MonoLabel>
                    <div className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-[#111111]">{selectedRig.rig_no}</div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <MetaChip label="Pressure" value={formatNumber(selectedRig.pressure_score, 1)} accent={tierMeta(selectedRig.status).accent} />
                      <MetaChip label="Queue" value={`${selectedRig.queue_exposure}`} accent={IBM_BLUE} />
                      <MetaChip label="Recovery" value={`${selectedRig.recovery_confidence_pct}%`} accent={ROBINHOOD_GREEN} />
                    </div>
                  </div>
                  <div className="rounded-[20px] border bg-[#FCFCFD] px-4 py-4" style={{ borderColor: SOFT }}>
                    <MonoLabel>Visible Signals</MonoLabel>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {rigQuantChips.map((chip) => (
                        <MetaChip key={chip.label} label={chip.label} value={chip.value} accent={chip.accent} />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {focusOverlay === "brief" ? (
          <div className="fixed inset-0 z-50 bg-[rgba(15,23,42,0.56)] px-6 py-6">
            <div className="mx-auto flex h-full w-full max-w-[1320px] flex-col rounded-[28px] border bg-white shadow-[0_24px_64px_rgba(17,17,17,0.18)]" style={{ borderColor: HAIRLINE }}>
              <div className="flex items-start justify-between gap-4 border-b px-6 py-5" style={{ borderColor: SOFT }}>
                <div>
                  <MonoLabel>Rig Brief</MonoLabel>
                  <div className="mt-2 text-[28px] font-semibold tracking-[-0.05em] text-[#111111]">Quant and model summary</div>
                  <div className="mt-1 text-[13px] text-[#6F7279]">Compact executive view for the client video: portfolio metrics, rig stack, and model layers.</div>
                </div>
                <button
                  onClick={() => setFocusOverlay(null)}
                  className="rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors hover:bg-[#111111] hover:text-white"
                  style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: INK }}
                >
                  Close
                </button>
              </div>

              <div className="grid min-h-0 flex-1 gap-4 p-6 lg:grid-cols-[minmax(0,1.15fr)_420px]">
                <div className="min-h-0 overflow-y-auto space-y-4">
                  <div className="rounded-[22px] border bg-[#FCFCFD] px-5 py-5" style={{ borderColor: SOFT }}>
                    <MonoLabel>Portfolio Metrics</MonoLabel>
                    <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                      {summaryChips.map((chip) => (
                        <div key={chip.label} className="rounded-[16px] border bg-white px-4 py-3" style={{ borderColor: SOFT }}>
                          <MonoLabel>{chip.label}</MonoLabel>
                          <div className="mt-2 text-[24px] font-semibold tracking-[-0.04em]" style={{ color: chip.accent }}>
                            {chip.value}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {selectedRig ? (
                    <div className="rounded-[22px] border bg-[#FCFCFD] px-5 py-5" style={{ borderColor: SOFT }}>
                      <MonoLabel>Rig Quant Stack</MonoLabel>
                      <div className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-[#111111]">{selectedRig.rig_no}</div>
                      <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                        <div className="rounded-[16px] border bg-white px-4 py-3" style={{ borderColor: SOFT }}>
                          <MonoLabel>Engine</MonoLabel>
                          <div className="mt-2 text-[18px] font-semibold tracking-[-0.03em]" style={{ color: IBM_BLUE }}>
                            {data.engine_label || "Hybrid pressure"}
                          </div>
                        </div>
                        <div className="rounded-[16px] border bg-white px-4 py-3" style={{ borderColor: SOFT }}>
                          <MonoLabel>Outlier Layer</MonoLabel>
                          <div className="mt-2 text-[18px] font-semibold tracking-[-0.03em]" style={{ color: selectedRig.anomaly_count > 0 ? DARK_RED : ROBINHOOD_GREEN }}>
                            CPU Isolation Forest
                          </div>
                        </div>
                        {rigQuantChips.map((chip) => (
                          <div key={chip.label} className="rounded-[16px] border bg-white px-4 py-3" style={{ borderColor: SOFT }}>
                            <MonoLabel>{chip.label}</MonoLabel>
                            <div className="mt-2 text-[22px] font-semibold tracking-[-0.04em]" style={{ color: chip.accent }}>
                              {chip.value}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>

                <div className="min-h-0 overflow-y-auto space-y-4">
                  {selectedWell ? (
                    <div className="rounded-[22px] border bg-[#FCFCFD] px-5 py-5" style={{ borderColor: SOFT }}>
                      <MonoLabel>Selected Well</MonoLabel>
                      <div className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-[#111111]">{selectedWell.well_name}</div>
                      <div className="mt-1 text-[13px] text-[#6F7279]">{selectedWell.project} • {selectedWell.rig_no}</div>
                      <div className="mt-4 grid grid-cols-2 gap-3">
                        <DossierMetric label="Pressure" value={formatNumber(selectedWell.ops_risk_score, 1)} accent={tierMeta(selectedWell.ops_risk_tier).accent} />
                        <DossierMetric label="Recovery" value={`${selectedWell.recovery_confidence_pct}%`} accent={ROBINHOOD_GREEN} />
                        <DossierMetric label="Gap" value={`${formatNumber(selectedWell.current_month_gap_pct, 1)}%`} accent={IBM_BLUE} />
                        <DossierMetric label="Queue" value={`${selectedWell.queue_exposure}`} accent={IBM_BLUE} />
                      </div>
                    </div>
                  ) : null}

                  <div className="rounded-[22px] border bg-[#FCFCFD] px-5 py-5" style={{ borderColor: SOFT }}>
                    <MonoLabel>Presentation Notes</MonoLabel>
                    <div className="mt-4 space-y-3 text-[13px] text-[#4A4E57]">
                      <div className="rounded-[16px] border bg-white px-4 py-3" style={{ borderColor: SOFT }}>
                        Show the fleet rank on the left, then open this brief to explain the model layers.
                      </div>
                      <div className="rounded-[16px] border bg-white px-4 py-3" style={{ borderColor: SOFT }}>
                        Use the chart focus modal for the visual demonstration, then return to the dossier for evidence and actions.
                      </div>
                      <div className="rounded-[16px] border bg-white px-4 py-3" style={{ borderColor: SOFT }}>
                        The client will see both the premium UI and the actual quant logic without needing a long spoken explanation.
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
