import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [svelte()],
  server: {
    host: '0.0.0.0',  // Listen on all interfaces for Docker
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true,  // Required for Docker volume mounts on Windows
      interval: 100
    }
  },
})
