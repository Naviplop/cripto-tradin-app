export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8765';
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8765/ws/market';
export const REQUEST_TIMEOUT_MS = 10_000;
export const WS_RECONNECT_BASE_DELAY_MS = 1_000;
export const WS_RECONNECT_MAX_DELAY_MS = 30_000;
export const WS_RECONNECT_JITTER_MS = 1_000;

export const SUPPORTED_PAIRS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'] as const;
export type SupportedPair = typeof SUPPORTED_PAIRS[number];

export const SUPPORTED_TIMEFRAMES = ['1m', '5m', '15m', '1H', '4H', '1D', '1W'] as const;
export type SupportedTimeframe = typeof SUPPORTED_TIMEFRAMES[number];

export const ORDER_SIDES = ['BUY', 'SELL'] as const;
export type OrderSide = typeof ORDER_SIDES[number];

export const ORDER_TYPES = ['MARKET', 'LIMIT', 'STOP_LIMIT', 'OCO'] as const;
export type OrderType = typeof ORDER_TYPES[number];
