/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#17212b',
        canvas: '#f5f7f9',
        coral: '#f36f4f',
        mint: '#22a06b',
        navy: '#20364b',
      },
      boxShadow: {
        card: '0 12px 36px rgba(31, 50, 68, 0.07)',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
