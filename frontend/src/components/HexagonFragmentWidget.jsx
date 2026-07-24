import { useState } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

const MODULES = [
  { id: 'ai', name: 'LAFM_AI', status: 'ACTIVE', color: '#00f2fe' },
  { id: 'feed', name: 'LIVE_FEED', status: 'STREAMING', color: '#00ff88' },
  { id: 'engine', name: 'TRADING_ENGINE', status: 'READY', color: '#ffaa00' },
  { id: 'security', name: 'SECURITY', status: 'ARMED', color: '#ff0066' },
  { id: 'storage', name: 'STORAGE', status: 'SYNCED', color: '#aa66ff' },
  { id: 'network', name: 'NETWORK', status: 'CONNECTED', color: '#00f2fe' },
];

const HEX_PATH = 'M 50 5 L 95 27.5 L 95 72.5 L 50 95 L 5 72.5 L 5 27.5 Z';

export default function HexagonFragmentWidget({ moduleId = 'ai' }) {
  const [hovered, setHovered] = useState(false);
  const module = MODULES.find(m => m.id === moduleId) || MODULES[0];

  const springConfig = { stiffness: 300, damping: 20 };
  const hoverSpring = useSpring(0, springConfig);
  const fragmentOffset = useTransform(hoverSpring, [0, 1], [0, 8]);

  const lineVariants = {
    idle: { x: 0, y: 0, opacity: 0.6 },
    hover: (i) => ({
      x: Math.cos((i * Math.PI) / 3) * 8,
      y: Math.sin((i * Math.PI) / 3) * 8,
      opacity: 1,
      transition: { type: 'spring', stiffness: 300, damping: 20, delay: i * 0.03 }
    })
  };

  const dotVariants = {
    idle: { scale: 1, opacity: 0.8 },
    hover: {
      scale: [1, 1.4, 1],
      opacity: 1,
      transition: { duration: 0.6, repeat: Infinity, ease: 'easeInOut' }
    }
  };

  const corners = [
    { x: 50, y: 5 },
    { x: 95, y: 27.5 },
    { x: 95, y: 72.5 },
    { x: 50, y: 95 },
    { x: 5, y: 72.5 },
    { x: 5, y: 27.5 },
  ];

  return (
    <motion.div
      className="relative w-48 h-48 cursor-pointer"
      onHoverStart={() => { setHovered(true); hoverSpring.set(1); }}
      onHoverEnd={() => { setHovered(false); hoverSpring.set(0); }}
      animate={{ scale: hovered ? 1.05 : 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
    >
      <svg viewBox="0 0 100 100" className="w-full h-full">
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2.5" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {corners.map((corner, i) => (
          <motion.line
            key={i}
            x1="50"
            y1="50"
            x2={corner.x}
            y2={corner.y}
            stroke={module.color}
            strokeWidth="1.5"
            strokeLinecap="round"
            variants={lineVariants}
            animate={hovered ? 'hover' : 'idle'}
            custom={i}
            filter="url(#glow)"
            style={{ pathLength: useTransform(hoverSpring, [0, 1], [1, 0.85]) }}
          />
        ))}

        <motion.circle
          cx="50"
          cy="50"
          r="3"
          fill={module.color}
          variants={dotVariants}
          animate={hovered ? 'hover' : 'idle'}
          filter="url(#glow)"
        />

        {corners.map((corner, i) => (
          <motion.circle
            key={`corner-${i}`}
            cx={corner.x}
            cy={corner.y}
            r="2"
            fill={module.color}
            opacity="0.6"
            variants={dotVariants}
            animate={hovered ? 'hover' : 'idle'}
            filter="url(#glow)"
          />
        ))}
      </svg>

      <motion.div
        className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
        animate={{ opacity: hovered ? 1 : 0.7 }}
        transition={{ duration: 0.2 }}
      >
        <div className="lafm-badge">
          <span className="w-1.5 h-1.5 rounded-full bg-lafm-accent animate-pulse" />
          {module.status}
        </div>
        <div className="text-[10px] font-mono text-lafm-muted mt-1 tracking-widest">
          {module.name}
        </div>
      </motion.div>
    </motion.div>
  );
}
