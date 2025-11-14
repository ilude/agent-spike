<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '$lib/api.js';

  let messages = [];
  let input = '';
  let ws = null;
  let connected = false;
  let error = '';
  let currentResponse = '';
  let isStreaming = false;

  function connectWebSocket() {
    ws = api.connectWebSocket();

    ws.onopen = () => {
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
              timestamp: new Date()
            }];
            currentResponse = '';
          }
          isStreaming = false;
        } else if (data.type === 'error') {
          error = data.content;
          isStreaming = false;
          currentResponse = '';
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
        error = 'Failed to parse server response';
      }
    };

    ws.onerror = (e) => {
      console.error('WebSocket error:', e);
      error = 'Connection error. Is the backend running?';
      connected = false;
    };

    ws.onclose = () => {
      connected = false;
      console.log('WebSocket disconnected');
      // Auto-reconnect after 2 seconds
      setTimeout(() => {
        if (!connected) {
          console.log('Attempting to reconnect...');
          connectWebSocket();
        }
      }, 2000);
    };
  }

  function send() {
    if (!input.trim() || !connected || isStreaming) return;

    const userMessage = input.trim();
    input = '';

    // Add user message to chat
    messages = [...messages, {
      role: 'user',
      content: userMessage,
      timestamp: new Date()
    }];

    // Send to backend
    ws.send(JSON.stringify({ message: userMessage }));
    isStreaming = true;
    currentResponse = '';
    error = '';
  }

  function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  }

  onMount(() => {
    connectWebSocket();
  });

  onDestroy(() => {
    if (ws) {
      ws.close();
    }
  });

  // Auto-scroll to bottom
  $: if (messages.length > 0 || currentResponse) {
    setTimeout(() => {
      const messagesDiv = document.querySelector('.messages');
      if (messagesDiv) {
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
      }
    }, 50);
  }
</script>

<main>
  <header>
    <h1>Mentat</h1>
    <div class="status">
      <span class="indicator" class:connected></span>
      {connected ? 'Connected' : 'Disconnected'}
    </div>
  </header>

  {#if error}
    <div class="error">
      <strong>Error:</strong> {error}
      <button on:click={() => error = ''}>✕</button>
    </div>
  {/if}

  <div class="messages">
    {#each messages as msg}
      <div class="message message-{msg.role}">
        <div class="message-header">
          <strong>{msg.role === 'user' ? 'You' : 'Mentat'}</strong>
          <span class="timestamp">{msg.timestamp.toLocaleTimeString()}</span>
        </div>
        <div class="message-content">{msg.content}</div>
        {#if msg.sources && msg.sources.length > 0}
          <div class="sources">
            <em>Sources:</em> {msg.sources.join(', ')}
          </div>
        {/if}
      </div>
    {/each}

    {#if currentResponse}
      <div class="message message-assistant streaming">
        <div class="message-header">
          <strong>Mentat</strong>
          <span class="typing-indicator">typing...</span>
        </div>
        <div class="message-content">{currentResponse}</div>
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

  <div class="input-area">
    <textarea
      bind:value={input}
      on:keypress={handleKeyPress}
      disabled={!connected || isStreaming}
      placeholder={connected ? "Ask Mentat..." : "Connecting..."}
      rows="2"
    ></textarea>
    <button
      on:click={send}
      disabled={!connected || isStreaming || !input.trim()}
    >
      {isStreaming ? 'Sending...' : 'Send'}
    </button>
  </div>
</main>

<style>
  main {
    max-width: 900px;
    margin: 0 auto;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    border-bottom: 1px solid #2a2a2a;
    background: #1a1a1a;
  }

  h1 {
    margin: 0;
    font-size: 1.5rem;
    color: #3b82f6;
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

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
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
    max-width: 75%;
    padding: 1rem;
    border-radius: 0.75rem;
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
  }

  .message-user {
    align-self: flex-end;
    background: #1e3a8a;
    border-color: #1e40af;
  }

  .message-assistant {
    align-self: flex-start;
  }

  .message-assistant.streaming {
    border-color: #3b82f6;
  }

  .message-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
  }

  .message-header strong {
    color: #3b82f6;
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

  .message-content {
    white-space: pre-wrap;
    word-wrap: break-word;
    line-height: 1.5;
  }

  .sources {
    margin-top: 0.75rem;
    padding-top: 0.75rem;
    border-top: 1px solid #2a2a2a;
    font-size: 0.875rem;
    color: #888;
  }

  .input-area {
    padding: 1rem 2rem;
    border-top: 1px solid #2a2a2a;
    background: #1a1a1a;
    display: flex;
    gap: 0.75rem;
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
    padding: 0.75rem 1.5rem;
    background: #3b82f6;
    border: none;
    border-radius: 0.5rem;
    color: white;
    font-weight: 600;
    cursor: pointer;
    font-size: 0.9375rem;
    transition: background 0.2s;
  }

  button:hover:not(:disabled) {
    background: #2563eb;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
