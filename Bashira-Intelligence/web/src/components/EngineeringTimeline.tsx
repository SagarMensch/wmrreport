"use client";

import { useState } from "react";

import {
  ErrorState,
  formatPct,
  LoadingState,
  SectionHeader,
  SurfacePanel,
  TonePill,
} from "@/components/CommandCenterPrimitives";
import { useCommandCenterData } from "@/components/useCommandCenterData";

interface EngineeringMilestone {
  label: string;
  date: string | null;
  status: string;
}

interface EngineeringWell {
  well_id: string;
  well_name: string;
  project: string;
  cluster: string;
  rig_no: string;
  engineering_pct: number;
  loc_prep_pct: number;
  progress_pct: number;
  risk_score: number;
  risk_tier: string;
  moc_state: string;
  milestones: EngineeringMilestone[];
  flaf_issue: string | null;
  engineering_start: string | null;
  engineering_finish: string | null;
  material_available: string | null;
  wlctf_acceptance: string | null;
}

interface EngineeringPayload {
  generated_at?: string;
  summary: {
    avg_engineering_pct?: number;
    flaf_issued?: number;
    engineering_started?: number;
    engineering_completed?: number;
    materials_ready?: number;
    moc_open?: number;
  };
  status_mix: { label: string; count: number }[];
  wells: EngineeringWell[];
}

const EMPTY_DATA: EngineeringPayload = {
  summary: {},
  status_mix: [],
  wells: [],
};

function toneForMilestone(status: string) {
  if (status === "completed") return "positive";
  return "warning";
}

export default function EngineeringTimeline() {
  const { data, loading, error, refresh } = useCommandCenterData<EngineeringPayload>(
    "engineering_timeline",
    EMPTY_DATA,
  );
  const [selectedWellId, setSelectedWellId] = useState("");

  const selectedWell =
    data.wells.find((well) => well.well_id === selectedWellId) || data.wells[0];

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex w-full max-w-[1540px] flex-col gap-4 px-5 py-5">
        <SectionHeader
          kicker="Engineering Timeline"
          title="Engineering ledger & milestone readiness"
          subtitle={`${data.wells.length} wells · Avg engineering ${formatPct(data.summary.avg_engineering_pct)} · ${data.summary.moc_open || 0} open MOC`}
          aside={
            <button
              onClick={() => void refresh()}
              className="rounded-[8px] border border-[#E5E5E5] bg-[#FFFFFF] px-4 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-[#525252] shadow-sm transition-all duration-300 hover:border-[#D4D4D4] hover:text-[#1A1A1A]"
            >
              Refresh
            </button>
          }
        />

        {loading ? <LoadingState label="Assembling engineering milestones…" /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!loading && !error ? (
          <>
            {/* KPI Strip */}
            <div className="grid gap-2 md:grid-cols-3 xl:grid-cols-6">
              {[
                { label: "Avg Eng.", value: formatPct(data.summary.avg_engineering_pct), accent: "#C9A96E" },
                { label: "FLAF Issued", value: String(data.summary.flaf_issued || 0), accent: "#9A8B78" },
                { label: "Eng Started", value: String(data.summary.engineering_started || 0), accent: "#5BA88C" },
                { label: "Eng Complete", value: String(data.summary.engineering_completed || 0), accent: "#5BA88C" },
                { label: "Mat Ready", value: String(data.summary.materials_ready || 0), accent: "#D4A04A" },
                { label: "Open MOC", value: String(data.summary.moc_open || 0), accent: "#D4636F" },
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

            <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
              {/* LEFT: Throughput + Focus */}
              <div className="flex flex-col gap-4">
                <SurfacePanel className="p-5">
                  <div className="text-[10px] font-bold uppercase tracking-[0.24em] text-[#737373]">
                    Throughput
                  </div>
                  <div className="mt-1 text-[14px] font-bold text-[#1A1A1A]">
                    Milestone completion mix
                  </div>
                  <div className="mt-4 space-y-3">
                    {data.status_mix.map((item) => (
                      <div key={item.label}>
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-bold text-[#1A1A1A]">{item.label}</span>
                          <span className="text-data font-medium text-[#737373]">{item.count}</span>
                        </div>
                        <div className="mt-1.5 h-[4px] overflow-hidden rounded-full bg-[#FAFAFA]">
                          <div
                            className="h-full rounded-full bg-[#1A1A1A]"
                            style={{
                              width: `${Math.max(
                                6,
                                (item.count / Math.max(data.wells.length, 1)) * 100,
                              )}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </SurfacePanel>

                <SurfacePanel className="p-5">
                  <div className="text-[10px] font-bold uppercase tracking-[0.24em] text-[#737373]">
                    Focus Well
                  </div>
                  <div className="mt-2 text-[16px] font-bold text-[#1A1A1A]">
                    {selectedWell?.well_name || "Select a well"}
                  </div>
                  {selectedWell ? (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      <TonePill label={selectedWell.project} tone="neutral" />
                      <TonePill label={selectedWell.cluster} tone="neutral" />
                      <TonePill
                        label={`Risk ${selectedWell.risk_score.toFixed(1)}`}
                        tone={selectedWell.risk_score >= 60 ? "critical" : "warning"}
                      />
                      <TonePill
                        label={`MOC ${selectedWell.moc_state}`}
                        tone={selectedWell.moc_state === "approved" ? "positive" : selectedWell.moc_state === "raised" ? "warning" : "neutral"}
                      />
                    </div>
                  ) : null}
                </SurfacePanel>
              </div>

              {/* RIGHT: Well table with milestones */}
              <SurfacePanel className="overflow-hidden">
                <div className="grid grid-cols-[200px_100px_100px_minmax(0,1fr)] gap-0 border-b border-[#E5E5E5] bg-[#F5F5F5] px-5 py-2.5 text-[9px] font-bold uppercase tracking-[0.18em] text-[#737373]">
                  <div>Well</div>
                  <div>Engineering</div>
                  <div>Readiness</div>
                  <div>Milestones</div>
                </div>

                <div className="divide-y divide-[#E5E5E5]">
                  {data.wells.map((well) => (
                    <button
                      key={well.well_id}
                      onClick={() => setSelectedWellId(well.well_id)}
                      className={`grid w-full grid-cols-1 gap-3 px-5 py-3 text-left transition-all duration-200 lg:grid-cols-[200px_100px_100px_minmax(0,1fr)] ${
                        selectedWell?.well_id === well.well_id
                          ? "bg-[#F5F5F5]"
                          : "hover:bg-[#FAFAFA]"
                      }`}
                    >
                      <div>
                        <div className="text-[12px] font-bold text-[#1A1A1A]">{well.well_name}</div>
                        <div className="mt-0.5 text-[10px] text-[#737373]">
                          {well.project} · Rig {well.rig_no}
                        </div>
                      </div>

                      <div>
                        <div className="text-[8px] font-bold uppercase tracking-[0.14em] text-[#737373]">
                          Eng %
                        </div>
                        <div className="text-data mt-1 text-[12px] font-bold text-[#1A1A1A]">
                          {formatPct(well.engineering_pct)}
                        </div>
                      </div>

                      <div>
                        <div className="text-[8px] font-bold uppercase tracking-[0.14em] text-[#737373]">
                          Loc Prep
                        </div>
                        <div className="text-data mt-1 text-[12px] font-bold text-[#1A1A1A]">
                          {formatPct(well.loc_prep_pct)}
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-1.5">
                        {well.milestones.map((milestone) => (
                          <div
                            key={`${well.well_id}-${milestone.label}`}
                            className="rounded-[8px] border border-[#E5E5E5] bg-[#FFFFFF] px-2.5 py-1.5 shadow-sm"
                          >
                            <div className="text-[8px] font-bold uppercase tracking-[0.12em] text-[#737373]">
                              {milestone.label}
                            </div>
                            <div className="mt-1">
                              <TonePill
                                label={milestone.date || "Pending"}
                                tone={toneForMilestone(milestone.status)}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </button>
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
