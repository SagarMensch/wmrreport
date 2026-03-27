'use client';
import { useRef, useMemo, useState, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

function isWebGLAvailable(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (c.getContext('webgl') || c.getContext('experimental-webgl'))
    );
  } catch {
    return false;
  }
}

// AL TASNIM - MINIMALIST OIL & GAS
// Desert sands meeting petroleum precision. Hermes-tier restraint.

// DESERT SAND DUNES
const vertexShader = `
uniform float uTime;
varying vec2 vUv;
varying float vElevation;

vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}
vec3 fade(vec3 t) {return t*t*t*(t*(t*6.0-15.0)+10.0);}

float cnoise(vec3 P){
  vec3 Pi0 = floor(P); vec3 Pi1 = Pi0 + vec3(1.0);
  Pi0 = mod(Pi0, 289.0); Pi1 = mod(Pi1, 289.0);
  vec3 Pf0 = fract(P); vec3 Pf1 = Pf0 - vec3(1.0);
  vec4 ix = vec4(Pi0.x, Pi1.x, Pi0.x, Pi1.x);
  vec4 iy = vec4(Pi0.yy, Pi1.yy);
  vec4 iz0 = Pi0.zzzz; vec4 iz1 = Pi1.zzzz;
  vec4 ixy = permute(permute(ix) + iy);
  vec4 ixy0 = permute(ixy + iz0); vec4 ixy1 = permute(ixy + iz1);
  vec4 gx0 = ixy0 / 7.0; vec4 gy0 = fract(floor(gx0) / 7.0) - 0.5;
  gx0 = fract(gx0);
  vec4 gz0 = vec4(0.5) - abs(gx0) - abs(gy0);
  vec4 sz0 = step(gz0, vec4(0.0));
  gx0 -= sz0 * (step(0.0, gx0) - 0.5); gy0 -= sz0 * (step(0.0, gy0) - 0.5);
  vec4 gx1 = ixy1 / 7.0; vec4 gy1 = fract(floor(gx1) / 7.0) - 0.5;
  gx1 = fract(gx1);
  vec4 gz1 = vec4(0.5) - abs(gx1) - abs(gy1);
  vec4 sz1 = step(gz1, vec4(0.0));
  gx1 -= sz1 * (step(0.0, gx1) - 0.5); gy1 -= sz1 * (step(0.0, gy1) - 0.5);
  vec3 g000 = vec3(gx0.x,gy0.x,gz0.x); vec3 g100 = vec3(gx0.y,gy0.y,gz0.y);
  vec3 g010 = vec3(gx0.z,gy0.z,gz0.z); vec3 g110 = vec3(gx0.w,gy0.w,gz0.w);
  vec3 g001 = vec3(gx1.x,gy1.x,gz1.x); vec3 g101 = vec3(gx1.y,gy1.y,gz1.y);
  vec3 g011 = vec3(gx1.z,gy1.z,gz1.z); vec3 g111 = vec3(gx1.w,gy1.w,gz1.w);
  vec4 norm0 = taylorInvSqrt(vec4(dot(g000,g000),dot(g010,g010),dot(g100,g100),dot(g110,g110)));
  g000 *= norm0.x; g010 *= norm0.y; g100 *= norm0.z; g110 *= norm0.w;
  vec4 norm1 = taylorInvSqrt(vec4(dot(g001,g001),dot(g011,g011),dot(g101,g101),dot(g111,g111)));
  g001 *= norm1.x; g011 *= norm1.y; g101 *= norm1.z; g111 *= norm1.w;
  float n000 = dot(g000, Pf0); float n100 = dot(g100, vec3(Pf1.x, Pf0.yz));
  float n010 = dot(g010, vec3(Pf0.x, Pf1.y, Pf0.z)); float n110 = dot(g110, vec3(Pf1.xy, Pf0.z));
  float n001 = dot(g001, vec3(Pf0.xy, Pf1.z)); float n101 = dot(g101, vec3(Pf1.x, Pf0.y, Pf1.z));
  float n011 = dot(g011, vec3(Pf0.x, Pf1.yz)); float n111 = dot(g111, Pf1);
  vec3 fade_xyz = fade(Pf0);
  vec4 n_z = mix(vec4(n000,n100,n010,n110), vec4(n001,n101,n011,n111), fade_xyz.z);
  vec2 n_yz = mix(n_z.xy, n_z.zw, fade_xyz.y);
  float n_xyz = mix(n_yz.x, n_yz.y, fade_xyz.x);
  return 2.2 * n_xyz;
}

void main() {
  vUv = uv; vec3 pos = position;
  float e = cnoise(vec3(pos.x*0.04, pos.y*0.04 + uTime*0.02, uTime*0.01)) * 4.0;
  e += cnoise(vec3(pos.x*0.08, pos.y*0.08, uTime*0.015)) * 1.2;
  pos.z += e; vElevation = e;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
}
`;

const fragmentShader = `
uniform vec3 uBase; uniform vec3 uHighlight; varying float vElevation;
void main() {
  float m = clamp((vElevation + 2.0) / 6.0, 0.0, 1.0);
  gl_FragColor = vec4(mix(uBase, uHighlight, m * 0.6), 1.0);
}
`;

function Wellhead({ position }: { position: [number, number, number] }) {
  const glowRef = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (glowRef.current) (glowRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.4 + Math.sin(state.clock.getElapsedTime() * 1.5) * 0.2;
  });
  return (
    <group position={position}>
      <mesh position={[0, 0.05, 0]} rotation={[-Math.PI/2, 0, 0]}>
        <ringGeometry args={[0.15, 0.25, 32]} />
        <meshStandardMaterial color="#C9A96E" metalness={0.9} roughness={0.1} />
      </mesh>
      <mesh position={[0, 0.15, 0]}>
        <cylinderGeometry args={[0.12, 0.15, 0.15, 8]} />
        <meshStandardMaterial color="#C9A96E" metalness={0.95} roughness={0.05} />
      </mesh>
      <mesh ref={glowRef} position={[0, 0.28, 0]}>
        <sphereGeometry args={[0.04, 12, 12]} />
        <meshStandardMaterial color="#F5F1EB" emissive="#F5F1EB" emissiveIntensity={0.6} />
      </mesh>
    </group>
  );
}

function Pipeline({ start, end }: { start: [number, number, number]; end: [number, number, number] }) {
  const mid: [number, number, number] = [(start[0]+end[0])/2, 0.08, (start[2]+end[2])/2];
  const dist = Math.sqrt(Math.pow(end[0]-start[0],2) + Math.pow(end[2]-start[2],2));
  const angle = Math.atan2(end[2]-start[2], end[0]-start[0]);
  return (
    <mesh position={mid} rotation={[Math.PI/2, 0, -angle]}>
      <cylinderGeometry args={[0.015, 0.015, dist, 6]} />
      <meshStandardMaterial color="#8B6914" metalness={0.8} roughness={0.3} transparent opacity={0.6} />
    </mesh>
  );
}

function RigSilhouette({ position, scale = 1 }: { position: [number, number, number]; scale?: number }) {
  return (
    <group position={position} scale={scale}>
      <mesh position={[0, 4, 0]}><coneGeometry args={[1.5, 8, 4]} /><meshStandardMaterial color="#0a0a0a" transparent opacity={0.3} /></mesh>
      <mesh position={[0, 8.5, 0]}><sphereGeometry args={[0.08, 8, 8]} /><meshStandardMaterial color="#C9A96E" emissive="#C9A96E" emissiveIntensity={0.8} /></mesh>
    </group>
  );
}

function SandDunes() {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  useFrame((state) => {
    if (materialRef.current) materialRef.current.uniforms.uTime.value = state.clock.getElapsedTime();
    if (meshRef.current) meshRef.current.position.y = -state.clock.getElapsedTime() * 0.015;
  });
  return (
    <mesh ref={meshRef} rotation={[-Math.PI/2.2, 0, 0]} position={[0, -3, -12]}>
      <planeGeometry args={[120, 80, 128, 128]} />
      <shaderMaterial ref={materialRef} vertexShader={vertexShader} fragmentShader={fragmentShader}
        uniforms={{ uTime: { value: 0 }, uBase: { value: new THREE.Color("#080808") }, uHighlight: { value: new THREE.Color("#C9A96E") } }} />
    </mesh>
  );
}

function CameraRig() {
  const { camera } = useThree();
  useFrame((state) => {
    const t = state.clock.getElapsedTime() * 0.02;
    camera.position.x = Math.sin(t) * 0.8;
    camera.position.y = 3.5 + Math.sin(t * 0.3) * 0.15;
    camera.position.z = 12 + Math.cos(t * 0.15) * 0.3;
    camera.lookAt(0, 0.5, -2);
  });
  return null;
}

export default function AlTasnimTopography() {
  const [webglOk, setWebglOk] = useState(true);

  useEffect(() => {
    setWebglOk(isWebGLAvailable());
  }, []);

  const wells: [number, number, number][] = [[-4,0.1,2],[-2,0.1,3],[0,0.1,2.5],[2,0.1,3],[4,0.1,2]];
  const pipelines: [[number,number,number],[number,number,number]][] = [[[-4,0.1,2],[-2,0.1,3]],[[-2,0.1,3],[0,0.1,2.5]],[[0,0.1,2.5],[2,0.1,3]],[[2,0.1,3],[4,0.1,2]]];

  if (!webglOk) {
    return (
      <div style={{
        width: '100%', height: '100%', position: 'relative', overflow: 'hidden',
        background: 'linear-gradient(160deg, #010101 0%, #0a0806 30%, #120e08 55%, #0a0806 80%, #010101 100%)',
      }}>
        {/* Animated shimmer overlay */}
        <div style={{
          position: 'absolute', inset: 0,
          background: 'radial-gradient(ellipse 80% 40% at 50% 60%, rgba(201,169,110,0.06) 0%, transparent 70%)',
          animation: 'duneShimmer 8s ease-in-out infinite',
        }} />
        {/* Dune ridges */}
        <svg style={{ position: 'absolute', bottom: 0, width: '100%', height: '60%', opacity: 0.15 }} viewBox="0 0 1200 400" preserveAspectRatio="none">
          <path d="M0 400 Q150 200 300 300 T600 250 T900 280 T1200 220 L1200 400Z" fill="#C9A96E" opacity="0.3" />
          <path d="M0 400 Q200 280 400 320 T800 290 T1200 310 L1200 400Z" fill="#C9A96E" opacity="0.2" />
        </svg>
        {/* Wellhead dots */}
        {[20, 35, 50, 65, 80].map((x, i) => (
          <div key={i} style={{
            position: 'absolute', left: `${x}%`, top: '55%',
            width: 6, height: 6, borderRadius: '50%',
            background: '#C9A96E', boxShadow: '0 0 8px rgba(201,169,110,0.4)',
            animation: `wellPulse 3s ease-in-out ${i * 0.4}s infinite`,
          }} />
        ))}
        <style>{`
          @keyframes duneShimmer {
            0%, 100% { opacity: 0.4; transform: translateX(-5%); }
            50% { opacity: 1; transform: translateX(5%); }
          }
          @keyframes wellPulse {
            0%, 100% { opacity: 0.5; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.4); }
          }
        `}</style>
      </div>
    );
  }

  return (
    <Canvas camera={{ position: [0, 3.5, 12], fov: 35, near: 0.1, far: 200 }} dpr={[1, 2]} gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 0.9 }}>
      <fog attach="fog" args={['#010101', 15, 45]} />
      <color attach="background" args={['#010101']} />
      <CameraRig />
      <ambientLight intensity={0.03} />
      <spotLight position={[0, 15, 5]} angle={0.9} penumbra={0.6} intensity={8} color="#C9A96E" />
      <spotLight position={[-8, 8, 3]} angle={0.6} penumbra={0.8} intensity={2} color="#C9A96E" />
      <spotLight position={[8, 8, 3]} angle={0.6} penumbra={0.8} intensity={2} color="#C9A96E" />
      <SandDunes />
      <RigSilhouette position={[-12, 0, -15]} scale={0.6} />
      <RigSilhouette position={[12, 0, -15]} scale={0.5} />
      {wells.map((pos, i) => <Wellhead key={i} position={pos} />)}
      {pipelines.map(([s, e], i) => <Pipeline key={i} start={s} end={e} />)}
    </Canvas>
  );
}

