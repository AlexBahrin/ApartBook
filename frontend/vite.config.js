import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// Django dev server target for API + media proxying
const DJANGO_TARGET = process.env.DJANGO_TARGET || 'http://127.0.0.1:8000'

export default defineConfig(({ command }) => ({
  plugins: [vue()],
  // In production the built assets are served by Django under /static/spa/.
  base: command === 'build' ? '/static/spa/' : '/',
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: DJANGO_TARGET, changeOrigin: true },
      '/media': { target: DJANGO_TARGET, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    manifest: true,
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.js'],
  },
}))
