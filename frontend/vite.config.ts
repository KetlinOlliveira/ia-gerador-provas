import { fileURLToPath, URL } from "node:url";

import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Em desenvolvimento, o Vite repassa /api ao backend: o navegador fala com uma origem
// só e o fluxo de eventos (SSE) funciona sem CORS. No compose, o alvo é o serviço
// `backend`; rodando direto no Windows, é a porta publicada pelo compose.
const alvoApi = process.env.API_PROXY_ALVO ?? "http://localhost:8010";

export default defineConfig({
  plugins: [tanstackRouter({ target: "react", autoCodeSplitting: true }), react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: { "/api": { target: alvoApi, changeOrigin: true } },
    // Eventos de arquivo do Windows não chegam ao container; lá o watch usa polling.
    watch: process.env.VITE_POLLING === "true" ? { usePolling: true, interval: 300 } : undefined,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
