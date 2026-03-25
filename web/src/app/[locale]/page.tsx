// @ts-nocheck
'use client';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { Link } from '@/i18n/routing';
import SplashScreen from '@/components/SplashScreen';
import dynamic from 'next/dynamic';

// ── Blackstone-Tier WebGL Architecture ──
const AlTasnimTopography = dynamic(() => import('@/components/AlTasnimTopography'), {
  ssr: false,
  loading: () => <div className="absolute inset-0 bg-[#000000] -z-10" />
});

export default function Home() {
  const t = useTranslations('Index');
  const [showSplash, setShowSplash] = useState(true);

  return (
    <>
      <AnimatePresence mode="wait">
        {showSplash && <SplashScreen key="splash" onComplete={() => setShowSplash(false)} />}
      </AnimatePresence>

      <main className="relative w-full h-screen overflow-hidden flex flex-col justify-between bg-[#000000] selection:bg-[#D4AF37] selection:text-[#000000]">

        {/* ── 3D Corporate Topography Environment ── */}
        <div className="absolute inset-0 z-0">
          <AlTasnimTopography />
        </div>

        {/* ── Precision Gradient Mask (Brings Typography Forward) ── */}
        <div className="absolute inset-0 z-0 pointer-events-none bg-[radial-gradient(circle_at_center,rgba(0,0,0,0.0)_0%,rgba(0,0,0,0.95)_100%)]" />

        {/* ── STRICT INSTITUTIONAL HEADER ── */}
        <header className="absolute top-0 w-full flex justify-between items-start z-10 px-8 py-10 md:px-16 md:py-12 pointer-events-none">
          {/* Left: Al Tasnim Global Mark (Official Corporate Seal) */}
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: showSplash ? 0 : 1, y: showSplash ? -10 : 0 }}
            transition={{ duration: 1.5, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col"
          >
            <img 
              src="https://i.postimg.cc/yY7PfFWk/1631309767639-1-removebg-preview.png" 
              alt="Al Tasnim Group"
              className="h-16 md:h-20 w-auto opacity-100 object-contain drop-shadow-[0_0_15px_rgba(212,175,55,0.2)]"
            />
          </motion.div>

          {/* Right: Security & Network Designation */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: showSplash ? 0 : 0.6 }}
            transition={{ duration: 1.5, delay: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col text-right text-[9px] text-[#F5F5F5] uppercase tracking-[0.5em] font-medium"
            style={{ fontFamily: '"Figtree", sans-serif' }}
          >
            <span>Network: V-22</span>
            <span className="mt-2 text-[#D4AF37]">Secure Session</span>
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
            {/* Flawless Dual-Language Signature Typography */}
            <div className="flex flex-col md:flex-row items-center justify-center gap-6 md:gap-14 text-[#D4AF37] mix-blend-screen px-4">
              <span 
                className="font-light outline-none"
                style={{ fontFamily: '"Noto Naskh Arabic", sans-serif', fontSize: 'clamp(3.5rem, 6vw, 6rem)', letterSpacing: '0.05em' }}
              >
                بصير
              </span>
              
              <span className="hidden md:block text-[#D4AF37]/20 font-light" style={{ fontSize: 'clamp(2rem, 5vw, 5rem)' }}>|</span>
              
              <span 
                className="uppercase outline-none px-4"
                style={{ fontFamily: '"Cinzel Decorative", serif', fontSize: 'clamp(4rem, 9vw, 9rem)', letterSpacing: '0.1em' }}
              >
                BASIR
              </span>
            </div>

            {/* The Unyielding Corporate Entry Terminal */}
            <Link
              href="/login"
              className="mt-24 pointer-events-auto relative group overflow-hidden border border-[#D4AF37]/20 bg-[#000000] hover:bg-[#D4AF37]/5 text-[#F5F5F5] py-5 px-16 transition-all duration-700 flex items-center justify-center"
            >
              {/* Ultra-subtle hover line tracking */}
              <div className="absolute bottom-0 left-0 w-full h-[1px] bg-[#D4AF37] scale-x-0 group-hover:scale-x-100 origin-left transition-transform duration-700 ease-[0.16,1,0.3,1]" />
              
              <span
                className="text-[10px] uppercase tracking-[0.6em] transition-colors group-hover:text-[#D4AF37]"
                style={{ fontFamily: '"Figtree", sans-serif', fontWeight: 500 }}
              >
                {t('enter') || 'Enter Intelligence Terminal'}
              </span>
            </Link>
          </motion.div>
        </div>

        {/* ── STRICT INSTITUTIONAL FOOTER ── */}
        <footer className="absolute bottom-0 w-full z-10 flex justify-between items-end px-8 py-10 md:px-16 md:py-12 pointer-events-none">
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: showSplash ? 0 : 0.5 }}
            transition={{ duration: 1.5, delay: 1, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col gap-2 text-[9px] uppercase tracking-[0.5em] text-[#F5F5F5]"
            style={{ fontFamily: '"Figtree", sans-serif', fontWeight: 500 }}
          >
             <span>Al Tasnim Management</span>
             <span>Executive Data Architecture</span>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: showSplash ? 0 : 0.8 }}
            transition={{ duration: 1.5, delay: 1, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col items-end gap-2 text-[9px] text-[#F5F5F5] uppercase tracking-[0.5em]"
            style={{ fontFamily: '"Figtree", sans-serif', fontWeight: 500 }}
          >
            <span className="text-[#D4AF37]" style={{ fontFamily: '"Noto Naskh Arabic", sans-serif', letterSpacing: '0.1em', fontSize: '11px' }}>مبني بواسطة</span>
            <span>Sequelstring AI</span>
          </motion.div>
        </footer>

      </main>
    </>
  );
}