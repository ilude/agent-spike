<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let health = null;
  let error = '';

  onMount(async () => {
    try {
      health = await api.health();
    } catch (e) {
      error = e.message;
    }
  });
</script>

<main>
  <div class="container">
    <h1>Mentat</h1>
    <p class="tagline">Your AI Research Assistant</p>

    {#if health}
      <div class="status-card">
        <div class="status-indicator connected"></div>
        <div>
          <strong>Backend Status:</strong> {health.status}
          <br />
          <small>API Key: {health.api_key_configured ? 'Configured' : 'Not configured'}</small>
        </div>
      </div>
    {:else if error}
      <div class="status-card error">
        <strong>Error:</strong> {error}
      </div>
    {:else}
      <div class="status-card">
        <div class="status-indicator checking"></div>
        <div>Checking backend status...</div>
      </div>
    {/if}

    <div class="actions">
      <a href="/chat" class="btn-primary">Start Chat</a>
    </div>
  </div>
</main>

<style>
  main {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 2rem;
  }

  .container {
    max-width: 600px;
    text-align: center;
  }

  h1 {
    font-size: 3rem;
    color: #3b82f6;
    margin: 0 0 0.5rem 0;
  }

  .tagline {
    font-size: 1.25rem;
    color: #888;
    margin: 0 0 3rem 0;
  }

  .status-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 0.75rem;
    padding: 1.5rem;
    margin: 2rem 0;
    display: flex;
    align-items: center;
    gap: 1rem;
    text-align: left;
  }

  .status-card.error {
    background: #7f1d1d;
    border-color: #dc2626;
  }

  .status-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .status-indicator.connected {
    background: #10b981;
  }

  .status-indicator.checking {
    background: #f59e0b;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .actions {
    margin-top: 2rem;
  }

  .btn-primary {
    display: inline-block;
    padding: 1rem 2rem;
    background: #3b82f6;
    color: white;
    text-decoration: none;
    border-radius: 0.5rem;
    font-weight: 600;
    font-size: 1.125rem;
    transition: background 0.2s;
  }

  .btn-primary:hover {
    background: #2563eb;
  }

  small {
    color: #888;
    font-size: 0.875rem;
  }
</style>
