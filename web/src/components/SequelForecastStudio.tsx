'use client';
import { useState, useEffect } from 'react';

// ═══════════════════════════════════════════════════════════════════════════
// CURATED PALETTE — Premium Light Institutional Aesthetic
// ═══════════════════════════════════════════════════════════════════════════
const C = {
  bg: '#F8F6F3',
  surface: '#FFFFFF',
  card: '#FFFFFF',
  border: 'rgba(0,0,0,0.08)',
  borderHi: 'rgba(0,0,0,0.15)',
  t1: '#1A1A1A',
  t2: '#4A4A4A',
  t3: '#6B6B6B',
  t4: '#9A9A9A',
  accent: '#E87722',
  danger: '#DC2626',
  safe: '#16A34A',
  warn: '#D97706',
};

const TIER_COLORS: Record<string, string> = {
  CRITICAL: '#DC2626',
  HIGH_RISK: '#D97706',
  WATCH: '#F59E0B',
  HEALTHY: '#16A34A',
};

interface Anomaly {
  id: string;
  well: string;
  old_tier: string;
  new_tier: string;
  severity: 'P1' | 'P2' | 'P3';
  delta: number;
  timestamp: string;
}

interface RiskDrivers {
  feature: string;
  description: string;
  importance: number;
}

interface PredictionResult {
  well_name: string;
  pdo_well_id?: string;
  rig_no: string;
  well_type: string;
  project_name?: string;
  current_progress_pct: number;
  risk_score: number;
  risk_tier: string;
  predicted_progress_4w?: number;
  predicted_delta_4w?: number;
  risk_drivers?: RiskDrivers[];
  risk_components?: { progress_risk: number; velocity_risk: number; schedule_risk: number; gap_risk: number };
  survival?: {
    predicted_completion_date?: string;
    completion_date_early?: string;
    completion_date_late?: string;
    median_completion_weeks?: number;
  };
}

interface ModelInfo {
  autogluon_loaded: boolean;
  rsf_loaded: boolean;
  feature_count: number;
  ag_best_model?: string;
  training_metrics?: { rmse?: number; r2?: number; mape_valid?: number };
}

interface PortfolioSummary {
  total_wells: number;
  avg_progress: number;
  avg_risk_score: number;
  tier_distribution: Record<string, number>;
  top_critical_wells: { well_name: string; rig_no: string; progress_pct: number; risk_score: number }[];
  rig_performance: { rig_no: string; avg_progress: number; avg_risk: number; well_count: number }[];
  risk_drivers: RiskDrivers[];
}

export default function SequelForecastStudio({ onClose }: { onClose: () => void }) {
  const [running, setRunning] = useState<'refresh' | 'full' | null>(null);
  const [targetWell, setTargetWell] = useState('');
  const [targetResult, setTargetResult] = useState<PredictionResult | null>(null);
  const [targetLoading, setTargetLoading] = useState(false);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [activeTab, setActiveTab] = useState<'forecast' | 'portfolio'>('forecast');
  const [error, setError] = useState<string | null>(null);

  // ── Load anomalies + model info on mount ───────────────────────────
  useEffect(() => {
    fetch('/api/predict?action=anomalies')
      .then(res => res.json())
      .then(data => { if (data?.anomalies) setAnomalies(data.anomalies); })
      .catch(console.error);

    fetch('/api/predict?action=model-info')
      .then(res => res.json())
      .then(data => { if (data?.model) setModelInfo(data.model); })
      .catch(console.error);
  }, []);

  // ── Handlers ───────────────────────────────────────────────────────
  const handleRun = async (type: 'refresh' | 'full') => {
    setRunning(type);
    setError(null);
    try {
      const res = await fetch(`/api/predict?action=${type}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
      const data = await res.json();
      if (data?.error) setError(data.error);
      if (type === 'refresh') {
        const anomRes = await fetch('/api/predict?action=anomalies');
        const anomData = await anomRes.json();
        if (anomData?.anomalies) setAnomalies(anomData.anomalies);
      }
    } catch (e: any) { setError(e.message); }
    setRunning(null);
  };

  const handleTargetPredict = async () => {
    if (!targetWell) return;
    setTargetResult(null);
    setTargetLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/predict?action=single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ well: targetWell }),
      });
      const data = await res.json();
      if (data?.result) setTargetResult(data.result);
      else if (data?.error) setError(data.error);
    } catch (e: any) { setError(e.message); }
    setTargetLoading(false);
  };

  const loadPortfolio = async () => {
    setActiveTab('portfolio');
    if (portfolio) return;
    try {
      const res = await fetch('/api/predict?action=portfolio');
      const data = await res.json();
      if (data?.error) { setError(data.error); return; }
      if (data?.tier_distribution) {
        setPortfolio(data);
      } else if (data) {
        // Ensure tier_distribution is always a valid object
        setPortfolio({ ...data, tier_distribution: data.tier_distribution ?? {} });
      }
    } catch (e: any) { setError(e.message); }
  };

  // ── Render Helpers ─────────────────────────────────────────────────
  const TierBadge = ({ tier }: { tier: string }) => (
    <span style={{
      background: TIER_COLORS[tier] || '#6B6B6B',
      color: '#FFFFFF',
      padding: '3px 10px',
      borderRadius: '4px',
      fontSize: '10px',
      fontWeight: 700,
      letterSpacing: '0.08em',
      textTransform: 'uppercase' as const,
    }}>
      {tier.replace('_', ' ')}
    </span>
  );

  const MetricCard = ({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) => (
    <div>
      <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase' as const, letterSpacing: '0.1em', color: C.t3, marginBottom: '4px' }}>{label}</div>
      <div style={{ fontSize: '22px', fontWeight: 700, color: color || C.t1 }}>{value}</div>
      {sub && <div style={{ fontSize: '11px', color: C.t3, marginTop: '2px' }}>{sub}</div>}
    </div>
  );

  return (
    <div className="absolute inset-0 z-50 flex flex-col" style={{ background: C.bg, fontFamily: '"Figtree", sans-serif' }}>

      {/* ── HEADER ── */}
      <div className="flex items-center justify-between px-8 py-5" style={{ background: C.surface, borderBottom: `1px solid ${C.border}` }}>
        <div className="flex items-center gap-4">
          <div className="w-[36px] h-[36px] relative" style={{ perspective: '400px' }}>
            <div className="w-full h-full relative" style={{ transformStyle: 'preserve-3d', animation: 'spinCube 14s infinite linear' }}>
              <style>{`
                @keyframes spinCube { 0% { transform: rotateX(0deg) rotateY(0deg); } 100% { transform: rotateX(360deg) rotateY(360deg); } }
                .qf { position: absolute; width: 100%; height: 100%; border: 1px solid rgba(0,0,0,0.08); opacity: 0.95; }
              `}</style>
              <div className="qf" style={{ background: C.accent, transform: 'translateZ(18px)' }} />
              <div className="qf" style={{ background: '#E5E5E5', transform: 'rotateY(180deg) translateZ(18px)' }} />
              <div className="qf" style={{ background: C.warn, transform: 'rotateY(90deg) translateZ(18px)' }} />
              <div className="qf" style={{ background: C.danger, transform: 'rotateY(-90deg) translateZ(18px)' }} />
              <div className="qf" style={{ background: C.safe, transform: 'rotateX(90deg) translateZ(18px)' }} />
              <div className="qf" style={{ background: '#F5F5F5', transform: 'rotateX(-90deg) translateZ(18px)' }} />
            </div>
          </div>
          <div>
            <h1 className="text-[15px] font-semibold tracking-wide" style={{ color: C.t1 }}>SEQUELFORECAST</h1>
            <p className="text-[10px] uppercase font-semibold tracking-[0.15em] mt-0.5" style={{ color: C.t3 }}>
              Institutional Predictive Engine
              {modelInfo && (
                <span style={{ color: modelInfo.autogluon_loaded ? C.safe : C.warn, marginLeft: '8px' }}>
                  ● {modelInfo.autogluon_loaded ? 'AG Live' : 'Cached ML'}
                </span>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Tab switcher */}
          <div className="flex rounded-lg overflow-hidden" style={{ border: `1px solid ${C.border}` }}>
            {(['forecast', 'portfolio'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => tab === 'portfolio' ? loadPortfolio() : setActiveTab('forecast')}
                className="px-4 py-2 text-[10px] font-semibold tracking-widest uppercase transition-all"
                style={{
                  background: activeTab === tab ? C.t1 : C.surface,
                  color: activeTab === tab ? '#fff' : C.t2,
                }}
              >
                {tab}
              </button>
            ))}
          </div>
          <button onClick={onClose} className="px-5 py-2.5 text-[10px] font-semibold tracking-widest uppercase transition-all rounded-lg"
            style={{ color: C.t1, background: C.surface, border: `1px solid ${C.borderHi}` }}
            onMouseEnter={e => e.currentTarget.style.background = '#F5F5F5'}
            onMouseLeave={e => e.currentTarget.style.background = C.surface}
          >CLOSE</button>
        </div>
      </div>

      {error && (
        <div className="mx-8 mt-4 px-4 py-3 rounded-lg text-[12px]" style={{ background: '#FEF2F2', color: C.danger, border: '1px solid #FECACA' }}>
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto w-full max-w-[1600px] mx-auto px-8 py-8 grid grid-cols-1 md:grid-cols-12 gap-6">

        {activeTab === 'forecast' ? (
          <>
            {/* ── LEFT COLUMN: CONTROL PANELS ── */}
            <div className="md:col-span-8 flex flex-col gap-6">

              {/* Target Well Forecast */}
              <div className="p-8 rounded-xl" style={{ background: C.surface, border: `1px solid #E5E5E5`, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
                <h2 className="text-[11px] font-bold tracking-[0.1em] uppercase mb-2" style={{ color: C.t1 }}>Target Well Forecast</h2>
                <p className="text-[12px] mb-6" style={{ color: C.t3 }}>Real ML prediction — AutoGluon R²=0.987 + Random Survival Forest for completion dates.</p>

                <div className="flex gap-4 items-end">
                  <div className="flex-1">
                    <label className="text-[10px] font-semibold uppercase tracking-widest block mb-2" style={{ color: C.t3 }}>Well Name or PDO Well ID</label>
                    <div className="flex items-center rounded-lg overflow-hidden" style={{ border: '1px solid #D4D4D4' }}>
                      <input
                        type="text"
                        value={targetWell}
                        onChange={e => setTargetWell(e.target.value)}
                        placeholder="e.g. RKDS_2026_OP_LOC3 or NIMR-1621"
                        className="w-full bg-transparent px-4 py-3 text-[13px] outline-none"
                        style={{ color: C.t1 }}
                        onKeyDown={e => e.key === 'Enter' && handleTargetPredict()}
                      />
                      <button
                        onClick={handleTargetPredict}
                        disabled={targetLoading}
                        className="px-8 py-3 text-[10px] font-bold tracking-widest uppercase transition-colors h-full disabled:opacity-50"
                        style={{ background: C.t1, color: '#FFFFFF' }}
                      >
                        {targetLoading ? 'Loading...' : 'Predict'}
                      </button>
                    </div>
                  </div>
                </div>

                {/* ── Prediction Results ── */}
                {targetResult && (
                  <div className="mt-8 pt-8" style={{ borderTop: '1px solid #E5E5E5' }}>
                    {/* Top metrics row */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
                      <MetricCard label="Risk Score" value={targetResult.risk_score} color={TIER_COLORS[targetResult.risk_tier]} />
                      <div>
                        <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: C.t3, marginBottom: '6px' }}>Tier</div>
                        <TierBadge tier={targetResult.risk_tier} />
                      </div>
                      <MetricCard label="Current Progress" value={`${targetResult.current_progress_pct}%`} />
                      {targetResult.predicted_progress_4w !== undefined && (
                        <MetricCard
                          label="4-Week Forecast"
                          value={`${targetResult.predicted_progress_4w}%`}
                          sub={`Δ ${(targetResult.predicted_delta_4w ?? 0) > 0 ? '+' : ''}${targetResult.predicted_delta_4w}pp`}
                          color={C.safe}
                        />
                      )}
                    </div>

                    {/* Well Details */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      {[
                        { l: 'Well', v: targetResult.well_name },
                        { l: 'Rig', v: targetResult.rig_no },
                        { l: 'Type', v: targetResult.well_type },
                        { l: 'Project', v: targetResult.project_name || 'N/A' },
                      ].map(({ l, v }) => (
                        <div key={l}>
                          <div style={{ fontSize: '10px', fontWeight: 600, color: C.t3, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{l}</div>
                          <div style={{ fontSize: '12px', fontWeight: 600, color: C.t1, marginTop: '2px' }}>{v || 'N/A'}</div>
                        </div>
                      ))}
                    </div>

                    {/* Survival Prediction */}
                    {targetResult.survival && targetResult.survival.predicted_completion_date && (
                      <div className="p-4 rounded-lg mb-6" style={{ background: '#F0FDF4', border: '1px solid #BBF7D0' }}>
                        <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: C.safe, marginBottom: '6px' }}>
                          Completion Prediction (RSF Model)
                        </div>
                        <div className="grid grid-cols-3 gap-4">
                          <div>
                            <div style={{ fontSize: '10px', color: C.t3 }}>Early (25th)</div>
                            <div style={{ fontSize: '13px', fontWeight: 700, color: C.t1 }}>{targetResult.survival.completion_date_early || '—'}</div>
                          </div>
                          <div>
                            <div style={{ fontSize: '10px', color: C.t3 }}>Median</div>
                            <div style={{ fontSize: '13px', fontWeight: 700, color: C.safe }}>{targetResult.survival.predicted_completion_date}</div>
                          </div>
                          <div>
                            <div style={{ fontSize: '10px', color: C.t3 }}>Late (75th)</div>
                            <div style={{ fontSize: '13px', fontWeight: 700, color: C.t1 }}>{targetResult.survival.completion_date_late || '—'}</div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Risk Components */}
                    {targetResult.risk_components && (
                      <div className="mb-6">
                        <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: C.t3, marginBottom: '8px' }}>
                          Risk Decomposition
                        </div>
                        <div className="grid grid-cols-4 gap-3">
                          {[
                            { l: 'Progress', v: targetResult.risk_components.progress_risk, w: '35%' },
                            { l: 'Velocity', v: targetResult.risk_components.velocity_risk, w: '25%' },
                            { l: 'Schedule', v: targetResult.risk_components.schedule_risk, w: '20%' },
                            { l: 'Gap', v: targetResult.risk_components.gap_risk, w: '20%' },
                          ].map(({ l, v, w }) => (
                            <div key={l} className="p-3 rounded-lg" style={{ background: '#FAFAFA', border: '1px solid #E5E5E5' }}>
                              <div style={{ fontSize: '9px', fontWeight: 600, color: C.t4, textTransform: 'uppercase' }}>{l} ({w})</div>
                              <div className="flex items-center gap-2 mt-1">
                                <div style={{ fontSize: '14px', fontWeight: 700, color: v > 70 ? C.danger : v > 40 ? C.warn : C.safe }}>{v}%</div>
                                <div className="flex-1 h-[4px] rounded-full" style={{ background: '#E5E5E5' }}>
                                  <div className="h-full rounded-full" style={{ width: `${Math.min(v, 100)}%`, background: v > 70 ? C.danger : v > 40 ? C.warn : C.safe }} />
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* SHAP Risk Drivers */}
                    {targetResult.risk_drivers && targetResult.risk_drivers.length > 0 && (
                      <div>
                        <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: C.t3, marginBottom: '8px' }}>
                          Top Risk Drivers (SHAP)
                        </div>
                        <div className="space-y-2">
                          {targetResult.risk_drivers.map((d, i) => (
                            <div key={i} className="flex items-center gap-3 px-3 py-2 rounded" style={{ background: '#FAFAFA' }}>
                              <span style={{ fontSize: '11px', fontWeight: 700, color: C.accent, minWidth: '18px' }}>#{i + 1}</span>
                              <span style={{ fontSize: '12px', fontWeight: 500, color: C.t1, flex: 1 }}>{d.description}</span>
                              <span style={{ fontSize: '11px', fontWeight: 600, color: C.t3 }}>{d.importance.toFixed(3)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* System Sync */}
              <div className="p-8 rounded-xl" style={{ background: C.surface, border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
                <h2 className="text-[11px] font-bold tracking-[0.1em] uppercase mb-2" style={{ color: C.t1 }}>Run Nightly Evaluation</h2>
                <p className="text-[12px] mb-6" style={{ color: C.t3 }}>Batch predict all active wells using AutoGluon + RSF. Detects tier changes and fires anomalies.</p>
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => handleRun('refresh')}
                    disabled={running !== null}
                    className="px-6 py-3 text-[10px] font-bold tracking-widest uppercase flex items-center gap-3 transition-colors disabled:opacity-50 rounded-lg"
                    style={{ background: running === 'refresh' ? '#F5F5F5' : C.t1, color: running === 'refresh' ? C.t3 : '#FFFFFF' }}
                  >
                    {running === 'refresh' ? 'Evaluating...' : 'Start Evaluation'}
                  </button>
                  <div className="text-[11px]" style={{ color: C.t4 }}>Real ML batch inference</div>
                </div>
              </div>

              {/* Full Pipeline */}
              <div className="p-8 rounded-xl" style={{ background: C.surface, border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
                <h2 className="text-[11px] font-bold tracking-[0.1em] uppercase mb-2" style={{ color: C.t1 }}>Retrain Predictive Engine</h2>
                <p className="text-[12px] mb-6" style={{ color: C.t3 }}>Full pipeline: export data → Kaggle GPU → AutoGluon best_quality (8-fold, 2-stack) + RSF + SHAP</p>
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => handleRun('full')}
                    disabled={running !== null}
                    className="px-6 py-3 text-[10px] font-bold tracking-widest uppercase flex items-center gap-3 transition-colors disabled:opacity-50 rounded-lg"
                    style={{ background: '#F8F6F3', color: C.t1, border: '1px solid #D4D4D4' }}
                  >
                    {running === 'full' ? 'Queued...' : 'Start Full Retrain'}
                  </button>
                  <div className="text-[11px]" style={{ color: C.t4 }}>Requires GPU (Kaggle)</div>
                </div>
              </div>

              {/* Model Health */}
              {modelInfo && (
                <div className="p-6 rounded-xl" style={{ background: C.surface, border: '1px solid #E5E5E5' }}>
                  <h2 className="text-[11px] font-bold tracking-[0.1em] uppercase mb-4" style={{ color: C.t1 }}>Model Health</h2>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[12px]">
                    <div>
                      <span style={{ color: C.t3 }}>AutoGluon:</span>{' '}
                      <span style={{ color: modelInfo.autogluon_loaded ? C.safe : C.danger, fontWeight: 700 }}>
                        {modelInfo.autogluon_loaded ? '● LIVE' : '○ OFFLINE'}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: C.t3 }}>RSF:</span>{' '}
                      <span style={{ color: modelInfo.rsf_loaded ? C.safe : C.danger, fontWeight: 700 }}>
                        {modelInfo.rsf_loaded ? '● LIVE' : '○ OFFLINE'}
                      </span>
                    </div>
                    {modelInfo.ag_best_model && (
                      <div><span style={{ color: C.t3 }}>Best:</span> <span style={{ fontWeight: 600 }}>{modelInfo.ag_best_model}</span></div>
                    )}
                    <div><span style={{ color: C.t3 }}>Features:</span> <span style={{ fontWeight: 600 }}>{modelInfo.feature_count}</span></div>
                    {modelInfo.training_metrics && (
                      <>
                        <div><span style={{ color: C.t3 }}>RMSE:</span> <span style={{ fontWeight: 600 }}>{modelInfo.training_metrics.rmse?.toFixed(4)}</span></div>
                        <div><span style={{ color: C.t3 }}>R²:</span> <span style={{ fontWeight: 600 }}>{modelInfo.training_metrics.r2?.toFixed(4)}</span></div>
                        <div><span style={{ color: C.t3 }}>MAPE:</span> <span style={{ fontWeight: 600 }}>{modelInfo.training_metrics.mape_valid?.toFixed(1)}%</span></div>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          /* ── PORTFOLIO TAB ── */
          <div className="md:col-span-8 flex flex-col gap-6">
            {portfolio ? (
              <>
                {/* Tier Distribution */}
                <div className="p-8 rounded-xl" style={{ background: C.surface, border: '1px solid #E5E5E5' }}>
                  <h2 className="text-[11px] font-bold tracking-[0.1em] uppercase mb-6" style={{ color: C.t1 }}>Portfolio Risk Distribution</h2>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <MetricCard label="Total Wells" value={portfolio.total_wells} />
                    {['CRITICAL', 'HIGH_RISK', 'WATCH', 'HEALTHY'].map(tier => (
                      <div key={tier}>
                        <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: C.t3, marginBottom: '4px' }}>{tier.replace('_', ' ')}</div>
                        <div style={{ fontSize: '22px', fontWeight: 700, color: TIER_COLORS[tier] }}>{portfolio.tier_distribution?.[tier] ?? 0}</div>
                        <div className="mt-1 h-[4px] rounded-full" style={{ background: '#E5E5E5' }}>
                          <div className="h-full rounded-full" style={{
                            width: `${((portfolio.tier_distribution?.[tier] ?? 0) / (portfolio.total_wells || 1)) * 100}%`,
                            background: TIER_COLORS[tier],
                          }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Top Critical Wells */}
                <div className="p-8 rounded-xl" style={{ background: C.surface, border: '1px solid #E5E5E5' }}>
                  <h2 className="text-[11px] font-bold tracking-[0.1em] uppercase mb-4" style={{ color: C.t1 }}>Top Critical Wells</h2>
                  <div className="space-y-2">
                    {portfolio.top_critical_wells.map((w, i) => (
                      <div key={i} className="flex items-center justify-between px-4 py-3 rounded-lg" style={{ background: '#FEF2F2', border: '1px solid #FECACA' }}>
                        <div className="flex items-center gap-3">
                          <span style={{ fontSize: '11px', fontWeight: 700, color: C.danger }}>#{i + 1}</span>
                          <span style={{ fontSize: '12px', fontWeight: 600, color: C.t1 }}>{w.well_name}</span>
                          <span style={{ fontSize: '11px', color: C.t3 }}>{w.rig_no}</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span style={{ fontSize: '11px', color: C.t3 }}>Progress: {w.progress_pct}%</span>
                          <span style={{ fontSize: '12px', fontWeight: 700, color: C.danger }}>Risk: {w.risk_score}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Rig Performance */}
                <div className="p-8 rounded-xl" style={{ background: C.surface, border: '1px solid #E5E5E5' }}>
                  <h2 className="text-[11px] font-bold tracking-[0.1em] uppercase mb-4" style={{ color: C.t1 }}>Rig Performance</h2>
                  <div className="overflow-x-auto">
                    <table className="w-full text-[12px]">
                      <thead>
                        <tr style={{ borderBottom: '1px solid #E5E5E5' }}>
                          {['Rig', 'Avg Progress', 'Avg Risk', 'Wells'].map(h => (
                            <th key={h} className="text-left py-2 px-3" style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: C.t3 }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {portfolio.rig_performance.slice(0, 15).map((r, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid #F5F5F5' }}>
                            <td className="py-2 px-3 font-semibold" style={{ color: C.t1 }}>{r.rig_no}</td>
                            <td className="py-2 px-3" style={{ color: r.avg_progress > 50 ? C.safe : r.avg_progress > 20 ? C.warn : C.danger }}>{r.avg_progress}%</td>
                            <td className="py-2 px-3" style={{ color: r.avg_risk > 65 ? C.danger : r.avg_risk > 45 ? C.warn : C.safe }}>{r.avg_risk}</td>
                            <td className="py-2 px-3" style={{ color: C.t2 }}>{r.well_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Risk Drivers */}
                {portfolio.risk_drivers && portfolio.risk_drivers.length > 0 && (
                  <div className="p-8 rounded-xl" style={{ background: C.surface, border: '1px solid #E5E5E5' }}>
                    <h2 className="text-[11px] font-bold tracking-[0.1em] uppercase mb-4" style={{ color: C.t1 }}>Global Risk Drivers (SHAP)</h2>
                    <div className="space-y-2">
                      {portfolio.risk_drivers.map((d, i) => (
                        <div key={i} className="flex items-center gap-3 px-3 py-2 rounded" style={{ background: '#FAFAFA' }}>
                          <span style={{ fontSize: '11px', fontWeight: 700, color: C.accent, minWidth: '18px' }}>#{i + 1}</span>
                          <span style={{ fontSize: '12px', fontWeight: 500, color: C.t1, flex: 1 }}>{d.description}</span>
                          <div className="w-[80px] h-[4px] rounded-full" style={{ background: '#E5E5E5' }}>
                            <div className="h-full rounded-full" style={{ width: `${Math.min(d.importance * 1000, 100)}%`, background: C.accent }} />
                          </div>
                          <span style={{ fontSize: '11px', fontWeight: 600, color: C.t3 }}>{d.importance.toFixed(3)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-64 text-[13px]" style={{ color: C.t3 }}>Loading portfolio data...</div>
            )}
          </div>
        )}

        {/* ── RIGHT COLUMN: ANOMALY FEED ── */}
        <div className="md:col-span-4 flex flex-col h-full">
          <div className="flex-1 flex flex-col p-8 rounded-xl" style={{ background: C.surface, border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-[11px] font-bold tracking-[0.1em] uppercase" style={{ color: C.t1 }}>Anomaly Feed</h2>
              <span className="text-[10px] font-bold tracking-widest uppercase" style={{ color: C.safe }}>
                {anomalies.length > 0 ? `${anomalies.length} events` : 'Monitoring'}
              </span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3">
              {anomalies.length === 0 ? (
                <div className="text-[12px] p-4 text-center rounded-lg" style={{ color: C.t4, background: '#FAFAFA', border: '1px solid #E5E5E5' }}>
                  No anomalies detected. Run nightly evaluation to detect tier changes.
                </div>
              ) : (
                anomalies.map(an => {
                  const isEscalation = an.delta > 0;
                  let c = C.t1;
                  if (an.severity === 'P1') c = C.danger;
                  else if (an.severity === 'P2') c = C.warn;
                  else if (an.severity === 'P3') c = C.safe;

                  return (
                    <div key={an.id} className="p-4 rounded-lg cursor-pointer transition-all" style={{ background: '#FAFAFA', border: '1px solid #E5E5E5', borderLeft: `3px solid ${c}` }}
                      onClick={() => { setTargetWell(an.well); setActiveTab('forecast'); }}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[12px] font-bold" style={{ color: C.t1 }}>{an.well}</span>
                        <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: C.t3 }}>{an.timestamp}</span>
                      </div>
                      <div className="flex items-baseline gap-2 mb-2">
                        <TierBadge tier={an.old_tier} />
                        <span className="text-[10px]" style={{ color: C.t4 }}>→</span>
                        <TierBadge tier={an.new_tier} />
                      </div>
                      <div className="flex items-center justify-between text-[10px]">
                        <span style={{ color: c }}>{an.severity} {isEscalation ? 'ESCALATION' : 'RECOVERY'}</span>
                        <span style={{ color: C.t2 }}>Δ {an.delta > 0 ? '+' : ''}{an.delta.toFixed(1)}</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
