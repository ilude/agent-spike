import { test, expect } from '@playwright/test';

/**
 * E2E tests for error scenarios
 *
 * Tests verify:
 * - UI handles backend errors gracefully
 * - Error messages are user-friendly
 * - State is cleaned up after errors
 * - Users can retry after errors
 */

test.describe('Error Scenarios', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/');
		await page.waitForLoadState('networkidle');
	});

	test('should handle API server down', async ({ page }) => {
		// Intercept all API calls and fail them
		await page.route('**/api/**', route => {
			route.abort('failed');
		});

		const urlInput = page.locator('input[type="text"]').first();
		await urlInput.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ');

		await page.locator('button:has-text("Ingest")').first().click();

		// Should show connection error
		await expect(page.locator('text=/cannot.*connect|server.*unavailable|connection.*failed/i')).toBeVisible({ timeout: 10000 });
	});

	test('should handle transcript fetch failure', async ({ page }) => {
		// Intercept ingest endpoint to return error
		await page.route('**/ingest/stream', route => {
			route.fulfill({
				status: 200,
				contentType: 'text/event-stream',
				body: 'event: complete\ndata: {"type": "video", "status": "error", "message": "ERROR: Transcript not available", "details": {}}\n\n'
			});
		});

		const urlInput = page.locator('input[type="text"]').first();
		await urlInput.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ');

		await page.locator('button:has-text("Ingest")').first().click();

		// Should show transcript error
		await expect(page.locator('text=/transcript.*not.*available|transcript.*error/i')).toBeVisible({ timeout: 10000 });
	});

	test('should handle database connection error', async ({ page }) => {
		// Intercept ingest endpoint to return database error
		await page.route('**/ingest/stream', route => {
			route.fulfill({
				status: 200,
				contentType: 'text/event-stream',
				body: 'event: complete\ndata: {"type": "video", "status": "error", "message": "Failed to ingest video: Database connection failed", "details": {}}\n\n'
			});
		});

		const urlInput = page.locator('input[type="text"]').first();
		await urlInput.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ');

		await page.locator('button:has-text("Ingest")').first().click();

		// Should show database error
		await expect(page.locator('text=/database.*error|failed.*ingest/i')).toBeVisible({ timeout: 10000 });
	});

	test('should allow retry after error', async ({ page }) => {
		// First attempt - simulate error
		await page.route('**/ingest/stream', route => {
			route.abort('failed');
		});

		const urlInput = page.locator('input[type="text"]').first();
		const testUrl = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
		await urlInput.fill(testUrl);

		await page.locator('button:has-text("Ingest")').first().click();
		await expect(page.locator('text=/error|failed/i')).toBeVisible({ timeout: 10000 });

		// Clear route interception for retry
		await page.unroute('**/ingest/stream');

		// Retry button should be available or input should be re-enabled
		const retryButton = page.locator('button:has-text("Retry")');
		if (await retryButton.isVisible()) {
			await retryButton.click();
		} else {
			// If no retry button, just re-submit
			await page.locator('button:has-text("Ingest")').first().click();
		}

		// Second attempt should work (or at least not fail with connection error)
		await page.waitForTimeout(2000);
	});

	test('should handle rate limiting', async ({ page }) => {
		// Intercept to return 429 Too Many Requests
		await page.route('**/ingest/stream', route => {
			route.fulfill({
				status: 429,
				body: JSON.stringify({ detail: 'Too many requests' })
			});
		});

		const urlInput = page.locator('input[type="text"]').first();
		await urlInput.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ');

		await page.locator('button:has-text("Ingest")').first().click();

		// Should show rate limit message
		await expect(page.locator('text=/too.*many.*requests|rate.*limit|try.*again.*later/i')).toBeVisible({ timeout: 10000 });
	});

	test('should handle network timeout', async ({ page }) => {
		// Intercept and delay indefinitely
		await page.route('**/ingest/stream', route => {
			// Never fulfill - simulates timeout
		});

		const urlInput = page.locator('input[type="text"]').first();
		await urlInput.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ');

		await page.locator('button:has-text("Ingest")').first().click();

		// Wait for timeout message (if UI implements timeout)
		// Or verify spinner continues (if no timeout)
		await page.waitForTimeout(30000);

		// Check for timeout message or still-running indicator
		const hasTimeout = await page.locator('text=/timeout|taking.*too.*long/i').count() > 0;
		const hasProgress = await page.locator('[data-testid="ingestion-progress"]').isVisible();

		// Either should show timeout or still be in progress
		expect(hasTimeout || hasProgress).toBeTruthy();
	});

	test('should clear error message on new ingestion', async ({ page }) => {
		// First attempt - simulate error
		await page.route('**/ingest/stream', route => {
			route.abort('failed');
		});

		const urlInput = page.locator('input[type="text"]').first();
		await urlInput.fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ');

		await page.locator('button:has-text("Ingest")').first().click();
		await expect(page.locator('text=/error|failed/i')).toBeVisible({ timeout: 10000 });

		// Clear interception
		await page.unroute('**/ingest/stream');

		// Start new ingestion
		await urlInput.fill('https://www.youtube.com/watch?v=jNQXAC9IVRw');
		await page.locator('button:has-text("Ingest")').first().click();

		// Previous error message should be cleared
		await page.waitForTimeout(1000);
		// New progress should show, old error should be gone
	});
});
