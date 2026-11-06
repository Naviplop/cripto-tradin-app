export const ORDER_TYPE_VALUES = ['MARKET', 'LIMIT', 'STOP_LIMIT', 'OCO'] as const;
export type OrderType = typeof ORDER_TYPE_VALUES[number];

export function isOrderType(value: unknown): value is OrderType {
  return ORDER_TYPE_VALUES.includes(value as OrderType);
}
