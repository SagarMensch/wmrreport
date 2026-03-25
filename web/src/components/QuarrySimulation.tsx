// @ts-nocheck
'use client';
import { useRef, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Line } from '@react-three/drei';
import * as THREE from 'three';

const HORIZON_PLANE = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);

// ─── Sky Dome ────────────────────────────────────────────────────────────────
// A large inverted sphere with a canvas gradient: navy zenith → violet → crimson → deep orange horizon
function SkyDome() {
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 4;
    canvas.height = 512;
    const ctx = canvas.getContext('2d')!;
    // gradient from top (zenith) to bottom (horizon)
    const grad = ctx.createLinearGradient(0, 0, 0, 512);
    grad.addColorStop(0.0, '#09050F');  // midnight navy
    grad.addColorStop(0.3, '#1A0828');  // deep violet
    grad.addColorStop(0.55, '#5C1520');  // blood crimson
    grad.addColorStop(0.72, '#C43A0E');  // sunset orange
    grad.addColorStop(0.85, '#E86020');  // bright orange
    grad.addColorStop(0.95, '#F5A030');  // pale gold at horizon
    grad.addColorStop(1.0, '#FAC060');  // pale gold at horizon edge
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 4, 512);
    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.ClampToEdgeWrapping;
    return tex;
  }, []);

  return (
    <mesh scale={[-1, 1, -1]}>
      <sphereGeometry args={[900, 32, 16]} />
      <meshBasicMaterial map={texture} side={THREE.BackSide} depthWrite={false} />
    </mesh>
  );
}

// ─── Horizon Glow Band ────────────────────────────────────────────────────────
// A bright emissive ring at the waterline to simulate the super-heated horizon
function HorizonGlow() {
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 512; canvas.height = 64;
    const ctx = canvas.getContext('2d')!;
    const grad = ctx.createLinearGradient(0, 0, 0, 64);
    grad.addColorStop(0, 'rgba(255,140,30,0.0)');
    grad.addColorStop(0.3, 'rgba(255,100,10,0.5)');
    grad.addColorStop(0.5, 'rgba(255,160,40,0.85)');
    grad.addColorStop(0.7, 'rgba(255,100,10,0.5)');
    grad.addColorStop(1, 'rgba(255,80,0,0.0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 512, 64);
    return new THREE.CanvasTexture(canvas);
  }, []);

  return (
    <mesh position={[0, 1.0, -200]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[2400, 28]} />
      <meshBasicMaterial map={texture} transparent depthWrite={false} blending={THREE.AdditiveBlending} />
    </mesh>
  );
}

// ─── Camera Parallax ─────────────────────────────────────────────────────────
function CameraRig() {
  const { camera, pointer } = useThree();
  useFrame(() => {
    camera.rotation.y = THREE.MathUtils.lerp(camera.rotation.y, -pointer.x * 0.04, 0.04);
    camera.rotation.x = THREE.MathUtils.lerp(camera.rotation.x, pointer.y * 0.02 - 0.07, 0.04);
  });
  return null;
}

// ─── AI Routing Lines ────────────────────────────────────────────────────────
function RoutingLines() {
  const lineRef = useRef<any>(null);
  const points = useMemo(() => [
    new THREE.Vector3(40, 14, -25),
    new THREE.Vector3(18, 9, -12),
    new THREE.Vector3(8, 5, -3),
    new THREE.Vector3(-4, 5, -3),
    new THREE.Vector3(-14, 7, -10),
    new THREE.Vector3(-28, 7, -10),
    new THREE.Vector3(-44, 12, -18),
  ], []);

  useFrame((_, delta) => {
    if (lineRef.current?.material) lineRef.current.material.dashOffset -= 0.5 * delta;
  });

  return (
    <Line
      ref={lineRef} points={points} color="#FFD080" lineWidth={1.8}
      dashed dashScale={3} dashSize={2} dashRatio={0.55} transparent opacity={0.7}
    />
  );
}

// ─── Ocean ───────────────────────────────────────────────────────────────────
// Key: deep teal-blue with near-zero roughness so it acts as a mirror and
// catches ALL the warm directional sun light as vivid orange reflections.
function DeepOcean() {
  const geomRef = useRef<THREE.PlaneGeometry>(null);

  useFrame((state) => {
    if (!geomRef.current) return;
    const time = state.clock.elapsedTime * 0.7;
    const pos = geomRef.current.attributes.position.array as Float32Array;
    for (let i = 0; i < pos.length; i += 3) {
      const x = pos[i], y = pos[i + 1];
      pos[i + 2] =
        Math.sin(x * 0.07 + time) * 0.9 +
        Math.cos(y * 0.11 + time * 0.75) * 0.55 +
        Math.sin((x + y) * 0.035 - time * 0.45) * 0.65;
    }
    geomRef.current.attributes.position.needsUpdate = true;
    geomRef.current.computeVertexNormals();
  });

  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
      <planeGeometry ref={geomRef} args={[600, 600, 100, 100]} />
      <meshStandardMaterial
        color="#0B1E30"       // dark navy base
        roughness={0.04}      // near-mirror so it catches the sun
        metalness={1.0}
        envMapIntensity={2.0}
      />
    </mesh>
  );
}

// Specular glitter patch on the water beneath the sun
function SunReflectionPatch() {
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 256; canvas.height = 512;
    const ctx = canvas.getContext('2d')!;
    const grad = ctx.createRadialGradient(128, 420, 0, 128, 420, 300);
    grad.addColorStop(0, 'rgba(255,180,60,0.95)');
    grad.addColorStop(0.25, 'rgba(255,130,20,0.6)');
    grad.addColorStop(0.6, 'rgba(255,80,0,0.15)');
    grad.addColorStop(1, 'rgba(255,60,0,0.0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 256, 512);
    return new THREE.CanvasTexture(canvas);
  }, []);

  return (
    <mesh position={[-40, 0.2, -90]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[120, 260]} />
      <meshBasicMaterial map={texture} transparent depthWrite={false} blending={THREE.AdditiveBlending} />
    </mesh>
  );
}

// ─── Pump Jack ───────────────────────────────────────────────────────────────
function PumpJack({ position, rotation, scale = 1, phaseOffset = 0 }: any) {
  const beamRef = useRef<THREE.Group>(null);
  const rodRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.elapsedTime + phaseOffset;
    if (beamRef.current) beamRef.current.rotation.z = Math.sin(t * 1.5) * 0.25;
    if (rodRef.current) rodRef.current.position.y = -Math.sin(t * 1.5) * 1.2 - 2;
  });

  const ironMat = new THREE.MeshStandardMaterial({ color: '#1A1208', roughness: 0.55, metalness: 0.85 });
  const maroonMat = new THREE.MeshStandardMaterial({ color: '#6B1418', roughness: 0.5, metalness: 0.2 });
  const rodMat = new THREE.MeshStandardMaterial({ color: '#C89830', metalness: 1.0, roughness: 0.08 });

  return (
    <group position={position} rotation={rotation} scale={scale}>
      <mesh position={[0, 0.5, 0]} castShadow><boxGeometry args={[4, 1, 2]} /><primitive object={ironMat} attach="material" /></mesh>
      <mesh position={[0, 2.5, 0]} castShadow><cylinderGeometry args={[0.2, 0.5, 4, 16]} /><primitive object={ironMat} attach="material" /></mesh>
      <group ref={beamRef} position={[0, 4.5, 0]}>
        <mesh castShadow><boxGeometry args={[6, 0.4, 0.4]} /><primitive object={maroonMat} attach="material" /></mesh>
        <mesh position={[-3, -0.5, 0]} castShadow><cylinderGeometry args={[0.5, 0.5, 1.5, 16]} rotation={[0, 0, Math.PI / 2]} /><primitive object={maroonMat} attach="material" /></mesh>
      </group>
      <mesh ref={rodRef} position={[-3, -2, 0]} castShadow>
        <cylinderGeometry args={[0.08, 0.08, 6, 8]} />
        <primitive object={rodMat} attach="material" />
      </mesh>
    </group>
  );
}

// ─── Flare Stack ─────────────────────────────────────────────────────────────
function FlareStack({ position }: { position: [number, number, number] }) {
  const flameRef = useRef<THREE.Mesh>(null);
  const flameRef2 = useRef<THREE.Mesh>(null);
  const ironMat = new THREE.MeshStandardMaterial({ color: '#120C08', roughness: 0.7 });

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (flameRef.current) {
      const s = 1 + Math.sin(t * 17) * 0.12 + Math.sin(t * 31) * 0.06;
      flameRef.current.scale.set(s, s * 1.3, s);
    }
    if (flameRef2.current) {
      const s2 = 0.6 + Math.sin(t * 22 + 1) * 0.1;
      flameRef2.current.scale.set(s2, s2 * 1.6, s2);
      flameRef2.current.position.y = 21.5 + Math.sin(t * 18) * 0.3;
    }
  });

  return (
    <group position={position}>
      <mesh position={[0, 10, 0]} castShadow><cylinderGeometry args={[0.2, 0.6, 20, 8]} /><primitive object={ironMat} attach="material" /></mesh>
      <mesh position={[-2, 5, 0]} rotation={[0, 0, -0.2]}><cylinderGeometry args={[0.05, 0.05, 12, 4]} /><primitive object={ironMat} attach="material" /></mesh>
      <mesh position={[2, 5, 0]} rotation={[0, 0, 0.2]}><cylinderGeometry args={[0.05, 0.05, 12, 4]} /><primitive object={ironMat} attach="material" /></mesh>
      {/* outer diffuse flame */}
      <mesh ref={flameRef} position={[0, 20.5, 0]}>
        <sphereGeometry args={[2.0, 16, 16]} />
        <meshStandardMaterial color="#FF4400" emissive="#FF2200" emissiveIntensity={6} transparent opacity={0.85} />
      </mesh>
      {/* inner white-hot core */}
      <mesh ref={flameRef2} position={[0, 21.5, 0]}>
        <sphereGeometry args={[0.7, 12, 12]} />
        <meshStandardMaterial color="#FFFFFF" emissive="#FFCC44" emissiveIntensity={12} />
      </mesh>
      <pointLight position={[0, 21, 0]} color="#FF6600" intensity={25} distance={80} decay={2} />
      <pointLight position={[0, 21, 0]} color="#FF9900" intensity={8} distance={200} decay={2} />
    </group>
  );
}

// ─── Offshore Rig ─────────────────────────────────────────────────────────────
function OffshoreRig({ position, scale = 1, withFlare = false }: { position: [number, number, number]; scale?: number; withFlare?: boolean }) {
  const platformMat = new THREE.MeshStandardMaterial({ color: '#1C1208', roughness: 0.75, metalness: 0.5 });
  const darkMat = new THREE.MeshStandardMaterial({ color: '#120D07', roughness: 1.0 });

  return (
    <group position={position} scale={scale}>
      {[[-6, -6], [6, -6], [-6, 6], [6, 6]].map(([x, z], i) => (
        <mesh key={i} position={[x, -5, z]} castShadow receiveShadow>
          <cylinderGeometry args={[1, 1, 25, 16]} />
          <primitive object={platformMat} attach="material" />
        </mesh>
      ))}
      <mesh position={[0, 5, 0]} castShadow receiveShadow><boxGeometry args={[18, 1.5, 18]} /><primitive object={platformMat} attach="material" /></mesh>
      <mesh position={[5, 8, 5]} castShadow receiveShadow><cylinderGeometry args={[2, 2, 6, 16]} /><primitive object={platformMat} attach="material" /></mesh>
      <mesh position={[5, 8, 0]} castShadow receiveShadow><cylinderGeometry args={[2, 2, 6, 16]} /><primitive object={platformMat} attach="material" /></mesh>
      <mesh position={[-2, 9, -2]} castShadow receiveShadow><boxGeometry args={[12, 1, 10]} /><primitive object={platformMat} attach="material" /></mesh>
      <mesh position={[-4, 16, -4]} castShadow receiveShadow><cylinderGeometry args={[0.5, 3.5, 14, 8]} /><primitive object={darkMat} attach="material" /></mesh>
      <group position={[-12, 5.5, 6]}>
        <mesh castShadow receiveShadow><cylinderGeometry args={[3.5, 3.2, 0.5, 32]} /><primitive object={platformMat} attach="material" /></mesh>
        <mesh position={[2, -1.5, 0]} rotation={[0, 0, -Math.PI / 4]}><cylinderGeometry args={[0.2, 0.2, 4, 8]} /><primitive object={platformMat} attach="material" /></mesh>
      </group>
      <PumpJack position={[0, 6, 6]} rotation={[0, Math.PI / 2, 0]} scale={0.7} phaseOffset={0} />
      <PumpJack position={[0, 10, -5]} rotation={[0, -Math.PI / 4, 0]} scale={0.7} phaseOffset={1.5} />
      {withFlare && <FlareStack position={[10, 5, -8]} />}
    </group>
  );
}

// ─── Pipelines ────────────────────────────────────────────────────────────────
function SurfacePipelines() {
  const pipeMat = new THREE.MeshStandardMaterial({ color: '#1A1208', roughness: 0.5, metalness: 0.9 });
  return (
    <group>
      <mesh position={[-15, 2, -15]} rotation={[0, 0.4, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[0.4, 0.4, 45, 12]} /><primitive object={pipeMat} attach="material" />
      </mesh>
      <mesh position={[18, 2, -25]} rotation={[0, -0.6, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[0.4, 0.4, 50, 12]} /><primitive object={pipeMat} attach="material" />
      </mesh>
    </group>
  );
}

// ─── Sun ─────────────────────────────────────────────────────────────────────
// Solid sphere + massive sprite glow. Sun sits just above horizon for a classic
// "golden hour" look. Clipping plane hides anything below y=0.
function NaturalSun() {
  const glowTexture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 1024; canvas.height = 1024;
    const ctx = canvas.getContext('2d')!;
    const cx = 512, cy = 512, r = 512;
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    grad.addColorStop(0, 'rgba(255,255,220,1.0)');   // white-hot core
    grad.addColorStop(0.05, 'rgba(255,240,160,1.0)');   // pale yellow
    grad.addColorStop(0.15, 'rgba(255,180,60,0.85)');   // gold
    grad.addColorStop(0.35, 'rgba(255,100,10,0.45)');   // orange
    grad.addColorStop(0.65, 'rgba(200,40,0,0.12)');     // deep red fade
    grad.addColorStop(1.0, 'rgba(120,10,0,0.0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 1024, 1024);
    return new THREE.CanvasTexture(canvas);
  }, []);

  return (
    <group position={[-38, 6, -210]}>
      {/* Solid sun disk */}
      <mesh>
        <sphereGeometry args={[16, 64, 64]} />
        <meshBasicMaterial color="#FFF8D0" clippingPlanes={[HORIZON_PLANE]} />
      </mesh>
      {/* Inner tight halo */}
      <sprite scale={[220, 220, 1]}>
        <spriteMaterial
          map={glowTexture} color="#FFD060" transparent depthWrite={false}
          blending={THREE.AdditiveBlending} clippingPlanes={[HORIZON_PLANE]}
        />
      </sprite>
      {/* Outer wide atmospheric bloom */}
      <sprite scale={[600, 600, 1]}>
        <spriteMaterial
          map={glowTexture} color="#FF6010" transparent depthWrite={false}
          blending={THREE.AdditiveBlending} opacity={0.35} clippingPlanes={[HORIZON_PLANE]}
        />
      </sprite>
    </group>
  );
}

// ─── Scene Composition ────────────────────────────────────────────────────────
function Scene() {
  const { gl } = useThree();
  gl.localClippingEnabled = true;
  gl.toneMapping = THREE.ACESFilmicToneMapping;
  gl.toneMappingExposure = 1.2;

  return (
    <>
      {/* === SKY === */}
      <SkyDome />
      <HorizonGlow />

      {/* === AMBIENT / FILL === */}
      {/* Warm fill to prevent total silhouette darkness on front faces */}
      <ambientLight color="#8B3A18" intensity={1.2} />

      {/* Hemisphere: sky is warm orange, ground bounce is dark brown */}
      <hemisphereLight skyColor="#C05018" groundColor="#0D0806" intensity={2.5} />

      {/* === SUN & KEY LIGHT === */}
      <NaturalSun />

      {/* Primary directional sunlight — matches sun position, casts crisp shadows */}
      <directionalLight
        position={[-38, 6, -210]}
        target-position={[0, 0, 0]}
        intensity={35}
        color="#FFCC55"
        castShadow
        shadow-mapSize={[4096, 4096]}
        shadow-bias={-0.0004}
        shadow-camera-near={1}
        shadow-camera-far={600}
        shadow-camera-left={-120}
        shadow-camera-right={120}
        shadow-camera-top={80}
        shadow-camera-bottom={-80}
      />

      {/* Subtle front fill so we can still read silhouettes against the sunset */}
      <directionalLight position={[10, 10, 80]} intensity={1.8} color="#FF8844" />

      {/* Cool sky bounce from above */}
      <directionalLight position={[0, 100, 0]} intensity={0.6} color="#301030" />

      {/* === GEOMETRY === */}
      <DeepOcean />
      <SunReflectionPatch />

      <OffshoreRig position={[-45, 0, -60]} scale={0.8} withFlare />
      <OffshoreRig position={[35, 0, -80]} scale={0.6} />
      <OffshoreRig position={[4, -1, -12]} scale={1.0} withFlare />
      <SurfacePipelines />

      <RoutingLines />
      <CameraRig />
    </>
  );
}

// ─── Root ─────────────────────────────────────────────────────────────────────
export default function QuarrySimulation() {
  return (
    <div className="absolute inset-0 w-full h-full -z-10" style={{ background: '#09050F' }}>
      <Canvas
        camera={{ position: [0, 22, 55], fov: 42 }}
        frameloop="always"
        shadows={{ type: THREE.PCFSoftShadowMap }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, logarithmicDepthBuffer: true }}
      >
        <color attach="background" args={['#09050F']} />
        {/* Thinner, warmer fog so distant rigs read clearly against the sky */}
        <fogExp2 attach="fog" args={['#3A1808', 0.0035]} />
        <Scene />
      </Canvas>
    </div>
  );
}