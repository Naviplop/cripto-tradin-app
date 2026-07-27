import { create } from 'zustand';

export const useAppStore = create((set, get) => ({
  licenseKey: typeof window !== 'undefined' ? localStorage.getItem('lafm_license_key') || '' : '',
  licenseValid: typeof window !== 'undefined' ? localStorage.getItem('lafm_license_valid') === 'true' : false,
  isLicensed: typeof window !== 'undefined' ? localStorage.getItem('lafm_licensed') === 'true' : false,
  showOnboarding: typeof window !== 'undefined' ? localStorage.getItem('lafm_onboarding_complete') !== 'true' : false,
  connected: false,
  error: '',
  setLicenseKey: (value) => set({ licenseKey: value }),
  setLicenseValid: (value) => {
    set({ licenseValid: value });
    if (typeof window !== 'undefined') {
      localStorage.setItem('lafm_license_valid', value ? 'true' : 'false');
    }
  },
  setIsLicensed: (value) => {
    set({ isLicensed: value });
    if (typeof window !== 'undefined') {
      localStorage.setItem('lafm_licensed', value ? 'true' : 'false');
    }
  },
  setShowOnboarding: (value) => {
    set({ showOnboarding: value });
    if (typeof window !== 'undefined' && value === false) {
      localStorage.setItem('lafm_onboarding_complete', 'true');
    }
  },
  setConnected: (value) => set({ connected: value }),
  setError: (value) => set({ error: value }),
}));
