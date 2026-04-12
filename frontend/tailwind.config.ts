import type { Config } from 'tailwindcss';
const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        brand: { 50:'#f0f4ff',100:'#dbe4ff',200:'#bac8ff',300:'#91a7ff',400:'#748ffc',500:'#5c7cfa',600:'#4c6ef5',700:'#4263eb',800:'#3b5bdb',900:'#364fc7' },
        surface: { 0:'#ffffff',1:'#f8f9fa',2:'#f1f3f5',3:'#e9ecef',4:'#dee2e6' },
        ink: { 0:'#212529',1:'#343a40',2:'#495057',3:'#868e96',4:'#adb5bd' },
        success: '#2f9e44', warning: '#f08c00', danger: '#e03131',
      },
      fontFamily: {
        sans: ['var(--font-body)','system-ui','sans-serif'],
        display: ['var(--font-display)','Georgia','serif'],
        mono: ['JetBrains Mono','monospace'],
      },
    },
  },
  plugins: [],
};
export default config;
