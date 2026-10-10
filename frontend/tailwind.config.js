/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#08080A",
        panel: "#101010",
        tile: "#141416",
        mint: "#9DB4CC",
        sky: "#7FB3FF",
        amber: "#C9B48A",
        home: "#3B82F6",
        homedeep: "#2563EB",
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
