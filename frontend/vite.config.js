import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // Proxy specific auth endpoints to backend, but NOT the callback URLs
      '/auth/login': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/auth/register': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/auth/refresh': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/auth/logout': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/auth/oauth/status': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/auth/google/authorize': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/auth/github/authorize': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // Proxy callback API calls (when OAuthCallback.jsx makes a fetch to exchange the code)
      '/auth/google/callback': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        bypass: function (req) {
          // Browser navigation sends Accept: text/html — serve React so OAuthCallback renders
          // fetch() sends Accept: */* — proxy to backend to exchange code for JWT
          if (req.headers['accept']?.includes('text/html')) {
            return '/index.html'
          }
        }
      },
      '/auth/github/callback': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        bypass: function (req) {
          if (req.headers['accept']?.includes('text/html')) {
            return '/index.html'
          }
        }
      }
    },
    // Enable client-side routing fallback
    historyApiFallback: true
  }
})