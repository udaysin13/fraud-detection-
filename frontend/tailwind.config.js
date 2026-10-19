/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          navy: '#F5F8FC',
          surface: '#FFFFFF',
          card: '#FFFFFF',
          border: '#E3EAF2',
          hover: '#EFF6FF',
          teal: '#0F766E',
          'teal-light': '#0D9488',
          blue: '#2563EB',
          'blue-light': '#3B82F6',
          orange: '#A16207',
          'orange-hover': '#854D0E',
          lightbg: '#F5F8FC',
          lightcard: '#FFFFFF',
          lightborder: '#E3EAF2',
        },
        risk: {
          low: '#10B981',
          'low-bg': 'rgba(16, 185, 129, 0.1)',
          review: '#F59E0B',
          'review-bg': 'rgba(245, 158, 11, 0.1)',
          high: '#EF4444',
          'high-bg': 'rgba(239, 68, 68, 0.1)',
        },
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
      },
      borderRadius: {
        'card': '14px',
      },
      boxShadow: {
        'card-soft': '0 2px 10px -2px rgba(15, 23, 42, 0.05), 0 1px 3px -1px rgba(15, 23, 42, 0.03)',
        'card-dark': '0 4px 20px -2px rgba(0, 0, 0, 0.35)',
        'card-hover': '0 8px 24px -4px rgba(15, 23, 42, 0.1)',
      },
    },
  },
  plugins: [],
};
