import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        dm: {
          bg: '#0F1117',
          surface: '#16181F',
          border: '#272B36',
          text: '#E6E8EF',
          muted: '#8B92A5',
          accent: '#3B82F6',
          'accent-hover': '#2563EB',
          success: '#22C55E',
          warning: '#F59E0B',
          danger: '#EF4444',
        },
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        surface: {
          0: '#ffffff',
          1: '#f8f9fa',
          2: '#f1f3f5',
          3: '#e9ecef',
          4: '#dee2e6',
        },
        ink: {
          0: '#212529',
          1: '#343a40',
          2: '#495057',
          3: '#868e96',
          4: '#adb5bd',
        },
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#ef4444',
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        display: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
};

export default config;
