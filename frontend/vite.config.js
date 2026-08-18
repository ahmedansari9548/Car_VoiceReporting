import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://59.103.233.98:7072',
      '/ws': { target: 'ws://59.103.233.98:7072', ws: true },
    }
  }
})
