import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * In development VITE_API_BASE is empty, so the app talks to its own origin
 * and this proxy forwards /api and /ws to the backend. That keeps one set of
 * relative paths working in dev and in production.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const target = env.DEV_BACKEND || 'http://59.103.233.98:7072';

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': { target, changeOrigin: true },
        '/ws': { target: target.replace(/^http/, 'ws'), ws: true },
      },
    },
  };
});
