// @ts-nocheck
'use client';
import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

// 1. Complex Lattice Structure (Procedural Cross-Bracing)
function LatticePillar({ position, height = 20 }) {
    const mat = new THREE.MeshStandardMaterial({ color: "#2A1C16", roughness: 0.6, metalness: 0.8 });
    return (
        <group position={position}>
            <mesh position={[0, height / 2, 0]}><cylinderGeometry args={[0.4, 0.6, height]} /><primitive object={mat} attach="material" /></mesh>
            {/* Bracing */}
            {Array.from({ length: 6 }).map((_, i) => (
                <group key={i} position={[0, i * 3, 0]}>
                    <mesh rotation={[0, 0, Math.PI / 4]}><boxGeometry args={[4, 0.1, 0.1]} /><primitive object={mat} attach="material" /></mesh>
                    <mesh rotation={[0, 0, -Math.PI / 4]}><boxGeometry args={[4, 0.1, 0.1]} /><primitive object={mat} attach="material" /></mesh>
                </group>
            ))}
        </group>
    );
}

// 2. Animated Pump Jack with Linked Physics
function WorkingPumpJack({ position, rotation, phase = 0 }) {
    const beam = useRef();
    const rod = useRef();
    const crank = useRef();

    useFrame((state) => {
        const t = state.clock.elapsedTime * 1.5 + phase;
        const angle = Math.sin(t) * 0.35; // Rhythmic movement

        if (beam.current) beam.current.rotation.z = angle;
        if (crank.current) crank.current.rotation.z = t;
        // Linked vertical rod physics
        if (rod.current) rod.current.position.y = -Math.sin(t) * 1.8 - 2.5;
    });

    const iron = new THREE.MeshStandardMaterial({ color: "#1F1612", roughness: 0.4, metalness: 0.7 });
    const maroon = new THREE.MeshStandardMaterial({ color: "#7A1A20", roughness: 0.5 });

    return (
        <group position={position} rotation={rotation}>
            {/* Frame */}
            <mesh position={[0, 2, 0]} castShadow><cylinderGeometry args={[0.2, 0.8, 4, 4]} /><primitive object={iron} attach="material" /></mesh>
            {/* Walking Beam */}
            <group ref={beam} position={[0, 4.2, 0]}>
                <mesh position={[0, 0, 0]} castShadow><boxGeometry args={[8, 0.6, 0.4]} /><primitive object={maroon} attach="material" /></mesh>
                <mesh position={[-4, -0.6, 0]} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.8, 0.8, 1.8, 32, 1, false, 0, Math.PI]} /><primitive object={maroon} attach="material" /></mesh>
            </group>
            {/* Piston Rod */}
            <mesh ref={rod} position={[-4, -2, 0]}><cylinderGeometry args={[0.12, 0.12, 10]} /><meshStandardMaterial color="#B8962E" metalness={1} roughness={0.1} /></mesh>
        </group>
    );
}

// 3. Dense Rig Complex
function RigComplex({ position, scale = 1 }) {
    return (
        <group position={position} scale={scale}>
            {/* Multi-tier platforms */}
            <mesh position={[0, 4, 0]} castShadow><boxGeometry args={[25, 1.5, 25]} /><meshStandardMaterial color="#1A110D" roughness={0.8} /></mesh>
            <mesh position={[0, 8, -4]} castShadow><boxGeometry args={[18, 1, 12]} /><meshStandardMaterial color="#1A110D" roughness={0.8} /></mesh>

            {/* Details: Tanks, Pipes, Rails */}
            <mesh position={[8, 10, 8]} castShadow><cylinderGeometry args={[3, 3, 8, 16]} /><meshStandardMaterial color="#2A1C16" metalness={0.8} /></mesh>
            <mesh position={[-8, 6, 0]} rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.5, 0.5, 20]} /><meshStandardMaterial color="#111" /></mesh>

            <LatticePillar position={[-10, -10, -10]} />
            <LatticePillar position={[10, -10, -10]} />
            <LatticePillar position={[-10, -10, 10]} />
            <LatticePillar position={[10, -10, 10]} />

            <WorkingPumpJack position={[0, 5, 8]} rotation={[0, 0, 0]} />
            <WorkingPumpJack position={[8, 5, -2]} rotation={[0, Math.PI / 2, 0]} phase={Math.PI} />
        </group>
    );
}

function Scene({ activeQuery }) {
    const oceanRef = useRef();

    useFrame((state) => {
        const t = state.clock.elapsedTime * 0.5;
        const pos = oceanRef.current.geometry.attributes.position.array;
        for (let i = 0; i < pos.length; i += 3) {
            const x = pos[i], y = pos[i + 1];
            pos[i + 2] = Math.sin(x * 0.1 + t) * 0.4 + Math.cos(y * 0.2 + t) * 0.4;
        }
        oceanRef.current.geometry.attributes.position.needsUpdate = true;
        oceanRef.current.geometry.computeVertexNormals();
    });

    return (
        <>
            <ambientLight color="#D9A05B" intensity={0.6} />
            <hemisphereLight skyColor="#FFBB55" groundColor="#000000" intensity={2} />
            <directionalLight position={[-80, 40, -100]} intensity={15} color="#FFD18C" castShadow />

            {/* PROPER SUN */}
            <group position={[-100, 20, -250]}>
                <mesh>
                    <sphereGeometry args={[40, 64, 64]} />
                    <meshStandardMaterial color="#FFB84D" emissive="#FF4400" emissiveIntensity={10} />
                </mesh>
                <pointLight intensity={50000} distance={1000} color="#FF6600" />
            </group>

            {/* OILY OCEAN */}
            <mesh ref={oceanRef} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
                <planeGeometry args={[1000, 1000, 100, 100]} />
                <meshStandardMaterial color="#0A0503" roughness={0.02} metalness={1} />
            </mesh>

            <RigComplex position={[0, 0, -15]} />
            <RigComplex position={[-60, 0, -60]} scale={0.8} />
            <RigComplex position={[70, 0, -90]} scale={0.6} />
        </>
    );
}

export default function OilPlantSimulation({ activeQuery }) {
    return (
        <div className="absolute inset-0 -z-20 bg-[#0F0C0A]">
            <Canvas camera={{ position: [0, 35, 90], fov: 38 }} shadows>
                <fogExp2 attach="fog" args={['#180C08', 0.004]} />
                <Scene activeQuery={activeQuery} />
            </Canvas>
        </div>
    );
}