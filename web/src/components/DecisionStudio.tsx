'use client';
import { useEffect, useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, RadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, Radar, AreaChart, Area,
} from 'recharts';
import dynamic from 'next/dynamic';
import SequelForecastStudio from './SequelForecastStudio';

const Plot = dynamic(
  () => import('plotly.js-dist-min').then((Plotly) => {
    return import('react-plotly.js/factory').then((mod) => {
      return mod.default(Plotly.default || Plotly);
    });
  }),
  { ssr: false }
);

// ═══════════════════════════════════════════════════════════════════════════
// HERMES / BLACKSTONE DESIGN SYSTEM
// Solid. Concrete. No gradients. No 3D. Photography-grade precision.
// Off-white canvas, solid black type, orange accent used SPARINGLY.
// ═══════════════════════════════════════════════════════════════════════════
const C = {
  bg: '#FAFAFA', surface: '#FFFFFF', card: '#FFFFFF', cardHover: '#F5F5F5',
  border: '#E5E5E5', borderHi: '#D4D4D4',
  t1: '#0A0A0A', t2: '#525252', t3: '#737373', t4: '#A3A3A3',
  orange: '#E87722', blue: '#2563EB',
  red: '#DC2626', gold: '#92702A',
  green: '#16A34A', violet: '#7C3AED', teal: '#0D9488',
};

const TIERS: Record<string, { c: string; l: string }> = {
  CRITICAL: { c: C.red, l: 'Critical' },
  HIGH_RISK: { c: C.orange, l: 'High Risk' },
  WATCH: { c: C.gold, l: 'Watch' },
  HEALTHY: { c: C.green, l: 'Healthy' },
};

// ── Types & Utils ─────────────────────────────────────────────────────────
interface Met { best_model: string; rmse: number; mae: number; r2: number; mape_valid: number; }
interface Well {
  pdo_well_id: string; well_name_after_spud: string; project_name: string; rig_no: string;
  well_type: string; current_progress_pct: number; risk_score: number;
  risk_tier: string; predicted_completion_date: string; weeks_remaining_predicted: number;
}

function csv(text: string): Record<string, string>[] {
  const ls = text.trim().split('\n');
  if (ls.length < 2) return [];
  const h = ls[0].split(',').map(s => s.trim().replace(/^"|"$/g, ''));
  return ls.slice(1).map(l => {
    const v = l.split(',').map(s => s.trim().replace(/^"|"$/g, ''));
    const o: Record<string, string> = {};
    h.forEach((k, i) => { o[k] = v[i] || ''; });
    return o;
  });
}

function CountUp({ to, d = 0, s = '' }: { to: number; d?: number; s?: string }) {
  const [v, setV] = useState(0);
  useEffect(() => {
    const start = performance.now(); let raf: number;
    const tick = (now: number) => {
      const t = Math.min((now - start) / 2000, 1);
      setV(to * (1 - Math.pow(1 - t, 3)));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [to]);
  return <>{v.toFixed(d)}{s}</>;
}

// ── ExplainTooltip ────────────────────────────────────────────────────────
function Info({ term, ctx, children }: { term: string; ctx?: string; children: React.ReactNode }) {
  const [show, setShow] = useState(false);
  const [text, setText] = useState('');
  const [ld, setLd] = useState(false);
  const cache = useRef<Record<string, string>>({});
  const to = useRef<ReturnType<typeof setTimeout>>();

  const load = useCallback(async () => {
    if (cache.current[term]) { setText(cache.current[term]); return; }
    setLd(true);
    try {
      const r = await fetch('/api/explain', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ term, context: ctx }) });
      const d = await r.json();
      const clean = (d.explanation || '').replace(/\*\*/g, '').replace(/\*/g, '').trim();
      cache.current[term] = clean; setText(clean);
    } catch { setText('Unavailable.'); } finally { setLd(false); }
  }, [term, ctx]);

  return (
    <div className="relative inline-block"
      onMouseEnter={() => { to.current = setTimeout(() => { setShow(true); load(); }, 600); }}
      onMouseLeave={() => { clearTimeout(to.current); setShow(false); }}
    >
      {children}
      <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full text-[8px] font-bold cursor-help" style={{ background: '#F0F0F0', color: '#6B6B6B' }}>?</span>
      <AnimatePresence>
        {show && (
          <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
            className="absolute z-50 top-full left-0 mt-2 w-72 p-5 rounded-lg shadow-xl" style={{ background: '#FFFFFF', border: '1px solid rgba(0,0,0,0.08)' }}>
            <div className="absolute bottom-full left-6 w-2.5 h-2.5 rotate-45 mb-[-5px]" style={{ background: '#FFFFFF', borderTop: '1px solid rgba(0,0,0,0.08)', borderLeft: '1px solid rgba(0,0,0,0.08)' }} />
            <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: '#E87722' }}>{term}</div>
            {ld ? <span className="text-[12px] font-medium" style={{ color: '#6B6B6B' }}>Reasoning...</span> : <p className="text-[13px] leading-relaxed font-medium" style={{ color: '#1A1A1A' }}>{text}</p>}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── 3D Mesh Bar Builder (actual 3D prisms) ────────────────────────────────
function meshBar(idx: number, height: number, color: string, label: string, bw = 0.35, bd = 0.35) {
  const x = idx, hw = bw / 2, hd = bd / 2;
  return {
    type: 'mesh3d' as const, name: label, showscale: false, flatshading: true,
    hovertext: `${label}: ${height}%`, hoverinfo: 'text' as const,
    x: [x - hw, x + hw, x + hw, x - hw, x - hw, x + hw, x + hw, x - hw],
    y: [-hd, -hd, hd, hd, -hd, -hd, hd, hd],
    z: [0, 0, 0, 0, height, height, height, height],
    i: [0, 0, 4, 4, 0, 0, 2, 2, 0, 0, 1, 1],
    j: [1, 2, 5, 6, 1, 5, 3, 7, 3, 7, 2, 6],
    k: [2, 3, 6, 7, 5, 4, 7, 6, 7, 4, 6, 5],
    facecolor: Array(12).fill(color),
    lighting: { ambient: 0.7, diffuse: 0.6, specular: 0.3, roughness: 0.5 },
    lightposition: { x: 100, y: 200, z: 50000 },
  };
}

const scene3D = (xt: string, yt: string, zt: string) => ({
  xaxis: { title: { text: xt, font: { size: 9, color: C.t3 } }, gridcolor: C.border, zerolinecolor: C.border, backgroundcolor: 'rgba(10,22,40,0)' },
  yaxis: { title: { text: yt, font: { size: 9, color: C.t3 } }, gridcolor: C.border, zerolinecolor: C.border, backgroundcolor: 'rgba(10,22,40,0)' },
  zaxis: { title: { text: zt, font: { size: 9, color: C.t3 } }, gridcolor: C.border, zerolinecolor: C.border, backgroundcolor: 'rgba(10,22,40,0)' },
  bgcolor: 'rgba(10,22,40,0)',
});
const pCfg = { displayModeBar: false, responsive: true };
const pLay = { paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { family: 'monospace', color: C.t2, size: 10 }, showlegend: false };

// ═══════════════════════════════════════════════════════════════════════════
// MAIN
// ═══════════════════════════════════════════════════════════════════════════
export default function DecisionStudio() {
  const [met, setMet] = useState<Met | null>(null);
  const [riskD, setRiskD] = useState<{ name: string; value: number }[]>([]);
  const [rigP, setRigP] = useState<{ rig: string; progress: number; count: number }[]>([]);
  const [feat, setFeat] = useState<{ feature: string; importance: number }[]>([]);
  const [wells, setWells] = useState<Well[]>([]);
  const [total, setTotal] = useState(0);
  const [crit, setCrit] = useState(0);
  const [hiR, setHiR] = useState(0);
  const [ld, setLd] = useState(true);
  const [tier, setTier] = useState<string | null>(null);
  const [expW, setExpW] = useState<string | null>(null);
  const [sCol, setSCol] = useState('risk_score');
  const [sDir, setSDir] = useState<'asc' | 'desc'>('desc');
  const [is3D, setIs3D] = useState(false);
  const [lb, setLb] = useState<string | null>(null);
  const [showRiskInfo, setShowRiskInfo] = useState(false);
  const [radar, setRadar] = useState<any[]>([]);
  const [showStudio, setShowStudio] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [mR, rsR, fiR, pwR] = await Promise.all([
          fetch('/wmr_results/ag_metrics.json'), fetch('/wmr_results/risk_scores.csv'),
          fetch('/wmr_results/feature_importance.csv'), fetch('/wmr_results/priority_wells_final.csv'),
        ]);
        setMet(await mR.json());
        const rs = csv(await rsR.text()); setTotal(rs.length);
        const tc: Record<string, number> = {}, rm: Record<string, { s: number; n: number }> = {};
        let cr = 0, hr = 0;
        rs.forEach(r => {
          const t = r.risk_tier || 'UNKNOWN'; tc[t] = (tc[t] || 0) + 1;
          if (t === 'CRITICAL') cr++; if (t === 'HIGH_RISK') hr++;
          const rg = r.rig_no || 'UNK', p = parseFloat(r.over_all_progress_percentages || '0');
          if (!rm[rg]) rm[rg] = { s: 0, n: 0 }; rm[rg].s += p; rm[rg].n++;
        });
        setCrit(cr); setHiR(hr);
        setRiskD(['CRITICAL', 'HIGH_RISK', 'WATCH', 'HEALTHY'].filter(t => tc[t]).map(t => ({ name: t, value: tc[t] })));
        const ra = Object.entries(rm).map(([r, d]) => ({ rig: r, progress: Math.round((d.s / d.n) * 100), count: d.n })).sort((a, b) => b.progress - a.progress).slice(0, 12);
        setRigP(ra);
        setRadar(ra.slice(0, 6).map(r => ({ rig: r.rig, progress: r.progress, load: Math.min(r.count * 4, 100), eff: Math.min(r.progress * 1.2, 100) })));
        const fi = csv(await fiR.text());
        setFeat(fi.slice(0, 10).map(r => ({ feature: (r[''] || r['Unnamed: 0'] || Object.values(r)[0] || '').replace(/_/g, ' '), importance: parseFloat(r.importance || '0') })).filter(r => r.importance > 0));
        const pw = csv(await pwR.text());
        setWells(pw.map(r => ({
          pdo_well_id: r.pdo_well_id || '', well_name_after_spud: r.well_name_after_spud || '', project_name: r.project_name || '', rig_no: r.rig_no || '',
          well_type: r.well_type || '', current_progress_pct: parseFloat(r.current_progress_pct || '0'),
          risk_score: parseFloat(r.risk_score || '0'), risk_tier: r.risk_tier || '',
          predicted_completion_date: r.predicted_completion_date || '', weeks_remaining_predicted: parseFloat(r.weeks_remaining_predicted || '0'),
        })).filter(w => w.well_name_after_spud && w.risk_tier));
      } catch (e) { console.error(e); } finally { setLd(false); }
    })();
  }, []);

  const fw = tier ? wells.filter(w => w.risk_tier === tier) : wells;
  const sw = [...fw].sort((a, b) => {
    const av = (a as any)[sCol], bv = (b as any)[sCol];
    const na = typeof av === 'number' ? av : parseFloat(av) || 0;
    const nb = typeof bv === 'number' ? bv : parseFloat(bv) || 0;
    if (typeof av === 'string' && isNaN(na)) return sDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    return sDir === 'asc' ? na - nb : nb - na;
  });
  const ts = (col: string) => { if (sCol === col) setSDir(d => d === 'asc' ? 'desc' : 'asc'); else { setSCol(col); setSDir('desc'); } };
  const pd = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100].map(b => ({ range: `${b}%`, count: wells.filter(w => w.current_progress_pct >= b && w.current_progress_pct < b + 10).length }));

  if (ld) return (
    <div className="w-full h-full flex items-center justify-center" style={{ background: '#FFFFFF', fontFamily: '"Figtree", sans-serif' }}>
      <div className="flex flex-col items-center gap-6">
        <div className="relative w-12 h-12">
          <div className="absolute inset-0 border-2 rounded-full" style={{ borderColor: '#F0F0F0' }} />
          <div className="absolute inset-0 border-2 border-t-[#1A1A1A] rounded-full animate-spin" />
        </div>
        <div className="text-[11px] font-semibold tracking-[0.2em] uppercase" style={{ color: '#6B6B6B' }}>Loading...</div>
      </div>
    </div>
  );

  const f = (i: number) => ({ initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { delay: 0.04 * i, duration: 0.3 } });
  const barCol = (p: number) => p > 55 ? C.green : p > 35 ? C.gold : C.red;

  // === 3D PLOTLY DATA ===
  const meshBars3D = rigP.map((r, i) => meshBar(i, r.progress, barCol(r.progress), r.rig));
  const featBars3D = feat.map((ft, i) => meshBar(i, ft.importance * 1000, [C.orange, C.violet, C.green, C.gold, C.teal, C.red][i % 6], ft.feature, 0.3, 0.3));

  const scatter3D = {
    data: [{ type: 'scatter3d' as const, mode: 'markers' as const,
      x: rigP.map(r => r.progress), y: rigP.map(r => r.count), z: rigP.map((_, i) => (i + 1) * 8),
      text: rigP.map(r => `${r.rig}\n${r.progress}% avg\n${r.count} wells`),
      marker: { size: rigP.map(r => Math.max(r.count * 1.5, 4)), color: C.orange, opacity: 0.9 },
    }],
    layout: { ...pLay, height: 310, scene: { ...scene3D('Progress %', 'Wells', 'Index'), camera: { eye: { x: 1.5, y: 1.5, z: 0.7 } } }, margin: { l: 0, r: 0, t: 10, b: 0 } },
  };

  const surface3D = {
    data: [{ type: 'surface' as const, z: [pd.map(p => p.count), pd.map(p => p.count * 0.65), pd.map(p => p.count * 0.3)],
      color: C.orange, showscale: false,
      contours: { z: { show: true, usecolormap: false, highlightcolor: '#FFFFFF', project: { z: true } } },
    }],
    layout: { ...pLay, height: 310, scene: { ...scene3D('Bucket', 'Layer', 'Count'), camera: { eye: { x: 1.6, y: 1.3, z: 0.6 } } }, margin: { l: 0, r: 0, t: 10, b: 0 } },
  };

  // Hermes Bespoke Icons - Each uniquely tailored, hand-crafted feel
  // Like custom engravings on luxury goods - no two are the same language
  
  const IconPortfolio = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* 3D Oil Derrick - solid dark */}
      <path d="M12 1L6.5 9H17.5L12 1Z" fill="#1A1A1A"/>
      <path d="M12 1L6.5 9H12V1Z" fill="#2A2A2A"/>
      <path d="M7.5 9L12 23L16.5 9H7.5Z" fill="#1A1A1A"/>
      <path d="M7.5 9L12 23V9H7.5Z" fill="#333333"/>
      <rect x="6" y="8.5" width="12" height="1.5" rx="0.5" fill="#0A0A0A"/>
      <rect x="9" y="13" width="6" height="1" rx="0.3" fill="#0A0A0A" opacity="0.6"/>
      <rect x="10" y="17" width="4" height="1" rx="0.3" fill="#0A0A0A" opacity="0.4"/>
    </svg>
  );

  const IconCritical = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* 3D Lightning Bolt - solid dark */}
      <path d="M13 2L4.5 14H11L8.5 22L19.5 10H13L15 2H13Z" fill="#1A1A1A"/>
      <path d="M13 2L4.5 14H11L13 2Z" fill="#2A2A2A"/>
      <path d="M11 14L8.5 22L19.5 10H13L11 14Z" fill="#0A0A0A"/>
    </svg>
  );

  const IconAtRisk = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* 3D Hourglass - solid dark */}
      <rect x="5" y="1" width="14" height="2.5" rx="0.8" fill="#0A0A0A"/>
      <rect x="5" y="20.5" width="14" height="2.5" rx="0.8" fill="#0A0A0A"/>
      <path d="M7 3.5V7L12 12L17 7V3.5H7Z" fill="#1A1A1A"/>
      <path d="M7 3.5V7L12 12V3.5H7Z" fill="#2A2A2A"/>
      <path d="M7 20.5V17L12 12L17 17V20.5H7Z" fill="#1A1A1A"/>
      <path d="M12 12L17 17V20.5H12V12Z" fill="#333333"/>
      <circle cx="12" cy="17" r="1.5" fill="#444444"/>
    </svg>
  );

  const IconAccuracy = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* 3D Target / Crosshair - solid dark */}
      <circle cx="12" cy="12" r="10" fill="#1A1A1A"/>
      <circle cx="12" cy="12" r="7" fill="#2A2A2A"/>
      <circle cx="12" cy="12" r="4" fill="#1A1A1A"/>
      <circle cx="12" cy="12" r="1.8" fill="#444444"/>
      <rect x="11.25" y="1" width="1.5" height="4" rx="0.5" fill="#0A0A0A"/>
      <rect x="11.25" y="19" width="1.5" height="4" rx="0.5" fill="#0A0A0A"/>
      <rect x="1" y="11.25" width="4" height="1.5" rx="0.5" fill="#0A0A0A"/>
      <rect x="19" y="11.25" width="4" height="1.5" rx="0.5" fill="#0A0A0A"/>
    </svg>
  );

  const IconCIndex = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* 3D Pulse / Heartbeat line - solid dark */}
      <rect x="1" y="10.5" width="5" height="3" rx="1" fill="#1A1A1A"/>
      <rect x="18" y="10.5" width="5" height="3" rx="1" fill="#1A1A1A"/>
      <path d="M6 12L8.5 12L10 5L12.5 19L15 8L16.5 12L18 12" stroke="#1A1A1A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M6 12L8.5 12L10 5L12.5 19L15 8L16.5 12L18 12" stroke="#333333" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );

  return (
    <div className="w-full h-full overflow-y-auto relative" style={{ background: '#FFFFFF', fontFamily: '"Figtree", sans-serif' }}>
      <AnimatePresence>
        {showStudio && <SequelForecastStudio onClose={() => setShowStudio(false)} />}
      </AnimatePresence>
      <AnimatePresence>
        {lb && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.85)' }}
            onClick={() => setLb(null)}>
            <button onClick={() => setLb(null)} className="absolute top-6 right-6 w-10 h-10 flex items-center justify-center text-[18px] z-[101]"
              style={{ color: '#FFFFFF', background: '#1A1A1A', borderRadius: '4px' }}>✕</button>
            <motion.img initial={{ scale: 0.92 }} animate={{ scale: 1 }} exit={{ scale: 0.92 }}
              src={lb} alt="Chart" className="max-w-[90vw] max-h-[85vh] object-contain rounded-lg shadow-2xl"
              style={{ background: '#FFFFFF' }}
              onClick={e => e.stopPropagation()} />
          </motion.div>
        )}
      </AnimatePresence>

      <div className="max-w-[1400px] mx-auto px-10 py-8">
        {/* HEADER */}
        <motion.div {...f(0)} className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-[28px] font-semibold tracking-tight" style={{ color: '#1A1A1A' }}>Decision Studio</h1>
            <p className="text-[13px] mt-1 font-medium" style={{ color: '#6B6B6B' }}>{total} Wells · Predictive Intelligence · R² {((met?.r2 || 0) * 100).toFixed(1)}%</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => setShowStudio(true)} className="px-6 py-2.5 text-[10px] font-semibold tracking-[0.2em] transition-all uppercase rounded-md"
              style={{ background: '#E87722', color: '#FFFFFF' }}
              onMouseEnter={e => e.currentTarget.style.background = '#D76B1A'}
              onMouseLeave={e => e.currentTarget.style.background = '#E87722'}
            >
              SEQUELFORECAST
            </button>
            <div className="flex rounded-md overflow-hidden" style={{ border: '1px solid rgba(0,0,0,0.15)' }}>
              <button onClick={() => setIs3D(false)} className="px-4 py-2 text-[11px] font-semibold transition-all"
                style={{ background: !is3D ? '#1A1A1A' : '#FFFFFF', color: !is3D ? '#FFFFFF' : '#1A1A1A' }}>2D</button>
              <button onClick={() => setIs3D(true)} className="px-4 py-2 text-[11px] font-semibold transition-all"
                style={{ background: is3D ? '#1A1A1A' : '#FFFFFF', color: is3D ? '#FFFFFF' : '#1A1A1A' }}>3D</button>
            </div>
            {tier && <button onClick={() => setTier(null)} className="px-4 py-2 text-[10px] font-semibold tracking-wider uppercase rounded-md"
              style={{ border: '1px solid rgba(0,0,0,0.15)', color: '#1A1A1A', background: '#FFFFFF' }}>✕ Clear {TIERS[tier]?.l}</button>}
          </div>
        </motion.div>

        {/* KPIs - Premium Cards with Tailored Icons */}
        <div className="grid grid-cols-5 gap-4 mb-8">
          {[
            { l: 'Portfolio', v: total, d: 0, s: '', sub: 'Total wells', c: '#2563EB', bg: '#EFF6FF', Icon: IconPortfolio },
            { l: 'Critical', v: crit, d: 0, s: '', sub: 'Immediate action', c: '#DC2626', bg: '#FEF2F2', Icon: IconCritical },
            { l: 'At Risk', v: hiR, d: 0, s: '', sub: 'Below target', c: '#D97706', bg: '#FFFBEB', Icon: IconAtRisk },
            { l: 'Accuracy', v: (met?.r2 || 0) * 100, d: 1, s: '%', sub: 'R² 4-week lead', c: '#16A34A', bg: '#F0FDF4', Icon: IconAccuracy },
            { l: 'C-Index', v: 0.993, d: 3, s: '', sub: 'Survival model', c: '#7C3AED', bg: '#F5F3FF', Icon: IconCIndex },
          ].map((k, i) => (
            <motion.div 
              key={k.l} 
              {...f(i + 1)} 
              className="p-5 transition-all duration-200 cursor-default"
              style={{ 
                background: '#FFFFFF', 
                borderRadius: '12px',
                border: '1px solid #E5E5E5',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
              }}
              onMouseEnter={e => { 
                (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)'; 
              }}
              onMouseLeave={e => { 
                (e.currentTarget as HTMLElement).style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)'; 
              }}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 flex items-center justify-center">
                  <k.Icon />
                </div>
                <span className="text-[11px] font-semibold tracking-[0.05em] uppercase" style={{ color: '#6B6B6B' }}>
                  <Info term={k.l} ctx={k.sub}>{k.l}</Info>
                </span>
              </div>
              <div className="text-[28px] font-bold tabular-nums leading-none mb-1.5" style={{ color: '#1A1A1A' }}>
                <CountUp to={k.v} d={k.d} s={k.s} />
              </div>
              <div className="text-[11px]" style={{ color: '#9A9A9A' }}>{k.sub}</div>
            </motion.div>
          ))}
        </div>

        {/* ROW 2 - Charts */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {/* Risk */}
          <motion.div {...f(6)} className="p-6" style={{ background: '#FFFFFF', borderRadius: '12px', border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <div className="text-[10px] font-semibold tracking-[0.08em] uppercase mb-1" style={{ color: '#6B6B6B' }}><Info term="Risk Distribution">Risk Distribution</Info></div>
            <div className="text-[11px] font-medium mb-4" style={{ color: '#9A9A9A' }}>Click segment to filter</div>
            {is3D ? (
              <Plot data={[{ type: 'pie' as const, labels: riskD.map(d => TIERS[d.name]?.l || d.name), values: riskD.map(d => d.value),
                marker: { colors: riskD.map(d => TIERS[d.name]?.c || C.t4) }, hole: 0.4, pull: riskD.map(d => tier === d.name ? 0.1 : 0.03),
                textinfo: 'label+percent' as const, textfont: { color: '#fff', size: 11, family: 'monospace' },
                rotation: 45, direction: 'clockwise' as const,
              }]} layout={{ ...pLay, height: 260, margin: { l: 10, r: 10, t: 10, b: 10 } }} config={pCfg} style={{ width: '100%' }} />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart><Pie data={riskD} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={2} strokeWidth={0}
                  onClick={(_, i) => { const t = riskD[i]?.name; setTier(p => p === t ? null : t); }} style={{ cursor: 'pointer' }}>
                  {riskD.map(e => <Cell key={e.name} fill={TIERS[e.name]?.c || C.t4} opacity={tier && tier !== e.name ? 0.25 : 1}
                    stroke={tier === e.name ? C.t1 : 'transparent'} strokeWidth={tier === e.name ? 2 : 0} />)}
                </Pie><Tooltip contentStyle={{ background: C.card, border: `1px solid ${C.borderHi}`, fontSize: '11px', fontFamily: 'monospace', borderRadius: '6px' }}
                  formatter={(v: any, n: any) => [`${v} wells`, TIERS[n]?.l || n]} /></PieChart>
              </ResponsiveContainer>
            )}
            <div className="grid grid-cols-2 gap-y-2 gap-x-4 mt-3">
              {riskD.map(d => (
                <button key={d.name} onClick={() => setTier(p => p === d.name ? null : d.name)}
                  className="flex items-center gap-2 px-2 py-1 rounded transition-opacity"
                  style={{ opacity: tier && tier !== d.name ? 0.3 : 1 }}>
                  <div className="w-2.5 h-2.5 rounded-sm" style={{ background: TIERS[d.name]?.c }} />
                  <span className="text-[10px] font-mono" style={{ color: C.t2 }}>{TIERS[d.name]?.l} ({d.value})</span>
                </button>
              ))}
            </div>
          </motion.div>

          {/* Progress */}
          <motion.div {...f(7)} className="p-6" style={{ background: '#FFFFFF', borderRadius: '12px', border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <div className="text-[10px] font-semibold tracking-[0.08em] uppercase mb-4" style={{ color: '#6B6B6B' }}><Info term="Progress Distribution">Progress Distribution</Info></div>
            {is3D ? <Plot {...surface3D} config={pCfg} style={{ width: '100%' }} /> : (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={pd} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} /><XAxis dataKey="range" tick={{ fill: C.t3, fontSize: 9, fontFamily: 'monospace' }} axisLine={{ stroke: C.border }} />
                  <YAxis tick={{ fill: C.t3, fontSize: 9, fontFamily: 'monospace' }} axisLine={false} />
                  <Tooltip contentStyle={{ background: C.card, border: `1px solid ${C.borderHi}`, fontSize: '11px', fontFamily: 'monospace', borderRadius: '6px' }} />
                  <Area type="monotone" dataKey="count" stroke={C.orange} strokeWidth={2} fill={C.orange} fillOpacity={0.15} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </motion.div>

          {/* Rig 3D Scatter / Radar */}
          <motion.div {...f(8)} className="p-6" style={{ background: '#FFFFFF', borderRadius: '12px', border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <div className="text-[10px] font-semibold tracking-[0.08em] uppercase mb-4" style={{ color: '#6B6B6B' }}>
              <Info term="Rig Profile">{is3D ? 'Rig 3D Scatter' : 'Rig Capability Radar'}</Info>
            </div>
            {is3D ? <Plot {...scatter3D} config={pCfg} style={{ width: '100%' }} /> : (
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radar}><PolarGrid stroke={C.border} /><PolarAngleAxis dataKey="rig" tick={{ fill: C.t3, fontSize: 8, fontFamily: 'monospace' }} />
                  <PolarRadiusAxis tick={false} axisLine={false} domain={[0, 100]} />
                  <Radar name="Progress" dataKey="progress" stroke={C.orange} fill={C.orange} fillOpacity={0.2} strokeWidth={2} />
                  <Radar name="Efficiency" dataKey="eff" stroke={C.green} fill={C.green} fillOpacity={0.1} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            )}
          </motion.div>
        </div>

        {/* RIG FLEET */}
        <motion.div {...f(9)} className="mb-6 p-6" style={{ background: '#FFFFFF', borderRadius: '12px', border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
          <div className="text-[10px] font-semibold tracking-[0.08em] uppercase mb-4" style={{ color: '#6B6B6B' }}><Info term="Rig Fleet Performance">Rig Fleet Performance</Info></div>
          {is3D ? (
            <Plot data={meshBars3D as any} layout={{ ...pLay, height: 350,
              scene: { ...scene3D('Rig', 'Depth', 'Progress %'), camera: { eye: { x: 1.8, y: 1.2, z: 0.8 } },
                xaxis: { ...scene3D('', '', '').xaxis, tickvals: rigP.map((_, i) => i), ticktext: rigP.map(r => r.rig) } },
              margin: { l: 0, r: 0, t: 10, b: 0 },
            }} config={pCfg} style={{ width: '100%' }} />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={rigP} layout="vertical" margin={{ left: 10, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: C.t3, fontSize: 9, fontFamily: 'monospace' }} axisLine={{ stroke: C.border }} tickFormatter={v => `${v}%`} />
                <YAxis type="category" dataKey="rig" tick={{ fill: C.t2, fontSize: 9, fontFamily: 'monospace' }} axisLine={false} width={80} />
                <Tooltip contentStyle={{ background: C.card, border: `1px solid ${C.borderHi}`, fontSize: '11px', fontFamily: 'monospace', borderRadius: '6px' }}
                  formatter={(v: any, _: any, p: any) => [`${v}% (${p.payload.count} wells)`, 'Completion']} />
                <Bar dataKey="progress" radius={[0, 4, 4, 0]}>{rigP.map(e => <Cell key={e.rig} fill={barCol(e.progress)} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* WELLS TABLE */}
        <motion.div {...f(10)} className="mb-6" style={{ background: '#FFFFFF', borderRadius: '12px', border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
          <div className="p-6 pb-3">
            <div className="text-[10px] font-semibold tracking-[0.08em] uppercase" style={{ color: '#6B6B6B' }}>
              Priority Wells {tier && <span style={{ color: TIERS[tier]?.c }}> — {TIERS[tier]?.l}</span>}
            </div>
            <div className="text-[11px] font-medium mt-1" style={{ color: '#9A9A9A' }}>{sw.length} entities · Click to expand</div>
          </div>
          <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 z-10">
                <tr style={{ background: C.surface }}>
                  {[{ k: 'pdo_well_id', l: 'ID' }, { k: 'well_name_after_spud', l: 'Well Name' }, { k: 'rig_no', l: 'Rig' }, { k: 'well_type', l: 'Type' }, { k: 'current_progress_pct', l: 'Progress' },
                    { k: 'risk_score', l: 'Risk Score', tooltip: true }, { k: 'risk_tier', l: 'Classification' }, { k: 'weeks_remaining_predicted', l: 'Est. Weeks' }].map(col => (
                    <th key={col.k} onClick={() => col.tooltip ? null : ts(col.k)} className={`px-4 py-3 text-left select-none relative ${col.tooltip ? '' : 'cursor-pointer'}`}
                      style={{ fontSize: '8px', fontFamily: 'monospace', letterSpacing: '0.15em', textTransform: 'uppercase' as const,
                        color: sCol === col.k ? C.blue : C.t3, borderBottom: `1px solid ${C.border}` }}>
                      <div className="flex items-center gap-1">
                        <span>{col.l}</span>
                        {col.tooltip && (
                          <span 
                            onMouseEnter={() => setShowRiskInfo(true)}
                            onMouseLeave={() => setShowRiskInfo(false)}
                            className="ml-1 px-1 text-[9px] font-mono cursor-help"
                            style={{ color: C.t3, border: `1px solid ${C.t3}`, borderRadius: '2px' }}
                          >
                            i
                          </span>
                        )}
                        {!col.tooltip && sCol === col.k && <span className="ml-1">{sDir === 'desc' ? 'v' : '^'}</span>}
                      </div>
                      {col.tooltip && showRiskInfo && (
                        <div className="absolute z-50 mt-2 w-72 p-3 border"
                          style={{ 
                            background: '#FFFFFF', 
                            borderColor: C.border,
                          }}
                          onMouseEnter={() => setShowRiskInfo(true)}
                          onMouseLeave={() => setShowRiskInfo(false)}
                        >
                          <div className="text-[10px] font-mono uppercase tracking-wider pb-2 mb-2" style={{ color: C.t1, borderBottom: `1px solid ${C.border}` }}>
                            Risk Score Calculation
                          </div>
                          <div className="space-y-1 text-[9px] font-mono" style={{ color: C.t2 }}>
                            <p className="mb-2">Composite score 0-100 from 4 factors:</p>
                            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                              <div className="flex justify-between">
                                <span style={{ color: C.t3 }}>Progress</span>
                                <span style={{ color: C.t1 }}>35%</span>
                              </div>
                              <div className="flex justify-between">
                                <span style={{ color: C.t3 }}>Velocity</span>
                                <span style={{ color: C.t1 }}>25%</span>
                              </div>
                              <div className="flex justify-between">
                                <span style={{ color: C.t3 }}>Schedule</span>
                                <span style={{ color: C.t1 }}>20%</span>
                              </div>
                              <div className="flex justify-between">
                                <span style={{ color: C.t3 }}>Gap</span>
                                <span style={{ color: C.t1 }}>20%</span>
                              </div>
                            </div>
                            <div className="mt-2 pt-2" style={{ borderTop: `1px solid ${C.border}` }}>
                              <p style={{ color: C.t3 }}>Tiers: CRITICAL 75-100 / HIGH 50-75 / WATCH 25-50 / HEALTHY 0-25</p>
                            </div>
                          </div>
                        </div>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sw.slice(0, 60).map((w, i) => {
                  const tc = TIERS[w.risk_tier] || { c: C.t4, l: w.risk_tier };
                  return (
                    <tr key={`${w.well_name_after_spud}-${i}`} onClick={() => setExpW(expW === w.well_name_after_spud ? null : w.well_name_after_spud)}
                      className="cursor-pointer transition-colors" style={{ borderBottom: `1px solid ${C.border}`, background: expW === w.well_name_after_spud ? C.cardHover : 'transparent' }}
                      onMouseEnter={e => { if (expW !== w.well_name_after_spud) (e.currentTarget as HTMLElement).style.background = C.surface; }}
                      onMouseLeave={e => { if (expW !== w.well_name_after_spud) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}>
                      <td className="px-4 py-3 text-[10px] font-mono text-[#6B7280]" style={{ color: C.t3 }}>{w.pdo_well_id}</td>
                      <td className="px-4 py-3 text-[11px] font-mono max-w-[180px] truncate" style={{ color: C.t1 }}>{w.well_name_after_spud}</td>
                      <td className="px-4 py-3 text-[11px] font-mono" style={{ color: C.t2 }}>{w.rig_no}</td>
                      <td className="px-4 py-3 text-[10px] font-mono" style={{ color: C.t3 }}>{w.well_type}</td>
                      <td className="px-4 py-3"><div className="flex items-center gap-2">
                        <div className="w-16 h-2 rounded-full overflow-hidden" style={{ background: C.border }}>
                          <div className="h-full rounded-full" style={{ width: `${Math.min(w.current_progress_pct, 100)}%`, background: barCol(w.current_progress_pct) }} /></div>
                        <span className="text-[10px] font-mono tabular-nums" style={{ color: C.t2 }}>{w.current_progress_pct.toFixed(0)}%</span></div></td>
                      <td className="px-4 py-3 text-[11px] font-mono font-medium tabular-nums" style={{ color: tc.c }}>{w.risk_score.toFixed(1)}</td>
                      <td className="px-4 py-3"><span className="px-2.5 py-1 text-[8px] font-mono tracking-wider uppercase rounded"
                        style={{ color: tc.c, border: `1px solid ${tc.c}40`, background: `${tc.c}10` }}>{tc.l}</span></td>
                      <td className="px-4 py-3 text-[11px] font-mono tabular-nums" style={{ color: C.t2 }}>{w.weeks_remaining_predicted > 0 ? `${w.weeks_remaining_predicted.toFixed(0)}w` : '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* ML INTELLIGENCE */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <motion.div {...f(12)} className="p-6" style={{ background: '#FFFFFF', borderRadius: '12px', border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <div className="text-[10px] font-semibold tracking-[0.08em] uppercase mb-1" style={{ color: '#6B6B6B' }}><Info term="Feature Importance">Predictive Drivers</Info></div>
            <div className="text-[11px] font-medium mb-4" style={{ color: '#9A9A9A' }}>AutoGluon permutation importance</div>
            {is3D ? (
              <Plot data={featBars3D as any} layout={{ ...pLay, height: 340,
                scene: { ...scene3D('Feature', 'Depth', 'Importance'), camera: { eye: { x: 1.6, y: 1.4, z: 0.8 } },
                  xaxis: { ...scene3D('', '', '').xaxis, tickvals: feat.map((_, i) => i), ticktext: feat.map(ft => ft.feature.slice(0, 12)) } },
                margin: { l: 0, r: 0, t: 10, b: 0 },
              }} config={pCfg} style={{ width: '100%' }} />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={feat} layout="vertical" margin={{ left: 20, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} horizontal={false} />
                  <XAxis type="number" tick={{ fill: C.t3, fontSize: 9, fontFamily: 'monospace' }} axisLine={{ stroke: C.border }} />
                  <YAxis type="category" dataKey="feature" tick={{ fill: C.t2, fontSize: 8, fontFamily: 'monospace' }} axisLine={false} width={120} />
                  <Tooltip contentStyle={{ background: C.card, border: `1px solid ${C.borderHi}`, fontSize: '11px', fontFamily: 'monospace', borderRadius: '6px' }} />
                  <Bar dataKey="importance" fill={C.orange} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </motion.div>

          <motion.div {...f(13)} className="p-6" style={{ background: '#FFFFFF', borderRadius: '12px', border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <div className="text-[10px] font-semibold tracking-[0.08em] uppercase mb-1" style={{ color: '#6B6B6B' }}><Info term="SHAP Beeswarm">SHAP Analysis</Info></div>
            <div className="text-[11px] font-medium mb-4" style={{ color: '#9A9A9A' }}>Variable impact direction</div>
            <div className="overflow-hidden cursor-pointer rounded-lg" style={{ background: '#FAFAFA' }} onClick={() => setLb('/wmr_results/shap_beeswarm.png')}>
              <img src="/wmr_results/shap_beeswarm.png" alt="SHAP" className="w-full h-auto max-h-[300px] object-contain hover:opacity-90 transition-opacity" /></div>
          </motion.div>
        </div>

        {/* SURVIVAL */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {[{ src: 'survival_kaplan_meier', t: 'Kaplan-Meier Curve', l: 'Completion Probability', d: 'Survival by rig tier', i: 14 },
            { src: 'completion_forecast', t: 'Completion Forecast', l: 'Timeline Forecast', d: '80% confidence intervals', i: 15 }].map(ch => (
            <motion.div key={ch.src} {...f(ch.i)} className="p-6" style={{ background: '#FFFFFF', borderRadius: '12px', border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
              <div className="text-[10px] font-semibold tracking-[0.08em] uppercase mb-1" style={{ color: '#6B6B6B' }}><Info term={ch.t}>{ch.l}</Info></div>
              <div className="text-[11px] font-medium mb-4" style={{ color: '#9A9A9A' }}>{ch.d}</div>
              <div className="overflow-hidden cursor-pointer rounded-lg" style={{ background: '#FAFAFA' }} onClick={() => setLb(`/wmr_results/${ch.src}.png`)}>
                <img src={`/wmr_results/${ch.src}.png`} alt={ch.l} className="w-full h-auto hover:opacity-90 transition-opacity" /></div>
            </motion.div>
          ))}
        </div>

        {/* MODEL DIAG */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <motion.div {...f(16)} className="p-6" style={{ background: '#FFFFFF', borderRadius: '12px', border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <div className="text-[10px] font-semibold tracking-[0.08em] uppercase mb-1" style={{ color: '#6B6B6B' }}><Info term="Model Diagnostics">Model Accuracy</Info></div>
            <div className="flex gap-8 my-4">
              {met && [{ l: 'RMSE', v: met.rmse.toFixed(4), c: '#E87722' }, { l: 'MAE', v: met.mae.toFixed(4), c: '#0D9488' }, { l: 'R²', v: met.r2.toFixed(4), c: '#16A34A' }, { l: 'MAPE', v: `${met.mape_valid.toFixed(1)}%`, c: '#7C3AED' }].map(m => (
                <div key={m.l}><div className="text-[9px] font-semibold tracking-widest uppercase" style={{ color: '#9A9A9A' }}><Info term={m.l}>{m.l}</Info></div>
                  <div className="text-[18px] font-semibold mt-1 tabular-nums" style={{ color: m.c }}>{m.v}</div></div>))}
            </div>
            <div className="overflow-hidden cursor-pointer rounded-lg" style={{ background: '#FAFAFA' }} onClick={() => setLb('/wmr_results/ag_diagnostics.png')}>
              <img src="/wmr_results/ag_diagnostics.png" alt="Diag" className="w-full h-auto hover:opacity-90 transition-opacity" /></div>
          </motion.div>

          <motion.div {...f(17)} className="p-6" style={{ background: '#FFFFFF', borderRadius: '12px', border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <div className="text-[10px] font-semibold tracking-[0.08em] uppercase mb-1" style={{ color: '#6B6B6B' }}><Info term="Cox Proportional Hazards">Completion Drivers</Info></div>
            <div className="text-[11px] font-medium mb-4" style={{ color: '#9A9A9A' }}>Factors accelerating or delaying completion</div>
            <div className="overflow-hidden cursor-pointer rounded-lg" style={{ background: '#FAFAFA' }} onClick={() => setLb('/wmr_results/survival_cox_hazard.png')}>
              <img src="/wmr_results/survival_cox_hazard.png" alt="Cox" className="w-full h-auto hover:opacity-90 transition-opacity" /></div>
          </motion.div>
        </div>

        <div className="py-8 flex items-center gap-4">
          <div className="h-px flex-1" style={{ background: 'rgba(0,0,0,0.08)' }} />
          <span className="text-[9px] font-semibold tracking-[0.2em] uppercase" style={{ color: '#9A9A9A' }}>SequelForecast Engine · Institutional Intelligence</span>
          <div className="h-px flex-1" style={{ background: 'rgba(0,0,0,0.08)' }} />
        </div>
      </div>
    </div>
  );
}
