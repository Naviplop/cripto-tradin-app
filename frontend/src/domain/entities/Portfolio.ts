export interface Portfolio {
  total_equity: number;
  unrealized_pnl: number;
  available_balance: number;
  positions_count: number;
  current_price?: number;
}

export function isValidPortfolio(p: unknown): p is Portfolio {
  if (typeof p !== 'object' || p === null) return false;
  const obj = p as Record<string, unknown>;
  return (
    typeof obj.total_equity === 'number' &&
    typeof obj.unrealized_pnl === 'number' &&
    typeof obj.available_balance === 'number' &&
    typeof obj.positions_count === 'number'
  );
}
