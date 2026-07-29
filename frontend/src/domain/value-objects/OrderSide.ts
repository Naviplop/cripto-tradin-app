export const ORDER_SIDE_VALUES = ['BUY', 'SELL'] as const;
export type OrderSide = typeof ORDER_SIDE_VALUES[number];

export function isOrderSide(value: unknown): value is OrderSide {
  return ORDER_SIDE_VALUES.includes(value as OrderSide);
}
