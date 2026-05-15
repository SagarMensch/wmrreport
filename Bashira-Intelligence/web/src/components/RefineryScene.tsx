// @ts-nocheck
'use client';
import { useRef, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useLoginStore } from '@/store/useLoginStore';
import WebGLGuard from './WebGLGuard';

// ─── Shared Material Palette (matches landing bg warmth) ─────────────────────
const MAT_IRON = new THREE.MeshStandardMaterial({ color: '#1C1208', roughness: 0.65, metalness: 0.80 });
const MAT_STEEL = new THREE.MeshStandardMaterial({ color: '#2A1C10', roughness: 0.45, metalness: 0.90 });
const MAT_RUST = new THREE.MeshStandardMaterial({ color: '#3A1A0A', roughness: 0.80, metalness: 0.40 });
const MAT_COPPER = new THREE.MeshStandardMaterial({ color: '#6B3A18', roughness: 0.35, metalness: 0.95 });
const MAT_GRATING = new THREE.MeshStandardMaterial({ color: '#151008', roughness: 0.90, metalness: 0.50, wireframe: false });

// ─── Sky Dome (matches QuarrySimulation gradient exactly) ────────────────────
function SkyDome() {
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 4; canvas.height = 512;
    const ctx = canvas.getContext('2d')!;
    const grad = ctx.createLinearGradient(0, 0, 0, 512);
    grad.addColorStop(0.00, '#09050F');
    grad.addColorStop(0.30, '#1A0828');
    grad.addColorStop(0.55, '#5C1520');
    grad.addColorStop(0.72, '#C43A0E');
    grad.addColorStop(0.85, '#E86020');
    grad.addColorStop(0.95, '#F5A030');
    grad.addColorStop(1.00, '#FAC060');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 4, 512);
    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.ClampToEdgeWrapping;
    return tex;
  }, []);

  return (
    <mesh scale={[-1, 1, -1]}>
      <sphereGeometry args={[600, 32, 16]} />
      <meshBasicMaterial map={texture} side={THREE.BackSide} depthWrite={false} />
    </mesh>
  );
}

// ─── Pipe Flange (thin disk at pipe joint) ───────────────────────────────────
function Flange({ position, axis = 'x' }: { position: [number, number, number]; axis?: 'x' | 'y' | 'z' }) {
  const rot: [number, number, number] =
    axis === 'x' ? [0, Math.PI / 2, 0] :
      axis === 'y' ? [Math.PI / 2, 0, 0] : [0, 0, 0];
  return (
    <mesh position={position} rotation={rot} castShadow>
      <cylinderGeometry args={[0.72, 0.72, 0.18, 24]} />
      <primitive object={MAT_RUST} attach="material" />
    </mesh>
  );
}

// ─── Pipe Segment with auto-flanges ─────────────────────────────────────────
function PipeRun({
  from, to, radius = 0.4, mat = MAT_STEEL, flanges = true,
}: {
  from: [number, number, number];
  to: [number, number, number];
  radius?: number;
  mat?: THREE.MeshStandardMaterial;
  flanges?: boolean;
}) {
  const dir = new THREE.Vector3(...to).sub(new THREE.Vector3(...from));
  const len = dir.length();
  const mid = new THREE.Vector3(...from).addScaledVector(dir.normalize(), len / 2);
  const quat = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0), dir.normalize()
  );
  const euler = new THREE.Euler().setFromQuaternion(quat);

  // flange axis
  const dominant: 'x' | 'y' | 'z' =
    Math.abs(dir.x) > Math.abs(dir.y) && Math.abs(dir.x) > Math.abs(dir.z) ? 'x' :
      Math.abs(dir.z) > Math.abs(dir.y) ? 'z' : 'y';

  return (
    <group>
      <mesh position={[mid.x, mid.y, mid.z]} rotation={euler} castShadow receiveShadow>
        <cylinderGeometry args={[radius, radius, len, 20]} />
        <primitive object={mat} attach="material" />
      </mesh>
      {flanges && (
        <>
          <Flange position={from} axis={dominant} />
          <Flange position={to} axis={dominant} />
        </>
      )}
    </group>
  );
}

// ─── Valve Hand-Wheel ────────────────────────────────────────────────────────
function ValveWheel({ position, formState }: { position: [number, number, number]; formState: string }) {
  const wheelRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (!wheelRef.current) return;
    let speed = 0.15;
    if (formState.includes('password')) speed = 1.4;
    if (formState === 'submit') speed = 3.0;
    if (formState === 'success') speed = 0.05;
    wheelRef.current.rotation.z += speed * delta;
  });

  return (
    <group position={position}>
      {/* valve body */}
      <mesh castShadow>
        <boxGeometry args={[0.45, 0.45, 0.9]} />
        <primitive object={MAT_COPPER} attach="material" />
      </mesh>
      {/* stem */}
      <mesh position={[0, 0.7, 0]} castShadow>
        <cylinderGeometry args={[0.07, 0.07, 0.9, 12]} />
        <primitive object={MAT_STEEL} attach="material" />
      </mesh>
      {/* hand-wheel */}
      <group ref={wheelRef} position={[0, 1.15, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <mesh castShadow>
          <torusGeometry args={[0.38, 0.045, 10, 28]} />
          <primitive object={MAT_IRON} attach="material" />
        </mesh>
        {[0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2].map((a, i) => (
          <mesh key={i} rotation={[0, 0, a]} castShadow>
            <boxGeometry args={[0.75, 0.04, 0.04]} />
            <primitive object={MAT_IRON} attach="material" />
          </mesh>
        ))}
      </group>
    </group>
  );
}

// ─── Pressure Vessel / Tank ──────────────────────────────────────────────────
function PressureVessel({
  position, scale = 1, formState,
}: {
  position: [number, number, number]; scale?: number; formState: string;
}) {
  const glowRef = useRef<THREE.PointLight>(null);

  useFrame(() => {
    if (!glowRef.current) return;
    const target =
      formState === 'password-typing' ? 18 :
        formState === 'password-focused' ? 8 :
          formState === 'submit' ? 25 :
            formState === 'success' ? 10 :
              formState === 'error' ? 30 : 1;
    glowRef.current.intensity = THREE.MathUtils.lerp(glowRef.current.intensity, target, 0.06);

    const col = formState === 'error'
      ? new THREE.Color('#FF2200')
      : formState === 'success'
        ? new THREE.Color('#FFAA30')
        : new THREE.Color('#7A1A20');
    glowRef.current.color.lerp(col, 0.08);
  });

  return (
    <group position={position} scale={scale}>
      {/* main cylinder body */}
      <mesh castShadow receiveShadow>
        <cylinderGeometry args={[1.6, 1.6, 7.0, 32]} />
        <primitive object={MAT_STEEL} attach="material" />
      </mesh>
      {/* hemispherical caps */}
      <mesh position={[0, 3.7, 0]} castShadow>
        <sphereGeometry args={[1.6, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <primitive object={MAT_IRON} attach="material" />
      </mesh>
      <mesh position={[0, -3.7, 0]} rotation={[Math.PI, 0, 0]} castShadow>
        <sphereGeometry args={[1.6, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <primitive object={MAT_IRON} attach="material" />
      </mesh>
      {/* reinforcing ring bands */}
      {[-2, 0, 2].map((y, i) => (
        <mesh key={i} position={[0, y, 0]} castShadow>
          <torusGeometry args={[1.62, 0.12, 8, 32]} />
          <primitive object={MAT_RUST} attach="material" />
        </mesh>
      ))}
      {/* pressure indicator port */}
      <mesh position={[1.65, 1.2, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
        <cylinderGeometry args={[0.12, 0.12, 0.5, 12]} />
        <primitive object={MAT_COPPER} attach="material" />
      </mesh>
      {/* inner forge glow */}
      <pointLight ref={glowRef} position={[0, 0, 0]} color="#7A1A20" intensity={1} distance={12} decay={2} />
    </group>
  );
}

// ─── Flare Stack (reacts to email + submit) ───────────────────────────────────
function RefineFlare({ position, formState }: { position: [number, number, number]; formState: string }) {
  const outerRef = useRef<THREE.Mesh>(null);
  const innerRef = useRef<THREE.Mesh>(null);
  const lightRef = useRef<THREE.PointLight>(null);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const active =
      formState.includes('email') || formState === 'submit' || formState === 'success';

    if (outerRef.current) {
      const s = active
        ? 1 + Math.sin(t * 19) * 0.15 + Math.sin(t * 33) * 0.07
        : 0.5 + Math.sin(t * 8) * 0.05;
      outerRef.current.scale.set(s, s * 1.4, s);
      const mat = outerRef.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = THREE.MathUtils.lerp(mat.emissiveIntensity, active ? 8 : 1.5, 0.08);
    }
    if (innerRef.current) {
      const s2 = active
        ? 0.6 + Math.sin(t * 27 + 1) * 0.1
        : 0.25 + Math.sin(t * 10) * 0.03;
      innerRef.current.scale.set(s2, s2 * 1.8, s2);
      innerRef.current.position.y = 1.3 + Math.sin(t * 22) * 0.15;
    }
    if (lightRef.current) {
      const targetI = active ? 30 : 4;
      lightRef.current.intensity = THREE.MathUtils.lerp(lightRef.current.intensity, targetI, 0.07);
    }
  });

  return (
    <group position={position}>
      {/* main stack */}
      <mesh castShadow>
        <cylinderGeometry args={[0.22, 0.55, 22, 10]} />
        <primitive object={MAT_IRON} attach="material" />
      </mesh>
      {/* side brace cables */}
      {[0.4, -0.4].map((xOff, i) => (
        <mesh key={i} position={[xOff, -4, 0]} rotation={[0, 0, xOff > 0 ? -0.18 : 0.18]} castShadow>
          <cylinderGeometry args={[0.03, 0.03, 13, 6]} />
          <primitive object={MAT_IRON} attach="material" />
        </mesh>
      ))}
      {/* outer diffuse flame */}
      <mesh ref={outerRef} position={[0, 11.8, 0]}>
        <sphereGeometry args={[1.0, 16, 16]} />
        <meshStandardMaterial color="#FF4400" emissive="#FF2200" emissiveIntensity={2} transparent opacity={0.9} />
      </mesh>
      {/* white-hot core */}
      <mesh ref={innerRef} position={[0, 12.5, 0]}>
        <sphereGeometry args={[0.42, 14, 14]} />
        <meshStandardMaterial color="#FFFFFF" emissive="#FFCC44" emissiveIntensity={12} />
      </mesh>
      <pointLight ref={lightRef} position={[0, 12, 0]} color="#FF6600" intensity={4} distance={70} decay={2} />
      <pointLight position={[0, 12, 0]} color="#FF9900" intensity={2} distance={180} decay={2} />
    </group>
  );
}

// ─── Scan Beam (email phase) ──────────────────────────────────────────────────
function ScanBeam({ formState }: { formState: string }) {
  const lightRef = useRef<THREE.SpotLight>(null);
  const targetRef = useRef<THREE.Object3D>(null);

  useFrame((state) => {
    if (!lightRef.current) return;
    const active = formState.includes('email');
    const targetI = active ? 35 : 0;
    lightRef.current.intensity = THREE.MathUtils.lerp(lightRef.current.intensity, targetI, 0.08);
    if (lightRef.current.target) {
      const sweep = active ? Math.sin(state.clock.elapsedTime * 3.5) * 5 : 0;
      lightRef.current.target.position.set(sweep, -2, 0);
      lightRef.current.target.updateMatrixWorld();
    }
  });

  return (
    <>
      <object3D ref={targetRef} position={[0, -2, 0]} />
      <spotLight
        ref={lightRef}
        position={[2, 16, 4]}
        angle={0.18}
        penumbra={0.4}
        intensity={0}
        color="#B8962E"
        distance={40}
        castShadow
      />
    </>
  );
}

// ─── Deck Grating Floor ───────────────────────────────────────────────────────
function DeckFloor() {
  const gratingTexture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 128; canvas.height = 128;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#0E0907';
    ctx.fillRect(0, 0, 128, 128);
    ctx.strokeStyle = '#1E130C';
    ctx.lineWidth = 2;
    for (let i = 0; i <= 128; i += 16) {
      ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, 128); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(128, i); ctx.stroke();
    }
    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(14, 14);
    return tex;
  }, []);

  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -4, 0]} receiveShadow>
      <planeGeometry args={[120, 120]} />
      <meshStandardMaterial
        map={gratingTexture}
        roughness={0.92}
        metalness={0.55}
        color="#1A1008"
      />
    </mesh>
  );
}

// ─── Structural I-Beam Frame ──────────────────────────────────────────────────
function IBeam({ from, to }: { from: [number, number, number]; to: [number, number, number] }) {
  const dir = new THREE.Vector3(...to).sub(new THREE.Vector3(...from));
  const len = dir.length();
  const mid = new THREE.Vector3(...from).addScaledVector(dir.clone().normalize(), len / 2);
  const quat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
  const euler = new THREE.Euler().setFromQuaternion(quat);
  return (
    <mesh position={[mid.x, mid.y, mid.z]} rotation={euler} castShadow receiveShadow>
      <boxGeometry args={[0.18, len, 0.45]} />
      <primitive object={MAT_RUST} attach="material" />
    </mesh>
  );
}

// ─── Main Scene ───────────────────────────────────────────────────────────────
function Scene() {
  const { gl } = useThree();
  gl.localClippingEnabled = true;
  gl.toneMapping = THREE.ACESFilmicToneMapping;
  gl.toneMappingExposure = 1.15;

  const formState = useLoginStore((state) => state.formState);

  // Success: warm wash; Error: red flash
  const ambientColor = formState === 'success' ? '#7A3C18' : formState === 'error' ? '#4A0A08' : '#3A1A0A';
  const ambientI = formState === 'submit' || formState === 'success' ? 1.8 : 0.9;

  return (
    <>
      <SkyDome />

      {/* ── Ambient & Fill ── */}
      <ambientLight color={ambientColor} intensity={ambientI} />
      <hemisphereLight skyColor="#C05018" groundColor="#0D0806" intensity={1.8} />

      {/* ── Key Sun (matches landing page sun direction) ── */}
      <directionalLight
        position={[-80, 18, -220]}
        intensity={22}
        color="#FFCC55"
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-bias={-0.0004}
        shadow-camera-near={1}
        shadow-camera-far={300}
        shadow-camera-left={-60}
        shadow-camera-right={60}
        shadow-camera-top={50}
        shadow-camera-bottom={-50}
      />
      {/* Front warm fill so we can read the metalwork */}
      <directionalLight position={[20, 10, 30]} intensity={3.5} color="#FF8844" />
      {/* Cool top bounce */}
      <directionalLight position={[0, 60, 0]} intensity={0.4} color="#2A1030" />

      {/* ── Floor ── */}
      <DeckFloor />

      {/* ── Structural scaffold frame ── */}
      <IBeam from={[-18, -4, -6]} to={[-18, 14, -6]} />
      <IBeam from={[18, -4, -6]} to={[18, 14, -6]} />
      <IBeam from={[-18, 8, -6]} to={[18, 8, -6]} />
      <IBeam from={[-18, 2, -6]} to={[18, 2, -6]} />
      <IBeam from={[6, -4, -6]} to={[6, 14, -6]} />

      {/* ── Main horizontal pipe runs ── */}
      {/* Top header pipe — large bore */}
      <PipeRun from={[-22, 6, 0]} to={[22, 6, 0]} radius={0.55} mat={MAT_STEEL} />
      {/* Mid pipe */}
      <PipeRun from={[-22, 2, 0]} to={[22, 2, 0]} radius={0.40} mat={MAT_IRON} />
      {/* Low return pipe */}
      <PipeRun from={[-22, -1, 2]} to={[22, -1, 2]} radius={0.30} mat={MAT_RUST} />
      {/* Diagonal bypass */}
      <PipeRun from={[-8, 2, 0]} to={[-4, 6, 0]} radius={0.28} mat={MAT_STEEL} flanges={false} />
      <PipeRun from={[4, 6, 0]} to={[9, 2, 0]} radius={0.28} mat={MAT_STEEL} flanges={false} />

      {/* ── Vertical riser pipes ── */}
      <PipeRun from={[-12, -4, 0]} to={[-12, 6.5, 0]} radius={0.42} mat={MAT_STEEL} />
      <PipeRun from={[0, -4, 0]} to={[0, 6.5, 0]} radius={0.36} mat={MAT_IRON} />
      <PipeRun from={[14, -4, 0]} to={[14, 6.5, 0]} radius={0.42} mat={MAT_STEEL} />

      {/* ── Depth pipes (going into/out of bg) ── */}
      <PipeRun from={[-6, 5.5, -8]} to={[-6, 5.5, 8]} radius={0.32} mat={MAT_COPPER} />
      <PipeRun from={[8, 1.5, -8]} to={[8, 1.5, 8]} radius={0.28} mat={MAT_STEEL} />

      {/* ── Elbow connectors (short L-segments) ── */}
      <PipeRun from={[-12, 6, 0]} to={[-12, 6, -4]} radius={0.42} mat={MAT_STEEL} flanges={false} />
      <PipeRun from={[14, 6, 0]} to={[14, 6, -4]} radius={0.42} mat={MAT_STEEL} flanges={false} />

      {/* ── Pressure Vessels ── */}
      <PressureVessel position={[-26, 3, -3]} scale={1.05} formState={formState} />
      <PressureVessel position={[24, 3, -2]} scale={0.80} formState={formState} />

      {/* ── Valve hand-wheels ── */}
      <ValveWheel position={[-5.5, 2.6, 0.5]} formState={formState} />
      <ValveWheel position={[9.0, 2.6, 0.5]} formState={formState} />
      <ValveWheel position={[0.0, 6.6, 0.5]} formState={formState} />

      {/* ── Flare Stacks ── */}
      <RefineFlare position={[28, -4, -10]} formState={formState} />
      <RefineFlare position={[-22, -4, -15]} formState={formState} />

      {/* ── Scan beam (email phase) ── */}
      <ScanBeam formState={formState} />

      {/* ── Small instrument clusters ── */}
      {/* Pressure gauge dome */}
      {[[-8, 6.7, 0.3], [4, 2.7, 0.3], [-12, 2.7, 0.3]].map(([x, y, z], i) => (
        <mesh key={i} position={[x, y, z]} castShadow>
          <sphereGeometry args={[0.22, 14, 14, 0, Math.PI * 2, 0, Math.PI / 2]} />
          <meshStandardMaterial color="#B8962E" roughness={0.2} metalness={0.9} emissive="#B8962E" emissiveIntensity={0.4} />
        </mesh>
      ))}

      {/* Instrument stubs */}
      {[[-8, 6.4, 0.3], [4, 2.4, 0.3], [-12, 2.4, 0.3]].map(([x, y, z], i) => (
        <mesh key={i} position={[x, y, z]} castShadow>
          <cylinderGeometry args={[0.09, 0.09, 0.35, 10]} />
          <primitive object={MAT_COPPER} attach="material" />
        </mesh>
      ))}
    </>
  );
}

// ─── Root Export ─────────────────────────────────────────────────────────────
export default function RefineryScene() {
  return (
    <div className="absolute inset-0 w-full h-full -z-10" style={{ background: '#09050F' }}>
      <WebGLGuard>
        <Canvas
          camera={{ position: [0, 8, 28], fov: 48 }}
          frameloop="always"
          shadows={{ type: THREE.PCFSoftShadowMap }}
          dpr={[1, 1.5]}
          gl={{ antialias: true, logarithmicDepthBuffer: true }}
        >
          <color attach="background" args={['#09050F']} />
          {/* Same fog settings as the landing page bg */}
          <fogExp2 attach="fog" args={['#3A1808', 0.018]} />
          <Scene />
        </Canvas>
      </WebGLGuard>
    </div>
  );
}