import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const LETTERS = ['L', 'A', 'F', 'M', '.'];
const HEX_PATH = 'M 50 5 L 95 27.5 L 95 72.5 L 50 95 L 5 72.5 L 5 27.5 Z';

export default function SplashScreen({ onComplete }) {
  const [phase, setPhase] = useState('loading');
  const [showHex, setShowHex] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => setShowHex(true), 500);
    const t2 = setTimeout(() => setPhase('ready'), 2500);
    const t3 = setTimeout(() => onComplete?.(), 3500);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [onComplete]);

  return (
    <motion.div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-lafm-bg"
      exit={{ opacity: 0, scale: 1.1 }}
      transition={{ duration: 0.6 }}
    >
      <div className="relative w-64 h-64 flex items-center justify-center">
        <AnimatePresence>
          {showHex && (
            <motion.svg
              viewBox="0 0 100 100"
              className="absolute w-40 h-40"
              initial={{ opacity: 0, rotate: -90, scale: 0.5 }}
              animate={{ opacity: 1, rotate: 0, scale: 1 }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
            >
              <motion.path
                d={HEX_PATH}
                fill="none"
                stroke="#00f2fe"
                strokeWidth="1.5"
                strokeDasharray="400"
                strokeDashoffset="400"
                animate={{ strokeDashoffset: 0 }}
                transition={{ duration: 1.5, ease: 'easeInOut' }}
                filter="url(#glow)"
              />
              <defs>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                  <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>
            </motion.svg>
          )}
        </AnimatePresence>

        <div className="relative flex items-end gap-1">
          {LETTERS.map((letter, i) => (
            <motion.span
              key={letter}
              className="text-5xl font-bold font-mono text-lafm-accent lafm-glow-text"
              initial={{ opacity: 0, y: 30, rotateX: -90 }}
              animate={{ opacity: 1, y: 0, rotateX: 0 }}
              transition={{
                delay: 1.2 + i * 0.1,
                type: 'spring',
                stiffness: 200,
                damping: 15
              }}
            >
              {letter}
            </motion.span>
          ))}
        </div>
      </div>

      <motion.div
        className="mt-8 text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2 }}
      >
        <div className="lafm-badge mb-2">
          <span className="w-1.5 h-1.5 rounded-full bg-lafm-accent animate-pulse" />
          CORE_SYSTEM // v2.0.26
        </div>
        <div className="text-xs font-mono text-lafm-muted tracking-wider">
          EDGE AI TRADING TERMINAL
        </div>
      </motion.div>

      <motion.div
        className="absolute bottom-12 left-1/2 -translate-x-1/2"
        initial={{ opacity: 0 }}
        animate={{ opacity: phase === 'ready' ? 0 : 1 }}
      >
        <div className="w-48 h-1 bg-lafm-border rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-lafm-accent"
            animate={{ width: phase === 'ready' ? '100%' : '60%' }}
            transition={{ duration: 2, ease: 'easeInOut' }}
          />
        </div>
        <div className="text-[10px] font-mono text-lafm-muted mt-2 text-center tracking-widest">
          {phase === 'ready' ? 'SYSTEM READY' : 'INITIALIZING NEURAL ENGINE...'}
        </div>
      </motion.div>
    </motion.div>
  );
}
