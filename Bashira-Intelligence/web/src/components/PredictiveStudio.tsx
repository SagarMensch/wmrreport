"use client";
import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import PredictiveAlgorithmDemoPanel from "./PredictiveAlgorithmDemoPanel";

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

interface WellSummary {
  pdo_well_id: string;
  well_name: string;
  rig_no: string;
  well_type: string;
  cluster: string;
  progress_pct: number;
  status: string;
  risk_tier: string;
  risk_score: number;
  buffer_status: string;
}

interface GanttPhase {
  phase_id: string;
  label: string;
  start: string | null;
  end: string | null;
  progress: number | null;
  status: string;
  color: string;
  duration_days: number | null;
}

interface Milestone {
  sequence: number;
  label: string;
  base_label?: string;
  phase_id?: string;
  date: string | null;
  timestamp?: number | null;
  status: "COMPLETED" | "SCHEDULED" | "OVERDUE" | "PENDING";
  is_completed?: boolean;
  is_future?: boolean;
  date_kind?: string;
}

interface HistoryPoint {
  week: string;
  progress: number | null;
  loc_prep?: number | null;
  engineering?: number | null;
  construction?: number | null;
  commissioning?: number | null;
  ohl?: number | null;
}

interface ForecastPoint {
  week: string;
  predicted: number;
  lower: number;
  upper: number;
  is_forecast: boolean;
  estimated_completion?: string;
  weeks_remaining?: number;
}

interface DataLineage {
  current_state_source?: string;
  current_snapshot_date?: string | null;
  history_source?: string;
  history_points?: number;
  plan_vs_actual_source?: string;
  forecast_source?: string;
  risk_source?: string;
}

interface RiskData {
  score: number;
  tier: string;
  components: Record<string, number>;
  drivers: Array<{
    factor: string;
    impact: number;
    direction: string;
    description?: string;
  }>;
}

interface RootCause {
  factor: string;
  description: string;
  delay_days: number;
  type: string;
  support_cases?: number;
}

interface ScenarioOption {
  value: string;
  label: string;
  support_cases?: number;
}

interface ScenarioAction {
  id: string;
  label: string;
  description: string;
  parameter_label?: string;
  default_value?: string;
  options: ScenarioOption[];
}

interface ScenarioBaseline {
  weekly_momentum_pct?: number;
  expected_completion_date?: string;
  support_cases?: number;
  benchmark_scope?: string;
  days_to_complete?: number;
  low_case_completion_date?: string;
  high_case_completion_date?: string;
}

interface CausalIntelligence {
  root_causes: RootCause[];
  interventions_available?: {
    actions?: ScenarioAction[];
    rigs?: string[];
    can_expedite?: boolean;
  };
  baseline?: ScenarioBaseline;
  methodology?: string;
  error?: string;
}

interface WellDetail {
  well_id: string;
  current_state: Record<string, any>;
  history: HistoryPoint[];
  gantt: GanttPhase[];
  forecast: ForecastPoint[];
  milestones: Milestone[];
  risk: RiskData;
  ml_intelligence?: {
    hidden_insights?: Array<{
      factor: string;
      description: string;
      direction: string;
    }>;
    causal_intelligence?: CausalIntelligence;
    error?: string;
  };
  data_lineage?: DataLineage;
  plan_vs_actual: { entries?: any[] };
}

interface Portfolio {
  total_wells: number;
  completed: number;
  active: number;
  not_started: number;
  avg_progress: number;
  tier_distribution: Record<string, number>;
  rig_performance: Array<{
    rig_no: string;
    avg_progress: number;
    well_count: number;
  }>;
}

// ═══════════════════════════════════════════════════════════════════════════
// DESIGN TOKENS (LIGHT THEME - FINANCIAL/PALANTIR APPROACH)
// ═══════════════════════════════════════════════════════════════════════════

const TIER_COLORS: Record<string, string> = {
  CRITICAL: "#D32F2F", // Strong red
  HIGH_RISK: "#ED6C02", // Strong orange
  WATCH: "#ED6C02", // Orange/Amber
  HEALTHY: "#2E7D32", // Strong green
  UNAVAILABLE: "#6B7280",
};

const STATUS_COLORS: Record<string, string> = {
  COMPLETED: "#2E7D32",
  DRILLING: "#1976D2", // Blue for active drilling
  IN_PROGRESS: "#1976D2",
  NOT_STARTED: "#757575",
};

const formatSourceLabel = (source?: string | null) => {
  if (!source) return "Unknown";
  return source
    .replace(/_/g, " ")
    .replace(/\bsql\b/gi, "SSMS")
    .replace(/\bwmr full\b/gi, "WMR Full")
    .replace(/\bcpu ml service\b/gi, "CPU ML")
    .replace(/\bcsv fallback\b/gi, "CSV Fallback")
    .replace(/\bcleaned\b/gi, "Cleaned")
    .replace(/\bheuristic fallback\b/gi, "Heuristic Fallback")
    .replace(/\bssms\b/gi, "SSMS")
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

const RISK_COMPONENT_LABELS: Record<string, string> = {
  progress: "Current Completion",
  recent_momentum_3w: "Recent Momentum",
  rig_efficiency_weekly: "Rig Execution Pace",
  cluster_density: "Workfront Congestion",
  material_lead_days: "Material Lead Time",
  has_engineering_started: "Engineering Readiness",
  has_location_started: "Location Readiness",
  is_rig_on: "Rig-On State",
  days_to_expected_rig_off: "Time To Target",
  schedule_pressure: "Schedule Gap",
};

const MILESTONE_STATUS_STYLE: Record<
  Milestone["status"],
  {
    cardBg: string;
    border: string;
    dot: string;
    label: string;
    text: string;
    subtext: string;
    badgeBg: string;
    badgeText: string;
  }
> = {
  COMPLETED: {
    cardBg: "#111827",
    border: "#111827",
    dot: "#00C805",
    label: "Completed",
    text: "#FFFFFF",
    subtext: "rgba(255,255,255,0.72)",
    badgeBg: "rgba(255,255,255,0.12)",
    badgeText: "#FFFFFF",
  },
  SCHEDULED: {
    cardBg: "#EEF4FF",
    border: "#D6E4FF",
    dot: "#1976D2",
    label: "Scheduled",
    text: "#111827",
    subtext: "#4B5563",
    badgeBg: "#DCEAFF",
    badgeText: "#0F62FE",
  },
  OVERDUE: {
    cardBg: "#FFF4E8",
    border: "#FFD9B5",
    dot: "#ED6C02",
    label: "Overdue",
    text: "#111827",
    subtext: "#7C4A03",
    badgeBg: "#FFE8CF",
    badgeText: "#B45309",
  },
  PENDING: {
    cardBg: "#F9FAFB",
    border: "#E5E7EB",
    dot: "#9CA3AF",
    label: "Pending",
    text: "#374151",
    subtext: "#6B7280",
    badgeBg: "#F3F4F6",
    badgeText: "#6B7280",
  },
};

// ═══════════════════════════════════════════════════════════════════════════
// MICRO COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════

const CleanCard = ({
  children,
  className = "",
  style = {},
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) => (
  <div
    className={className}
    style={{
      background: "#FFFFFF",
      border: "1px solid #E5E7EB",
      borderRadius: "8px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
      ...style,
    }}
  >
    {children}
  </div>
);

const ProgressRing = ({
  value,
  size = 56,
  strokeWidth = 4,
  color = "#1976D2",
}: {
  value: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(value, 100) / 100) * circumference;
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="#F3F4F6"
        strokeWidth={strokeWidth}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{
          transition: "stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      />
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#111827"
        fontSize={size * 0.22}
        fontWeight="600"
        style={{
          transform: "rotate(90deg)",
          transformOrigin: "center",
          fontFamily: '"Inter", sans-serif',
        }}
      >
        {Math.round(value)}%
      </text>
    </svg>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// PORTFOLIO DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════

const PortfolioDashboard = ({
  portfolio,
  wells,
  onSelectWell,
}: {
  portfolio: Portfolio;
  wells: WellSummary[];
  onSelectWell: (id: string) => void;
}) => {
  const tiers = portfolio.tier_distribution || {};
  const totalTier = Object.values(tiers).reduce((a, b) => a + b, 0) || 1;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "20px",
        padding: "24px",
        background: "#F8F9FA",
        minHeight: "100%",
      }}
    >
      <PredictiveAlgorithmDemoPanel />

      {/* KPI Row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: "16px",
        }}
      >
        {[
          {
            label: "Total Wells",
            value: portfolio.total_wells,
            color: "#374151",
          },
          { label: "Active", value: portfolio.active, color: "#1976D2" },
          { label: "Completed", value: portfolio.completed, color: "#2E7D32" },
          {
            label: "Avg Progress",
            value: `${portfolio.avg_progress}%`,
            color: "#374151",
          },
          {
            label: "Critical Risk",
            value: tiers.CRITICAL || 0,
            color: "#D32F2F",
          },
        ].map((kpi, i) => (
          <CleanCard
            key={i}
            style={{
              padding: "20px 16px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                fontSize: "11px",
                color: "#6B7280",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: "8px",
              }}
            >
              {kpi.label}
            </div>
            <div
              style={{
                fontSize: "28px",
                fontWeight: "700",
                color: kpi.color,
                fontFamily: "'Inter', sans-serif",
                lineHeight: 1,
              }}
            >
              {kpi.value}
            </div>
          </CleanCard>
        ))}
      </div>

      {/* Risk Distribution Bar */}
      <CleanCard style={{ padding: "20px 24px" }}>
        <div
          style={{
            fontSize: "12px",
            color: "#4B5563",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            marginBottom: "16px",
          }}
        >
          Portfolio Risk Distribution
        </div>
        <div
          style={{
            display: "flex",
            height: "16px",
            borderRadius: "4px",
            overflow: "hidden",
            gap: "1px",
          }}
        >
          {["CRITICAL", "HIGH_RISK", "WATCH", "HEALTHY"].map((tier) => {
            const pct = ((tiers[tier] || 0) / totalTier) * 100;
            return pct > 0 ? (
              <div
                key={tier}
                style={{
                  width: `${pct}%`,
                  background: TIER_COLORS[tier],
                  transition: "width 1s ease",
                }}
                title={`${tier}: ${tiers[tier]}`}
              />
            ) : null;
          })}
        </div>
        <div style={{ display: "flex", gap: "24px", marginTop: "12px" }}>
          {["CRITICAL", "HIGH_RISK", "WATCH", "HEALTHY"].map((tier) => (
            <div
              key={tier}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "12px",
                color: "#374151",
                fontWeight: 500,
              }}
            >
              <div
                style={{
                  width: "10px",
                  height: "10px",
                  borderRadius: "2px",
                  background: TIER_COLORS[tier],
                }}
              />
              {tier.replace("_", " ")}{" "}
              <span style={{ color: "#6B7280" }}>({tiers[tier] || 0})</span>
            </div>
          ))}
        </div>
      </CleanCard>

      {/* Well Grid — Financial Table Style approach inside cards */}
      <CleanCard style={{ padding: "20px 24px", flex: 1 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "16px",
          }}
        >
          <div
            style={{
              fontSize: "12px",
              color: "#4B5563",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Well Forecast Registry
          </div>
          <div style={{ fontSize: "12px", color: "#6B7280" }}>
            Showing {wells.length} objects
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: "12px",
          }}
        >
          {wells.map((w) => (
            <motion.div
              key={w.pdo_well_id}
              whileHover={{
                scale: 1.01,
                boxShadow:
                  "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
              }}
              whileTap={{ scale: 0.99 }}
              onClick={() => onSelectWell(w.pdo_well_id)}
              style={{
                background: "#FFFFFF",
                border: "1px solid #E5E7EB",
                borderLeft: `4px solid ${TIER_COLORS[w.risk_tier]}`,
                borderRadius: "6px",
                padding: "16px",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  marginBottom: "12px",
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: "10px",
                      color: "#6B7280",
                      fontWeight: 600,
                      marginBottom: "2px",
                    }}
                  >
                    {w.pdo_well_id}
                  </div>
                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: "600",
                      color: "#111827",
                      maxWidth: "180px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {w.well_name || "N/A"}
                  </div>
                </div>
                <div
                  style={{
                    fontSize: "10px",
                    fontWeight: "600",
                    padding: "2px 6px",
                    borderRadius: "4px",
                    background: `${TIER_COLORS[w.risk_tier]}15`,
                    color: TIER_COLORS[w.risk_tier],
                  }}
                >
                  {w.risk_tier?.replace("_", " ")}
                </div>
              </div>

              <div
                style={{
                  flexWrap: "wrap",
                  display: "flex",
                  gap: "12px",
                  marginBottom: "12px",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontSize: "10px", color: "#6B7280" }}>
                    RIG
                  </span>
                  <span
                    style={{
                      fontSize: "12px",
                      color: "#374151",
                      fontWeight: 500,
                    }}
                  >
                    {w.rig_no || "—"}
                  </span>
                </div>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontSize: "10px", color: "#6B7280" }}>
                    CLUSTER
                  </span>
                  <span
                    style={{
                      fontSize: "12px",
                      color: "#374151",
                      fontWeight: 500,
                    }}
                  >
                    {w.cluster || "—"}
                  </span>
                </div>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div
                  style={{
                    fontSize: "11px",
                    color: "#4B5563",
                    fontWeight: 600,
                  }}
                >
                  Overall Progress
                </div>
                <div
                  style={{
                    fontSize: "14px",
                    fontWeight: "700",
                    color: "#111827",
                  }}
                >
                  {w.progress_pct}%
                </div>
              </div>
              <div
                style={{
                  height: "4px",
                  borderRadius: "2px",
                  background: "#F3F4F6",
                  marginTop: "6px",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    borderRadius: "2px",
                    background: TIER_COLORS[w.risk_tier],
                    width: `${Math.min(w.progress_pct, 100)}%`,
                    transition: "width 0.5s ease",
                  }}
                />
              </div>
            </motion.div>
          ))}
        </div>
      </CleanCard>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// WELL DEEP DIVE
// ═══════════════════════════════════════════════════════════════════════════

const WellDeepDive = ({
  detail,
  onBack,
}: {
  detail: WellDetail;
  onBack: () => void;
}) => {
  const cs = detail.current_state;
  const risk = detail.risk;
  const tierColor = TIER_COLORS[risk?.tier] || "#6B7280";
  const causal = detail.ml_intelligence?.causal_intelligence;
  const lineage = detail.data_lineage;
  const scenarioActions = useMemo(
    () => causal?.interventions_available?.actions || [],
    [causal],
  );
  const milestones = (detail.milestones || []).map((milestone, index) => {
    const derivedStatus: Milestone["status"] =
      milestone.status ||
      (milestone.is_completed
        ? "COMPLETED"
        : milestone.is_future
          ? "SCHEDULED"
          : milestone.date
            ? "COMPLETED"
            : "PENDING");

    return {
      ...milestone,
      sequence: milestone.sequence ?? index + 1,
      status: derivedStatus,
    };
  });
  const completedMilestones = milestones.filter(
    (m) => m.status === "COMPLETED",
  ).length;
  const scheduledMilestones = milestones.filter(
    (m) => m.status === "SCHEDULED",
  ).length;
  const overdueMilestones = milestones.filter(
    (m) => m.status === "OVERDUE",
  ).length;
  const pendingMilestones = milestones.filter(
    (m) => m.status === "PENDING",
  ).length;
  const milestoneCompletionPct =
    milestones.length > 0 ? (completedMilestones / milestones.length) * 100 : 0;

  const [simParams, setSimParams] = useState({
    intervention_type: "",
    intervention_value: "",
  });
  const [simResult, setSimResult] = useState<any>(null);
  const [simLoading, setSimLoading] = useState(false);

  useEffect(() => {
    const firstAction = scenarioActions[0];
    if (!firstAction) {
      setSimParams({ intervention_type: "", intervention_value: "" });
      return;
    }
    setSimParams({
      intervention_type: firstAction.id,
      intervention_value:
        firstAction.default_value || firstAction.options?.[0]?.value || "",
    });
  }, [detail.well_id, scenarioActions]);

  const selectedAction = scenarioActions.find(
    (action) => action.id === simParams.intervention_type,
  );

  const runSimulation = async () => {
    if (!simParams.intervention_type) return;
    setSimLoading(true);
    setSimResult(null);
    try {
      const res = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ well_id: detail.well_id, ...simParams }),
      });
      if (res.ok) {
        setSimResult(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
    setSimLoading(false);
  };

  // Chart dimensions
  const chartW = 720,
    chartH = 260,
    padL = 50,
    padR = 20,
    padT = 20,
    padB = 30;

  // Build combined history + forecast series
  const histPts = (detail.history || []).filter((h) => h.progress != null);
  const forecastPts = (detail.forecast || []).filter((f) => f.is_forecast);

  const allProgressValues = [
    ...histPts.map((h) => h.progress!),
    ...forecastPts.map((f) => f.upper),
  ];
  const maxY = Math.max(
    100,
    Math.min(110, Math.max(...allProgressValues) + 10),
  ); // max 100 or slightly above
  const totalPts = histPts.length + forecastPts.length;

  const toX = (i: number) =>
    padL + ((chartW - padL - padR) * i) / Math.max(totalPts - 1, 1);
  const toY = (v: number) => padT + (chartH - padT - padB) * (1 - v / maxY);

  const histLine = histPts
    .map((h, i) => `${toX(i)},${toY(h.progress!)}`)
    .join(" ");
  const forecastLine = forecastPts
    .map((f, i) => `${toX(histPts.length + i)},${toY(f.predicted)}`)
    .join(" ");
  const forecastBand =
    forecastPts.length > 0
      ? forecastPts
          .map((f, i) => `${toX(histPts.length + i)},${toY(f.upper)}`)
          .join(" ") +
        " " +
        [...forecastPts]
          .reverse()
          .map(
            (f, i) =>
              `${toX(histPts.length + forecastPts.length - 1 - i)},${toY(f.lower)}`,
          )
          .join(" ")
      : "";

  const connectorLine =
    histPts.length > 0 && forecastPts.length > 0
      ? `${toX(histPts.length - 1)},${toY(histPts[histPts.length - 1].progress!)} ${toX(histPts.length)},${toY(forecastPts[0].predicted)}`
      : "";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "20px",
        padding: "24px",
        background: "#F8F9FA",
        minHeight: "100%",
      }}
    >
      {/* Header with back button */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "20px",
          background: "#FFFFFF",
          padding: "20px 24px",
          borderRadius: "8px",
          border: "1px solid #E5E7EB",
        }}
      >
        <button
          onClick={onBack}
          style={{
            background: "#F3F4F6",
            border: "1px solid #E5E7EB",
            borderRadius: "6px",
            padding: "8px 12px",
            color: "#374151",
            cursor: "pointer",
            fontSize: "13px",
            fontWeight: 500,
            display: "flex",
            alignItems: "center",
            gap: "6px",
            transition: "all 0.15s ease",
          }}
          onMouseOver={(e) => (e.currentTarget.style.background = "#E5E7EB")}
          onMouseOut={(e) => (e.currentTarget.style.background = "#F3F4F6")}
        >
          ← Back
        </button>
        <div style={{ flex: 1 }}>
          <div
            style={{
              fontSize: "24px",
              fontWeight: "700",
              color: "#111827",
              letterSpacing: "-0.02em",
              marginBottom: "4px",
            }}
          >
            {cs.well_name || cs.pdo_well_id}
          </div>
          <div
            style={{
              fontSize: "13px",
              color: "#6B7280",
              display: "flex",
              gap: "16px",
            }}
          >
            <span>
              <strong style={{ fontWeight: 600, color: "#374151" }}>ID:</strong>{" "}
              {cs.pdo_well_id}
            </span>
            <span>
              <strong style={{ fontWeight: 600, color: "#374151" }}>
                Rig:
              </strong>{" "}
              {cs.rig_no || "—"}
            </span>
            <span>
              <strong style={{ fontWeight: 600, color: "#374151" }}>
                Type:
              </strong>{" "}
              {cs.well_type || "—"}
            </span>
            <span>
              <strong style={{ fontWeight: 600, color: "#374151" }}>
                Cluster:
              </strong>{" "}
              {cs.cluster || "—"}
            </span>
          </div>
          {lineage && (
            <div
              style={{
                marginTop: "8px",
                fontSize: "11px",
                color: "#6B7280",
                display: "flex",
                gap: "12px",
                flexWrap: "wrap",
              }}
            >
              <span>
                <strong style={{ color: "#374151" }}>Snapshot:</strong>{" "}
                {lineage.current_snapshot_date || "—"}
              </span>
              <span>
                <strong style={{ color: "#374151" }}>Facts:</strong>{" "}
                {formatSourceLabel(lineage.current_state_source)}
              </span>
              <span>
                <strong style={{ color: "#374151" }}>History:</strong>{" "}
                {formatSourceLabel(lineage.history_source)}
              </span>
              <span>
                <strong style={{ color: "#374151" }}>Forecast:</strong>{" "}
                {formatSourceLabel(lineage.forecast_source)}
              </span>
              <span>
                <strong style={{ color: "#374151" }}>Risk:</strong>{" "}
                {formatSourceLabel(lineage.risk_source)}
              </span>
            </div>
          )}
        </div>
        <div
          style={{
            display: "flex",
            gap: "16px",
            alignItems: "center",
            paddingLeft: "24px",
            borderLeft: "1px solid #E5E7EB",
          }}
        >
          <div>
            <div
              style={{
                fontSize: "11px",
                fontWeight: 600,
                color: "#6B7280",
                textTransform: "uppercase",
                marginBottom: "4px",
                textAlign: "right",
              }}
            >
              Risk Assessment
            </div>
            <div
              style={{
                padding: "4px 10px",
                borderRadius: "4px",
                fontSize: "13px",
                fontWeight: "700",
                background: `${tierColor}15`,
                color: tierColor,
                border: `1px solid ${tierColor}30`,
                textAlign: "right",
              }}
            >
              {risk?.tier?.replace("_", " ")} ({risk?.score}%)
            </div>
          </div>
          <ProgressRing value={risk?.score || 0} size={56} color={tierColor} />
        </div>
      </div>

      {/* Phase Progress Cards (Light theme) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: "16px",
        }}
      >
        {[
          { label: "Engineering", value: cs.engg_progress, color: "#1976D2" },
          { label: "Loc Prep", value: cs.loc_prep_progress, color: "#9C27B0" },
          { label: "Construction", value: cs.const_progress, color: "#0097A7" },
          { label: "OHL", value: cs.ohl_progress, color: "#ED6C02" },
          { label: "Commissioning", value: cs.comm_progress, color: "#2E7D32" },
        ].map((p, i) => (
          <CleanCard
            key={i}
            style={{
              padding: "16px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: "11px",
                  color: "#6B7280",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  marginBottom: "4px",
                }}
              >
                {p.label}
              </div>
              <div
                style={{ fontSize: "20px", fontWeight: 700, color: "#111827" }}
              >
                {p.value == null ? "N/A" : `${p.value.toFixed(1)}%`}
              </div>
            </div>
            <ProgressRing
              value={p.value ?? 0}
              size={42}
              strokeWidth={4}
              color={p.color}
            />
          </CleanCard>
        ))}
      </div>

      <div
        style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: "16px" }}
      >
        {/* Progress Forecast Chart */}
        <CleanCard style={{ padding: "24px" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "20px",
            }}
          >
            <div
              style={{
                fontSize: "13px",
                color: "#374151",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Predictive Trajectory
            </div>
            {/* Legend */}
            <div
              style={{
                display: "flex",
                gap: "16px",
                fontSize: "11px",
                fontWeight: 500,
                color: "#4B5563",
              }}
            >
              <span
                style={{ display: "flex", alignItems: "center", gap: "4px" }}
              >
                <div
                  style={{
                    width: "12px",
                    height: "3px",
                    background: "#1976D2",
                  }}
                />{" "}
                Actual
              </span>
              <span
                style={{ display: "flex", alignItems: "center", gap: "4px" }}
              >
                <div
                  style={{
                    width: "12px",
                    height: "3px",
                    background: tierColor,
                    borderTop: `2px dashed white`,
                  }}
                />{" "}
                Forecast
              </span>
              <span
                style={{ display: "flex", alignItems: "center", gap: "4px" }}
              >
                <div
                  style={{
                    width: "12px",
                    height: "10px",
                    background: `${tierColor}15`,
                  }}
                />{" "}
                95% CI
              </span>
            </div>
          </div>

          <svg
            width={chartW}
            height={chartH}
            style={{
              display: "block",
              width: "100%",
              height: "auto",
              background: "#FFFFFF",
            }}
            viewBox={`0 0 ${chartW} ${chartH}`}
          >
            {/* Grid lines */}
            {[0, 25, 50, 75, 100].map((v) => (
              <g key={v}>
                <line
                  x1={padL}
                  y1={toY(v)}
                  x2={chartW - padR}
                  y2={toY(v)}
                  stroke="#F3F4F6"
                  strokeWidth="1"
                />
                <text
                  x={padL - 12}
                  y={toY(v) + 4}
                  fill="#9CA3AF"
                  fontSize="11"
                  fontFamily="Inter"
                  textAnchor="end"
                >
                  {v}%
                </text>
              </g>
            ))}
            {/* Forecast confidence band */}
            {forecastBand && (
              <polygon
                points={forecastBand}
                fill={`${tierColor}15`}
                stroke="none"
              />
            )}
            {/* History line */}
            {histLine && (
              <polyline
                points={histLine}
                fill="none"
                stroke="#1976D2"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}
            {connectorLine && (
              <polyline
                points={connectorLine}
                fill="none"
                stroke={tierColor}
                strokeWidth="2"
                strokeDasharray="4,4"
              />
            )}
            {forecastLine && (
              <polyline
                points={forecastLine}
                fill="none"
                stroke={tierColor}
                strokeWidth="2.5"
                strokeDasharray="6,4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}
            {/* Data points */}
            {histPts.map((h, i) => (
              <circle
                key={i}
                cx={toX(i)}
                cy={toY(h.progress!)}
                r="3.5"
                fill="#FFFFFF"
                stroke="#1976D2"
                strokeWidth="2"
              />
            ))}
            {forecastPts.map((f, i) => (
              <circle
                key={`f${i}`}
                cx={toX(histPts.length + i)}
                cy={toY(f.predicted)}
                r="3.5"
                fill="#FFFFFF"
                stroke={tierColor}
                strokeWidth="2"
              />
            ))}
            {/* X-axis labels */}
            {histPts
              .filter(
                (_, i) => i % Math.max(1, Math.floor(histPts.length / 6)) === 0,
              )
              .map((h, idx) => {
                const origIdx = histPts.indexOf(h);
                return (
                  <text
                    key={idx}
                    x={toX(origIdx)}
                    y={chartH - 4}
                    fill="#6B7280"
                    fontSize="10"
                    fontFamily="Inter"
                    textAnchor="middle"
                  >
                    {h.week?.substring(5, 10)}
                  </text>
                );
              })}
          </svg>
          {lineage && (
            <div
              style={{
                marginTop: "12px",
                fontSize: "11px",
                color: "#6B7280",
                display: "flex",
                justifyContent: "space-between",
                gap: "16px",
                flexWrap: "wrap",
              }}
            >
              <span>
                Actual line: {formatSourceLabel(lineage.history_source)} (
                {lineage.history_points ?? 0} points)
              </span>
              <span>
                Forecast line: {formatSourceLabel(lineage.forecast_source)}
              </span>
            </div>
          )}

          {detail.ml_intelligence?.hidden_insights &&
            detail.ml_intelligence.hidden_insights.length > 0 && (
              <div
                style={{
                  marginTop: "20px",
                  padding: "16px",
                  borderRadius: "8px",
                  background: "#F9FAFB",
                  border: "1px solid #E5E7EB",
                }}
              >
                <div
                  style={{
                    fontSize: "14px",
                    color: "#111827",
                    fontWeight: 600,
                    marginBottom: "12px",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <span style={{ color: "#6366F1" }}>✧</span> AI Hidden Insights
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  {detail.ml_intelligence.hidden_insights.map(
                    (insight, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          gap: "12px",
                        }}
                      >
                        <div
                          style={{
                            flexShrink: 0,
                            marginTop: "2px",
                            width: "6px",
                            height: "6px",
                            borderRadius: "50%",
                            background:
                              insight.direction === "negative"
                                ? "#EF4444"
                                : "#10B981",
                          }}
                        />
                        <div>
                          <div
                            style={{
                              fontSize: "13px",
                              fontWeight: 500,
                              color: "#374151",
                            }}
                          >
                            {insight.factor}
                          </div>
                          <div
                            style={{
                              fontSize: "12px",
                              color: "#6B7280",
                              marginTop: "2px",
                            }}
                          >
                            {insight.description}
                          </div>
                        </div>
                      </div>
                    ),
                  )}
                </div>
              </div>
            )}
        </CleanCard>

        {/* Operations Gantt */}
        <CleanCard style={{ padding: "24px" }}>
          <div
            style={{
              fontSize: "13px",
              color: "#374151",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: "20px",
            }}
          >
            Phase Execution
          </div>
          <div
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            {detail.gantt.map((phase) => (
              <div key={phase.phase_id}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "6px",
                  }}
                >
                  <span
                    style={{
                      fontSize: "12px",
                      color: "#111827",
                      fontWeight: 600,
                    }}
                  >
                    {phase.label}
                  </span>
                  <span
                    style={{
                      fontSize: "11px",
                      color:
                        phase.status === "DONE"
                          ? "#2E7D32"
                          : phase.status === "IN_PROGRESS"
                            ? "#1976D2"
                            : "#6B7280",
                      fontWeight: "600",
                    }}
                  >
                    {phase.status === "DONE"
                      ? "✓ Completed"
                      : phase.status === "IN_PROGRESS"
                        ? `${phase.progress?.toFixed(0)}%`
                        : "Pending"}
                  </span>
                </div>
                <div
                  style={{
                    height: "8px",
                    borderRadius: "4px",
                    background: "#F3F4F6",
                    overflow: "hidden",
                  }}
                >
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: `${Math.min(phase.progress || 0, 100)}%`,
                    }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    style={{ height: "100%", background: phase.color }}
                  />
                </div>
                {phase.start && (
                  <div
                    style={{
                      fontSize: "10px",
                      color: "#6B7280",
                      marginTop: "6px",
                      fontWeight: 500,
                    }}
                  >
                    {phase.start}
                    {phase.end ? ` → ${phase.end}` : ""}
                    {phase.duration_days ? ` (${phase.duration_days}d)` : ""}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CleanCard>
      </div>

      <div
        style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: "16px" }}
      >
        <CleanCard style={{ padding: "24px" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: "16px",
              marginBottom: "18px",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: "13px",
                  color: "#374151",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Milestone Ledger
              </div>
              <div
                style={{
                  marginTop: "8px",
                  fontSize: "28px",
                  fontWeight: 700,
                  color: "#111827",
                  lineHeight: 1,
                }}
              >
                {completedMilestones}/{milestones.length}
              </div>
              <div
                style={{
                  marginTop: "6px",
                  fontSize: "12px",
                  color: "#6B7280",
                  fontWeight: 500,
                }}
              >
                lifecycle milestones completed
              </div>
            </div>
            <div style={{ minWidth: "260px", flex: 1 }}>
              <div
                style={{
                  height: "10px",
                  borderRadius: "999px",
                  background: "#F3F4F6",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${Math.min(milestoneCompletionPct, 100)}%`,
                    background:
                      "linear-gradient(90deg, #111827 0%, #00C805 100%)",
                    transition: "width 0.8s ease",
                  }}
                />
              </div>
              <div
                style={{
                  display: "flex",
                  gap: "10px",
                  flexWrap: "wrap",
                  marginTop: "12px",
                }}
              >
                {[
                  {
                    label: `${completedMilestones} Completed`,
                    bg: "#111827",
                    color: "#FFFFFF",
                  },
                  {
                    label: `${scheduledMilestones} Scheduled`,
                    bg: "#EEF4FF",
                    color: "#0F62FE",
                  },
                  {
                    label: `${overdueMilestones} Overdue`,
                    bg: "#FFF4E8",
                    color: "#B45309",
                  },
                  {
                    label: `${pendingMilestones} Pending`,
                    bg: "#F3F4F6",
                    color: "#6B7280",
                  },
                ].map((item) => (
                  <span
                    key={item.label}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      padding: "6px 10px",
                      borderRadius: "999px",
                      background: item.bg,
                      color: item.color,
                      fontSize: "11px",
                      fontWeight: 700,
                      letterSpacing: "0.03em",
                      textTransform: "uppercase",
                    }}
                  >
                    {item.label}
                  </span>
                ))}
              </div>
            </div>
          </div>
          {milestones.length === 0 ? (
            <div
              style={{
                color: "#6B7280",
                fontSize: "13px",
                textAlign: "center",
                padding: "20px",
              }}
            >
              No milestones recorded
            </div>
          ) : (
            <div style={{ position: "relative", paddingLeft: "24px" }}>
              <div
                style={{
                  position: "absolute",
                  left: "8px",
                  top: "4px",
                  bottom: "4px",
                  width: "2px",
                  background: "#E5E7EB",
                }}
              />
              {milestones.map((m) => {
                const statusStyle =
                  MILESTONE_STATUS_STYLE[m.status] ||
                  MILESTONE_STATUS_STYLE.PENDING;
                return (
                  <div
                    key={`${m.sequence}-${m.base_label || m.label}`}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "72px 110px 1fr auto",
                      alignItems: "center",
                      gap: "14px",
                      marginBottom: "16px",
                      position: "relative",
                      padding: "14px 16px",
                      borderRadius: "14px",
                      background: statusStyle.cardBg,
                      border: `1px solid ${statusStyle.border}`,
                    }}
                  >
                    {/* Timeline Dot */}
                    <div
                      style={{
                        position: "absolute",
                        left: "-23px",
                        width: "11px",
                        height: "11px",
                        borderRadius: "50%",
                        background: statusStyle.dot,
                        border:
                          m.status === "PENDING"
                            ? "2px solid #FFFFFF"
                            : "2px solid rgba(255,255,255,0.9)",
                        boxShadow: "0 0 0 1px #E5E7EB",
                      }}
                    />
                    <div
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        letterSpacing: "0.05em",
                        textTransform: "uppercase",
                        color:
                          m.status === "COMPLETED"
                            ? "rgba(255,255,255,0.7)"
                            : "#6B7280",
                      }}
                    >
                      M{String(m.sequence).padStart(2, "0")}
                    </div>
                    {/* Date */}
                    <div
                      style={{
                        fontSize: "12px",
                        color: statusStyle.subtext,
                        fontFamily: '"SF Mono", monospace',
                        fontWeight: 600,
                      }}
                    >
                      {m.date || "Not recorded"}
                    </div>
                    {/* Label */}
                    <div
                      style={{
                        fontSize: "13px",
                        color: statusStyle.text,
                        fontWeight: 600,
                      }}
                    >
                      <div>{m.label}</div>
                      {m.base_label && m.base_label !== m.label && (
                        <div
                          style={{
                            marginTop: "4px",
                            fontSize: "11px",
                            color: statusStyle.subtext,
                            fontWeight: 500,
                          }}
                        >
                          Actual milestone: {m.base_label}
                        </div>
                      )}
                    </div>
                    <div
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        padding: "7px 10px",
                        minWidth: "92px",
                        borderRadius: "999px",
                        background: statusStyle.badgeBg,
                        color: statusStyle.badgeText,
                        fontSize: "11px",
                        fontWeight: 700,
                        letterSpacing: "0.04em",
                        textTransform: "uppercase",
                      }}
                    >
                      {statusStyle.label}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CleanCard>

        <CleanCard style={{ padding: "24px" }}>
          <div
            style={{
              fontSize: "13px",
              color: "#374151",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: "20px",
            }}
          >
            Risk Model
          </div>
          <div style={{ textAlign: "center", marginBottom: "24px" }}>
            <div
              style={{
                fontSize: "36px",
                fontWeight: 700,
                color: tierColor,
                lineHeight: 1,
              }}
            >
              {risk?.score}
            </div>
            <div
              style={{
                fontSize: "11px",
                color: "#6B7280",
                fontWeight: 600,
                textTransform: "uppercase",
                marginTop: "4px",
              }}
            >
              Probability Of Missing Target
            </div>
          </div>

          {risk?.components &&
            Object.entries(risk.components)
              .filter(([, value]) => (value as number) > 0)
              .map(([key, value]) => (
                <div key={key} style={{ marginBottom: "16px" }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "4px",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "12px",
                        color: "#4B5563",
                        fontWeight: 500,
                      }}
                    >
                      {RISK_COMPONENT_LABELS[key] || key.replace(/_/g, " ")}
                    </span>
                    <span
                      style={{
                        fontSize: "12px",
                        color: "#111827",
                        fontWeight: "600",
                      }}
                    >
                      {Math.round(value as number)} pts
                    </span>
                  </div>
                  <div
                    style={{
                      height: "4px",
                      borderRadius: "2px",
                      background: "#F3F4F6",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        borderRadius: "2px",
                        width: `${Math.min(value as number, 100)}%`,
                        background:
                          (value as number) > 20
                            ? "#D32F2F"
                            : (value as number) > 10
                              ? "#ED6C02"
                              : "#2E7D32",
                      }}
                    />
                  </div>
                </div>
              ))}

          {risk?.drivers?.length > 0 && (
            <div
              style={{
                marginTop: "24px",
                borderTop: "1px solid #E5E7EB",
                paddingTop: "16px",
              }}
            >
              <div
                style={{
                  fontSize: "11px",
                  color: "#6B7280",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  marginBottom: "12px",
                }}
              >
                Key Drivers
              </div>
              {risk.drivers.map((d, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "8px",
                    marginBottom: "8px",
                  }}
                >
                  <span
                    style={{
                      fontSize: "14px",
                      color: d.direction === "positive" ? "#2E7D32" : "#D32F2F",
                    }}
                  >
                    {d.direction === "positive" ? "●" : "●"}
                  </span>
                  <span
                    style={{
                      fontSize: "12px",
                      color: "#374151",
                      fontWeight: 500,
                    }}
                  >
                    {d.factor}
                  </span>
                  {d.description && (
                    <span
                      style={{
                        fontSize: "11px",
                        color: "#6B7280",
                        fontWeight: 400,
                      }}
                    >
                      {d.description}
                    </span>
                  )}
                  <span
                    style={{
                      fontSize: "12px",
                      color: "#111827",
                      fontWeight: 600,
                      marginLeft: "auto",
                    }}
                  >
                    {d.impact}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CleanCard>
      </div>

      {/* ─────────────────────────────────────────────────────────────────
          CAUSAL ROOT CAUSE & INTERVENTION SIMULATOR
          ───────────────────────────────────────────────────────────────── */}
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}
      >
        <CleanCard style={{ padding: "24px" }}>
          <div
            style={{
              fontSize: "13px",
              color: "#374151",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: "20px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#6366F1"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M18 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"></path>
              <path d="M6 8a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"></path>
              <path d="M18 15a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"></path>
              <path d="M8.5 11.5 15.5 6.5"></path>
              <path d="M8.5 13.5 15.5 18.5"></path>
              <path d="M6 14v4"></path>
              <path d="M18 9v4"></path>
            </svg>
            Causal Root Cause Vector
          </div>
          {causal?.baseline && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                gap: "10px",
                marginBottom: "18px",
              }}
            >
              {[
                {
                  label: "Baseline Completion",
                  value: causal.baseline.expected_completion_date || "N/A",
                },
                {
                  label: "Baseline Pace",
                  value:
                    causal.baseline.weekly_momentum_pct != null
                      ? `${causal.baseline.weekly_momentum_pct} pts/week`
                      : "N/A",
                },
                {
                  label: "Benchmark Scope",
                  value: causal.baseline.benchmark_scope || "N/A",
                },
              ].map((item) => (
                <div
                  key={item.label}
                  style={{
                    background: "#F9FAFB",
                    border: "1px solid #E5E7EB",
                    borderRadius: "8px",
                    padding: "10px 12px",
                  }}
                >
                  <div
                    style={{
                      fontSize: "10px",
                      color: "#6B7280",
                      textTransform: "uppercase",
                      fontWeight: 600,
                      letterSpacing: "0.05em",
                    }}
                  >
                    {item.label}
                  </div>
                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: "#111827",
                      marginTop: "4px",
                    }}
                  >
                    {item.value}
                  </div>
                </div>
              ))}
            </div>
          )}
          {causal?.root_causes && causal.root_causes.length > 0 ? (
            <div
              style={{ display: "flex", flexDirection: "column", gap: "16px" }}
            >
              {causal.root_causes.map((rc, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    gap: "16px",
                    alignItems: "center",
                    padding: "12px",
                    background: "#F9FAFB",
                    borderRadius: "6px",
                    borderLeft: "4px solid #D32F2F",
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        fontSize: "14px",
                        fontWeight: 600,
                        color: "#111827",
                      }}
                    >
                      {rc.factor}
                    </div>
                    <div
                      style={{
                        fontSize: "12px",
                        color: "#6B7280",
                        marginTop: "2px",
                      }}
                    >
                      {rc.description}
                    </div>
                    {rc.support_cases ? (
                      <div
                        style={{
                          fontSize: "11px",
                          color: "#9CA3AF",
                          marginTop: "8px",
                          fontWeight: 500,
                        }}
                      >
                        Historical support: {rc.support_cases} comparable cases
                      </div>
                    ) : null}
                  </div>
                  <div
                    style={{
                      textAlign: "center",
                      paddingLeft: "16px",
                      borderLeft: "1px solid #E5E7EB",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "20px",
                        fontWeight: 700,
                        color: "#D32F2F",
                      }}
                    >
                      +{rc.delay_days}
                    </div>
                    <div
                      style={{
                        fontSize: "10px",
                        color: "#6B7280",
                        textTransform: "uppercase",
                        fontWeight: 600,
                      }}
                    >
                      Days Delay
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div
              style={{
                padding: "24px",
                textAlign: "center",
                color: "#6B7280",
                fontSize: "13px",
                background: "#F9FAFB",
                borderRadius: "6px",
              }}
            >
              No scenario-attributable recovery drivers were detected for this
              well.
            </div>
          )}
        </CleanCard>

        <CleanCard
          style={{ padding: "24px", display: "flex", flexDirection: "column" }}
        >
          <div
            style={{
              fontSize: "13px",
              color: "#111827",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: "20px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#059669"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
              <line x1="8" y1="21" x2="16" y2="21"></line>
              <line x1="12" y1="17" x2="12" y2="21"></line>
              <path d="M11 7h4M11 11h4M7 7v4"></path>
            </svg>
            Counterfactual Simulator
          </div>
          {causal?.methodology && (
            <div
              style={{
                fontSize: "12px",
                color: "#6B7280",
                marginBottom: "16px",
                lineHeight: 1.5,
              }}
            >
              Uses live SSMS comparable cases plus CPU ML uplift models on
              governed execution levers.
            </div>
          )}

          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            {causal?.baseline && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                  gap: "10px",
                }}
              >
                <div
                  style={{
                    background: "#F9FAFB",
                    border: "1px solid #E5E7EB",
                    borderRadius: "8px",
                    padding: "10px 12px",
                  }}
                >
                  <div
                    style={{
                      fontSize: "10px",
                      color: "#6B7280",
                      textTransform: "uppercase",
                      fontWeight: 600,
                      letterSpacing: "0.05em",
                    }}
                  >
                    Baseline Completion
                  </div>
                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: "#111827",
                      marginTop: "4px",
                    }}
                  >
                    {causal.baseline.expected_completion_date || "N/A"}
                  </div>
                </div>
                <div
                  style={{
                    background: "#F9FAFB",
                    border: "1px solid #E5E7EB",
                    borderRadius: "8px",
                    padding: "10px 12px",
                  }}
                >
                  <div
                    style={{
                      fontSize: "10px",
                      color: "#6B7280",
                      textTransform: "uppercase",
                      fontWeight: 600,
                      letterSpacing: "0.05em",
                    }}
                  >
                    Comparable Cases
                  </div>
                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: "#111827",
                      marginTop: "4px",
                    }}
                  >
                    {causal.baseline.support_cases ?? 0}
                  </div>
                </div>
              </div>
            )}
            <div style={{ display: "flex", gap: "12px" }}>
              <select
                value={simParams.intervention_type}
                onChange={(e) => {
                  const nextAction = scenarioActions.find(
                    (action) => action.id === e.target.value,
                  );
                  setSimParams({
                    intervention_type: e.target.value,
                    intervention_value:
                      nextAction?.default_value ||
                      nextAction?.options?.[0]?.value ||
                      "",
                  });
                }}
                style={{
                  flex: 1,
                  padding: "10px",
                  borderRadius: "6px",
                  border: "1px solid #D1D5DB",
                  fontSize: "13px",
                  background: "#FFFFFF",
                  color: "#374151",
                  outline: "none",
                }}
              >
                {scenarioActions.length > 0 ? (
                  scenarioActions.map((action) => (
                    <option key={action.id} value={action.id}>
                      {action.label}
                    </option>
                  ))
                ) : (
                  <option value="">No governed scenarios available</option>
                )}
              </select>
              <select
                value={simParams.intervention_value}
                onChange={(e) =>
                  setSimParams({
                    ...simParams,
                    intervention_value: e.target.value,
                  })
                }
                style={{
                  flex: 1,
                  padding: "10px",
                  borderRadius: "6px",
                  border: "1px solid #D1D5DB",
                  fontSize: "13px",
                  background: "#FFFFFF",
                  color: "#374151",
                  outline: "none",
                }}
              >
                {selectedAction?.options?.length ? (
                  selectedAction.options.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))
                ) : (
                  <option value="">No options available</option>
                )}
              </select>
            </div>
            {selectedAction && (
              <div
                style={{
                  background: "#F9FAFB",
                  border: "1px solid #E5E7EB",
                  borderRadius: "8px",
                  padding: "12px 14px",
                }}
              >
                <div
                  style={{
                    fontSize: "13px",
                    fontWeight: 600,
                    color: "#111827",
                  }}
                >
                  {selectedAction.label}
                </div>
                <div
                  style={{
                    fontSize: "12px",
                    color: "#6B7280",
                    marginTop: "4px",
                    lineHeight: 1.5,
                  }}
                >
                  {selectedAction.description}
                </div>
              </div>
            )}

            <button
              onClick={runSimulation}
              disabled={simLoading || !simParams.intervention_type}
              style={{
                padding: "12px",
                background: "#111827",
                color: "#FFFFFF",
                border: "none",
                borderRadius: "6px",
                fontWeight: 600,
                fontSize: "13px",
                cursor: "pointer",
                transition: "background 0.2s ease",
                opacity: simLoading ? 0.7 : 1,
              }}
              onMouseOver={(e) =>
                !simLoading && (e.currentTarget.style.background = "#374151")
              }
              onMouseOut={(e) =>
                !simLoading && (e.currentTarget.style.background = "#111827")
              }
            >
              {simLoading ? "Running Governed Scenario..." : "Run Scenario"}
            </button>

            {simResult && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  padding: "16px",
                  background: "#ECFDF5",
                  border: "1px solid #A7F3D0",
                  borderRadius: "6px",
                  marginTop: "auto",
                }}
              >
                <div
                  style={{
                    fontSize: "12px",
                    color: "#065F46",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    marginBottom: "8px",
                  }}
                >
                  Simulation Result
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: "12px",
                    marginBottom: "12px",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "13px", color: "#047857" }}>
                      Expected Recovery
                    </div>
                    <div
                      style={{
                        fontSize: "24px",
                        fontWeight: 700,
                        color: "#059669",
                      }}
                    >
                      {simResult.effect_days} Days
                    </div>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "#047857",
                        marginTop: "4px",
                      }}
                    >
                      Conservative {simResult.low_case_days_saved ?? 0} · Upside{" "}
                      {simResult.high_case_days_saved ?? 0}
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "#047857",
                        opacity: 0.8,
                      }}
                    >
                      Scenario Completion
                    </div>
                    <div
                      style={{
                        fontSize: "14px",
                        fontWeight: 600,
                        color: "#065F46",
                        fontFamily: '"SF Mono", monospace',
                      }}
                    >
                      {simResult.counterfactual_completion_date}
                    </div>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "#047857",
                        marginTop: "4px",
                      }}
                    >
                      Baseline {simResult.factual_completion_date}
                    </div>
                  </div>
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: "10px",
                    marginBottom: "10px",
                  }}
                >
                  <div style={{ fontSize: "12px", color: "#065F46" }}>
                    Pace: {simResult.baseline_weekly_momentum_pct} {"->"}{" "}
                    {simResult.scenario_weekly_momentum_pct} pts/week
                  </div>
                  <div
                    style={{
                      fontSize: "12px",
                      color: "#065F46",
                      textAlign: "right",
                    }}
                  >
                    Support: {simResult.support_cases ?? 0} cases
                  </div>
                </div>
                {simResult.assumption_note && (
                  <div
                    style={{
                      fontSize: "12px",
                      color: "#065F46",
                      lineHeight: 1.5,
                    }}
                  >
                    {simResult.assumption_note}
                  </div>
                )}
              </motion.div>
            )}
          </div>
        </CleanCard>
      </div>

      {/* Key Dates Summary */}
      <CleanCard style={{ padding: "24px" }}>
        <div
          style={{
            fontSize: "13px",
            color: "#374151",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            marginBottom: "16px",
          }}
        >
          Milestone Matrix
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
            gap: "1px",
            background: "#E5E7EB",
            border: "1px solid #E5E7EB",
            borderRadius: "6px",
            overflow: "hidden",
          }}
        >
          {[
            { label: "FLAF Issue", value: cs.flaf_issue },
            { label: "Loc Prep Start", value: cs.actual_start },
            { label: "Eng. Start", value: cs.engg_start },
            { label: "Eng. Finish", value: cs.engg_finish },
            { label: "Const. Start", value: cs.const_start },
            { label: "Const. Finish", value: cs.const_finish },
            { label: "Rig On", value: cs.rig_on },
            { label: "Rig Off", value: cs.rig_off },
            { label: "Comm. Start", value: cs.comm_start },
            { label: "Comm. Finish", value: cs.comm_finish },
          ].map((d, i) => (
            <div
              key={i}
              style={{ padding: "12px 16px", background: "#FFFFFF" }}
            >
              <div
                style={{
                  fontSize: "10px",
                  color: "#6B7280",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  fontWeight: 600,
                }}
              >
                {d.label}
              </div>
              <div
                style={{
                  fontSize: "13px",
                  color: d.value ? "#111827" : "#9CA3AF",
                  fontWeight: d.value ? "600" : "400",
                  marginTop: "4px",
                  fontFamily: d.value ? '"SF Mono", monospace' : "inherit",
                }}
              >
                {d.value || "N/A"}
              </div>
            </div>
          ))}
        </div>
      </CleanCard>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

export default function PredictiveStudio() {
  const [wells, setWells] = useState<WellSummary[]>([]);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [selectedWellId, setSelectedWellId] = useState<string | null>(null);
  const [wellDetail, setWellDetail] = useState<WellDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterTier, setFilterTier] = useState<string>("ALL");

  useEffect(() => {
    fetchWells();
  }, []);

  const fetchWells = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/forecast?action=wells");
      const data = await res.json();
      if (data.wells) setWells(data.wells);
      if (data.portfolio) setPortfolio(data.portfolio);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  const selectWell = async (wellId: string) => {
    setSelectedWellId(wellId);
    setDetailLoading(true);
    try {
      const res = await fetch(
        `/api/forecast?action=well&id=${encodeURIComponent(wellId)}`,
      );
      const data = await res.json();
      if (data.data) setWellDetail(data.data);
    } catch (e: any) {
      setError(e.message);
    }
    setDetailLoading(false);
  };

  const filteredWells = useMemo(() => {
    let filtered = wells;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (w) =>
          w.well_name?.toLowerCase().includes(term) ||
          w.pdo_well_id?.toLowerCase().includes(term) ||
          w.rig_no?.toLowerCase().includes(term),
      );
    }
    if (filterTier !== "ALL") {
      filtered = filtered.filter((w) => w.risk_tier === filterTier);
    }
    return filtered;
  }, [wells, searchTerm, filterTier]);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100%",
          color: "#6B7280",
          background: "#F8F9FA",
        }}
      >
        <span style={{ fontSize: "14px", fontWeight: 500 }}>
          Initializing Forecast Engine...
        </span>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "#F8F9FA",
      }}
    >
      {/* Header bar */}
      {!selectedWellId && (
        <div
          style={{
            padding: "16px 24px",
            background: "#FFFFFF",
            borderBottom: "1px solid #E5E7EB",
            display: "flex",
            gap: "16px",
            alignItems: "center",
          }}
        >
          <div style={{ flex: 1, position: "relative" }}>
            <input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by ID, Name, or Rig..."
              style={{
                width: "100%",
                padding: "8px 16px",
                borderRadius: "6px",
                border: "1px solid #D1D5DB",
                background: "#FFFFFF",
                fontSize: "13px",
                color: "#111827",
                outline: "none",
              }}
              onFocus={(e) =>
                Object.assign(e.target.style, {
                  borderColor: "#1976D2",
                  boxShadow: "0 0 0 2px rgba(25,118,210,0.1)",
                })
              }
              onBlur={(e) =>
                Object.assign(e.target.style, {
                  borderColor: "#D1D5DB",
                  boxShadow: "none",
                })
              }
            />
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            {["ALL", "CRITICAL", "HIGH_RISK", "WATCH", "HEALTHY"].map(
              (tier) => (
                <button
                  key={tier}
                  onClick={() => setFilterTier(tier)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: "4px",
                    fontSize: "11px",
                    fontWeight: 600,
                    border: "1px solid",
                    borderColor:
                      filterTier === tier
                        ? tier === "ALL"
                          ? "#1976D2"
                          : TIER_COLORS[tier]
                        : "#E5E7EB",
                    background:
                      filterTier === tier
                        ? tier === "ALL"
                          ? "#E3F2FD"
                          : `${TIER_COLORS[tier]}15`
                        : "#FFFFFF",
                    color:
                      filterTier === tier
                        ? tier === "ALL"
                          ? "#1976D2"
                          : TIER_COLORS[tier]
                        : "#6B7280",
                    cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                >
                  {tier.replace("_", " ")}
                </button>
              ),
            )}
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        <AnimatePresence mode="wait">
          {selectedWellId && wellDetail ? (
            <motion.div
              key="detail"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <WellDeepDive
                detail={wellDetail}
                onBack={() => {
                  setSelectedWellId(null);
                  setWellDetail(null);
                }}
              />
            </motion.div>
          ) : detailLoading ? (
            <motion.div
              key="loading"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "400px",
                color: "#6B7280",
              }}
            >
              <span style={{ fontSize: "14px", fontWeight: 500 }}>
                Fetching well intelligence...
              </span>
            </motion.div>
          ) : portfolio ? (
            <motion.div
              key="portfolio"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              style={{ height: "100%" }}
            >
              <PortfolioDashboard
                portfolio={portfolio}
                wells={filteredWells}
                onSelectWell={selectWell}
              />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  );
}
