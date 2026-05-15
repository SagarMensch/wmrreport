"use client";

import { useMemo, useState } from "react";

import {
  ErrorState,
  formatPct,
  LoadingState,
  SectionHeader,
  SurfacePanel,
  TonePill,
} from "@/components/CommandCenterPrimitives";
import { useCommandCenterData } from "@/components/useCommandCenterData";

interface ReadinessCategory {
  label: string;
  value: number;
}

interface ReadinessWell {
  well_id: string;
  well_name: string;
  project: string;
  cluster: string;
  overall_pct: number;
  risk_score: number;
  categories: ReadinessCategory[];
}

interface ReadinessSummary {
  label: string;
  value: number;
  min: number;
  max: number;
}

interface ReadinessPayload {
  summary_cards: ReadinessSummary[];
  wells: ReadinessWell[];
  readiness_curve: { label: string; portfolio_avg: number; target: number }[];
}

const EMPTY_DATA: ReadinessPayload = {
  summary_cards: [],
  wells: [],
  readiness_curve: [],
};

function RadarMesh({ categories }: { categories: ReadinessCategory[] }) {
  const points = useMemo(() => {
    const cx = 170;
    const cy = 170;
    const radius = 115;
    return categories.map((item, index) => {
      const angle = -Math.PI / 2 + (index * Math.PI * 2) / categories.length;
      const outerX = cx + radius * Math.cos(angle);
      const outerY = cy + radius * Math.sin(angle);
      const scaledRadius =
        radius * (Math.max(0, Math.min(item.value, 100)) / 100);
      const valueX = cx + scaledRadius * Math.cos(angle);
      const valueY = cy + scaledRadius * Math.sin(angle);
      return {
        label: item.label,
        value: item.value,
        outerX,
        outerY,
        valueX,
        valueY,
      };
    });
  }, [categories]);

  const polygon = points
    .map((point) => `${point.valueX},${point.valueY}`)
    .join(" ");

  return (
    <svg viewBox="0 0 340 340" className="h-[340px] w-full">
      {[25, 50, 75, 100].map((level) => {
        const radius = (115 * level) / 100;
        const mesh = points
          .map((point, index) => {
            const angle = -Math.PI / 2 + (index * Math.PI * 2) / points.length;
            return `${170 + radius * Math.cos(angle)},${170 + radius * Math.sin(angle)}`;
          })
          .join(" ");
        return (
          <polygon
            key={level}
            points={mesh}
            fill="none"
            stroke="rgba(185,150,100,0.10)"
            strokeWidth="1"
          />
        );
      })}

      {points.map((point) => (
        <g key={point.label}>
          <line
            x1="170"
            y1="170"
            x2={point.outerX}
            y2={point.outerY}
            stroke="#E5E5E5"
            strokeWidth="1"
          />
          <text
            x={point.outerX}
            y={point.outerY}
            textAnchor={
              point.outerX < 170
                ? "end"
                : point.outerX > 170
                  ? "start"
                  : "middle"
            }
            dominantBaseline={
              point.outerY < 170 ? "text-after-edge" : "hanging"
            }
            fill="#737373"
            fontSize="10"
            fontWeight="700"
          >
            {point.label}
          </text>
        </g>
      ))}

      <polygon
        points={polygon}
        fill="rgba(15,98,254,0.15)"
        stroke="#0F62FE"
        strokeWidth="2.5"
      />
      {points.map((point) => (
        <circle
          key={`${point.label}-dot`}
          cx={point.valueX}
          cy={point.valueY}
          r="4"
          fill="#1A1A1A"
        />
      ))}
    </svg>
  );
}

export default function LocationPreparation() {
  const { data, loading, error, refresh } =
    useCommandCenterData<ReadinessPayload>("location_prep", EMPTY_DATA);
  const [selectedWellId, setSelectedWellId] = useState("");

  const selectedWell =
    data.wells.find((well) => well.well_id === selectedWellId) || data.wells[0];

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex w-full max-w-[1540px] flex-col gap-4 px-5 py-5">
        <SectionHeader
          kicker="Location Readiness"
          title="Preparation & construction readiness"
          subtitle={`${data.wells.length} wells tracked · Category-level progress across all readiness dimensions`}
          aside={
            <button
              onClick={() => void refresh()}
              className="rounded-[8px] border border-[#E5E5E5] bg-[#FFFFFF] px-4 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-[#525252] shadow-sm transition-all duration-300 hover:border-[#D4D4D4] hover:text-[#1A1A1A]"
            >
              Refresh
            </button>
          }
        />

        {loading ? (
          <LoadingState label="Computing location readiness…" />
        ) : null}
        {error ? <ErrorState message={error} /> : null}

        {!loading && !error ? (
          <>
            {/* KPI Strip */}
            <div className="grid gap-2 md:grid-cols-3 xl:grid-cols-6">
              {data.summary_cards.map((card) => (
                <div
                  key={card.label}
                  className="group rounded-[10px] border border-[#E5E5E5] bg-[#FFFFFF] px-4 py-3 shadow-sm transition-all duration-300 hover:border-[#D4D4D4] hover:shadow-md"
                >
                  <div className="text-[9px] font-bold uppercase tracking-[0.22em] text-[#737373]">
                    {card.label}
                  </div>
                  <div className="text-data mt-1 text-[22px] font-bold tracking-[-0.02em] text-[#1A1A1A]">
                    {formatPct(card.value)}
                  </div>
                  <div className="mt-0.5 text-[9px] text-[#A3A3A3]">
                    {formatPct(card.min)} – {formatPct(card.max)}
                  </div>
                </div>
              ))}
            </div>

            <div className="grid gap-4 xl:grid-cols-[440px_minmax(0,1fr)]">
              <SurfacePanel className="p-5">
                <div className="text-[10px] font-bold uppercase tracking-[0.24em] text-[#737373]">
                  Readiness Radar
                </div>
                <div className="mt-2 text-[16px] font-bold text-[#1A1A1A]">
                  {selectedWell ? selectedWell.well_name : "Select a well"}
                </div>
                {selectedWell ? (
                  <>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <TonePill label={selectedWell.project} tone="neutral" />
                      <TonePill label={selectedWell.cluster} tone="neutral" />
                      <TonePill
                        label={`Risk ${selectedWell.risk_score.toFixed(1)}`}
                        tone={
                          selectedWell.risk_score >= 60 ? "critical" : "warning"
                        }
                      />
                    </div>
                    <div className="mt-4">
                      <RadarMesh categories={selectedWell.categories} />
                    </div>
                  </>
                ) : null}
              </SurfacePanel>

              <SurfacePanel className="overflow-hidden">
                <div className="flex flex-col gap-3 border-b border-[#E5E5E5] px-5 py-4 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-[0.24em] text-[#737373]">
                      Well Overlays
                    </div>
                    <div className="mt-1 text-[14px] font-bold text-[#1A1A1A]">
                      Lowest-readiness wells sorted by gap
                    </div>
                  </div>
                </div>

                <div className="divide-y divide-[#E5E5E5]">
                  {data.wells.map((well) => (
                    <button
                      key={well.well_id}
                      onClick={() => setSelectedWellId(well.well_id)}
                      className={`grid w-full grid-cols-1 gap-3 px-5 py-3.5 text-left transition-all duration-200 lg:grid-cols-[1.1fr_repeat(6,80px)] ${
                        selectedWell?.well_id === well.well_id
                          ? "bg-[#F5F5F5]"
                          : "hover:bg-[#FAFAFA]"
                      }`}
                    >
                      <div>
                        <div className="text-[12px] font-bold text-[#1A1A1A]">
                          {well.well_name}
                        </div>
                        <div className="mt-0.5 text-[10px] text-[#737373]">
                          {well.project} · {well.cluster}
                        </div>
                      </div>
                      {well.categories.map((category) => (
                        <div key={`${well.well_id}-${category.label}`}>
                          <div className="text-[8px] font-bold uppercase tracking-[0.14em] text-[#737373]">
                            {category.label}
                          </div>
                          <div className="text-data mt-1 text-[12px] font-bold text-[#1A1A1A]">
                            {formatPct(category.value)}
                          </div>
                        </div>
                      ))}
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
