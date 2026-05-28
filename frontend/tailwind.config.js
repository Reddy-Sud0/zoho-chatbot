/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./pages/**/*.{js,jsx}", "./components/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        brand: {
          50:  '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95',
        },
        surface: {
          50:  '#0a0b14',
          100: '#0f1120',
          200: '#141628',
          300: '#1a1d30',
          400: '#212440',
        }
      },
      animation: {
        'fade-up':    'fadeSlideUp 0.35s cubic-bezier(0.22,1,0.36,1) forwards',
        'fade-left':  'fadeSlideLeft 0.35s cubic-bezier(0.22,1,0.36,1) forwards',
        'fade-right': 'fadeSlideRight 0.35s cubic-bezier(0.22,1,0.36,1) forwards',
        'spin-slow':  'spin 8s linear infinite',
        'breathe':    'breathe 2s ease-in-out infinite',
      },
      backdropBlur: {
        xs: '4px',
      },
    },
  },
  plugins: [],
};
