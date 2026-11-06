import type { Order, Position, Trade, Portfolio } from '../entities';
import type { ITradingApi } from '../interfaces';

export interface PlaceOrderResult {
  success: boolean;
  order?: Order;
  error?: string;
}

export class PlaceOrderUseCase {
  constructor(private readonly tradingApi: ITradingApi) {}

  async execute(params: {
    symbol: string;
    side: 'BUY' | 'SELL';
    order_type: 'MARKET' | 'LIMIT' | 'STOP_LIMIT' | 'OCO';
    quantity: number;
    price?: number;
    stop_price?: number;
    limit_price?: number;
    tp?: number;
    sl?: number;
  }): Promise<PlaceOrderResult> {
    const result = await this.tradingApi.placeOrder({
      ...params,
    });

    if (result.success) {
      return { success: true, order: result.order };
    }

    return { success: false, error: result.detail || 'Order placement failed' };
  }
}

export interface FetchPositionsResult {
  positions: Position[];
  portfolio?: Portfolio;
}

export class FetchPositionsUseCase {
  constructor(private readonly tradingApi: ITradingApi) {}

  async execute(): Promise<FetchPositionsResult> {
    const positions = await this.tradingApi.fetchPositions();
    const history = await this.tradingApi.fetchHistory();

    const unrealizedPnl = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0);
    const totalEquity = 0;

    return {
      positions,
      portfolio: {
        total_equity: totalEquity + unrealizedPnl,
        unrealized_pnl: unrealizedPnl,
        available_balance: totalEquity,
        positions_count: positions.length,
      },
    };
  }
}
