/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dark': '#0a0a0a',
        'accent': '#7c3aed',
        'accent-light': '#a855f7',
      },
      backgroundImage: {
        'neural-grid': `
          linear-gradient(to right, rgba(124, 58, 237, 0.1) 1px, transparent 1px),
          linear-gradient(to bottom, rgba(124, 58, 237, 0.1) 1px, transparent 1px)
        `,
      },
      backgroundSize: {
        'grid': '40px 40px',
      },
      animation: {
        'pulse-border': 'pulse-border 2s infinite',
        'grid-flow': 'grid-flow 8s linear infinite',
      },
      keyframes: {
        'pulse-border': {
          '0%, 100%': { opacity: '0.5' },
          '50%': { opacity: '1' },
        },
        'grid-flow': {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '40px 40px' },
        },
      },
    },
  },
  plugins: [],
}
