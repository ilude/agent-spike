<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '$lib/api.js';

  let stats = null;
  let eventSource = null;
  let connected = false;
  let error = '';

  // Ingest state
  let ingestUrl = '';
  let ingestLoading = false;
  let ingestResult = null;
  let channelLimitOpen = false;
  let detectedType = null;

  // Detect URL type as user types
  async function detectUrlType() {
    if (!ingestUrl.trim()) {
      detectedType = null;
      return;
    }
    try {
      const result = await api.detectUrlType(ingestUrl);
      detectedType = result.type;
    } catch (e) {
      detectedType = null;
    }
  }

  async function submitIngest(channelLimit = 'all') {
    if (!ingestUrl.trim() || ingestLoading) return;

    ingestLoading = true;
    ingestResult = null;
    channelLimitOpen = false;

    try {
      const result = await api.ingestUrl(ingestUrl, channelLimit);
      ingestResult = result;
      if (result.status === 'success' || result.status === 'queued') {
        ingestUrl = '';
        detectedType = null;
        // Auto-fade success/queued messages after 5 seconds
        setTimeout(() => {
          if (ingestResult?.status === 'success' || ingestResult?.status === 'queued') {
            ingestResult = null;
          }
        }, 5000);
      }
    } catch (e) {
      ingestResult = { status: 'error', message: e.message };
    } finally {
      ingestLoading = false;
    }
  }

  function handleIngestKeypress(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitIngest();
    }
  }

  onMount(() => {
    // Connect to SSE stream for real-time updates
    eventSource = api.connectStatsStream(
      (data) => {
        stats = data;
        connected = true;
        error = '';
      },
      (err) => {
        connected = false;
        // Connection status shown in Stream health card, no need for flash bar
      }
    );
  });

  onDestroy(() => {
    if (eventSource) {
      eventSource.close();
    }
  });

  function formatNumber(n) {
    return n?.toLocaleString() ?? '0';
  }

  function getProgressPercent(progress) {
    if (!progress || !progress.total) return 0;
    return Math.round((progress.completed / progress.total) * 100);
  }
</script>

<main>
  <header>
    <a href="/" class="logo">Mentat</a>
    <nav>
      <a href="/chat" class="nav-link">Chat</a>
    </nav>
  </header>

  <div class="dashboard">
    <h1>Dashboard</h1>

    {#if error}
      <div class="alert error">{error}</div>
    {/if}

    <!-- Ingest Section -->
    <div class="ingest-section">
      <h2>Ingest URL</h2>
      <div class="ingest-form">
        <div class="ingest-input-wrapper">
          <input
            type="text"
            bind:value={ingestUrl}
            on:input={detectUrlType}
            on:keypress={handleIngestKeypress}
            placeholder="Paste YouTube video, channel, or article URL..."
            disabled={ingestLoading}
          />
          {#if detectedType}
            <span class="url-type-badge" class:video={detectedType === 'video'} class:channel={detectedType === 'channel'} class:article={detectedType === 'article'}>
              {detectedType}
            </span>
          {/if}
        </div>
        <div class="ingest-buttons">
          <button
            class="ingest-btn primary"
            on:click={() => submitIngest()}
            disabled={!ingestUrl.trim() || ingestLoading}
          >
            {ingestLoading ? 'Processing...' : 'Ingest'}
          </button>
          {#if detectedType === 'channel'}
            <div class="dropdown-wrapper">
              <button
                class="ingest-btn secondary dropdown-trigger"
                on:click={() => channelLimitOpen = !channelLimitOpen}
                disabled={!ingestUrl.trim() || ingestLoading}
              >
                Options
              </button>
              {#if channelLimitOpen}
                <div class="dropdown-menu">
                  <button on:click={() => submitIngest('month')}>Past Month</button>
                  <button on:click={() => submitIngest('year')}>Past Year</button>
                  <button on:click={() => submitIngest('50')}>50 Videos</button>
                  <button on:click={() => submitIngest('100')}>100 Videos</button>
                  <button on:click={() => submitIngest('all')}>All Videos</button>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      </div>
      {#if ingestResult}
        <div class="ingest-result" class:success={ingestResult.status === 'success' || ingestResult.status === 'queued'} class:error={ingestResult.status === 'error'} class:skipped={ingestResult.status === 'skipped'}>
          <span class="result-status">{ingestResult.status}</span>
          <span class="result-message">{ingestResult.message}</span>
        </div>
      {/if}
    </div>

    {#if stats}
      <div class="stats-grid">
        <!-- System Health -->
        <div class="stat-card health">
          <h3>System Health</h3>
          <div class="sub-cards health-grid">
            <div class="sub-card health-status" class:healthy={stats.health?.qdrant?.ok} class:unhealthy={!stats.health?.qdrant?.ok}>
              <span class="sub-card-label">Qdrant</span>
              <span class="sub-card-location">{stats.health?.qdrant?.local ? 'local' : 'remote'}</span>
            </div>
            <div class="sub-card health-status" class:healthy={stats.health?.infinity?.ok} class:unhealthy={!stats.health?.infinity?.ok}>
              <span class="sub-card-label">Infinity</span>
              <span class="sub-card-location">{stats.health?.infinity?.local ? 'local' : 'remote'}</span>
            </div>
            <div class="sub-card health-status" class:healthy={stats.health?.ollama?.ok} class:unhealthy={!stats.health?.ollama?.ok}>
              <span class="sub-card-label">Ollama</span>
              <span class="sub-card-location">{stats.health?.ollama?.local ? 'local' : 'remote'}</span>
            </div>
            <div class="sub-card health-status" class:healthy={stats.health?.queue_worker?.ok} class:unhealthy={!stats.health?.queue_worker?.ok}>
              <span class="sub-card-label">Worker</span>
              <span class="sub-card-location">{stats.health?.queue_worker?.local ? 'local' : 'remote'}</span>
            </div>
            <div class="sub-card health-status" class:healthy={connected} class:unhealthy={!connected}>
              <span class="sub-card-label">Stream</span>
              <span class="sub-card-location">local</span>
            </div>
          </div>
        </div>

        <!-- Queue Status -->
        <div class="stat-card queue">
          <h3>Queue Status</h3>
          <div class="sub-cards">
            <div class="sub-card">
              <span class="sub-card-value">{stats.queue?.pending_count ?? 0}</span>
              <span class="sub-card-label">Pending</span>
            </div>
            <div class="sub-card">
              <span class="sub-card-value">{stats.queue?.processing_count ?? 0}</span>
              <span class="sub-card-label">Processing</span>
            </div>
            <div class="sub-card">
              <span class="sub-card-value">{stats.queue?.completed_count ?? 0}</span>
              <span class="sub-card-label">Completed</span>
            </div>
          </div>

          {#if stats.queue?.current_progress}
            <div class="progress-section">
              <div class="progress-label">
                <strong>{stats.queue.current_progress.filename}</strong>
              </div>
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  style="width: {getProgressPercent(stats.queue.current_progress)}%"
                ></div>
              </div>
              <div class="progress-text">
                {stats.queue.current_progress.completed} / {stats.queue.current_progress.total}
                ({getProgressPercent(stats.queue.current_progress)}%)
              </div>
            </div>
          {:else if stats.queue?.processing_count > 0}
            <div class="progress-section">
              <div class="progress-label">{stats.queue.processing_files?.[0]}</div>
            </div>
          {:else}
            <div class="idle-text">Idle</div>
          {/if}
        </div>

        <!-- Content -->
        <div class="stat-card content">
          <div class="card-header">
            <h3>Content</h3>
            <span class="card-source">In Qdrant</span>
          </div>
          <div class="sub-cards">
            <div class="sub-card">
              <span class="sub-card-value">{formatNumber(stats.cache?.videos ?? 0)}</span>
              <span class="sub-card-label">Videos</span>
            </div>
            <div class="sub-card">
              <span class="sub-card-value">{formatNumber(stats.cache?.articles ?? 0)}</span>
              <span class="sub-card-label">Articles</span>
            </div>
            <div class="sub-card highlight">
              <span class="sub-card-value">{formatNumber(stats.cache?.total ?? 0)}</span>
              <span class="sub-card-label">Total</span>
            </div>
          </div>
          {#if stats.cache?.status === 'error'}
            <div class="stat-error">{stats.cache.message}</div>
          {/if}
          <div class="archived-count">
            {formatNumber(stats.archive?.total_videos ?? 0)} Archived Items
          </div>
        </div>

        <!-- Recent Activity -->
        <div class="stat-card activity">
          <h3>Recent Activity</h3>
          {#if stats.recent_activity?.length > 0}
            <div class="activity-list">
              {#each stats.recent_activity as activity}
                <div class="activity-item">
                  <span class="activity-type">{activity.type}</span>
                  <span class="activity-file">{activity.file}</span>
                </div>
              {/each}
            </div>
          {:else}
            <div class="no-activity">No recent activity</div>
          {/if}
        </div>
      </div>

      <div class="timestamp">
        Last updated: {new Date(stats.timestamp).toLocaleTimeString()}
      </div>
    {:else}
      <div class="loading">
        <div class="spinner"></div>
        <span>Connecting to stats stream...</span>
      </div>
    {/if}
  </div>
</main>

<style>
  main {
    min-height: 100vh;
    padding: 0;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    background: #111;
    border-bottom: 1px solid #222;
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

  nav {
    display: flex;
    gap: 1rem;
  }

  .nav-link {
    color: #888;
    text-decoration: none;
    padding: 0.5rem 1rem;
    border-radius: 0.375rem;
    transition: all 0.2s;
  }

  .nav-link:hover {
    color: #fff;
    background: #1a1a1a;
  }

  .dashboard {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
  }

  h1 {
    font-size: 2rem;
    margin: 0 0 2rem 0;
    color: #fff;
  }

  .alert {
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
  }

  .alert.error {
    background: #7f1d1d;
    border: 1px solid #dc2626;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem;
  }

  .stat-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 0.75rem;
    padding: 1.5rem;
  }

  .stat-card h3 {
    margin: 0 0 1rem 0;
    font-size: 0.875rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #888;
  }

  .stat-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: #fff;
    line-height: 1;
  }

  .stat-label {
    font-size: 0.875rem;
    color: #666;
    margin-top: 0.25rem;
  }

  .stat-error {
    font-size: 0.75rem;
    color: #f87171;
    margin-top: 0.5rem;
  }

  /* Health card */
  .health-items {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .health-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .indicator {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #666;
  }

  .indicator.ok {
    background: #10b981;
  }

  .indicator.error {
    background: #ef4444;
  }

  /* Progress section */
  .progress-section {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #2a2a2a;
  }

  .progress-label {
    font-size: 0.75rem;
    color: #888;
    margin-bottom: 0.5rem;
  }

  .progress-label strong {
    color: #fff;
  }

  .progress-bar {
    height: 8px;
    background: #2a2a2a;
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #60a5fa);
    transition: width 0.3s ease;
  }

  .progress-text {
    font-size: 0.75rem;
    color: #888;
    margin-top: 0.25rem;
    text-align: right;
  }

  .idle-text {
    margin-top: 1rem;
    font-size: 0.875rem;
    color: #666;
  }

  /* Sub-cards */
  .sub-cards {
    display: flex;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .sub-card {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    padding: 0.75rem 0.5rem;
    background: #0a0a0a;
    border: 1px solid #2a2a2a;
    border-radius: 0.5rem;
  }

  .sub-card.highlight {
    background: rgba(59, 130, 246, 0.1);
    border-color: rgba(59, 130, 246, 0.3);
  }

  .health-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
  }

  .sub-card.health-status {
    padding: 0.5rem;
    justify-content: center;
  }

  .sub-card.health-status .sub-card-label {
    color: #fff;
    font-size: 0.75rem;
  }

  .sub-card-location {
    font-size: 0.625rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: lowercase;
  }

  .sub-card.healthy {
    background: rgba(16, 185, 129, 0.2);
    border-color: rgba(16, 185, 129, 0.4);
  }

  .sub-card.unhealthy {
    background: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.4);
  }

  .sub-card-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #fff;
    line-height: 1;
  }

  .sub-card.highlight .sub-card-value {
    color: #3b82f6;
  }

  .sub-card-label {
    font-size: 0.625rem;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 1rem;
  }

  .card-header h3 {
    margin: 0;
  }

  .card-source {
    font-size: 0.75rem;
    color: #666;
  }

  .archived-count {
    margin-top: 0.75rem;
    padding-top: 0.75rem;
    border-top: 1px solid #2a2a2a;
    font-size: 0.75rem;
    color: #666;
    text-align: right;
  }

  /* Month breakdown */
  .month-breakdown {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #2a2a2a;
  }

  .month-item {
    display: flex;
    justify-content: space-between;
    font-size: 0.875rem;
    color: #888;
    padding: 0.25rem 0;
  }

  /* File list */
  .file-list {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #2a2a2a;
  }

  .file-item {
    font-size: 0.75rem;
    color: #666;
    padding: 0.25rem 0;
    word-break: break-all;
  }

  /* Activity */
  .activity-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .activity-item {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    padding: 0.5rem;
    background: #0a0a0a;
    border-radius: 0.375rem;
  }

  .activity-type {
    font-size: 0.625rem;
    text-transform: uppercase;
    color: #3b82f6;
  }

  .activity-file {
    font-size: 0.75rem;
    color: #888;
    word-break: break-all;
  }

  .no-activity {
    color: #666;
    font-size: 0.875rem;
  }

  .timestamp {
    position: fixed;
    bottom: 1rem;
    right: 1rem;
    font-size: 0.75rem;
    color: #666;
  }

  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    padding: 4rem;
    color: #888;
  }

  .spinner {
    width: 24px;
    height: 24px;
    border: 2px solid #333;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* Ingest Section */
  .ingest-section {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 0.75rem;
    padding: 1.5rem;
    margin-bottom: 2rem;
  }

  .ingest-section h2 {
    margin: 0 0 1rem 0;
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #888;
  }

  .ingest-form {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
  }

  .ingest-input-wrapper {
    flex: 1;
    position: relative;
  }

  .ingest-input-wrapper input {
    width: 100%;
    padding: 0.75rem 1rem;
    padding-right: 5rem;
    background: #0a0a0a;
    border: 1px solid #2a2a2a;
    border-radius: 0.5rem;
    color: #e5e5e5;
    font-size: 0.9375rem;
    transition: border-color 0.2s;
  }

  .ingest-input-wrapper input:focus {
    outline: none;
    border-color: #3b82f6;
  }

  .ingest-input-wrapper input:disabled {
    opacity: 0.5;
  }

  .url-type-badge {
    position: absolute;
    right: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.625rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .url-type-badge.video {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }

  .url-type-badge.channel {
    background: rgba(59, 130, 246, 0.2);
    color: #3b82f6;
  }

  .url-type-badge.article {
    background: rgba(16, 185, 129, 0.2);
    color: #10b981;
  }

  .ingest-buttons {
    display: flex;
    gap: 0.5rem;
  }

  .ingest-btn {
    padding: 0.75rem 1.25rem;
    border: none;
    border-radius: 0.5rem;
    font-weight: 600;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .ingest-btn.primary {
    background: #3b82f6;
    color: white;
  }

  .ingest-btn.primary:hover:not(:disabled) {
    background: #2563eb;
  }

  .ingest-btn.secondary {
    background: #2a2a2a;
    color: #a0a0a0;
  }

  .ingest-btn.secondary:hover:not(:disabled) {
    background: #3a3a3a;
    color: #e5e5e5;
  }

  .ingest-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .dropdown-wrapper {
    position: relative;
  }

  .dropdown-menu {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 0.25rem;
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 0.5rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    z-index: 100;
    min-width: 140px;
  }

  .dropdown-menu button {
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

  .dropdown-menu button:hover {
    background: #2a2a2a;
  }

  .dropdown-menu button:first-child {
    border-radius: 0.5rem 0.5rem 0 0;
  }

  .dropdown-menu button:last-child {
    border-radius: 0 0 0.5rem 0.5rem;
  }

  .ingest-result {
    margin-top: 1rem;
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .ingest-result.success {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .ingest-result.error {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
  }

  .ingest-result.skipped {
    background: rgba(234, 179, 8, 0.1);
    border: 1px solid rgba(234, 179, 8, 0.3);
  }

  .result-status {
    font-size: 0.625rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
  }

  .ingest-result.success .result-status {
    background: rgba(16, 185, 129, 0.2);
    color: #10b981;
  }

  .ingest-result.error .result-status {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }

  .ingest-result.skipped .result-status {
    background: rgba(234, 179, 8, 0.2);
    color: #eab308;
  }

  .result-message {
    font-size: 0.875rem;
    color: #e5e5e5;
  }
</style>
