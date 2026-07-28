import { useState, useEffect, useCallback } from 'react';

const PAIRS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'];
const TIMEFRAMES = ['1m', '5m', '15m', '1H', '4H', '1D', '1W'];

export default function HeaderBar({ account, connected, ticker, onTimeframeChange, onPairChange }) {
  const [pair, setPair] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('1m');
  const [latency, setLatency] = useState(null);
  const [mode, setMode] = useState('PAPER');

  useEffect(() => {
    if (!connected) return;
    const start = performance.now();
    const ws = new WebSocket('ws://127.0.0.1:8765/ws/market');
    ws.onopen = () => setLatency(Math.round(performance.now() - start));
    ws.onerror = () => setLatency(null);
    ws.onclose = () => {};
    return () => ws.close();
  }, [connected]);

  const changePair = useCallback((next) => setPair(next), []);
  const changeTimeframe = useCallback((next) => setTimeframe(next), []);
  const toggleMode = useCallback(() => setMode(prev => prev === 'PAPER' ? 'LIVE' : 'PAPER'), []);

  const price = ticker?.price ?? 0;
  const change24h = ticker?.priceChangePercent ?? 0;
  const high24h = ticker?.high ?? 0;
  const low24h = ticker?.low ?? 0;
  const volume24h = ticker?.volume ?? 0;

  const equity = account?.total_equity ?? 0;
  const unrealized = account?.unrealized_pnl ?? 0;
  const positionsCount = account?.positions_count ?? 0;

  return (
    <header className="h-[60px] bg-slate-900 border-b border-slate-700 px-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-sm font-bold text-slate-100 tracking-wide">LAFM</span>
        <select
          value={pair}
          onChange={(e) => {
            const next = e.target.value;
            setPair(next);
            onPairChange?.(next);
          }}
          className="bg-slate-800 border border-slate-700 text-slate-200 text-xs font-mono rounded px-2 py-1 focus:outline-none focus:border-cyan-500"
        >
          {PAIRS.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <select
          value={timeframe}
          onChange={(e) => {
            const next = e.target.value;
            setTimeframe(next);
            onTimeframeChange?.(next);
          }}
          className="bg-slate-800 border border-slate-700 text-slate-200 text-xs font-mono rounded px-2 py-1 focus:outline-none focus:border-cyan-500"
        >
          {TIMEFRAMES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <div className="flex items-center gap-4 text-xs">
        <div className="hidden md:flex items-center gap-3">
          <div className="text-slate-400">
            Price <span className="text-slate-200 font-mono">{price ? `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '--'}</span>
          </div>
          <div className={`font-mono ${change24h >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            24h {change24h >= 0 ? '+' : ''}{change24h?.toFixed(2)}%
          </div>
          <div className="text-slate-400">
            H <span className="text-slate-200 font-mono">{high24h ? `$${high24h.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '--'}</span>
          </div>
          <div className="text-slate-400">
            L <span className="text-slate-200 font-mono">{low24h ? `$${low24h.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '--'}</span>
          </div>
          <div className="text-slate-400">
            Vol <span className="text-slate-200 font-mono">{volume24h ? `${(volume24h / 1000).toFixed(1)}K` : '--'}</span>
          </div>
          <div className="text-slate-400">
            Equity <span className="text-slate-200 font-mono">${equity.toFixed(2)}</span>
          </div>
          <div className={`font-mono ${unrealized >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            PnL {unrealized >= 0 ? '+' : ''}{unrealized.toFixed(2)} USDT
          </div>
          <div className="text-slate-400">Pos <span className="text-slate-200 font-mono">{positionsCount}</span></div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
          <span className="text-slate-400 font-mono">{latency !== null ? `${latency} ms` : '--'}</span>
        </div>
        <button
          onClick={toggleMode}
          className={`px-2 py-1 rounded border transition-colors ${mode === 'PAPER' ? 'bg-slate-800 border-slate-700 text-slate-200 hover:border-cyan-500' : 'bg-emerald-900/30 border-emerald-700 text-emerald-300'}`}
        >
          {mode === 'PAPER' ? 'Paper Trading' : 'Binance Live'}
        </button>
      </div>
    </header>
  );
}
