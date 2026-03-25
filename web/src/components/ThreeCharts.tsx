'use client';
import React, { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Instance, Instances, Float, Environment, ContactShadows, Sparkles } from '@react-three/drei';
import * as THREE from 'three';

// Static particles - no animation
function Particles({ count = 50 }) {
  const ref = useRef<THREE.Points>(null);
  
  const [positions, colors] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    const colorPalette = [
      new THREE.Color('#333333'),
      new THREE.Color('#444444'),
      new THREE.Color('#222222'),
    ];
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 30;
      pos[i * 3 + 1] = Math.random() * 15;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 30;
      
      const c = colorPalette[Math.floor(Math.random() * colorPalette.length)];
      col[i * 3] = c.r;
      col[i * 3 + 1] = c.g;
      col[i * 3 + 2] = c.b;
    }
    return [pos, col];
  }, [count]);

  // NO animation - completely static
  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.05} vertexColors transparent opacity={0.3} sizeAttenuation />
    </points>
  );
}

interface ThreeChartsProps {
  chartType: string;
  columns: string[];
  rows: any[][];
}

function formatColumnName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase());
}

// Blackstone/Blackrock style - professional, sophisticated, dark theme
const COLORS = ['#1E3A5F', '#2E5077', '#3D6B99', '#4A90C2', '#C9A227', '#8B7355', '#2C3E50', '#34495E'];

// Blackstone aesthetic - dark navy, charcoal, subtle gold
const METALLIC_COLORS = [
  '#0D1B2A', '#1B263B', '#243B53', '#1E3A5F', '#C9A227', '#8B7355'
];

// A helper to normalize data for 3D mapping
function normalizeData(rows: any[][], colIdx: number): number[] {
  const vals = rows.map(r => parseFloat(r[colIdx]) || 0);
  const max = Math.max(...vals, 1);
  return vals.map(v => v / max);
}

function BarChart3D({ rows, columns }: { rows: any[][]; columns: string[] }) {
  const groupRef = useRef<THREE.Group>(null);
  const [hovered, setHover] = useState<number | null>(null);

  const formattedColumns = columns.map(formatColumnName);

  const hasNumericData = columns.length >= 2;
  const normY = hasNumericData ? normalizeData(rows, 1) : rows.map(() => 0.8);
  const normZ = columns.length >= 3 ? normalizeData(rows, 2) : rows.map(() => 0.5);

  const numRows = rows.length;
  const spread = Math.max(10, numRows * 0.8);
  
  // NO auto-rotation - static chart, user can manually rotate with mouse

  return (
    <group ref={groupRef} position={[0, -2, 0]}>
      {/* Enhanced base grid with glow */}
      <gridHelper args={[spread * 1.5, Math.ceil(spread * 1.5), 0x444444, 0x222222]} position={[0, -0.01, 0]} />
      
      {/* Reflective ground plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]}>
        <planeGeometry args={[spread * 2, spread * 2]} />
        <meshStandardMaterial color="#0a0a0f" metalness={0.9} roughness={0.1} transparent opacity={0.6} />
      </mesh>

      {rows.map((row, i) => {
        const xPos = (i - numRows / 2) * 1.5;
        const h = Math.max(0.1, normY[i] * 8);
        const zPos = columns.length >= 3 ? (normZ[i] - 0.5) * 5 : 0;
        
        const isHovered = hovered === i;
        const color = isHovered ? '#FFFFFF' : COLORS[i % COLORS.length];
        const glowIntensity = isHovered ? 0.8 : 0.15;
        
        const displayValue = hasNumericData && row[1] !== undefined ? `${row[1]}` : '';
        const labelValue = row[0] !== undefined ? formatColumnName(String(row[0])) : `Item ${i + 1}`;

        return (
          <group key={i} position={[xPos, h / 2, zPos]}>
            {/* Glow effect */}
            <mesh>
              <boxGeometry args={[1.2, h + 0.1, 1.2]} />
              <meshBasicMaterial color={color} transparent opacity={0.15} />
            </mesh>
            
            {/* Main bar */}
            <mesh 
              onPointerOver={(e) => { e.stopPropagation(); setHover(i); }}
              onPointerOut={() => setHover(null)}
            >
              <boxGeometry args={[1, h, 1]} />
              <meshStandardMaterial 
                color={color} 
                metalness={0.6} 
                roughness={0.15} 
                emissive={color}
                emissiveIntensity={glowIntensity}
              />
            </mesh>

            {/* Top cap with gradient */}
            <mesh position={[0, h / 2 + 0.05, 0]}>
              <boxGeometry args={[1.05, 0.1, 1.05]} />
              <meshStandardMaterial color={color} metalness={0.8} roughness={0.1} emissive={color} emissiveIntensity={0.3} />
            </mesh>
            
            {/* Floating label above bar */}
            <Text
              position={[0, (h / 2) + 0.6, 0]}
              fontSize={0.35}
              color={color}
              anchorX="center"
              anchorY="middle"
              outlineWidth={0.015}
              outlineColor="#000000"
            >
              {displayValue}
            </Text>
            
            {/* Label below */}
            <Text
              position={[0, -0.5, 0]}
              fontSize={0.3}
              color="#9AA0A6"
              anchorX="center"
              anchorY="middle"
              maxWidth={1.2}
            >
              {labelValue}
            </Text>
            
            {isHovered && (
              <Text
                position={[0, (h / 2) + 1.2, 0]}
                fontSize={0.4}
                color="#FFFFFF"
                anchorX="center"
                anchorY="middle"
                outlineWidth={0.02}
                outlineColor="#000000"
              >
                {displayValue ? `${labelValue}: ${displayValue}` : labelValue}
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
  
  return (
    <div className="w-full h-full min-h-[500px] relative bg-[#050505] rounded-xl overflow-hidden border border-[#333333]">
      <Canvas 
        camera={{ position: [0, 10, 18], fov: 40 }}
        gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
        dpr={[1, 2]}
      >
        <color attach="background" args={['#030308']} />
        <fog attach="fog" args={['#030308', 12, 45]} />
        
        {/* Advanced lighting setup */}
        <ambientLight intensity={0.15} />
        <directionalLight position={[15, 25, 15]} intensity={1.0} color="#ffffff" castShadow />
        <pointLight position={[-15, 8, -15]} intensity={2} color="#00D4FF" distance={40} />
        {/* Professional lighting - subtle, no flashy colors */}
        <pointLight position={[15, 8, 15]} intensity={0.8} color="#C9A227" distance={40} />
        <pointLight position={[0, -5, 0]} intensity={0.3} color="#4A90C2" distance={30} />
        
        {/* Minimal ambient sparkles - Blackstone style */}
        <Sparkles count={30} scale={20} size={1} speed={0.1} color="#C9A227" opacity={0.15} />
        
        {/* Background particles */}
        <Particles count={200} />
        
        {/* Static chart - user can manually rotate with OrbitControls */}
        <BarChart3D rows={rows} columns={columns} />
        
        {/* Contact shadows for grounding */}
        <ContactShadows position={[0, -3, 0]} opacity={0.4} scale={30} blur={2.5} far={15} color="#000000" />
        
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
      
      {/* Blackstone-style HUD - clean, minimal, sophisticated */}
      <div className="absolute top-4 left-4 pointer-events-none">
        <div className="text-[#C9A227] text-[10px] font-mono tracking-wider uppercase">BASHIRA ANALYTICS</div>
        <div className="text-[#8B9DAF] text-[9px] font-mono mt-1">{formattedColumns[0] || 'Analysis'}</div>
      </div>
      <div className="absolute bottom-4 right-4 pointer-events-none">
         <div className="text-[#4A5568] text-[8px] font-mono uppercase tracking-widest">3D VIEW - DRAG TO ROTATE</div>
      </div>
    </div>
  );
}
