export interface Trade {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  fee: number;
  timestamp: number;
}

export function isValidTrade(t: unknown): t is Trade {
  if (typeof t !== 'object' || t === null) return false;
  const obj = t as Record<string, unknown>;
  return (
    typeof obj.id === 'string' &&
    typeof obj.symbol === 'string' &&
    (obj.side === 'BUY' || obj.side === 'SELL') &&
    typeof obj.quantity === 'number' &&
    typeof obj.price === 'number' &&
    typeof obj.fee === 'number' &&
    typeof obj.timestamp === 'number'
  );
}
