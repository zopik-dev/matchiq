import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  // Multi-site deployment: build assets under a subpath so MatchIQ can live
  // alongside other sites on the same host (e.g. http://host/matchiq/).
  // Set VITE_BASE_PATH=/matchiq/ when building for a subpath; default "/" is
  // the standalone root deployment.
  build: {
    base: process.env.VITE_BASE_PATH || "/",
  },
});
