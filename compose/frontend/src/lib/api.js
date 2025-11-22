// API client for Agent Spike FastAPI backend

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * API client for chat backend
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
	 * @returns {Promise<{status: string, timestamp: string}>}
	 */
	async health() {
		const res = await fetch(`${this.baseURL}/health`);
		if (!res.ok) {
			throw new Error(`Health check failed: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Fetch available models from backend
	 * @returns {Promise<{models: Array}>}
	 */
	async fetchModels() {
		const res = await fetch(`${this.baseURL}/chat/models`);
		if (!res.ok) {
			throw new Error(`Failed to fetch models: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get a random question based on indexed video content
	 * @returns {Promise<{question: string}>}
	 */
	async getRandomQuestion() {
		const res = await fetch(`${this.baseURL}/chat/random-question`);
		if (!res.ok) {
			throw new Error(`Failed to fetch random question: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Create WebSocket connection for chat
	 * @param {boolean} useRAG - Whether to use RAG endpoint
	 * @returns {WebSocket}
	 */
	connectWebSocket(useRAG = false) {
		const wsURL = this.baseURL.replace('http://', 'ws://').replace('https://', 'wss://');
		const endpoint = useRAG ? '/chat/ws/rag-chat' : '/chat/ws/chat';
		return new WebSocket(`${wsURL}${endpoint}`);
	}

	/**
	 * Get current stats (one-time fetch)
	 * @returns {Promise<Object>}
	 */
	async getStats() {
		const res = await fetch(`${this.baseURL}/stats`);
		if (!res.ok) {
			throw new Error(`Failed to fetch stats: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Connect to stats SSE stream for real-time updates
	 * @param {function} onMessage - Callback for each stats update
	 * @param {function} onError - Callback for errors
	 * @returns {EventSource}
	 */
	connectStatsStream(onMessage, onError = null) {
		const eventSource = new EventSource(`${this.baseURL}/stats/stream`);

		eventSource.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				onMessage(data);
			} catch (e) {
				console.error('Failed to parse stats:', e);
			}
		};

		eventSource.onerror = (error) => {
			if (onError) {
				onError(error);
			}
		};

		return eventSource;
	}

	/**
	 * Detect URL type (video, channel, or article)
	 * @param {string} url - URL to detect
	 * @returns {Promise<{url: string, type: string}>}
	 */
	async detectUrlType(url) {
		const res = await fetch(`${this.baseURL}/ingest/detect?url=${encodeURIComponent(url)}`);
		if (!res.ok) {
			throw new Error(`Failed to detect URL type: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Ingest a URL (video, channel, or article)
	 * @param {string} url - URL to ingest
	 * @param {string} channelLimit - For channels: 'month', 'year', '50', '100', 'all'
	 * @returns {Promise<{type: string, status: string, message: string, details: object}>}
	 */
	async ingestUrl(url, channelLimit = 'all') {
		const res = await fetch(`${this.baseURL}/ingest`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ url, channel_limit: channelLimit })
		});
		if (!res.ok) {
			const error = await res.json().catch(() => ({ detail: res.statusText }));
			throw new Error(error.detail || `Ingest failed: ${res.statusText}`);
		}
		return res.json();
	}

	// ============ Conversation Methods ============

	/**
	 * List all conversations
	 * @returns {Promise<{conversations: Array}>}
	 */
	async listConversations() {
		const res = await fetch(`${this.baseURL}/conversations`);
		if (!res.ok) {
			throw new Error(`Failed to list conversations: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Create a new conversation
	 * @param {string} title - Initial title
	 * @param {string} model - Model ID
	 * @returns {Promise<Object>}
	 */
	async createConversation(title = 'New conversation', model = '') {
		const res = await fetch(`${this.baseURL}/conversations`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ title, model })
		});
		if (!res.ok) {
			throw new Error(`Failed to create conversation: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get a conversation by ID
	 * @param {string} id - Conversation ID
	 * @returns {Promise<Object>}
	 */
	async getConversation(id) {
		const res = await fetch(`${this.baseURL}/conversations/${id}`);
		if (!res.ok) {
			throw new Error(`Failed to get conversation: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Update a conversation
	 * @param {string} id - Conversation ID
	 * @param {Object} data - Update data (title, model)
	 * @returns {Promise<Object>}
	 */
	async updateConversation(id, data) {
		const res = await fetch(`${this.baseURL}/conversations/${id}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(data)
		});
		if (!res.ok) {
			throw new Error(`Failed to update conversation: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Delete a conversation
	 * @param {string} id - Conversation ID
	 * @returns {Promise<Object>}
	 */
	async deleteConversation(id) {
		const res = await fetch(`${this.baseURL}/conversations/${id}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			throw new Error(`Failed to delete conversation: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Search conversations
	 * @param {string} query - Search query
	 * @returns {Promise<{conversations: Array}>}
	 */
	async searchConversations(query) {
		const res = await fetch(`${this.baseURL}/conversations/search?q=${encodeURIComponent(query)}`);
		if (!res.ok) {
			throw new Error(`Failed to search conversations: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Generate a title for a conversation
	 * @param {string} message - First message to generate title from
	 * @returns {Promise<{title: string}>}
	 */
	async generateTitle(message) {
		const res = await fetch(`${this.baseURL}/conversations/generate-title`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ message })
		});
		if (!res.ok) {
			throw new Error(`Failed to generate title: ${res.statusText}`);
		}
		return res.json();
	}
}

/**
 * Default API client instance
 */
export const api = new MentatAPI();
