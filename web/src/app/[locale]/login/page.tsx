'use client';
import { useTranslations } from 'next-intl';
import { useState } from 'react';
import { useRouter } from '@/i18n/routing';
import { motion, AnimatePresence } from 'framer-motion';
import { useLoginStore } from '@/store/useLoginStore';

// ── THE INSTITUTIONAL VAULT PORTAL ──────────────────────────────────────────
// A multi-million dollar terminal does not use "rusty pipe" 3D graphics.
// It uses absolute, severe containment. Pure black workspace. Flawless symmetry.
// A singular, undeniable entry point.

const VALID_USER = 'admin';
const VALID_PASS = 'admin123';

export default function LoginPage() {
  const t = useTranslations('Login');
  const router = useRouter();
  const setFormState = useLoginStore((state) => state.setFormState);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsAuthenticating(true);
    setFormState('submit');

    // Brutally efficient loading state (1.5s visual hold for tension/power)
    setTimeout(() => {
      if (email === VALID_USER && password === VALID_PASS) {
        setFormState('success');
        // Flash green verification sequence then transport to Dashboard
        setTimeout(() => router.push('/dashboard'), 800);
      } else {
        setIsAuthenticating(false);
        setFormState('error');
        setError('UNAUTHORIZED CREDENTIALS. USE ADMIN / ADMIN123.');
      }
    }, 1500);
  };

  const handleBlur = () => {
    setTimeout(() => {
      const activeTag = document.activeElement?.tagName;
      if (activeTag !== 'INPUT' && activeTag !== 'BUTTON') setFormState('idle');
    }, 50);
  };

  return (
    <div className="relative w-full h-screen bg-[#000000] overflow-hidden flex flex-col items-center justify-center selection:bg-[#8AB4F8] selection:text-[#000000]">
      
      {/* ── IMMENSE BACKGROUND DEPTH ── */}
      {/* Absolute monolithic darkness with a single radial gradient focusing the user */}
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,rgba(138,180,248,0.03)_0%,rgba(0,0,0,1)_80%)]" />

      {/* ── THE SECURITY TERMINAL ── */}
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
        className="z-10 flex flex-col items-center w-full max-w-[420px] px-8"
      >
        {/* Core Identity Mark (Logo & Signature) */}
        <div className="flex flex-col items-center gap-8 mb-16">
          <img 
            src="https://i.postimg.cc/yY7PfFWk/1631309767639-1-removebg-preview.png" 
            alt="Al Tasnim Group"
            className="h-20 md:h-28 w-auto opacity-100 object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]"
          />
          <span 
            className="text-[#F5F5F5] text-4xl font-light"
            style={{ fontFamily: '"Noto Naskh Arabic", sans-serif', letterSpacing: '0.05em' }}
          >
            التحقق من الوصول
          </span>
        </div>

        {/* The Exacting Data Form */}
        <form onSubmit={handleSubmit} className="w-full flex flex-col gap-10">
          
          {/* Identity Vector */}
          <div className="flex flex-col gap-2 relative group">
            <label
              className="text-[9px] uppercase tracking-[0.3em] text-[#F5F5F5]/40"
              style={{ fontFamily: '"Figtree", sans-serif', fontWeight: 600 }}
            >
              System Identity
            </label>
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onFocus={() => setFormState(email ? 'email-typing' : 'email-focused')}
              onKeyDown={() => setFormState('email-typing')}
              onBlur={handleBlur}
              placeholder="admin"
              disabled={isAuthenticating}
              className="w-full bg-transparent outline-none border-b border-[#333333] py-2 text-[#F5F5F5] placeholder:text-[#F5F5F5]/20 focus:border-[#8AB4F8] transition-colors text-sm disabled:opacity-50"
              style={{ fontFamily: '"Figtree", sans-serif' }}
            />
          </div>

          {/* Cryptographic Key */}
          <div className="flex flex-col gap-2 relative group">
            <label
              className="text-[9px] uppercase tracking-[0.3em] text-[#F5F5F5]/40"
              style={{ fontFamily: '"Figtree", sans-serif', fontWeight: 600 }}
            >
              Cryptographic Key
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onFocus={() => setFormState(password ? 'password-typing' : 'password-focused')}
              onKeyDown={() => setFormState('password-typing')}
              onBlur={handleBlur}
              placeholder="••••••••"
              disabled={isAuthenticating}
              className="w-full bg-transparent outline-none border-b border-[#333333] py-2 text-[#8AB4F8] placeholder:text-[#F5F5F5]/20 focus:border-[#8AB4F8] transition-colors text-lg tracking-[0.3em] font-mono disabled:opacity-50"
            />
          </div>

          {/* Error State */}
          <AnimatePresence mode="wait">
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="text-[#E02424] text-[9px] uppercase tracking-[0.2em] font-medium"
                style={{ fontFamily: '"Figtree", sans-serif' }}
              >
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Submission Execution */}
          <motion.div className="mt-8 overflow-hidden relative" whileTap={{ scale: 0.98 }}>
            <button
              type="submit"
              disabled={isAuthenticating || !email || !password}
              className="w-full border border-[#FFFFFF] bg-transparent text-[#FFFFFF] py-4 uppercase tracking-[0.5em] text-[10px] font-medium transition-all hover:bg-[#FFFFFF] hover:text-[#000000] disabled:border-[#333333] disabled:text-[#333333] disabled:hover:bg-transparent"
              style={{ fontFamily: '"Figtree", sans-serif' }}
            >
              {isAuthenticating ? 'Executing Protocol...' : 'Authenticate'}
            </button>
            
            {/* Loading line overlay */}
            <AnimatePresence>
              {isAuthenticating && (
                <motion.div 
                  initial={{ x: "-100%" }}
                  animate={{ x: "100%" }}
                  transition={{ duration: 1.5, ease: "linear", repeat: Infinity }}
                  className="absolute bottom-0 left-0 w-full h-[2px] bg-[#FFFFFF]"
                />
              )}
            </AnimatePresence>
          </motion.div>
          
        </form>
      </motion.div>

    </div>
  );
}