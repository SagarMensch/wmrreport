'use client';
import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Text, Float } from '@react-three/drei';
import { motion } from 'framer-motion';
import WebGLGuard from './WebGLGuard';

interface ThreeKPIProps {
  value: string | number;
  label: string;
  unit?: string;
  theme?: 'light' | 'dark';
  mode: 'glass_kpi' | '3d_kpi';
}

function formatKPIValue(val: any, label: string): string {
  if (val === null || val === undefined) return '0';
  
  let num = parseFloat(String(val));
  if (isNaN(num)) return String(val);

  // Heuristic: If label contains "progress" and value is small (0-1), it's likely a decimal percentage
  const isProgress = label.toLowerCase().includes('progress') || label.toLowerCase().includes('percentage');
  
  if (isProgress && num <= 1.5) {
     num = num * 100;
  }

  // Round to 2 decimals if it's a float
  if (!Number.isInteger(num)) {
    return num.toLocaleString(undefined, { maximumFractionDigits: 1 });
  }
  
  return num.toLocaleString();
}

function FloatingNumber({ value, label }: { value: string, label: string }) {
  const textRef = useRef<any>(null);
  const formatted = formatKPIValue(value, label);
  
  // Responsive font scaling
  const baseSize = 2.5;
  const fontSize = formatted.length > 5 ? baseSize * (5 / formatted.length) : baseSize;

  useFrame((state) => {
    if (textRef.current) {
      textRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.2;
    }
  });

  return (
    <Float speed={2} rotationIntensity={0.3} floatIntensity={0.5}>
      <group ref={textRef}>
        <Text
          position={[0, 0.5, 0]}
          fontSize={Math.max(fontSize, 0.8)}
          color="#1A1A1A"
          anchorX="center"
          anchorY="middle"
        >
          {formatted}
        </Text>
        <Text
          position={[0, -1.2, 0]}
          fontSize={0.4}
          color="#6B6B6B"
          anchorX="center"
          anchorY="middle"
          letterSpacing={0.2}
        >
          {label.replace(/_/g, ' ').toUpperCase()}
        </Text>
      </group>
    </Float>
  );
}

export default function ThreeKPI({ value, label, unit, theme = 'dark', mode }: ThreeKPIProps) {
  const isLight = theme === 'light';
  const formatted = formatKPIValue(value, label);
  const isProgress = label.toLowerCase().includes('progress') || label.toLowerCase().includes('percentage');
  const finalUnit = unit || (isProgress ? '%' : '');

  // Professional Blackstone-style KPI - clean, minimal, corporate
  if (mode === 'glass_kpi') {
    return (
      <div className={`w-full h-full flex items-center justify-center p-6`}>
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
          className={`
            w-full max-w-md p-8 border-l-2 flex flex-col justify-center
            ${isLight 
              ? 'bg-white border-gray-200' 
              : 'bg-[#0A0A0A] border-[#2A2A2A]'}`}
        >
          <h3 className={`text-[11px] font-medium tracking-[0.15em] uppercase mb-2 ${isLight ? 'text-[#666666]' : 'text-[#666666]'}`}>
            {label.replace(/_/g, ' ')}
          </h3>
          <div className="flex items-baseline gap-1">
            <span className={`font-normal tracking-tight ${isLight ? 'text-[#1A1A1A]' : 'text-[#E0E0E0]'}
              text-5xl md:text-6xl`}>
              {formatted}
            </span>
            {finalUnit && <span className={`text-lg font-light ${isLight ? 'text-[#888888]' : 'text-[#555555]'}`}>{finalUnit}</span>}
          </div>
        </motion.div>
      </div>
    );
  }

  // Pure 3D Mode - Clean white background
  return (
    <div className="w-full h-full min-h-[400px] relative rounded-xl overflow-hidden" style={{ background: '#FFFFFF', border: '1px solid #E5E5E5', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
      <WebGLGuard>
        <Canvas camera={{ position: [0, 0, 8], fov: 45 }}>
          <color attach="background" args={['#FFFFFF']} />
          <ambientLight intensity={0.8} />
          <directionalLight position={[10, 10, 10]} intensity={1} color="#ffffff" />
          <directionalLight position={[-10, -10, -10]} intensity={0.3} color="#ffffff" />
          
          <FloatingNumber value={String(value)} label={label || 'Result'} />
        </Canvas>
      </WebGLGuard>
    </div>
  );
}
