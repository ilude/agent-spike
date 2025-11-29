import { test, expect } from '@playwright/test';

/**
 * E2E tests for video ingestion workflow
 *
 * Prerequisites:
 * - Backend API must be running (make up)
 * - User must be logged in (or auth disabled)
 * - Valid YouTube API key configured
 *
 * Tests verify:
 * - Full ingestion workflow from URL input to completion
 * - SSE events are received and processed correctly
 * - UI updates reflect ingestion progress
 * - Error handling works as expected
 */

test.describe('Video Ingestion Workflow', () => {
	test.beforeEach(async ({ page }) => {
		// Navigate to ingestion page
		await page.goto('/');

		// Wait for page to be ready
		await page.waitForLoadState('networkidle');
	});

	test('should successfully ingest a YouTube video with SSE progress', async ({ page }) => {
		// Find the URL input field
		const urlInput = page.locator('input[type="text"]').first();
		await expect(urlInput).toBeVisible();

		// Enter a test YouTube URL (use a short, well-known video)
		const testUrl = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
		await urlInput.fill(testUrl);

		// Find and click the ingest button
		const ingestButton = page.locator('button:has-text("Ingest")').first();
		await ingestButton.click();

		// Wait for progress indicator to appear
		const progressIndicator = page.locator('[data-testid="ingestion-progress"]').first();
		await expect(progressIndicator).toBeVisible({ timeout: 5000 });

		// Monitor SSE events by watching for progress updates
		// Look for expected progress steps
		await expect(page.locator('text=/extracting.*id/i')).toBeVisible({ timeout: 10000 });
		await expect(page.locator('text=/fetching.*transcript/i')).toBeVisible({ timeout: 30000 });
		await expect(page.locator('text=/archiving/i')).toBeVisible({ timeout: 30000 });
		await expect(page.locator('text=/storing/i')).toBeVisible({ timeout: 30000 });

		// Wait for completion message
		await expect(page.locator('text=/success|ingested/i')).toBeVisible({ timeout: 60000 });

		// Verify progress indicator is hidden after completion
		await expect(progressIndicator).toBeHidden({ timeout: 5000 });

		// Verify the URL input is cleared or reset
		await expect(urlInput).toHaveValue('');
	});

	test('should show error message for invalid YouTube URL', async ({ page }) => {
		const urlInput = page.locator('input[type="text"]').first();
		await expect(urlInput).toBeVisible();

		// Enter an invalid URL
		const invalidUrl = 'https://not-youtube.com/video';
		await urlInput.fill(invalidUrl);

		const ingestButton = page.locator('button:has-text("Ingest")').first();
		await ingestButton.click();

		// Wait for error message
		await expect(page.locator('text=/error|invalid/i')).toBeVisible({ timeout: 10000 });
	});

	test('should handle duplicate video gracefully', async ({ page }) => {
		// First ingestion
		const urlInput = page.locator('input[type="text"]').first();
		const testUrl = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
		await urlInput.fill(testUrl);

		const ingestButton = page.locator('button:has-text("Ingest")').first();
		await ingestButton.click();

		// Wait for first ingestion to complete
		await expect(page.locator('text=/success|ingested/i')).toBeVisible({ timeout: 60000 });

		// Second ingestion of the same video
		await urlInput.fill(testUrl);
		await ingestButton.click();

		// Should show "already cached" or "skipped" message
		await expect(page.locator('text=/already.*cached|skipped/i')).toBeVisible({ timeout: 10000 });
	});

	test('should handle concurrent ingestions', async ({ page, context }) => {
		// Open two pages to simulate concurrent users
		const page2 = await context.newPage();
		await page2.goto('/');
		await page2.waitForLoadState('networkidle');

		// Start ingestion on both pages with different videos
		const url1 = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
		const url2 = 'https://www.youtube.com/watch?v=jNQXAC9IVRw'; // Different video

		// Page 1 ingestion
		await page.locator('input[type="text"]').first().fill(url1);
		await page.locator('button:has-text("Ingest")').first().click();

		// Page 2 ingestion
		await page2.locator('input[type="text"]').first().fill(url2);
		await page2.locator('button:has-text("Ingest")').first().click();

		// Both should show progress
		await expect(page.locator('[data-testid="ingestion-progress"]')).toBeVisible({ timeout: 5000 });
		await expect(page2.locator('[data-testid="ingestion-progress"]')).toBeVisible({ timeout: 5000 });

		// Both should complete successfully
		await expect(page.locator('text=/success|ingested/i')).toBeVisible({ timeout: 60000 });
		await expect(page2.locator('text=/success|ingested/i')).toBeVisible({ timeout: 60000 });

		await page2.close();
	});

	test('should allow cancellation during ingestion', async ({ page }) => {
		const urlInput = page.locator('input[type="text"]').first();
		const testUrl = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
		await urlInput.fill(testUrl);

		const ingestButton = page.locator('button:has-text("Ingest")').first();
		await ingestButton.click();

		// Wait for progress to start
		const progressIndicator = page.locator('[data-testid="ingestion-progress"]');
		await expect(progressIndicator).toBeVisible({ timeout: 5000 });

		// Look for cancel button
		const cancelButton = page.locator('button:has-text("Cancel")');
		if (await cancelButton.isVisible()) {
			await cancelButton.click();

			// Progress should disappear
			await expect(progressIndicator).toBeHidden({ timeout: 5000 });

			// Should show cancellation message
			await expect(page.locator('text=/cancel.*ed/i')).toBeVisible({ timeout: 5000 });
		}
	});
});
