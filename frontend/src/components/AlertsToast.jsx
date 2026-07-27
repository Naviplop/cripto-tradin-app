import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function AlertsToast({ signals, account }) {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    if (!signals) return;
    const newAlerts = [];
    if (signals.signal === 'BUY' && signals.ai_probability > 0.75) {
      newAlerts.push({
        id: Date.now(),
        type: 'success',
        title: 'STRONG BUY',
        body: `AI probability ${(signals.ai_probability * 100).toFixed(1)}%`,
      });
    } else if (signals.signal === 'SELL' && signals.ai_probability > 0.75) {
      newAlerts.push({
        id: Date.now(),
        type: 'danger',
        title: 'STRONG SELL',
        body: `AI probability ${(signals.ai_probability * 100).toFixed(1)}%`,
      });
    }
    if (signals.atr_spike) {
      newAlerts.push({
        id: Date.now() + 1,
        type: 'warning',
        title: 'Volatility Spike',
        body: 'ATR breakout detected',
      });
    }
    if (newAlerts.length > 0) {
      setAlerts(prev => [...newAlerts, ...prev].slice(0, 5));
    }
  }, [signals]);

  useEffect(() => {
    if (!account) return;
    setAlerts(prev => {
      const exists = prev.find(a => a.title === 'ORDER EXECUTED');
      if (exists) return prev;
      return [{ id: Date.now(), type: 'info', title: 'ORDER EXECUTED', body: `Positions: ${account.positions_count}` }, ...prev].slice(0, 5);
    });
  }, [account?.positions_count]);

  useEffect(() => {
    if (alerts.length === 0) return;
    const timers = alerts.map(alert => setTimeout(() => {
      setAlerts(prev => prev.filter(a => a.id !== alert.id));
    }, 4000));
    return () => timers.forEach(clearTimeout);
  }, [alerts]);

  const colorMap = {
    success: 'border-emerald-500/40 bg-emerald-900/20 text-emerald-200',
    danger: 'border-red-500/40 bg-red-900/20 text-red-200',
    warning: 'border-yellow-500/40 bg-yellow-900/20 text-yellow-200',
    info: 'border-cyan-500/40 bg-cyan-900/20 text-cyan-200',
  };

  return (
    <div className="fixed top-4 right-4 z-50 w-80 space-y-2">
      <AnimatePresence>
        {alerts.map(alert => (
          <motion.div
            key={alert.id}
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            className={`rounded-lg border px-3 py-2 shadow-lg backdrop-blur-sm ${colorMap[alert.type] || colorMap.info}`}
          >
            <div className="text-xs font-bold tracking-wide">{alert.title}</div>
            <div className="text-[11px] opacity-90">{alert.body}</div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
