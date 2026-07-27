import { useState, useEffect, useRef, useCallback } from 'react';
import Chart from './components/CandleChart';
import TradingPanel from './components/TradingPanel';
import Onboarding from './components/Onboarding';
import SplashScreen from './components/SplashScreen';
import HeaderBar from './components/HeaderBar';
import AlertsToast from './components/AlertsToast';
import OrderBookWidget from './components/OrderBookWidget';
import { useAppStore } from './store';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8765';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8765/ws/market';
const REQUEST_TIMEOUT = 10000;

const getReconnectDelay = (attempt) => {
  const base = 1000;
  const maxDelay = 30000;
  const delay = Math.min(base * Math.pow(2, attempt), maxDelay);
  const jitter = Math.random() * 1000;
  return delay + jitter;
};

export default function App() {
  const [splashComplete, setSplashComplete] = useState(false);
  const handleSplashComplete = useCallback(() => setSplashComplete(true), []);
  const [candleData, setCandleData] = useState([]);
  const [signals, setSignals] = useState(null);
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [history, setHistory] = useState([]);
  const [ticker, setTicker] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [bootstrapError, setBootstrapError] = useState('');
  const wsRef = useRef(null);

  const store = useAppStore();
  const {
    licenseKey, setLicenseKey,
    licenseValid, setLicenseValid,
    isLicensed, setIsLicensed,
    showOnboarding, setShowOnboarding,
    connected, setConnected,
    error, setError,
  } = store;

  const fetchWithTimeout = useCallback(async (url, options = {}, timeout = REQUEST_TIMEOUT) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    try {
      const res = await fetch(url, { ...options, signal: controller.signal });
      clearTimeout(timeoutId);
      if (!res.ok) {
        const text = await res.text();
        let detail = text;
        try { detail = JSON.parse(text).detail || text; } catch { /* ignore */ }
        throw new Error(detail || `HTTP ${res.status}`);
      }
      return await res.json();
    } finally {
      clearTimeout(timeoutId);
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current) wsRef.current.close();
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setReconnectAttempt(0);
      setError('');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'market_data') {
          setCandleData(prev => {
            const map = new Map();
            for (const c of prev) map.set(typeof c.time === 'string' ? c.time : JSON.stringify(c.time), c);
            const key = typeof msg.candle.time === 'string' ? msg.candle.time : JSON.stringify(msg.candle.time);
            map.set(key, msg.candle);
            const next = Array.from(map.values());
            return next.slice(-500);
          });
          setSignals(msg.signals);
        } else if (msg.type === 'account_update') {
          setAccount(msg.data);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message', e);
      }
    };

    ws.onerror = () => {
      setError('WebSocket connection error');
    };

    ws.onclose = () => {
      setConnected(false);
      const delay = getReconnectDelay(reconnectAttempt);
      setReconnectAttempt(prev => prev + 1);
      setTimeout(connectWebSocket, delay);
    };
  }, [reconnectAttempt]);

  useEffect(() => {
    if (!splashComplete) return;
    let cancelled = false;
    setIsBootstrapping(true);
    setBootstrapError('');
    fetchWithTimeout(`${API_BASE}/api/health`, {}, 8000)
      .then(data => {
        if (cancelled) return;
        if (data?.license_valid) {
          setIsLicensed(true);
          setLicenseValid(true);
          store.setIsLicensed?.(true);
          store.setLicenseValid?.(true);
        } else {
          setIsLicensed(false);
          setLicenseValid(false);
          store.setIsLicensed?.(false);
          store.setLicenseValid?.(false);
        }
      })
      .catch(err => {
        if (cancelled) return;
        console.warn('Health check failed:', err);
        setIsLicensed(false);
        setLicenseValid(false);
        store.setIsLicensed?.(false);
        store.setLicenseValid?.(false);
        setBootstrapError('Backend unreachable. Running in offline mode.');
      })
      .finally(() => {
        if (!cancelled) setIsBootstrapping(false);
      });
    return () => { cancelled = true; };
  }, [splashComplete]);

  useEffect(() => {
    if (isLicensed && !showOnboarding) {
      const onboardingDone = typeof window !== 'undefined' ? localStorage.getItem('lafm_onboarding_complete') : null;
      if (onboardingDone) {
        connectWebSocket();
        fetchAccount();
        fetchPositions();
        fetchHistory();
        fetchTicker();
        fetchCandles();
      }
    }
  }, [isLicensed, showOnboarding]);

  const fetchAccount = async () => {
    try {
      const data = await fetchWithTimeout(`${API_BASE}/api/account/balance`);
      setAccount(data);
    } catch (e) {
      // silent
    }
  };

  const fetchPositions = async () => {
    try {
      const data = await fetchWithTimeout(`${API_BASE}/api/account/positions`);
      setPositions(data);
    } catch (e) {
      // silent
    }
  };

  const fetchHistory = async () => {
    try {
      const data = await fetchWithTimeout(`${API_BASE}/api/account/history`);
      setHistory(data);
    } catch (e) {
      // silent
    }
  };

  const fetchTicker = async () => {
    try {
      const data = await fetchWithTimeout(`${API_BASE}/api/market/ticker`);
      setTicker(data);
    } catch (e) {
      // silent
    }
  };

  const fetchCandles = async () => {
    try {
      const data = await fetchWithTimeout(`${API_BASE}/api/market/klines?limit=200`);
      if (Array.isArray(data)) {
        const seen = new Set();
        const deduped = [];
        for (const c of data) {
          const t = typeof c.time === 'string' ? c.time : JSON.stringify(c.time);
          if (!seen.has(t)) {
            seen.add(t);
            deduped.push(c);
          }
        }
        deduped.sort((a, b) => {
          const ta = typeof a.time === 'string' ? new Date(a.time).getTime() : a.time;
          const tb = typeof b.time === 'string' ? new Date(b.time).getTime() : b.time;
          return ta - tb;
        });
        setCandleData(deduped);
      }
    } catch (e) {
      // silent
    }
  };

  const handleOrderSubmit = async (order) => {
    try {
      const data = await fetchWithTimeout(`${API_BASE}/api/trading/order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(order),
      });
      if (data.success) {
        fetchPositions();
        fetchAccount();
        setError('');
      } else {
        setError(data.detail || 'Order failed');
      }
    } catch (e) {
      let message = 'Failed to place order';
      if (e.name === 'AbortError') message = 'Order request timed out.';
      setError(message);
    }
  };

  const handleTimeframeChange = (tf) => {
    // In a real implementation, send a WS message to change subscription
    console.log('Timeframe change requested:', tf);
  };

  const handlePauseToggle = (paused) => {
    console.log('Pause toggled:', paused);
  };

  const handleCancelOrders = () => {
    console.log('Cancel orders requested');
  };

  const validateLicense = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchWithTimeout(`${API_BASE}/api/license/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ license_key: licenseKey }),
      });
      if (data.valid) {
        setLicenseValid(true);
        setIsLicensed(true);
        store.setLicenseValid?.(true);
        store.setIsLicensed?.(true);
        if (typeof window !== 'undefined') {
          localStorage.setItem('lafm_license_key', licenseKey);
        }
        if (!localStorage.getItem('lafm_onboarding_complete')) {
          setShowOnboarding(true);
        } else {
          connectWebSocket();
          fetchAccount();
          fetchPositions();
          fetchHistory();
          fetchTicker();
        }
      } else {
        setError(data.message || 'Invalid license');
      }
    } catch (e) {
      let message = 'Cannot connect to backend. Ensure it is running.';
      if (e.name === 'AbortError') message = 'License validation timed out. Backend may be unreachable.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleOnboardingComplete = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('lafm_onboarding_complete', 'true');
    }
    setShowOnboarding(false);
    connectWebSocket();
    fetchAccount();
    fetchPositions();
    fetchHistory();
    fetchTicker();
  };

  if (!splashComplete) {
    return <SplashScreen onComplete={handleSplashComplete} />;
  }

  if (isBootstrapping) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-900 rounded-xl p-8 border border-slate-700 shadow-2xl text-center">
          <div className="text-2xl font-bold text-slate-100 mb-2">LAFM Core Engine</div>
          <div className="text-slate-400 text-sm mb-4">Iniciando motor de trading...</div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div className="bg-cyan-400 h-2 rounded-full animate-pulse" style={{ width: '70%' }} />
          </div>
          {bootstrapError && <div className="mt-3 text-xs text-red-300">{bootstrapError}</div>}
        </div>
      </div>
    );
  }

  if (!isLicensed) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-900 rounded-xl p-8 border border-slate-700 shadow-2xl">
          <h1 className="text-2xl font-bold text-slate-100 mb-2">Crypto Trading Terminal</h1>
          <p className="text-slate-400 text-sm mb-6">Enter your license key to activate the application.</p>
          {error && <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded text-red-300 text-sm">{error}</div>}
          <input
            type="text"
            value={licenseKey}
            onChange={(e) => setLicenseKey(e.target.value)}
            placeholder="XXXX-XXXX-XXXX-XXXX"
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 text-slate-200 mb-4 focus:outline-none focus:border-blue-500 font-mono"
            onKeyDown={(e) => e.key === 'Enter' && validateLicense()}
          />
          <button
            onClick={validateLicense}
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white font-medium py-3 rounded-lg transition-colors"
          >
            {loading ? 'Validating...' : 'Activate License'}
          </button>
          <p className="text-xs text-slate-500 mt-4 text-center">Requires backend server running on port 8765</p>
        </div>
      </div>
    );
  }

  if (showOnboarding) {
    return <Onboarding onComplete={handleOnboardingComplete} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <HeaderBar account={account} connected={connected} ticker={ticker} />
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-900/30 border border-red-700 rounded text-red-300 text-sm">
          {error}
        </div>
      )}
      <AlertsToast signals={signals} account={account} />
      <div className="flex h-[calc(100vh-60px)] relative">
        <div className={`fixed inset-0 bg-black/50 z-20 md:hidden ${sidebarOpen ? 'block' : 'hidden'}`} onClick={() => setSidebarOpen(false)} />
        <aside className={`fixed md:static inset-y-0 left-0 z-30 w-80 bg-slate-900 border-r border-slate-700 transform transition-transform duration-300 ease-in-out ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0 flex flex-col`}>
          <div className="p-4 border-b border-slate-700 flex items-center justify-between md:hidden">
            <span className="text-slate-200 font-semibold">Menu</span>
            <button onClick={() => setSidebarOpen(false)} className="text-slate-400 hover:text-white">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <TradingPanel account={account} onOrderSubmit={handleOrderSubmit} signals={signals} />
            <OrderBookWidget />
          </div>
        </aside>
        <main className="flex-1 p-4 overflow-hidden">
          <div className="h-full relative">
            <Chart
              data={candleData}
              signals={signals}
              onTimeframeChange={handleTimeframeChange}
              onPauseToggle={handlePauseToggle}
              onOrderSubmit={handleOrderSubmit}
              onCancelOrders={handleCancelOrders}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
