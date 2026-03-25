// @ts-nocheck
'use client';
import dynamic from 'next/dynamic';
import React, { useMemo } from 'react';

// Dynamically import Plotly to avoid Next.js SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });
const ThreeKPI = dynamic(() => import('@/components/ThreeKPI'), { ssr: false });

interface ResultsChartProps {
  chartType?: string;
  columns?: string[];
  rows?: any[][];
  theme?: 'light' | 'dark';
  onDrillDown?: (value: string) => void;
}

// Quant/Blackstone solid color palette - no gradients, clean, corporate
const COLORS = [
  '#1A1A1A',    // Near black - primary
  '#2D3748',    // Slate gray
  '#4A5568',    // Cool gray
  '#718096',    // Medium gray
  '#A0AEC0',    // Light gray
  '#CBD5E0',    // Silver
  '#E2E8F0',    // Light silver
  '#EDF2F7',    // Off white
];

function formatColumnName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase());
}

function isProgressColumn(colName: string): boolean {
  const lower = colName.toLowerCase();
  return lower.includes('progress') || 
         lower.includes('pct') || 
         lower.includes('percent') ||
         lower.includes('completion');
}

function formatValue(value: any, colName: string): string {
  if (value === null || value === undefined || value === 'NULL') return '—';
  
  const num = parseFloat(value);
  if (isNaN(num)) return String(value);
  
  // For progress/percentage columns - convert decimal to percentage
  if (isProgressColumn(colName)) {
    if (num <= 1 && num > 0) {
      return `${(num * 100).toFixed(1)}%`;
    }
    return `${num.toFixed(1)}%`;
  }
  
  // For count/number columns - show as integer
  if (colName.toLowerCase().includes('count') || colName.toLowerCase().includes('wells') || colName.toLowerCase().includes('number')) {
    return num.toFixed(0);
  }
  
  // For other numbers - show nicely
  if (num > 0 && num < 1) {
    return num.toFixed(2);
  }
  return num.toFixed(1);
}

export default function ResultsChart({
  chartType = 'Data table',
  columns = [],
  rows = [],
  theme = 'dark',
  onDrillDown
}: ResultsChartProps) {
  const type = chartType.toLowerCase();
  const isKPI = type === 'glass_kpi' || type === '3d_kpi';

  // Always show table if there's data, even if chart rendering fails
  if (!columns.length || !rows.length) {
    return (
      <div className={`h-full flex flex-col items-center justify-center text-[13px] ${theme === 'light' ? 'text-[#888888]' : 'text-[#9AA0A6]'}`} style={{ fontFamily: '"Figtree", sans-serif' }}>
        <span className="mb-2 text-[20px] opacity-40">∅</span>
        <span>Execution Complete: No Data Available</span>
        <span className="text-[10px] opacity-50 mt-1">No rows returned from query.</span>
      </div>
    );
  }

  const isLight = theme === 'light';

  // Clean Blackstone/Quant color scheme
  const pBgColor = isLight ? '#FFFFFF' : 'transparent';
  const pPaperColor = isLight ? '#FFFFFF' : 'transparent';
  const pFontColor = isLight ? '#1A1A1A' : '#E0E0E0';
  const pGridColor = isLight ? '#E5E5E5' : '#1A1A1A';
  const pAccent = '#1A1A1A';  // Near black
  const pSecondary = '#4A5568';  // Slate

  const formattedColumns = columns.map(formatColumnName);

  // Render KPI if requested
  if (type === 'glass_kpi' || type === '3d_kpi') {
    const rawValue = rows[0] ? rows[0][0] : 'NULL';
    const displayValue = formatValue(rawValue, columns[0]);
    return (
      <ThreeKPI
        value={displayValue}
        label={columns[0] || 'Metric'}
        mode={type as any}
        theme={theme}
      />
    );
  }

  // Hand-off pure 3D Bar volumetric graphs to Three.js
  if (type === '3d_bar') {
    const ThreeCharts = dynamic(() => import('@/components/ThreeCharts'), { ssr: false });
    return <ThreeCharts chartType={type} columns={columns} rows={rows} />;
  }

  // Render clean Blackstone/Blackrock styled table - minimal, professional
  if (type.includes('table')) {
    return (
      <div className="w-full h-full overflow-auto bg-[#0A0A0A] rounded-lg border border-[#2A2A2A]">
        <div className="sticky top-0 z-10 bg-[#111111] border-b border-[#2A2A2A]">
          <div className="flex items-center px-4 py-3">
            <h3 className="text-[#B0B0B0] text-[12px] font-medium tracking-wide uppercase" style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}>
              {formatColumnName(columns[0])}
            </h3>
            <div className="ml-auto">
              <span className="text-[11px] text-[#666666]">
                {rows.length} {rows.length === 1 ? 'row' : 'rows'}
              </span>
            </div>
          </div>
        </div>
        
        <div className="divide-y divide-[#1A1A1A]">
          {rows.map((row, i) => (
            <div 
              key={i}
              onClick={() => onDrillDown && onDrillDown(String(row[0]))}
              className={`
                flex items-center px-4 py-3 cursor-pointer
                ${onDrillDown ? 'hover:bg-[#151515]' : ''}
                ${i % 2 === 0 ? 'bg-[#0A0A0A]' : 'bg-[#0D0D0D]'}
              `}
            >
              <div className="flex items-center gap-3 w-full">
                <span className="text-[11px] text-[#444444] w-6 font-mono">
                  {(i + 1).toString().padStart(2, '0')}
                </span>
                <div className="flex-1 min-w-0">
                  {columns.map((col, j) => (
                    <div key={col} className="flex items-center gap-2">
                      {columns.length > 1 && (
                        <span className="text-[10px] text-[#555555] uppercase tracking-wide w-16 flex-shrink-0">
                          {formatColumnName(col).substring(0, 8)}
                        </span>
                      )}
                      <span className={`text-[13px] ${isLight ? 'text-[#202124]' : 'text-[#D0D0D0]'} font-normal truncate`}>
                        {formatValue(row[j], col)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
        
        <div className="sticky bottom-0 bg-gradient-to-r from-[#12121a] via-[#1a1a24] to-[#12121a] border-t border-[#2a2a35] px-6 py-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-[#6B7280]">Showing {rows.length} entries</span>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-[#00D4FF] animate-pulse" />
              <span className="text-[11px] text-[#6B7280]">Live Data</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Generic Plotly Data Mapper
  const traces = useMemo(() => {
    // Handle horizontal bar specially - always render as chart
    const isHorizontal = type.includes('horizontal');
    
    // If only 1 column is returned (e.g count), still show chart for count queries
    if (columns.length < 2) {
      // Use bar for count/single value data
      if (type === '3d_bar' || type === 'bar' || type.includes('horizontal') || type.includes('count')) {
        return [{
          x: rows.map((r, i) => String(r[0])),
          y: rows.map((_, i) => 1),
          type: 'bar',
          marker: { 
            color: COLORS[0],
            line: { color: '#00D4FF', width: 1 }
          },
          name: formattedColumns[0] || 'Items'
        }];
      }
      return [];
    }

    const xData = rows.map((r) => r[0]);

    // Helper: Convert progress values from decimal (0.65) to percentage (65)
    const convertToPct = (val: any, colName: string): number => {
      if (val === null || val === undefined || val === 'NULL') return 0;
      const num = parseFloat(val);
      if (isNaN(num)) return 0;
      // If column name suggests it's a progress/percentage, and value is <= 1, multiply by 100
      if (isProgressColumn(colName) && num <= 1 && num > 0) {
        return num * 100;
      }
      return num;
    };

    // Handle 3D specifically if requested and we have 3 columns
    if (type.includes('3d') && columns.length >= 3) {
      const yData = rows.map((r) => r[1]);
      const zData = rows.map((r) => r[2]);
      
      return [{
        x: xData,
        y: yData,
        z: zData,
        mode: 'markers',
        type: 'scatter3d',
        marker: {
          size: 6,
          color: zData,
          colorscale: 'Viridis',
          opacity: 0.8
        },
        name: '3D Spatial View'
      }];
    }

    // Determine 2D Plotly Type
    let modeType = 'lines+markers';
    let plotlyType = 'scatter';

    if (type.includes('bar') || type.includes('grouped')) {
      plotlyType = 'bar';
    } else if (type.includes('scatter')) {
      modeType = 'markers';
    }

    const isGrouped = type.includes('grouped');

    // Build multiple Y-traces if there are more than 2 columns
    return columns.slice(1).map((colName, idx) => {
      const yData = rows.map((r) => convertToPct(r[idx + 1], colName));
      const formattedColName = formatColumnName(colName);

      let plotType = plotlyType;
      
      // For horizontal bar, set orientation
      if (isHorizontal && plotType === 'bar') {
        plotType = 'bar';
      }

      const baseTrace: any = {
        name: isProgressColumn(colName) ? `${formattedColName} (%)` : formattedColName,
        type: plotType,
        marker: { color: COLORS[idx % COLORS.length] },
      };

      // Horizontal bar orientation
      if (isHorizontal && plotType === 'bar') {
        baseTrace.orientation = 'h';
        baseTrace.x = yData;
        baseTrace.y = xData;
      }
      // Grouped bar specific (not horizontal)
      else if (isGrouped && plotType === 'bar') {
        baseTrace.x = xData;
        baseTrace.y = yData;
      }

      if (plotlyType === 'scatter') {
        baseTrace.mode = modeType;
        baseTrace.line = { shape: 'spline', smoothing: 1.3, width: 3 };
        if (type.includes('area') || type.includes('line')) {
           baseTrace.fill = 'tozeroy';
           baseTrace.fillcolor = COLORS[idx % COLORS.length] + '33';
        }
      }

      // For non-horizontal, non-grouped bars
      if (!isHorizontal && !isGrouped) {
        baseTrace.x = xData;
        baseTrace.y = yData;
      }

      return baseTrace;
    });
  }, [columns, rows, type]);

  // If chart rendering fails (traces empty), show table
  if (traces.length === 0) {
    return (
      <div className="h-full overflow-auto">
        <RenderDataTable data={toChartData(columns, rows)} columns={columns} theme={theme} />
      </div>
    );
  }

  // Bloomberg-style layout - clean, professional, data-first
  const layout: any = {
    autosize: true,
    height: 420,
    margin: { l: 60, r: 40, t: 40, b: 50 },
    paper_bgcolor: isLight ? '#FFFFFF' : 'transparent',
    plot_bgcolor: isLight ? '#FFFFFF' : 'transparent',
    font: { family: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', color: pFontColor, size: 11 },
    title: {
      text: '',
      font: { family: 'system-ui', size: 14, color: pAccent },
      x: 0.02,
      y: 0.98,
    },
    xaxis: {
      gridcolor: '#E5E5E5',
      zerolinecolor: '#E5E5E5',
      tickfont: { color: '#666666', size: 10, },
      title: { text: '' }, // Clean - no axis title
      showgrid: true,
      linecolor: '#E5E5E5',
      automargin: true,
    },
    yaxis: {
      gridcolor: '#E5E5E5',
      zerolinecolor: '#E5E5E5',
      tickfont: { color: '#666666', size: 10 },
      title: { text: '' }, // Clean - no axis title
      showgrid: true,
      linecolor: '#E5E5E5',
      automargin: true,
    },
    legend: {
      orientation: 'h',
      y: -0.08,
      x: 0.5,
      xanchor: 'center',
      font: { color: '#666666', size: 9 }
    },
    hovermode: 'closest',
    hoverlabel: {
      bgcolor: '#FFFFFF',
      bordercolor: '#E5E5E5',
      font: { family: 'system-ui', size: 11, color: '#1A1A1A' }
    },
    showlegend: true,
  };

  // Donut/Pie styling - Clean corporate style
  if (type.includes('donut') || type.includes('pie')) {
    layout.annotations = [{
      text: rows.length > 0 ? String(Math.round(rows.reduce((sum: number, r: any[]) => sum + (parseFloat(r[1]) || 0), 0))) : '0',
      x: 0.5, y: 0.5,
      font: { family: 'system-ui', size: 36, color: '#1A1A1A', weight: 300 },
      showarrow: False
    }];
    layout.margin = { l: 20, r: 20, t: 20, b: 20 };
    layout.height = 380;
  }

  // 3D styling - Clean corporate
  if (type.includes('3d')) {
    layout.scene = {
      xaxis: { title: { text: '' }, gridcolor: '#333', bgcolor: '#1A1A1A', showbackground: false },
      yaxis: { title: { text: '' }, gridcolor: '#333', bgcolor: '#1A1A1A', showbackground: false },
      zaxis: { title: { text: '' }, gridcolor: '#333', bgcolor: '#1A1A1A', showbackground: false },
      camera: { eye: { x: 1.5, y: 1.5, z: 1.5 } }
    };
    layout.margin = { l: 0, r: 0, t: 0, b: 0 };
    layout.height = 500;
  }

  return (
    <div className="w-full h-full flex flex-col justify-center animate-in fade-in duration-700">
      <Plot
        data={traces}
        layout={layout}
        useResizeHandler={true}
        style={{ width: '100%', height: '100%' }}
        onClick={(e: any) => {
          if (onDrillDown && e.points && e.points.length > 0) {
            onDrillDown(String(e.points[0].x));
          }
        }}
        config={{ displayModeBar: false, responsive: true }}
      />
    </div>
  );
}

// Fallback to exactly mimic the visual of the tabular renderer if something fails in Plotly 
function toChartData(columns: string[], rows: any[][]) {
  return rows.map((row) => {
    const obj: Record<string, any> = {};
    columns.forEach((col, i) => {
      obj[col] = row[i];
    });
    return obj;
  });
}

function RenderDataTable({ data, columns, theme }: { data: any[]; columns: string[]; theme: string }) {
  const isLight = theme === 'light';
  const formattedColumns = columns.map(formatColumnName);
  
  return (
    <div className="w-full h-full overflow-auto bg-gradient-to-br from-[#0a0a0f] via-[#0d0d12] to-[#0a0a0f] rounded-xl border border-[#2a2a35] shadow-2xl">
      <div className="sticky top-0 z-10 bg-gradient-to-r from-[#12121a] via-[#1a1a24] to-[#12121a] border-b border-[#2a2a35] backdrop-blur-xl">
        <div className="flex items-center px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="w-1 h-6 bg-gradient-to-b from-[#00D4FF] to-[#669DF6] rounded-full" />
            <h3 className="text-[#E2E2E2] text-[13px] font-semibold tracking-wide uppercase" style={{ fontFamily: '"Figtree", sans-serif' }}>
              {formattedColumns.join(' × ')}
            </h3>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="px-2 py-1 text-[10px] font-medium text-[#00D4FF] bg-[#00D4FF10] border border-[#00D4FF30] rounded-md">
              {data.length} {data.length === 1 ? 'Record' : 'Records'}
            </span>
          </div>
        </div>
      </div>
      
      <div className="divide-y divide-[#1e1e28]">
        {data.map((row, i) => (
          <div 
            key={i}
            className={`
              group flex items-center px-6 py-4 transition-all duration-300
              ${i % 2 === 0 ? 'bg-[#0d0d12]' : 'bg-[#0a0a0f]'}
            `}
          >
            <div className="flex items-center gap-4 w-full">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#669DF6] to-[#00D4FF] flex items-center justify-center text-[12px] font-bold text-white shadow-lg shadow-[#669DF620]">
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                {columns.map((col) => (
                  <div key={col} className="flex items-center gap-2">
                    <span className="text-[10px] text-[#6B7280] uppercase tracking-wider w-24 flex-shrink-0">
                      {formatColumnName(col)}
                    </span>
                    <span className={`text-[14px] ${isLight ? 'text-[#202124]' : 'text-[#E2E2E2]'} font-medium truncate`}>
                      {formatValue(row[col], col)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
      
      <div className="sticky bottom-0 bg-gradient-to-r from-[#12121a] via-[#1a1a24] to-[#12121a] border-t border-[#2a2a35] px-6 py-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-[#6B7280]">Showing {data.length} entries</span>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-[#00D4FF] animate-pulse" />
            <span className="text-[11px] text-[#6B7280]">Live Data</span>
          </div>
        </div>
      </div>
    </div>
  );
}
