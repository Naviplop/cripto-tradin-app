import type { Order, Position, Trade, Portfolio, License } from '../domain';
import type { Candle } from '../domain/entities/Candle';
import type { Signal } from '../domain/value-objects/Signal';
import type { OrderSide, OrderType } from '../domain/value-objects/OrderSide';

export interface ITradingApi {
  placeOrder(params: {
    symbol: string;
    side: OrderSide;
    order_type: OrderType;
    quantity: number;
    price?: number;
    stop_price?: number;
    limit_price?: number;
    tp?: number;
    sl?: number;
  }): Promise<{ success: boolean; order?: Order; detail?: string }>;
  fetchPositions(): Promise<Position[]>;
  fetchHistory(): Promise<Trade[]>;
  cancelOrders(): Promise<{ success: boolean }>;
}

export interface ILicenseApi {
  validateLicense(key: string): Promise<License>;
  fetchHealth(): Promise<{ hwid?: string; license_valid?: boolean }>;
}

export interface IMarketApi {
  fetchCandles(symbol: string, interval: string, limit: number): Promise<Candle[]>;
  fetchTicker(): Promise<{ price: number; priceChangePercent: number; high: number; low: number; volume: number }>;
  fetchOrderBook(limit: number): Promise<{ bids: [string, string][]; asks: [string, string][] }>;
}

export interface IStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export interface IWebSocketClient {
  connect(): void;
  disconnect(): void;
  send(data: unknown): void;
  addListener(listener: (event: unknown) => void): () => void;
  getState(): string;
}
