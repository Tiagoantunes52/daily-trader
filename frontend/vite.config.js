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
      // Proxy specific auth endpoints to backend, but NOT the callback URLs
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
      },
      // Proxy callback API calls (when frontend makes fetch requests)
      '/auth/google/callback': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Only proxy if it's an API call (has specific headers or query params)
        bypass: function (req, res, options) {
          // If it's a browser navigation (no fetch headers), let React handle it
          if (!req.headers['content-type'] && !req.headers['accept']?.includes('application/json')) {
            return '/index.html'
          }
        }
      },
      '/auth/github/callback': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Only proxy if it's an API call (has specific headers or query params)
        bypass: function (req, res, options) {
          // If it's a browser navigation (no fetch headers), let React handle it
          if (!req.headers['content-type'] && !req.headers['accept']?.includes('application/json')) {
            return '/index.html'
          }
        }
      }
    },
    // Enable client-side routing fallback
    historyApiFallback: true
  }
})