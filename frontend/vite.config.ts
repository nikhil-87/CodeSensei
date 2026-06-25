import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_BASE_URL || "http://localhost:8000";

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "src"),
      },
    },
    server: {
      port: 5173,
      strictPort: false,
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
    build: {
      target: "es2022",
      sourcemap: true,
      rollupOptions: {
        output: {
          manualChunks: {
            "vendor-react": ["react", "react-dom", "react-router-dom"],
            "vendor-charts": ["recharts"],
            "vendor-graph": [
              "cytoscape",
              "cytoscape-cose-bilkent",
              "cytoscape-dagre",
              "react-cytoscapejs",
            ],
            "vendor-mermaid": ["mermaid"],
            "vendor-query": [
              "@tanstack/react-query",
              "@tanstack/react-query-devtools",
            ],
          },
        },
      },
    },
    test: {
      globals: true,
      environment: "happy-dom",
      setupFiles: ["./tests/setup.ts"],
      include: ["src/**/*.{test,spec}.{ts,tsx}"],
      coverage: {
        reporter: ["text", "html"],
        exclude: ["**/*.d.ts", "**/*.test.*", "tests/**", "src/main.tsx"],
      },
    },
  };
});
