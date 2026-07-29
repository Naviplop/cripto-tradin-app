import { SUPPORTED_TIMEFRAMES } from '../../lib/constants';

export type Timeframe = typeof SUPPORTED_TIMEFRAMES[number];

export function isValidTimeframe(value: unknown): value is Timeframe {
  return SUPPORTED_TIMEFRAMES.includes(value as Timeframe);
}

export const TIMEFRAME_SECONDS: Record<Timeframe, number> = {
  '1m': 60,
  '5m': 300,
  '15m': 900,
  '1H': 3600,
  '4H': 14400,
  '1D': 86400,
  '1W': 604800,
};
