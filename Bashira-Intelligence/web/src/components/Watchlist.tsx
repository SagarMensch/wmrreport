"use client";

import { useEffect, useMemo, useState } from "react";

import {
  ErrorState,
  formatPct,
  LoadingState,
  SectionHeader,
  SurfacePanel,
  TonePill,
} from "@/components/CommandCenterPrimitives";
import { useCommandCenterData } from "@/components/useCommandCenterData";

interface WatchWell {
  well_id: string;
  well_name: string;
  project: string;
  cluster: string;
  rig_no: string;
  rig_status: string;
  risk_score: number;
  risk_tier: string;
  progress_pct: number;
  engineering_pct: number;
  loc_prep_pct: number;
  delay_days: number;
  rig_on_delay_days: number;
  owner_hint: string;
  reasons: string[];
}

interface WatchlistPayload {
  generated_at?: string;
  summary: {
    recommended_wells?: number;
    critical_recommended?: number;
    delayed_recommended?: number;
    projects_impacted?: number;
  };
  recommended: WatchWell[];
  owners: { label: string; count: number }[];
}

const EMPTY_DATA: WatchlistPayload = {
  summary: {},
  recommended: [],
  owners: [],
};

const STORAGE_KEY = "bashira_watchlist_ids";

function toneForRisk(riskTier: string) {
  if (riskTier === "CRITICAL" || riskTier === "HIGH_RISK") return "critical";
  if (riskTier === "WATCH") return "warning";
  return "positive";
}

export default function Watchlist() {
  const { data, loading, error, refresh } = useCommandCenterData<WatchlistPayload>(
    "watchlist",
    EMPTY_DATA,
  );
  const [pinnedIds, setPinnedIds] = useState<string[]>([]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as string[];
      if (Array.isArray(parsed)) {
        setPinnedIds(parsed);
      }
    } catch {
      setPinnedIds([]);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(pinnedIds));
  }, [pinnedIds]);

  const pinnedRows = useMemo(
    () => data.recommended.filter((row) => pinnedIds.includes(row.well_id)),
    [data.recommended, pinnedIds],
  );

  const queueRows = useMemo(
    () => data.recommended.filter((row) => !pinnedIds.includes(row.well_id)),
    [data.recommended, pinnedIds],
  );

  const togglePin = (wellId: string) => {
    setPinnedIds((current) =>
      current.includes(wellId)
        ? current.filter((item) => item !== wellId)
        : [wellId, ...current].slice(0, 12),
    );
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex w-full max-w-[1540px] flex-col gap-4 px-5 py-5">
        <SectionHeader
          kicker="Watchlist"
          title="Execution watchlist"
          subtitle={`${data.summary.recommended_wells || 0} recommended · ${data.summary.critical_recommended || 0} critical · ${data.summary.projects_impacted || 0} projects`}
          aside={
            <button
              onClick={() => void refresh()}
              className="rounded-[8px] border border-[rgba(185,150,100,0.14)] bg-[rgba(26,21,16,0.6)] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#C9A96E] backdrop-blur-[16px] transition-all duration-300 hover:border-[rgba(185,150,100,0.28)] hover:text-[#EDE8DF]"
            >
              Refresh
            </button>
          }
        />

        {loading ? <LoadingState label="Building watch queue…" /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!loading && !error ? (
          <>
            {/* KPI Strip */}
            <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
              {[
                { label: "Recommended", value: String(data.summary.recommended_wells || 0), accent: "#C9A96E" },
                { label: "Critical", value: String(data.summary.critical_recommended || 0), accent: "#D4636F" },
                { label: "Delayed", value: String(data.summary.delayed_recommended || 0), accent: "#D4A04A" },
                { label: "Projects", value: String(data.summary.projects_impacted || 0), accent: "#9A8B78" },
              ].map((m) => (
                <div
                  key={m.label}
                  className="group rounded-[10px] border border-[rgba(185,150,100,0.08)] bg-[rgba(26,21,16,0.65)] px-4 py-3 backdrop-blur-[16px] transition-all duration-300 hover:border-[rgba(185,150,100,0.18)]"
                >
                  <div className="text-[9px] font-semibold uppercase tracking-[0.22em] text-[#6B6259]">
                    {m.label}
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="text-data mt-1 text-[24px] font-semibold tracking-[-0.02em] text-[#EDE8DF]">
                      {m.value}
                    </div>
                    <div
                      className="h-6 w-[2px] rounded-full opacity-40 transition-opacity group-hover:opacity-80"
                      style={{ backgroundColor: m.accent }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="grid gap-4 xl:grid-cols-[380px_minmax(0,1fr)]">
              {/* LEFT: Pinned + Owner Mix */}
              <div className="flex flex-col gap-4">
                <SurfacePanel className="p-5">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#C9A96E]">
                    Pinned Wells
                  </div>
                  <div className="mt-4 space-y-2">
                    {pinnedRows.length ? (
                      pinnedRows.map((well) => (
                        <div
                          key={`pinned-${well.well_id}`}
                          className="rounded-[10px] border border-[rgba(185,150,100,0.12)] bg-[rgba(35,28,21,0.60)] p-4"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="text-[13px] font-semibold text-[#EDE8DF]">{well.well_name}</div>
                              <div className="mt-0.5 text-[11px] text-[#7A6E62]">
                                {well.project} · Rig {well.rig_no}
                              </div>
                            </div>
                            <button
                              onClick={() => togglePin(well.well_id)}
                              className="rounded-[6px] border border-[rgba(185,150,100,0.14)] px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[0.14em] text-[#9A8B78] transition-all hover:border-[rgba(212,99,111,0.30)] hover:text-[#D4636F]"
                            >
                              Unpin
                            </button>
                          </div>
                          <div className="mt-3 flex flex-wrap gap-1.5">
                            <TonePill label={well.risk_tier} tone={toneForRisk(well.risk_tier)} />
                            <TonePill label={`${well.delay_days}d`} tone="warning" />
                            <TonePill label={well.owner_hint} tone="neutral" />
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-[10px] border border-dashed border-[rgba(185,150,100,0.12)] bg-[rgba(35,28,21,0.30)] px-4 py-5 text-[12px] leading-5 text-[#6B6259]">
                        No wells pinned. Pin from the recommendation queue.
                      </div>
                    )}
                  </div>
                </SurfacePanel>

                <SurfacePanel className="p-5">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#C9A96E]">
                    Owner Mix
                  </div>
                  <div className="mt-4 space-y-2">
                    {data.owners.map((owner) => (
                      <div
                        key={owner.label}
                        className="flex items-center justify-between rounded-[8px] border border-[rgba(185,150,100,0.06)] bg-[rgba(35,28,21,0.40)] px-3.5 py-2.5"
                      >
                        <span className="text-[12px] font-medium text-[#EDE8DF]">
                          {owner.label}
                        </span>
                        <TonePill label={String(owner.count)} tone="neutral" />
                      </div>
                    ))}
                  </div>
                </SurfacePanel>
              </div>

              {/* RIGHT: Recommendation queue table */}
              <SurfacePanel className="overflow-hidden">
                <div className="grid grid-cols-[200px_90px_80px_90px_100px_minmax(0,1fr)_70px] gap-0 border-b border-[rgba(185,150,100,0.08)] bg-[rgba(35,28,21,0.30)] px-5 py-3 text-[9px] font-semibold uppercase tracking-[0.18em] text-[#6B6259]">
                  <div>Well</div>
                  <div>Risk</div>
                  <div>Delay</div>
                  <div>Progress</div>
                  <div>Owner</div>
                  <div>Reasons</div>
                  <div>Pin</div>
                </div>

                <div className="divide-y divide-[rgba(185,150,100,0.06)]">
                  {queueRows.map((well) => (
                    <div
                      key={well.well_id}
                      className="grid grid-cols-1 gap-3 px-5 py-3.5 transition-all duration-200 hover:bg-[rgba(201,169,110,0.03)] lg:grid-cols-[200px_90px_80px_90px_100px_minmax(0,1fr)_70px]"
                    >
                      <div>
                        <div className="text-[12px] font-semibold text-[#EDE8DF]">
                          {well.well_name}
                        </div>
                        <div className="mt-0.5 text-[10px] text-[#6B6259]">
                          {well.project} · {well.cluster}
                        </div>
                      </div>

                      <div className="flex items-start">
                        <TonePill label={well.risk_tier} tone={toneForRisk(well.risk_tier)} />
                      </div>

                      <div>
                        <div className="text-data text-[12px] font-semibold text-[#D4A04A]">
                          {well.delay_days}d
                        </div>
                        <div className="mt-0.5 text-[10px] text-[#6B6259]">
                          Rig-on {well.rig_on_delay_days}d
                        </div>
                      </div>

                      <div>
                        <div className="text-data text-[12px] font-semibold text-[#EDE8DF]">
                          {formatPct(well.progress_pct)}
                        </div>
                        <div className="mt-0.5 text-[10px] text-[#6B6259]">
                          Eng {formatPct(well.engineering_pct)}
                        </div>
                      </div>

                      <div className="text-[11px] font-medium text-[#9A8B78]">
                        {well.owner_hint}
                      </div>

                      <div className="flex flex-wrap gap-1">
                        {well.reasons.map((reason) => (
                          <TonePill key={`${well.well_id}-${reason}`} label={reason} tone="warning" />
                        ))}
                      </div>

                      <div className="flex items-start">
                        <button
                          onClick={() => togglePin(well.well_id)}
                          className="rounded-[6px] bg-[rgba(201,169,110,0.10)] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#C9A96E] transition-all duration-200 hover:bg-[rgba(201,169,110,0.22)]"
                        >
                          Pin
                        </button>
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
