'use client';
import { motion } from 'framer-motion';
import { useEffect } from 'react';

// ── AL TASNIM SPLASH SCREEN ──────────────────────────────────────────────────
// IBM Plex typography. Al Tasnim brand colors.
// Clean, institutional, premium.

export default function SplashScreen({ onComplete }: { onComplete: () => void }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onComplete();
    }, 4000);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 1, ease: "easeInOut" } }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0A1628] overflow-hidden"
    >
      <div className="flex flex-col items-center justify-center">
        
        {/* ── Arabic Mark ── */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="overflow-hidden pb-2"
        >
          <span 
            className="text-[#F5F1EB] text-3xl md:text-4xl font-light opacity-90"
            style={{ fontFamily: '"Noto Naskh Arabic", serif', letterSpacing: '0.05em' }}
          >
            بصير
          </span>
        </motion.div>

        {/* ── BASIR Product Name - Cinzel Decorative (Blackstone precision) ── */}
        <div className="overflow-visible pb-1 mt-2">
          <motion.h1 
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 2, ease: [0.16, 1, 0.3, 1], delay: 0.3 }}
            className="text-[#F5F1EB] text-[18vw] md:text-[140px] leading-none select-none px-4 md:px-8" 
            style={{ 
              fontFamily: '"Cinzel Decorative", "Cinzel", serif', 
              fontWeight: 400, 
              letterSpacing: '0.12em' 
            }}
          >
            BASIR
          </motion.h1>
        </div>

        {/* ── Brand Accent Line ── */}
        <div className="relative mt-8 w-[60vw] md:w-[400px] h-[2px] bg-[#1E3A5F] overflow-hidden">
          <motion.div 
            initial={{ x: "-100%" }}
            animate={{ x: "100%" }}
            transition={{ duration: 3, ease: "easeInOut", delay: 0.6 }}
            className="absolute top-0 left-0 h-full w-full bg-gradient-to-r from-transparent via-[#C9A96E] to-transparent"
          />
        </div>

        {/* ── Firm Designation ── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.5 }}
          transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1], delay: 1.2 }}
          className="mt-6 flex items-center justify-between w-[60vw] md:w-[400px] px-1"
          style={{ fontFamily: '"IBM Plex Sans", sans-serif' }}
        >
          <span className="text-[#8B9DAF] text-[8px] tracking-[0.35em] uppercase font-light">
            Al Tasnim Petroleum
          </span>
          <span className="text-[#C9A96E] text-[8px] tracking-[0.35em] uppercase font-light">
            Data Intelligence
          </span>
        </motion.div>

      </div>
    </motion.div>
  );
}