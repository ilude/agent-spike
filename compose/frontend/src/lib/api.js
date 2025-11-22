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

	// ============ Styles API ============

	/**
	 * Fetch all available writing styles
	 * @returns {Promise<{styles: Array}>}
	 */
	async fetchStyles() {
		const res = await fetch(`${this.baseURL}/styles`);
		if (!res.ok) {
			throw new Error(`Failed to fetch styles: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get a specific writing style by ID
	 * @param {string} styleId - Style identifier (e.g., 'concise', 'detailed')
	 * @returns {Promise<Object>}
	 */
	async getStyle(styleId) {
		const res = await fetch(`${this.baseURL}/styles/${encodeURIComponent(styleId)}`);
		if (!res.ok) {
			throw new Error(`Failed to fetch style: ${res.statusText}`);
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

	// ============ Project Methods ============

	/**
	 * List all projects
	 * @returns {Promise<{projects: Array}>}
	 */
	async listProjects() {
		const res = await fetch(`${this.baseURL}/projects`);
		if (!res.ok) {
			throw new Error(`Failed to list projects: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Create a new project
	 * @param {string} name - Project name
	 * @param {string} description - Project description
	 * @returns {Promise<Object>}
	 */
	async createProject(name = 'New Project', description = '') {
		const res = await fetch(`${this.baseURL}/projects`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name, description })
		});
		if (!res.ok) {
			throw new Error(`Failed to create project: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get a project by ID
	 * @param {string} id - Project ID
	 * @returns {Promise<Object>}
	 */
	async getProject(id) {
		const res = await fetch(`${this.baseURL}/projects/${id}`);
		if (!res.ok) {
			throw new Error(`Failed to get project: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Update a project
	 * @param {string} id - Project ID
	 * @param {Object} data - Update data (name, description, custom_instructions)
	 * @returns {Promise<Object>}
	 */
	async updateProject(id, data) {
		const res = await fetch(`${this.baseURL}/projects/${id}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(data)
		});
		if (!res.ok) {
			throw new Error(`Failed to update project: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Delete a project
	 * @param {string} id - Project ID
	 * @returns {Promise<Object>}
	 */
	async deleteProject(id) {
		const res = await fetch(`${this.baseURL}/projects/${id}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			throw new Error(`Failed to delete project: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Add a conversation to a project
	 * @param {string} projectId - Project ID
	 * @param {string} conversationId - Conversation ID
	 * @returns {Promise<Object>}
	 */
	async addConversationToProject(projectId, conversationId) {
		const res = await fetch(`${this.baseURL}/projects/${projectId}/conversations`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ conversation_id: conversationId })
		});
		if (!res.ok) {
			throw new Error(`Failed to add conversation to project: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Upload a file to a project
	 * @param {string} projectId - Project ID
	 * @param {File} file - File to upload
	 * @returns {Promise<Object>}
	 */
	async uploadProjectFile(projectId, file) {
		const formData = new FormData();
		formData.append('file', file);

		const res = await fetch(`${this.baseURL}/projects/${projectId}/files`, {
			method: 'POST',
			body: formData
		});
		if (!res.ok) {
			throw new Error(`Failed to upload file: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Delete a file from a project
	 * @param {string} projectId - Project ID
	 * @param {string} fileId - File ID
	 * @returns {Promise<Object>}
	 */
	async deleteProjectFile(projectId, fileId) {
		const res = await fetch(`${this.baseURL}/projects/${projectId}/files/${fileId}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			throw new Error(`Failed to delete file: ${res.statusText}`);
		}
		return res.json();
	}

	// ============ Memory Methods ============

	/**
	 * List all memories
	 * @param {string} category - Optional category filter
	 * @returns {Promise<{memories: Array, count: number}>}
	 */
	async listMemories(category = null) {
		let url = `${this.baseURL}/memory`;
		if (category) url += `?category=${encodeURIComponent(category)}`;
		const res = await fetch(url);
		if (!res.ok) {
			throw new Error(`Failed to list memories: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Add a new memory
	 * @param {string} content - Memory content
	 * @param {string} category - Category (preference, fact, context, general)
	 * @returns {Promise<Object>}
	 */
	async addMemory(content, category = 'general') {
		const res = await fetch(`${this.baseURL}/memory`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ content, category })
		});
		if (!res.ok) {
			throw new Error(`Failed to add memory: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get a memory by ID
	 * @param {string} id - Memory ID
	 * @returns {Promise<Object>}
	 */
	async getMemory(id) {
		const res = await fetch(`${this.baseURL}/memory/${id}`);
		if (!res.ok) {
			throw new Error(`Failed to get memory: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Update a memory
	 * @param {string} id - Memory ID
	 * @param {Object} data - Update data (content, category, relevance_score)
	 * @returns {Promise<Object>}
	 */
	async updateMemory(id, data) {
		const res = await fetch(`${this.baseURL}/memory/${id}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(data)
		});
		if (!res.ok) {
			throw new Error(`Failed to update memory: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Delete a memory
	 * @param {string} id - Memory ID
	 * @returns {Promise<Object>}
	 */
	async deleteMemory(id) {
		const res = await fetch(`${this.baseURL}/memory/${id}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			throw new Error(`Failed to delete memory: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Clear all memories
	 * @returns {Promise<{deleted_count: number, message: string}>}
	 */
	async clearAllMemories() {
		const res = await fetch(`${this.baseURL}/memory`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			throw new Error(`Failed to clear memories: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Search memories
	 * @param {string} query - Search query
	 * @returns {Promise<{memories: Array, count: number}>}
	 */
	async searchMemories(query) {
		const res = await fetch(`${this.baseURL}/memory/search?q=${encodeURIComponent(query)}`);
		if (!res.ok) {
			throw new Error(`Failed to search memories: ${res.statusText}`);
		}
		return res.json();
	}

	// ============ Artifact Methods ============

	/**
	 * List all artifacts
	 * @param {string} conversationId - Optional filter by conversation
	 * @param {string} projectId - Optional filter by project
	 * @returns {Promise<{artifacts: Array}>}
	 */
	async listArtifacts(conversationId = null, projectId = null) {
		let url = `${this.baseURL}/artifacts`;
		const params = new URLSearchParams();
		if (conversationId) params.append('conversation_id', conversationId);
		if (projectId) params.append('project_id', projectId);
		if (params.toString()) url += `?${params.toString()}`;

		const res = await fetch(url);
		if (!res.ok) {
			throw new Error(`Failed to list artifacts: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Create a new artifact
	 * @param {string} title - Artifact title
	 * @param {string} content - Artifact content
	 * @param {string} artifactType - Type (document, code, markdown)
	 * @param {string} language - Programming language (for code)
	 * @param {string} conversationId - Associated conversation
	 * @param {string} projectId - Associated project
	 * @returns {Promise<Object>}
	 */
	async createArtifact(
		title = 'Untitled',
		content = '',
		artifactType = 'document',
		language = null,
		conversationId = null,
		projectId = null
	) {
		const res = await fetch(`${this.baseURL}/artifacts`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				title,
				content,
				artifact_type: artifactType,
				language,
				conversation_id: conversationId,
				project_id: projectId
			})
		});
		if (!res.ok) {
			throw new Error(`Failed to create artifact: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get an artifact by ID
	 * @param {string} id - Artifact ID
	 * @returns {Promise<Object>}
	 */
	async getArtifact(id) {
		const res = await fetch(`${this.baseURL}/artifacts/${id}`);
		if (!res.ok) {
			throw new Error(`Failed to get artifact: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Update an artifact
	 * @param {string} id - Artifact ID
	 * @param {Object} data - Update data (title, content, artifact_type, language)
	 * @returns {Promise<Object>}
	 */
	async updateArtifact(id, data) {
		const res = await fetch(`${this.baseURL}/artifacts/${id}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(data)
		});
		if (!res.ok) {
			throw new Error(`Failed to update artifact: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Delete an artifact
	 * @param {string} id - Artifact ID
	 * @returns {Promise<Object>}
	 */
	async deleteArtifact(id) {
		const res = await fetch(`${this.baseURL}/artifacts/${id}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			throw new Error(`Failed to delete artifact: ${res.statusText}`);
		}
		return res.json();
	}
}

/**
 * Default API client instance
 */
export const api = new MentatAPI();
