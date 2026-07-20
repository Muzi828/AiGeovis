import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  base: '/AiGeovis/',
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 8939,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:35696',
        changeOrigin: true,
      },
    },
  },
})
