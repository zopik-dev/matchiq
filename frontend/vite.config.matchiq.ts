import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Production build for subpath deployment (e.g. /matchiq/ on a shared host).
// Keeps the dev config unchanged (base "/").
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  build: {
    base: "/matchiq/",
  },
});
