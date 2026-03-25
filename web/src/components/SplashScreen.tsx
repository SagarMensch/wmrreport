'use client';
import { motion } from 'framer-motion';
import { useEffect } from 'react';

// ── THE BLACKSTONE / BLACKROCK DOCTRINE ─────────────────────────────────────
// A 50-person top-tier institutional design team does NOT use flash, 3D gimmicks, 
// glowing stars, or floating geometric cubes. They use absolute, terrifying brevity.
// 
// Institutional power is projected through:
// 1. Unyielding Negative Space (Pure #000000 OLED Black)
// 2. Absolute Flat Typography (No drop shadows, no neon glows)
// 3. Exacting Architectural Lines
// 4. Breathtakingly smooth Bezier curve animations
//
// This is exactly how the Aladdin terminal or a Blackstone internal portal boots.

export default function SplashScreen({ onComplete }: { onComplete: () => void }) {
  useEffect(() => {
    // Exact 4.5 second hold. Institutional software is brutally efficient.
    const timer = setTimeout(() => {
      onComplete();
    }, 4500);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 1.2, ease: "easeInOut" } }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#000000] overflow-hidden"
    >
      <div className="flex flex-col items-center justify-center">
        
        {/* ── 1. The Institutional Arabic Mark ── */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.8, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="overflow-hidden pb-4"
        >
          <span 
            className="text-[#D4AF37] text-3xl md:text-5xl font-light opacity-90"
            style={{ fontFamily: '"Noto Naskh Arabic", sans-serif', letterSpacing: '0.05em' }}
          >
            بصير
          </span>
        </motion.div>

        {/* ── 2. The Unyielding Primary Mark (Cinzel Decorative) ── */}
        {/* No Drop Shadows. No Glow. Pure mathematically flat #D4AF37 Gold. */}
        <div className="overflow-visible pb-2 mt-4">
          <motion.h1 
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 2.2, ease: [0.16, 1, 0.3, 1], delay: 0.4 }}
            className="text-[#D4AF37] text-[20vw] md:text-[180px] leading-none select-none px-4 md:px-12" 
            style={{ 
              fontFamily: '"Cinzel Decorative", serif', 
              fontWeight: 400, 
              letterSpacing: '0.1em' 
            }}
          >
            BASIR
          </motion.h1>
        </div>

        {/* ── 3. The Precision Structural Line ── */}
        <div className="relative mt-12 w-[80vw] md:w-[600px] h-[1px] bg-[#333333] overflow-hidden">
          <motion.div 
            initial={{ x: "-100%" }}
            animate={{ x: "100%" }}
            transition={{ duration: 3.5, ease: "easeInOut", delay: 0.8 }}
            className="absolute top-0 left-0 h-full w-full bg-[#D4AF37]"
          />
        </div>

        {/* ── 4. The Firm Designation ── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.7 }}
          transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1], delay: 1.5 }}
          className="mt-8 flex items-center justify-between w-[80vw] md:w-[600px] px-2"
        >
          <span 
            className="text-[#FFFFFF] text-[9px] tracking-[0.4em] uppercase" 
            style={{ fontFamily: '"Figtree", -apple-system, sans-serif', fontWeight: 500 }}
          >
            Al Tasnim Management
          </span>
          <span 
            className="text-[#FFFFFF] text-[9px] tracking-[0.4em] uppercase" 
            style={{ fontFamily: '"Figtree", -apple-system, sans-serif', fontWeight: 500 }}
          >
            Executive Intelligence
          </span>
        </motion.div>

      </div>
    </motion.div>
  );
}