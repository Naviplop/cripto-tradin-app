export interface Order {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  order_type: 'MARKET' | 'LIMIT' | 'STOP_LIMIT' | 'OCO';
  quantity: number;
  price?: number;
  stop_price?: number;
  limit_price?: number;
  tp?: number;
  sl?: number;
  status: 'PENDING' | 'FILLED' | 'CANCELLED' | 'REJECTED';
  created_at: number;
  filled_at?: number;
}

export function isValidOrder(o: unknown): o is Order {
  if (typeof o !== 'object' || o === null) return false;
  const obj = o as Record<string, unknown>;
  return (
    typeof obj.id === 'string' &&
    typeof obj.symbol === 'string' &&
    (obj.side === 'BUY' || obj.side === 'SELL') &&
    ['MARKET', 'LIMIT', 'STOP_LIMIT', 'OCO'].includes(obj.order_type as string) &&
    typeof obj.quantity === 'number' &&
    ['PENDING', 'FILLED', 'CANCELLED', 'REJECTED'].includes(obj.status as string) &&
    typeof obj.created_at === 'number'
  );
}

export type MarketOrder = Omit<Order, 'price' | 'stop_price' | 'limit_price'>;
export type LimitOrder = Order & { price: number };
export type StopLimitOrder = Order & { stop_price: number; limit_price: number };
export type OcoOrder = Order & { stop_price: number; limit_price: number };

export type OrderVariant = MarketOrder | LimitOrder | StopLimitOrder | OcoOrder;

export function orderTypeOf(order: Order): OrderVariant['order_type'] {
  return order.order_type;
}
