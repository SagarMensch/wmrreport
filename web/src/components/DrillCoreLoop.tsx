// @ts-nocheck
'use client';
import { useRef, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { motion, AnimatePresence } from 'framer-motion';

function GeologicalCore() {
  const coreRef = useRef<THREE.Group>(null);
  const scannerRef = useRef<THREE.Group>(null);

  useFrame((state, delta) => {
    if (coreRef.current) {
      // Core spins slowly on its axis
      coreRef.current.rotation.y += 0.8 * delta;
    }
    if (scannerRef.current) {
      // AI Laser scanner sweeps up and down the length of the core
      // Math.sin creates a smooth oscillating movement between -1.2 and +1.2
      scannerRef.current.position.y = Math.sin(state.clock.elapsedTime * 2.5) * 1.4;
    }
  });

  return (
    // Tipped at an isometric angle so we can see the length and depth
    <group rotation={[0.5, 0, 0.4]}>

      {/* The Physical Core Sample */}
      <group ref={coreRef}>
        {/* Gold Intelligence Layer (Top) */}
        <mesh position={[0, 1.45, 0]} castShadow>
          <cylinderGeometry args={[0.52, 0.52, 0.15, 32]} />
          <meshStandardMaterial color="#B8962E" roughness={0.2} metalness={0.9} />
        </mesh>

        {/* Basalt Stratum */}
        <mesh position={[0, 0.95, 0]} castShadow>
          <cylinderGeometry args={[0.49, 0.51, 0.85, 32]} />
          {/* Dark, rough volcanic rock */}
          <meshStandardMaterial color="#2E1F16" roughness={1.0} metalness={0.1} />
        </mesh>

        {/* Deep Clay Stratum */}
        <mesh position={[0, 0.35, 0]} castShadow>
          <cylinderGeometry args={[0.51, 0.48, 0.35, 32]} />
          <meshStandardMaterial color="#4A3424" roughness={1.0} metalness={0.0} />
        </mesh>

        {/* Clay Stratum */}
        <mesh position={[0, -0.05, 0]} castShadow>
          <cylinderGeometry args={[0.48, 0.5, 0.45, 32]} />
          <meshStandardMaterial color="#6B4E37" roughness={0.9} metalness={0.0} />
        </mesh>

        {/* Limestone Base (Omani terrain base) */}
        <mesh position={[0, -0.85, 0]} castShadow>
          <cylinderGeometry args={[0.5, 0.49, 1.15, 32]} />
          {/* Sandy, dusty limestone */}
          <meshStandardMaterial color="#967B5C" roughness={1.0} metalness={0.0} />
        </mesh>
      </group>

      {/* Analytical Extraction Cage (Static background framing) */}
      <group>
        <mesh position={[0, 0, 0]}>
          <cylinderGeometry args={[0.7, 0.7, 3.5, 16]} />
          <meshBasicMaterial color="#181210" wireframe opacity={0.3} transparent />
        </mesh>
      </group>

      {/* The AI Processing Laser */}
      <group ref={scannerRef}>
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.65, 0.03, 16, 64]} />
          <meshBasicMaterial color="#7A1A20" />
        </mesh>
        {/* Glow effect attached to the laser */}
        <pointLight color="#7A1A20" intensity={10} distance={2} />
      </group>

    </group>
  );
}

export function DrillCoreSimulation() {
  return (
    <Canvas
      camera={{ position: [0, 0, 5.5], fov: 45 }}
      // Made the canvas larger so the detail is visible
      className="!w-48 !h-48 m-auto"
      frameloop="always"
    >
      {/* High-intensity lighting to expose the PBR textures */}
      <ambientLight color="#F5E8D5" intensity={2} />
      <directionalLight position={[5, 5, 5]} intensity={6} color="#FFFFFF" />
      {/* Fill light */}
      <hemisphereLight skyColor="#F5E8D5" groundColor="#0F0C0A" intensity={1} />

      <GeologicalCore />
    </Canvas>
  );
}

export default function DrillCoreLoop() {
  const steps = [
    { ar: 'جاري معالجة البيانات...', en: 'Processing Intelligence...' },
    { ar: 'تحليل البيانات التشغيلية...', en: 'Analyzing Operational Data...' },
    { ar: 'إنشاء التمثيلات المرئية...', en: 'Generating Visual Insights...' },
  ];

  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setStep((prev) => (prev + 1) % steps.length);
    }, 3000);
    return () => clearInterval(timer);
  }, [steps.length]);

  return (
    <div className="flex flex-col items-center justify-center gap-8">
      <DrillCoreSimulation />

      <div className="h-12 relative w-full flex flex-col items-center justify-center overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col items-center gap-1"
          >
            <span
              className="text-[#EDE8DF] text-[15px] font-medium whitespace-nowrap"
              style={{ fontFamily: '"Noto Naskh Arabic", "Amiri", serif', letterSpacing: '0' }}
            >
              {steps[step].ar}
            </span>

            <span
              className="text-[#8A7B6E] text-[11px] font-medium uppercase whitespace-nowrap"
              style={{ fontFamily: '"IBM Plex Mono", monospace', letterSpacing: '0.16em' }}
            >
              {steps[step].en}
            </span>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}