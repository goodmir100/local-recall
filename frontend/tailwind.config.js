/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      fontFamily: { sans: ['Inter', 'Segoe UI', 'sans-serif'] },
      boxShadow: { glow: '0 16px 60px rgba(58, 206, 167, .12)' },
    },
  },
  plugins: [],
}
