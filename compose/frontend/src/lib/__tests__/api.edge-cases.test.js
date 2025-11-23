// Edge case and error handling tests for MentatAPI client
// Tests network failures, malformed responses, and boundary conditions

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MentatAPI } from '../api.js';

describe('MentatAPI Edge Cases', () => {
	let client;

	beforeEach(() => {
		client = new MentatAPI('http://test-api:8000');
		vi.clearAllMocks();
	});

	// ============ Network Failures ============

	describe('Network Failures', () => {
		it('should handle network errors gracefully', async () => {
			fetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

			await expect(client.health()).rejects.toThrow('Failed to fetch');
		});

		it('should handle timeout errors', async () => {
			fetch.mockRejectedValueOnce(new DOMException('The operation was aborted', 'AbortError'));

			await expect(client.health()).rejects.toThrow('The operation was aborted');
		});

		it('should handle DNS resolution failures', async () => {
			fetch.mockRejectedValueOnce(new TypeError('getaddrinfo ENOTFOUND'));

			await expect(client.getStats()).rejects.toThrow('getaddrinfo ENOTFOUND');
		});

		it('should handle connection refused', async () => {
			fetch.mockRejectedValueOnce(new TypeError('ECONNREFUSED'));

			await expect(client.listConversations()).rejects.toThrow('ECONNREFUSED');
		});
	});

	// ============ HTTP Status Codes ============

	describe('HTTP Status Codes', () => {
		it('should handle 400 Bad Request', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				statusText: 'Bad Request',
				json: () => Promise.resolve({ detail: 'Invalid input' })
			});

			await expect(client.ingestUrl('bad')).rejects.toThrow('Invalid input');
		});

		it('should handle 401 Unauthorized', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				status: 401,
				statusText: 'Unauthorized'
			});

			await expect(client.listProjects()).rejects.toThrow('Failed to list projects: Unauthorized');
		});

		it('should handle 403 Forbidden', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				status: 403,
				statusText: 'Forbidden'
			});

			await expect(client.deleteProject('123')).rejects.toThrow('Failed to delete project: Forbidden');
		});

		it('should handle 404 Not Found', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				statusText: 'Not Found'
			});

			await expect(client.getConversation('nonexistent')).rejects.toThrow('Failed to get conversation: Not Found');
		});

		it('should handle 429 Too Many Requests', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				status: 429,
				statusText: 'Too Many Requests'
			});

			await expect(client.fetchModels()).rejects.toThrow('Failed to fetch models: Too Many Requests');
		});

		it('should handle 500 Internal Server Error', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				statusText: 'Internal Server Error'
			});

			await expect(client.health()).rejects.toThrow('Health check failed: Internal Server Error');
		});

		it('should handle 502 Bad Gateway', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				status: 502,
				statusText: 'Bad Gateway'
			});

			await expect(client.getStats()).rejects.toThrow('Failed to fetch stats: Bad Gateway');
		});

		it('should handle 503 Service Unavailable', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				status: 503,
				statusText: 'Service Unavailable'
			});

			await expect(client.listConversations()).rejects.toThrow('Failed to list conversations: Service Unavailable');
		});

		it('should handle 504 Gateway Timeout', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				status: 504,
				statusText: 'Gateway Timeout'
			});

			await expect(client.searchConversations('test')).rejects.toThrow('Failed to search conversations: Gateway Timeout');
		});
	});

	// ============ Malformed Responses ============

	describe('Malformed Responses', () => {
		it('should handle JSON parse error', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.reject(new SyntaxError('Unexpected token'))
			});

			await expect(client.health()).rejects.toThrow('Unexpected token');
		});

		it('should handle empty response body', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(null)
			});

			const result = await client.health();
			expect(result).toBeNull();
		});

		it('should handle response with wrong structure', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ unexpected: 'structure' })
			});

			const result = await client.listConversations();
			expect(result).toEqual({ unexpected: 'structure' });
			// Note: API client doesn't validate response structure
		});

		it('should handle ingest error fallback when JSON parse fails', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				statusText: 'Bad Request',
				json: () => Promise.reject(new Error('Invalid JSON'))
			});

			// When JSON parse fails, catch returns { detail: statusText }
			// So error.detail = 'Bad Request', which is truthy
			await expect(client.ingestUrl('bad')).rejects.toThrow('Bad Request');
		});
	});

	// ============ URL Encoding ============

	describe('URL Encoding', () => {
		it('should properly encode special characters in search query', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ conversations: [] })
			});

			await client.searchConversations('hello & goodbye');

			expect(fetch).toHaveBeenCalledWith(
				'http://test-api:8000/conversations/search?q=hello%20%26%20goodbye'
			);
		});

		it('should encode URL with special characters for detection', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ type: 'video' })
			});

			await client.detectUrlType('https://example.com/path?foo=bar&baz=qux');

			expect(fetch).toHaveBeenCalledWith(
				'http://test-api:8000/ingest/detect?url=https%3A%2F%2Fexample.com%2Fpath%3Ffoo%3Dbar%26baz%3Dqux'
			);
		});

		it('should handle unicode in search query', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ conversations: [] })
			});

			await client.searchConversations('日本語 emoji 🎉');

			expect(fetch).toHaveBeenCalledWith(expect.stringContaining('conversations/search?q='));
		});
	});

	// ============ Boundary Conditions ============

	describe('Boundary Conditions', () => {
		it('should handle empty string for conversation title', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ id: '123', title: '' })
			});

			const result = await client.createConversation('', '');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/conversations', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ title: '', model: '' })
			});
		});

		it('should handle very long title', async () => {
			const longTitle = 'a'.repeat(10000);
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ id: '123' })
			});

			await client.createConversation(longTitle);

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/conversations', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ title: longTitle, model: '' })
			});
		});

		it('should handle empty search query', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ conversations: [] })
			});

			await client.searchConversations('');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/conversations/search?q=');
		});

		it('should handle null/undefined parameters gracefully', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ artifacts: [] })
			});

			// listArtifacts with null parameters
			await client.listArtifacts(null, null);

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/artifacts');
		});
	});

	// ============ WebSocket Edge Cases ============

	describe('WebSocket Edge Cases', () => {
		it('should handle baseURL without protocol correctly', () => {
			// This tests that the replace works even with edge cases
			const ws = client.connectWebSocket();
			expect(ws.url).toContain('ws://');
		});

		it('should create separate WebSocket instances', () => {
			const ws1 = client.connectWebSocket(false);
			const ws2 = client.connectWebSocket(true);

			expect(ws1).not.toBe(ws2);
			expect(ws1.url).not.toBe(ws2.url);
		});
	});

	// ============ EventSource Edge Cases ============

	describe('EventSource Edge Cases', () => {
		it('should handle EventSource error callback', async () => {
			const onMessage = vi.fn();
			const onError = vi.fn();

			const eventSource = client.connectStatsStream(onMessage, onError);

			// Simulate an error
			eventSource.onerror({ type: 'error' });

			expect(onError).toHaveBeenCalledWith({ type: 'error' });
		});

		it('should handle EventSource without error callback', async () => {
			const onMessage = vi.fn();

			// Should not throw when no error callback provided
			const eventSource = client.connectStatsStream(onMessage);

			// Simulate an error - should not throw
			expect(() => {
				if (eventSource.onerror) eventSource.onerror({ type: 'error' });
			}).not.toThrow();
		});
	});

	// ============ File Upload Edge Cases ============

	describe('File Upload Edge Cases', () => {
		it('should handle large file upload', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ id: 'file-123' })
			});

			// Create a mock large file (10MB)
			const largeContent = new Uint8Array(10 * 1024 * 1024);
			const mockFile = new File([largeContent], 'large.bin', { type: 'application/octet-stream' });

			await client.uploadProjectFile('proj-123', mockFile);

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/projects/proj-123/files', {
				method: 'POST',
				body: expect.any(FormData)
			});
		});

		it('should handle file with special characters in name', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ id: 'file-123' })
			});

			const mockFile = new File(['content'], 'test file (1).pdf', { type: 'application/pdf' });

			await client.uploadProjectFile('proj-123', mockFile);

			// Verify FormData was created (fetch was called with body)
			const [, options] = fetch.mock.calls[0];
			expect(options.body).toBeInstanceOf(FormData);
		});

		it('should handle upload failure', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				statusText: 'Payload Too Large'
			});

			const mockFile = new File(['content'], 'test.pdf');

			await expect(client.uploadProjectFile('proj-123', mockFile)).rejects.toThrow(
				'Failed to upload file: Payload Too Large'
			);
		});
	});

	// ============ Concurrent Requests ============

	describe('Concurrent Requests', () => {
		it('should handle multiple concurrent requests', async () => {
			fetch
				.mockResolvedValueOnce({
					ok: true,
					json: () => Promise.resolve({ conversations: [] })
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () => Promise.resolve({ projects: [] })
				})
				.mockResolvedValueOnce({
					ok: true,
					json: () => Promise.resolve({ artifacts: [] })
				});

			const [conversations, projects, artifacts] = await Promise.all([
				client.listConversations(),
				client.listProjects(),
				client.listArtifacts()
			]);

			expect(conversations).toEqual({ conversations: [] });
			expect(projects).toEqual({ projects: [] });
			expect(artifacts).toEqual({ artifacts: [] });
			expect(fetch).toHaveBeenCalledTimes(3);
		});

		it('should handle partial failures in concurrent requests', async () => {
			fetch
				.mockResolvedValueOnce({
					ok: true,
					json: () => Promise.resolve({ conversations: [] })
				})
				.mockResolvedValueOnce({
					ok: false,
					statusText: 'Internal Server Error'
				});

			const results = await Promise.allSettled([
				client.listConversations(),
				client.listProjects()
			]);

			expect(results[0].status).toBe('fulfilled');
			expect(results[1].status).toBe('rejected');
		});
	});
});
