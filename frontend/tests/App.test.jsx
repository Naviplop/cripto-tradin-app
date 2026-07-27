import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAppStore } from '../src/store';
import App from '../src/App';

vi.mock('../src/components/CandleChart', () => ({
  default: () => <div data-testid="chart">Chart</div>,
}));
vi.mock('../src/components/TradingPanel', () => ({
  default: ({ onOrderSubmit }) => (
    <div data-testid="trading-panel">
      <button onClick={() => onOrderSubmit({ side: 'BUY' })}>Buy</button>
    </div>
  ),
}));
vi.mock('../src/components/Onboarding', () => ({
  default: ({ onComplete }) => (
    <div data-testid="onboarding">
      <button onClick={onComplete}>Finish</button>
    </div>
  ),
}));
vi.mock('../src/components/SplashScreen', () => ({
  default: ({ onComplete }) => (
    <div data-testid="splash">
      <button onClick={onComplete}>Enter</button>
    </div>
  ),
}));

const resetStore = () => {
  localStorage.clear();
  useAppStore.setState({
    licenseKey: '',
    licenseValid: false,
    isLicensed: false,
    showOnboarding: false,
    connected: false,
    error: '',
  });
};

describe('App', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('shows splash screen first', () => {
    render(<App />);
    expect(screen.getByTestId('splash')).toBeTruthy();
  });

  it('shows license gate after splash when not licensed', async () => {
    global.fetch = vi.fn(() => Promise.reject(new Error('Backend unreachable')));
    render(<App />);
    const splashButton = screen.getByText('Enter');
    await act(async () => {
      splashButton.click();
    });
    expect(await screen.findByText('Enter your license key to activate the application.')).toBeTruthy();
  });

  it('shows onboarding after license validation without completion flag', async () => {
    const calls = [];
    global.fetch = vi.fn(async (url, options) => {
      calls.push({ url, options });
      if (url.includes('/api/health')) {
        return { ok: true, json: () => Promise.resolve({ license_valid: false }) };
      }
      if (url.includes('/api/license/validate')) {
        return { ok: true, json: () => Promise.resolve({ valid: true }) };
      }
      return { ok: true, json: () => Promise.resolve({}) };
    });
    render(<App />);
    const splashButton = screen.getByText('Enter');
    await act(async () => {
      splashButton.click();
    });
    const licenseInput = await screen.findByPlaceholderText('XXXX-XXXX-XXXX-XXXX');
    licenseInput.value = 'TEST-KEY';
    licenseInput.dispatchEvent(new Event('input', { bubbles: true }));
    const activateButton = screen.getByText('Activate License');
    await act(async () => {
      activateButton.click();
    });
    expect(await screen.findByTestId('onboarding')).toBeTruthy();
  });

  it('skips onboarding if already completed', async () => {
    localStorage.setItem('lafm_onboarding_complete', 'true');
    useAppStore.setState({ isLicensed: true, licenseKey: 'TEST-KEY' });
    global.fetch = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ license_valid: true, valid: true }) }));
    render(<App />);
    const splashButton = screen.getByText('Enter');
    await act(async () => {
      splashButton.click();
    });
    expect(await screen.findByTestId('chart')).toBeTruthy();
    expect(screen.getByTestId('trading-panel')).toBeTruthy();
  });
});
