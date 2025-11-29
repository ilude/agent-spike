import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
	testDir: './tests/e2e',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: 0, // Fail-fast approach - no retries
	workers: process.env.CI ? 1 : undefined,
	reporter: 'html',
	use: {
		baseURL: 'https://mentat.local.ilude.com',
		trace: 'on-first-retry',
		ignoreHTTPSErrors: true, // Local development uses self-signed certs
	},

	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] },
		},
	],

	webServer: {
		command: 'bun run dev',
		url: 'https://mentat.local.ilude.com',
		reuseExistingServer: !process.env.CI,
		ignoreHTTPSErrors: true,
	},
});
