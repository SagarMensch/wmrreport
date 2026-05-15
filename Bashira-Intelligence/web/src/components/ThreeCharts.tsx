'use client';
import React, { useRef, useState, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Text, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';
import WebGLGuard from './WebGLGuard';

interface ThreeChartsProps {
  chartType: string;
  columns: string[];
  rows: any[][];
}

function formatColumnName(name: string): string {
  return name
    .replace(/[\[\]]/g, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase());
}

// Solid dark premium palette — Blackstone/Hermes
const BAR_COLORS = [
  '#1A1A1A', '#E87722', '#2563EB', '#16A34A', '#7C3AED',
  '#0D9488', '#DC2626', '#B8860B', '#4A4A4A', '#6366F1',
];

function getProgressColor(pct: number): string {
  if (pct >= 80) return '#16A34A';
  if (pct >= 50) return '#B8860B';
  if (pct >= 20) return '#E87722';
  return '#DC2626';
}

function BarChart3D({ rows, columns }: { rows: any[][]; columns: string[] }) {
  const groupRef = useRef<THREE.Group>(null);
  const [hovered, setHover] = useState<number | null>(null);

  const formattedColumns = columns.map(formatColumnName);

  // Smart data analysis: columns[0] = label, columns[1] = value
  const hasValue = columns.length >= 2;
  
  // Get max value for normalization
  const values = useMemo(() => {
    if (!hasValue) return rows.map(() => 1);
    return rows.map(r => {
      const n = parseFloat(r[1]);
      return isNaN(n) ? 0 : n;
    });
  }, [rows, hasValue]);

  const maxVal = Math.max(...values, 1);

  const numRows = rows.length;
  const spread = Math.max(10, numRows * 1.2);

  // Detect if values are percentages (for color coding)
  const isPercentage = columns[1] && /progress|pct|percent|completion/i.test(columns[1]);

  return (
    <group ref={groupRef} position={[0, -2, 0]}>
      {/* Clean grid */}
      <gridHelper args={[spread * 1.5, Math.ceil(spread * 1.5), 0xE5E5E5, 0xE5E5E5]} position={[0, -0.01, 0]} />
      
      {/* Ground plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]}>
        <planeGeometry args={[spread * 2, spread * 2]} />
        <meshStandardMaterial color="#F5F5F5" metalness={0} roughness={0.9} />
      </mesh>

      {rows.map((row, i) => {
        const xPos = (i - numRows / 2) * 1.8;
        const normalizedHeight = maxVal > 0 ? (values[i] / maxVal) * 8 : 0.1;
        const h = Math.max(0.1, normalizedHeight);
        
        const isHovered = hovered === i;
        
        // Smart color: progress-based if percentage, else palette
        let color: string;
        if (isHovered) {
          color = '#E87722';
        } else if (isPercentage) {
          color = getProgressColor(values[i]);
        } else {
          color = BAR_COLORS[i % BAR_COLORS.length];
        }
        
        // Label = first column (always the label)
        const labelValue = String(row[0] ?? `Item ${i + 1}`);
        const displayLabel = labelValue.length > 15 ? labelValue.substring(0, 12) + '...' : labelValue;
        
        // Value display
        const displayValue = hasValue ? `${values[i]}${isPercentage ? '%' : ''}` : '';

        return (
          <group key={i} position={[xPos, h / 2, 0]}>
            {/* Main bar */}
            <mesh 
              onPointerOver={(e) => { e.stopPropagation(); setHover(i); }}
              onPointerOut={() => setHover(null)}
            >
              <boxGeometry args={[1.2, h, 1.2]} />
              <meshStandardMaterial color={color} metalness={0.15} roughness={0.4} />
            </mesh>
            
            {/* Top cap */}
            <mesh position={[0, h / 2 + 0.02, 0]}>
              <boxGeometry args={[1.22, 0.04, 1.22]} />
              <meshStandardMaterial color={color} metalness={0.2} roughness={0.3} />
            </mesh>
            
            {/* Value above bar */}
            <Text
              position={[0, (h / 2) + 0.6, 0]}
              fontSize={0.35}
              color={color}
              anchorX="center"
              anchorY="middle"
              outlineWidth={0.015}
              outlineColor="#000000"
              font={undefined}
            >
              {displayValue}
            </Text>
            
            {/* Label below bar */}
            <Text
              position={[0, -(h / 2) - 0.5, 0]}
              fontSize={0.25}
              color="#6B6B6B"
              anchorX="center"
              anchorY="middle"
              maxWidth={1.6}
              font={undefined}
            >
              {displayLabel}
            </Text>
            
            {/* Hover tooltip */}
            {isHovered && (
              <Text
                position={[0, (h / 2) + 1.4, 0]}
                fontSize={0.3}
                color="#FFFFFF"
                anchorX="center"
                anchorY="middle"
                outlineWidth={0.025}
                outlineColor="#000000"
                font={undefined}
              >
                {`${labelValue}: ${displayValue}`}
              </Text>
            )}
          </group>
        );
      })}
    </group>
  );
}


export default function ThreeCharts({ chartType, columns, rows }: ThreeChartsProps) {
  const formattedColumns = columns.map(formatColumnName);
  
  // If no data or not suitable, show message
  if (!rows.length || !columns.length) {
    return (
      <div className="w-full h-full min-h-[500px] flex items-center justify-center" style={{ background: '#FFFFFF', borderRadius: '12px', border: '1px solid #E5E5E5' }}>
        <div className="text-center">
          <div className="text-[20px] mb-2" style={{ color: '#A0A0A0' }}>∅</div>
          <div className="text-[12px] font-medium" style={{ color: '#6B6B6B', fontFamily: '"Figtree", sans-serif' }}>No data for 3D visualization</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full min-h-[500px] relative bg-[#FFFFFF] rounded-xl overflow-hidden" style={{ border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
      <WebGLGuard>
        <Canvas 
          camera={{ position: [0, 10, 18], fov: 40 }}
          gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
          dpr={[1, 2]}
        >
          <color attach="background" args={['#FFFFFF']} />
          
          <ambientLight intensity={0.8} />
          <directionalLight position={[15, 25, 15]} intensity={1.2} color="#ffffff" castShadow />
          <directionalLight position={[-15, 15, -15]} intensity={0.5} color="#ffffff" />
          
          <BarChart3D rows={rows} columns={columns} />
          
          <ContactShadows position={[0, -3, 0]} opacity={0.15} scale={30} blur={2.5} far={15} color="#000000" />
          
          <OrbitControls 
            enableDamping 
            dampingFactor={0.03} 
            autoRotate={false}
            autoRotateSpeed={0.5}
            minPolarAngle={Math.PI / 6}
            maxPolarAngle={Math.PI / 2 - 0.05}
            minDistance={8}
            maxDistance={35}
          />
        </Canvas>
      </WebGLGuard>
      
      {/* HUD */}
      <div className="absolute top-4 left-4 pointer-events-none">
        <div className="text-[#1A1A1A] text-[10px] font-semibold tracking-wider uppercase" style={{ fontFamily: '"Figtree", sans-serif' }}>BASIR ANALYTICS</div>
        <div className="text-[#6B6B6B] text-[9px] mt-1" style={{ fontFamily: '"Figtree", sans-serif' }}>
          {formattedColumns[1] || formattedColumns[0] || 'Analysis'} — {rows.length} items
        </div>
      </div>
      <div className="absolute bottom-4 right-4 pointer-events-none">
         <div className="text-[#A0A0A0] text-[8px] font-medium uppercase tracking-widest" style={{ fontFamily: '"Figtree", sans-serif' }}>3D View · Drag to Rotate</div>
      </div>
    </div>
  );
}
