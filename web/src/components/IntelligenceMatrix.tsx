'use client';
import { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';

// Dynamically import force-graph-3d to avoid SSR issues with WebGL
const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), { ssr: false });

interface GraphNode {
  id: string;
  labels?: string[];
  name?: string;
  description?: string;
  tableName?: string;
  dataType?: string;
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
  const [error, setError] = useState('');
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);
  const graphRef = useRef<any>(null);
  const hasInitialZoom = useRef(false);

  useEffect(() => {
    async function loadGraph() {
      try {
        const res = await fetch('/api/knowledge-graph?limit=2000');
        if (!res.ok) throw new Error('Failed to synchronize with Neo4j Data Core');
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
          .filter((edge: GraphLink) => nodeIds.has(edge.source) && nodeIds.has(edge.target));

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
    const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);
    graphRef.current.cameraPosition(
      { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
      { x: node.x || 0, y: node.y || 0, z: node.z || 0 },
      1500
    );
  };

  // Strict Institutional Color Logic
  const getNodeColor = (node: GraphNode) => {
    const labels = node.labels || [];
    if (labels.includes('Table')) return '#8AB4F8';
    if (labels.includes('Column')) return '#A0A0A0';
    if (labels.includes('Well')) return '#4E9E6A';
    return '#444444';
  };

  const getNodeSize = (node: GraphNode) => {
    const labels = node.labels || [];
    if (labels.includes('Table')) return 10;
    if (labels.includes('Well')) return 8;
    return 4;
  };

  return (
    <div className="relative w-full h-full bg-[#000000] overflow-hidden flex flex-col font-sans">

      {/* ── METADATA OVERLAY ── */}
      <div className="absolute top-8 left-8 z-20 pointer-events-none flex flex-col gap-2">
        <h2 className="text-[#E2E2E2] text-sm font-semibold tracking-wide" style={{ fontFamily: '"Figtree", sans-serif' }}>
          SequelOntology
        </h2>

        {data?.stats && (
          <div className="mt-4 flex gap-8 border-t border-[#222222] pt-4">
            <div className="flex flex-col">
              <span className="text-[#555555] text-[8px] uppercase tracking-widest font-mono">Active Nodes</span>
              <span className="text-[#F5F5F5] font-mono text-sm">{data.stats.total_nodes}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[#555555] text-[8px] uppercase tracking-widest font-mono">Relational Edges</span>
              <span className="text-[#8AB4F8] font-mono text-sm">{data.stats.total_edges}</span>
            </div>
          </div>
        )}
      </div>

      {/* ── TOOLTIP HUD ── */}
      <AnimatePresence>
        {hoverNode && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="absolute bottom-8 right-8 z-20 p-6 bg-[#050505]/90 border border-[#222222] backdrop-blur-md min-w-[300px] pointer-events-none shadow-2xl"
          >
            <div className="flex items-center gap-3 mb-4 border-b border-[#222222] pb-3">
               <span className="w-2 h-2 rounded-full" style={{ backgroundColor: getNodeColor(hoverNode) }} />
               <h3 className="text-[#F5F5F5] text-xs uppercase tracking-widest font-bold font-mono">
                 {hoverNode.labels?.[0] || 'Unknown Node'}
               </h3>
            </div>
            <div className="flex flex-col gap-2 text-[10px] font-mono text-[#A0A0A0]">
               <div className="flex justify-between">
                 <span className="text-[#555555]">Identity:</span>
                 <span className="text-[#8AB4F8] text-right">{hoverNode.name || 'UNNAMED'}</span>
               </div>
               {(hoverNode.tableName || hoverNode.dataType) && (
                  <div className="flex justify-between mt-2 pt-2 border-t border-[#111111]">
                    <span className="text-[#555555]">Schema Ref:</span>
                    <span>{hoverNode.tableName || ''} {hoverNode.dataType ? `(${hoverNode.dataType})` : ''}</span>
                  </div>
               )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── WEBGL RENDER WINDOW ── */}
      <div className="absolute inset-0 z-10">
        {loading ? (
          <div className="w-full h-full flex items-center justify-center">
            <div className="flex flex-col items-center gap-6">
              <div className="w-16 h-16 border-t-2 border-[#8AB4F8] border-l-2 border-transparent rounded-full animate-spin" />
              <span className="text-[#8AB4F8] text-[9px] uppercase tracking-[0.4em] font-mono animate-pulse">
                Establishing Matrix Uplink...
              </span>
            </div>
          </div>
        ) : error ? (
          <div className="w-full h-full flex items-center justify-center">
            <div className="bg-[#110505] border border-[#E53935]/30 p-8 text-center max-w-sm">
              <span className="text-[#E53935] text-2xl mb-4 block">⚠</span>
              <p className="text-[#E53935] text-[10px] uppercase tracking-widest font-mono leading-relaxed">
                Uplink Severed: {error}
              </p>
            </div>
          </div>
        ) : data && (
          <ForceGraph3D
            ref={graphRef}
            graphData={data}
            backgroundColor="#000000"
            nodeRelSize={1}
            nodeVal={getNodeSize}
            nodeColor={getNodeColor}
            nodeResolution={32}
            linkColor={() => '#222222'}
            linkOpacity={0.55}
            linkWidth={0.8}
            warmupTicks={80}
            cooldownTicks={120}
            onNodeClick={handleNodeClick}
            onNodeHover={(node) => setHoverNode(node || null)}
            enableNodeDrag={true}
          />
        )}
      </div>

    </div>
  );
}
