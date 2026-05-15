'use client';
import { useState, useEffect, ReactNode } from 'react';

let _webglResult: boolean | null = null;

function checkWebGL(): boolean {
  if (_webglResult !== null) return _webglResult;
  try {
    const c = document.createElement('canvas');
    _webglResult = !!(
      window.WebGLRenderingContext &&
      (c.getContext('webgl') || c.getContext('experimental-webgl'))
    );
  } catch {
    _webglResult = false;
  }
  return _webglResult;
}

interface WebGLGuardProps {
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Wraps Three.js <Canvas> components. If WebGL is unavailable,
 * renders the fallback (or a default dark placeholder) instead of crashing.
 */
export default function WebGLGuard({ children, fallback }: WebGLGuardProps) {
  const [ok, setOk] = useState(true); // default true to avoid SSR flash

  useEffect(() => {
    setOk(checkWebGL());
  }, []);

  if (!ok) {
    return (
      <>
        {fallback || (
          <div style={{
            width: '100%', height: '100%', minHeight: 200,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%)',
            borderRadius: 12, position: 'relative', overflow: 'hidden',
          }}>
            <div style={{
              position: 'absolute', inset: 0,
              background: 'radial-gradient(circle at 50% 50%, rgba(201,169,110,0.05) 0%, transparent 60%)',
              animation: 'wgPulse 4s ease-in-out infinite',
            }} />
            <p style={{
              color: 'rgba(255,255,255,0.35)', fontSize: 13, fontFamily: 'Inter, system-ui, sans-serif',
              letterSpacing: '0.05em', textTransform: 'uppercase', zIndex: 1,
            }}>
              WebGL unavailable — enable hardware acceleration
            </p>
            <style>{`
              @keyframes wgPulse {
                0%, 100% { opacity: 0.5; }
                50% { opacity: 1; }
              }
            `}</style>
          </div>
        )}
      </>
    );
  }

  return <>{children}</>;
}
