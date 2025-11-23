// Unit tests for MentatAPI client
// Tests all 28 API methods with mocked fetch responses

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MentatAPI, api } from '../api.js';

describe('MentatAPI', () => {
	let client;

	beforeEach(() => {
		client = new MentatAPI('http://test-api:8000');
		vi.clearAllMocks();
	});

	describe('constructor', () => {
		it('should use provided baseURL', () => {
			const custom = new MentatAPI('http://custom:9000');
			expect(custom.baseURL).toBe('http://custom:9000');
		});

		it('should use default URL when not provided', () => {
			// Default comes from import.meta.env.VITE_API_URL
			const defaultClient = new MentatAPI();
			expect(defaultClient.baseURL).toBeDefined();
		});
	});

	// ============ Health & Stats ============

	describe('health()', () => {
		it('should return health status on success', async () => {
			const mockResponse = { status: 'ok', timestamp: '2025-01-01T00:00:00Z' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResponse)
			});

			const result = await client.health();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/health');
			expect(result).toEqual(mockResponse);
		});

		it('should throw error on failure', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				statusText: 'Service Unavailable'
			});

			await expect(client.health()).rejects.toThrow('Health check failed: Service Unavailable');
		});
	});

	describe('getStats()', () => {
		it('should return stats on success', async () => {
			const mockStats = { videos: 100, articles: 50 };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockStats)
			});

			const result = await client.getStats();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/stats');
			expect(result).toEqual(mockStats);
		});

		it('should throw error on failure', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				statusText: 'Internal Server Error'
			});

			await expect(client.getStats()).rejects.toThrow('Failed to fetch stats');
		});
	});

	// ============ Models ============

	describe('fetchModels()', () => {
		it('should return models list', async () => {
			const mockModels = { models: [{ id: 'gpt-4', name: 'GPT-4' }] };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockModels)
			});

			const result = await client.fetchModels();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/chat/models');
			expect(result).toEqual(mockModels);
		});

		it('should throw error on failure', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				statusText: 'Not Found'
			});

			await expect(client.fetchModels()).rejects.toThrow('Failed to fetch models');
		});
	});

	describe('getRandomQuestion()', () => {
		it('should return random question', async () => {
			const mockQuestion = { question: 'What is AI?' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockQuestion)
			});

			const result = await client.getRandomQuestion();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/chat/random-question');
			expect(result).toEqual(mockQuestion);
		});
	});

	// ============ Styles API ============

	describe('fetchStyles()', () => {
		it('should return all writing styles', async () => {
			const mockStyles = {
				styles: [
					{ id: 'default', name: 'Default', description: 'Balanced responses' },
					{ id: 'concise', name: 'Concise', description: 'Brief responses' }
				]
			};
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockStyles)
			});

			const result = await client.fetchStyles();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/styles');
			expect(result).toEqual(mockStyles);
		});

		it('should throw on fetch error', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				statusText: 'Internal Server Error'
			});

			await expect(client.fetchStyles()).rejects.toThrow('Failed to fetch styles');
		});
	});

	describe('getStyle()', () => {
		it('should return a specific style', async () => {
			const mockStyle = {
				id: 'concise',
				name: 'Concise',
				description: 'Brief responses',
				system_prompt_modifier: 'Be concise'
			};
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockStyle)
			});

			const result = await client.getStyle('concise');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/styles/concise');
			expect(result).toEqual(mockStyle);
		});

		it('should URL-encode style ID', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({})
			});

			await client.getStyle('style with spaces');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/styles/style%20with%20spaces');
		});

		it('should throw on 404', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				statusText: 'Not Found'
			});

			await expect(client.getStyle('nonexistent')).rejects.toThrow('Failed to fetch style');
		});
	});

	// ============ WebSocket & SSE ============

	describe('connectWebSocket()', () => {
		it('should create WebSocket with chat endpoint by default', () => {
			const ws = client.connectWebSocket(false);

			expect(ws.url).toBe('ws://test-api:8000/chat/ws/chat');
		});

		it('should create WebSocket with RAG endpoint when useRAG is true', () => {
			const ws = client.connectWebSocket(true);

			expect(ws.url).toBe('ws://test-api:8000/chat/ws/rag-chat');
		});

		it('should handle https to wss conversion', () => {
			const httpsClient = new MentatAPI('https://secure-api:8000');
			const ws = httpsClient.connectWebSocket(false);

			expect(ws.url).toBe('wss://secure-api:8000/chat/ws/chat');
		});
	});

	describe('connectStatsStream()', () => {
		it('should create EventSource and call onMessage on data', async () => {
			const onMessage = vi.fn();
			const onError = vi.fn();

			const eventSource = client.connectStatsStream(onMessage, onError);

			expect(eventSource.url).toBe('http://test-api:8000/stats/stream');

			// Simulate receiving a message
			eventSource._receiveEvent({ videos: 100 });

			// Wait for event processing
			await new Promise((resolve) => setTimeout(resolve, 10));

			expect(onMessage).toHaveBeenCalledWith({ videos: 100 });
		});

		it('should handle parse errors gracefully', async () => {
			const onMessage = vi.fn();
			const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

			const eventSource = client.connectStatsStream(onMessage);

			// Simulate malformed data by calling onmessage directly with bad JSON
			eventSource.onmessage({ data: 'not-json' });

			await new Promise((resolve) => setTimeout(resolve, 10));

			expect(consoleSpy).toHaveBeenCalled();
			consoleSpy.mockRestore();
		});
	});

	// ============ Ingest ============

	describe('detectUrlType()', () => {
		it('should detect URL type', async () => {
			const mockResult = { url: 'https://youtube.com/watch?v=123', type: 'video' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.detectUrlType('https://youtube.com/watch?v=123');

			expect(fetch).toHaveBeenCalledWith(
				'http://test-api:8000/ingest/detect?url=https%3A%2F%2Fyoutube.com%2Fwatch%3Fv%3D123'
			);
			expect(result).toEqual(mockResult);
		});
	});

	describe('ingestUrl()', () => {
		it('should ingest URL with default channel limit', async () => {
			const mockResult = { type: 'video', status: 'success', message: 'Ingested' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.ingestUrl('https://youtube.com/watch?v=123');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/ingest', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ url: 'https://youtube.com/watch?v=123', channel_limit: 'all' })
			});
			expect(result).toEqual(mockResult);
		});

		it('should ingest URL with custom channel limit', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({})
			});

			await client.ingestUrl('https://youtube.com/@channel', 'month');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/ingest', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ url: 'https://youtube.com/@channel', channel_limit: 'month' })
			});
		});

		it('should throw error with detail from response', async () => {
			fetch.mockResolvedValueOnce({
				ok: false,
				statusText: 'Bad Request',
				json: () => Promise.resolve({ detail: 'Invalid URL format' })
			});

			await expect(client.ingestUrl('bad-url')).rejects.toThrow('Invalid URL format');
		});
	});

	// ============ Conversations ============

	describe('listConversations()', () => {
		it('should return conversations list', async () => {
			const mockConversations = { conversations: [{ id: '1', title: 'Test' }] };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockConversations)
			});

			const result = await client.listConversations();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/conversations');
			expect(result).toEqual(mockConversations);
		});
	});

	describe('createConversation()', () => {
		it('should create conversation with defaults', async () => {
			const mockConversation = { id: '123', title: 'New conversation' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockConversation)
			});

			const result = await client.createConversation();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/conversations', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ title: 'New conversation', model: '' })
			});
			expect(result).toEqual(mockConversation);
		});

		it('should create conversation with custom title and model', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({})
			});

			await client.createConversation('My Chat', 'gpt-4');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/conversations', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ title: 'My Chat', model: 'gpt-4' })
			});
		});
	});

	describe('getConversation()', () => {
		it('should get conversation by ID', async () => {
			const mockConversation = { id: '123', title: 'Test', messages: [] };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockConversation)
			});

			const result = await client.getConversation('123');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/conversations/123');
			expect(result).toEqual(mockConversation);
		});
	});

	describe('updateConversation()', () => {
		it('should update conversation', async () => {
			const mockUpdated = { id: '123', title: 'Updated Title' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockUpdated)
			});

			const result = await client.updateConversation('123', { title: 'Updated Title' });

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/conversations/123', {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ title: 'Updated Title' })
			});
			expect(result).toEqual(mockUpdated);
		});
	});

	describe('deleteConversation()', () => {
		it('should delete conversation', async () => {
			const mockResult = { status: 'deleted' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.deleteConversation('123');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/conversations/123', {
				method: 'DELETE'
			});
			expect(result).toEqual(mockResult);
		});
	});

	describe('searchConversations()', () => {
		it('should search conversations with encoded query', async () => {
			const mockResults = { conversations: [{ id: '1', title: 'Match' }] };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResults)
			});

			const result = await client.searchConversations('hello world');

			expect(fetch).toHaveBeenCalledWith(
				'http://test-api:8000/conversations/search?q=hello%20world'
			);
			expect(result).toEqual(mockResults);
		});
	});

	describe('generateTitle()', () => {
		it('should generate title from message', async () => {
			const mockResult = { title: 'Question about AI' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.generateTitle('What is artificial intelligence?');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/conversations/generate-title', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ message: 'What is artificial intelligence?' })
			});
			expect(result).toEqual(mockResult);
		});
	});

	// ============ Projects ============

	describe('listProjects()', () => {
		it('should return projects list', async () => {
			const mockProjects = { projects: [{ id: '1', name: 'Project 1' }] };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockProjects)
			});

			const result = await client.listProjects();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/projects');
			expect(result).toEqual(mockProjects);
		});
	});

	describe('createProject()', () => {
		it('should create project with defaults', async () => {
			const mockProject = { id: '123', name: 'New Project' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockProject)
			});

			const result = await client.createProject();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/projects', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name: 'New Project', description: '' })
			});
			expect(result).toEqual(mockProject);
		});

		it('should create project with custom name and description', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({})
			});

			await client.createProject('My Project', 'A description');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/projects', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name: 'My Project', description: 'A description' })
			});
		});
	});

	describe('getProject()', () => {
		it('should get project by ID', async () => {
			const mockProject = { id: '123', name: 'Test Project' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockProject)
			});

			const result = await client.getProject('123');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/projects/123');
			expect(result).toEqual(mockProject);
		});
	});

	describe('updateProject()', () => {
		it('should update project', async () => {
			const mockUpdated = { id: '123', name: 'Updated Name' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockUpdated)
			});

			const result = await client.updateProject('123', { name: 'Updated Name' });

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/projects/123', {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name: 'Updated Name' })
			});
			expect(result).toEqual(mockUpdated);
		});
	});

	describe('deleteProject()', () => {
		it('should delete project', async () => {
			const mockResult = { status: 'deleted' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.deleteProject('123');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/projects/123', {
				method: 'DELETE'
			});
			expect(result).toEqual(mockResult);
		});
	});

	describe('addConversationToProject()', () => {
		it('should add conversation to project', async () => {
			const mockResult = { status: 'added' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.addConversationToProject('proj-123', 'conv-456');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/projects/proj-123/conversations', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ conversation_id: 'conv-456' })
			});
			expect(result).toEqual(mockResult);
		});
	});

	describe('uploadProjectFile()', () => {
		it('should upload file to project', async () => {
			const mockResult = { id: 'file-123', name: 'test.pdf' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });
			const result = await client.uploadProjectFile('proj-123', mockFile);

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/projects/proj-123/files', {
				method: 'POST',
				body: expect.any(FormData)
			});
			expect(result).toEqual(mockResult);
		});
	});

	describe('deleteProjectFile()', () => {
		it('should delete file from project', async () => {
			const mockResult = { status: 'deleted' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.deleteProjectFile('proj-123', 'file-456');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/projects/proj-123/files/file-456', {
				method: 'DELETE'
			});
			expect(result).toEqual(mockResult);
		});
	});

	// ============ Artifacts ============

	describe('listArtifacts()', () => {
		it('should list all artifacts without filters', async () => {
			const mockArtifacts = { artifacts: [{ id: '1', title: 'Doc 1' }] };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockArtifacts)
			});

			const result = await client.listArtifacts();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/artifacts');
			expect(result).toEqual(mockArtifacts);
		});

		it('should list artifacts with conversation filter', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ artifacts: [] })
			});

			await client.listArtifacts('conv-123');

			expect(fetch).toHaveBeenCalledWith(
				'http://test-api:8000/artifacts?conversation_id=conv-123'
			);
		});

		it('should list artifacts with project filter', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ artifacts: [] })
			});

			await client.listArtifacts(null, 'proj-123');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/artifacts?project_id=proj-123');
		});

		it('should list artifacts with both filters', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ artifacts: [] })
			});

			await client.listArtifacts('conv-123', 'proj-456');

			expect(fetch).toHaveBeenCalledWith(
				'http://test-api:8000/artifacts?conversation_id=conv-123&project_id=proj-456'
			);
		});
	});

	describe('createArtifact()', () => {
		it('should create artifact with defaults', async () => {
			const mockArtifact = { id: '123', title: 'Untitled' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockArtifact)
			});

			const result = await client.createArtifact();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/artifacts', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					title: 'Untitled',
					content: '',
					artifact_type: 'document',
					language: null,
					conversation_id: null,
					project_id: null
				})
			});
			expect(result).toEqual(mockArtifact);
		});

		it('should create code artifact with all options', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({})
			});

			await client.createArtifact(
				'My Code',
				'console.log("hello")',
				'code',
				'javascript',
				'conv-123',
				'proj-456'
			);

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/artifacts', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					title: 'My Code',
					content: 'console.log("hello")',
					artifact_type: 'code',
					language: 'javascript',
					conversation_id: 'conv-123',
					project_id: 'proj-456'
				})
			});
		});
	});

	describe('getArtifact()', () => {
		it('should get artifact by ID', async () => {
			const mockArtifact = { id: '123', title: 'Test', content: 'Hello' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockArtifact)
			});

			const result = await client.getArtifact('123');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/artifacts/123');
			expect(result).toEqual(mockArtifact);
		});
	});

	describe('updateArtifact()', () => {
		it('should update artifact', async () => {
			const mockUpdated = { id: '123', title: 'Updated', content: 'New content' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockUpdated)
			});

			const result = await client.updateArtifact('123', { title: 'Updated', content: 'New content' });

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/artifacts/123', {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ title: 'Updated', content: 'New content' })
			});
			expect(result).toEqual(mockUpdated);
		});
	});

	describe('deleteArtifact()', () => {
		it('should delete artifact', async () => {
			const mockResult = { status: 'deleted' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.deleteArtifact('123');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/artifacts/123', {
				method: 'DELETE'
			});
			expect(result).toEqual(mockResult);
		});
	});

	// ============ Memory ============

	describe('listMemories()', () => {
		it('should list all memories', async () => {
			const mockMemories = { memories: [{ id: '1', content: 'Test' }], count: 1 };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockMemories)
			});

			const result = await client.listMemories();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/memory');
			expect(result).toEqual(mockMemories);
		});

		it('should filter by category', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ memories: [], count: 0 })
			});

			await client.listMemories('preference');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/memory?category=preference');
		});
	});

	describe('addMemory()', () => {
		it('should add memory with content and category', async () => {
			const mockMemory = { id: '123', content: 'User likes Python', category: 'preference' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockMemory)
			});

			const result = await client.addMemory('User likes Python', 'preference');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/memory', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ content: 'User likes Python', category: 'preference' })
			});
			expect(result).toEqual(mockMemory);
		});

		it('should use default category', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({})
			});

			await client.addMemory('Simple memory');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/memory', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ content: 'Simple memory', category: 'general' })
			});
		});
	});

	describe('getMemory()', () => {
		it('should get memory by ID', async () => {
			const mockMemory = { id: '123', content: 'Test memory' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockMemory)
			});

			const result = await client.getMemory('123');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/memory/123');
			expect(result).toEqual(mockMemory);
		});
	});

	describe('updateMemory()', () => {
		it('should update memory', async () => {
			const mockUpdated = { id: '123', content: 'Updated', category: 'fact' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockUpdated)
			});

			const result = await client.updateMemory('123', { content: 'Updated' });

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/memory/123', {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ content: 'Updated' })
			});
			expect(result).toEqual(mockUpdated);
		});
	});

	describe('deleteMemory()', () => {
		it('should delete memory', async () => {
			const mockResult = { success: true, message: 'Memory deleted' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.deleteMemory('123');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/memory/123', {
				method: 'DELETE'
			});
			expect(result).toEqual(mockResult);
		});
	});

	describe('clearAllMemories()', () => {
		it('should clear all memories', async () => {
			const mockResult = { deleted_count: 5, message: 'Deleted 5 memories' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.clearAllMemories();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/memory', {
				method: 'DELETE'
			});
			expect(result).toEqual(mockResult);
		});
	});

	describe('searchMemories()', () => {
		it('should search memories with encoded query', async () => {
			const mockResults = { memories: [{ id: '1', content: 'Python code' }], count: 1 };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResults)
			});

			const result = await client.searchMemories('python code');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/memory/search?q=python%20code');
			expect(result).toEqual(mockResults);
		});
	});

	// ============ Web Search ============

	describe('webSearch()', () => {
		it('should search with query and num', async () => {
			const mockResults = {
				results: [{ title: 'Test', url: 'https://test.com', snippet: 'Test' }],
				query: 'test query',
				source: 'duckduckgo'
			};
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResults)
			});

			const result = await client.webSearch('test query', 3);

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/search?q=test%20query&num=3');
			expect(result).toEqual(mockResults);
		});

		it('should use default num of 5', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ results: [], query: 'test', source: 'duckduckgo' })
			});

			await client.webSearch('test');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/search?q=test&num=5');
		});
	});

	describe('checkFreedium()', () => {
		it('should check if URL is Medium', async () => {
			const mockResult = {
				original_url: 'https://medium.com/test',
				freedium_url: 'https://freedium.cfd/https://medium.com/test',
				is_medium: true
			};
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.checkFreedium('https://medium.com/test');

			expect(fetch).toHaveBeenCalledWith(
				'http://test-api:8000/search/freedium?url=https%3A%2F%2Fmedium.com%2Ftest'
			);
			expect(result).toEqual(mockResult);
		});
	});

	describe('fetchViaFreedium()', () => {
		it('should fetch article via Freedium', async () => {
			const mockResult = {
				original_url: 'https://medium.com/test',
				freedium_url: 'https://freedium.cfd/https://medium.com/test',
				is_medium: true,
				content: '<html>Article</html>'
			};
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.fetchViaFreedium('https://medium.com/test');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/search/freedium', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ url: 'https://medium.com/test' })
			});
			expect(result).toEqual(mockResult);
		});
	});

	// ============ Code Sandbox ============

	describe('listSandboxLanguages()', () => {
		it('should list supported languages', async () => {
			const mockResult = {
				languages: [
					{ id: 'python', name: 'Python', extension: '.py' },
					{ id: 'javascript', name: 'JavaScript', extension: '.js' }
				]
			};
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.listSandboxLanguages();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/sandbox/languages');
			expect(result).toEqual(mockResult);
		});
	});

	describe('executeCode()', () => {
		it('should execute code with defaults', async () => {
			const mockResult = {
				execution_id: 'abc123',
				stdout: 'hello\n',
				stderr: '',
				exit_code: 0
			};
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.executeCode("print('hello')");

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/sandbox/execute', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ code: "print('hello')", language: 'python', timeout: 10, stdin: '' })
			});
			expect(result).toEqual(mockResult);
		});

		it('should execute with custom options', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({})
			});

			await client.executeCode('console.log("hi")', 'javascript', 5, 'input');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/sandbox/execute', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ code: 'console.log("hi")', language: 'javascript', timeout: 5, stdin: 'input' })
			});
		});
	});

	describe('validateCode()', () => {
		it('should validate code', async () => {
			const mockResult = { valid: true, error: null, language: 'python' };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.validateCode("print('safe')");

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/sandbox/validate', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ code: "print('safe')", language: 'python' })
			});
			expect(result).toEqual(mockResult);
		});
	});

	// ============ Image Generation ============

	describe('getImageOptions()', () => {
		it('should get supported sizes and styles', async () => {
			const mockOptions = {
				sizes: [
					{ id: 'large', name: 'Large', dimensions: '1024x1024' }
				],
				styles: [
					{ id: 'natural', name: 'Natural' }
				]
			};
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockOptions)
			});

			const result = await client.getImageOptions();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/imagegen/options');
			expect(result).toEqual(mockOptions);
		});
	});

	describe('generateImage()', () => {
		it('should generate image with all parameters', async () => {
			const mockResult = {
				images: [{ id: 'img1', url: 'https://example.com/img.png' }],
				prompt: 'a sunset',
				backend: 'dalle-3'
			};
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.generateImage('a sunset', 'wide', 'vivid', 2);

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/imagegen/generate', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ prompt: 'a sunset', size: 'wide', style: 'vivid', n: 2 })
			});
			expect(result).toEqual(mockResult);
		});

		it('should use default size, style, and n', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ images: [], prompt: 'test', backend: 'dalle-3' })
			});

			await client.generateImage('test');

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/imagegen/generate', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ prompt: 'test', size: 'large', style: 'natural', n: 1 })
			});
		});
	});

	describe('listImages()', () => {
		it('should list images with limit', async () => {
			const mockResult = { images: ['img1.png', 'img2.png'], count: 2 };
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve(mockResult)
			});

			const result = await client.listImages(10);

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/imagegen/images?limit=10');
			expect(result).toEqual(mockResult);
		});

		it('should use default limit of 50', async () => {
			fetch.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ images: [], count: 0 })
			});

			await client.listImages();

			expect(fetch).toHaveBeenCalledWith('http://test-api:8000/imagegen/images?limit=50');
		});
	});

	// ============ Default Export ============

	describe('default api instance', () => {
		it('should export a pre-configured API instance', () => {
			expect(api).toBeInstanceOf(MentatAPI);
		});
	});
});
