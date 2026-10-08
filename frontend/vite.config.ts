import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The SPA and the API share one origin (cookies without CORS). In development
// Vite proxies /api to the FastAPI server on :8000; on Vercel a rewrite does it.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
  preview: { port: 4173, proxy: { "/api": "http://127.0.0.1:8000" } },
  test: {
    environment: "node",
    // `npm run measure` (AEGIS_MEASURE=1) runs the timing harness instead of the unit tests.
    include: process.env.AEGIS_MEASURE ? ["src/**/*.measure.ts"] : ["src/**/*.test.ts"],
    testTimeout: 120_000,
  },
});
