"use client";
import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";

// Dynamically import force-graph-3d to avoid SSR issues with WebGL
const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
});

interface GraphNode {
  id: string;
  labels?: string[];
  name?: string;
  description?: string;
  tableName?: string;
  dataType?: string;
  x?: number;
  y?: number;
  z?: number;
}

interface GraphLink {
  id?: string;
  source: string;
  target: string;
  type?: string;
  description?: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  stats?: { total_nodes: number; total_edges: number };
  error?: string;
}

export default function IntelligenceMatrix() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);
  const graphRef = useRef<any>(null);
  const hasInitialZoom = useRef(false);

  useEffect(() => {
    async function loadGraph() {
      try {
        const res = await fetch("/api/knowledge-graph?limit=2000");
        if (!res.ok)
          throw new Error("Failed to synchronize with Neo4j Data Core");
        const json = await res.json();

        if (json.error) throw new Error(json.error);

        const rawNodes = Array.isArray(json.nodes) ? json.nodes : [];
        const rawEdges = Array.isArray(json.edges)
          ? json.edges
          : Array.isArray(json.links)
            ? json.links
            : [];

        // Extract valid node IDs to prevent orphaned edges
        const nodes: GraphNode[] = rawNodes.map((node: any) => ({
          ...node,
          id: String(node.id),
        }));
        const nodeIds = new Set(nodes.map((node) => node.id));
        const validLinks: GraphLink[] = rawEdges
          .map((edge: any) => ({
            ...edge,
            source: String(edge.source),
            target: String(edge.target),
          }))
          .filter(
            (edge: GraphLink) =>
              nodeIds.has(edge.source) && nodeIds.has(edge.target),
          );

        // Map Neo4j edges to ForceGraph 'links' format
        const formattedData: GraphData = {
          nodes,
          links: validLinks,
          stats: json.stats ?? {
            total_nodes: nodes.length,
            total_edges: validLinks.length,
          },
        };

        setData(formattedData);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    loadGraph();
  }, []);

  // One-time initial zoom when data first loads
  useEffect(() => {
    if (!data || !graphRef.current || hasInitialZoom.current) {
      return;
    }
    const timer = window.setTimeout(() => {
      graphRef.current?.zoomToFit?.(1200, 80);
      hasInitialZoom.current = true;
    }, 500);
    return () => window.clearTimeout(timer);
  }, [data]);

  // Click handler: zoom INTO the clicked node
  const handleNodeClick = (node: any) => {
    if (!graphRef.current || !node) return;
    const distance = 120;
    const distRatio =
      1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);
    graphRef.current.cameraPosition(
      {
        x: (node.x || 0) * distRatio,
        y: (node.y || 0) * distRatio,
        z: (node.z || 0) * distRatio,
      },
      { x: node.x || 0, y: node.y || 0, z: node.z || 0 },
      1500,
    );
  };

  // Strict Institutional Color Logic
  const getNodeColor = (node: any) => {
    const labels = node.labels || [];
    if (labels.includes("Table")) return "#8AB4F8";
    if (labels.includes("Column")) return "#A0A0A0";
    if (labels.includes("Well")) return "#4E9E6A";
    return "#444444";
  };

  const getNodeSize = (node: any) => {
    const labels = node.labels || [];
    if (labels.includes("Table")) return 10;
    if (labels.includes("Well")) return 8;
    return 4;
  };

  return (
    <div
      className="relative w-full h-full bg-[#0A0A0A] overflow-hidden flex flex-col"
      style={{ fontFamily: '"Figtree", sans-serif' }}
    >
      {/* ── METADATA OVERLAY ── */}
      <div className="absolute top-8 left-8 z-20 pointer-events-none">
        <div
          className="bg-white/70 backdrop-blur-md rounded-xl p-5"
          style={{ border: "1px solid rgba(255,255,255,0.2)" }}
        >
          <h2 className="text-[#FFFFFF] text-base font-semibold tracking-wide mb-4">
            SequelOntology
          </h2>

          {data?.stats && (
            <div className="flex gap-10">
              <div className="flex flex-col">
                <span className="text-white/60 text-[9px] uppercase tracking-widest font-semibold mb-1">
                  Active Nodes
                </span>
                <span className="text-[#FFFFFF] font-bold text-2xl">
                  {data.stats.total_nodes}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-white/60 text-[9px] uppercase tracking-widest font-semibold mb-1">
                  Relational Edges
                </span>
                <span className="text-[#E87722] font-bold text-2xl">
                  {data.stats.total_edges}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── TOOLTIP HUD ── */}
      <AnimatePresence>
        {hoverNode && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="absolute bottom-8 right-8 z-20 p-6 bg-white/90 backdrop-blur-md rounded-xl min-w-[320px] pointer-events-none"
            style={{ border: "1px solid rgba(255,255,255,0.2)" }}
          >
            <div
              className="flex items-center gap-3 mb-4 pb-4"
              style={{ borderBottom: "1px solid rgba(255,255,255,0.15)" }}
            >
              <span
                className="w-3.5 h-3.5 rounded-full shadow-sm"
                style={{ backgroundColor: getNodeColor(hoverNode) }}
              />
              <h3 className="text-[#1A1A1A] text-[11px] uppercase tracking-widest font-semibold">
                {hoverNode.labels?.[0] || "Unknown Node"}
              </h3>
            </div>
            <div className="flex flex-col gap-2.5 text-[12px] text-[#1A1A1A]">
              <div className="flex justify-between items-center">
                <span className="text-[#6B6B6B] font-medium">Identity</span>
                <span className="text-[#E87722] font-semibold text-right">
                  {hoverNode.name || "UNNAMED"}
                </span>
              </div>
              {(hoverNode.tableName || hoverNode.dataType) && (
                <div
                  className="flex justify-between items-center pt-2"
                  style={{ borderTop: "1px solid rgba(0,0,0,0.06)" }}
                >
                  <span className="text-[#6B6B6B] font-medium">Schema Ref</span>
                  <span className="text-[#1A1A1A] font-semibold">
                    {hoverNode.tableName || ""}{" "}
                    {hoverNode.dataType ? `(${hoverNode.dataType})` : ""}
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── WEBGL RENDER WINDOW ── */}
      <div className="absolute inset-0 z-10">
        {loading ? (
          <div className="w-full h-full flex items-center justify-center bg-[#0A0A0A]">
            <div className="flex flex-col items-center gap-6">
              <div className="w-14 h-14 border-2 border-[#2A2A2A] border-t-2 border-t-[#E87722] rounded-full animate-spin" />
              <span className="text-[#FFFFFF] text-[10px] uppercase tracking-[0.3em] font-medium">
                Establishing Matrix Uplink...
              </span>
            </div>
          </div>
        ) : error ? (
          <div className="w-full h-full flex items-center justify-center bg-[#0A0A0A]">
            <div
              className="bg-[#FFFFFF] rounded-lg p-8 text-center max-w-sm shadow-2xl"
              style={{ border: "1px solid rgba(0,0,0,0.08)" }}
            >
              <span className="text-[#DC2626] text-3xl mb-4 block">⚠</span>
              <p className="text-[#DC2626] text-[11px] uppercase tracking-widest font-semibold leading-relaxed">
                Uplink Severed: {error}
              </p>
            </div>
          </div>
        ) : (
          data && (
            <ForceGraph3D
              ref={graphRef}
              graphData={data}
              backgroundColor="#000000"
              nodeRelSize={1}
              nodeVal={getNodeSize}
              nodeColor={getNodeColor}
              nodeResolution={32}
              linkColor={() => "#222222"}
              linkOpacity={0.55}
              linkWidth={0.8}
              warmupTicks={80}
              cooldownTicks={120}
              onNodeClick={handleNodeClick}
              onNodeHover={(node) =>
                setHoverNode((node as GraphNode | null) || null)
              }
              enableNodeDrag={true}
            />
          )
        )}
      </div>
    </div>
  );
}
