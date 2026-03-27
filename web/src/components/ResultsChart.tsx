// @ts-nocheck
'use client';
import dynamic from 'next/dynamic';
import React, { useMemo, useState } from 'react';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });
const ThreeKPI = dynamic(() => import('@/components/ThreeKPI'), { ssr: false });

// ═══════════════════════════════════════════════════════════════════════════
// PALANTIR FOUNDRY / BLOOMBERG TERMINAL — DATA INTELLIGENCE ENGINE
// ═══════════════════════════════════════════════════════════════════════════
// Philosophy: "Data dictates form. Every pixel must earn its place."
//
// This is NOT a chart renderer. This is a Decision Intelligence Surface.
// Every visualization must answer: "So what? What do I do next?"
//
// The system ANALYZES data before rendering. If data cannot be charted
// meaningfully, it renders a Palantir-style Insight Table instead —
// with grouping, in-cell sparklines, and interactive drill-downs.
// ═══════════════════════════════════════════════════════════════════════════

interface ResultsChartProps {
  chartType?: string;
  columns?: string[];
  rows?: any[][];
  theme?: 'light' | 'dark';
  onDrillDown?: (value: string) => void;
}

// ── Palantir Design Tokens ──────────────────────────────────────────────
const P = {
  // Monochrome foundation
  black: '#0A0A0A',
  t1: '#1A1A1A',
  t2: '#4A4A4A',
  t3: '#6B6B6B',
  t4: '#9A9A9A',
  t5: '#B0B0B0',
  border: '#E5E5E5',
  surface: '#FAFAFA',
  card: '#FFFFFF',
  // Accent palette — used SPARINGLY for semantic meaning
  orange: '#E87722',   // Al Tasnim brand — primary action
  green: '#16A34A',    // Healthy / On Track
  red: '#DC2626',      // Critical / Alert
  gold: '#B8860B',     // Warning / Watch
  blue: '#2563EB',     // Info / Neutral KPI
  violet: '#7C3AED',   // Model / AI metrics
  teal: '#0D9488',     // Completion / Success
};

// Chart palette — premium, vibrant, distinct, corporate
const CHART_COLORS = [
  '#E87722', '#2563EB', '#16A34A', '#7C3AED', '#0D9488',
  '#DC2626', '#B8860B', '#6366F1', '#0891B2', '#C026D3',
];

// Progress gradient — per-bar color based on value (0-100%)
function getBarColor(value: number, isProgress: boolean, index: number = 0): string {
  if (!isProgress) return CHART_COLORS[index % CHART_COLORS.length];
  if (value >= 90) return '#059669';  // Emerald
  if (value >= 70) return '#16A34A';  // Green
  if (value >= 50) return '#B8860B';  // Gold
  if (value >= 30) return '#D97706';  // Amber
  if (value >= 10) return '#EA580C';  // Orange
  return '#DC2626';                   // Red — stalled/zero
}

// Detect if two columns are effectively identical (all values equal)
function columnsAreIdentical(rows: any[][], idxA: number, idxB: number): boolean {
  if (rows.length === 0) return false;
  const sample = rows.slice(0, Math.min(rows.length, 50));
  return sample.every(r => {
    const a = parseFloat(r[idxA]) || 0;
    const b = parseFloat(r[idxB]) || 0;
    return Math.abs(a - b) < 0.0001;
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SECTION 1: DATA INTELLIGENCE — Column Analysis Engine
// ═══════════════════════════════════════════════════════════════════════════

type ColumnType = 'numeric' | 'percentage' | 'categorical' | 'identifier' | 'date';

interface ColumnAnalysis {
  name: string;
  displayName: string;
  type: ColumnType;
  index: number;
  numericRatio: number;       // % of values that are parseable numbers
  uniqueCount: number;
  isIdColumn: boolean;
  isProgressColumn: boolean;
  sampleValues: any[];
}

interface DataProfile {
  columns: ColumnAnalysis[];
  labelColumn: ColumnAnalysis | null;      // Best column for axis labels (categorical/name)
  valueColumns: ColumnAnalysis[];           // Numeric columns suitable for charting
  idColumn: ColumnAnalysis | null;          // ID column (for drill-down, never on axis)
  groupColumn: ColumnAnalysis | null;       // Best column for grouping (cluster, type, etc.)
  isChartable: boolean;                     // Can this data be meaningfully charted?
  bestChartType: string;                    // What the DATA says is best
  suitableChartTypes: string[];             // All chart types that make sense
  rowCount: number;
}

// ID column patterns — these should NEVER be on a numeric axis
const ID_PATTERNS = [
  /^pdo_well_id$/i, /well_?id$/i, /^id$/i, /^uid$/i, /_id$/i,
  /^scr_no$/i, /^rig_no$/i, /^crew_uid$/i, /^well_?location$/i,
  /project_?id$/i, /^wbs_/i, /^sap_/i, /employee_?id$/i,
];

// Label-friendly columns — prefer these for axis labels
const LABEL_PATTERNS = [
  /well_name/i, /project_name/i, /ph_name/i, /crew_name/i, 
  /rig_no$/i, /^cluster$/i, /well_type/i, /category/i,
  /^name$/i, /description/i, /contractor/i, /operator/i,
];

// Group-friendly columns — for Insight Table grouping
const GROUP_PATTERNS = [
  /^cluster$/i, /well_type/i, /^category$/i, /risk_tier/i,
  /^status$/i, /well_status/i, /^type$/i, /^rig_no$/i,
];

// Progress/percentage columns — need 0-1 → 0-100 conversion
const PROGRESS_PATTERNS = [
  /progress/i, /pct$/i, /percent/i, /completion/i,
  /^r2$/i, /accuracy/i, /flowline.*progress/i,
];

// Date patterns
const DATE_PATTERNS = [
  /date/i, /^created/i, /^updated/i, /^timestamp/i,
  /spud_date/i, /rig_on_date/i, /rig_off_date/i,
];

function isDateValue(val: any): boolean {
  if (!val || typeof val !== 'string') return false;
  // ISO date pattern: 2024-01-15 or 2024-01-15T00:00:00
  return /^\d{4}-\d{2}-\d{2}/.test(val);
}

function analyzeColumns(columns: string[], rows: any[][]): DataProfile {
  const sampleSize = Math.min(rows.length, 50);
  const sampleRows = rows.slice(0, sampleSize);

  const analyses: ColumnAnalysis[] = columns.map((col, idx) => {
    const values = sampleRows.map(r => r[idx]);
    const nonNull = values.filter(v => v !== null && v !== undefined && v !== '' && v !== 'NULL');
    
    // Count how many values are numeric
    let numericCount = 0;
    nonNull.forEach(v => {
      const n = parseFloat(v);
      if (!isNaN(n) && isFinite(n)) numericCount++;
    });
    const numericRatio = nonNull.length > 0 ? numericCount / nonNull.length : 0;

    // Unique values
    const uniqueSet = new Set(nonNull.map(String));
    
    // Column type detection
    const isId = ID_PATTERNS.some(p => p.test(col));
    const isProgress = PROGRESS_PATTERNS.some(p => p.test(col));
    const isDate = DATE_PATTERNS.some(p => p.test(col)) || 
                   (nonNull.length > 0 && nonNull.slice(0, 5).every(isDateValue));

    let type: ColumnType;
    if (isId) {
      type = 'identifier';
    } else if (isDate) {
      type = 'date';
    } else if (isProgress && numericRatio > 0.5) {
      type = 'percentage';
    } else if (numericRatio > 0.7 && !isId) {
      type = 'numeric';
    } else {
      type = 'categorical';
    }

    return {
      name: col,
      displayName: formatColumnName(col),
      type,
      index: idx,
      numericRatio,
      uniqueCount: uniqueSet.size,
      isIdColumn: isId,
      isProgressColumn: isProgress,
      sampleValues: nonNull.slice(0, 5),
    };
  });

  // Find best label column (categorical, preferring names)
  const labelCandidates = analyses.filter(a => 
    a.type === 'categorical' || a.type === 'identifier'
  );
  const labelColumn = labelCandidates.find(a => LABEL_PATTERNS.some(p => p.test(a.name)))
    || labelCandidates.find(a => a.type === 'categorical')
    || labelCandidates[0]
    || null;

  // Find value columns (numeric or percentage, not IDs)
  const valueColumns = analyses.filter(a => 
    (a.type === 'numeric' || a.type === 'percentage') && !a.isIdColumn
  );

  // Find ID column for drill-down
  const idColumn = analyses.find(a => a.type === 'identifier') || null;

  // Find group column
  const groupColumn = analyses.find(a => GROUP_PATTERNS.some(p => p.test(a.name))) || null;

  // Determine chartability and best chart type
  const isChartable = valueColumns.length > 0 && (labelColumn !== null || rows.length === 1);
  let bestChartType = 'data_table';
  const suitableTypes: string[] = ['data_table']; // Always available

  if (isChartable) {
    const hasTimeAxis = analyses.some(a => a.type === 'date');
    const rowCount = rows.length;

    if (rowCount === 1 && valueColumns.length <= 2) {
      bestChartType = 'glass_kpi';
      suitableTypes.push('glass_kpi');
    } else if (rowCount <= 1 && valueColumns.length > 2) {
      // CRITICAL FIX: Single-row with multiple metrics (planned vs actual)
      // This is a COMPARISON scenario — perfect for grouped bar
      // Transpose: metric names become X-axis labels, values become bar heights
      bestChartType = 'bar';
      suitableTypes.push('bar', 'horizontal_bar', 'donut', '3d_bar');
    } else if (hasTimeAxis && valueColumns.length >= 1) {
      bestChartType = 'area';
      suitableTypes.push('area', 'line', 'bar');
    } else if (valueColumns.length >= 2) {
      bestChartType = 'grouped_bar';
      suitableTypes.push('bar', 'grouped_bar', 'horizontal_bar');
      if (rowCount <= 30) suitableTypes.push('3d_bar');
    } else if (rowCount <= 8 && labelColumn) {
      bestChartType = 'donut';
      suitableTypes.push('donut', 'bar', 'horizontal_bar');
    } else if (rowCount <= 30) {
      bestChartType = 'horizontal_bar';
      suitableTypes.push('bar', 'horizontal_bar');
      if (rowCount <= 20) suitableTypes.push('donut', '3d_bar');
    } else {
      // Large dataset (30+ items) — horizontal bar is most readable
      bestChartType = 'horizontal_bar';
      suitableTypes.push('bar', 'horizontal_bar');
    }

    // Line/Area ONLY when there's a real date/time axis
    // NEVER for categorical data (well names, rig numbers)
    if (hasTimeAxis && !suitableTypes.includes('line')) {
      suitableTypes.push('line', 'area');
    }

    // Always allow 3d_bar if we have values and labels and reasonable row count
    if (rowCount <= 40 && !suitableTypes.includes('3d_bar') && (labelColumn || rowCount === 1)) {
      suitableTypes.push('3d_bar');
    }
  }

  return {
    columns: analyses,
    labelColumn,
    valueColumns,
    idColumn,
    groupColumn,
    isChartable,
    bestChartType,
    suitableChartTypes: [...new Set(suitableTypes)],
    rowCount: rows.length,
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// SECTION 2: FORMATTING UTILITIES
// ═══════════════════════════════════════════════════════════════════════════

function formatColumnName(name: string): string {
  return name
    .replace(/[\[\]]/g, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase());
}

function formatValue(value: any, col: ColumnAnalysis): string {
  if (value === null || value === undefined || value === 'NULL' || value === '') return '—';

  if (col.type === 'date') {
    try {
      const d = new Date(value);
      return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch { return String(value); }
  }

  // CRITICAL FIX: Ensure only PURE numeric strings are treated as numbers. 
  // parseFloat("30-MMHE") returns 30, which truncates the well name!
  const isNumericString = /^-?\d+(\.\d+)?$/.test(String(value).trim());
  const num = parseFloat(value);
  if (isNaN(num) || (!isNumericString && col.type !== 'numeric' && col.type !== 'percentage')) return String(value);

  if (col.type === 'percentage' || col.isProgressColumn) {
    const pct = num <= 1 && num >= 0 ? num * 100 : num;
    return `${pct.toFixed(1)}%`;
  }

  if (col.type === 'identifier') return String(value);

  // PRECISION FIX: Show exact values with commas — NEVER abbreviate
  // SSMS shows 1086535.97, we show 1,086,535.97 — NOT 1.1M
  if (Number.isInteger(num)) return num.toLocaleString('en-US');
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getNumericValue(value: any, col: ColumnAnalysis): number {
  if (value === null || value === undefined || value === 'NULL') return 0;
  const num = parseFloat(value);
  if (isNaN(num)) return 0;
  // Convert 0-1 progress to 0-100
  if (col.isProgressColumn && num <= 1 && num > 0) return num * 100;
  return num;
}

function getProgressColor(pct: number): string {
  if (pct >= 80) return P.green;
  if (pct >= 50) return P.gold;
  if (pct >= 20) return P.orange;
  return P.red;
}

// ═══════════════════════════════════════════════════════════════════════════
// SECTION 3: MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

export default function ResultsChart({
  chartType = 'data_table',
  columns = [],
  rows = [],
  theme = 'dark',
  onDrillDown,
}: ResultsChartProps) {

  // ── Step 1: Analyze the data ────────────────────────────────────────
  const profile = useMemo(() => analyzeColumns(columns, rows), [columns, rows]);
  
  // Effective chart type: use the one that makes sense for the data
  const requestedType = chartType.toLowerCase();
  const effectiveType = useMemo(() => {
    // If data isn't chartable and user picks a chart type, force table
    if (!profile.isChartable && requestedType !== 'data_table' && requestedType !== 'glass_kpi') {
      return 'data_table';
    }
    // GUARD: Line/Area on categorical data is MEANINGLESS → redirect to horizontal_bar
    if ((requestedType === 'line' || requestedType === 'area') && 
        !profile.columns.some(c => c.type === 'date')) {
      return profile.rowCount > 8 ? 'horizontal_bar' : 'bar';
    }
    // If requested type is suitable, use it
    if (profile.suitableChartTypes.includes(requestedType)) {
      return requestedType;
    }
    // Fall back to best type
    return profile.bestChartType;
  }, [requestedType, profile]);

  // ── Empty State ─────────────────────────────────────────────────────
  if (!columns.length || !rows.length) {
    return (
      <div className="h-full flex flex-col items-center justify-center" style={{ fontFamily: '"Figtree", sans-serif' }}>
        <div className="w-16 h-16 rounded-full flex items-center justify-center mb-4" style={{ background: P.surface, border: `1px solid ${P.border}` }}>
          <span className="text-[24px]" style={{ color: P.t4 }}>∅</span>
        </div>
        <span className="text-[13px] font-medium" style={{ color: P.t2 }}>No Data Returned</span>
        <span className="text-[11px] mt-1" style={{ color: P.t4 }}>The query executed successfully but produced no results.</span>
      </div>
    );
  }

  // ── KPI Rendering ───────────────────────────────────────────────────
  if (effectiveType === 'glass_kpi' || effectiveType === '3d_kpi') {
    const rawValue = rows[0] ? rows[0][0] : 'NULL';
    const col = profile.columns[0];
    const displayValue = col ? formatValue(rawValue, col) : String(rawValue);
    return (
      <ThreeKPI
        value={displayValue}
        label={formatColumnName(columns[0] || 'Metric')}
        mode={effectiveType as any}
        theme={theme}
      />
    );
  }

  // ── 3D Bar ──────────────────────────────────────────────────────────
  if (effectiveType === '3d_bar') {
    const ThreeCharts = dynamic(() => import('@/components/ThreeCharts'), { ssr: false });
    const reorderedCols: string[] = [];
    const reorderedRows: any[][] = [];
    
    if (rows.length === 1 && profile.valueColumns.length >= 2) {
      // SINGLE-ROW MULTI-METRIC: Transpose — each metric becomes a bar
      reorderedCols.push('Metric', 'Value');
      profile.valueColumns.forEach(vc => {
        const val = getNumericValue(rows[0][vc.index], vc);
        reorderedRows.push([vc.displayName, val]);
      });
    } else if (profile.labelColumn && profile.valueColumns.length > 0) {
      const labelIdx = profile.labelColumn.index;
      const valueIdx = profile.valueColumns[0].index;
      reorderedCols.push(profile.labelColumn.name, profile.valueColumns[0].name);
      rows.forEach(r => {
        const val = getNumericValue(r[valueIdx], profile.valueColumns[0]);
        reorderedRows.push([r[labelIdx], val]);
      });
    } else {
      return <InsightTable profile={profile} rows={rows} onDrillDown={onDrillDown} />;
    }
    return <ThreeCharts chartType={effectiveType} columns={reorderedCols} rows={reorderedRows} />;
  }

  // ── Data Table / Insight Table ──────────────────────────────────────
  if (effectiveType === 'data_table' || effectiveType.includes('table')) {
    return <InsightTable profile={profile} rows={rows} onDrillDown={onDrillDown} />;
  }

  // ── Plotly Charts ───────────────────────────────────────────────────
  return (
    <PlotlyChart
      profile={profile}
      rows={rows}
      chartType={effectiveType}
      theme={theme}
      onDrillDown={onDrillDown}
    />
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SECTION 4: PALANTIR INSIGHT TABLE
// ═══════════════════════════════════════════════════════════════════════════
// Not just a data dump — an interactive decision surface with:
// - Smart grouping by cluster/type/status
// - In-cell progress bars for percentage columns
// - Clickable rows for drill-down
// - Color-coded risk/status columns
// - Row numbering and count badges

function InsightTable({ profile, rows, onDrillDown }: {
  profile: DataProfile;
  rows: any[][];
  onDrillDown?: (value: string) => void;
}) {
  const [search, setSearch] = useState('');
  const [sortCol, setSortCol] = useState<number | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  // Filter rows by search
  const filteredRows = useMemo(() => {
    if (!search.trim()) return rows;
    const q = search.toLowerCase();
    return rows.filter(r => r.some((v: any) => String(v ?? '').toLowerCase().includes(q)));
  }, [rows, search]);

  // Sort
  const sortedRows = useMemo(() => {
    if (sortCol === null) return filteredRows;
    const col = profile.columns[sortCol];
    return [...filteredRows].sort((a, b) => {
      const va = a[sortCol], vb = b[sortCol];
      if (col.type === 'numeric' || col.type === 'percentage') {
        const na = parseFloat(va) || 0, nb = parseFloat(vb) || 0;
        return sortDir === 'asc' ? na - nb : nb - na;
      }
      return sortDir === 'asc'
        ? String(va ?? '').localeCompare(String(vb ?? ''))
        : String(vb ?? '').localeCompare(String(va ?? ''));
    });
  }, [filteredRows, sortCol, sortDir, profile]);

  const handleSort = (idx: number) => {
    if (sortCol === idx) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(idx); setSortDir('desc'); }
  };

  // Decide which column to use for drill-down click
  const drillCol = profile.idColumn || profile.labelColumn || profile.columns[0];

  return (
    <div className="w-full h-full flex flex-col overflow-hidden" style={{ background: P.card, borderRadius: '12px', border: `1px solid ${P.border}`, boxShadow: '0 1px 3px rgba(0,0,0,0.04)', fontFamily: '"Figtree", sans-serif' }}>
      
      {/* Header */}
      <div className="shrink-0 sticky top-0 z-20" style={{ background: P.t1, borderRadius: '12px 12px 0 0' }}>
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <h3 className="text-[12px] font-semibold tracking-wide uppercase" style={{ color: '#FFFFFF' }}>
              {profile.labelColumn ? profile.labelColumn.displayName : 'Query Results'}
            </h3>
            {profile.groupColumn && profile.groupColumn !== profile.labelColumn && (
              <span className="px-2 py-0.5 text-[9px] font-medium uppercase tracking-wider rounded" style={{ background: 'rgba(255,255,255,0.12)', color: 'rgba(255,255,255,0.7)' }}>
                by {profile.groupColumn.displayName}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[11px] font-medium" style={{ color: 'rgba(255,255,255,0.5)' }}>
              {filteredRows.length}{filteredRows.length !== rows.length ? ` of ${rows.length}` : ''} {rows.length === 1 ? 'record' : 'records'}
            </span>
          </div>
        </div>
        {/* Search Bar */}
        {rows.length > 5 && (
          <div className="px-6 pb-3">
            <input
              type="text"
              placeholder="Search across all columns..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full px-3 py-2 text-[12px] rounded-md outline-none"
              style={{ background: 'rgba(255,255,255,0.1)', color: '#FFFFFF', border: '1px solid rgba(255,255,255,0.1)' }}
            />
          </div>
        )}
      </div>

      {/* Column Headers */}
      <div className="shrink-0 flex items-center px-6 py-2.5 gap-1" style={{ background: P.surface, borderBottom: `1px solid ${P.border}` }}>
        <span className="w-10 text-[8px] font-semibold uppercase tracking-widest shrink-0" style={{ color: P.t4 }}>#</span>
        {profile.columns.map((col, i) => (
          <button
            key={col.name}
            onClick={() => handleSort(i)}
            className="flex-1 min-w-0 text-left flex items-center gap-1 cursor-pointer hover:opacity-80 transition-opacity"
          >
            <span className="text-[9px] font-semibold uppercase tracking-wider truncate" style={{ color: sortCol === i ? P.orange : P.t3 }}>
              {col.displayName}
            </span>
            {sortCol === i && (
              <span className="text-[8px]" style={{ color: P.orange }}>{sortDir === 'desc' ? '▼' : '▲'}</span>
            )}
            {col.type === 'percentage' && (
              <span className="text-[7px] px-1 rounded" style={{ background: `${P.green}15`, color: P.green }}>%</span>
            )}
          </button>
        ))}
      </div>

      {/* Rows */}
      <div className="flex-1 overflow-y-auto">
        {sortedRows.map((row, i) => (
          <div
            key={i}
            onClick={() => onDrillDown && drillCol && onDrillDown(String(row[drillCol.index]))}
            className="flex items-center px-6 py-3 gap-1 transition-colors cursor-pointer hover:bg-[#F8F8F8]"
            style={{ 
              background: i % 2 === 0 ? P.card : P.surface,
              borderBottom: '1px solid rgba(0,0,0,0.03)',
            }}
          >
            <span className="w-10 text-[10px] font-medium shrink-0 tabular-nums" style={{ color: P.t5 }}>
              {(i + 1).toString().padStart(2, '0')}
            </span>
            {profile.columns.map((col, j) => (
              <div key={col.name} className="flex-1 min-w-0 flex items-center gap-2">
                {(col.type === 'percentage' || col.isProgressColumn) && !isNaN(parseFloat(row[j])) ? (
                  // In-cell progress bar — Palantir signature
                  <div className="flex items-center gap-2 w-full">
                    <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: P.border }}>
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.min(getNumericValue(row[j], col), 100)}%`,
                          background: getProgressColor(getNumericValue(row[j], col)),
                        }}
                      />
                    </div>
                    <span className="text-[11px] font-medium tabular-nums shrink-0 w-12 text-right" style={{ color: P.t1 }}>
                      {formatValue(row[j], col)}
                    </span>
                  </div>
                ) : col.name.toLowerCase().includes('risk_tier') || col.name.toLowerCase().includes('status') ? (
                  // Status badge
                  <span className="px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider rounded" style={{
                    color: String(row[j] ?? '').toUpperCase().includes('CRITICAL') ? P.red
                         : String(row[j] ?? '').toUpperCase().includes('HIGH') ? P.orange
                         : String(row[j] ?? '').toUpperCase().includes('WATCH') ? P.gold
                         : String(row[j] ?? '').toUpperCase().includes('HEALTHY') ? P.green
                         : P.t2,
                    background: String(row[j] ?? '').toUpperCase().includes('CRITICAL') ? `${P.red}12`
                              : String(row[j] ?? '').toUpperCase().includes('HIGH') ? `${P.orange}12`
                              : String(row[j] ?? '').toUpperCase().includes('WATCH') ? `${P.gold}12`
                              : String(row[j] ?? '').toUpperCase().includes('HEALTHY') ? `${P.green}12`
                              : `${P.t4}15`,
                    border: `1px solid ${
                      String(row[j] ?? '').toUpperCase().includes('CRITICAL') ? `${P.red}30`
                    : String(row[j] ?? '').toUpperCase().includes('HIGH') ? `${P.orange}30`
                    : String(row[j] ?? '').toUpperCase().includes('WATCH') ? `${P.gold}30`
                    : String(row[j] ?? '').toUpperCase().includes('HEALTHY') ? `${P.green}30`
                    : `${P.t4}20`
                    }`,
                  }}>
                    {String(row[j] ?? '—')}
                  </span>
                ) : (
                  <span className="text-[12px] truncate" style={{ 
                    color: j === 0 || col === profile.labelColumn ? P.t1 : P.t2,
                    fontWeight: j === 0 || col === profile.labelColumn ? 500 : 400,
                  }}>
                    {formatValue(row[j], col)}
                  </span>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="shrink-0 px-6 py-3 flex items-center justify-between" style={{ background: P.surface, borderRadius: '0 0 12px 12px', borderTop: `1px solid ${P.border}` }}>
        <span className="text-[11px] font-medium" style={{ color: P.t3 }}>
          {filteredRows.length} entries {profile.valueColumns.length > 0 && `· ${profile.valueColumns.length} metric${profile.valueColumns.length > 1 ? 's' : ''}`}
        </span>
        <div className="flex items-center gap-3">
          {onDrillDown && (
            <span className="text-[10px] font-medium" style={{ color: P.t4 }}>Click row to drill down</span>
          )}
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: P.green }} />
            <span className="text-[10px] font-medium" style={{ color: P.t3 }}>Live</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SECTION 5: PLOTLY CHART RENDERER — Bloomberg Terminal Quality
// ═══════════════════════════════════════════════════════════════════════════

function PlotlyChart({ profile, rows, chartType, theme, onDrillDown }: {
  profile: DataProfile;
  rows: any[][];
  chartType: string;
  theme: string;
  onDrillDown?: (value: string) => void;
}) {
  const isLight = theme === 'light';
  const label = profile.labelColumn;
  const values = profile.valueColumns;

  // ═══ SINGLE-ROW MULTI-METRIC TRANSPOSE ═══
  // Example: 1 row with [cluster_name, well_count, total_planned, total_actual, achievement_rate]
  // Transpose → metric names on X-axis, their values as bar heights
  if (rows.length === 1 && values.length >= 2) {
    const metricLabels = values.map(v => v.displayName);
    const metricValues = values.map(v => getNumericValue(rows[0][v.index], v));
    const metricColors = values.map((v, i) => CHART_COLORS[i % CHART_COLORS.length]);

    const traces: any[] = [];

    if (chartType === 'donut' || chartType === 'pie') {
      traces.push({
        type: 'pie', labels: metricLabels, values: metricValues, hole: 0.55,
        textinfo: 'label+value', textfont: { color: '#FFFFFF', size: 11, family: '"Figtree", system-ui' },
        marker: { colors: metricColors, line: { color: '#FFFFFF', width: 2 } },
      });
    } else {
      const isHoriz = chartType.includes('horizontal');
      traces.push({
        type: 'bar',
        x: isHoriz ? metricValues : metricLabels,
        y: isHoriz ? metricLabels : metricValues,
        orientation: isHoriz ? 'h' : undefined,
        marker: { color: metricColors },
        text: metricValues.map(v => v.toLocaleString('en-US', { maximumFractionDigits: 2 })),
        textposition: 'auto',
        textfont: { color: '#FFFFFF', size: 11 },
        hovertemplate: isHoriz 
          ? '<b>%{y}</b><br>Value: %{x:,.2f}<extra></extra>'
          : '<b>%{x}</b><br>Value: %{y:,.2f}<extra></extra>',
      });
    }

    // Add the label context as subtitle
    const contextLabel = label ? `${label.displayName}: ${String(rows[0][label.index])}` : '';

    return (
      <div className="w-full h-full flex flex-col justify-center animate-in fade-in duration-700">
        {contextLabel && (
          <div className="px-4 pb-2 text-center">
            <span className="text-[12px] font-semibold uppercase tracking-wider" style={{ color: P.t3 }}>{contextLabel}</span>
          </div>
        )}
        <Plot
          data={traces}
          layout={{
            autosize: true, height: 420,
            margin: chartType.includes('horizontal') ? { l: 160, r: 40, t: 20, b: 40 } : { l: 60, r: 40, t: 20, b: 80 },
            paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
            font: { family: '"Figtree", system-ui', color: P.t2, size: 11 },
            xaxis: { gridcolor: `${P.border}80`, tickfont: { color: P.t3 }, type: chartType.includes('horizontal') ? undefined : 'category', automargin: true },
            yaxis: { gridcolor: `${P.border}80`, tickfont: { color: P.t3 }, automargin: true, type: chartType.includes('horizontal') ? 'category' : undefined },
            showlegend: false,
            bargap: 0.35,
            hoverlabel: { bgcolor: '#FFFFFF', bordercolor: P.border, font: { family: '"Figtree", system-ui', size: 12, color: P.t1 } },
            ...(chartType === 'donut' ? { annotations: [{ text: contextLabel, x: 0.5, y: 0.5, font: { size: 14, color: P.t1 }, showarrow: false }] } : {}),
          }}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: '100%', height: '100%' }}
          onClick={(e: any) => {
            if (onDrillDown && e.points?.[0]) {
              onDrillDown(String(e.points[0].x || e.points[0].label));
            }
          }}
        />
      </div>
    );
  }

  // ═══ STANDARD MULTI-ROW CHARTS ═══

  // If somehow we got here with unchartable data, show table
  if (!label || values.length === 0) {
    return <InsightTable profile={profile} rows={rows} onDrillDown={onDrillDown} />;
  }

  // ── DATA INTELLIGENCE: De-duplicate identical series ──────────────
  // If two value columns have identical values in every row (e.g.
  // cum_progress_for_this_week = last_week_cum_progress), collapse to one
  let effectiveValues = [...values];
  if (values.length >= 2) {
    const keep: number[] = [0];
    for (let i = 1; i < values.length; i++) {
      const isDuplicate = keep.some(k =>
        columnsAreIdentical(rows, values[k].index, values[i].index)
      );
      if (!isDuplicate) keep.push(i);
    }
    if (keep.length < values.length) {
      effectiveValues = keep.map(k => values[k]);
    }
  }

  // ── DATA INTELLIGENCE: Auto-limit large datasets ─────────────────
  // For 30+ rows, sort by first value column descending and show top 25
  let displayRows = rows;
  let truncatedCount = 0;
  const DISPLAY_LIMIT = 30;
  if (rows.length > DISPLAY_LIMIT && effectiveValues.length > 0) {
    const valIdx = effectiveValues[0].index;
    const isProgress = effectiveValues[0].isProgressColumn;
    const sorted = [...rows].sort((a, b) => {
      const va = parseFloat(a[valIdx]) || 0;
      const vb = parseFloat(b[valIdx]) || 0;
      return vb - va; // descending — show biggest first
    });
    displayRows = sorted.slice(0, DISPLAY_LIMIT);
    truncatedCount = rows.length - DISPLAY_LIMIT;
  }

  // Extract labels
  const labels = displayRows.map(r => {
    const v = r[label.index];
    const s = String(v ?? '');
    return s.length > 30 ? s.substring(0, 27) + '…' : s;
  });

  const drillIds = profile.idColumn
    ? displayRows.map(r => String(r[profile.idColumn!.index]))
    : labels;

  // ── Build Traces ──────────────────────────────────────────────
  const traces: any[] = [];

  if (chartType === 'donut' || chartType === 'pie') {
    const valCol = effectiveValues[0];
    const nums = displayRows.map(r => getNumericValue(r[valCol.index], valCol));
    const total = nums.reduce((s, n) => s + n, 0);

    traces.push({
      type: 'pie',
      labels,
      values: nums,
      hole: 0.6,
      textinfo: 'label+percent',
      textfont: { color: '#FFFFFF', size: 11, family: '"Figtree", system-ui' },
      hovertemplate: '<b>%{label}</b><br>%{value:,.1f}<br>%{percent}<extra></extra>',
      marker: {
        colors: labels.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]),
        line: { color: '#FFFFFF', width: 2.5 },
      },
      pull: labels.map((_, i) => i === 0 ? 0.05 : 0.02),
      sort: false,
      direction: 'clockwise',
    });

    return (
      <div className="w-full h-full flex flex-col justify-center animate-in fade-in duration-700">
        <Plot
          data={traces}
          layout={{
            autosize: true,
            height: 420,
            margin: { l: 30, r: 30, t: 20, b: 20 },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { family: '"Figtree", system-ui', color: P.t2, size: 11 },
            annotations: [{
              text: `<b style="font-size:28px">${total >= 1000000 ? (total/1000000).toFixed(1)+'M' : total >= 1000 ? (total/1000).toFixed(1)+'K' : Math.round(total)}</b><br><span style="font-size:10px;color:${P.t3}">${valCol.displayName}</span>`,
              x: 0.5, y: 0.5,
              font: { size: 28, color: P.t1, family: '"Figtree", system-ui' },
              showarrow: false,
            }],
            showlegend: true,
            legend: { orientation: 'h', y: -0.08, x: 0.5, xanchor: 'center', font: { size: 10, color: P.t3 } },
          }}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: '100%', height: '100%' }}
          onClick={(e: any) => {
            if (onDrillDown && e.points?.[0]) {
              const idx = e.points[0].pointNumber;
              onDrillDown(drillIds[idx] || labels[idx]);
            }
          }}
        />
      </div>
    );
  }

  // ── Bar / Horizontal Bar / Grouped Bar / Line / Area ────────
  const isHorizontal = chartType.includes('horizontal');
  const isGrouped = chartType.includes('grouped') || effectiveValues.length > 1;
  const isLine = chartType.includes('line') || chartType.includes('area');

  // For horizontal bars, sort ascending so largest bars are at top
  let sortedLabels = labels;
  let sortedRows = displayRows;
  let sortedDrillIds = drillIds;
  if (isHorizontal && effectiveValues.length >= 1) {
    const valIdx = effectiveValues[0].index;
    const indices = displayRows.map((_, i) => i);
    indices.sort((a, b) => {
      const va = parseFloat(displayRows[a][valIdx]) || 0;
      const vb = parseFloat(displayRows[b][valIdx]) || 0;
      return va - vb; // ascending for horizontal (top = largest in Plotly)
    });
    sortedLabels = indices.map(i => labels[i]);
    sortedRows = indices.map(i => displayRows[i]);
    sortedDrillIds = indices.map(i => drillIds[i]);
  }

  const finalLabels = isHorizontal ? sortedLabels : labels;
  const finalRows = isHorizontal ? sortedRows : displayRows;
  const finalDrillIds = isHorizontal ? sortedDrillIds : drillIds;

  effectiveValues.forEach((valCol, idx) => {
    const nums = finalRows.map(r => getNumericValue(r[valCol.index], valCol));
    const traceName = effectiveValues.length > 1 
      ? (valCol.isProgressColumn ? `${valCol.displayName} (%)` : valCol.displayName)
      : (valCol.isProgressColumn ? `${valCol.displayName} (%)` : valCol.displayName);
    const isProg = valCol.isProgressColumn;

    const trace: any = {
      name: traceName,
      hovertemplate: isHorizontal
        ? `<b>%{y}</b><br>${traceName}: %{x:,.1f}${isProg ? '%' : ''}<extra></extra>`
        : `<b>%{x}</b><br>${traceName}: %{y:,.1f}${isProg ? '%' : ''}<extra></extra>`,
    };

    if (isLine) {
      trace.type = 'scatter';
      trace.mode = 'lines+markers';
      trace.line = { shape: 'spline', smoothing: 1.3, width: 3, color: CHART_COLORS[idx % CHART_COLORS.length] };
      trace.marker = { size: 7, color: CHART_COLORS[idx % CHART_COLORS.length], line: { color: '#FFFFFF', width: 1.5 } };
      if (chartType.includes('area')) {
        trace.fill = 'tozeroy';
        trace.fillcolor = CHART_COLORS[idx % CHART_COLORS.length] + '20';
      }
      trace.x = finalLabels;
      trace.y = nums;
    } else if (isHorizontal) {
      trace.type = 'bar';
      trace.orientation = 'h';
      trace.x = nums;
      trace.y = finalLabels;
      // Premium: per-bar gradient coloring for progress
      if (effectiveValues.length === 1) {
        trace.marker = {
          color: nums.map((n, i) => getBarColor(n, isProg, i)),
          line: { color: nums.map((n, i) => getBarColor(n, isProg, i)), width: 0 },
        };
      } else {
        trace.marker = { color: CHART_COLORS[idx % CHART_COLORS.length] };
      }
      // Value labels on bars
      trace.text = nums.map(n => isProg ? `${n.toFixed(1)}%` : n.toLocaleString('en-US', { maximumFractionDigits: 1 }));
      trace.textposition = 'auto';
      trace.textfont = { color: '#FFFFFF', size: 10, family: '"Figtree", system-ui' };
      trace.insidetextanchor = 'end';
    } else {
      trace.type = 'bar';
      trace.x = finalLabels;
      trace.y = nums;
      // Premium: per-bar gradient coloring for progress
      if (effectiveValues.length === 1) {
        trace.marker = {
          color: nums.map((n, i) => getBarColor(n, isProg, i)),
          line: { color: 'rgba(255,255,255,0.15)', width: 1 },
        };
      } else {
        trace.marker = { color: CHART_COLORS[idx % CHART_COLORS.length] };
      }
      // Value labels on bars
      trace.text = nums.map(n => isProg ? `${n.toFixed(1)}%` : (n >= 1000 ? `${(n/1000).toFixed(1)}K` : n.toFixed(1)));
      trace.textposition = 'outside';
      trace.textfont = { color: P.t2, size: 9, family: '"Figtree", system-ui' };
    }

    traces.push(trace);
  });

  // ── Premium Layout ──────────────────────────────────────────
  const yLabel = effectiveValues.length === 1 
    ? (effectiveValues[0].isProgressColumn ? `${effectiveValues[0].displayName} (%)` : effectiveValues[0].displayName) 
    : '';

  const layout: any = {
    autosize: true,
    height: isHorizontal ? Math.max(400, finalLabels.length * 28 + 80) : 450,
    margin: isHorizontal 
      ? { l: 200, r: 60, t: 30, b: 50 }
      : { l: 60, r: 40, t: 30, b: displayRows.length > 10 ? 130 : 80 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: '"Figtree", system-ui', color: P.t2, size: 11 },
    xaxis: {
      gridcolor: isHorizontal ? `${P.border}60` : 'transparent',
      zerolinecolor: `${P.border}80`,
      zerolinewidth: 1,
      tickfont: { color: P.t3, size: 10 },
      title: { text: isHorizontal ? yLabel : '', font: { size: 11, color: P.t3 } },
      showgrid: isHorizontal,
      linecolor: `${P.border}60`,
      automargin: true,
      type: isHorizontal ? undefined : 'category',
      tickangle: !isHorizontal && displayRows.length > 8 ? -45 : 0,
      dtick: isHorizontal && effectiveValues[0]?.isProgressColumn ? 10 : undefined,
      range: isHorizontal && effectiveValues[0]?.isProgressColumn ? [0, 105] : undefined,
    },
    yaxis: {
      gridcolor: !isHorizontal ? `${P.border}40` : 'transparent',
      zerolinecolor: `${P.border}80`,
      zerolinewidth: 1,
      tickfont: { color: P.t3, size: 10 },
      title: { text: !isHorizontal ? yLabel : '', font: { size: 11, color: P.t3 } },
      showgrid: !isHorizontal,
      linecolor: `${P.border}60`,
      automargin: true,
      type: isHorizontal ? 'category' : undefined,
      dtick: !isHorizontal && effectiveValues[0]?.isProgressColumn ? 10 : undefined,
      range: !isHorizontal && effectiveValues[0]?.isProgressColumn ? [0, 105] : undefined,
    },
    legend: {
      orientation: 'h',
      y: -0.18,
      x: 0.5,
      xanchor: 'center',
      font: { color: P.t3, size: 10 },
      bgcolor: 'transparent',
    },
    hovermode: 'closest',
    hoverlabel: {
      bgcolor: '#FFFFFF',
      bordercolor: P.border,
      font: { family: '"Figtree", system-ui', size: 12, color: P.t1 },
    },
    showlegend: effectiveValues.length > 1,
    barmode: isGrouped ? 'group' : undefined,
    bargap: isHorizontal ? 0.25 : 0.3,
    bargroupgap: 0.1,
    annotations: truncatedCount > 0 ? [{
      text: `Showing top ${DISPLAY_LIMIT} of ${rows.length} results`,
      xref: 'paper', yref: 'paper',
      x: 1, y: 1.05,
      showarrow: false,
      font: { size: 10, color: P.t4, family: '"Figtree", system-ui' },
      xanchor: 'right',
    }] : [],
  };

  return (
    <div className="w-full h-full flex flex-col justify-center animate-in fade-in duration-700">
      <Plot
        data={traces}
        layout={layout}
        useResizeHandler
        style={{ width: '100%', height: '100%' }}
        onClick={(e: any) => {
          if (onDrillDown && e.points?.[0]) {
            const idx = e.points[0].pointNumber;
            onDrillDown(finalDrillIds[idx] || String(e.points[0].x || e.points[0].y));
          }
        }}
        config={{ displayModeBar: false, responsive: true }}
      />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// EXPORT: Utility for external use (dashboard needs this)
// ═══════════════════════════════════════════════════════════════════════════
export { analyzeColumns, type DataProfile, type ColumnAnalysis };
