import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Only proxy auth endpoints that should go to backend
      // Do NOT proxy callback URLs - they should be handled by React
      '/auth/login': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth/register': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth/refresh': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth/logout': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth/oauth/status': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth/google/authorize': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth/github/authorize': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
      // Note: /auth/google/callback and /auth/github/callback are NOT proxied
      // They should be handled by the React app routing
      // The OAuthCallback component calls the backend directly
    }
  }
})
