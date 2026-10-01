/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0B0F19",
        panel: "#111827",
        home: "#38bdf8",
        away: "#f43f5e",
      },
    },
  },
  plugins: [],
};
