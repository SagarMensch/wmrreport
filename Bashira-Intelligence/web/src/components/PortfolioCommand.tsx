"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";

import {
  ErrorState,
  formatCompactNumber,
  formatPct,
  LoadingState,
  SurfacePanel,
  TonePill,
} from "@/components/CommandCenterPrimitives";
import { useCommandCenterData } from "@/components/useCommandCenterData";
import ChartViewToggle from "@/components/ChartViewToggle";
import {
  buildTreemap,
  buildScatter,
  buildDonut,
  buildRiskSurface3D,
  buildScatter3D,
  buildTreemap3D,
  buildDonut3D,
  DESERT_CONFIG,
  SERIES_COLORS,
} from "@/components/DesertPlotly";

const Plot = dynamic(() => import("@/components/PlotlyClient"), { ssr: false });

/* ── Data Contracts ─────────────────────────────────────────────────────── */

interface PortfolioCard {
  project: string;
  status: string;
  health_band: string;
  open_wells: number;
  completed_wells: number;
  total_wells: number;
  delayed_wells: number;
  critical_wells: number;
  risk_badges: number;
  avg_progress_pct: number;
  avg_delay_probability_pct: number;
  max_delay_probability_pct: number;
  max_delay_days: number;
  p95_delay_exposure_days?: number;
  expected_delay_days?: number;
  risk_price?: number;
  nhpp_intensity?: number;
  cluster_count: number;
  lead_rig: string;
  last_updated: string | null;
}

interface PortfolioWell {
  well_name: string;
  project: string;
  rig_no: string;
  delay_days: number;
  risk_score: number;
  risk_tier: string;
  progress_pct: number;
}

interface AgenticFeedItem {
  project: string;
  trigger: string;
  action: string;
  recommendation: string;
}

interface PortfolioPayload {
  generated_at?: string;
  summary: {
    total_projects?: number;
    active_projects?: number;
    total_wells?: number;
    avg_progress_pct?: number;
    avg_delay_probability_pct?: number;
    projects_under_pressure?: number;
  };
  status_mix: { label: string; count: number }[];
  project_cards: PortfolioCard[];
  top_wells: PortfolioWell[];
  agentic_feed?: AgenticFeedItem[];
}

const EMPTY_DATA: PortfolioPayload = {
  summary: {},
  status_mix: [],
  project_cards: [],
  top_wells: [],
};

/* ── Visual helpers ─────────────────────────────────────────────────────── */

function toneForBand(band: string) {
  if (band === "Critical") return "critical" as const;
  if (band === "Watch") return "warning" as const;
  return "positive" as const;
}

function toneForRisk(riskTier: string) {
  if (riskTier === "CRITICAL") return "critical" as const;
  if (riskTier === "HIGH_RISK" || riskTier === "WATCH") return "warning" as const;
  return "neutral" as const;
}

function bandDotColor(band: string) {
  if (band === "Critical") return "#a91101"; // dark red
  if (band === "Watch") return "#ffd700"; // solid yellow
  return "#00c805"; // robinhood green
}

function progressBarBg(band: string) {
  if (band === "Critical") return "bg-[#a91101]";
  if (band === "Watch") return "bg-[#ffd700]";
  return "bg-[#00c805]";
}

function formatTimestamp(value?: string | null) {
  if (!value) return "Awaiting refresh";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value.replace("T", " ").slice(0, 16);
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function formatCurrency(value?: number) {
  if (value === undefined || value === null) return "$0";
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}k`;
  return `$${value.toFixed(0)}`;
}

/* ── Component ──────────────────────────────────────────────────────────── */

export default function PortfolioCommand() {
  const [filter, setFilter] = useState<"all" | "active" | "inactive">("all");
  const [expandedProject, setExpandedProject] = useState<string | null>(null);
  const [chartTab, setChartTab] = useState<"treemap" | "scatter" | "composition" | "topology">("topology");

  const { data, loading, error, refresh } = useCommandCenterData<PortfolioPayload>(
    "portfolio",
    EMPTY_DATA,
  );

  const filteredCards = useMemo(() => {
    const cards = data.project_cards.filter((card) => {
      if (filter === "active") return card.status === "Active";
      if (filter === "inactive") return card.status === "Inactive";
      return true;
    });
    return cards.sort((a, b) => {
      const sa = a.avg_delay_probability_pct * 0.55 + a.critical_wells * 8 + a.delayed_wells * 4;
      const sb = b.avg_delay_probability_pct * 0.55 + b.critical_wells * 8 + b.delayed_wells * 4;
      return sb - sa;
    });
  }, [data.project_cards, filter]);

  const pressureIndex = Math.round(
    Math.min(
      99,
      (Number(data.summary.avg_delay_probability_pct ?? 0) * 0.62) +
        ((Number(data.summary.projects_under_pressure ?? 0) /
          Math.max(Number(data.summary.total_projects ?? 1), 1)) * 38),
    ),
  );

  const maxPressure = useMemo(() => {
    if (!filteredCards.length) return 1;
    return Math.max(
      1,
      ...filteredCards.map(
        (c) => c.avg_delay_probability_pct * 0.68 + c.delayed_wells * 4.5 + c.critical_wells * 6,
      ),
    );
  }, [filteredCards]);

  /* ── Chart data ── */

  const treemapData = useMemo(() => {
    return buildTreemap(
      filteredCards.map((card) => ({
        label: card.project,
        value: card.total_wells,
        color: bandDotColor(card.health_band),
      })),
    );
  }, [filteredCards]);

  const treemapData3D = useMemo(() => {
    return buildTreemap3D(
      filteredCards.map((card) => ({
        label: card.project,
        value: card.total_wells,
        color: bandDotColor(card.health_band),
      })),
    );
  }, [filteredCards]);

  const scatterData = useMemo(() => {
    return buildScatter(
      filteredCards.map((card) => ({
        x: card.avg_progress_pct,
        y: card.avg_delay_probability_pct,
        label: card.project.length > 12 ? card.project.slice(0, 10) + "…" : card.project,
        color: bandDotColor(card.health_band),
        size: 8 + Math.min(10, card.total_wells * 1.5),
      })),
      "Progress %",
      "Delay Probability %",
    );
  }, [filteredCards]);

  const scatterData3D = useMemo(() => {
    return buildScatter3D(
      filteredCards.map((card) => ({
        x: card.avg_progress_pct,
        y: card.avg_delay_probability_pct,
        z: (card.avg_delay_probability_pct * 0.55 + card.critical_wells * 8), // Compound risk index as Z
        label: card.project.length > 12 ? card.project.slice(0, 10) + "…" : card.project,
        color: bandDotColor(card.health_band),
        size: 8 + Math.min(10, card.total_wells * 1.5),
      })),
      "Progress %",
      "Delay Probability %",
      "Compound Risk",
    );
  }, [filteredCards]);

  const statusDonut = useMemo(() => {
    return buildDonut(
      data.status_mix.map((item, i) => ({
        label: item.label,
        value: item.count,
        color: SERIES_COLORS[i % SERIES_COLORS.length],
      })),
    );
  }, [data.status_mix]);

  const statusDonut3D = useMemo(() => {
    return buildDonut3D(
      data.status_mix.map((item, i) => ({
        label: item.label,
        value: item.count,
        color: SERIES_COLORS[i % SERIES_COLORS.length],
      })),
    );
  }, [data.status_mix]);

  const surfaceData = useMemo(() => {
    return buildRiskSurface3D(
      filteredCards.map((card, i) => ({
        x: i,
        y: card.avg_progress_pct,
        z: card.avg_delay_probability_pct,
      })),
      "Execution Risk Topography"
    );
  }, [filteredCards]);

  const LIGHT_LAYOUT_OVERRIDES = {
    paper_bgcolor: "#FFFFFF",
    plot_bgcolor: "#FFFFFF",
    font: { color: "#000000", family: '"Figtree", sans-serif' },
    xaxis: { gridcolor: "#E5E5E5", zerolinecolor: "#000000", title: { font: { color: "#000000", size: 10 } } },
    yaxis: { gridcolor: "#E5E5E5", zerolinecolor: "#000000", title: { font: { color: "#000000", size: 10 } } },
  };

  return (
    <div className="h-full overflow-y-auto bg-white">
      <div className="mx-auto flex w-full max-w-[1540px] flex-col gap-0 px-5 py-5">
        {/* ── HERO — Light Clean Command Bar ── */}
        <section className="overflow-hidden border-b-2 border-black bg-white">
          <div className="px-6 pb-4 pt-5 border border-[#E5E5E5]">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 shrink-0 relative flex items-center justify-center">
                  <svg viewBox="0 0 100 100" className="animate-[spin_10s_linear_infinite] h-full w-full">
                    <polygon points="50,10 90,30 90,70 50,90 10,70 10,30" fill="none" stroke="#0f62fe" strokeWidth="4" />
                    <line x1="50" y1="10" x2="50" y2="50" stroke="#0f62fe" strokeWidth="4" />
                    <line x1="90" y1="30" x2="50" y2="50" stroke="#0f62fe" strokeWidth="4" />
                    <line x1="10" y1="30" x2="50" y2="50" stroke="#0f62fe" strokeWidth="4" />
                    <polygon points="10,70 50,90 50,50" fill="#00c805" stroke="#00c805" strokeWidth="2" opacity="0.8" />
                  </svg>
                </div>
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#0f62fe]">
                    Portfolio Command
                  </div>
                  <h1 className="mt-1 text-[24px] font-bold tracking-[-0.03em] text-black">
                    Execution Risk & Pricing
                  </h1>
                  <p className="mt-1 text-[12px] text-black font-medium">
                    {formatCompactNumber(data.summary.total_projects)} active lanes · Portfolio snapshot {formatTimestamp(data.generated_at)}
                  </p>
                </div>
              </div>
              <button
                onClick={() => void refresh()}
                className="shrink-0 bg-black px-6 py-2.5 text-[11px] font-bold uppercase tracking-[0.1em] text-white transition-all duration-300 hover:bg-[#1A1A1A]"
              >
                Recalculate Risk
              </button>
            </div>

            {/* KPI capsules - Solid Mode */}
            <div className="mt-6 grid grid-cols-2 gap-px bg-black border border-black md:grid-cols-5">
              {[
                { label: "Projects", value: formatCompactNumber(data.summary.total_projects), sub: `${formatCompactNumber(data.summary.active_projects)} active`, color: "black" },
                { label: "Wells", value: formatCompactNumber(data.summary.total_wells), sub: "population", color: "black" },
                { label: "Avg Progress", value: formatPct(data.summary.avg_progress_pct), sub: "completion", color: "#00c805" },
                { label: "Pressure", value: formatCompactNumber(data.summary.projects_under_pressure), sub: "above threshold", color: "#ffd700" },
                { label: "Risk Index", value: String(pressureIndex), sub: "/ 99 max", color: "#a91101", hasBar: true as const },
              ].map((m) => (
                <div
                  key={m.label}
                  className="bg-white px-5 py-4"
                >
                  <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-black">
                    {m.label}
                  </div>
                  <div className="mt-1 flex items-baseline gap-1.5">
                    <span className="text-[22px] font-bold tracking-[-0.02em]" style={{ color: m.color }}>
                      {m.value}
                    </span>
                    <span className="text-[11px] font-medium text-black uppercase">{m.sub}</span>
                  </div>
                  {"hasBar" in m && m.hasBar ? (
                    <div className="mt-2 h-[4px] overflow-hidden bg-[#E5E5E5]">
                      <div
                        className="h-full bg-[#a91101]"
                        style={{ width: `${Math.max(6, pressureIndex)}%` }}
                      />
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>

          {/* Filter strip solid block */}
          <div className="border-t border-[#E5E5E5] bg-black px-6 py-2">
            <div className="flex items-center gap-3">
              <div className="shrink-0 text-[10px] font-bold uppercase tracking-[0.1em] text-white">
                Filter
              </div>
              <div className="mx-1 h-4 w-px bg-[#333333]" />
              {(["all", "active", "inactive"] as const).map((value) => (
                <button
                  key={value}
                  onClick={() => setFilter(value)}
                  className={`px-4 py-1.5 text-[11px] font-bold uppercase tracking-[0.1em] transition-all duration-300 ${
                    filter === value
                      ? "bg-white text-black"
                      : "text-white hover:bg-[#333333]"
                  }`}
                >
                  {value}
                </button>
              ))}
              <div className="ml-auto text-[11px] font-bold uppercase text-[#00c805]">
                {filteredCards.length} lane{filteredCards.length !== 1 ? "s" : ""} visible
              </div>
            </div>
          </div>
        </section>

        {loading ? <LoadingState label="Loading live portfolio structure…" /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!loading && !error ? (
          <>
            {/* ── Analytics Chart Panel ── */}
            <section className="overflow-hidden border-2 border-black bg-white relative mt-8">
              <div className="flex items-center gap-0 border-b-2 border-black bg-black">
                {([
                  ["topology", "3D Risk Topography"],
                  ["scatter", "Risk vs Progress"],
                  ["treemap", "Portfolio Capital Map"],
                  ["composition", "Execution Mix"],
                ] as const).map(([key, label]) => (
                  <button
                    key={key}
                    onClick={() => setChartTab(key)}
                    className={`px-5 py-2.5 text-[11px] font-bold uppercase tracking-[0.1em] border-r border-[#333] transition-all duration-300 ${
                      chartTab === key
                        ? "bg-white text-black"
                        : "text-white hover:bg-[#1A1A1A]"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <div className="p-0">
                {chartTab === "topology" && filteredCards.length > 0 ? (
                  <div className="flex flex-col lg:flex-row gap-5">
                    <div className="flex-1 min-w-0">
                      <ChartViewToggle
                        label="3D Execution Risk Surface"
                        view2d={
                          <Plot
                            data={surfaceData.data}
                            layout={{ ...surfaceData.layout, ...LIGHT_LAYOUT_OVERRIDES, height: 450, width: undefined }}
                            config={DESERT_CONFIG}
                            style={{ width: "100%", height: 450 }}
                            useResizeHandler
                          />
                        }
                      />
                    </div>
                    {/* Agentic Feed Component */}
                    {data.agentic_feed && data.agentic_feed.length > 0 && (
                      <div className="w-full lg:w-[320px] flex-shrink-0 flex flex-col gap-3">
                        <div className="flex items-center gap-2 pb-2 bg-black text-white px-3 py-2 border-b border-black">
                          <div className="w-2 h-2 bg-[#00c805] animate-none"></div>
                          <span className="text-[11px] font-bold uppercase tracking-[0.15em]">Synthetic Officer</span>
                        </div>
                        <div className="flex flex-col gap-0 overflow-y-auto max-h-[450px]">
                          {data.agentic_feed.map((feed, idx) => (
                            <div key={idx} className="bg-white border-b border-[#000] p-3 text-left">
                              <div className="text-[10px] font-bold text-[#0f62fe] uppercase tracking-wide mb-1">
                                {feed.trigger}
                              </div>
                              <div className="text-[12px] font-bold text-black mb-1.5">
                                {feed.project} — {feed.action}
                              </div>
                              <div className="text-[11px] leading-relaxed text-black font-medium">
                                {feed.recommendation}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : null}

                {chartTab === "treemap" && filteredCards.length > 0 ? (
                  <ChartViewToggle
                    label="Project Health Map"
                    view2d={
                      <Plot
                        data={treemapData.data}
                        layout={{ ...treemapData.layout, ...LIGHT_LAYOUT_OVERRIDES, margin: { l: 4, r: 4, t: 36, b: 4 }, height: 400, width: undefined }}
                        config={DESERT_CONFIG}
                        style={{ width: "100%", height: 400 }}
                        useResizeHandler
                      />
                    }
                    view3d={
                      <Plot
                        data={treemapData3D.data}
                        layout={{ ...treemapData3D.layout, ...LIGHT_LAYOUT_OVERRIDES, margin: { l: 0, r: 0, t: 30, b: 0 }, height: 400, width: undefined }}
                        config={DESERT_CONFIG}
                        style={{ width: "100%", height: 400 }}
                        useResizeHandler
                      />
                    }
                  />
                ) : null}

                {chartTab === "scatter" && filteredCards.length > 0 ? (
                  <ChartViewToggle
                    label="Execution Risk Scatter"
                    view2d={
                      <Plot
                        data={scatterData.data}
                        layout={{ ...scatterData.layout, ...LIGHT_LAYOUT_OVERRIDES, height: 400, width: undefined }}
                        config={DESERT_CONFIG}
                        style={{ width: "100%", height: 400 }}
                        useResizeHandler
                      />
                    }
                    view3d={
                      <Plot
                        data={scatterData3D.data}
                        layout={{ ...scatterData3D.layout, ...LIGHT_LAYOUT_OVERRIDES, height: 400, width: undefined }}
                        config={DESERT_CONFIG}
                        style={{ width: "100%", height: 400 }}
                        useResizeHandler
                      />
                    }
                  />
                ) : null}

                {chartTab === "composition" && data.status_mix.length > 0 ? (
                  <ChartViewToggle
                    label="Well Status Composition"
                    view2d={
                      <Plot
                        data={statusDonut.data}
                        layout={{ ...statusDonut.layout, ...LIGHT_LAYOUT_OVERRIDES, margin: { l: 10, r: 10, t: 40, b: 10 }, height: 400, width: undefined }}
                        config={DESERT_CONFIG}
                        style={{ width: "100%", height: 400 }}
                        useResizeHandler
                      />
                    }
                    view3d={
                      <Plot
                        data={statusDonut3D.data}
                        layout={{ ...statusDonut3D.layout, ...LIGHT_LAYOUT_OVERRIDES, height: 400, width: undefined }}
                        config={DESERT_CONFIG}
                        style={{ width: "100%", height: 400 }}
                        useResizeHandler
                      />
                    }
                  />
                ) : null}
              </div>
            </section>

            {/* ── Main Grid: Project Lanes + Sidebar ── */}
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px] mt-4">
              {/* LEFT: Project lane table */}
              <section className="border-2 border-black bg-white">
                <div className="flex items-center justify-between border-b-2 border-black bg-white px-5 py-3">
                  <div>
                    <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-black">
                      Project Ledger
                    </div>
                    <div className="text-[10px] uppercase font-bold text-[#0f62fe] mt-0.5">
                      Ranked by execution pressure
                    </div>
                  </div>
                  <div className="text-[11px] font-bold bg-black text-white px-2 py-1">{filteredCards.length} LANES</div>
                </div>

                {/* Column headers */}
                <div className="grid grid-cols-[minmax(150px,1.5fr)_70px_90px_80px_100px_72px_75px_75px] items-center gap-0 border-b border-black bg-black px-5 py-2">
                  {["Project", "Status", "Progress", "Delay Prob", "P95 Risk Val", "Wells", "Issues", "Band"].map((col) => (
                    <div key={col} className="text-[10px] font-bold uppercase tracking-[0.1em] text-white">
                      {col}
                    </div>
                  ))}
                </div>

                {/* Project rows */}
                {filteredCards.map((card, idx) => {
                  const isExpanded = expandedProject === card.project;
                  return (
                    <div key={card.project}>
                      <button
                        onClick={() => setExpandedProject(isExpanded ? null : card.project)}
                        className="grid w-full grid-cols-[minmax(150px,1.5fr)_70px_90px_80px_100px_72px_75px_75px] items-center gap-0 border-b border-[#333] bg-white px-5 py-3 text-left transition-none hover:bg-[#E5E5E5]"
                      >
                        <div className="flex items-center gap-2 pr-2">
                          <span
                            className="inline-flex h-[20px] min-w-[20px] items-center justify-center text-[10px] font-bold text-white shadow-sm"
                            style={{ backgroundColor: bandDotColor(card.health_band) }}
                          >
                            {idx + 1}
                          </span>
                          <div>
                            <div className="text-[13px] font-bold text-black uppercase">{card.project}</div>
                            <div className="text-[10px] font-bold text-black uppercase">
                              {card.lead_rig} · {card.cluster_count} cluster{card.cluster_count !== 1 ? "s" : ""}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className={`h-[8px] w-[8px] ${card.status === "Active" ? "bg-[#00c805]" : "bg-[#333]"}`} />
                          <span className="text-[11px] font-bold text-black uppercase">{card.status}</span>
                        </div>
                        <div className="flex items-center gap-2 pr-2">
                          <div className="h-[6px] w-[38px] bg-[#E5E5E5]">
                            <div className={`h-full ${progressBarBg(card.health_band)}`} style={{ width: `${Math.max(2, card.avg_progress_pct)}%` }} />
                          </div>
                          <span className="text-data text-[12px] font-bold text-black">{formatPct(card.avg_progress_pct)}</span>
                        </div>
                        <div className="flex items-center gap-2 pr-2">
                          <span className="text-data text-[12px] font-bold text-[#ffd700]">{formatPct(card.avg_delay_probability_pct)}</span>
                        </div>
                        <div className="text-data text-[12px] font-bold text-[#a91101]">
                          {formatCurrency(card.risk_price)}
                        </div>
                        <div className="text-data text-[12px]">
                          <span className="font-bold text-black">{card.open_wells}</span>
                          <span className="text-black font-medium">/{card.total_wells}</span>
                        </div>
                        <div className={`text-data text-[12px] font-bold ${(card.delayed_wells + card.critical_wells) > 0 ? "text-[#a91101]" : "text-black"}`}>
                          {card.delayed_wells + card.critical_wells} FLAGS
                        </div>
                        <div>
                          <TonePill label={card.health_band} tone={toneForBand(card.health_band)} />
                        </div>
                      </button>

                      {/* Expanded detail panel - Solid mode */}
                      {isExpanded ? (
                        <div className="border-b-2 border-black bg-white px-5 py-4">
                          <div className="grid gap-4 md:grid-cols-3">
                            <div className="border border-black bg-white p-4">
                              <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#0f62fe]">NHPP Monte Carlo Stats</div>
                              <div className="mt-3 space-y-2.5">
                                {[
                                  { label: "Execution Price (Risk)", value: formatCurrency(card.risk_price) },
                                  { label: "P95 Worst Case Delay", value: `${card.p95_delay_exposure_days ?? card.max_delay_days}d` },
                                  { label: "Expected Delay (Mean)", value: `${card.expected_delay_days ?? 0}d` },
                                  { label: "Poisson Intensity (λ)", value: String(card.nhpp_intensity ?? 0) },
                                ].map((item) => (
                                  <div key={item.label} className="flex justify-between text-[11px]">
                                    <span className="font-bold text-black uppercase">{item.label}</span>
                                    <span className="text-data font-bold text-[#a91101]">{item.value}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                            <div className="border border-black bg-white p-4">
                              <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#0f62fe]">Execution Signals</div>
                              <div className="mt-3 flex flex-wrap gap-2">
                                <TonePill label={`${card.completed_wells} DONE`} tone="positive" />
                                <TonePill label={`${card.delayed_wells} DELAYED`} tone="warning" />
                                <TonePill label={`${card.critical_wells} CRITICAL`} tone="critical" />
                              </div>
                              <div className="mt-3 text-[11px] leading-5 text-black font-medium">
                                {card.health_band === "Critical"
                                  ? `HEAVY RISK PRICING APPLIED FOR ${card.critical_wells} CRITICAL WELLS.`
                                  : card.health_band === "Watch"
                                    ? `AVERAGE DELAY PROBABILITY REFLECTS PIPELINE CONSTRAINTS.`
                                    : `CLEAN EXECUTION PATH. MCEP SIMULATOR: NEGLIGIBLE DISRUPTION.`}
                              </div>
                            </div>
                            <div className="border border-black bg-white p-4">
                              <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#0f62fe]">Workfront Matrix</div>
                              <div className="mt-3 space-y-2.5">
                                {[
                                  { label: "Max delay prob", value: formatPct(card.max_delay_probability_pct) },
                                  { label: "Lead rig", value: card.lead_rig },
                                  { label: "Clusters", value: String(card.cluster_count) },
                                  { label: "Snapshot", value: card.last_updated || "—" },
                                ].map((item) => (
                                  <div key={item.label} className="flex justify-between text-[11px]">
                                    <span className="font-bold text-black uppercase">{item.label}</span>
                                    <span className="font-bold text-black">{item.value}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </section>

              {/* RIGHT: Pressure Queue + Spectrum */}
              <div className="flex flex-col gap-4">
                {/* Pressure queue */}
                <section className="border-2 border-black bg-white">
                  <div className="flex items-center justify-between border-b-2 border-black bg-white px-5 py-3">
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-black">Live Pressure Stack</div>
                      <div className="mt-0.5 text-[10px] font-bold uppercase text-[#0f62fe]">Top at-risk individual wells</div>
                    </div>
                    <div className="text-[11px] font-bold bg-black text-white px-2 py-1">{data.top_wells.length} TRACKED</div>
                  </div>
                  <div className="divide-y divide-black">
                    {data.top_wells.slice(0, 8).map((well, index) => (
                      <div
                        key={`${well.project}-${well.well_name}`}
                        className="flex items-center gap-3 px-5 py-3 hover:bg-[#E5E5E5]"
                      >
                        <span className="flex h-[20px] w-[20px] shrink-0 items-center justify-center bg-black text-[10px] font-bold text-white">
                          {index + 1}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <div className="truncate text-[12px] font-bold text-black uppercase">{well.well_name}</div>
                            <TonePill label={well.risk_tier} tone={toneForRisk(well.risk_tier)} />
                          </div>
                          <div className="mt-1.5 flex items-center gap-2 text-[10px] font-bold text-black uppercase">
                            <span className="truncate max-w-[80px]">{well.project}</span>
                            <span className="opacity-30">|</span>
                            <span>{well.rig_no}</span>
                            <span className="opacity-30">|</span>
                            <span className="text-data font-bold text-[#00c805]">{formatPct(well.progress_pct)}</span>
                            <span className="opacity-30">|</span>
                            <span className={`text-data font-bold ${well.delay_days > 14 ? "text-[#a91101]" : "text-[#ffd700]"}`}>
                              {well.delay_days}d slip
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                {/* Spectrum */}
                <section className="border-2 border-black bg-white">
                  <div className="border-b-2 border-black px-5 py-3">
                    <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-black">Risk Spectrum</div>
                    <div className="text-[10px] mt-0.5 font-bold uppercase text-[#0f62fe]">Relative portfolio impact</div>
                  </div>
                  <div className="px-5 py-4">
                    <div className="space-y-3">
                      {filteredCards.map((card) => {
                        const pressure = Math.min(
                          100,
                          card.avg_delay_probability_pct * 0.68 + card.delayed_wells * 4.5 + card.critical_wells * 6,
                        );
                        return (
                          <div key={card.project}>
                            <div className="flex items-center justify-between text-[11px]">
                              <div className="flex items-center gap-2">
                                <span className="h-[8px] w-[8px]" style={{ backgroundColor: bandDotColor(card.health_band) }} />
                                <span className="font-bold text-black uppercase">{card.project}</span>
                              </div>
                              <span className="text-data font-bold text-black">{Math.round(pressure)} PTS</span>
                            </div>
                            <div className="mt-1.5 h-[6px] bg-[#E5E5E5] border-y border-black">
                              <div className={`h-full ${progressBarBg(card.health_band)} border-r border-black`} style={{ width: `${Math.max(4, (pressure / maxPressure) * 100)}%` }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </section>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
