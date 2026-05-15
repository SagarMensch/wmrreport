import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

export const runtime = "nodejs";

type TrainingManifest = {
  tier_thresholds?: {
    watch?: number;
    high_risk?: number;
    critical?: number;
  };
  risk_metrics?: {
    auc?: number;
    brier?: number;
  };
  survival_metrics?: {
    c_index?: number;
    cox_features_used?: string[];
  };
};

type AgMetrics = {
  rmse?: number;
  mae?: number;
  r2?: number;
  mape_valid?: number;
};

type Snapshot = {
  wellCount: number;
  tierCounts: Record<string, number>;
  thresholds: {
    watch: number;
    highRisk: number;
    critical: number;
  };
  topDrivers: string[];
  topSurvivalDrivers: string[];
  metrics: {
    rmse: number;
    mae: number;
    r2: number;
    mape: number;
    auc: number;
    brier: number;
    cIndex: number;
  };
};

type EnvMap = Record<string, string>;

const TERM_ALIASES: Record<string, string> = {
  portfolio: "Portfolio",
  critical: "Critical",
  "at risk": "At Risk",
  watch: "Watch",
  healthy: "Healthy",
  "risk distribution": "Risk Distribution",
  "progress distribution": "Progress Distribution",
  "rig profile": "Rig Profile",
  "rig capability radar": "Rig Profile",
  "rig 3d scatter": "Rig Profile",
  "rig fleet performance": "Rig Fleet Performance",
  "predictive drivers": "Predictive Drivers",
  "feature importance": "Predictive Drivers",
  "driver distribution": "Driver Distribution",
  "shap analysis": "Driver Distribution",
  "completion probability": "Completion Probability",
  "timeline forecast": "Timeline Forecast",
  "model accuracy": "Model Accuracy",
  "model diagnostics": "Model Accuracy",
  rmse: "RMSE",
  mae: "MAE",
  r2: "R2",
  mape: "MAPE",
  auc: "AUC",
  brier: "Brier",
  "c-index": "C-Index",
  "completion drivers": "Completion Drivers",
  "completion driver curve": "Completion Drivers",
};

const responseCache = new Map<string, string>();
let snapshotCache: { at: number; value: Snapshot } | null = null;

function normalizeTerm(term: string): string {
  return TERM_ALIASES[term.trim().toLowerCase()] || term.trim();
}

function stripQuotes(value: string) {
  return value.replace(/^"(.*)"$/, "$1").trim();
}

function humanizeToken(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\bwmr\b/gi, "WMR")
    .replace(/\bkpi\b/gi, "KPI")
    .replace(/\bloc\b/gi, "location")
    .replace(/\bconst\b/gi, "construction")
    .replace(/\bover all\b/gi, "overall")
    .replace(/\s+/g, " ")
    .trim();
}

function parseCsvLine(line: string) {
  const values: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    const next = line[i + 1];

    if (char === '"' && inQuotes && next === '"') {
      current += '"';
      i += 1;
      continue;
    }

    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (char === "," && !inQuotes) {
      values.push(stripQuotes(current));
      current = "";
      continue;
    }

    current += char;
  }

  values.push(stripQuotes(current));
  return values;
}

function parseCsv(text: string) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) return [] as Record<string, string>[];

  const headers = parseCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = parseCsvLine(line);
    const row: Record<string, string> = {};
    headers.forEach((header, index) => {
      row[header] = cells[index] ?? "";
    });
    return row;
  });
}

function parseEnv(content: string) {
  const env: EnvMap = {};
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    const value = line.slice(eq + 1).trim();
    env[key] = value;
  }
  return env;
}

async function loadEnv() {
  const candidates = [
    path.join(process.cwd(), ".env.local"),
    path.join(process.cwd(), ".env"),
    path.join(process.cwd(), "..", ".env"),
  ];

  const merged: EnvMap = {};
  for (const candidate of candidates) {
    try {
      const content = await fs.readFile(candidate, "utf8");
      Object.assign(merged, parseEnv(content));
    } catch {
      // Ignore missing env files.
    }
  }

  return merged;
}

function safeNumber(value: unknown) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

function formatCompact(value: number, digits = 1) {
  return safeNumber(value).toFixed(digits);
}

async function loadSnapshot() {
  if (snapshotCache && Date.now() - snapshotCache.at < 60_000) {
    return snapshotCache.value;
  }

  const baseDir = path.join(process.cwd(), "public", "wmr_results");
  const [manifestText, metricsText, driversText, riskScoresText] =
    await Promise.all([
      fs.readFile(path.join(baseDir, "training_manifest.json"), "utf8"),
      fs.readFile(path.join(baseDir, "ag_metrics.json"), "utf8"),
      fs.readFile(path.join(baseDir, "feature_importance.csv"), "utf8"),
      fs.readFile(path.join(baseDir, "risk_scores.csv"), "utf8"),
    ]);

  const manifest = JSON.parse(manifestText) as TrainingManifest;
  const metrics = JSON.parse(metricsText) as AgMetrics;
  const driverRows = parseCsv(driversText);
  const riskRows = parseCsv(riskScoresText);

  const tierCounts = riskRows.reduce<Record<string, number>>((acc, row) => {
    const tier = row.risk_tier || "UNKNOWN";
    acc[tier] = (acc[tier] || 0) + 1;
    return acc;
  }, {});

  const topDrivers = driverRows
    .slice(0, 3)
    .map((row) => humanizeToken(row.feature || ""))
    .filter(Boolean);

  const snapshot: Snapshot = {
    wellCount: riskRows.length,
    tierCounts,
    thresholds: {
      watch: safeNumber(manifest.tier_thresholds?.watch),
      highRisk: safeNumber(manifest.tier_thresholds?.high_risk),
      critical: safeNumber(manifest.tier_thresholds?.critical),
    },
    topDrivers,
    topSurvivalDrivers: (manifest.survival_metrics?.cox_features_used || [])
      .slice(0, 4)
      .map((feature) => humanizeToken(feature)),
    metrics: {
      rmse: safeNumber(metrics.rmse),
      mae: safeNumber(metrics.mae),
      r2: safeNumber(metrics.r2),
      mape: safeNumber(metrics.mape_valid),
      auc: safeNumber(manifest.risk_metrics?.auc),
      brier: safeNumber(manifest.risk_metrics?.brier),
      cIndex: safeNumber(manifest.survival_metrics?.c_index),
    },
  };

  snapshotCache = { at: Date.now(), value: snapshot };
  return snapshot;
}

function buildFallback(term: string, context: string | undefined, snapshot: Snapshot) {
  const counts = snapshot.tierCounts;
  const total = snapshot.wellCount;
  const topDrivers = snapshot.topDrivers.join(", ");
  const topSurvivalDrivers = snapshot.topSurvivalDrivers.join(", ");

  switch (term) {
    case "Portfolio":
      return `This card shows the current portfolio size in the live scoring package. It is the total number of wells currently included in the Decision Studio view, which is ${total}.`;
    case "Critical":
      return `This card counts wells above the critical threshold in the live risk stack. The current critical bucket is ${counts.CRITICAL || 0} wells, based on a risk score at or above ${formatCompact(snapshot.thresholds.critical, 1)}.`;
    case "At Risk":
      return `This card counts the high-risk tier, which sits below critical but above watch. The current at-risk bucket is ${counts.HIGH_RISK || 0} wells, using the live threshold band from ${formatCompact(snapshot.thresholds.highRisk, 1)} to ${formatCompact(snapshot.thresholds.critical, 1)}.`;
    case "Watch":
      return `This card counts wells that are showing pressure but are not yet in the high-risk band. The current watch bucket is ${counts.WATCH || 0} wells, starting at a score of ${formatCompact(snapshot.thresholds.watch, 1)}.`;
    case "Healthy":
      return `This card counts wells that remain below the watch threshold in the current scoring package. The current healthy bucket is ${counts.HEALTHY || 0} wells.`;
    case "Risk Distribution":
      return `This chart shows the current portfolio split across the live risk tiers: critical ${counts.CRITICAL || 0}, high risk ${counts.HIGH_RISK || 0}, watch ${counts.WATCH || 0}, and healthy ${counts.HEALTHY || 0}. It is a live portfolio mix view, and clicking a segment filters the well list to that tier.`;
    case "Progress Distribution":
      return `This chart groups the current ${total} wells by live progress percentage. It shows where the portfolio is concentrated today, so it is a current-state distribution, not a forecast range or scenario fan.`;
    case "Rig Profile":
      return `This view compares rigs on operational shape rather than on one headline score. In radar mode it contrasts progress and derived efficiency by rig; in 3D mode it positions rigs against the portfolio using the same live scored package.`;
    case "Rig Fleet Performance":
      return `This chart benchmarks rig performance across the active portfolio. It helps compare which rigs are carrying more wells, more progress, or more risk concentration at the same time.`;
    case "Predictive Drivers":
      return `This ranking shows which inputs move the progress model the most in the current live package. The strongest drivers right now are ${topDrivers}, and the bars show relative model influence rather than causation or action priority.`;
    case "Driver Distribution":
      return `This beeswarm shows how the strongest drivers push predictions up or down across wells. Points to the right increase expected progress, points to the left reduce it, and the spread shows how uneven that effect is across the portfolio.`;
    case "Completion Probability":
      return `This survival chart tracks the probability that wells are still incomplete as weeks pass. A faster drop means faster completion, and the current survival model has a C-index of ${formatCompact(snapshot.metrics.cIndex, 3)}.`;
    case "Timeline Forecast":
      return `This chart shows predicted completion windows for the selected near-term wells. Each line centers on the model’s median completion date, and the horizontal band shows the 80% timing interval around that estimate.`;
    case "Model Accuracy":
      return `This panel summarizes validation accuracy for the live Decision Studio package. Current metrics are R2 ${formatCompact(snapshot.metrics.r2, 4)}, RMSE ${formatCompact(snapshot.metrics.rmse, 4)}, MAE ${formatCompact(snapshot.metrics.mae, 4)}, MAPE ${formatCompact(snapshot.metrics.mape, 1)}%, AUC ${formatCompact(snapshot.metrics.auc, 4)}, Brier ${formatCompact(snapshot.metrics.brier, 4)}, and C-index ${formatCompact(snapshot.metrics.cIndex, 4)}.`;
    case "RMSE":
      return `RMSE is the typical size of the progress prediction error on the validation set, with larger misses weighted more heavily. Lower is better, and the current live package is at ${formatCompact(snapshot.metrics.rmse, 4)}.`;
    case "MAE":
      return `MAE is the average absolute prediction error on the validation set. Lower is better, and the current live package is at ${formatCompact(snapshot.metrics.mae, 4)}.`;
    case "R2":
      return `R2 measures how much of the validation variation in progress the model explains. Higher is better, and the current live package is at ${formatCompact(snapshot.metrics.r2, 4)}.`;
    case "MAPE":
      return `MAPE measures the average percentage error on the validation set. Lower is better, and the current live package is at ${formatCompact(snapshot.metrics.mape, 1)}%.`;
    case "AUC":
      return `AUC measures how well the risk model ranks wells that will miss target ahead of wells that will not. Higher is better, and the current live package is at ${formatCompact(snapshot.metrics.auc, 4)}.`;
    case "Brier":
      return `Brier score measures probability calibration error for the risk model. Lower is better, and the current live package is at ${formatCompact(snapshot.metrics.brier, 4)}.`;
    case "C-Index":
      return `C-index measures how well the survival model orders wells by time to completion. Higher is better, and the current live package is at ${formatCompact(snapshot.metrics.cIndex, 4)}.`;
    case "Completion Drivers":
      return `This hazard-ratio chart shows which variables are associated with faster or slower completion in the survival model. Values on the accelerating side indicate faster expected completion, values on the delaying side indicate slower completion, and the current retained covariates are ${topSurvivalDrivers}.`;
    default:
      return context
        ? `Explanation for ${term} in the context of: ${context}.`
        : `Advanced operational metric: ${term}, analyzing Al Tasnim project outcomes.`;
  }
}

function buildGrounding(term: string, context: string | undefined, snapshot: Snapshot) {
  const facts = [
    `Visible term: ${term}`,
    context ? `Visible subtitle/context: ${context}` : null,
    `Portfolio wells in current package: ${snapshot.wellCount}`,
    `Tier counts: CRITICAL ${snapshot.tierCounts.CRITICAL || 0}, HIGH_RISK ${snapshot.tierCounts.HIGH_RISK || 0}, WATCH ${snapshot.tierCounts.WATCH || 0}, HEALTHY ${snapshot.tierCounts.HEALTHY || 0}`,
    `Thresholds: watch ${formatCompact(snapshot.thresholds.watch, 1)}, high risk ${formatCompact(snapshot.thresholds.highRisk, 1)}, critical ${formatCompact(snapshot.thresholds.critical, 1)}`,
    `Top progress drivers: ${snapshot.topDrivers.join(", ")}`,
    `Survival covariates used: ${snapshot.topSurvivalDrivers.join(", ")}`,
    `Validation metrics: R2 ${formatCompact(snapshot.metrics.r2, 4)}, RMSE ${formatCompact(snapshot.metrics.rmse, 4)}, MAE ${formatCompact(snapshot.metrics.mae, 4)}, MAPE ${formatCompact(snapshot.metrics.mape, 1)}%, AUC ${formatCompact(snapshot.metrics.auc, 4)}, Brier ${formatCompact(snapshot.metrics.brier, 4)}, C-index ${formatCompact(snapshot.metrics.cIndex, 4)}`,
    `Required explanation style for ${term}: ${buildFallback(term, context, snapshot)}`,
  ].filter(Boolean);

  return facts.join("\n");
}

async function callGroq(term: string, context: string | undefined, snapshot: Snapshot) {
  const env = await loadEnv();
  const apiKey =
    process.env.GROQ_API_KEY_2 ||
    process.env.GROQ_API_KEY ||
    env.GROQ_API_KEY_2 ||
    env.GROQ_API_KEY;

  if (!apiKey) {
    return buildFallback(term, context, snapshot);
  }

  const rawModel =
    process.env.GROQ_EXPLAIN_MODEL ||
    process.env.GROQ_MODEL ||
    env.GROQ_EXPLAIN_MODEL ||
    env.GROQ_MODEL ||
    "llama-3.1-8b-instant";
  const model = rawModel.replace(/^groq\//, "");

  const system = [
    "You are the Bashira Decision OS AI. Your task is to provide highly accurate, advanced tooltip explanations for the Al Tasnim project (Construction & Oil/Gas Well Monitoring).",
    "Explain the provided definition/metric and EXACTLY how it relates to project timelines, progress, efficiency, delays, or risk in the Al Tasnim portfolio.",
    "Be highly analytical. For ML features (e.g. 'phase alignment gap', 'cellar 20', 'progress lag', 'over all progress percentages'), explain what the feature physically means on a construction site or rig and how the AI models use it to predict completion.",
    "Do not mention vendors, model families, GPUs, APIs, prompts, or training packages.",
    "Return 2-3 dense, professional sentences. Around 35 to 80 words total.",
    "If the term is a chart, explain how to read it. If it is a metric/variable, describe what it measures and its physical operational impact.",
  ].join(" ");

  const user = [
    `Write the tooltip for: ${term}`,
    context ? `On-screen context: ${context}` : null,
    "Ground truth facts:",
    buildGrounding(term, context, snapshot),
  ]
    .filter(Boolean)
    .join("\n");

  const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      temperature: 0.15,
      max_tokens: 120,
      messages: [
        { role: "system", content: system },
        { role: "user", content: user },
      ],
    }),
  });

  if (!response.ok) {
    return buildFallback(term, context, snapshot);
  }

  const payload = (await response.json()) as {
    choices?: Array<{
      message?: {
        content?: string;
      };
    }>;
  };

  const content = payload.choices?.[0]?.message?.content?.trim();
  if (!content) {
    return buildFallback(term, context, snapshot);
  }

  return content.replace(/\s+/g, " ").trim();
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as {
      term?: string;
      context?: string;
    };

    const rawTerm = (body.term || "").trim();
    if (!rawTerm) {
      return NextResponse.json(
        { error: "Missing term." },
        { status: 400 },
      );
    }

    const context = body.context?.trim() || undefined;
    const term = normalizeTerm(rawTerm);
    const cacheKey = `${term}::${context || ""}`;

    if (responseCache.has(cacheKey)) {
      return NextResponse.json({
        explanation: responseCache.get(cacheKey),
      });
    }

    const snapshot = await loadSnapshot();
    const explanation = await callGroq(term, context, snapshot);
    responseCache.set(cacheKey, explanation);

    return NextResponse.json({ explanation });
  } catch {
    return NextResponse.json(
      {
        explanation:
          "This panel is part of the live Decision Studio package and is explained from the current model outputs.",
      },
      { status: 200 },
    );
  }
}
