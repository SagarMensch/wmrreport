"use client";

import {
  ErrorState,
  LoadingState,
  SectionHeader,
  SurfacePanel,
  TonePill,
} from "@/components/CommandCenterPrimitives";
import { useCommandCenterData } from "@/components/useCommandCenterData";

interface HeatmapCell {
  week: string;
  plan_pct: number;
  actual_pct: number;
  delta_pct: number;
  severity: string;
}

interface HeatmapRow {
  well_id: string;
  well_name: string;
  project: string;
  target_end: string;
  cum_plan_pct: number;
  cum_actual_pct: number;
  cum_delta_pct: number;
  cells: HeatmapCell[];
}

interface HeatmapPayload {
  rows: HeatmapRow[];
  distribution: { bucket: string; count: number }[];
  benchmark: {
    wells_tracked?: number;
    critical_cells?: number;
    avg_delta_pct?: number;
    p90_abs_delta_pct?: number;
  };
}

const EMPTY_DATA: HeatmapPayload = {
  rows: [],
  distribution: [],
  benchmark: {},
};

function cellStyle(severity: string) {
  if (severity === "critical") {
    return "bg-[#FEF2F2] border-[#FCA5A5] text-[#DC2626]";
  }
  if (severity === "at_risk") {
    return "bg-[#FFFBEB] border-[#FDE68A] text-[#D97706]";
  }
  if (severity === "watch") {
    return "bg-[#F5F5F5] border-[#E5E5E5] text-[#525252]";
  }
  return "bg-[#F0FDF4] border-[#86EFAC] text-[#16A34A]";
}

export default function DelayHeatmap() {
  const { data, loading, error, refresh } = useCommandCenterData<HeatmapPayload>(
    "delay_heatmap",
    EMPTY_DATA,
  );

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex w-full max-w-[1540px] flex-col gap-4 px-5 py-5">
        <SectionHeader
          kicker="Delay Matrix"
          title="Weekly delivery variance heatmap"
          subtitle={`${data.benchmark.wells_tracked || 0} wells tracked · ${data.benchmark.critical_cells || 0} critical cells · Avg delta ${Number(data.benchmark.avg_delta_pct || 0).toFixed(1)} pts`}
          aside={
            <button
              onClick={() => void refresh()}
              className="rounded-[8px] border border-[#E5E5E5] bg-[#FFFFFF] px-4 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-[#525252] shadow-sm transition-all duration-300 hover:border-[#D4D4D4] hover:text-[#1A1A1A]"
            >
              Refresh
            </button>
          }
        />

        {loading ? <LoadingState label="Rendering delay heatmap…" /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!loading && !error ? (
          <>
            {/* KPI Strip */}
            <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
              {[
                { label: "Wells Tracked", value: String(data.benchmark.wells_tracked || 0), accent: "#C9A96E" },
                { label: "Critical Cells", value: String(data.benchmark.critical_cells || 0), accent: "#D4636F" },
                { label: "Avg Delta", value: `${Number(data.benchmark.avg_delta_pct || 0).toFixed(1)} pts`, accent: "#D4A04A" },
                { label: "P90 Abs Delta", value: `${Number(data.benchmark.p90_abs_delta_pct || 0).toFixed(1)} pts`, accent: "#9A8B78" },
              ].map((m) => (
                <div
                  key={m.label}
                  className="group rounded-[10px] border border-[#E5E5E5] bg-[#FFFFFF] px-4 py-3 shadow-sm transition-all duration-300 hover:border-[#D4D4D4] hover:shadow-md"
                >
                  <div className="text-[9px] font-bold uppercase tracking-[0.22em] text-[#737373]">
                    {m.label}
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="text-data mt-1 text-[22px] font-bold tracking-[-0.02em] text-[#1A1A1A]">
                      {m.value}
                    </div>
                    <div
                      className="h-5 w-[2px] rounded-full opacity-40 transition-opacity group-hover:opacity-100"
                      style={{ backgroundColor: m.accent }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
              {/* LEFT: Distribution */}
              <SurfacePanel className="p-5">
                <div className="text-[10px] font-bold uppercase tracking-[0.24em] text-[#737373]">
                  Distribution
                </div>
                <div className="mt-1 text-[14px] font-bold text-[#1A1A1A]">
                  Variance bucket mix
                </div>
                <div className="mt-4 space-y-3">
                  {data.distribution.map((item) => (
                    <div key={item.bucket}>
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-bold text-[#1A1A1A]">{item.bucket}</span>
                        <span className="text-data font-medium text-[#737373]">{item.count}</span>
                      </div>
                      <div className="mt-1.5 h-[4px] overflow-hidden rounded-full bg-[#FAFAFA]">
                        <div
                          className="h-full rounded-full bg-[#1A1A1A]"
                          style={{
                            width: `${Math.max(
                              6,
                              (item.count /
                                Math.max(
                                  data.distribution.reduce(
                                    (sum, entry) => sum + entry.count,
                                    0,
                                  ),
                                  1,
                                )) *
                                100,
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-5 flex flex-wrap gap-1.5">
                  <TonePill label="On Time" tone="positive" />
                  <TonePill label="Watch" tone="warning" />
                  <TonePill label="Critical" tone="critical" />
                </div>
              </SurfacePanel>

              {/* RIGHT: Heatmap grid */}
              <SurfacePanel className="overflow-hidden">
                <div className="grid grid-cols-[240px_repeat(5,90px)_100px] gap-0 border-b border-[#E5E5E5] bg-[#F5F5F5] px-5 py-2.5 text-[9px] font-bold uppercase tracking-[0.18em] text-[#737373]">
                  <div>Well</div>
                  <div>W1</div>
                  <div>W2</div>
                  <div>W3</div>
                  <div>W4</div>
                  <div>W5</div>
                  <div>Month</div>
                </div>

                <div className="divide-y divide-[#E5E5E5]">
                  {data.rows.map((row) => (
                    <div
                      key={row.well_id}
                      className="grid grid-cols-1 gap-2 px-5 py-3 lg:grid-cols-[240px_repeat(5,90px)_100px]"
                    >
                      <div>
                        <div className="text-[12px] font-bold text-[#1A1A1A]">
                          {row.well_name}
                        </div>
                        <div className="mt-0.5 text-[10px] text-[#737373]">
                          {row.project} · Target {row.target_end || "NA"}
                        </div>
                      </div>

                      {row.cells.map((cell) => (
                        <div
                          key={`${row.well_id}-${cell.week}`}
                          className={`rounded-[8px] border px-2.5 py-2 ${cellStyle(cell.severity)}`}
                          title={`Plan ${cell.plan_pct}% | Actual ${cell.actual_pct}% | Delta ${cell.delta_pct} pts`}
                        >
                          <div className="text-[8px] font-bold uppercase tracking-[0.12em] opacity-70">
                            {cell.week}
                          </div>
                          <div className="text-data mt-1 text-[13px] font-bold">
                            {cell.delta_pct >= 0 ? "+" : ""}
                            {cell.delta_pct}
                          </div>
                          <div className="mt-0.5 text-[9px] opacity-70">
                            {cell.actual_pct}% / {cell.plan_pct}%
                          </div>
                        </div>
                      ))}

                      <div className="rounded-[8px] border border-[#E5E5E5] bg-[#FFFFFF] px-2.5 py-2 shadow-sm">
                        <div className="text-[8px] font-bold uppercase tracking-[0.12em] text-[#737373]">
                          Cum Delta
                        </div>
                        <div className="text-data mt-1 text-[13px] font-bold text-[#1A1A1A]">
                          {row.cum_delta_pct >= 0 ? "+" : ""}
                          {row.cum_delta_pct}
                        </div>
                        <div className="mt-0.5 text-[9px] text-[#525252]">
                          {row.cum_actual_pct}% / {row.cum_plan_pct}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </SurfacePanel>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
