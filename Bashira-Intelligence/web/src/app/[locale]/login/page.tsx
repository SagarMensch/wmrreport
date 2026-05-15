'use client';
import { useTranslations } from 'next-intl';
import { useState } from 'react';
import { useRouter } from '@/i18n/routing';
import { motion, AnimatePresence } from 'framer-motion';
import { useLoginStore } from '@/store/useLoginStore';

// ── BLACKSTONE PREMIUM AUTHENTICATION TERMINAL ─────────────────────────────
// Solid, institutional, premium. Clean navy background with subtle texture.
// White cards with soft shadows. Clear typography hierarchy.

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

    setTimeout(() => {
      if (email === VALID_USER && password === VALID_PASS) {
        setFormState('success');
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
    <div 
      className="relative w-full h-screen overflow-hidden flex flex-col items-center justify-center selection:bg-[#E87722] selection:text-[#FFFFFF]"
      style={{ 
        background: 'linear-gradient(180deg, #0A1628 0%, #0D1B2A 100%)',
        fontFamily: '"Figtree", sans-serif'
      }}
    >
      {/* ── Subtle Texture ── */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-20"
        style={{ 
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23C9A96E' fill-opacity='0.04'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }}
      />

      {/* ── Radial Focus ── */}
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,rgba(232,119,34,0.05)_0%,transparent_50%)]" />

      {/* ── THE SECURITY TERMINAL CARD ── */}
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
        className="z-10 flex flex-col items-center w-full max-w-[440px] px-8"
      >
        {/* Login Card */}
        <div 
          className="w-full bg-[#FFFFFF] rounded-xl p-10"
          style={{ boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)' }}
        >
          {/* Logo & Title */}
          <div className="flex flex-col items-center gap-6 mb-10">
            <img 
              src="https://i.postimg.cc/yY7PfFWk/1631309767639-1-removebg-preview.png" 
              alt="Al Tasnim Group"
              className="h-16 md:h-20 w-auto object-contain"
              style={{ filter: 'brightness(1.1)' }}
            />
            <div className="text-center">
              <span 
                className="text-[#1A1A1A] text-3xl font-normal block"
                style={{ fontFamily: '"Noto Naskh Arabic", serif', letterSpacing: '0.05em' }}
              >
                التحقق من الوصول
              </span>
              <span className="text-[10px] text-[#6B6B6B] uppercase tracking-[0.2em] font-medium mt-2 block">
                Secure Authentication
              </span>
            </div>
          </div>

          {/* The Form */}
          <form onSubmit={handleSubmit} className="w-full flex flex-col gap-6">
            
            {/* Identity Input */}
            <div className="flex flex-col gap-2">
              <label className="text-[10px] uppercase tracking-[0.2em] text-[#6B6B6B] font-semibold">
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
                className="w-full bg-[#F8F6F3] outline-none border border-[#E5E0D8] rounded-lg px-4 py-3 text-[#1A1A1A] placeholder:text-[#9A9A9A] focus:border-[#1A1A1A] transition-colors text-[14px] disabled:opacity-50"
              />
            </div>

            {/* Password Input */}
            <div className="flex flex-col gap-2">
              <label className="text-[10px] uppercase tracking-[0.2em] text-[#6B6B6B] font-semibold">
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
                className="w-full bg-[#F8F6F3] outline-none border border-[#E5E0D8] rounded-lg px-4 py-3 text-[#1A1A1A] placeholder:text-[#9A9A9A] focus:border-[#1A1A1A] transition-colors text-[14px] tracking-[0.2em] disabled:opacity-50"
              />
            </div>

            {/* Error State */}
            <AnimatePresence mode="wait">
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-[#DC2626] text-[10px] uppercase tracking-[0.15em] font-semibold text-center py-2"
                >
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit Button */}
            <motion.div className="mt-6 overflow-hidden relative" whileTap={{ scale: 0.98 }}>
              <button
                type="submit"
                disabled={isAuthenticating || !email || !password}
                className="w-full border-2 border-[#1A1A1A] bg-[#1A1A1A] text-[#FFFFFF] py-3.5 rounded-lg uppercase tracking-[0.3em] text-[10px] font-semibold transition-all hover:bg-[#333333] hover:border-[#333333] disabled:opacity-40 disabled:hover:bg-[#1A1A1A]"
              >
                {isAuthenticating ? 'Executing Protocol...' : 'Authenticate'}
              </button>
              
              {/* Loading animation */}
              <AnimatePresence>
                {isAuthenticating && (
                  <motion.div 
                    initial={{ x: "-100%" }}
                    animate={{ x: "100%" }}
                    transition={{ duration: 1.5, ease: "linear", repeat: Infinity }}
                    className="absolute bottom-0 left-0 w-full h-[2px] bg-[#E87722]"
                  />
                )}
              </AnimatePresence>
            </motion.div>
            
          </form>
        </div>

        {/* Footer Info */}
        <div className="mt-8 text-center">
          <span className="text-[9px] text-[#B0B0B0] uppercase tracking-[0.3em]">Al Tasnim Petroleum Operations</span>
        </div>
      </motion.div>

    </div>
  );
}
