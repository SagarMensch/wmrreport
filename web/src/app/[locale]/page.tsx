// @ts-nocheck
'use client';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { Link } from '@/i18n/routing';
import SplashScreen from '@/components/SplashScreen';
import dynamic from 'next/dynamic';

// ── AL TASNIM BRAND COLORS ────────────────────────────────────────────────────
// Orange: #E87722 (Primary brand)
// Blue: #1E3A5F (Secondary brand)
// Navy: #0A1628 (Dark backgrounds)
// Light: #F8F9FA (Text)

// ── Blackstone-Tier WebGL Architecture ──
const AlTasnimTopography = dynamic(() => import('@/components/AlTasnimTopography'), {
  ssr: false,
  loading: () => <div className="absolute inset-0 bg-[#0A1628] -z-10" />
});

export default function Home() {
  const t = useTranslations('Index');
  const [showSplash, setShowSplash] = useState(true);

  return (
    <>
      <AnimatePresence mode="wait">
        {showSplash && <SplashScreen key="splash" onComplete={() => setShowSplash(false)} />}
      </AnimatePresence>

      <main className="relative w-full h-screen overflow-hidden flex flex-col justify-between selection:bg-[#C9A96E] selection:text-[#0A1628]" style={{ background: '#0A1628' }}>

        {/* ── 3D Corporate Topography Environment ── */}
        <div className="absolute inset-0 z-0">
          <AlTasnimTopography />
        </div>

        {/* ── Subtle Texture Overlay ── */}
        <div 
          className="absolute inset-0 z-0 pointer-events-none opacity-30"
          style={{ 
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23C9A96E' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />

        {/* ── Precision Gradient Mask (Brings Typography Forward) ── */}
        <div className="absolute inset-0 z-0 pointer-events-none" style={{ background: 'radial-gradient(ellipse at center, rgba(10,22,40,0.4) 0%, rgba(10,22,40,0.95) 100%)' }} />

        {/* ── AL TASNIM COLOR FLOW - Orange sweep on load ── */}
        <motion.div 
          initial={{ x: '-100%', opacity: 0 }}
          animate={{ x: '100%', opacity: [0, 0.4, 0.4, 0] }}
          transition={{ duration: 2.5, delay: 0.3, ease: 'easeInOut' }}
          className="absolute top-0 left-0 w-full h-full pointer-events-none z-0"
          style={{
            background: 'linear-gradient(90deg, transparent 0%, #E87722 50%, transparent 100%)',
            opacity: 0.08
          }}
        />

        {/* ── STRICT INSTITUTIONAL HEADER ── */}
        <header className="absolute top-0 w-full flex justify-between items-start z-10 px-8 py-10 md:px-16 md:py-12 pointer-events-none">
          {/* Left: Al Tasnim Global Mark */}
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: showSplash ? 0 : 1, y: showSplash ? -10 : 0 }}
            transition={{ duration: 1.5, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col items-start gap-2"
          >
            {/* Al Tasnim Logo - Original with enhancement */}
            <div className="flex items-center gap-4">
              <div className="relative">
                <img 
                  src="https://i.postimg.cc/yY7PfFWk/1631309767639-1-removebg-preview.png" 
                  alt="Al Tasnim Group"
                  className="h-14 md:h-16 w-auto object-contain"
                  style={{ filter: 'brightness(1.2) contrast(1.1)' }}
                />
                <div className="absolute inset-0 rounded-lg" style={{ boxShadow: '0 0 30px rgba(232,119,34,0.2)' }} />
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-[13px] text-[#FFFFFF] font-semibold tracking-[0.12em] uppercase">Al Tasnim</span>
                <span className="text-[9px] text-[#E87722] tracking-[0.2em] uppercase font-medium">Petroleum Operations</span>
              </div>
            </div>
          </motion.div>

          {/* Right: Security Designation */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: showSplash ? 0 : 1 }}
            transition={{ duration: 1.5, delay: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col text-right"
            style={{ fontFamily: '"Figtree", sans-serif' }}
          >
            <span className="text-[11px] text-[#B0B0B0] uppercase tracking-[0.25em] font-medium">Network: V-22</span>
            <span className="mt-2 text-[11px] text-[#E87722] uppercase tracking-[0.25em] font-semibold">Secure Session</span>
          </motion.div>
        </header>

        {/* ── CENTRAL EXECUTIVE ORACLE ── */}
        <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
          <motion.div 
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: showSplash ? 0 : 1, scale: showSplash ? 0.98 : 1 }}
            transition={{ duration: 2.0, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
            className="flex flex-col items-center w-full"
          >
            {/* Dual-Language Typography - Premium Minimal */}
            <div className="flex flex-col md:flex-row items-center justify-center gap-6 md:gap-14 px-4">
              {/* Arabic Mark */}
              <span 
                className="font-normal outline-none"
                style={{ 
                  fontFamily: '"Noto Naskh Arabic", serif', 
                  fontSize: 'clamp(3rem, 5vw, 5rem)', 
                  letterSpacing: '0.05em',
                  color: '#FFFFFF',
                  textShadow: '0 0 40px rgba(255,255,255,0.3)'
                }}
              >
                بصير
              </span>
              
              {/* Separator */}
              <span 
                className="hidden md:block font-light" 
                style={{ 
                  fontSize: 'clamp(2rem, 4vw, 4rem)', 
                  color: '#E87722',
                  textShadow: '0 0 20px rgba(232,119,34,0.4)'
                }}
              >
                |
              </span>
              
              {/* BASIR - Bright White with subtle glow */}
              <span 
                className="uppercase outline-none px-2"
                style={{ 
                  fontFamily: '"Cinzel Decorative", "Cinzel", serif', 
                  fontSize: 'clamp(4rem, 10vw, 10rem)', 
                  letterSpacing: '0.2em',
                  fontWeight: 400,
                  color: '#FFFFFF',
                  textShadow: '0 0 60px rgba(255,255,255,0.3)'
                }}
              >
                BASIR
              </span>
            </div>

            {/* Subtitle */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: showSplash ? 0 : 0.8 }}
              transition={{ duration: 1.5, delay: 0.8 }}
              className="mt-6 text-[11px] uppercase tracking-[0.5em]"
              style={{ fontFamily: '"Figtree", sans-serif', color: '#C9A96E', fontWeight: 500 }}
            >
              Executive Data Intelligence
            </motion.p>

            {/* Flowing brand line */}
            <motion.div 
              initial={{ scaleX: 0, opacity: 0 }}
              animate={{ scaleX: showSplash ? 0 : 1, opacity: showSplash ? 0 : 0.6 }}
              transition={{ duration: 2, delay: 1 }}
              className="mt-8 w-32 h-[1px] origin-center"
              style={{ background: '#C9A96E' }}
            />

            {/* Refined Entry Button - Solid Orange on Hover */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: showSplash ? 0 : 1, y: showSplash ? 10 : 0 }}
              transition={{ duration: 1.5, delay: 1.2, ease: [0.16, 1, 0.3, 1] }}
            >
              <Link
                href="/login"
                className="mt-16 pointer-events-auto relative group overflow-hidden border-2 border-[#C9A96E] bg-transparent hover:bg-[#C9A96E] hover:border-[#C9A96E] text-[#FFFFFF] hover:text-[#0A1628] py-4 px-16 transition-all duration-300 flex items-center justify-center"
              >
                <span
                  className="text-[10px] uppercase tracking-[0.4em]"
                  style={{ fontFamily: '"Figtree", sans-serif', fontWeight: 600 }}
                >
                  {t('enter') || 'Enter Basir'}
                </span>
              </Link>
            </motion.div>
          </motion.div>
        </div>

        {/* ── INSTITUTIONAL FOOTER ── */}
        <footer className="absolute bottom-0 w-full z-10 flex justify-between items-end px-8 py-10 md:px-16 md:py-12 pointer-events-none">
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: showSplash ? 0 : 0.8 }}
            transition={{ duration: 1.5, delay: 1, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col gap-1.5"
            style={{ fontFamily: '"Figtree", sans-serif' }}
          >
             <span className="text-[10px] uppercase tracking-[0.3em] text-[#FFFFFF] font-medium">Al Tasnim Petroleum Operations</span>
             <span className="text-[9px] uppercase tracking-[0.25em] text-[#B0B0B0]">Executive Data Intelligence</span>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: showSplash ? 0 : 0.9 }}
            transition={{ duration: 1.5, delay: 1, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col items-end gap-1.5"
            style={{ fontFamily: '"Figtree", sans-serif' }}
          >
            <span 
              className="text-[#C9A96E]" 
              style={{ fontFamily: '"Noto Naskh Arabic", serif', letterSpacing: '0.1em', fontSize: '14px' }}
            >
              مبني بواسطة
            </span>
            <span className="text-[10px] uppercase tracking-[0.3em] text-[#FFFFFF] font-medium">Sequelstring AI</span>
          </motion.div>
        </footer>

      </main>
    </>
  );
}