export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export const CANDLE_SCHEMA = {
  time: 'number',
  open: 'number',
  high: 'number',
  low: 'number',
  close: 'number',
} as const;

export function isValidCandle(c: unknown): c is Candle {
  if (typeof c !== 'object' || c === null) return false;
  const obj = c as Record<string, unknown>;
  return (
    typeof obj.time === 'number' &&
    typeof obj.open === 'number' &&
    typeof obj.high === 'number' &&
    typeof obj.low === 'number' &&
    typeof obj.close === 'number'
  );
}
