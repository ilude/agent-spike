// Vitest test setup file
// This runs before each test file

import { vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom/vitest';

// Mock import.meta.env for tests
globalThis.import = { meta: { env: { VITE_API_URL: 'http://localhost:8000' } } };

// Mock fetch globally
globalThis.fetch = vi.fn();

// Mock WebSocket
class MockWebSocket {
	constructor(url) {
		this.url = url;
		this.readyState = WebSocket.CONNECTING;
		this.onopen = null;
		this.onclose = null;
		this.onmessage = null;
		this.onerror = null;

		// Simulate connection
		setTimeout(() => {
			this.readyState = WebSocket.OPEN;
			if (this.onopen) this.onopen({ type: 'open' });
		}, 0);
	}

	send(data) {
		if (this.readyState !== WebSocket.OPEN) {
			throw new Error('WebSocket is not open');
		}
	}

	close() {
		this.readyState = WebSocket.CLOSED;
		if (this.onclose) this.onclose({ type: 'close' });
	}

	// Test helper to simulate receiving a message
	_receiveMessage(data) {
		if (this.onmessage) {
			this.onmessage({ data: JSON.stringify(data) });
		}
	}
}

MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSING = 2;
MockWebSocket.CLOSED = 3;

globalThis.WebSocket = MockWebSocket;

// Mock EventSource for SSE
class MockEventSource {
	constructor(url) {
		this.url = url;
		this.readyState = EventSource.CONNECTING;
		this.onmessage = null;
		this.onerror = null;
		this.onopen = null;

		setTimeout(() => {
			this.readyState = EventSource.OPEN;
			if (this.onopen) this.onopen({ type: 'open' });
		}, 0);
	}

	close() {
		this.readyState = EventSource.CLOSED;
	}

	// Test helper to simulate receiving an event
	_receiveEvent(data) {
		if (this.onmessage) {
			this.onmessage({ data: JSON.stringify(data) });
		}
	}
}

MockEventSource.CONNECTING = 0;
MockEventSource.OPEN = 1;
MockEventSource.CLOSED = 2;

globalThis.EventSource = MockEventSource;

// Reset mocks before each test
beforeEach(() => {
	vi.clearAllMocks();
});
