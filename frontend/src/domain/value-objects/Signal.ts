export interface Signal {
  signal: 'BUY' | 'SELL' | 'HOLD';
  ai_probability: number;
  atr: number;
  atr_spike: boolean;
  current_price: number;
  ma_fast: number;
  ma_slow: number;
  features: Record<string, number | string>;
}

export const SIGNAL_SCHEMA = {
  signal: 'BUY | SELL | HOLD',
  ai_probability: 'number',
  atr: 'number',
  atr_spike: 'boolean',
  current_price: 'number',
  ma_fast: 'number',
  ma_slow: 'number',
  features: 'Record<string, number | string>',
} as const;

export function isValidSignal(s: unknown): s is Signal {
  if (typeof s !== 'object' || s === null) return false;
  const obj = s as Record<string, unknown>;
  return (
    obj.signal === 'BUY' || obj.signal === 'SELL' || obj.signal === 'HOLD'
  ) &&
    typeof obj.ai_probability === 'number' &&
    typeof obj.atr === 'number' &&
    typeof obj.atr_spike === 'boolean' &&
    typeof obj.current_price === 'number' &&
    typeof obj.ma_fast === 'number' &&
    typeof obj.ma_slow === 'number' &&
    typeof obj.features === 'object' && obj.features !== null;
}

export type SignalPayload = Omit<Signal, 'features'> & { features: Record<string, number | string> };
