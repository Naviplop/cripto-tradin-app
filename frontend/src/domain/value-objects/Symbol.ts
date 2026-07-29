import { SUPPORTED_PAIRS } from '../../lib/constants';

export type Symbol = typeof SUPPORTED_PAIRS[number];

export function isValidSymbol(value: unknown): value is Symbol {
  return SUPPORTED_PAIRS.includes(value as Symbol);
}

export function normalizeSymbol(value: string): Symbol {
  const upper = value.toUpperCase();
  if (!isValidSymbol(upper)) {
    throw new Error(`Unsupported symbol: ${upper}`);
  }
  return upper;
}
