export interface OrderPlacedEvent {
  type: 'ORDER_PLACED';
  orderId: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  timestamp: number;
}

export interface MarketDataReceivedEvent {
  type: 'MARKET_DATA_RECEIVED';
  symbol: string;
  candleCount: number;
  timestamp: number;
}

export interface LicenseValidatedEvent {
  type: 'LICENSE_VALIDATED';
  valid: boolean;
  licenseKey: string;
  timestamp: number;
}

export type DomainEvent = OrderPlacedEvent | MarketDataReceivedEvent | LicenseValidatedEvent;

export class EventEmitter {
  private listeners: Map<string, Set<(event: unknown) => void>> = new Map();

  on<K extends DomainEvent['type']>(type: K, listener: (event: Extract<DomainEvent, { type: K }>) => void): () => void {
    const set = this.listeners.get(type) || new Set();
    set.add(listener as (event: unknown) => void);
    this.listeners.set(type, set);
    return () => {
      const s = this.listeners.get(type);
      if (s) {
        s.delete(listener as (event: unknown) => void);
      }
    };
  }

  emit(event: DomainEvent): void {
    const set = this.listeners.get(event.type);
    if (set) {
      set.forEach(listener => listener(event));
    }
  }

  clear(): void {
    this.listeners.clear();
  }
}

export const domainEvents = new EventEmitter();
