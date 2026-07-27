import { useEffect, useRef, useState, useCallback } from 'react';

const MAX_ROWS = 12;

export default function OrderBookWidget({ symbol = 'BTCUSDT' }) {
  const [bids, setBids] = useState([]);
  const [asks, setAsks] = useState([]);
  const [spread, setSpread] = useState(null);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const fmt = useCallback((v) => {
    if (v == null || Number.isNaN(v)) return '0.00';
    return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }, []);

  const fmtQty = useCallback((v) => {
    if (v == null || Number.isNaN(v)) return '0.0000';
    return v.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  }, []);

  useEffect(() => {
    const API_BASE = window._LAFM_API_BASE || 'http://127.0.0.1:8765';
    let cancelled = false;

    const load = async () => {
      try {
        const [obRes, tickerRes] = await Promise.all([
          fetch(`${API_BASE}/api/market/orderbook?limit=50`, { signal: new AbortController(5000).signal }),
          fetch(`${API_BASE}/api/market/ticker`, { signal: new AbortController(5000).signal }),
        ]);
        if (!obRes.ok || !tickerRes.ok) throw new Error('Market data unavailable');
        const ob = await obRes.json();
        const ticker = await tickerRes.json();

        const bidLevels = (ob.bids || []).slice(0, MAX_ROWS).map(([price, qty]) => ({
          price: parseFloat(price),
          qty: parseFloat(qty),
          total: parseFloat(qty),
        }));
        const askLevels = (ob.asks || []).slice(0, MAX_ROWS).map(([price, qty]) => ({
          price: parseFloat(price),
          qty: parseFloat(qty),
          total: parseFloat(qty),
        }));

        if (!cancelled) {
          setBids(bidLevels);
          setAsks(askLevels);
          const bestBid = bidLevels[0]?.price || ticker.price || 0;
          const bestAsk = askLevels[0]?.price || ticker.price || 0;
          setSpread(bestAsk - bestBid);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError('Order book unavailable');
      }
    };

    load();
    intervalRef.current = setInterval(load, 1000);

    return () => {
      cancelled = true;
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [symbol]);

  const renderRows = (book, type) => {
    const sorted = type === 'bid'
      ? [...book].sort((a, b) => b.price - a.price).slice(0, MAX_ROWS)
      : [...book].sort((a, b) => a.price - b.price).slice(0, MAX_ROWS);

    const maxTotal = sorted.reduce((m, r) => Math.max(m, r.total || 0), 0);

    return sorted.map((row, idx) => {
      const pct = maxTotal > 0 ? ((row.total || 0) / maxTotal) * 100 : 0;
      const sideColor = type === 'bid' ? 'bg-emerald-500/10' : 'bg-red-500/10';
      const textColor = type === 'bid' ? 'text-emerald-300' : 'text-red-300';

      return (
        <div key={idx} className={`relative flex items-center justify-between text-[11px] font-mono px-2 py-1 ${textColor}`}>
          <div
            className={`absolute inset-y-0 left-0 ${sideColor}`}
            style={{ width: `${pct}%` }}
          />
          <span className="relative z-10">{fmt(row.price)}</span>
          <span className="relative z-10">{fmtQty(row.qty)}</span>
          <span className="relative z-10">{fmt(row.total)}</span>
        </div>
      );
    });
  };

  if (error) return null;

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg h-full flex flex-col overflow-hidden">
      <div className="px-3 py-2 border-b border-slate-700 flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-200">Order Book</span>
        <span className="text-[10px] text-slate-400">
          {spread != null ? `Spread: ${fmt(spread)} USDT` : 'Live'}
        </span>
      </div>
      <div className="grid grid-cols-2 divide-x divide-slate-700 flex-1 min-h-0">
        <div className="flex flex-col">
          <div className="grid grid-cols-3 text-[10px] text-slate-500 px-2 py-1 border-b border-slate-800">
            <span>Price</span>
            <span className="text-right">Size</span>
            <span className="text-right">Total</span>
          </div>
          <div className="flex-1 overflow-hidden">{renderRows(bids, 'bid')}</div>
        </div>
        <div className="flex flex-col">
          <div className="grid grid-cols-3 text-[10px] text-slate-500 px-2 py-1 border-b border-slate-800">
            <span>Price</span>
            <span className="text-right">Size</span>
            <span className="text-right">Total</span>
          </div>
          <div className="flex-1 overflow-hidden">{renderRows(asks, 'ask')}</div>
        </div>
      </div>
    </div>
  );
}
