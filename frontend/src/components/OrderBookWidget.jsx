import { useEffect, useRef, useState, useCallback } from 'react';

const MAX_ROWS = 12;

export default function OrderBookWidget({ symbol = 'BTCUSDT' }) {
  const [bids, setBids] = useState([]);
  const [asks, setAsks] = useState([]);
  const [spread, setSpread] = useState(null);
  const wsRef = useRef(null);

  const fmt = useCallback((v) => {
    if (v == null || Number.isNaN(v)) return '0.00';
    return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }, []);

  const fmtQty = useCallback((v) => {
    if (v == null || Number.isNaN(v)) return '0.0000';
    return v.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  }, []);

  useEffect(() => {
    const ws = new WebSocket('wss://stream.binance.com:9443/ws');
    wsRef.current = ws;

    const sub = {
      method: 'SUBSCRIBE',
      params: [`${symbol.toLowerCase()}@depth@100ms`, `${symbol.toLowerCase()}@ticker`],
      id: 1,
    };

    ws.onopen = () => ws.send(JSON.stringify(sub));
    ws.onclose = () => {};
    ws.onerror = () => {};

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.e === 'depthUpdate') {
          setBids(prev => mergeDepth(prev, msg.b, 'bid'));
          setAsks(prev => mergeDepth(prev, msg.a, 'ask'));
        } else if (msg.e === '24hrTicker' && msg.bestBidPrice && msg.bestAskPrice) {
          const bestBid = parseFloat(msg.bestBidPrice);
          const bestAsk = parseFloat(msg.bestAskPrice);
          setSpread(bestAsk - bestBid);
        }
      } catch (e) {
        // ignore parse errors
      }
    };

    return () => ws.close();
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

  if (!spread) return null;

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg h-full flex flex-col overflow-hidden">
      <div className="px-3 py-2 border-b border-slate-700 flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-200">Order Book</span>
        <span className="text-[10px] text-slate-400">Spread: {fmt(spread)} USDT</span>
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

function mergeDepth(prev, levels, side) {
  const map = new Map();
  for (const l of prev) map.set(l.price, l);

  for (const l of levels) {
    const price = parseFloat(l[0]);
    const qty = parseFloat(l[1]);
    if (qty === 0) map.delete(price);
    else {
      const existing = map.get(price);
      const total = existing ? existing.total + qty : qty;
      map.set(price, { price, qty, total: Number.parseFloat(total.toFixed(4)) });
    }
  }
  return Array.from(map.values());
}
