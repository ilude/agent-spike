import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],

	// Pre-bundle CommonJS OpenTelemetry packages for browser use
	optimizeDeps: {
		include: [
			'@opentelemetry/api',
			'@opentelemetry/sdk-trace-web',
			'@opentelemetry/sdk-trace-base',
			'@opentelemetry/resources',
			'@opentelemetry/semantic-conventions',
			'@opentelemetry/instrumentation',
			'@opentelemetry/instrumentation-fetch',
			'@opentelemetry/exporter-trace-otlp-http'
		]
	},

	// Prevent externalizing OTel packages during SSR
	ssr: {
		noExternal: [
			'@opentelemetry/api',
			'@opentelemetry/sdk-trace-web',
			'@opentelemetry/resources',
			'@opentelemetry/semantic-conventions'
		]
	},

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
	},
	test: {
		// Enable vitest globals (describe, it, expect, etc.)
		globals: true,
		// Use jsdom for DOM testing
		environment: 'jsdom',
		// Setup files run before each test file
		setupFiles: ['./src/lib/__tests__/setup.js'],
		// Include test files
		include: ['src/**/*.{test,spec}.{js,ts}'],
		// Coverage configuration
		coverage: {
			provider: 'v8',
			reporter: ['text', 'json', 'html'],
			include: ['src/lib/**/*.js'],
			exclude: ['src/lib/__tests__/**']
		}
	}
});
