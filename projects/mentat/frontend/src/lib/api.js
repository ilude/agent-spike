// API client for Mentat FastAPI backend

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

/**
 * API client for Mentat backend
 */
export class MentatAPI {
	/**
	 * @param {string} baseURL - Base URL for the API
	 */
	constructor(baseURL = API_URL) {
		this.baseURL = baseURL;
	}

	/**
	 * Check backend health
	 * @returns {Promise<{status: string, timestamp: string, api_key_configured: boolean}>}
	 */
	async health() {
		const res = await fetch(`${this.baseURL}/health`);
		if (!res.ok) {
			throw new Error(`Health check failed: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Create WebSocket connection for chat
	 * @returns {WebSocket}
	 */
	connectWebSocket() {
		const wsURL = this.baseURL.replace('http://', 'ws://').replace('https://', 'wss://');
		return new WebSocket(`${wsURL}/ws/chat`);
	}
}

/**
 * Default API client instance
 */
export const api = new MentatAPI();
