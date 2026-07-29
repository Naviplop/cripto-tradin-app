import { WS_RECONNECT_BASE_DELAY_MS, WS_RECONNECT_MAX_DELAY_MS, WS_RECONNECT_JITTER_MS } from '../lib/constants';
import type { Candle, Signal } from '../domain/value-objects';

export interface MarketDataMessage {
  type: 'market_data';
  candle: Candle;
  signals: Signal;
}

export interface AccountUpdateMessage {
  type: 'account_update';
  data: Account;
}

export type WebSocketMessage = MarketDataMessage | AccountUpdateMessage;

export interface Account {
  total_equity: number;
  unrealized_pnl: number;
  positions_count: number;
  balance: number;
  current_price?: number;
}

export type WebSocketState = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING';

export type WebSocketEvent = {
  type: 'open';
} | {
  type: 'message';
  message: WebSocketMessage;
} | {
  type: 'close';
  willReconnect: boolean;
} | {
  type: 'error';
  error: Event;
};

export type WebSocketListener = (event: WebSocketEvent) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private retryCount = 0;
  private listeners: Set<WebSocketListener> = new Set();
  private state: WebSocketState = 'DISCONNECTED';
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private manualClose = false;

  constructor(url: string) {
    this.url = url;
  }

  getState(): WebSocketState {
    return this.state;
  }

  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.manualClose = false;
    this.state = 'CONNECTING';
    this.notify({ type: 'message', message: { type: 'open' } });

    try {
      this.ws = new WebSocket(this.url);
    } catch (error) {
      this.state = 'DISCONNECTED';
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.state = 'CONNECTED';
      this.retryCount = 0;
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        this.notify({ type: 'message', message });
      } catch {
        // ignore malformed messages
      }
    };

    this.ws.onerror = (error) => {
      this.notify({ type: 'error', error });
    };

    this.ws.onclose = () => {
      const willReconnect = !this.manualClose;
      this.state = 'DISCONNECTED';
      this.ws = null;
      this.notify({ type: 'close', willReconnect });
      if (willReconnect) {
        this.scheduleReconnect();
      }
    };
  }

  disconnect(): void {
    this.manualClose = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.state = 'DISCONNECTED';
  }

  send(data: unknown): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  addListener(listener: WebSocketListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private scheduleReconnect(): void {
    if (this.manualClose) return;
    this.state = 'RECONNECTING';

    const base = WS_RECONNECT_BASE_DELAY_MS;
    const max = WS_RECONNECT_MAX_DELAY_MS;
    const jitter = Math.random() * WS_RECONNECT_JITTER_MS;
    const delay = Math.min(base * Math.pow(2, this.retryCount), max) + jitter;

    this.retryCount += 1;
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  private notify(event: WebSocketEvent): void {
    for (const listener of this.listeners) {
      listener(event);
    }
  }
}
