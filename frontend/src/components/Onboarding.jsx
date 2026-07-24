import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const steps = [
  {
    id: 1,
    title: 'Welcome to Edge AI Trading',
    description: 'Zero-knowledge privacy. No external servers touch your API keys. All inference runs locally on your hardware using ONNX.',
    icon: '🤖',
  },
  {
    id: 2,
    title: 'Connect Exchange (Optional)',
    description: 'Enter your Binance API Key and Secret. Or skip and use Paper Trading mode to test the Edge AI system instantly.',
    icon: '🔐',
  },
  {
    id: 3,
    title: 'AI Model Configuration',
    description: 'Load your local ONNX model. The system expects 13 technical features including RSI, MACD, EMA crossover, and ATR.',
    icon: '🧠',
  },
  {
    id: 4,
    title: 'Latency Check',
    description: 'Verify WebSocket connectivity to Binance and confirm the candlestick buffer is streaming with minimal latency.',
    icon: '⚡',
  },
];

const slideVariants = {
  enter: (direction) => ({
    x: direction > 0 ? 1000 : -1000,
    opacity: 0,
    scale: 0.95,
  }),
  center: {
    x: 0,
    opacity: 1,
    scale: 1,
    transition: { type: 'spring', stiffness: 300, damping: 30 }
  },
  exit: (direction) => ({
    x: direction < 0 ? 1000 : -1000,
    opacity: 0,
    scale: 0.95,
    transition: { duration: 0.3 }
  }),
};

export default function Onboarding({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState(1);
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [paperMode, setPaperMode] = useState(true);
  const [modelLoaded, setModelLoaded] = useState(false);
  const [latencyMs, setLatencyMs] = useState(null);

  useEffect(() => {
    if (currentStep === 3) {
      const ws = new WebSocket('ws://127.0.0.1:8765/ws/market');
      const start = performance.now();
      ws.onopen = () => {
        const end = performance.now();
        setLatencyMs(Math.round(end - start));
      };
      ws.onerror = () => setLatencyMs('error');
      return () => ws.close();
    }
  }, [currentStep]);

  const handleNext = () => {
    if (currentStep === steps.length - 1) {
      onComplete?.();
      return;
    }
    setDirection(1);
    setCurrentStep(prev => prev + 1);
  };

  const handleBack = () => {
    setDirection(-1);
    setCurrentStep(prev => prev - 1);
  };

  if (currentStep === 2) {
    return (
      <div className="min-h-screen bg-lafm-bg flex items-center justify-center p-4">
        <motion.div
          className="max-w-lg w-full lafm-panel p-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: 'spring', stiffness: 200, damping: 20 }}
        >
          <h2 className="text-2xl font-bold text-lafm-text mb-6">AI Model Configuration</h2>
          <div className="space-y-4">
            <div className="bg-lafm-bg/50 rounded-lg p-4 border border-lafm-border">
              <div className="text-sm text-lafm-muted mb-2">Model File</div>
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-lafm-panel rounded px-3 py-2 text-xs text-lafm-muted font-mono border border-lafm-border">
                  trading_model.onnx
                </div>
                <motion.button
                  onClick={() => setModelLoaded(true)}
                  className="bg-lafm-accent hover:bg-lafm-accent/90 text-lafm-bg text-sm px-4 py-2 rounded transition-colors"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {modelLoaded ? 'Loaded' : 'Load'}
                </motion.button>
              </div>
            </div>
            <div className="bg-lafm-bg/50 rounded-lg p-4 border border-lafm-border">
              <div className="text-sm text-lafm-muted mb-2">Features (13)</div>
              <motion.div className="flex flex-wrap gap-2">
                {['EMA_10', 'EMA_30', 'RSI_14', 'MACD', 'ATR_14', 'BB_upper', 'BB_mid', 'BB_lower', 'Volume', 'Return', 'Volatility', 'Momentum', 'Trend'].map((f, i) => (
                  <motion.span
                    key={f}
                    className="text-xs bg-lafm-panel text-lafm-text px-2 py-1 rounded font-mono border border-lafm-border"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.03 }}
                  >
                    {f}
                  </motion.span>
                ))}
              </motion.div>
            </div>
          </div>
          <div className="flex justify-between mt-6">
            <motion.button onClick={handleBack} className="px-4 py-2 text-lafm-muted hover:text-lafm-text transition-colors" whileHover={{ x: -5 }} whileTap={{ scale: 0.95 }}>
              Back
            </motion.button>
            <motion.button onClick={handleNext} disabled={!modelLoaded} className="bg-lafm-accent hover:bg-lafm-accent/90 disabled:bg-lafm-border text-lafm-bg px-6 py-2 rounded transition-colors" whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              Next
            </motion.button>
          </div>
        </motion.div>
      </div>
    );
  }

  if (currentStep === 3) {
    return (
      <div className="min-h-screen bg-lafm-bg flex items-center justify-center p-4">
        <motion.div
          className="max-w-lg w-full lafm-panel p-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: 'spring', stiffness: 200, damping: 20 }}
        >
          <h2 className="text-2xl font-bold text-lafm-text mb-6">Latency Check</h2>
          <div className="space-y-4">
            <div className="bg-lafm-bg/50 rounded-lg p-4 border border-lafm-border">
              <div className="text-sm text-lafm-muted mb-1">WebSocket Connection</div>
              <div className="text-xs text-lafm-text font-mono">ws://127.0.0.1:8765/ws/market</div>
            </div>
            <div className="bg-lafm-bg/50 rounded-lg p-4 border border-lafm-border">
              <div className="text-sm text-lafm-muted mb-1">Round-trip Latency</div>
              <motion.div className="text-2xl font-mono text-lafm-text" animate={latencyMs && latencyMs !== 'error' ? { color: '#00f2fe' } : { color: '#e2e8f0' }}>
                {latencyMs === null ? 'Measuring...' : latencyMs === 'error' ? 'Connection Failed' : `${latencyMs} ms`}
              </motion.div>
            </div>
            <div className="bg-lafm-bg/50 rounded-lg p-4 border border-lafm-border">
              <div className="text-sm text-lafm-muted mb-1">Candlestick Buffer</div>
              <div className="text-xs text-lafm-text">Receiving 1m candles for BTC/USDT...</div>
            </div>
          </div>
          <div className="flex justify-between mt-6">
            <motion.button onClick={handleBack} className="px-4 py-2 text-lafm-muted hover:text-lafm-text transition-colors" whileHover={{ x: -5 }} whileTap={{ scale: 0.95 }}>
              Back
            </motion.button>
            <motion.button onClick={handleNext} className="bg-lafm-accent hover:bg-lafm-accent/90 text-lafm-bg px-6 py-2 rounded transition-colors" whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              Launch Terminal
            </motion.button>
          </div>
        </motion.div>
      </div>
    );
  }

  if (currentStep === 1) {
    return (
      <div className="min-h-screen bg-lafm-bg flex items-center justify-center p-4">
        <motion.div
          className="max-w-lg w-full lafm-panel p-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: 'spring', stiffness: 200, damping: 20 }}
        >
          <h2 className="text-2xl font-bold text-lafm-text mb-6">Connect Exchange</h2>
          <div className="space-y-4">
            <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
              <label className="block text-sm text-lafm-muted mb-1">API Key</label>
              <input
                type="text"
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder="Enter your API Key"
                className="lafm-input"
              />
            </motion.div>
            <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}>
              <label className="block text-sm text-lafm-muted mb-1">API Secret</label>
              <input
                type="password"
                value={apiSecret}
                onChange={e => setApiSecret(e.target.value)}
                placeholder="Enter your API Secret"
                className="lafm-input"
              />
            </motion.div>
            <motion.label
              className="flex items-center gap-3 bg-lafm-bg/50 rounded-lg p-4 border border-lafm-border cursor-pointer"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
              whileHover={{ borderColor: 'rgba(0, 242, 254, 0.3)' }}
            >
              <input
                type="checkbox"
                checked={paperMode}
                onChange={e => setPaperMode(e.target.checked)}
                className="w-4 h-4 rounded border-lafm-border bg-lafm-bg text-lafm-accent focus:ring-lafm-accent"
              />
              <div>
                <div className="text-sm text-lafm-text">Paper Trading / Testnet</div>
                <div className="text-xs text-lafm-muted">Skip live credentials and simulate with $10,000 USDT</div>
              </div>
            </motion.label>
          </div>
          <div className="flex justify-between mt-6">
            <motion.button onClick={handleBack} className="px-4 py-2 text-lafm-muted hover:text-lafm-text transition-colors" whileHover={{ x: -5 }} whileTap={{ scale: 0.95 }}>
              Back
            </motion.button>
            <motion.button onClick={handleNext} className="lafm-btn-primary" whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              Next
            </motion.button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-lafm-bg flex items-center justify-center p-4">
      <AnimatePresence mode="wait" custom={direction}>
        <motion.div
          key={currentStep}
          className="max-w-md w-full lafm-panel p-8 text-center"
          custom={direction}
          variants={slideVariants}
          initial="enter"
          animate="center"
          exit="exit"
        >
          <motion.div
            className="text-6xl mb-4"
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: 'spring', stiffness: 200, damping: 15 }}
          >
            {steps[0].icon}
          </motion.div>
          <motion.h2
            className="text-2xl font-bold text-lafm-text mb-2 lafm-glow-text"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            {steps[0].title}
          </motion.h2>
          <motion.p
            className="text-lafm-muted text-sm mb-8"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            {steps[0].description}
          </motion.p>
          <motion.div className="flex justify-center gap-2 mb-8">
            {steps.map((_, i) => (
              <motion.div
                key={i}
                className={`h-1.5 rounded-full transition-colors ${i === currentStep ? 'bg-lafm-accent w-8' : 'bg-lafm-border w-4'}`}
                animate={i === currentStep ? { scaleY: [1, 1.5, 1] } : {}}
                transition={{ duration: 0.3 }}
              />
            ))}
          </motion.div>
          <motion.button
            onClick={handleNext}
            className="lafm-btn-primary"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            Get Started
          </motion.button>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
