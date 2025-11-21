import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		host: '0.0.0.0',  // Listen on all interfaces
		port: 5173,
		strictPort: true,
		allowedHosts: ['mentat.local.ilude.com', 'localhost'],
		// HMR works natively when running locally
		// When behind traefik (HTTPS), HMR WebSocket upgrades automatically
	},
	preview: {
		host: '0.0.0.0',
		port: 5173,
		strictPort: true
	}
});
