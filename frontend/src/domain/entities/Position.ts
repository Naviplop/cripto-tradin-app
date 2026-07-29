export interface Position {
  symbol: string;
  side: 'LONG' | 'SHORT';
  quantity: number;
  entry_price: number;
  mark_price: number;
  unrealized_pnl: number;
  percentage: number;
}

export function isValidPosition(p: unknown): p is Position {
  if (typeof p !== 'object' || p === null) return false;
  const obj = p as Record<string, unknown>;
  return (
    typeof obj.symbol === 'string' &&
    (obj.side === 'LONG' || obj.side === 'SHORT') &&
    typeof obj.quantity === 'number' &&
    typeof obj.entry_price === 'number' &&
    typeof obj.mark_price === 'number' &&
    typeof obj.unrealized_pnl === 'number' &&
    typeof obj.percentage === 'number'
  );
}

export type PositionSide = Position['side'];
