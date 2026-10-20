import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Development: Vite on 5173 proxies /api to the backend on 8000 -- same origin, no CORS
// Production: the npm run build output is served by FastAPI (see StaticFiles in main.py)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
