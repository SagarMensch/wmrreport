"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { useCommandCenterData } from "@/components/useCommandCenterData";

type ChartMode = "2d-map" | "3d-topology";
type FilterMode = "all" | "critical" | "high" | "watch" | "healthy";
type FocusOverlay = null | "chart" | "corridors" | "dossier";

interface ScoreBreakdown { key: string; label: string; value: number; }
interface ActionRow { label: string; owner: string; impact_days: number; detail: string; }

interface AtlasSummary {
  total_wells?: number;
  positioned_wells?: number;
  atlas_wells?: number;
  spatial_coverage_pct?: number;
  critical_positioned?: number;
  hotspot_cells?: number;
  rig_corridors?: number;
  zone_count?: number;
  avg_spatial_signal_score?: number;
  exposed_wells?: number;
}

interface AtlasBounds { min_easting?: number; max_easting?: number; min_northing?: number; max_northing?: number; }

interface AtlasWell {
  well_id: string; well_name: string; project: string; cluster: string; rig_no: string; well_type: string;
  risk_score: number; risk_tier: string; ops_risk_score: number; ops_risk_tier: string;
  spatial_signal_score: number; progress_pct: number; delay_days: number; rig_on_delay_days: number;
  engineering_pct: number; loc_prep_pct: number; construction_pct: number; commissioning_pct: number; flowline_pct: number;
  rig_status: string; expected_rig_on?: string | null; expected_rig_off?: string | null;
  actual_rig_on?: string | null; actual_rig_off?: string | null;
  recovery_confidence_pct: number; dominant_bottleneck: string; queue_exposure: number; anomaly_flag: boolean;
  local_neighbor_count: number; nearby_critical_count: number; neighborhood_pressure_score: number; local_density_score: number;
  zone_id: string; coord_source: "actual" | "cluster_imputed"; easting: number; northing: number;
  badges: string[]; evidence: string[]; actions: ActionRow[]; score_breakdown: ScoreBreakdown[];
}

interface AtlasZone {
  zone_id: string; label: string; easting: number; northing: number; radius_x: number; radius_y: number;
  well_count: number; active_wells: number; rig_count: number; rigs: string[];
  critical_wells: number; delayed_wells: number; anomaly_wells: number; avg_signal_score: number;
  avg_risk_score: number; avg_progress_pct: number; avg_recovery_confidence_pct: number; queue_exposure: number;
  dominant_bottleneck: string; top_wells: string[];
}

interface AtlasCorridor {
  id: string; rig_no: string; from_well_id: string; to_well_id: string; from_well_name: string; to_well_name: string;
  from_easting: number; from_northing: number; to_easting: number; to_northing: number;
  from_zone_id?: string; to_zone_id?: string; dominant_bottleneck: string; distance_m: number;
  handover_gap_days: number; corridor_type: string; pressure_score: number;
}

interface AtlasPayload {
  generated_at?: string; engine_label?: string; model_note?: string;
  summary: AtlasSummary; bounds: AtlasBounds; wells: AtlasWell[]; clusters: any[]; zones: AtlasZone[]; hotspots: any[]; corridors: AtlasCorridor[];
}

const EMPTY_DATA: AtlasPayload = { summary: {}, bounds: {}, wells: [], clusters: [], zones: [], hotspots: [], corridors: [] };

const INK = "#111111";
const PAPER = "#FFFFFF";
const SOFT = "#ECEEF2";
const HAIRLINE = "#D6D8DD";
const MUTED = "#6F7279";
const IBM_BLUE = "#0F62FE";
const ROBINHOOD_GREEN = "#00C805";
const SOLID_YELLOW = "#F1C21B";
const DARK_RED = "#8E1B1B";

function normalizeToken(value: string) { return String(value || "").trim().toUpperCase().replace(/\s+/g, "_"); }
function formatNumber(value: number | null | undefined, digits = 1) { return Number(value ?? 0).toFixed(digits); }
function formatDistanceMeters(value: number | null | undefined) { const num = Number(value ?? 0); return num >= 1000 ? `${(num / 1000).toFixed(1)} km` : `${num.toFixed(0)} m`; }
function formatDateLabel(val?: string | null) { return val && !Number.isNaN(new Date(val).getTime()) ? new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(val)) : "Awaiting"; }
function finiteNumber(value: number | null | undefined) {
  return Number.isFinite(Number(value)) ? Number(value) : null;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function tierMeta(value: string) {
  const norm = normalizeToken(value);
  if (norm.includes("CRITICAL")) return { label: "Critical", accent: DARK_RED, tint: "#FBE9E9" };
  if (norm.includes("HIGH") || norm.includes("WATCH")) return { label: "High Risk", accent: SOLID_YELLOW, tint: "#FFF7D6" };
  if (norm.includes("WARNING")) return { label: "Warning", accent: IBM_BLUE, tint: "#EAF1FF" };
  return { label: "Healthy", accent: ROBINHOOD_GREEN, tint: "#E8FAED" };
}

function matchesFilter(tier: string, mode: FilterMode) {
  if (mode === "all") return true;
  const meta = tierMeta(tier);
  switch(mode) {
     case "critical": return meta.accent === DARK_RED;
     case "high": return meta.accent === SOLID_YELLOW;
     case "watch": return meta.accent === IBM_BLUE;
     case "healthy": return meta.accent === ROBINHOOD_GREEN;
  }
}

function MonoLabel({ children }: { children: React.ReactNode }) {
  return <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>{children}</div>;
}

function SurfacePanel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`rounded-[24px] border bg-white shadow-[0_18px_42px_rgba(17,17,17,0.06)] ${className}`} style={{ borderColor: HAIRLINE }}>{children}</section>;
}

function FilterChip({ label, active, accent, onClick }: { label: string; active: boolean; accent?: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] transition-colors"
      style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: active ? accent || INK : HAIRLINE, backgroundColor: active ? accent || INK : PAPER, color: active ? PAPER : INK }}
    >
      {label}
    </button>
  );
}

function SeverityPill({ value }: { value: string }) {
  const meta = tierMeta(value);
  return (
    <div className="inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em]" style={{ borderColor: meta.accent, backgroundColor: meta.tint, color: meta.accent, fontFamily: "IBM Plex Mono, monospace" }}>
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: meta.accent }} />{meta.label}
    </div>
  );
}

function MetaChip({ label, value, accent = INK }: { label: string; value: React.ReactNode; accent?: string }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border bg-[#FCFCFD] px-3 py-2" style={{ borderColor: SOFT }}>
      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#6F7279]" style={{ fontFamily: "IBM Plex Mono, monospace" }}>{label}</span>
      <span className="text-[12px] font-semibold" style={{ color: accent }}>{value}</span>
    </div>
  );
}

function MapGlyph() {
  return (
    <svg width="42" height="42" viewBox="0 0 42 42" aria-hidden="true" role="img">
      <path d="M7 10L16 6L26 10L35 6V32L26 36L16 32L7 36V10Z" fill={IBM_BLUE} stroke={INK} strokeWidth="1.6" opacity="0.2"/>
      <path d="M16 6V32" stroke={IBM_BLUE} strokeWidth="1.6" strokeDasharray="3 3"/>
      <path d="M26 10V36" stroke={IBM_BLUE} strokeWidth="1.6" strokeDasharray="3 3"/>
      <circle cx="26" cy="18" r="4" fill={PAPER} stroke={INK} strokeWidth="2"/>
      <circle cx="16" cy="24" r="3" fill={DARK_RED} stroke={INK} strokeWidth="1.5"/>
    </svg>
  );
}

function AtlasCanvas({
  wells,
  corridors,
  bounds,
  mode,
  onSelectWell,
  onSelectCorridor,
  selectedWellId,
  selectedCorridorId,
}: {
  wells: AtlasWell[];
  corridors: AtlasCorridor[];
  bounds: { min_easting: number; max_easting: number; min_northing: number; max_northing: number };
  mode: ChartMode;
  onSelectWell: (wellId: string) => void;
  onSelectCorridor: (corridorId: string) => void;
  selectedWellId: string | null;
  selectedCorridorId: string | null;
}) {
  const width = 1280;
  const height = 760;
  const padding = 92;
  const spanX = Math.max(1, bounds.max_easting - bounds.min_easting);
  const spanY = Math.max(1, bounds.max_northing - bounds.min_northing);
  const maxRisk = Math.max(10, ...wells.map((well) => Number(well.ops_risk_score || 0)));
  const is3D = mode === "3d-topology";

  const project = (x: number, y: number, z = 0) => {
    const nx = (x - bounds.min_easting) / spanX;
    const ny = (y - bounds.min_northing) / spanY;

    if (!is3D) {
      return {
        x: padding + nx * (width - padding * 2),
        y: height - padding - ny * (height - padding * 2),
      };
    }

    const isoX = (nx - ny) * 360;
    const isoY = (nx + ny) * 130;
    const zLift = (z / maxRisk) * 220;
    return {
      x: width / 2 + isoX,
      y: height - 180 - isoY - zLift,
    };
  };

  const floorCorners = [
    project(bounds.min_easting, bounds.min_northing, 0),
    project(bounds.max_easting, bounds.min_northing, 0),
    project(bounds.max_easting, bounds.max_northing, 0),
    project(bounds.min_easting, bounds.max_northing, 0),
  ];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full">
      <defs>
        <linearGradient id="atlasFloor" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#F5F7FB" />
          <stop offset="100%" stopColor="#EEF3FB" />
        </linearGradient>
        <linearGradient id="atlasBlueBar" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#2B78FF" />
          <stop offset="100%" stopColor="#0F62FE" />
        </linearGradient>
        <linearGradient id="atlasYellowBar" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#F8D84A" />
          <stop offset="100%" stopColor="#F1C21B" />
        </linearGradient>
        <linearGradient id="atlasRedBar" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#B42318" />
          <stop offset="100%" stopColor="#8E1B1B" />
        </linearGradient>
        <filter id="atlasShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="10" stdDeviation="12" floodColor="rgba(17,17,17,0.16)" />
        </filter>
      </defs>

      <rect x="0" y="0" width={width} height={height} fill="#FAFAFB" />

      {is3D ? (
        <>
          <polygon
            points={floorCorners.map((point) => `${point.x},${point.y}`).join(" ")}
            fill="url(#atlasFloor)"
            stroke={SOFT}
            strokeWidth="2"
          />
          {Array.from({ length: 5 }).map((_, index) => {
            const ratio = (index + 1) / 6;
            const x1 = bounds.min_easting + spanX * ratio;
            const y1 = bounds.min_northing;
            const x2 = bounds.min_easting + spanX * ratio;
            const y2 = bounds.max_northing;
            const p1 = project(x1, y1, 0);
            const p2 = project(x2, y2, 0);
            return <line key={`grid-x-${index}`} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke={SOFT} strokeWidth="1.5" />;
          })}
          {Array.from({ length: 5 }).map((_, index) => {
            const ratio = (index + 1) / 6;
            const x1 = bounds.min_easting;
            const y1 = bounds.min_northing + spanY * ratio;
            const x2 = bounds.max_easting;
            const y2 = bounds.min_northing + spanY * ratio;
            const p1 = project(x1, y1, 0);
            const p2 = project(x2, y2, 0);
            return <line key={`grid-y-${index}`} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke={SOFT} strokeWidth="1.5" />;
          })}
        </>
      ) : (
        <>
          <rect x={padding - 24} y={padding - 24} width={width - (padding - 24) * 2} height={height - (padding - 24) * 2} rx="32" fill="#FCFCFD" stroke={SOFT} strokeWidth="2" />
          {Array.from({ length: 6 }).map((_, index) => {
            const ratio = index / 5;
            const x = padding + ratio * (width - padding * 2);
            return <line key={`plane-x-${index}`} x1={x} y1={padding} x2={x} y2={height - padding} stroke={SOFT} strokeWidth="1.5" />;
          })}
          {Array.from({ length: 6 }).map((_, index) => {
            const ratio = index / 5;
            const y = padding + ratio * (height - padding * 2);
            return <line key={`plane-y-${index}`} x1={padding} y1={y} x2={width - padding} y2={y} stroke={SOFT} strokeWidth="1.5" />;
          })}
        </>
      )}

      {corridors.map((corridor) => {
        const from = project(corridor.from_easting, corridor.from_northing, 0);
        const to = project(corridor.to_easting, corridor.to_northing, 0);
        const active = selectedCorridorId === corridor.id;
        return (
          <g key={corridor.id} onClick={() => onSelectCorridor(corridor.id)} style={{ cursor: "pointer" }}>
            <line
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={active ? IBM_BLUE : "#96B8FF"}
              strokeWidth={active ? 4 : 2.4}
              strokeLinecap="round"
              opacity={active ? 0.96 : 0.52}
            />
          </g>
        );
      })}

      {wells.map((well) => {
        const accent = tierMeta(well.ops_risk_tier).accent;
        const point = project(well.easting, well.northing, is3D ? well.ops_risk_score : 0);
        const floorPoint = project(well.easting, well.northing, 0);
        const active = selectedWellId === well.well_id;
        const size = is3D ? clamp(8 + well.queue_exposure * 1.2, 8, 20) : clamp(10 + well.queue_exposure * 1.4, 10, 22);
        const fill =
          accent === DARK_RED ? "url(#atlasRedBar)"
          : accent === SOLID_YELLOW ? "url(#atlasYellowBar)"
          : "url(#atlasBlueBar)";

        return (
          <g key={well.well_id} onClick={() => onSelectWell(well.well_id)} style={{ cursor: "pointer" }}>
            {is3D && (
              <>
                <line
                  x1={floorPoint.x}
                  y1={floorPoint.y}
                  x2={point.x}
                  y2={point.y}
                  stroke={accent}
                  strokeWidth={active ? 4 : 2.5}
                  opacity={0.85}
                />
                <circle cx={floorPoint.x} cy={floorPoint.y} r={3.2} fill={accent} opacity={0.4} />
              </>
            )}
            <circle
              cx={point.x}
              cy={point.y}
              r={size}
              fill={fill}
              stroke={active ? INK : PAPER}
              strokeWidth={active ? 4 : 2}
              filter={active ? "url(#atlasShadow)" : undefined}
            />
            {active && (
              <>
                <circle cx={point.x} cy={point.y} r={size + 8} fill="none" stroke={accent} strokeWidth="2" opacity="0.45" />
                <text
                  x={point.x}
                  y={point.y - size - 14}
                  textAnchor="middle"
                  fontFamily="IBM Plex Mono, monospace"
                  fontSize="14"
                  fontWeight="700"
                  letterSpacing="1.4"
                  fill={INK}
                >
                  {well.well_name.length > 18 ? `${well.well_name.slice(0, 18)}…` : well.well_name}
                </text>
              </>
            )}
          </g>
        );
      })}
    </svg>
  );
}

export default function FieldAtlas() {
  const { data, loading, error } = useCommandCenterData<AtlasPayload>("field_atlas", EMPTY_DATA);
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [filterMode, setFilterMode] = useState<FilterMode>("all");
  const [chartMode, setChartMode] = useState<ChartMode>("3d-topology");
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [selectedEntityType, setSelectedEntityType] = useState<"well" | "zone" | "corridor" | null>(null);
  const [focusOverlay, setFocusOverlay] = useState<FocusOverlay>(null);
  const [showCorridors, setShowCorridors] = useState(true);

  const filteredWells = useMemo(() => {
    const query = deferredSearch.toLowerCase();
    return data.wells.filter(w => {
       if (!matchesFilter(w.ops_risk_tier, filterMode)) return false;
       return !query || w.well_name.toLowerCase().includes(query) || w.project.toLowerCase().includes(query) || w.rig_no.toLowerCase().includes(query);
    });
  }, [data.wells, deferredSearch, filterMode]);

  // Set default selection
  useEffect(() => {
    if (!selectedEntityId && filteredWells.length > 0) {
       setSelectedEntityId(filteredWells[0].well_id);
       setSelectedEntityType("well");
    }
  }, [filteredWells, selectedEntityId]);

  const activeWell = selectedEntityType === "well" ? data.wells.find(w => w.well_id === selectedEntityId) : null;
  const activeZone = selectedEntityType === "zone" ? data.zones.find(z => z.zone_id === selectedEntityId) : null;
  const activeCorridor = selectedEntityType === "corridor" ? data.corridors.find(c => c.id === selectedEntityId) : null;

  const effectiveBounds = useMemo(() => {
    const boundMinX = finiteNumber(data.bounds.min_easting);
    const boundMaxX = finiteNumber(data.bounds.max_easting);
    const boundMinY = finiteNumber(data.bounds.min_northing);
    const boundMaxY = finiteNumber(data.bounds.max_northing);
    if (boundMinX !== null && boundMaxX !== null && boundMinY !== null && boundMaxY !== null) {
      return {
        min_easting: boundMinX,
        max_easting: boundMaxX,
        min_northing: boundMinY,
        max_northing: boundMaxY,
      };
    }

    const source = filteredWells.length > 0 ? filteredWells : data.wells;
    if (!source.length) {
      return {
        min_easting: 0,
        max_easting: 1,
        min_northing: 0,
        max_northing: 1,
      };
    }

    const eastings = source.map((w) => Number(w.easting)).filter((v) => Number.isFinite(v));
    const northings = source.map((w) => Number(w.northing)).filter((v) => Number.isFinite(v));
    const minEasting = eastings.length ? Math.min(...eastings) : 0;
    const maxEasting = eastings.length ? Math.max(...eastings) : 1;
    const minNorthing = northings.length ? Math.min(...northings) : 0;
    const maxNorthing = northings.length ? Math.max(...northings) : 1;
    return {
      min_easting: minEasting,
      max_easting: maxEasting <= minEasting ? minEasting + 1 : maxEasting,
      min_northing: minNorthing,
      max_northing: maxNorthing <= minNorthing ? minNorthing + 1 : maxNorthing,
    };
  }, [data.bounds, data.wells, filteredWells]);

  const visibleCorridors = useMemo(() => (showCorridors ? data.corridors : []), [data.corridors, showCorridors]);
  const hasPlotData = filteredWells.length > 0;

  if (loading || error) return <div className="min-h-[calc(100vh-32px)]" />;

  return (
    <div className="min-h-[calc(100vh-32px)] bg-[#FDFDFE] pb-8 text-[#111111]" style={{ fontFamily: "Figtree, system-ui, sans-serif", backgroundImage: "linear-gradient(rgba(15,98,254,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(15,98,254,0.035) 1px, transparent 1px)", backgroundSize: "40px 40px" }}>
      <div className="mx-auto flex w-full max-w-[1820px] flex-col gap-4 px-6 py-5 xl:px-8">
        
        {/* HEADER */}
        <SurfacePanel className="px-6 py-5 shrink-0">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div className="flex items-start gap-4">
              <MapGlyph/>
              <div className="space-y-3">
                <MonoLabel>Spatial Logistics</MonoLabel>
                <div className="text-[28px] font-semibold tracking-[-0.05em] text-[#111111]">Field Atlas Topology</div>
                <div className="flex flex-wrap gap-2">
                  <MetaChip label="Wells" value={`${filteredWells.length} positioned`} accent={INK} />
                  <MetaChip label="Corridors" value={data.summary.rig_corridors} accent={IBM_BLUE} />
                  <MetaChip label="Critical Layer" value={data.summary.critical_positioned} accent={DARK_RED} />
                </div>
              </div>
            </div>

            <div className="flex w-full flex-col gap-3 xl:w-[880px] xl:items-end">
              <div className="flex w-full gap-3">
                 <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search atlas by well or project..." className="h-12 flex-1 rounded-full border bg-white px-5 text-[15px] outline-none focus:border-[#0F62FE]" style={{borderColor: HAIRLINE}} />
                 <button onClick={() => setFocusOverlay("chart")} className="h-12 rounded-full border px-5 text-[12px] font-semibold uppercase tracking-[0.18em] transition-colors hover:bg-[#111111] hover:text-white" style={{ fontFamily: "IBM Plex Mono, monospace", borderColor: INK }}>Fullscreen Map</button>
              </div>
              <div className="flex flex-wrap gap-2">
                 <FilterChip label="All Tiers" active={filterMode === "all"} onClick={() => setFilterMode("all")} />
                 <FilterChip label="Critical" active={filterMode === "critical"} accent={DARK_RED} onClick={() => setFilterMode("critical")} />
                 <FilterChip label="High Risk" active={filterMode === "high"} accent={SOLID_YELLOW} onClick={() => setFilterMode("high")} />
              </div>
            </div>
          </div>
        </SurfacePanel>

        {/* MAIN BODY */}
        <div className="grid gap-4 xl:grid-cols-12">
            
           {/* LEFT METRICS */}
           <SurfacePanel className="xl:col-span-3">
              <div className="border-b px-5 py-4" style={{borderColor: SOFT}}>
                 <MonoLabel>Local Rig Sequencing</MonoLabel>
                 <div className="mt-2 text-[22px] font-semibold tracking-[-0.04em]">Priority Corridors</div>
              </div>
              <div className="space-y-3 p-3">
                 {data.corridors.slice(0, 10).map((c) => {
                    const active = selectedEntityId === c.id;
                    const meta = tierMeta(c.pressure_score >= 70 ? "CRITICAL" : "WATCH");
                    return (
                       <button key={c.id} onClick={() => { setSelectedEntityId(c.id); setSelectedEntityType("corridor"); }} className={`w-full text-left p-4 rounded-[18px] border transition-colors hover:bg-[#FCFCFD]`} style={{ borderColor: active ? meta.accent : SOFT, backgroundColor: active ? meta.tint : PAPER }}>
                          <div className="flex justify-between items-start">
                             <div>
                                <MonoLabel>Sequence Gap: {c.handover_gap_days}d</MonoLabel>
                                <div className="mt-1 text-[16px] font-semibold">{c.rig_no}</div>
                             </div>
                             <span className="text-[14px] font-semibold" style={{color: meta.accent}}>{formatNumber(c.pressure_score)}</span>
                          </div>
                          <div className="mt-3 text-[12px] text-[#6F7279]">From <b className="text-black">{c.from_well_name}</b> to <b className="text-black">{c.to_well_name}</b></div>
                          <div className="mt-2 flex gap-2">
                             <span className="bg-white border rounded px-2 py-1 text-[10px] uppercase font-bold text-[#111111]" style={{fontFamily:"IBM Plex Mono", borderColor:SOFT}}>{formatDistanceMeters(c.distance_m)}</span>
                             <span className="bg-white border rounded px-2 py-1 text-[10px] uppercase font-bold text-[#111111]" style={{fontFamily:"IBM Plex Mono", borderColor:SOFT}}>{c.dominant_bottleneck}</span>
                          </div>
                       </button>
                    )
                 })}
              </div>
           </SurfacePanel>

           {/* CENTER PLOTLY MAP */}
           <SurfacePanel className="relative flex min-h-[400px] flex-col xl:col-span-6">
              <div className="absolute top-4 left-4 z-10 flex gap-2">
                 <div className="bg-white/90 backdrop-blur rounded-full border shadow-sm p-1 inline-flex" style={{borderColor: HAIRLINE}}>
                    <FilterChip label="3D Topology" active={chartMode === "3d-topology"} onClick={() => setChartMode("3d-topology")} />
                    <FilterChip label="2D Extent" active={chartMode === "2d-map"} onClick={() => setChartMode("2d-map")} />
                 </div>
                 <div className="bg-white/90 backdrop-blur rounded-full border shadow-sm p-1 inline-flex" style={{borderColor: HAIRLINE}}>
                    <FilterChip label="Toggle Lines" active={showCorridors} accent={IBM_BLUE} onClick={() => setShowCorridors(s => !s)} />
                 </div>
              </div>

              <div className="relative h-[680px] w-full rounded-b-[24px] bg-[#FAFAFB] pt-[78px]">
                 {hasPlotData ? (
                   <AtlasCanvas
                     wells={filteredWells}
                     corridors={visibleCorridors}
                     bounds={effectiveBounds}
                     mode={chartMode}
                     onSelectWell={(wellId) => { setSelectedEntityId(wellId); setSelectedEntityType("well"); }}
                     onSelectCorridor={(corridorId) => { setSelectedEntityId(corridorId); setSelectedEntityType("corridor"); }}
                     selectedWellId={selectedEntityType === "well" ? selectedEntityId : null}
                     selectedCorridorId={selectedEntityType === "corridor" ? selectedEntityId : null}
                   />
                 ) : (
                   <div className="flex h-full items-center justify-center text-[13px] text-[#6F7279]">
                     No spatially positioned wells match the current filter.
                   </div>
                 )}
              </div>
              <div className="h-12 border-t bg-white px-5 flex items-center justify-between text-[11px] font-semibold text-[#6F7279] uppercase tracking-[0.1em]" style={{borderColor: SOFT, fontFamily: "IBM Plex Mono"}}>
                 <span>{filteredWells.length} visible entities mapped</span>
                 <span>WebGL Render Engine Active</span>
              </div>
           </SurfacePanel>

           {/* RIGHT DOSSIER */}
           <SurfacePanel className="xl:col-span-3">
              <div className="border-b px-5 py-4" style={{borderColor: SOFT}}>
                 <MonoLabel>Spatial Dossier</MonoLabel>
                 <div className="mt-2 text-[22px] font-semibold tracking-[-0.04em]">Entity inspector</div>
              </div>
              <div className="p-5">
                 {activeWell && (
                    <div className="space-y-5">
                       <div>
                          <SeverityPill value={activeWell.ops_risk_tier} />
                          <div className="mt-3 text-[28px] font-semibold tracking-tight">{activeWell.well_name}</div>
                          <div className="mt-1 text-[13px] text-[#6F7279]">{activeWell.project} • {activeWell.rig_no}</div>
                       </div>
                       <div className="grid grid-cols-2 gap-3">
                          <div className="rounded-[16px] border bg-[#FCFCFD] px-3 py-3" style={{borderColor: SOFT}}>
                             <MonoLabel>Ops Risk Score</MonoLabel>
                             <div className="mt-2 text-[22px] font-semibold" style={{color: tierMeta(activeWell.ops_risk_tier).accent}}>{formatNumber(activeWell.ops_risk_score)}</div>
                          </div>
                          <div className="rounded-[16px] border bg-[#FCFCFD] px-3 py-3" style={{borderColor: SOFT}}>
                             <MonoLabel>Spatial Signal</MonoLabel>
                             <div className="mt-2 text-[22px] font-semibold text-[#111111]">{formatNumber(activeWell.spatial_signal_score)}</div>
                          </div>
                          <div className="rounded-[16px] border bg-[#FCFCFD] px-3 py-3" style={{borderColor: SOFT}}>
                             <MonoLabel>Rig-On Delay</MonoLabel>
                             <div className="mt-2 text-[22px] font-semibold" style={{color: activeWell.rig_on_delay_days > 0 ? DARK_RED : ROBINHOOD_GREEN}}>{activeWell.rig_on_delay_days}d</div>
                          </div>
                          <div className="rounded-[16px] border bg-[#FCFCFD] px-3 py-3" style={{borderColor: SOFT}}>
                             <MonoLabel>Queue Impact</MonoLabel>
                             <div className="mt-2 text-[22px] font-semibold text-[#111111]">{activeWell.queue_exposure} wells</div>
                          </div>
                       </div>
                       
                       <div>
                          <MonoLabel>Anomaly Engine Evidence</MonoLabel>
                          <div className="mt-3 space-y-2">
                             {activeWell.evidence?.map((e, i) => (
                                <div key={i} className="p-3 bg-white border rounded-[12px] text-[12px] leading-5 text-[#4A4E57]" style={{borderColor: SOFT}}>{e}</div>
                             ))}
                          </div>
                       </div>
                       
                       <div className="flex flex-wrap gap-2 pt-2 border-t" style={{borderColor: SOFT}}>
                          <MetaChip label="Recovery" value={`${activeWell.recovery_confidence_pct}%`} accent={ROBINHOOD_GREEN} />
                          <MetaChip label="Density" value={formatNumber(activeWell.local_density_score)} accent={IBM_BLUE} />
                          <MetaChip label="Zone" value={activeWell.zone_id} accent={INK} />
                       </div>
                    </div>
                 )}
                 {activeCorridor && (
                    <div className="space-y-4">
                       <div>
                          <SeverityPill value={activeCorridor.pressure_score >= 70 ? "CRITICAL" : "WATCH"} />
                          <div className="mt-3 text-[24px] font-semibold tracking-tight">{activeCorridor.rig_no} Transit</div>
                       </div>
                       <MetaChip label="Type" value={activeCorridor.corridor_type} accent={INK} />
                       <div className="grid gap-3">
                          <div className="p-4 bg-[#FCFCFD] border rounded-[16px]" style={{borderColor: SOFT}}>
                             <div className="text-[12px] font-semibold text-[#111111]">{activeCorridor.from_well_name}</div>
                             <div className="my-2 border-l-2 ml-2 pl-3 py-1 space-y-1" style={{borderColor: HAIRLINE}}>
                                <div className="text-[10px] uppercase font-bold text-[#6F7279]" style={{fontFamily:"IBM Plex Mono"}}>Distance: {formatDistanceMeters(activeCorridor.distance_m)}</div>
                                <div className="text-[10px] uppercase font-bold text-[#6F7279]" style={{fontFamily:"IBM Plex Mono"}}>Gap: {activeCorridor.handover_gap_days} days</div>
                             </div>
                             <div className="text-[12px] font-semibold text-[#111111]">{activeCorridor.to_well_name}</div>
                          </div>
                          <div className="p-4 bg-white border rounded-[16px] text-[12px] text-[#4A4E57] leading-5" style={{borderColor: SOFT}}>
                             Driving Bottleneck: <b>{activeCorridor.dominant_bottleneck}</b>. Spatial model identifies this corridor as a high-pressure sequenced transition.
                          </div>
                       </div>
                    </div>
                 )}
                 {!activeCorridor && !activeWell && (
                    <div className="text-center text-[#6F7279] text-[13px] pt-10">Select an entity from the map or left matrix to view deep causal metrics.</div>
                 )}
              </div>
           </SurfacePanel>

        </div>

        {/* FULLSCREEN MAP OVERLAY */}
        {focusOverlay === "chart" && (
           <div className="fixed inset-0 z-50 overflow-y-auto bg-[rgba(15,23,42,0.8)] p-6 backdrop-blur-sm xl:p-8">
              <SurfacePanel className="relative mx-auto flex min-h-[calc(100vh-48px)] w-full max-w-[1880px] flex-col overflow-hidden xl:min-h-[calc(100vh-64px)]">
                 <div className="absolute top-6 left-6 z-10 flex flex-col gap-3">
                    <div className="bg-white/90 backdrop-blur rounded-full border shadow-sm p-1 inline-flex" style={{borderColor: HAIRLINE}}>
                       <FilterChip label="3D Topology" active={chartMode === "3d-topology"} onClick={() => setChartMode("3d-topology")} />
                       <FilterChip label="2D Extent" active={chartMode === "2d-map"} onClick={() => setChartMode("2d-map")} />
                    </div>
                 </div>
                 <div className="absolute top-6 right-6 z-10">
                    <button onClick={() => setFocusOverlay(null)} className="rounded-full bg-black text-white px-6 py-3 text-[12px] font-semibold uppercase tracking-[0.16em] shadow-lg hover:bg-[#333333]" style={{ fontFamily: "IBM Plex Mono" }}>Exit Fullscreen</button>
                 </div>
                 <div className="h-[calc(100vh-48px)] min-h-[760px] w-full bg-[#FAFAFB]">
                   {hasPlotData ? (
                     <AtlasCanvas
                       wells={filteredWells}
                       corridors={visibleCorridors}
                       bounds={effectiveBounds}
                       mode={chartMode}
                       onSelectWell={(wellId) => { setSelectedEntityId(wellId); setSelectedEntityType("well"); }}
                       onSelectCorridor={(corridorId) => { setSelectedEntityId(corridorId); setSelectedEntityType("corridor"); }}
                       selectedWellId={selectedEntityType === "well" ? selectedEntityId : null}
                       selectedCorridorId={selectedEntityType === "corridor" ? selectedEntityId : null}
                     />
                   ) : (
                     <div className="flex h-full items-center justify-center text-[14px] text-[#6F7279]">
                       No map is available for the current atlas filter.
                     </div>
                   )}
                 </div>
                 
                 <div className="absolute bottom-6 left-6 z-10 flex gap-4 max-w-xl bg-white/95 backdrop-blur border p-6 rounded-[24px] shadow-2xl" style={{borderColor: HAIRLINE}}>
                    <div>
                       <MonoLabel>Executive Brief</MonoLabel>
                       <div className="text-[18px] font-semibold mt-2">{data.engine_label || "Spatial Topology"}</div>
                       <p className="text-[12px] text-[#4A4E57] leading-5 mt-2">Visually mapping {filteredWells.length} wells on continuous 3D coordinate planes. Z-axis represents operational risk density computed via asynchronous Isolation Forests. Drag canvas to rotate.</p>
                       <div className="flex gap-2 mt-4">
                          <MetaChip label="Wells" value={filteredWells.length} accent={INK} />
                          <MetaChip label="Corridors" value={data.summary.rig_corridors} accent={IBM_BLUE} />
                       </div>
                    </div>
                 </div>
              </SurfacePanel>
           </div>
        )}

      </div>
    </div>
  );
}
