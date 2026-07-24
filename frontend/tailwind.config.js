/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        lafm: {
          bg: '#050811',
          panel: '#0a0f1d',
          border: '#1e293b',
          accent: '#00f2fe',
          accentGlow: 'rgba(0, 242, 254, 0.15)',
          text: '#e2e8f0',
          muted: '#94a3b8',
        }
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'neon': '0 0 10px rgba(0, 242, 254, 0.3), 0 0 20px rgba(0, 242, 254, 0.1)',
        'neon-strong': '0 0 15px rgba(0, 242, 254, 0.5), 0 0 30px rgba(0, 242, 254, 0.2)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'scan': 'scan 2s linear infinite',
      },
      keyframes: {
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        }
      }
    },
  },
  plugins: [],
}
