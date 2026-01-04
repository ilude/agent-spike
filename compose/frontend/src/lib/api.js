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
		this._getToken = null;
	}

	/**
	 * Set the token getter function (for auth integration)
	 * @param {function(): string|null} getter
	 */
	setTokenGetter(getter) {
		this._getToken = getter;
	}

	/**
	 * Get auth headers if token is available
	 * @returns {Object}
	 */
	_authHeaders() {
		if (!this._getToken) return {};
		const token = this._getToken();
		if (!token) return {};
		return { Authorization: `Bearer ${token}` };
	}

	/**
	 * Make an authenticated fetch request
	 * @param {string} url
	 * @param {Object} options
	 * @returns {Promise<Response>}
	 */
	async _fetch(url, options = {}) {
		const headers = {
			...this._authHeaders(),
			...options.headers
		};
		return fetch(url, { ...options, headers });
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

		// Include auth token in query string if available
		const token = this._getToken ? this._getToken() : null;
		const authQuery = token ? `?token=${encodeURIComponent(token)}` : '';

		return new WebSocket(`${wsURL}${endpoint}${authQuery}`);
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

	/**
	 * Ingest a URL with real-time progress streaming (SSE)
	 * @param {string} url - URL to ingest
	 * @param {string} channelLimit - For channels: 'month', 'year', '50', '100', 'all'
	 * @param {function} onProgress - Callback for progress events: ({step, message, ...})
	 * @param {function} onComplete - Callback for completion: ({type, status, message, details})
	 * @param {function} onError - Callback for errors
	 * @returns {Promise<void>}
	 */
	async ingestUrlStream(url, channelLimit = 'all', onProgress, onComplete, onError) {
		try {
			const res = await fetch(`${this.baseURL}/ingest/stream`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ url, channel_limit: channelLimit })
			});

			if (!res.ok) {
				const error = await res.json().catch(() => ({ detail: res.statusText }));
				onError(new Error(error.detail || `Ingest failed: ${res.statusText}`));
				return;
			}

			const reader = res.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });

				// Parse SSE events from buffer
				const lines = buffer.split('\n');
				buffer = lines.pop() || ''; // Keep incomplete line in buffer

				let currentEvent = null;
				for (const line of lines) {
					if (line.startsWith('event: ')) {
						currentEvent = line.slice(7).trim();
					} else if (line.startsWith('data: ')) {
						const data = line.slice(6);
						try {
							const parsed = JSON.parse(data);
							if (currentEvent === 'progress' && onProgress) {
								onProgress(parsed);
							} else if (currentEvent === 'complete' && onComplete) {
								onComplete(parsed);
							}
						} catch (e) {
							console.error('Failed to parse SSE data:', e, data);
						}
						currentEvent = null;
					}
				}
			}
		} catch (e) {
			if (onError) {
				onError(e);
			}
		}
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

	/**
	 * Generate a filename for content export using LLM
	 * @param {string} content - Content to generate filename for
	 * @param {string} model - Model to use (default: ollama:llama3.2)
	 * @param {string} contentType - Type of content ('message' or 'conversation')
	 * @param {string|null} prompt - Custom prompt template (optional)
	 * @returns {Promise<{filename: string}>}
	 */
	async generateFilename(content, model = 'ollama:llama3.2', contentType = 'conversation', prompt = null) {
		const body = { content, model, content_type: contentType };
		if (prompt) {
			body.prompt = prompt;
		}
		const res = await fetch(`${this.baseURL}/conversations/generate-filename`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		if (!res.ok) {
			throw new Error(`Failed to generate filename: ${res.statusText}`);
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

	// ============ Web Search Methods ============

	/**
	 * Perform a web search
	 * @param {string} query - Search query
	 * @param {number} num - Number of results (1-10)
	 * @returns {Promise<{results: Array, query: string, source: string}>}
	 */
	async webSearch(query, num = 5) {
		const res = await fetch(`${this.baseURL}/search?q=${encodeURIComponent(query)}&num=${num}`);
		if (!res.ok) {
			throw new Error(`Search failed: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Check if URL is Medium and get Freedium version
	 * @param {string} url - URL to check
	 * @returns {Promise<{original_url: string, freedium_url: string, is_medium: boolean}>}
	 */
	async checkFreedium(url) {
		const res = await fetch(`${this.baseURL}/search/freedium?url=${encodeURIComponent(url)}`);
		if (!res.ok) {
			throw new Error(`Freedium check failed: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Fetch article content via Freedium
	 * @param {string} url - Medium URL to fetch
	 * @returns {Promise<{original_url: string, freedium_url: string, is_medium: boolean, content: string}>}
	 */
	async fetchViaFreedium(url) {
		const res = await fetch(`${this.baseURL}/search/freedium`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ url })
		});
		if (!res.ok) {
			throw new Error(`Freedium fetch failed: ${res.statusText}`);
		}
		return res.json();
	}

	// ============ Code Sandbox Methods ============

	/**
	 * List supported programming languages
	 * @returns {Promise<{languages: Array}>}
	 */
	async listSandboxLanguages() {
		const res = await fetch(`${this.baseURL}/sandbox/languages`);
		if (!res.ok) {
			throw new Error(`Failed to list languages: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Execute code in sandbox
	 * @param {string} code - Code to execute
	 * @param {string} language - Language (python, javascript, bash)
	 * @param {number} timeout - Timeout in seconds (1-30)
	 * @param {string} stdin - Optional input
	 * @returns {Promise<Object>}
	 */
	async executeCode(code, language = 'python', timeout = 10, stdin = '') {
		const res = await fetch(`${this.baseURL}/sandbox/execute`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ code, language, timeout, stdin })
		});
		if (!res.ok) {
			throw new Error(`Execution failed: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Validate code without executing
	 * @param {string} code - Code to validate
	 * @param {string} language - Language
	 * @returns {Promise<{valid: boolean, error: string|null, language: string}>}
	 */
	async validateCode(code, language = 'python') {
		const res = await fetch(`${this.baseURL}/sandbox/validate`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ code, language })
		});
		if (!res.ok) {
			throw new Error(`Validation failed: ${res.statusText}`);
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

	// ============ Image Generation Methods ============

	/**
	 * Get supported image sizes and styles
	 * @returns {Promise<{sizes: Array, styles: Array}>}
	 */
	async getImageOptions() {
		const res = await fetch(`${this.baseURL}/imagegen/options`);
		if (!res.ok) {
			throw new Error(`Failed to get options: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Generate an image from text prompt
	 * @param {string} prompt - Text description of desired image
	 * @param {string} size - Size (small, medium, large, wide, tall)
	 * @param {string} style - Style (natural, vivid, anime, photographic, digital-art, cinematic)
	 * @param {number} n - Number of images (1-4)
	 * @returns {Promise<Object>}
	 */
	async generateImage(prompt, size = 'large', style = 'natural', n = 1) {
		const res = await fetch(`${this.baseURL}/imagegen/generate`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ prompt, size, style, n })
		});
		if (!res.ok) {
			throw new Error(`Image generation failed: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * List saved images
	 * @param {number} limit - Max number of images to return
	 * @returns {Promise<{images: Array, count: number}>}
	 */
	async listImages(limit = 50) {
		const res = await fetch(`${this.baseURL}/imagegen/images?limit=${limit}`);
		if (!res.ok) {
			throw new Error(`Failed to list images: ${res.statusText}`);
		}
		return res.json();
	}


	// ============ Backup Methods ============

	/**
	 * List all backups
	 * @returns {Promise<{backups: Array}>}
	 */
	async listBackups() {
		const res = await fetch(`${this.baseURL}/backup`);
		if (!res.ok) {
			throw new Error(`Failed to list backups: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Start a new backup
	 * @returns {Promise<Object>}
	 */
	async startBackup() {
		const res = await fetch(`${this.baseURL}/backup`, {
			method: 'POST'
		});
		if (!res.ok) {
			throw new Error(`Failed to start backup: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get a backup by ID
	 * @param {string} backupId - Backup ID
	 * @returns {Promise<Object>}
	 */
	async getBackup(backupId) {
		const res = await fetch(`${this.baseURL}/backup/${backupId}`);
		if (!res.ok) {
			throw new Error(`Failed to get backup: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Restore a backup
	 * @param {string} backupId - Backup ID
	 * @returns {Promise<Object>}
	 */
	async restoreBackup(backupId) {
		const res = await fetch(`${this.baseURL}/backup/${backupId}/restore`, {
			method: 'POST'
		});
		if (!res.ok) {
			throw new Error(`Failed to restore backup: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Delete a backup
	 * @param {string} backupId - Backup ID
	 * @returns {Promise<Object>}
	 */
	async deleteBackup(backupId) {
		const res = await fetch(`${this.baseURL}/backup/${backupId}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			throw new Error(`Failed to delete backup: ${res.statusText}`);
		}
		return res.json();
	}

	// ============ Settings Methods ============

	/**
	 * Get current user's settings
	 * @returns {Promise<Object>}
	 */
	async getSettings() {
		const res = await this._fetch(`${this.baseURL}/settings`);
		if (!res.ok) {
			throw new Error(`Failed to get settings: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Update user preferences
	 * @param {Object} preferences
	 * @returns {Promise<Object>}
	 */
	async updatePreferences(preferences) {
		const res = await this._fetch(`${this.baseURL}/settings`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(preferences)
		});
		if (!res.ok) {
			throw new Error(`Failed to update preferences: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get API key status
	 * @returns {Promise<Array>}
	 */
	async getApiKeys() {
		const res = await this._fetch(`${this.baseURL}/settings/api-keys`);
		if (!res.ok) {
			throw new Error(`Failed to get API keys: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Update user's API keys
	 * @param {Object} keys - { anthropic?, openai?, openrouter?, youtube? }
	 * @returns {Promise<Object>}
	 */
	async updateApiKeys(keys) {
		const res = await this._fetch(`${this.baseURL}/settings/api-keys`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(keys)
		});
		if (!res.ok) {
			throw new Error(`Failed to update API keys: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get visible models list
	 * @returns {Promise<Array<string>>}
	 */
	async getVisibleModels() {
		const res = await this._fetch(`${this.baseURL}/settings/models`);
		if (!res.ok) {
			throw new Error(`Failed to get visible models: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Update visible models
	 * @param {Array<string>} models - Model IDs to show
	 * @returns {Promise<Object>}
	 */
	async updateVisibleModels(models) {
		const res = await this._fetch(`${this.baseURL}/settings/models`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ visible_models: models })
		});
		if (!res.ok) {
			throw new Error(`Failed to update visible models: ${res.statusText}`);
		}
		return res.json();
	}

	// ============ Admin Settings Methods ============

	/**
	 * Get system configuration (admin only)
	 * @returns {Promise<Object>}
	 */
	async getSystemConfig() {
		const res = await this._fetch(`${this.baseURL}/settings/system`);
		if (!res.ok) {
			throw new Error(`Failed to get system config: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Update system configuration (admin only)
	 * @param {string} key
	 * @param {string} value
	 * @returns {Promise<Object>}
	 */
	async updateSystemConfig(key, value) {
		const res = await this._fetch(`${this.baseURL}/settings/system`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ key, value })
		});
		if (!res.ok) {
			throw new Error(`Failed to update system config: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Export config to .env (admin only)
	 * @param {Array<string>} keys - Specific keys to export (optional)
	 * @returns {Promise<Object>}
	 */
	async exportConfig(keys = null) {
		const res = await this._fetch(`${this.baseURL}/settings/system/export`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: keys ? JSON.stringify(keys) : null
		});
		if (!res.ok) {
			throw new Error(`Failed to export config: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * List all users (admin only)
	 * @returns {Promise<Array>}
	 */
	async listUsers() {
		const res = await this._fetch(`${this.baseURL}/auth/users`);
		if (!res.ok) {
			throw new Error(`Failed to list users: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Delete a user (admin only)
	 * @param {string} userId
	 * @returns {Promise<Object>}
	 */
	async deleteUser(userId) {
		const res = await this._fetch(`${this.baseURL}/auth/users/${userId}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			throw new Error(`Failed to delete user: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Create invite (admin only)
	 * @param {string} email - Optional email restriction
	 * @param {number} expiresDays
	 * @returns {Promise<Object>}
	 */
	async createInvite(email = null, expiresDays = 7) {
		const res = await this._fetch(`${this.baseURL}/auth/invites`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email, expires_days: expiresDays })
		});
		if (!res.ok) {
			throw new Error(`Failed to create invite: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * List invites (admin only)
	 * @returns {Promise<Array>}
	 */
	async listInvites() {
		const res = await this._fetch(`${this.baseURL}/auth/invites`);
		if (!res.ok) {
			throw new Error(`Failed to list invites: ${res.statusText}`);
		}
		return res.json();
	}

	// ============ Studio: Vault Methods ============

	/**
	 * List all vaults
	 * @returns {Promise<{vaults: Array}>}
	 */
	async listVaults() {
		const res = await this._fetch(`${this.baseURL}/vaults`);
		if (!res.ok) {
			throw new Error(`Failed to list vaults: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Create a new vault
	 * @param {Object} data - Vault data
	 * @param {string} data.name - Vault name
	 * @param {string} [data.storage_type] - 'minio' or 'local'
	 * @param {Object} [data.settings] - Vault settings
	 * @returns {Promise<Object>}
	 */
	async createVault({ name, storage_type = 'minio', settings = {} }) {
		const res = await this._fetch(`${this.baseURL}/vaults`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name, storage_type, settings })
		});
		if (!res.ok) {
			throw new Error(`Failed to create vault: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get a vault by ID
	 * @param {string} vaultId - Vault ID
	 * @returns {Promise<Object>}
	 */
	async getVault(vaultId) {
		const res = await this._fetch(`${this.baseURL}/vaults/${vaultId}`);
		if (!res.ok) {
			throw new Error(`Failed to get vault: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get a vault by slug
	 * @param {string} slug - Vault slug
	 * @returns {Promise<Object>}
	 */
	async getVaultBySlug(slug) {
		const res = await this._fetch(`${this.baseURL}/vaults/by-slug/${encodeURIComponent(slug)}`);
		if (!res.ok) {
			throw new Error(`Failed to get vault: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Update a vault
	 * @param {string} vaultId - Vault ID
	 * @param {Object} data - Update data (name, settings)
	 * @returns {Promise<Object>}
	 */
	async updateVault(vaultId, data) {
		const res = await this._fetch(`${this.baseURL}/vaults/${vaultId}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(data)
		});
		if (!res.ok) {
			throw new Error(`Failed to update vault: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Delete a vault
	 * @param {string} vaultId - Vault ID
	 * @returns {Promise<Object>}
	 */
	async deleteVault(vaultId) {
		const res = await this._fetch(`${this.baseURL}/vaults/${vaultId}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			throw new Error(`Failed to delete vault: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get file tree for a vault
	 * @param {string} vaultId - Vault ID
	 * @returns {Promise<{tree: Array}>}
	 */
	async getVaultFileTree(vaultId) {
		const res = await this._fetch(`${this.baseURL}/vaults/${vaultId}/tree`);
		if (!res.ok) {
			throw new Error(`Failed to get file tree: ${res.statusText}`);
		}
		return res.json();
	}

	// ============ Studio: Note Methods ============

	/**
	 * List notes in a vault
	 * @param {string} vaultId - Vault ID
	 * @param {string} folderPath - Optional folder filter
	 * @returns {Promise<{notes: Array}>}
	 */
	async listNotes(vaultId, folderPath = null) {
		let url = `${this.baseURL}/notes?vault_id=${encodeURIComponent(vaultId)}`;
		if (folderPath) url += `&folder_path=${encodeURIComponent(folderPath)}`;
		const res = await fetch(url);
		if (!res.ok) {
			throw new Error(`Failed to list notes: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Create a new note
	 * @param {string} vaultId - Vault ID
	 * @param {string} path - Note path
	 * @param {string} content - Note content
	 * @param {string} title - Note title
	 * @returns {Promise<Object>}
	 */
	async createNote(vaultId, path, content = '', title = null) {
		const res = await this._fetch(`${this.baseURL}/notes`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ vault_id: vaultId, path, content, title })
		});
		if (!res.ok) {
			throw new Error(`Failed to create note: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get a note by ID
	 * @param {string} noteId - Note ID
	 * @returns {Promise<Object>}
	 */
	async getNote(noteId) {
		const res = await this._fetch(`${this.baseURL}/notes/${noteId}`);
		if (!res.ok) {
			throw new Error(`Failed to get note: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get a note by vault and path
	 * @param {string} vaultId - Vault ID
	 * @param {string} path - Note path
	 * @returns {Promise<Object>}
	 */
	async getNoteByPath(vaultId, path) {
		const res = await this._fetch(`${this.baseURL}/notes/by-path/${vaultId}/${encodeURIComponent(path)}`);
		if (!res.ok) {
			throw new Error(`Failed to get note: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Update a note
	 * @param {string} noteId - Note ID
	 * @param {Object} data - Update data (content, title, path)
	 * @returns {Promise<Object>}
	 */
	async updateNote(noteId, data) {
		const res = await this._fetch(`${this.baseURL}/notes/${noteId}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(data)
		});
		if (!res.ok) {
			throw new Error(`Failed to update note: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Delete a note
	 * @param {string} noteId - Note ID
	 * @returns {Promise<Object>}
	 */
	async deleteNote(noteId) {
		const res = await this._fetch(`${this.baseURL}/notes/${noteId}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			throw new Error(`Failed to delete note: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Search notes
	 * @param {string} vaultId - Vault ID
	 * @param {string} query - Search query
	 * @param {number} limit - Max results
	 * @returns {Promise<{notes: Array}>}
	 */
	async searchNotes(vaultId, query, limit = 20) {
		const res = await fetch(
			`${this.baseURL}/notes/search/${vaultId}?q=${encodeURIComponent(query)}&limit=${limit}`
		);
		if (!res.ok) {
			throw new Error(`Failed to search notes: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get links for a note
	 * @param {string} noteId - Note ID
	 * @returns {Promise<{outlinks: Array, backlinks: Array}>}
	 */
	async getNoteLinks(noteId) {
		const res = await this._fetch(`${this.baseURL}/notes/${noteId}/links`);
		if (!res.ok) {
			throw new Error(`Failed to get note links: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Create a link between notes
	 * @param {string} sourceNoteId - Source note ID
	 * @param {string} targetNoteId - Target note ID
	 * @param {string} linkText - Link display text
	 * @returns {Promise<Object>}
	 */
	async createNoteLink(sourceNoteId, targetNoteId, linkText) {
		const res = await this._fetch(`${this.baseURL}/notes/${sourceNoteId}/links`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ target_id: targetNoteId, link_text: linkText })
		});
		if (!res.ok) {
			throw new Error(`Failed to create link: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get AI suggestions for a note
	 * @param {string} noteId - Note ID
	 * @param {string} status - Filter by status
	 * @returns {Promise<{suggestions: Array}>}
	 */
	async getNoteSuggestions(noteId, status = 'pending') {
		const res = await this._fetch(`${this.baseURL}/notes/${noteId}/suggestions?status=${status}`);
		if (!res.ok) {
			throw new Error(`Failed to get suggestions: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Accept an AI suggestion
	 * @param {string} noteId - Note ID
	 * @param {string} suggestionId - Suggestion ID
	 * @returns {Promise<Object>}
	 */
	async acceptSuggestion(noteId, suggestionId) {
		const res = await this._fetch(`${this.baseURL}/notes/${noteId}/suggestions/${suggestionId}/accept`, {
			method: 'POST'
		});
		if (!res.ok) {
			throw new Error(`Failed to accept suggestion: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Reject an AI suggestion
	 * @param {string} noteId - Note ID
	 * @param {string} suggestionId - Suggestion ID
	 * @returns {Promise<Object>}
	 */
	async rejectSuggestion(noteId, suggestionId) {
		const res = await this._fetch(`${this.baseURL}/notes/${noteId}/suggestions/${suggestionId}/reject`, {
			method: 'POST'
		});
		if (!res.ok) {
			throw new Error(`Failed to reject suggestion: ${res.statusText}`);
		}
		return res.json();
	}

	// ============ Studio: Graph Methods ============

	/**
	 * Get graph data for a vault
	 * @param {string} vaultId - Vault ID
	 * @returns {Promise<{nodes: Array, edges: Array}>}
	 */
	async getGraphData(vaultId) {
		const res = await this._fetch(`${this.baseURL}/graph/${vaultId}`);
		if (!res.ok) {
			throw new Error(`Failed to get graph data: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get local graph centered on a note
	 * @param {string} vaultId - Vault ID
	 * @param {string} noteId - Note ID
	 * @param {number} depth - Depth of graph (hops)
	 * @returns {Promise<{nodes: Array, edges: Array}>}
	 */
	async getLocalGraph(vaultId, noteId, depth = 2) {
		const res = await this._fetch(`${this.baseURL}/graph/${vaultId}/local/${noteId}?depth=${depth}`);
		if (!res.ok) {
			throw new Error(`Failed to get local graph: ${res.statusText}`);
		}
		return res.json();
	}

	/**
	 * Get graph statistics
	 * @param {string} vaultId - Vault ID
	 * @returns {Promise<Object>}
	 */
	async getGraphStats(vaultId) {
		const res = await this._fetch(`${this.baseURL}/graph/${vaultId}/stats`);
		if (!res.ok) {
			throw new Error(`Failed to get graph stats: ${res.statusText}`);
		}
		return res.json();
	}
}

/**
 * Default API client instance
 */
export const api = new MentatAPI();
