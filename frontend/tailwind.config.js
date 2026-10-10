/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#090D16",
        panel: "#0F1626",
        tile: "#131C30",
        mint: "#9DB4CC",
        sky: "#9DB4CC",
        amber: "#C9B48A",
        home: "#2563EB",
        homedeep: "#1D4ED8",
        away: "#DC2626",
        awaydeep: "#991B1B",
      },
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", "SF Pro Text", "Inter", "system-ui", "sans-serif"],
        display: ["-apple-system", "BlinkMacSystemFont", "SF Pro Display", "Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
