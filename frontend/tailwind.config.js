/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        go: '#22c55e',
        nogo: '#ef4444',
        conditions: '#eab308',
      }
    },
  },
  plugins: [],
}
