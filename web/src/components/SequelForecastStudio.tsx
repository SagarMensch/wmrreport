'use client';
import { useState, useEffect } from 'react';

// ═══════════════════════════════════════════════════════════════════════════
// CURATED PALETTE — Pure Institutional Solid Aesthetic
// ═══════════════════════════════════════════════════════════════════════════
const C = {
  bg: '#000000',          // Absolute solid black
  surface: '#080808',     // Deep solid grey
  card: '#111111',        // Opaque card background
  cardHover: '#161616',   // Slightly elevated opaque
  border: '#242424',      // Sharp solid border
  borderHi: '#383838',    // Highlight border for active states
  t1: '#FFFFFF',          // Pure white
  t2: '#A3A3A3',          // Neutral medium text
  t3: '#737373',          // Neutral dark text
  accent: '#2563EB',      // Deep solid royal blue
  danger: '#DC2626',      // Professional solid red
  safe: '#059669',        // Professional solid green
  warn: '#D97706',        // Professional solid gold
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

export default function SequelForecastStudio({ onClose }: { onClose: () => void }) {
  const [running, setRunning] = useState<'refresh' | 'full' | null>(null);
  const [targetWell, setTargetWell] = useState('');
  const [targetResult, setTargetResult] = useState<any>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);

  useEffect(() => {
    fetch('/api/predict?action=anomalies')
      .then(res => res.json())
      .then(data => {
        if (data && data.anomalies) setAnomalies(data.anomalies);
      })
      .catch(console.error);
  }, []);

  const handleRun = async (type: 'refresh' | 'full') => {
    setRunning(type);
    try {
      await fetch(`/api/predict?action=${type}`, { method: 'POST', body: JSON.stringify({}) });
      if (type === 'refresh') {
        const res = await fetch('/api/predict?action=anomalies');
        const data = await res.json();
        if (data && data.anomalies) setAnomalies(data.anomalies);
      } else {
        // Mock a 5s delay for UI feedback on the full pipeline
        await new Promise(r => setTimeout(r, 5000));
      }
    } catch(e) { console.error(e); }
    setRunning(null);
  };

  const handleTargetPredict = async () => {
    if (!targetWell) return;
    setTargetResult(null);
    try {
      const res = await fetch('/api/predict?action=single', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ well: targetWell }) });
      const data = await res.json();
      if (data && data.result) setTargetResult(data.result);
      else setTargetResult({ risk: 'N/A', tier: 'NOT_FOUND', completion: 'Entity not found in centralized datastore' });
    } catch (e) {
      console.error(e);
      setTargetResult({ risk: 'ERR', tier: 'SYSTEM_ERROR', completion: 'Data integration failed' });
    }
  };

  return (
    <div className="absolute inset-0 z-50 flex flex-col font-sans" style={{ background: C.bg }}>
      
      {/* ── HEADER ── */}
      <div className="flex items-center justify-between px-8 py-5" style={{ background: C.surface, borderBottom: `1px solid ${C.border}` }}>
        <div className="flex items-center gap-4">
          <div className="w-[32px] h-[32px] relative" style={{ perspective: '400px' }}>
            <div className="w-full h-full relative" style={{ transformStyle: 'preserve-3d', animation: 'spinCube 14s infinite linear' }}>
              <style>{`
                @keyframes spinCube { 0% { transform: rotateX(0deg) rotateY(0deg); } 100% { transform: rotateX(360deg) rotateY(360deg); } }
                .qf { position: absolute; width: 100%; height: 100%; border: 1px solid ${C.bg}; opacity: 0.95; }
              `}</style>
              <div className="qf" style={{ background: C.accent, transform: 'translateZ(16px)' }} />
              <div className="qf" style={{ background: C.card, transform: 'rotateY(180deg) translateZ(16px)' }} />
              <div className="qf" style={{ background: C.warn, transform: 'rotateY(90deg) translateZ(16px)' }} />
              <div className="qf" style={{ background: C.danger, transform: 'rotateY(-90deg) translateZ(16px)' }} />
              <div className="qf" style={{ background: C.safe, transform: 'rotateX(90deg) translateZ(16px)' }} />
              <div className="qf" style={{ background: C.t1, transform: 'rotateX(-90deg) translateZ(16px)' }} />
            </div>
          </div>
          <div>
            <h1 className="text-[14px] font-semibold tracking-wide" style={{ color: C.t1 }}>SEQUELFORECAST</h1>
            <p className="text-[10px] uppercase font-bold tracking-[0.15em] mt-0.5" style={{ color: C.t3 }}>Institutional Predictive Engine</p>
          </div>
        </div>
        <button 
          onClick={onClose} 
          className="px-5 py-2 text-[10px] font-bold tracking-widest uppercase transition-colors" 
          style={{ color: C.t2, border: `1px solid ${C.border}`, background: C.card }}
          onMouseEnter={e => e.currentTarget.style.background = C.border}
          onMouseLeave={e => e.currentTarget.style.background = C.card}
        >
          CLOSE
        </button>
      </div>

      <div className="flex-1 overflow-y-auto w-full max-w-[1600px] mx-auto px-8 py-8 grid grid-cols-1 md:grid-cols-12 gap-6">
        
        {/* ── LEFT COLUMN: CONTROL PANELS ── */}
        <div className="md:col-span-8 flex flex-col gap-6">
          
          {/* Targeted Entity Forecast */}
          <div className="p-8" style={{ background: C.card, border: `1px solid ${C.border}` }}>
            <h2 className="text-[11px] font-bold tracking-widest uppercase mb-2" style={{ color: C.t1 }}>Target Well Forecast</h2>
            <p className="text-[12px] mb-8" style={{ color: C.t2 }}>Evaluate specific risk factors and predicted completion timelines for an individual well.</p>
            
            <div className="flex gap-4 items-end">
              <div className="flex-1">
                <label className="text-[10px] font-bold uppercase tracking-widest block mb-2" style={{ color: C.t3 }}>Well Name</label>
                <div className="flex items-center" style={{ border: `1px solid ${C.border}`, background: C.surface }}>
                  <input
                    type="text"
                    value={targetWell}
                    onChange={e => setTargetWell(e.target.value)}
                    placeholder="e.g. RKDS_2026_OP_LOC3"
                    className="w-full bg-transparent px-4 py-3 text-[13px] font-mono outline-none"
                    style={{ color: C.t1 }}
                    onKeyDown={e => e.key === 'Enter' && handleTargetPredict()}
                  />
                  <button
                    onClick={handleTargetPredict}
                    className="px-8 py-3 text-[10px] font-bold tracking-widest uppercase transition-colors h-full"
                    style={{ background: C.t1, color: C.bg }}
                  >
                    Load
                  </button>
                </div>
              </div>
            </div>

            {targetResult && (
              <div className="mt-8 pt-8 grid grid-cols-3 gap-6" style={{ borderTop: `1px solid ${C.border}` }}>
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: C.t3 }}>Risk Index</div>
                  <div className="text-[24px] font-mono font-medium" style={{ color: C.t1 }}>{targetResult.risk}</div>
                </div>
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: C.t3 }}>Tier Assignment</div>
                  <div className="text-[11px] font-bold px-3 py-1.5 inline-block uppercase tracking-wider mt-1" style={{ background: C.surface, color: C.t1, border: `1px solid ${C.border}` }}>
                    {targetResult.tier.replace('_', ' ')}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: C.t3 }}>Projected Completion</div>
                  <div className="text-[16px] mt-1" style={{ color: C.t1 }}>{targetResult.completion}</div>
                </div>
              </div>
            )}
          </div>

          {/* System Sync */}
          <div className="p-8" style={{ background: C.card, border: `1px solid ${C.border}` }}>
            <h2 className="text-[11px] font-bold tracking-widest uppercase mb-2" style={{ color: C.t1 }}>Run Nightly Evaluation</h2>
            <p className="text-[12px] mb-6" style={{ color: C.t2 }}>Evaluate the latest operational data across all active wells to detect emerging risks and update tiers.</p>
            
            <div className="flex items-center gap-4">
              <button
                onClick={() => handleRun('refresh')}
                disabled={running !== null}
                className="px-6 py-3 text-[10px] font-bold tracking-widest uppercase flex items-center gap-3 transition-colors disabled:opacity-50"
                style={{ background: running === 'refresh' ? C.surface : C.t1, color: running === 'refresh' ? C.t2 : C.bg, border: `1px solid ${running === 'refresh' ? C.border : C.t1}` }}
              >
                {running === 'refresh' ? 'Evaluating...' : 'Start Evaluation'}
              </button>
              <div className="text-[11px]" style={{ color: C.t3 }}>Run Time: ~2 seconds</div>
            </div>
          </div>

          {/* Full Pipeline */}
          <div className="p-8" style={{ background: C.card, border: `1px solid ${C.border}` }}>
            <h2 className="text-[11px] font-bold tracking-widest uppercase mb-2" style={{ color: C.t1 }}>Retrain Predictive Engine</h2>
            <p className="text-[12px] mb-6" style={{ color: C.t2 }}>Update the core forecasting model using the latest historical well data to ensure predictions remain highly accurate.</p>
            
            <div className="flex items-center gap-4">
              <button
                onClick={() => handleRun('full')}
                disabled={running !== null}
                className="px-6 py-3 text-[10px] font-bold tracking-widest uppercase flex items-center gap-3 transition-colors disabled:opacity-50"
                style={{ background: C.surface, color: C.t1, border: `1px solid ${C.borderHi}` }}
                onMouseEnter={e => { if(running === null) e.currentTarget.style.background = C.border; }}
                onMouseLeave={e => { if(running === null) e.currentTarget.style.background = C.surface; }}
              >
                {running === 'full' ? 'Retraining active...' : 'Start Full Retrain'}
              </button>
              <div className="text-[11px]" style={{ color: C.t3 }}>Run Time: ~15 minutes</div>
            </div>
          </div>

        </div>

        {/* ── RIGHT COLUMN: ANOMALY FEED ── */}
        <div className="md:col-span-4 flex flex-col h-full">
          <div className="flex-1 flex flex-col p-8" style={{ background: C.card, border: `1px solid ${C.border}` }}>
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-[11px] font-bold tracking-widest uppercase" style={{ color: C.t1 }}>Anomaly Feed</h2>
              <span className="text-[10px] font-bold tracking-widest uppercase" style={{ color: C.safe }}>Active</span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4">
              {anomalies.length === 0 ? (
                <div className="text-[12px] p-4 text-center" style={{ color: C.t3, background: C.surface, border: `1px solid ${C.border}` }}>No anomalies detected in the current cycle.</div>
              ) : (
                anomalies.map(an => {
                  const isEscalation = an.delta > 0;
                  // Use crisp solid colors for severity
                  let c = C.t1;
                  if (an.severity === 'P1') c = C.danger;
                  else if (an.severity === 'P2') c = C.warn;
                  else if (an.severity === 'P3') c = C.safe;

                  return (
                    <div key={an.id} className="p-4" style={{ background: C.surface, border: `1px solid ${C.border}`, borderLeft: `3px solid ${c}` }}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[12px] font-bold" style={{ color: C.t1 }}>{an.well}</span>
                        <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: C.t3 }}>{an.timestamp}</span>
                      </div>
                      <div className="flex items-baseline gap-2 mb-3">
                        <span className="text-[11px]" style={{ color: C.t2 }}>{an.old_tier}</span>
                        <span className="text-[10px]" style={{ color: C.t3 }}>→</span>
                        <span className="text-[11px] font-bold" style={{ color: C.t1 }}>{an.new_tier}</span>
                      </div>
                      <div className="flex items-center justify-between text-[10px] font-mono">
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
