import { useState } from 'react';

export default function TradingPanel({ account, onOrderSubmit }) {
  const [side, setSide] = useState('BUY');
  const [orderType, setOrderType] = useState('MARKET');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [tp, setTp] = useState('');
  const [sl, setSl] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!quantity || parseFloat(quantity) <= 0) return;
    onOrderSubmit({
      side,
      order_type: orderType,
      quantity: parseFloat(quantity),
      price: orderType === 'LIMIT' ? parseFloat(price) : undefined,
      tp: tp ? parseFloat(tp) : undefined,
      sl: sl ? parseFloat(sl) : undefined,
    });
    setQuantity('');
    setPrice('');
    setTp('');
    setSl('');
  };

  if (!account) return null;

  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 h-full">
      <h2 className="text-lg font-semibold text-slate-200 mb-4">Paper Trading</h2>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-slate-900/50 rounded p-2">
          <div className="text-xs text-slate-400">Balance</div>
          <div className="text-sm font-medium text-slate-200">${account.balance.toFixed(2)}</div>
        </div>
        <div className="bg-slate-900/50 rounded p-2">
          <div className="text-xs text-slate-400">Equity</div>
          <div className="text-sm font-medium text-slate-200">${account.total_equity.toFixed(2)}</div>
        </div>
        <div className="bg-slate-900/50 rounded p-2">
          <div className="text-xs text-slate-400">Unrealized PnL</div>
          <div className={`text-sm font-medium ${account.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {account.unrealized_pnl >= 0 ? '+' : ''}{account.unrealized_pnl.toFixed(2)}
          </div>
        </div>
        <div className="bg-slate-900/50 rounded p-2">
          <div className="text-xs text-slate-400">Open Positions</div>
          <div className="text-sm font-medium text-slate-200">{account.positions_count}</div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex rounded-lg overflow-hidden border border-slate-600">
          <button
            type="button"
            onClick={() => setSide('BUY')}
            className={`flex-1 py-2 text-sm font-medium transition-colors ${side === 'BUY' ? 'bg-green-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
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
            <option value="MARKET">Market</option>
            <option value="LIMIT">Limit</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Quantity (BTC)</label>
          <input
            type="number"
            step="0.0001"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            placeholder="0.0000"
          />
        </div>

        {orderType === 'LIMIT' && (
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

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Take Profit (USDT)</label>
            <input
              type="number"
              step="0.01"
              value={tp}
              onChange={(e) => setTp(e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
              placeholder="Optional"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Stop Loss (USDT)</label>
            <input
              type="number"
              step="0.01"
              value={sl}
              onChange={(e) => setSl(e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
              placeholder="Optional"
            />
          </div>
        </div>

        <button
          type="submit"
          className={`w-full py-2.5 rounded font-medium text-sm transition-colors ${side === 'BUY' ? 'bg-green-600 hover:bg-green-500 text-white' : 'bg-red-600 hover:bg-red-500 text-white'}`}
        >
          Place {side} Order
        </button>
      </form>
    </div>
  );
}
