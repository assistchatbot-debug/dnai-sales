/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: { primary: '#6366f1', secondary: '#a855f7', dark: '#0f172a' },
      animation: { 'bounce-slow': 'bounce 3s infinite' }
    },
  },
  plugins: [],
}
