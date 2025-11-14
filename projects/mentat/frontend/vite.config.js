import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		host: '0.0.0.0',  // Listen on all interfaces for Docker
		port: 5173,
		strictPort: true,
		watch: {
			usePolling: true,  // Required for Docker volume mounts on Windows
			interval: 100
		}
	},
	preview: {
		host: '0.0.0.0',
		port: 5173,
		strictPort: true
	}
});
