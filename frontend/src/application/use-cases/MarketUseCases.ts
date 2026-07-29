import type { Candle } from '../../domain/entities/Candle';
import type { Signal } from '../../domain/value-objects/Signal';
import { SupportedPair, SupportedTimeframe } from '../../lib/constants';
import type { ILicenseApi, IMarketApi } from '../interfaces';

export interface FetchCandlesResult {
  candles: Candle[];
  error?: string;
}

export class FetchCandlesUseCase {
  constructor(private readonly marketApi: IMarketApi) {}

  async execute(symbol: SupportedPair, timeframe: SupportedTimeframe, limit = 200): Promise<FetchCandlesResult> {
    try {
      const candles = await this.marketApi.fetchCandles(symbol, timeframe, limit);
      return { candles };
    } catch (error) {
      return { candles: [], error: (error as Error).message };
    }
  }
}

export interface FetchTickerResult {
  prices: { price: number; change: number; high: number; low: number; volume: number } | null;
  error?: string;
}

export class FetchTickerUseCase {
  constructor(private readonly marketApi: IMarketApi) {}

  async execute(): Promise<FetchTickerResult> {
    try {
      const ticker = await this.marketApi.fetchTicker();
      return {
        prices: {
          price: ticker.price,
          change: ticker.priceChangePercent,
          high: ticker.high,
          low: ticker.low,
          volume: ticker.volume,
        },
      };
    } catch (error) {
      return { prices: null, error: (error as Error).message };
    }
  }
}

export interface FetchSignalsResult {
  signal: Signal | null;
  error?: string;
}

export class FetchSignalsUseCase {
  constructor(private readonly marketApi: IMarketApi) {}

  async execute(): Promise<FetchSignalsResult> {
    return { signal: null };
  }
}

export interface ValidateLicenseResult {
  license: { valid: boolean; hwid?: string } | null;
  error?: string;
}

export class ValidateLicenseUseCase {
  constructor(private readonly licenseApi: ILicenseApi) {}

  async execute(key: string): Promise<ValidateLicenseResult> {
    try {
      const license = await this.licenseApi.validateLicense(key);
      return { license };
    } catch (error) {
      return { license: null, error: (error as Error).message };
    }
  }
}
