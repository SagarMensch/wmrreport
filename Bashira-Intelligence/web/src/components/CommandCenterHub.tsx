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
  buildDonut,
  DESERT_CONFIG,
  PALETTE,
  SERIES_COLORS,
} from "@/components/DesertPlotly";

const Plot = dynamic(() => import("@/components/PlotlyClient"), { ssr: false });

interface PortfolioCard {
  project: string;
  health_band: string;
  avg_progress_pct: number;
  avg_delay_probability_pct: number;
  delayed_wells: number;
  critical_wells: number;
}

interface AlertsPayload {
  alerts: {
    id: string;
    severity: string;
    title: string;
    summary: string;
    project: string;
    action_label: string;
  }[];
  insights: {
    title: string;
    message: string;
    action: string;
  }[];
  summary_cards: {
    label: string;
    count: number;
    accent: string;
  }[];
}

interface PortfolioPayload {
  summary: {
    total_projects?: number;
    projects_under_pressure?: number;
    avg_progress_pct?: number;
    avg_delay_probability_pct?: number;
  };
  project_cards: PortfolioCard[];
}

interface WatchPayload {
  summary: {
    recommended_wells?: number;
    critical_recommended?: number;
    delayed_recommended?: number;
    projects_impacted?: number;
  };
  recommended: {
    well_id: string;
    well_name: string;
    project: string;
    rig_no: string;
    risk_tier: string;
    delay_days: number;
    owner_hint: string;
    reasons: string[];
  }[];
}

const EMPTY_PORTFOLIO: PortfolioPayload = { summary: {}, project_cards: [] };
const EMPTY_ALERTS: AlertsPayload = { alerts: [], insights: [], summary_cards: [] };
const EMPTY_WATCH: WatchPayload = { summary: {}, recommended: [] };

function toneForBand(band: string) {
  if (band === "Critical") return "critical";
  if (band === "Watch") return "warning";
  return "positive";
}

function toneForSeverity(severity: string) {
  if (severity === "critical" || severity === "high" || severity === "high_risk") return "critical";
  if (severity === "medium" || severity === "watch") return "warning";
  return "neutral";
}

function bandDotColor(band: string) {
  if (band === "Critical") return "#D4636F";
  if (band === "Watch") return "#D4A04A";
  return "#5BA88C";
}

export default function CommandCenterHub({
  onOpenCommandWorkspace,
  onOpenWatchlist,
  onOpenAssetLens,
  onOpenDecisionLab,
  onOpenTrustLayer,
}: {
  onOpenCommandWorkspace: () => void;
  onOpenWatchlist: () => void;
  onOpenAssetLens: (
    view?: "atlas" | "portfolio" | "rigs" | "readiness" | "engineering" | "heatmap",
  ) => void;
  onOpenDecisionLab: (view?: "studio" | "forecast" | "causal") => void;
  onOpenTrustLayer: (view?: "integrity" | "dictionary" | "lineage") => void;
}) {
  const portfolio = useCommandCenterData<PortfolioPayload>("portfolio", EMPTY_PORTFOLIO);
  const alerts = useCommandCenterData<AlertsPayload>("alerts", EMPTY_ALERTS);
  const watch = useCommandCenterData<WatchPayload>("watchlist", EMPTY_WATCH);

  const [chartMode, setChartMode] = useState<"treemap" | "donut">("treemap");

  const loading = portfolio.loading || alerts.loading || watch.loading;
  const error = portfolio.error || alerts.error || watch.error;

  const criticalCount =
    alerts.data.summary_cards.find((item) => item.label === "Critical")?.count || 0;

  /* ── Chart data ── */

  const treemapData = useMemo(() => {
    return buildTreemap(
      portfolio.data.project_cards.map((c) => ({
        label: c.project,
        value: Math.max(1, c.delayed_wells + c.critical_wells + 1),
        color: bandDotColor(c.health_band),
      })),
    );
  }, [portfolio.data.project_cards]);

  const alertsDonut = useMemo(() => {
    return buildDonut(
      alerts.data.summary_cards.map((card) => ({
        label: card.label,
        value: card.count,
        color:
          card.label === "Critical"
            ? PALETTE.rose
            : card.label === "Warning"
              ? PALETTE.sand
              : PALETTE.sage,
      })),
    );
  }, [alerts.data.summary_cards]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex w-full max-w-[1540px] flex-col gap-4 px-5 py-5">
        {/* ── Header ── */}
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[#C9A96E]">
              Command Center
            </div>
            <h1 className="mt-2 text-[26px] font-semibold tracking-[-0.03em] text-[#EDE8DF]">
              Operational command
            </h1>
            <p className="mt-1.5 text-[13px] leading-5 text-[#8A7B6E]">
              NL0010 · Nimr Location · Live
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={onOpenCommandWorkspace}
              className="rounded-[8px] bg-[rgba(201,169,110,0.12)] px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#C9A96E] transition-all duration-300 hover:bg-[rgba(201,169,110,0.22)]"
            >
              Bashira Command
            </button>
            <button
              onClick={() => onOpenDecisionLab("causal")}
              className="rounded-[8px] border border-[rgba(185,150,100,0.12)] bg-[rgba(26,21,16,0.6)] px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#9A8B78] backdrop-blur-[16px] transition-all duration-300 hover:border-[rgba(185,150,100,0.25)] hover:text-[#EDE8DF]"
            >
              Decision Lab
            </button>
          </div>
        </div>

        {loading ? <LoadingState label="Composing the operating picture…" /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!loading && !error ? (
          <>
            {/* ── KPI Strip ── */}
            <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
              {[
                { label: "Projects", value: formatCompactNumber(portfolio.data.summary.total_projects), accent: "#C9A96E" },
                { label: "Under Pressure", value: formatCompactNumber(portfolio.data.summary.projects_under_pressure), accent: "#D4636F" },
                { label: "Avg Progress", value: formatPct(portfolio.data.summary.avg_progress_pct), accent: "#5BA88C" },
                { label: "Critical Alerts", value: String(criticalCount), accent: "#D4A04A" },
                { label: "Watch Queue", value: String(watch.data.summary.recommended_wells || 0), accent: "#9A8B78" },
              ].map((m) => (
                <div
                  key={m.label}
                  className="group rounded-[10px] border border-[rgba(185,150,100,0.08)] bg-[rgba(26,21,16,0.65)] px-4 py-3 backdrop-blur-[16px] transition-all duration-300 hover:border-[rgba(185,150,100,0.18)]"
                >
                  <div className="text-[9px] font-semibold uppercase tracking-[0.22em] text-[#6B6259]">{m.label}</div>
                  <div className="flex items-center gap-2">
                    <div className="text-data mt-1 text-[24px] font-semibold tracking-[-0.02em] text-[#EDE8DF]">{m.value}</div>
                    <div className="h-6 w-[2px] rounded-full opacity-40 transition-opacity group-hover:opacity-80" style={{ backgroundColor: m.accent }} />
                  </div>
                </div>
              ))}
            </div>

            {/* ── Operating Actions ── */}
            <SurfacePanel className="px-5 py-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#C9A96E]">
                    Operating Actions
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {[
                    { label: "Watchlist", action: () => onOpenWatchlist() },
                    { label: "Field Atlas", action: () => onOpenAssetLens("atlas") },
                    { label: "Forecast", action: () => onOpenDecisionLab("forecast") },
                    { label: "Trust Layer", action: () => onOpenTrustLayer("integrity") },
                    { label: "Rig Ops", action: () => onOpenAssetLens("rigs") },
                    { label: "Heatmap", action: () => onOpenAssetLens("heatmap") },
                  ].map((btn) => (
                    <button
                      key={btn.label}
                      onClick={btn.action}
                      className="rounded-[6px] border border-[rgba(185,150,100,0.10)] bg-[rgba(35,28,21,0.5)] px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#9A8B78] transition-all duration-200 hover:border-[rgba(185,150,100,0.22)] hover:text-[#EDE8DF]"
                    >
                      {btn.label}
                    </button>
                  ))}
                </div>
              </div>
            </SurfacePanel>

            {/* ── Analytics Panel — Portfolio + Alert Charts ── */}
            <SurfacePanel className="overflow-hidden">
              <div className="flex items-center gap-1 border-b border-[rgba(185,150,100,0.08)] px-5 py-3">
                {([
                  ["treemap", "Portfolio Map"],
                  ["donut", "Alert Distribution"],
                ] as const).map(([key, label]) => (
                  <button
                    key={key}
                    onClick={() => setChartMode(key)}
                    className={`rounded-[6px] px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.14em] transition-all duration-300 ${
                      chartMode === key
                        ? "bg-[rgba(201,169,110,0.15)] text-[#C9A96E] border border-[rgba(201,169,110,0.30)]"
                        : "text-[#6B6259] hover:text-[#9A8B78] border border-transparent"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="p-5">
                {chartMode === "treemap" && portfolio.data.project_cards.length > 0 ? (
                  <ChartViewToggle
                    label="Project Pressure Topology"
                    view2d={
                      <Plot
                        data={treemapData.data}
                        layout={{ ...treemapData.layout, height: 340, width: undefined }}
                        config={DESERT_CONFIG}
                        style={{ width: "100%", height: 340 }}
                        useResizeHandler
                      />
                    }
                  />
                ) : null}

                {chartMode === "donut" && alerts.data.summary_cards.length > 0 ? (
                  <ChartViewToggle
                    label="Alert Severity Distribution"
                    view2d={
                      <Plot
                        data={alertsDonut.data}
                        layout={{ ...alertsDonut.layout, height: 340, width: undefined }}
                        config={DESERT_CONFIG}
                        style={{ width: "100%", height: 340 }}
                        useResizeHandler
                      />
                    }
                  />
                ) : null}
              </div>
            </SurfacePanel>

            {/* ── Main Grid ── */}
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_380px]">
              {/* LEFT: Portfolio Pressure + AI Brief */}
              <div className="flex flex-col gap-4">
                {/* Portfolio Pressure */}
                <SurfacePanel className="overflow-hidden">
                  <div className="flex items-center justify-between border-b border-[rgba(185,150,100,0.08)] px-5 py-3.5">
                    <div>
                      <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#C9A96E]">
                        Portfolio Pressure
                      </div>
                      <div className="mt-1 text-[15px] font-semibold text-[#EDE8DF]">
                        Ranked by operating strain
                      </div>
                    </div>
                    <button
                      onClick={() => onOpenAssetLens("atlas")}
                      className="rounded-[6px] bg-[rgba(201,169,110,0.10)] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#C9A96E] transition-all duration-200 hover:bg-[rgba(201,169,110,0.20)]"
                    >
                      Atlas
                    </button>
                  </div>

                  <div className="divide-y divide-[rgba(185,150,100,0.06)]">
                    {portfolio.data.project_cards.slice(0, 6).map((project) => (
                      <div
                        key={project.project}
                        className="grid grid-cols-[minmax(150px,1.2fr)_80px_80px_minmax(0,1fr)] items-center gap-3 px-5 py-3 transition-all duration-200 hover:bg-[rgba(201,169,110,0.03)]"
                      >
                        <div className="flex items-center gap-2.5">
                          <span
                            className="inline-flex h-[7px] w-[7px] shrink-0 rounded-full"
                            style={{ backgroundColor: bandDotColor(project.health_band) }}
                          />
                          <div>
                            <div className="text-[13px] font-semibold text-[#EDE8DF]">{project.project}</div>
                            <div className="mt-0.5">
                              <TonePill label={project.health_band} tone={toneForBand(project.health_band)} />
                            </div>
                          </div>
                        </div>
                        <div>
                          <div className="text-[9px] font-semibold uppercase tracking-[0.14em] text-[#6B6259]">Progress</div>
                          <div className="text-data mt-1 text-[13px] font-semibold text-[#EDE8DF]">{formatPct(project.avg_progress_pct)}</div>
                        </div>
                        <div>
                          <div className="text-[9px] font-semibold uppercase tracking-[0.14em] text-[#6B6259]">Risk</div>
                          <div className="text-data mt-1 text-[13px] font-semibold text-[#D4A04A]">{formatPct(project.avg_delay_probability_pct)}</div>
                        </div>
                        <div className="flex justify-end gap-1.5">
                          <TonePill label={`${project.delayed_wells} del`} tone="warning" />
                          <TonePill label={`${project.critical_wells} crt`} tone="critical" />
                        </div>
                      </div>
                    ))}
                  </div>
                </SurfacePanel>

                {/* AI Brief */}
                <SurfacePanel className="p-5">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#C9A96E]">
                    AI Briefing
                  </div>
                  <div className="mt-4 grid gap-3 lg:grid-cols-3">
                    {alerts.data.insights.slice(0, 3).map((insight) => (
                      <div
                        key={insight.title}
                        className="rounded-[10px] border border-[rgba(185,150,100,0.08)] bg-[rgba(35,28,21,0.50)] p-4 transition-all duration-300 hover:border-[rgba(185,150,100,0.16)]"
                      >
                        <div className="text-[13px] font-semibold text-[#EDE8DF]">{insight.title}</div>
                        <div className="mt-2 text-[12px] leading-5 text-[#8A7B6E]">{insight.message}</div>
                        <div className="mt-3">
                          <TonePill label={insight.action} tone="neutral" />
                        </div>
                      </div>
                    ))}
                  </div>
                </SurfacePanel>
              </div>

              {/* RIGHT: Watch Queue + Signal Feed */}
              <div className="flex flex-col gap-4">
                {/* Priority Watch Queue */}
                <SurfacePanel className="p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#C9A96E]">Priority Watch</div>
                    <button
                      onClick={onOpenWatchlist}
                      className="rounded-[6px] border border-[rgba(185,150,100,0.10)] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#6B6259] transition-all duration-200 hover:border-[rgba(185,150,100,0.22)] hover:text-[#C9A96E]"
                    >
                      Queue
                    </button>
                  </div>
                  <div className="mt-4 space-y-2">
                    {watch.data.recommended.slice(0, 6).map((well) => (
                      <div
                        key={well.well_id}
                        className="rounded-[10px] border border-[rgba(185,150,100,0.06)] bg-[rgba(35,28,21,0.45)] p-3.5 transition-all duration-300 hover:border-[rgba(185,150,100,0.14)]"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="text-[13px] font-semibold text-[#EDE8DF]">{well.well_name}</div>
                            <div className="mt-0.5 text-[11px] text-[#7A6E62]">
                              {well.project} · Rig {well.rig_no}
                            </div>
                          </div>
                          <TonePill label={well.risk_tier} tone={toneForSeverity(well.risk_tier.toLowerCase())} />
                        </div>
                        <div className="mt-2.5 flex items-center justify-between text-[11px]">
                          <div className="flex gap-1">
                            {well.reasons.slice(0, 2).map((reason) => (
                              <TonePill key={`${well.well_id}-${reason}`} label={reason} tone="warning" />
                            ))}
                          </div>
                          <span className="text-data text-[#D4A04A]">{well.delay_days}d</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </SurfacePanel>

                {/* Signal Feed */}
                <SurfacePanel className="p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#C9A96E]">Signal Feed</div>
                    <button
                      onClick={() => onOpenAssetLens("heatmap")}
                      className="rounded-[6px] border border-[rgba(185,150,100,0.10)] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#6B6259] transition-all duration-200 hover:border-[rgba(185,150,100,0.22)] hover:text-[#C9A96E]"
                    >
                      Signals
                    </button>
                  </div>
                  <div className="mt-4 space-y-2">
                    {alerts.data.alerts.slice(0, 5).map((alert) => (
                      <div
                        key={alert.id}
                        className="rounded-[10px] border border-[rgba(185,150,100,0.06)] bg-[rgba(35,28,21,0.45)] p-3.5 transition-all duration-300 hover:border-[rgba(185,150,100,0.14)]"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <TonePill label={alert.severity} tone={toneForSeverity(alert.severity)} />
                          <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#6B6259]">{alert.project}</span>
                        </div>
                        <div className="mt-2 text-[13px] font-semibold leading-tight text-[#EDE8DF]">{alert.title}</div>
                        <div className="mt-1 text-[11px] leading-4 text-[#7A6E62]">{alert.summary}</div>
                      </div>
                    ))}
                  </div>
                </SurfacePanel>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
