<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { marked } from 'marked';
  import DOMPurify from 'dompurify';
  import hljs from 'highlight.js';
  import 'highlight.js/styles/atom-one-dark.css';

  let messages = [];
  let input = '';
  let ws = null;
  let connected = false;
  let error = '';
  let currentResponse = '';
  let isStreaming = false;
  let useRAG = true; // Enable RAG by default
  let inputField; // Reference to textarea for focus management
  let selectedModel = 'moonshotai/kimi-k2:free'; // Default model
  let availableModels = [];
  let modelsLoading = true;
  let reconnectTimeout = null; // Track reconnection timeout to prevent stacking
  let markedConfigured = false; // Track if marked has been configured
  let tooltipVisible = false;
  let modelDropdownOpen = false; // Track model dropdown state
  let tooltipContent = { description: '', tags: [] };
  let tooltipPosition = { x: 0, y: 0 };
  let storageInitialized = false; // Track if we've restored from storage
  let messageQueue = []; // Queue for messages sent while streaming

  // Conversation state
  let conversations = [];
  let activeConversationId = null;
  let conversationsLoading = true;
  let searchQuery = '';
  let sidebarCollapsed = false;

  // Project state
  let projects = [];
  let activeProjectId = null;
  let activeProject = null;
  let projectsLoading = true;
  let projectDropdownOpen = false;

  // Canvas/Artifact state
  let canvasOpen = false;
  let canvasTab = 'editor'; // 'editor' or 'browser'
  let artifacts = [];
  let activeArtifact = null;
  let artifactContent = '';
  let artifactTitle = '';
  let artifactSaving = false;
  let artifactDirty = false;

  // Storage version - increment when message format changes
  const STORAGE_VERSION = 7; // Bumped for conversation support

  // Configure marked once (browser-only)
  function configureMarked() {
    if (!browser || markedConfigured) return;

    marked.setOptions({
      async: false,
      breaks: true, // Convert \n to <br>
      gfm: true, // GitHub Flavored Markdown
      highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
          try {
            return hljs.highlight(code, { language: lang }).value;
          } catch (e) {
            console.error('Highlight error:', e);
          }
        }
        return hljs.highlightAuto(code).value;
      }
    });

    markedConfigured = true;
  }

  // Render markdown with sanitization (browser-only)
  function renderMarkdown(text) {
    if (!browser) return text; // Return plain text during SSR

    configureMarked(); // Ensure marked is configured
    const html = marked.parse(text);
    return DOMPurify.sanitize(html);
  }

  // Process inline video citations
  function renderWithInlineCitations(content, sources) {
    if (!browser || !sources || sources.length === 0) {
      return renderMarkdown(content);
    }

    // Render markdown first
    let html = renderMarkdown(content);

    // Replace each video title with clickable link
    sources.forEach((source, index) => {
      const title = source.video_title;
      // Create a regex to find the exact title (case-insensitive, with optional quotes)
      const regex = new RegExp(`(['"]?)${title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\1`, 'gi');

      // Build URL with optional timestamp
      let videoUrl = source.url;
      if (source.start_time !== undefined && source.start_time !== null) {
        // Subtract 10 seconds to give context before the relevant part
        const timestamp = Math.max(0, Math.floor(source.start_time - 10));
        // Add timestamp to URL (YouTube uses &t=123s format)
        videoUrl = `${source.url}&t=${timestamp}s`;
      }

      // Replace with link that has data attributes for tooltip
      const replacement = `<a href="${videoUrl}"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-video-link"
        data-source-index="${index}"
        data-video-description="${(source.description || '').replace(/"/g, '&quot;')}"
        data-video-tags="${(source.tags || []).join(', ')}">${title}</a>`;

      html = html.replace(regex, replacement);
    });

    return html;
  }

  // Handle hover over inline video links
  function handleInlineLinkHover(event) {
    const target = event.target;

    // Check if hovering over an inline video link (check target and parents)
    let linkElement = null;
    if (target.classList && target.classList.contains('inline-video-link')) {
      linkElement = target;
    } else if (target.closest && target.closest('.inline-video-link')) {
      linkElement = target.closest('.inline-video-link');
    }

    if (linkElement) {
      const description = linkElement.getAttribute('data-video-description') || 'No description available';
      const tagsStr = linkElement.getAttribute('data-video-tags') || '';
      const tags = tagsStr ? tagsStr.split(', ') : [];

      showTooltip(event, description, tags);
    } else {
      hideTooltip();
    }
  }

  // Tooltip functions
  function showTooltip(event, description, tags) {
    tooltipContent = { description, tags };

    // Calculate initial position
    let x = event.clientX + 10;
    let y = event.clientY + 10;

    // Tooltip max-width is 400px, estimate height at ~100px
    const tooltipWidth = 400;
    const tooltipHeight = 100;

    // Check right edge - flip to left of cursor if too close to right edge
    if (x + tooltipWidth > window.innerWidth) {
      x = event.clientX - tooltipWidth - 10;
    }

    // Check bottom edge - flip above cursor if too close to bottom
    if (y + tooltipHeight > window.innerHeight) {
      y = event.clientY - tooltipHeight - 10;
    }

    // Ensure tooltip doesn't go off left edge
    if (x < 0) {
      x = 10;
    }

    // Ensure tooltip doesn't go off top edge
    if (y < 0) {
      y = 10;
    }

    tooltipPosition = { x, y };
    tooltipVisible = true;
  }

  function hideTooltip() {
    tooltipVisible = false;
  }

  function connectWebSocket() {
    // Set disconnected state immediately
    connected = false;

    ws = api.connectWebSocket(useRAG);

    // Connection timeout - if not connected within 5 seconds, consider it failed
    const connectionTimeout = setTimeout(() => {
      if (ws && ws.readyState !== WebSocket.OPEN) {
        console.error('WebSocket connection timeout');
        connected = false;
        error = 'Connection timeout. Is the backend running?';
        ws.close();
      }
    }, 5000);

    ws.onopen = () => {
      clearTimeout(connectionTimeout);
      connected = true;
      error = '';
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'token') {
          // Accumulate streaming response
          currentResponse += data.content;
          messages = messages; // Trigger reactivity
        } else if (data.type === 'done') {
          // Finish current message
          if (currentResponse) {
            messages = [...messages, {
              role: 'assistant',
              content: currentResponse.trim(),
              sources: data.sources || [],
              timestamp: new Date(),
              id: crypto.randomUUID()
            }];
            currentResponse = '';
          }
          isStreaming = false;
          processQueue(); // Process next queued message if any
        } else if (data.type === 'error') {
          error = data.content;
          isStreaming = false;
          currentResponse = '';
          processQueue(); // Process next queued message if any
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
        error = 'Failed to parse server response';
      }
    };

    ws.onerror = (e) => {
      clearTimeout(connectionTimeout);
      console.error('WebSocket error:', e);
      error = 'Connection error. Is the backend running?';
      connected = false;
    };

    ws.onclose = () => {
      clearTimeout(connectionTimeout);
      connected = false;
      console.log('WebSocket disconnected');
      // Auto-reconnect after 2 seconds
      if (reconnectTimeout) clearTimeout(reconnectTimeout); // Clear pending reconnect
      reconnectTimeout = setTimeout(() => {
        if (!connected) {
          console.log('Attempting to reconnect...');
          connectWebSocket();
        }
      }, 2000);
    };
  }

  async function send() {
    if (!input.trim() || !connected) return;

    const userMessage = input.trim();
    input = '';
    if (browser) sessionStorage.removeItem('mentat_draft'); // Clear saved draft after sending

    // If currently streaming, queue the message
    if (isStreaming) {
      messageQueue = [...messageQueue, userMessage];
      // Add user message to chat immediately (queued indicator could be added here)
      messages = [...messages, {
        role: 'user',
        content: userMessage,
        timestamp: new Date(),
        id: crypto.randomUUID()
      }];

      // Return focus to input field
      if (inputField) {
        inputField.focus();
      }
      return;
    }

    // Create conversation if this is the first message
    const isFirstMessage = !activeConversationId && messages.length === 0;
    if (!activeConversationId) {
      try {
        const conv = await api.createConversation('New conversation', selectedModel);
        activeConversationId = conv.id;
        // Add to conversation list
        conversations = [{ ...conv, message_count: 0 }, ...conversations];
      } catch (e) {
        console.error('Failed to create conversation:', e);
        // Continue without persistence
      }
    }

    // Add user message to chat
    const userMsg = {
      role: 'user',
      content: userMessage,
      timestamp: new Date(),
      id: crypto.randomUUID()
    };
    messages = [...messages, userMsg];

    // Send to backend with selected model, conversation ID, and project ID
    ws.send(JSON.stringify({
      message: userMessage,
      model: selectedModel,
      conversation_id: activeConversationId,
      project_id: activeProjectId
    }));
    isStreaming = true;
    currentResponse = '';
    error = '';

    // Generate title after first message (async, don't block)
    if (isFirstMessage && activeConversationId) {
      generateConversationTitle(userMessage, activeConversationId);
    }

    // Return focus to input field
    if (inputField) {
      inputField.focus();
    }
  }

  // Generate title for conversation asynchronously
  async function generateConversationTitle(message, conversationId) {
    try {
      const { title } = await api.generateTitle(message);
      // Update local conversation
      conversations = conversations.map(c =>
        c.id === conversationId ? { ...c, title } : c
      );
      // Update on backend
      await api.updateConversation(conversationId, { title });
    } catch (e) {
      console.error('Failed to generate title:', e);
    }
  }

  // Process next message in queue
  function processQueue() {
    if (messageQueue.length === 0 || !connected) return;

    const nextMessage = messageQueue[0];
    messageQueue = messageQueue.slice(1);

    // Send to backend with selected model and project ID
    ws.send(JSON.stringify({
      message: nextMessage,
      model: selectedModel,
      conversation_id: activeConversationId,
      project_id: activeProjectId
    }));
    isStreaming = true;
    currentResponse = '';
    error = '';
  }

  function retry(message) {
    if (!connected || isStreaming) return;

    // Populate input field with original message content and auto-send
    input = message.content;
    send();
  }

  function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  }

  function handleModelChange(event) {
    selectedModel = event.target.value;
    localStorage.setItem('mentat_model', selectedModel);
  }

  function selectModel(modelId) {
    selectedModel = modelId;
    localStorage.setItem('mentat_model', modelId);
    modelDropdownOpen = false;
  }

  function toggleModelDropdown() {
    if (!modelsLoading && !isStreaming) {
      modelDropdownOpen = !modelDropdownOpen;
    }
  }

  function getSelectedModelName() {
    const model = availableModels.find(m => m.id === selectedModel);
    return model ? model.name : selectedModel.split('/').pop();
  }

  function toggleRAG() {
    useRAG = !useRAG;
    if (ws) ws.close();
    connectWebSocket();
  }

  // Close dropdown when clicking outside
  function handleClickOutside(event) {
    if (modelDropdownOpen && !event.target.closest('.model-dropdown')) {
      modelDropdownOpen = false;
    }
  }

  function clearChat() {
    messages = [];
    currentResponse = '';
    sessionStorage.removeItem('mentat_messages');
    sessionStorage.removeItem('mentat_current_response');
  }

  async function generateRandomQuestion() {
    try {
      const response = await api.getRandomQuestion();
      input = response.question;

      // Focus the input field
      if (inputField) {
        inputField.focus();
      }
    } catch (error) {
      console.error('Failed to generate random question:', error);
      // Fallback to a default question
      input = "What are the best practices for prompt engineering?";

      if (inputField) {
        inputField.focus();
      }
    }
  }

  // ============ Project Functions ============

  async function loadProjects() {
    try {
      projectsLoading = true;
      const response = await api.listProjects();
      projects = response.projects || [];
    } catch (e) {
      console.error('Failed to load projects:', e);
      projects = [];
    } finally {
      projectsLoading = false;
    }
  }

  async function selectProject(id) {
    if (id === activeProjectId) return;

    activeProjectId = id;
    projectDropdownOpen = false;

    if (id) {
      try {
        activeProject = await api.getProject(id);
        // Filter conversations to show only this project's conversations
        // For now, reload all and filter client-side
        await loadConversations();
      } catch (e) {
        console.error('Failed to load project:', e);
        activeProject = null;
      }
    } else {
      activeProject = null;
      await loadConversations();
    }
  }

  async function createProject() {
    try {
      const project = await api.createProject('New Project');
      projects = [project, ...projects];
      await selectProject(project.id);
    } catch (e) {
      console.error('Failed to create project:', e);
      error = 'Failed to create project';
    }
  }

  async function deleteProject(id, event) {
    event.stopPropagation();
    if (!confirm('Delete this project and all its files?')) return;

    try {
      await api.deleteProject(id);
      projects = projects.filter(p => p.id !== id);

      if (activeProjectId === id) {
        await selectProject(null);
      }
    } catch (e) {
      console.error('Failed to delete project:', e);
      error = 'Failed to delete project';
    }
  }

  // Filter conversations by active project
  $: projectConversations = activeProject
    ? conversations.filter(c => activeProject.conversation_ids?.includes(c.id))
    : conversations;

  // ============ Canvas/Artifact Functions ============

  async function loadArtifacts() {
    try {
      const response = await api.listArtifacts(null, activeProjectId);
      artifacts = response.artifacts || [];
    } catch (e) {
      console.error('Failed to load artifacts:', e);
      artifacts = [];
    }
  }

  async function openCanvas(artifact = null) {
    canvasOpen = true;
    if (artifact) {
      try {
        activeArtifact = await api.getArtifact(artifact.id);
        artifactTitle = activeArtifact.title;
        artifactContent = activeArtifact.content;
        artifactDirty = false;
        canvasTab = 'editor';
      } catch (e) {
        console.error('Failed to load artifact:', e);
        error = 'Failed to load artifact';
      }
    }
  }

  function closeCanvas() {
    if (artifactDirty && !confirm('You have unsaved changes. Close anyway?')) {
      return;
    }
    canvasOpen = false;
    activeArtifact = null;
    artifactContent = '';
    artifactTitle = '';
    artifactDirty = false;
  }

  async function createArtifact() {
    try {
      const artifact = await api.createArtifact(
        'Untitled Document',
        '',
        'document',
        null,
        activeConversationId,
        activeProjectId
      );
      artifacts = [artifact, ...artifacts];
      await openCanvas(artifact);
    } catch (e) {
      console.error('Failed to create artifact:', e);
      error = 'Failed to create artifact';
    }
  }

  async function saveArtifact() {
    if (!activeArtifact || artifactSaving) return;

    artifactSaving = true;
    try {
      await api.updateArtifact(activeArtifact.id, {
        title: artifactTitle,
        content: artifactContent
      });
      artifactDirty = false;
      // Update in list
      artifacts = artifacts.map(a =>
        a.id === activeArtifact.id
          ? { ...a, title: artifactTitle, preview: artifactContent.slice(0, 200) }
          : a
      );
    } catch (e) {
      console.error('Failed to save artifact:', e);
      error = 'Failed to save artifact';
    } finally {
      artifactSaving = false;
    }
  }

  async function deleteArtifact(id, event) {
    if (event) event.stopPropagation();
    if (!confirm('Delete this artifact?')) return;

    try {
      await api.deleteArtifact(id);
      artifacts = artifacts.filter(a => a.id !== id);
      if (activeArtifact?.id === id) {
        activeArtifact = null;
        artifactContent = '';
        artifactTitle = '';
      }
    } catch (e) {
      console.error('Failed to delete artifact:', e);
      error = 'Failed to delete artifact';
    }
  }

  function handleArtifactContentChange() {
    artifactDirty = true;
  }

  // Auto-save artifact with debounce
  let autoSaveTimeout = null;
  $: if (artifactDirty && activeArtifact) {
    if (autoSaveTimeout) clearTimeout(autoSaveTimeout);
    autoSaveTimeout = setTimeout(() => {
      saveArtifact();
    }, 2000);
  }

  // ============ Conversation Functions ============

  async function loadConversations() {
    try {
      conversationsLoading = true;
      const response = await api.listConversations();
      conversations = response.conversations || [];
    } catch (e) {
      console.error('Failed to load conversations:', e);
      conversations = [];
    } finally {
      conversationsLoading = false;
    }
  }

  async function selectConversation(id) {
    if (id === activeConversationId) return;

    try {
      const conversation = await api.getConversation(id);
      activeConversationId = id;
      messages = conversation.messages.map(msg => ({
        ...msg,
        timestamp: new Date(msg.timestamp)
      }));
      currentResponse = '';

      // Update model if conversation has one
      if (conversation.model) {
        selectedModel = conversation.model;
      }
    } catch (e) {
      console.error('Failed to load conversation:', e);
      error = 'Failed to load conversation';
    }
  }

  async function startNewChat() {
    activeConversationId = null;
    messages = [];
    currentResponse = '';
    sessionStorage.removeItem('mentat_messages');
    sessionStorage.removeItem('mentat_current_response');

    if (inputField) {
      inputField.focus();
    }
  }

  async function deleteConversation(id, event) {
    event.stopPropagation();
    if (!confirm('Delete this conversation?')) return;

    try {
      await api.deleteConversation(id);
      conversations = conversations.filter(c => c.id !== id);

      if (activeConversationId === id) {
        startNewChat();
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e);
      error = 'Failed to delete conversation';
    }
  }

  // Rename conversation
  let renamingConversationId = null;
  let renameInput = '';

  function startRename(id, currentTitle, event) {
    event.stopPropagation();
    renamingConversationId = id;
    renameInput = currentTitle;
  }

  async function saveRename(id) {
    if (!renameInput.trim()) {
      renamingConversationId = null;
      return;
    }

    try {
      await api.updateConversation(id, { title: renameInput.trim() });
      conversations = conversations.map(c =>
        c.id === id ? { ...c, title: renameInput.trim() } : c
      );
    } catch (e) {
      console.error('Failed to rename conversation:', e);
      error = 'Failed to rename conversation';
    } finally {
      renamingConversationId = null;
    }
  }

  function handleRenameKeydown(event, id) {
    if (event.key === 'Enter') {
      event.preventDefault();
      saveRename(id);
    } else if (event.key === 'Escape') {
      renamingConversationId = null;
    }
  }

  function formatConversationDate(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  }

  // Search with debounce
  let searchResults = null;
  let searchTimeout = null;
  let isSearching = false;

  async function handleSearchInput(query) {
    if (searchTimeout) clearTimeout(searchTimeout);

    if (!query || query.length < 2) {
      searchResults = null;
      return;
    }

    // Debounce search requests
    searchTimeout = setTimeout(async () => {
      isSearching = true;
      try {
        const response = await api.searchConversations(query);
        searchResults = response.conversations || [];
      } catch (e) {
        console.error('Search failed:', e);
        searchResults = null;
      } finally {
        isSearching = false;
      }
    }, 300);
  }

  // Watch searchQuery changes
  $: handleSearchInput(searchQuery);

  // Use search results when available, otherwise show all conversations
  $: filteredConversations = searchResults !== null ? searchResults : projectConversations;

  onMount(async () => {
    // Load saved model preference from localStorage
    const savedModel = localStorage.getItem('mentat_model');
    if (savedModel) {
      selectedModel = savedModel;
    }

    // Fetch available models
    try {
      const response = await api.fetchModels();
      availableModels = response.models || [];
      modelsLoading = false;

      // Validate saved model still exists
      if (savedModel && !availableModels.some(m => m.id === savedModel)) {
        selectedModel = 'moonshotai/kimi-k2:free';
        localStorage.setItem('mentat_model', selectedModel);
      }
    } catch (e) {
      console.error('Failed to fetch models:', e);
      modelsLoading = false;
      // Use fallback model
      availableModels = [
        {
          id: 'moonshotai/kimi-k2:free',
          name: 'Moonshot Kimi K2 (Free)',
          is_free: true
        }
      ];
    }

    // Restore saved draft, messages, and current response from sessionStorage (only in browser)
    if (browser) {
      // Check storage version - clear old data if version mismatch
      const savedVersion = sessionStorage.getItem('mentat_storage_version');
      if (savedVersion !== String(STORAGE_VERSION)) {
        console.log('Storage version mismatch, clearing old messages');
        sessionStorage.removeItem('mentat_messages');
        sessionStorage.removeItem('mentat_current_response');
        sessionStorage.setItem('mentat_storage_version', String(STORAGE_VERSION));
      }

      const savedDraft = sessionStorage.getItem('mentat_draft');
      if (savedDraft) {
        input = savedDraft;
      }

      // Restore saved messages
      const savedMessages = sessionStorage.getItem('mentat_messages');
      if (savedMessages) {
        try {
          const parsed = JSON.parse(savedMessages);
          // Restore Date objects from timestamps
          messages = parsed.map(msg => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }));
        } catch (e) {
          console.error('Failed to restore messages:', e);
          messages = [];
        }
      }

      // Restore current streaming response if any
      const savedResponse = sessionStorage.getItem('mentat_current_response');
      if (savedResponse) {
        currentResponse = savedResponse;
      }

      // Mark storage as initialized to enable reactive saving
      storageInitialized = true;
    }

    connectWebSocket();

    // Load projects, conversations, and artifacts
    loadProjects();
    loadConversations();
    loadArtifacts();

    // Focus input field after a short delay to ensure it's rendered
    setTimeout(() => {
      if (inputField) {
        inputField.focus();
      }
    }, 100);
  });

  onDestroy(() => {
    if (ws) {
      ws.close();
    }
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout); // Prevent orphaned timeouts
    }
  });

  // Auto-scroll to bottom after messages update
  async function scrollToBottom() {
    await tick(); // Wait for DOM to update
    const messagesWrapper = document.querySelector('.messages-wrapper');
    if (messagesWrapper) {
      messagesWrapper.scrollTop = messagesWrapper.scrollHeight;
    }
  }

  $: if (messages.length > 0 || currentResponse) {
    scrollToBottom();
  }

  // Save messages to sessionStorage whenever they change (only in browser after initialization)
  $: if (browser && storageInitialized && messages !== undefined) {
    if (messages.length > 0) {
      sessionStorage.setItem('mentat_messages', JSON.stringify(messages));
    } else {
      sessionStorage.removeItem('mentat_messages');
    }
  }

  // Save current streaming response to sessionStorage (only in browser after initialization)
  $: if (browser && storageInitialized && currentResponse !== undefined) {
    if (currentResponse.trim()) {
      sessionStorage.setItem('mentat_current_response', currentResponse);
    } else {
      sessionStorage.removeItem('mentat_current_response');
    }
  }

  // Save input draft to sessionStorage whenever it changes (only in browser after initialization)
  $: if (browser && storageInitialized && input !== undefined) {
    if (input.trim()) {
      sessionStorage.setItem('mentat_draft', input);
    } else {
      sessionStorage.removeItem('mentat_draft');
    }
  }
</script>

<svelte:window on:click={handleClickOutside} />

<main>
  <header>
    <a href="/" class="logo">Mentat</a>
    <div class="controls">
      <button
        class="canvas-toggle-btn"
        class:active={canvasOpen}
        on:click={() => canvasOpen = !canvasOpen}
        title="Toggle Canvas"
      >
        Canvas
      </button>
      <div class="status">
        <span class="indicator" class:connected></span>
        {connected ? 'Connected' : 'Disconnected'}
      </div>
    </div>
  </header>

  <div class="app-layout">
    <!-- Sidebar -->
    <aside class="sidebar" class:collapsed={sidebarCollapsed}>
      <div class="sidebar-header">
        <button class="new-chat-btn" on:click={startNewChat}>
          + New Chat
        </button>
        <button class="collapse-btn" on:click={() => sidebarCollapsed = !sidebarCollapsed}>
          {sidebarCollapsed ? '→' : '←'}
        </button>
      </div>

      {#if !sidebarCollapsed}
        <!-- Project Selector -->
        <div class="project-selector">
          <button
            class="project-dropdown-btn"
            on:click={() => projectDropdownOpen = !projectDropdownOpen}
          >
            <span class="project-icon">📁</span>
            <span class="project-name">{activeProject?.name || 'All Chats'}</span>
            <span class="dropdown-arrow">{projectDropdownOpen ? '▲' : '▼'}</span>
          </button>

          {#if projectDropdownOpen}
            <div class="project-dropdown-menu">
              <button
                class="project-option"
                class:active={!activeProjectId}
                on:click={() => selectProject(null)}
              >
                All Chats
              </button>

              {#if projects.length > 0}
                <div class="project-divider"></div>
                {#each projects as project}
                  <div class="project-option-row">
                    <button
                      class="project-option"
                      class:active={activeProjectId === project.id}
                      on:click={() => selectProject(project.id)}
                    >
                      {project.name}
                    </button>
                    <button
                      class="project-delete-btn"
                      on:click={(e) => deleteProject(project.id, e)}
                      title="Delete project"
                    >×</button>
                  </div>
                {/each}
              {/if}

              <div class="project-divider"></div>
              <button class="project-option create-project" on:click={createProject}>
                + New Project
              </button>
            </div>
          {/if}
        </div>

        <div class="sidebar-search">
          <input
            type="text"
            placeholder="Search conversations..."
            bind:value={searchQuery}
          />
        </div>

        <div class="conversations-list">
          {#if conversationsLoading || isSearching}
            <div class="conversations-loading">{isSearching ? 'Searching...' : 'Loading...'}</div>
          {:else if filteredConversations.length === 0}
            <div class="no-conversations">
              {searchQuery ? 'No matches found' : 'No conversations yet'}
            </div>
          {:else}
            {#each filteredConversations as conv}
              <div
                class="conversation-item"
                class:active={conv.id === activeConversationId}
                on:click={() => selectConversation(conv.id)}
              >
                {#if renamingConversationId === conv.id}
                  <input
                    type="text"
                    class="rename-input"
                    bind:value={renameInput}
                    on:keydown={(e) => handleRenameKeydown(e, conv.id)}
                    on:blur={() => saveRename(conv.id)}
                    on:click|stopPropagation
                    autofocus
                  />
                {:else}
                  <div class="conversation-title">{conv.title}</div>
                {/if}
                <div class="conversation-meta">
                  <span class="conversation-date">{formatConversationDate(conv.updated_at)}</span>
                  <div class="conversation-actions">
                    <button
                      class="rename-btn"
                      on:click={(e) => startRename(conv.id, conv.title, e)}
                      title="Rename conversation"
                    >✎</button>
                    <button
                      class="delete-btn"
                      on:click={(e) => deleteConversation(conv.id, e)}
                      title="Delete conversation"
                    >×</button>
                  </div>
                </div>
              </div>
            {/each}
          {/if}
        </div>
      {/if}
    </aside>

    <!-- Chat Area -->
    <div class="chat-area">
      {#if error}
        <div class="error">
          <strong>Error:</strong> {error}
          <button on:click={() => error = ''}>✕</button>
        </div>
      {/if}

      <!-- ChatGPT-style model selector -->
      <div class="model-dropdown" class:open={modelDropdownOpen}>
        <button
          class="model-dropdown-trigger"
          on:click={toggleModelDropdown}
          disabled={modelsLoading || isStreaming}
        >
          <span class="model-name">{getSelectedModelName()}</span>
          <span class="dropdown-arrow">▼</span>
        </button>

        {#if modelDropdownOpen}
          <div class="model-dropdown-menu">
            {#if availableModels.some(m => m.is_local)}
              <div class="model-group">
                <div class="model-group-label">Ollama</div>
                {#each availableModels.filter(m => m.is_local) as model}
                  <button
                    class="model-option"
                    class:selected={model.id === selectedModel}
                    on:click={() => selectModel(model.id)}
                  >
                    {model.name}
                  </button>
                {/each}
              </div>
            {/if}

            {#if availableModels.some(m => m.is_free && !m.is_local)}
              <div class="model-group">
                <div class="model-group-label">Free Models</div>
                {#each availableModels.filter(m => m.is_free && !m.is_local) as model}
                  <button
                    class="model-option"
                    class:selected={model.id === selectedModel}
                    on:click={() => selectModel(model.id)}
                  >
                    {model.name}
                  </button>
                {/each}
              </div>
            {/if}

            {#if availableModels.some(m => !m.is_free && !m.is_local)}
              <div class="model-group">
                <div class="model-group-label">Paid Models</div>
                {#each availableModels.filter(m => !m.is_free && !m.is_local) as model}
                  <button
                    class="model-option"
                    class:selected={model.id === selectedModel}
                    on:click={() => selectModel(model.id)}
                  >
                    {model.name}
                  </button>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
      </div>

      <div class="messages-wrapper">
        <div class="messages">
          {#each messages as msg}
            <div class="message-wrapper message-wrapper-{msg.role}">
              <div class="message message-{msg.role}">
                <div
                  class="message-content"
                  on:mousemove={handleInlineLinkHover}
                  on:mouseleave={hideTooltip}
                >
                  {@html renderWithInlineCitations(msg.content, msg.sources)}
                </div>
              </div>
              <div class="message-metadata">
                <span class="timestamp">{msg.timestamp.toLocaleTimeString()}</span>
                {#if msg.role === 'user'}
                  <button
                    class="retry-btn"
                    on:click={() => retry(msg)}
                    disabled={!connected}
                    title="Retry this message"
                  >
                    ↻
                  </button>
                {/if}
              </div>
            </div>
          {/each}

          {#if isStreaming}
            <div class="message-wrapper message-wrapper-assistant">
              <div class="message message-assistant streaming">
                {#if currentResponse}
                  <div class="message-content">{@html renderMarkdown(currentResponse)}</div>
                {:else}
                  <div class="message-content processing">
                    <span class="processing-dots">●●●</span>
                  </div>
                {/if}
              </div>
              <div class="message-metadata">
                <span class="typing-indicator">{currentResponse ? 'typing...' : 'processing...'}</span>
              </div>
            </div>
          {/if}

          {#if messages.length === 0 && !currentResponse}
            <div class="welcome">
              <h2>Welcome to Mentat</h2>
              <p>Ask me anything about your cached videos.</p>
              <p class="hint">Type a message below and press Enter to start.</p>
            </div>
          {/if}
        </div>
      </div>

      <div class="input-area">
        <div class="input-content">
          <button
            class="random-question-btn"
            on:click={generateRandomQuestion}
            disabled={!connected}
            title="Generate random question"
          >
            🎲
          </button>
          <textarea
            bind:this={inputField}
            bind:value={input}
            on:keypress={handleKeyPress}
            disabled={!connected}
            placeholder={connected ? "Ask Mentat..." : "Connecting..."}
            rows="2"
          ></textarea>
          <button
            on:click={send}
            disabled={!connected || !input.trim()}
          >
            Send
          </button>
          <button
            class="rag-btn"
            class:active={useRAG}
            on:click={toggleRAG}
            title={useRAG ? 'RAG Mode ON - Click to disable' : 'RAG Mode OFF - Click to enable'}
          >
            RAG
          </button>
          <button class="clear-btn" on:click={clearChat} title="Clear chat history">
            Clear
          </button>
        </div>
      </div>
    </div><!-- /.chat-area -->

    <!-- Canvas Sidebar -->
    {#if canvasOpen}
      <aside class="canvas-sidebar">
        <div class="canvas-header">
          <div class="canvas-tabs">
            <button
              class="canvas-tab"
              class:active={canvasTab === 'editor'}
              on:click={() => canvasTab = 'editor'}
            >
              Editor
            </button>
            <button
              class="canvas-tab"
              class:active={canvasTab === 'browser'}
              on:click={() => { canvasTab = 'browser'; loadArtifacts(); }}
            >
              Browse
            </button>
          </div>
          <button class="canvas-close-btn" on:click={closeCanvas}>×</button>
        </div>

        {#if canvasTab === 'editor'}
          <div class="canvas-editor">
            {#if activeArtifact}
              <div class="canvas-title-row">
                <input
                  type="text"
                  class="canvas-title-input"
                  bind:value={artifactTitle}
                  on:input={handleArtifactContentChange}
                  placeholder="Document title..."
                />
                <span class="save-status">
                  {#if artifactSaving}
                    Saving...
                  {:else if artifactDirty}
                    Unsaved
                  {:else}
                    Saved
                  {/if}
                </span>
              </div>
              <textarea
                class="canvas-content"
                bind:value={artifactContent}
                on:input={handleArtifactContentChange}
                placeholder="Start writing..."
              ></textarea>
              <div class="canvas-actions">
                <button
                  class="save-btn"
                  on:click={saveArtifact}
                  disabled={artifactSaving || !artifactDirty}
                >
                  Save
                </button>
              </div>
            {:else}
              <div class="canvas-empty">
                <p>No document open</p>
                <button class="create-artifact-btn" on:click={createArtifact}>
                  + New Document
                </button>
              </div>
            {/if}
          </div>
        {:else}
          <div class="canvas-browser">
            <div class="browser-header">
              <button class="create-artifact-btn" on:click={createArtifact}>
                + New Document
              </button>
            </div>
            <div class="artifacts-list">
              {#if artifacts.length === 0}
                <div class="no-artifacts">No documents yet</div>
              {:else}
                {#each artifacts as artifact}
                  <div
                    class="artifact-item"
                    class:active={activeArtifact?.id === artifact.id}
                    on:click={() => openCanvas(artifact)}
                  >
                    <div class="artifact-title">{artifact.title}</div>
                    <div class="artifact-preview">{artifact.preview || 'Empty document'}</div>
                    <div class="artifact-meta">
                      <span class="artifact-date">
                        {new Date(artifact.updated_at).toLocaleDateString()}
                      </span>
                      <button
                        class="artifact-delete-btn"
                        on:click={(e) => deleteArtifact(artifact.id, e)}
                        title="Delete"
                      >×</button>
                    </div>
                  </div>
                {/each}
              {/if}
            </div>
          </div>
        {/if}
      </aside>
    {/if}
  </div><!-- /.app-layout -->
</main>

<!-- Custom Tooltip -->
{#if tooltipVisible}
  <div
    class="custom-tooltip"
    style="left: {tooltipPosition.x}px; top: {tooltipPosition.y}px;"
  >
    <div class="tooltip-description">{tooltipContent.description}</div>
    {#if tooltipContent.tags && tooltipContent.tags.length > 0}
      <div class="tooltip-tags">
        {tooltipContent.tags.join(', ')}
      </div>
    {/if}
  </div>
{/if}

<style>
  main {
    width: 100%;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    background: #111;
    border-bottom: 1px solid #222;
    width: 100%;
  }

  .logo {
    font-size: 1.5rem;
    font-weight: 700;
    color: #3b82f6;
    text-decoration: none;
  }

  .logo:hover {
    color: #60a5fa;
  }

  .controls {
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }

  /* App layout with sidebar */
  .app-layout {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  /* Sidebar */
  .sidebar {
    width: 260px;
    background: #0a0a0a;
    border-right: 1px solid #222;
    display: flex;
    flex-direction: column;
    transition: width 0.2s ease;
  }

  .sidebar.collapsed {
    width: 60px;
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem;
    border-bottom: 1px solid #222;
  }

  .new-chat-btn {
    flex: 1;
    padding: 0.625rem 1rem;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 0.5rem;
    color: #e5e5e5;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .sidebar.collapsed .new-chat-btn {
    display: none;
  }

  .new-chat-btn:hover {
    background: #2a2a2a;
    border-color: #444;
  }

  .collapse-btn {
    width: 36px;
    height: 36px;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: 0.375rem;
    color: #888;
    font-size: 0.875rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  }

  .collapse-btn:hover {
    background: #1a1a1a;
    color: #e5e5e5;
  }

  /* Project Selector */
  .project-selector {
    position: relative;
    padding: 0.75rem;
    border-bottom: 1px solid #222;
  }

  .project-dropdown-btn {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 0.5rem;
    color: #e5e5e5;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .project-dropdown-btn:hover {
    background: #2a2a2a;
    border-color: #444;
  }

  .project-icon {
    font-size: 1rem;
  }

  .project-name {
    flex: 1;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .project-dropdown-menu {
    position: absolute;
    top: 100%;
    left: 0.75rem;
    right: 0.75rem;
    z-index: 100;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 0.5rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    max-height: 300px;
    overflow-y: auto;
  }

  .project-option {
    width: 100%;
    padding: 0.625rem 0.75rem;
    background: transparent;
    border: none;
    color: #e5e5e5;
    font-size: 0.8125rem;
    text-align: left;
    cursor: pointer;
    transition: background 0.15s;
  }

  .project-option:hover {
    background: #2a2a2a;
  }

  .project-option.active {
    background: rgba(59, 130, 246, 0.15);
    color: #3b82f6;
  }

  .project-option.create-project {
    color: #3b82f6;
  }

  .project-option-row {
    display: flex;
    align-items: center;
  }

  .project-option-row .project-option {
    flex: 1;
  }

  .project-delete-btn {
    width: 24px;
    height: 24px;
    margin-right: 0.5rem;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: 0.25rem;
    color: #666;
    font-size: 1rem;
    cursor: pointer;
    opacity: 0;
    transition: all 0.15s;
  }

  .project-option-row:hover .project-delete-btn {
    opacity: 1;
  }

  .project-delete-btn:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }

  .project-divider {
    height: 1px;
    background: #333;
    margin: 0.25rem 0;
  }

  .sidebar-search {
    padding: 0.75rem;
    border-bottom: 1px solid #222;
  }

  .sidebar-search input {
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 0.375rem;
    color: #e5e5e5;
    font-size: 0.8125rem;
  }

  .sidebar-search input:focus {
    outline: none;
    border-color: #3b82f6;
  }

  .sidebar-search input::placeholder {
    color: #666;
  }

  .conversations-list {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem;
  }

  .conversations-loading,
  .no-conversations {
    padding: 1rem;
    text-align: center;
    color: #666;
    font-size: 0.8125rem;
  }

  .conversation-item {
    padding: 0.75rem;
    border-radius: 0.5rem;
    cursor: pointer;
    transition: background 0.15s;
    margin-bottom: 0.25rem;
  }

  .conversation-item:hover {
    background: #1a1a1a;
  }

  .conversation-item.active {
    background: rgba(59, 130, 246, 0.15);
  }

  .conversation-title {
    font-size: 0.875rem;
    color: #e5e5e5;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 0.25rem;
  }

  .conversation-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .conversation-date {
    font-size: 0.75rem;
    color: #666;
  }

  .conversation-actions {
    display: flex;
    gap: 0.25rem;
    opacity: 0;
    transition: opacity 0.15s;
  }

  .conversation-item:hover .conversation-actions {
    opacity: 1;
  }

  .rename-btn,
  .delete-btn {
    width: 20px;
    height: 20px;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: 0.25rem;
    color: #888;
    font-size: 0.875rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
  }

  .rename-btn:hover {
    background: rgba(59, 130, 246, 0.2);
    color: #3b82f6;
  }

  .delete-btn:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }

  .rename-input {
    width: 100%;
    padding: 0.25rem 0.5rem;
    background: #1a1a1a;
    border: 1px solid #3b82f6;
    border-radius: 0.25rem;
    color: #e5e5e5;
    font-size: 0.875rem;
    margin-bottom: 0.25rem;
  }

  .rename-input:focus {
    outline: none;
  }

  /* Chat area */
  .chat-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* ChatGPT-style model dropdown */
  .model-dropdown {
    position: relative;
    padding: 0.5rem 2rem;
    background: #0a0a0a;
  }

  .model-dropdown-trigger {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: transparent;
    border: none;
    color: #e5e5e5;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .model-dropdown-trigger:hover:not(:disabled) {
    background: #1a1a1a;
    border-radius: 0.375rem;
  }

  .model-dropdown-trigger:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .model-name {
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dropdown-arrow {
    font-size: 0.625rem;
    color: #888;
    transition: transform 0.2s;
  }

  .model-dropdown.open .dropdown-arrow {
    transform: rotate(180deg);
  }

  .model-dropdown-menu {
    position: absolute;
    top: 100%;
    left: 2rem;
    z-index: 100;
    min-width: 280px;
    max-height: 400px;
    overflow-y: auto;
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 0.5rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    padding: 0.5rem 0;

    /* Dark mode scrollbar */
    scrollbar-width: thin;
    scrollbar-color: #3a3a3a #1a1a1a;
  }

  .model-dropdown-menu::-webkit-scrollbar {
    width: 8px;
  }

  .model-dropdown-menu::-webkit-scrollbar-track {
    background: #1a1a1a;
    border-radius: 4px;
  }

  .model-dropdown-menu::-webkit-scrollbar-thumb {
    background: #3a3a3a;
    border-radius: 4px;
  }

  .model-dropdown-menu::-webkit-scrollbar-thumb:hover {
    background: #4a4a4a;
  }

  .model-group {
    padding: 0.25rem 0;
  }

  .model-group:not(:last-child) {
    border-bottom: 1px solid #2a2a2a;
    margin-bottom: 0.25rem;
    padding-bottom: 0.5rem;
  }

  .model-group-label {
    padding: 0.375rem 1rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: #3b82f6;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .model-option {
    display: block;
    width: 100%;
    padding: 0.5rem 1rem;
    background: transparent;
    border: none;
    color: #e5e5e5;
    font-size: 0.875rem;
    text-align: left;
    cursor: pointer;
    transition: background 0.15s;
  }

  .model-option:hover {
    background: #2a2a2a;
  }

  .model-option.selected {
    background: rgba(59, 130, 246, 0.2);
    color: #3b82f6;
  }

  /* Secondary button base style (RAG, Clear, Random) */
  .btn-secondary {
    padding: 0.75rem 1.25rem;
    background: #2a2a2a;
    border: none;
    border-radius: 0.5rem;
    color: #a0a0a0;
    font-weight: 600;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn-secondary:hover:not(:disabled) {
    background: #3a3a3a;
    color: #e5e5e5;
  }

  .btn-secondary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* RAG toggle button */
  .rag-btn {
    padding: 0.75rem 1.25rem;
    background: #2a2a2a;
    border: none;
    border-radius: 0.5rem;
    color: #a0a0a0;
    font-weight: 600;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .rag-btn:hover:not(:disabled) {
    background: #3a3a3a;
    color: #e5e5e5;
  }

  .rag-btn.active {
    background: #3b82f6;
    color: white;
  }

  .rag-btn.active:hover:not(:disabled) {
    background: #2563eb;
  }

  /* Clear button */
  .clear-btn {
    padding: 0.75rem 1.25rem;
    background: #2a2a2a;
    border: none;
    border-radius: 0.5rem;
    color: #a0a0a0;
    font-weight: 600;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .clear-btn:hover:not(:disabled) {
    background: #3a3a3a;
    color: #e5e5e5;
  }

  .status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: #888;
  }

  .indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #ef4444;
  }

  .indicator.connected {
    background: #10b981;
  }

  .error {
    margin: 1rem 2rem 0;
    padding: 1rem;
    background: #7f1d1d;
    border: 1px solid #dc2626;
    border-radius: 0.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .error button {
    background: none;
    border: none;
    color: #fff;
    cursor: pointer;
    font-size: 1.25rem;
    padding: 0;
    width: 24px;
    height: 24px;
  }

  .messages-wrapper {
    flex: 1;
    overflow-y: auto;
    width: 100%;
  }

  .messages {
    padding: 2rem;
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    width: 100%;
    max-width: 900px;
    margin: 0 auto;
    box-sizing: border-box;
    min-height: 100%;
  }

  .welcome {
    margin: auto;
    text-align: center;
    color: #888;
  }

  .welcome h2 {
    color: #3b82f6;
    margin-bottom: 0.5rem;
  }

  .welcome p {
    margin: 0.5rem 0;
  }

  .hint {
    font-size: 0.875rem;
    font-style: italic;
  }

  .message {
    padding: 0.1rem 1rem;
    border-radius: 0.75rem;
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    width: 100%;
  }

  .message-user {
    background: #1e3a8a;
    border-color: #1e40af;
  }

  .message-assistant {
    background: #1a1a1a;
  }

  .message-assistant.streaming {
    border-color: #3b82f6;
  }

  /* Message wrapper contains both message box and metadata */
  .message-wrapper {
    display: flex;
    flex-direction: column;
    max-width: 75%;
  }

  .message-wrapper-user {
    align-self: flex-end;
  }

  .message-wrapper-assistant {
    align-self: flex-start;
  }

  /* Metadata row (timestamp + retry button) */
  .message-metadata {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 0.025rem;
    padding: 0 0.5rem;
    font-size: 0.75rem;
    min-height: 1.5rem;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .message-wrapper:hover .message-metadata {
    opacity: 1;
  }

  .timestamp {
    color: #666;
    font-size: 0.75rem;
  }

  .typing-indicator {
    color: #3b82f6;
    font-size: 0.75rem;
    font-style: italic;
  }

  .processing {
    min-height: 1.5em;
  }

  .processing-dots {
    color: #6b7280;
    font-size: 1.25rem;
    letter-spacing: 0.25em;
    animation: pulse 1.5s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 1; }
  }

  .retry-btn {
    background: none;
    border: none;
    color: #666;
    cursor: pointer;
    font-size: 1rem;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.2s;
  }

  .retry-btn:hover:not(:disabled) {
    color: #3b82f6;
    background: rgba(59, 130, 246, 0.1);
  }

  .retry-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .message-content {
    white-space: normal;
    word-wrap: break-word;
    line-height: 1.6;
  }

  /* Markdown styling */
  .message-content p {
    margin: 0.75rem 0;
  }

  .message-content p:first-child {
    margin-top: 0;
  }

  .message-content p:last-child {
    margin-bottom: 0;
  }

  .message-content code {
    background: rgba(0, 0, 0, 0.3);
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 0.875em;
  }

  .message-content pre {
    background: #0a0a0a;
    border: 1px solid #2a2a2a;
    border-radius: 0.5rem;
    padding: 1rem;
    overflow-x: auto;
    margin: 0.75rem 0;
  }

  .message-content pre code {
    background: none;
    padding: 0;
    font-size: 0.875rem;
    line-height: 1.5;
  }

  .message-content a {
    color: #3b82f6;
    text-decoration: none;
  }

  .message-content a:hover {
    text-decoration: underline;
  }

  .message-content ul,
  .message-content ol {
    margin: 0.75rem 0;
    padding-left: 1.5rem;
  }

  .message-content li {
    margin: 0.25rem 0;
  }

  .message-content blockquote {
    margin: 0.75rem 0;
    padding-left: 1rem;
    border-left: 3px solid #3b82f6;
    color: #aaa;
    font-style: italic;
  }

  .message-content table {
    border-collapse: collapse;
    margin: 0.75rem 0;
    width: 100%;
  }

  .message-content th,
  .message-content td {
    border: 1px solid #2a2a2a;
    padding: 0.5rem;
    text-align: left;
  }

  .message-content th {
    background: rgba(59, 130, 246, 0.1);
    font-weight: 600;
  }

  .message-content h1,
  .message-content h2,
  .message-content h3,
  .message-content h4,
  .message-content h5,
  .message-content h6 {
    margin: 1rem 0 0.5rem;
    font-weight: 600;
    line-height: 1.3;
  }

  .message-content h1:first-child,
  .message-content h2:first-child,
  .message-content h3:first-child {
    margin-top: 0;
  }

  .message-content h1 { font-size: 1.5rem; }
  .message-content h2 { font-size: 1.3rem; }
  .message-content h3 { font-size: 1.1rem; }
  .message-content h4 { font-size: 1rem; }

  .message-content strong {
    font-weight: 600;
  }

  .message-content em {
    font-style: italic;
  }

  .message-content hr {
    border: none;
    border-top: 1px solid #2a2a2a;
    margin: 1rem 0;
  }

  /* Video Sources - New Card Design */
  .video-sources {
    margin-top: 1rem;
    padding-top: 0.75rem;
    border-top: 1px solid #2a2a2a;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .video-item {
    cursor: pointer;
    transition: background 0.2s ease;
    padding: 0.5rem;
    border-radius: 4px;
  }

  .video-item:hover {
    background: rgba(59, 130, 246, 0.05);
  }

  .video-title {
    color: #3b82f6;
    text-decoration: none;
    font-weight: 600;
    font-size: 1rem;
    display: block;
    margin-bottom: 0.25rem;
  }

  .video-title:hover {
    text-decoration: underline;
  }

  .video-description {
    color: #666;
    font-size: 0.75rem;
    line-height: 1.4;
    white-space: nowrap;
    overflow: hidden;
    position: relative;
    padding-right: 2rem;
  }

  /* Gradient fade effect on description */
  .video-description::after {
    content: '';
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 3rem;
    background: linear-gradient(to right, transparent, #1a1a1a);
    pointer-events: none;
  }

  /* Missing description fallback (old cached messages) */
  .video-description-missing {
    font-style: italic;
    opacity: 0.7;
  }

  /* Inline Video Citation Links */
  .message-content :global(.inline-video-link) {
    color: #3b82f6;
    text-decoration: none;
    font-weight: 600;
    border-bottom: 1px dotted #3b82f6;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .message-content :global(.inline-video-link:hover) {
    color: #60a5fa;
    border-bottom-color: #60a5fa;
    background: rgba(59, 130, 246, 0.1);
  }

  /* Custom Tooltip Styles */
  .custom-tooltip {
    position: fixed;
    z-index: 9999;
    background: #2a2a2a;
    border: 1px solid #3b82f6;
    border-radius: 6px;
    padding: 0.75rem;
    max-width: 400px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    pointer-events: none;
  }

  .tooltip-description {
    color: #e0e0e0;
    font-size: 0.875rem;
    line-height: 1.5;
    margin-bottom: 0.5rem;
  }

  .tooltip-tags {
    color: #888;
    font-size: 0.75rem;
    padding-top: 0.5rem;
    border-top: 1px solid #3a3a3a;
  }

  .input-area {
    padding: 1rem 2rem;
    border-top: 1px solid #2a2a2a;
    background: #1a1a1a;
    width: 100%;
    display: flex;
    justify-content: center;
  }

  .input-content {
    display: flex;
    gap: 0.75rem;
    width: 100%;
    max-width: 900px;
  }

  textarea {
    flex: 1;
    padding: 0.75rem;
    background: #0a0a0a;
    border: 1px solid #2a2a2a;
    border-radius: 0.5rem;
    color: #e5e5e5;
    font-family: inherit;
    font-size: 0.9375rem;
    resize: vertical;
    min-height: 60px;
  }

  textarea:focus {
    outline: none;
    border-color: #3b82f6;
  }

  textarea:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  button {
    padding: 0.75rem 1.25rem;
    background: #3b82f6;
    border: none;
    border-radius: 0.5rem;
    color: white;
    font-weight: 600;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s ease;
  }

  button:hover:not(:disabled) {
    background: #2563eb;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .random-question-btn {
    padding: 0.75rem;
    min-width: auto;
    width: 48px;
    height: 48px;
    background: #2a2a2a;
    border: none;
    border-radius: 0.5rem;
    color: #a0a0a0;
    font-size: 1.25rem;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .random-question-btn:hover:not(:disabled) {
    background: #3a3a3a;
    color: #e5e5e5;
    transform: rotate(15deg);
  }

  .random-question-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* Canvas Toggle Button */
  .canvas-toggle-btn {
    padding: 0.5rem 1rem;
    background: #2a2a2a;
    border: 1px solid #333;
    border-radius: 0.375rem;
    color: #a0a0a0;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .canvas-toggle-btn:hover {
    background: #3a3a3a;
    color: #e5e5e5;
  }

  .canvas-toggle-btn.active {
    background: #3b82f6;
    border-color: #3b82f6;
    color: white;
  }

  /* Canvas Sidebar */
  .canvas-sidebar {
    width: 400px;
    background: #0a0a0a;
    border-left: 1px solid #222;
    display: flex;
    flex-direction: column;
    transition: width 0.2s ease;
  }

  .canvas-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem;
    border-bottom: 1px solid #222;
  }

  .canvas-tabs {
    display: flex;
    gap: 0.25rem;
  }

  .canvas-tab {
    padding: 0.5rem 0.75rem;
    background: transparent;
    border: none;
    border-radius: 0.375rem;
    color: #888;
    font-size: 0.8125rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
  }

  .canvas-tab:hover {
    background: #1a1a1a;
    color: #e5e5e5;
  }

  .canvas-tab.active {
    background: #1a1a1a;
    color: #3b82f6;
  }

  .canvas-close-btn {
    width: 28px;
    height: 28px;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: 0.25rem;
    color: #888;
    font-size: 1.25rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
  }

  .canvas-close-btn:hover {
    background: #1a1a1a;
    color: #e5e5e5;
  }

  /* Canvas Editor */
  .canvas-editor {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 1rem;
    overflow: hidden;
  }

  .canvas-title-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
  }

  .canvas-title-input {
    flex: 1;
    padding: 0.5rem 0.75rem;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 0.375rem;
    color: #e5e5e5;
    font-size: 1rem;
    font-weight: 500;
  }

  .canvas-title-input:focus {
    outline: none;
    border-color: #3b82f6;
  }

  .save-status {
    font-size: 0.75rem;
    color: #666;
    white-space: nowrap;
  }

  .canvas-content {
    flex: 1;
    padding: 0.75rem;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 0.375rem;
    color: #e5e5e5;
    font-family: inherit;
    font-size: 0.9375rem;
    line-height: 1.6;
    resize: none;
  }

  .canvas-content:focus {
    outline: none;
    border-color: #3b82f6;
  }

  .canvas-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 0.75rem;
  }

  .save-btn {
    padding: 0.5rem 1rem;
    background: #3b82f6;
    border: none;
    border-radius: 0.375rem;
    color: white;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
  }

  .save-btn:hover:not(:disabled) {
    background: #2563eb;
  }

  .save-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .canvas-empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #666;
  }

  .canvas-empty p {
    margin-bottom: 1rem;
  }

  .create-artifact-btn {
    padding: 0.625rem 1.25rem;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 0.5rem;
    color: #e5e5e5;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .create-artifact-btn:hover {
    background: #2a2a2a;
    border-color: #444;
  }

  /* Canvas Browser */
  .canvas-browser {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .browser-header {
    padding: 0.75rem;
    border-bottom: 1px solid #222;
  }

  .artifacts-list {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem;
  }

  .no-artifacts {
    padding: 2rem;
    text-align: center;
    color: #666;
    font-size: 0.875rem;
  }

  .artifact-item {
    padding: 0.75rem;
    border-radius: 0.5rem;
    cursor: pointer;
    transition: background 0.15s;
    margin-bottom: 0.25rem;
  }

  .artifact-item:hover {
    background: #1a1a1a;
  }

  .artifact-item.active {
    background: rgba(59, 130, 246, 0.15);
  }

  .artifact-title {
    font-size: 0.875rem;
    font-weight: 500;
    color: #e5e5e5;
    margin-bottom: 0.25rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .artifact-preview {
    font-size: 0.75rem;
    color: #888;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin-bottom: 0.25rem;
  }

  .artifact-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .artifact-date {
    font-size: 0.6875rem;
    color: #666;
  }

  .artifact-delete-btn {
    width: 20px;
    height: 20px;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: 0.25rem;
    color: #666;
    font-size: 0.875rem;
    cursor: pointer;
    opacity: 0;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .artifact-item:hover .artifact-delete-btn {
    opacity: 1;
  }

  .artifact-delete-btn:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }
</style>
