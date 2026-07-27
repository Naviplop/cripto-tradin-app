import { useState, useMemo } from 'react';

const ORDER_TYPES = ['MARKET', 'LIMIT', 'STOP_LIMIT', 'OCO'];

export default function TradingPanel({ account, onOrderSubmit, signals }) {
  const [side, setSide] = useState('BUY');
  const [orderType, setOrderType] = useState('MARKET');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [stopPrice, setStopPrice] = useState('');
  const [limitPrice, setLimitPrice] = useState('');
  const [tp, setTp] = useState('');
  const [sl, setSl] = useState('');

  const currentPrice = signals?.current_price ?? account?.current_price ?? 0;
  const atr = signals?.atr ?? 0;

  const balance = account?.balance ?? 0;
  const equity = account?.total_equity ?? balance;

  const pctPresets = useMemo(() => {
    const base = orderType === 'OCO' ? equity : balance;
    return [
      { label: '25%', value: (base * 0.25) / (currentPrice || 1) },
      { label: '50%', value: (base * 0.5) / (currentPrice || 1) },
      { label: '75%', value: (base * 0.75) / (currentPrice || 1) },
      { label: '100%', value: base / (currentPrice || 1) },
    ];
  }, [balance, equity, currentPrice, orderType]);

  const suggestedTP = useMemo(() => {
    if (!currentPrice || !atr) return '';
    const mult = 1.5;
    return side === 'BUY'
      ? (currentPrice + mult * atr).toFixed(2)
      : (currentPrice - mult * atr).toFixed(2);
  }, [currentPrice, atr, side]);

  const suggestedSL = useMemo(() => {
    if (!currentPrice || !atr) return '';
    const mult = 1.0;
    return side === 'BUY'
      ? (currentPrice - mult * atr).toFixed(2)
      : (currentPrice + mult * atr).toFixed(2);
  }, [currentPrice, atr, side]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const qty = parseFloat(quantity);
    if (!qty || qty <= 0) return;

    const payload = {
      side,
      order_type: orderType,
      quantity: qty,
      price: orderType === 'LIMIT' || orderType === 'OCO' ? parseFloat(price) : undefined,
      stop_price: orderType === 'STOP_LIMIT' || orderType === 'OCO' ? parseFloat(stopPrice) : undefined,
      limit_price: orderType === 'STOP_LIMIT' ? parseFloat(limitPrice) : (orderType === 'OCO' ? parseFloat(limitPrice) : undefined),
      tp: tp ? parseFloat(tp) : undefined,
      sl: sl ? parseFloat(sl) : undefined,
    };

    onOrderSubmit?.(payload);
    setQuantity('');
    setPrice('');
    setStopPrice('');
    setLimitPrice('');
    setTp('');
    setSl('');
  };

  if (!account) return null;

  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 h-full overflow-y-auto">
      <h2 className="text-lg font-semibold text-slate-200 mb-4">Trading</h2>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-slate-900/50 rounded p-2">
          <div className="text-xs text-slate-400">Balance</div>
          <div className="text-sm font-medium text-slate-200">${balance.toFixed(2)}</div>
        </div>
        <div className="bg-slate-900/50 rounded p-2">
          <div className="text-xs text-slate-400">Equity</div>
          <div className="text-sm font-medium text-slate-200">${equity.toFixed(2)}</div>
        </div>
        <div className="bg-slate-900/50 rounded p-2">
          <div className="text-xs text-slate-400">Unrealized PnL</div>
          <div className={`text-sm font-medium ${account.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {account.unrealized_pnl >= 0 ? '+' : ''}{account.unrealized_pnl.toFixed(2)}
          </div>
        </div>
        <div className="bg-slate-900/50 rounded p-2">
          <div className="text-xs text-slate-400">Positions</div>
          <div className="text-sm font-medium text-slate-200">{account.positions_count}</div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex rounded-lg overflow-hidden border border-slate-600">
          <button
            type="button"
            onClick={() => setSide('BUY')}
            className={`flex-1 py-2 text-sm font-medium transition-colors ${side === 'BUY' ? 'bg-emerald-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
          >
            Buy
          </button>
          <button
            type="button"
            onClick={() => setSide('SELL')}
            className={`flex-1 py-2 text-sm font-medium transition-colors ${side === 'SELL' ? 'bg-red-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
          >
            Sell
          </button>
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Order Type</label>
          <select
            value={orderType}
            onChange={(e) => setOrderType(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
          >
            {ORDER_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Quantity (% of balance)</label>
          <div className="flex gap-2 mb-2">
            {pctPresets.map(p => (
              <button
                key={p.label}
                type="button"
                onClick={() => setQuantity(p.value.toFixed(6))}
                className="flex-1 text-[10px] font-mono bg-slate-900 border border-slate-700 text-slate-300 rounded py-1 hover:border-cyan-500 transition-colors"
              >
                {p.label}
              </button>
            ))}
          </div>
          <input
            type="number"
            step="0.000001"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            placeholder="0.000000"
          />
        </div>

        {(orderType === 'LIMIT' || orderType === 'OCO') && (
          <div>
            <label className="block text-xs text-slate-400 mb-1">Limit Price (USDT)</label>
            <input
              type="number"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
              placeholder="0.00"
            />
          </div>
        )}

        {(orderType === 'STOP_LIMIT' || orderType === 'OCO') && (
          <div>
            <label className="block text-xs text-slate-400 mb-1">Stop Price (USDT)</label>
            <input
              type="number"
              step="0.01"
              value={stopPrice}
              onChange={(e) => setStopPrice(e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
              placeholder="0.00"
            />
          </div>
        )}

        {orderType === 'STOP_LIMIT' && (
          <div>
            <label className="block text-xs text-slate-400 mb-1">Limit Price (USDT)</label>
            <input
              type="number"
              step="0.01"
              value={limitPrice}
              onChange={(e) => setLimitPrice(e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
              placeholder="0.00"
            />
          </div>
        )}

        {(orderType === 'LIMIT' || orderType === 'OCO' || orderType === 'STOP_LIMIT') && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Take Profit</label>
              <input
                type="number"
                step="0.01"
                value={tp}
                onChange={(e) => setTp(e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                placeholder={suggestedTP || 'Optional'}
              />
              {suggestedTP && (
                <button
                  type="button"
                  onClick={() => setTp(suggestedTP)}
                  className="mt-1 text-[10px] text-cyan-300 hover:text-cyan-200"
                >
                  Suggested: {suggestedTP}
                </button>
              )}
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Stop Loss</label>
              <input
                type="number"
                step="0.01"
                value={sl}
                onChange={(e) => setSl(e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                placeholder={suggestedSL || 'Optional'}
              />
              {suggestedSL && (
                <button
                  type="button"
                  onClick={() => setSl(suggestedSL)}
                  className="mt-1 text-[10px] text-red-300 hover:text-red-200"
                >
                  Suggested: {suggestedSL}
                </button>
              )}
            </div>
          </div>
        )}

        <button
          type="submit"
          className={`w-full py-2.5 rounded font-medium text-sm transition-colors ${
            side === 'BUY'
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
              : 'bg-red-600 hover:bg-red-500 text-white'
          }`}
        >
          {side === 'BUY' ? 'Buy' : 'Sell'} {orderType.replace('_', ' ')}
        </button>
      </form>
    </div>
  );
}
