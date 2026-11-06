export class Money {
  constructor(
    public readonly amount: number,
    public readonly currency: string = 'USDT'
  ) {
    if (!Number.isFinite(amount)) {
      throw new Error('Money amount must be finite');
    }
  }

  format(decimals = 2): string {
    return `${this.amount.toFixed(decimals)} ${this.currency}`;
  }

  plus(other: Money): Money {
    if (this.currency !== other.currency) {
      throw new Error('Currency mismatch');
    }
    return new Money(this.amount + other.amount, this.currency);
  }

  minus(other: Money): Money {
    if (this.currency !== other.currency) {
      throw new Error('Currency mismatch');
    }
    return new Money(this.amount - other.amount, this.currency);
  }

  times(multiplier: number): Money {
    return new Money(this.amount * multiplier, this.currency);
  }

  get isPositive(): boolean {
    return this.amount > 0;
  }

  get isNegative(): boolean {
    return this.amount < 0;
  }
}
