/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#193044',
        canvas: '#edf1f2',
        amber: '#bb761d',
        mist: '#f7f9f8',
      },
      boxShadow: { panel: '0 10px 30px rgba(25, 48, 68, 0.08)' },
    },
  },
  plugins: [],
}
