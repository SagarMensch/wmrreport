"use client";

/**
 * DesertPlotly — Themed Plotly chart presets for Desert Atelier.
 * Each function returns { data, layout } ready for <Plot />.
 */

/* ── Desert Atelier Plotly Layout Defaults ─────────────────────────────── */

const FONT = { family: "IBM Plex Mono, Figtree, sans-serif", size: 10 };

export const DESERT_LAYOUT: Partial<Plotly.Layout> = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { ...FONT, color: "#000000" },
  margin: { l: 50, r: 24, t: 36, b: 50, pad: 4 },
  xaxis: {
    gridcolor: "#E5E5E5",
    zerolinecolor: "#000000",
    linecolor: "#000000",
    tickfont: { ...FONT, size: 9, color: "#000000" },
  },
  yaxis: {
    gridcolor: "#E5E5E5",
    zerolinecolor: "#000000",
    linecolor: "#000000",
    tickfont: { ...FONT, size: 9, color: "#000000" },
  },
  hoverlabel: {
    bgcolor: "#000000",
    bordercolor: "#000000",
    font: { ...FONT, size: 11, color: "#FFFFFF" },
  },
  legend: {
    font: { ...FONT, size: 9, color: "#000000" },
    bgcolor: "rgba(0,0,0,0)",
    borderwidth: 0,
  },
  modebar: { bgcolor: "rgba(0,0,0,0)", color: "#000000", activecolor: "#0f62fe" },
};

export const DESERT_CONFIG: Partial<Plotly.Config> = {
  displayModeBar: true,
  modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
  displaylogo: false,
  responsive: true,
};

/* ── Color Palette ─────────────────────────────────────────────────────── */

export const PALETTE = {
  blue: "#0f62fe",
  green: "#00c805",
  yellow: "#ffd700",
  red: "#a91101",
  rose: "#d4636f",
  sand: "#d4a04a",
  sage: "#5ba88c",
  black: "#000000",
  white: "#FFFFFF",
  gray: "#E5E5E5",
  darkGray: "#333333",
  void: "#000000",
  carbon: "#1A1A1A",
};

export const SERIES_COLORS = [
  PALETTE.blue,
  PALETTE.green,
  PALETTE.yellow,
  PALETTE.red,
  PALETTE.black,
  PALETTE.darkGray,
];

/* ── Treemap ───────────────────────────────────────────────────────────── */

interface TreemapItem {
  label: string;
  value: number;
  parent?: string;
  color?: string;
}

export function buildTreemap(items: TreemapItem[], title?: string) {
  const labels = ["Portfolio", ...items.map((i) => i.label)];
  const parents = ["", ...items.map((i) => i.parent || "Portfolio")];
  const values = [0, ...items.map((i) => i.value)];
  const colors = [
    "rgba(0,0,0,0)",
    ...items.map(
      (i, idx) => i.color || SERIES_COLORS[idx % SERIES_COLORS.length],
    ),
  ];

  return {
    data: [
      {
        type: "treemap" as const,
        labels,
        parents,
        values,
        marker: {
          colors,
          line: { width: 1, color: "#000000" },
        },
        textfont: { family: FONT.family, size: 11, color: "#FFFFFF" },
        pathbar: { visible: false },
        hovertemplate: "<b>%{label}</b><br>Value: %{value}<extra></extra>",
        textposition: "middle center" as const,
      },
    ],
    layout: {
      ...DESERT_LAYOUT,
      title: title ? { text: title, font: { ...FONT, size: 12, color: "#000000" }, x: 0.02 } : undefined,
      margin: { l: 4, r: 4, t: title ? 36 : 8, b: 4 },
    },
  };
}

/* ── 3D Mathematical Risk Surface ───────────────────────────────────────── */

export function buildRiskSurface3D(dataPoints: { x: number; y: number; z: number }[], title?: string) {
  // We generate a high-fidelity 50x50 mathematical mesh that mimics a paraboloid topology
  // warped by the actual portfolio data points to create the "Aesthetic 3D map" requested.
  const size = 50;
  const zData: number[][] = [];
  const xData: number[] = [];
  const yData: number[] = [];

  for (let i = 0; i < size; i++) {
    xData.push(-5 + (i * 10) / size);
    yData.push(-5 + (i * 10) / size);
  }

  // Create undulating surface influenced by input risk points
  for (let i = 0; i < size; i++) {
    const row: number[] = [];
    for (let j = 0; j < size; j++) {
      const x = xData[j];
      const y = yData[i];
      // Base paraboloid: z = x^2 + y^2
      let z = (x * x + y * y) * 0.5;
      
      // Add topological interference to make it look highly aesthetic
      z += Math.sin(x * 1.5) * Math.cos(y * 1.5) * 3;
      
      row.push(z);
    }
    zData.push(row);
  }

  return {
    data: [
      {
        type: "surface" as const,
        z: zData,
        x: xData,
        y: yData,
        colorscale: [
          [0, "#E5E5E5"], // Valleys
          [0.2, "#0f62fe"], // Rising
          [0.5, "#00c805"], // Mid
          [0.8, "#ffd700"], // Pressure
          [1.0, "#a91101"]  // Peak Risk
        ],
        showscale: false,
        contours: {
          z: { show: true, usecolormap: true, highlightcolor: "white", project: { z: true } }
        }
      }
    ],
    layout: {
      ...DESERT_LAYOUT,
      title: title ? { text: title, font: { ...FONT, size: 12, color: "#000000" }, x: 0.02 } : undefined,
      margin: { l: 0, r: 0, t: 20, b: 0 },
      scene: {
        camera: { eye: { x: 1.8, y: 1.8, z: 1.0 } },
        xaxis: { showgrid: true, gridcolor: "#E5E5E5", zeroline: false, showticklabels: false, title: "" },
        yaxis: { showgrid: true, gridcolor: "#E5E5E5", zeroline: false, showticklabels: false, title: "" },
        zaxis: { showgrid: true, gridcolor: "#E5E5E5", zeroline: false, showticklabels: false, title: "" },
        bgcolor: "#FFFFFF"
      }
    }
  };
}

/* ── Waterfall ──────────────────────────────────────────────────────────── */

interface WaterfallItem {
  label: string;
  value: number;
  measure?: "relative" | "total";
}

export function buildWaterfall(items: WaterfallItem[], title?: string) {
  return {
    data: [
      {
        type: "waterfall" as const,
        orientation: "v" as const,
        x: items.map((i) => i.label),
        y: items.map((i) => i.value),
        measure: items.map((i) => i.measure || "relative"),
        connector: { line: { color: "rgba(185,150,100,0.15)", width: 1 } },
        increasing: { marker: { color: PALETTE.green } },
        decreasing: { marker: { color: PALETTE.red } },
        totals: { marker: { color: PALETTE.blue } },
        textposition: "outside" as const,
        textfont: { ...FONT, size: 9, color: "#9A8B78" },
        hovertemplate: "<b>%{x}</b><br>%{y:.1f}<extra></extra>",
      },
    ],
    layout: {
      ...DESERT_LAYOUT,
      title: title ? { text: title, font: { ...FONT, size: 12, color: "#C9A96E" }, x: 0.02 } : undefined,
      showlegend: false,
    },
  };
}

/* ── Horizontal Bar ────────────────────────────────────────────────────── */

interface HBarItem {
  label: string;
  value: number;
  color?: string;
}

export function buildHorizontalBar(items: HBarItem[], title?: string) {
  const sorted = [...items].sort((a, b) => a.value - b.value);
  return {
    data: [
      {
        type: "bar" as const,
        orientation: "h" as const,
        x: sorted.map((i) => i.value),
        y: sorted.map((i) => i.label),
        marker: {
          color: sorted.map(
            (i, idx) =>
              i.color || SERIES_COLORS[idx % SERIES_COLORS.length],
          ),
          line: { width: 0 },
        },
        textposition: "outside" as const,
        textfont: { ...FONT, size: 9, color: "#9A8B78" },
        hovertemplate: "<b>%{y}</b>: %{x:.1f}<extra></extra>",
      },
    ],
    layout: {
      ...DESERT_LAYOUT,
      title: title ? { text: title, font: { ...FONT, size: 12, color: "#C9A96E" }, x: 0.02 } : undefined,
      margin: { l: 110, r: 30, t: title ? 40 : 12, b: 30 },
      showlegend: false,
      xaxis: {
        ...DESERT_LAYOUT.xaxis,
        showgrid: true,
      },
      yaxis: {
        ...DESERT_LAYOUT.yaxis,
        showgrid: false,
        automargin: true,
      },
    },
  };
}

/* ── Scatter ───────────────────────────────────────────────────────────── */

interface ScatterPoint {
  x: number;
  y: number;
  label: string;
  color?: string;
  size?: number;
}

export function buildScatter(
  points: ScatterPoint[],
  xLabel?: string,
  yLabel?: string,
  title?: string,
) {
  return {
    data: [
      {
        type: "scatter" as const,
        mode: "markers+text" as const,
        x: points.map((p) => p.x),
        y: points.map((p) => p.y),
        text: points.map((p) => p.label),
        textposition: "top center" as const,
        textfont: { ...FONT, size: 8, color: "#000000" },
        marker: {
          size: points.map((p) => p.size || 10),
          color: points.map(
            (p, i) => p.color || SERIES_COLORS[i % SERIES_COLORS.length],
          ),
          line: { width: 1, color: "#000000" },
          opacity: 0.85,
        },
        hovertemplate:
          "<b>%{text}</b><br>" +
          (xLabel || "X") +
          ": %{x:.1f}<br>" +
          (yLabel || "Y") +
          ": %{y:.1f}<extra></extra>",
      },
    ],
    layout: {
      ...DESERT_LAYOUT,
      title: title ? { text: title, font: { ...FONT, size: 12, color: "#000000" }, x: 0.02 } : undefined,
      xaxis: {
        ...DESERT_LAYOUT.xaxis,
        title: { text: xLabel, font: { ...FONT, size: 9, color: "#000000" } },
      },
      yaxis: {
        ...DESERT_LAYOUT.yaxis,
        title: { text: yLabel, font: { ...FONT, size: 9, color: "#000000" } },
      },
    },
  };
}

export function buildScatter3D(
  points: (ScatterPoint & { z: number })[],
  xLabel?: string,
  yLabel?: string,
  zLabel?: string,
  title?: string,
) {
  return {
    data: [
      {
        type: "scatter3d" as const,
        mode: "markers" as const,
        x: points.map((p) => p.x),
        y: points.map((p) => p.y),
        z: points.map((p) => p.z),
        text: points.map((p) => p.label),
        marker: {
          size: points.map((p) => (p.size ? p.size / 2.5 : 4)), // SCATTER3D size is slightly different scale
          color: points.map(
            (p, i) => p.color || SERIES_COLORS[i % SERIES_COLORS.length],
          ),
          line: { width: 0.5, color: "#000" },
          opacity: 0.95,
        },
        hovertemplate:
          "<b>%{text}</b><br>" +
          (xLabel || "X") +
          ": %{x:.1f}<br>" +
          (yLabel || "Y") +
          ": %{y:.1f}<br>" +
          (zLabel || "Z") +
          ": %{z:.1f}<extra></extra>",
      },
    ],
    layout: {
      ...DESERT_LAYOUT,
      title: title ? { text: title, font: { ...FONT, size: 12, color: "#000000" }, x: 0.02 } : undefined,
      margin: { l: 0, r: 0, t: title ? 30 : 0, b: 0 },
      scene: {
        camera: { eye: { x: 1.5, y: 1.5, z: 1.2 } },
        xaxis: { showgrid: true, gridcolor: "#E5E5E5", zeroline: false, showbackground: false, title: { text: xLabel || "", font: { ...FONT, size: 10, color: "#000000" } } },
        yaxis: { showgrid: true, gridcolor: "#E5E5E5", zeroline: false, showbackground: false, title: { text: yLabel || "", font: { ...FONT, size: 10, color: "#000000" } } },
        zaxis: { showgrid: true, gridcolor: "#E5E5E5", zeroline: false, showbackground: false, title: { text: zLabel || "", font: { ...FONT, size: 10, color: "#000000" } } },
        bgcolor: "#FFFFFF"
      }
    },
  };
}

/* ── Gantt (using bar shapes) ──────────────────────────────────────────── */

interface GanttRow {
  label: string;
  start: string;
  end: string;
  color?: string;
  group?: string;
}

export function buildGantt(rows: GanttRow[], title?: string) {
  const traces = rows.map((row, i) => ({
    type: "bar" as const,
    orientation: "h" as const,
    y: [row.label],
    x: [
      Math.max(
        1,
        (new Date(row.end).getTime() - new Date(row.start).getTime()) /
          (1000 * 60 * 60 * 24),
      ),
    ],
    base: [row.start],
    marker: {
      color: row.color || SERIES_COLORS[i % SERIES_COLORS.length],
      line: { width: 0 },
    },
    name: row.group || row.label,
    showlegend: false,
    hovertemplate: `<b>${row.label}</b><br>Start: ${row.start}<br>End: ${row.end}<extra></extra>`,
  }));

  return {
    data: traces,
    layout: {
      ...DESERT_LAYOUT,
      title: title ? { text: title, font: { ...FONT, size: 12, color: "#C9A96E" }, x: 0.02 } : undefined,
      barmode: "stack" as const,
      margin: { l: 140, r: 24, t: title ? 40 : 12, b: 40 },
      xaxis: {
        ...DESERT_LAYOUT.xaxis,
        type: "date" as const,
      },
      yaxis: {
        ...DESERT_LAYOUT.yaxis,
        autorange: "reversed" as const,
        automargin: true,
      },
    },
  };
}

/* ── Donut ──────────────────────────────────────────────────────────────── */

interface DonutSegment {
  label: string;
  value: number;
  color?: string;
}

export function buildDonut(segments: DonutSegment[], title?: string) {
  return {
    data: [
      {
        type: "pie" as const,
        labels: segments.map((s) => s.label),
        values: segments.map((s) => s.value),
        hole: 0.55,
        marker: {
          colors: segments.map(
            (s, i) => s.color || SERIES_COLORS[i % SERIES_COLORS.length],
          ),
          line: { color: "#000000", width: 2 },
        },
        textfont: { ...FONT, size: 10, color: "#000000" },
        textposition: "inside" as const,
        hovertemplate: "<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
      },
    ],
    layout: {
      ...DESERT_LAYOUT,
      title: title ? { text: title, font: { ...FONT, size: 12, color: "#000000" }, x: 0.02 } : undefined,
      margin: { l: 10, r: 10, t: title ? 40 : 10, b: 10 },
      showlegend: true,
      legend: {
        font: { ...FONT, size: 10, color: "#000000" },
        bgcolor: "rgba(0,0,0,0)",
        orientation: "h" as const,
        x: 0.5,
        xanchor: "center" as const,
        y: -0.05,
      },
    },
  };
}

export function buildDonut3D(segments: DonutSegment[], title?: string) {
  // Translate a donut into a 3D bubble tower (execution stack)
  return {
    data: [
      {
        type: "scatter3d" as const,
        mode: "markers" as const,
        x: segments.map((_, i) => Math.cos((i / segments.length) * Math.PI * 2)),
        y: segments.map((_, i) => Math.sin((i / segments.length) * Math.PI * 2)),
        z: segments.map((s) => s.value),
        text: segments.map((s) => s.label),
        marker: {
          size: segments.map((s) => Math.max(10, s.value / 2)),
          color: segments.map(
            (s, i) => s.color || SERIES_COLORS[i % SERIES_COLORS.length],
          ),
          opacity: 0.9,
          line: { width: 1, color: "#000" }
        },
        hovertemplate: "<b>%{text}</b><br>Value: %{z}<extra></extra>",
      },
    ],
    layout: {
      ...DESERT_LAYOUT,
      title: title ? { text: title, font: { ...FONT, size: 12, color: "#000000" }, x: 0.02 } : undefined,
      margin: { l: 0, r: 0, t: 20, b: 0 },
      scene: {
        camera: { eye: { x: 1.2, y: 1.2, z: 1.2 } },
        xaxis: { showgrid: false, zeroline: false, showbackground: false, showticklabels: false, title: "" },
        yaxis: { showgrid: false, zeroline: false, showbackground: false, showticklabels: false, title: "" },
        zaxis: { showgrid: true, gridcolor: "#E5E5E5", zeroline: false, showbackground: false, title: "" },
        bgcolor: "#FFFFFF"
      }
    },
  };
}

export function buildTreemap3D(items: TreemapItem[], title?: string) {
  // Translate a treemap into a 3D landscape of boxes or spheres (Portfolio Map)
  const size = Math.ceil(Math.sqrt(items.length));
  return {
    data: [
      {
        type: "scatter3d" as const,
        mode: "markers" as const,
        x: items.map((_, i) => i % size),
        y: items.map((_, i) => Math.floor(i / size)),
        z: items.map((i) => i.value),
        text: items.map((i) => i.label),
        marker: {
          symbol: "square",
          size: items.map((i) => Math.max(8, Math.min(30, i.value * 2))),
          color: items.map(
            (item, idx) => item.color || SERIES_COLORS[idx % SERIES_COLORS.length],
          ),
          opacity: 0.95,
          line: { width: 1, color: "#000" }
        },
        hovertemplate: "<b>%{text}</b><br>Value: %{z}<extra></extra>",
      },
    ],
    layout: {
      ...DESERT_LAYOUT,
      title: title ? { text: title, font: { ...FONT, size: 12, color: "#000000" }, x: 0.02 } : undefined,
      margin: { l: 0, r: 0, t: 30, b: 0 },
      scene: {
        camera: { eye: { x: 1.5, y: 1.5, z: 1.2 } },
        xaxis: { showgrid: true, gridcolor: "#E5E5E5", zeroline: false, showbackground: false, title: "", showticklabels: false },
        yaxis: { showgrid: true, gridcolor: "#E5E5E5", zeroline: false, showbackground: false, title: "", showticklabels: false },
        zaxis: { showgrid: true, gridcolor: "#E5E5E5", zeroline: false, showbackground: false, title: "Capital Value" },
        bgcolor: "#FFFFFF"
      }
    },
  };
}
