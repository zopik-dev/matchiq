/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#070A11",
        panel: "#0B111E",
        mint: "#3ee6a0",
        sky: "#6ab7ff",
        amber: "#ffb84d",
        home: "#00F2FE",
        homedeep: "#0284C7",
        away: "#F59E0B",
        awaydeep: "#D97706",
      },
      fontFamily: {
        sans: ["Manrope", "system-ui", "sans-serif"],
        display: ["Sora", "Manrope", "sans-serif"],
      },
    },
  },
  plugins: [],
};
