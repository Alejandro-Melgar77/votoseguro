/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'civic-navy': {
          950: '#070C1B',
          900: '#0B132B',
          800: '#1C2541',
          700: '#3A506B',
        },
        'ballot-ivory': {
          50: '#FAF9F6',
          100: '#F8F7F4',
          200: '#EFECE6',
          300: '#E2DDD4',
        },
        'seal-emerald': {
          DEFAULT: '#047857',
          light: '#D1FAE5',
          dark: '#065F46',
        },
        'seal-amber': {
          DEFAULT: '#B45309',
          light: '#FEF3C7',
          dark: '#92400E',
        },
        'seal-crimson': {
          DEFAULT: '#B91C1C',
          light: '#FEE2E2',
          dark: '#991B1B',
        },
      },
      fontFamily: {
        title: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'electoral': '0 4px 20px -2px rgba(11, 19, 43, 0.08), 0 2px 6px -1px rgba(11, 19, 43, 0.04)',
        'seal': '0 0 0 1px rgba(11, 19, 43, 0.1), 0 2px 4px rgba(11, 19, 43, 0.05)',
      },
    },
  },
  plugins: [],
}
