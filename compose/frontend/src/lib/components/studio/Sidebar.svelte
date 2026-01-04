<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { sidebarMode, openNote } from '$lib/stores/studio.js';

  export let note = null;

  let backlinks = [];
  let outlinks = [];
  let suggestions = [];
  let loading = false;

  // Reload data when note changes
  $: if (note?.id) {
    loadSidebarData(note.id);
  }

  async function loadSidebarData(noteId) {
    loading = true;
    try {
      const links = await api.getNoteLinks(noteId);
      backlinks = links.backlinks || [];
      outlinks = links.outlinks || [];
      suggestions = await api.getNoteSuggestions(noteId);
    } catch (e) {
      console.error('Failed to load sidebar data:', e);
    } finally {
      loading = false;
    }
  }

  async function handleLinkClick(link) {
    try {
      const linkedNote = await api.getNote(link.target_id || link.source_id);
      openNote(linkedNote);
    } catch (e) {
      console.error('Failed to load linked note:', e);
    }
  }

  async function acceptSuggestion(suggestion) {
    try {
      await api.acceptSuggestion(suggestion.id);
      suggestions = suggestions.filter(s => s.id !== suggestion.id);
    } catch (e) {
      console.error('Failed to accept suggestion:', e);
    }
  }

  async function rejectSuggestion(suggestion) {
    try {
      await api.rejectSuggestion(suggestion.id);
      suggestions = suggestions.filter(s => s.id !== suggestion.id);
    } catch (e) {
      console.error('Failed to reject suggestion:', e);
    }
  }
</script>

<div class="sidebar">
  <div class="sidebar-tabs">
    <button
      class="sidebar-tab"
      class:active={$sidebarMode === 'backlinks'}
      on:click={() => sidebarMode.set('backlinks')}
    >
      Links
      {#if backlinks.length > 0 || outlinks.length > 0}
        <span class="badge">{backlinks.length + outlinks.length}</span>
      {/if}
    </button>
    <button
      class="sidebar-tab"
      class:active={$sidebarMode === 'suggestions'}
      on:click={() => sidebarMode.set('suggestions')}
    >
      AI
      {#if suggestions.length > 0}
        <span class="badge">{suggestions.length}</span>
      {/if}
    </button>
    <button
      class="sidebar-tab"
      class:active={$sidebarMode === 'outline'}
      on:click={() => sidebarMode.set('outline')}
    >
      Outline
    </button>
  </div>

  <div class="sidebar-content">
    {#if !note}
      <div class="empty-sidebar">
        <p>Select a note to view details</p>
      </div>
    {:else if loading}
      <div class="loading-sidebar">
        <div class="spinner"></div>
      </div>
    {:else if $sidebarMode === 'backlinks'}
      <div class="links-section">
        {#if backlinks.length > 0}
          <div class="link-group">
            <h4>Backlinks ({backlinks.length})</h4>
            <ul class="link-list">
              {#each backlinks as link}
                <li>
                  <button class="link-item" on:click={() => handleLinkClick(link)}>
                    <span class="link-icon">←</span>
                    <span class="link-text">{link.source_title || link.source_path}</span>
                  </button>
                </li>
              {/each}
            </ul>
          </div>
        {/if}

        {#if outlinks.length > 0}
          <div class="link-group">
            <h4>Outgoing Links ({outlinks.length})</h4>
            <ul class="link-list">
              {#each outlinks as link}
                <li>
                  <button class="link-item" on:click={() => handleLinkClick(link)}>
                    <span class="link-icon">→</span>
                    <span class="link-text">{link.target_title || link.link_text}</span>
                  </button>
                </li>
              {/each}
            </ul>
          </div>
        {/if}

        {#if backlinks.length === 0 && outlinks.length === 0}
          <div class="empty-section">
            <p>No links yet</p>
            <span class="hint">Use [[wiki-links]] to connect notes</span>
          </div>
        {/if}
      </div>
    {:else if $sidebarMode === 'suggestions'}
      <div class="suggestions-section">
        {#if suggestions.length > 0}
          <ul class="suggestion-list">
            {#each suggestions as suggestion}
              <li class="suggestion-item">
                <div class="suggestion-content">
                  <span class="suggestion-type">{suggestion.suggestion_type}</span>
                  <p class="suggestion-text">{suggestion.suggested_text}</p>
                  {#if suggestion.reason}
                    <span class="suggestion-reason">{suggestion.reason}</span>
                  {/if}
                </div>
                <div class="suggestion-actions">
                  <button
                    class="action-btn accept"
                    on:click={() => acceptSuggestion(suggestion)}
                    title="Accept"
                  >
                    ✓
                  </button>
                  <button
                    class="action-btn reject"
                    on:click={() => rejectSuggestion(suggestion)}
                    title="Dismiss"
                  >
                    ×
                  </button>
                </div>
              </li>
            {/each}
          </ul>
        {:else}
          <div class="empty-section">
            <p>No suggestions</p>
            <span class="hint">AI will suggest links as you write</span>
          </div>
        {/if}
      </div>
    {:else if $sidebarMode === 'outline'}
      <div class="outline-section">
        <div class="empty-section">
          <p>Outline</p>
          <span class="hint">Headings will appear here</span>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .sidebar {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #181818;
    border-left: 1px solid #2a2a2a;
  }

  .sidebar-tabs {
    display: flex;
    border-bottom: 1px solid #2a2a2a;
    flex-shrink: 0;
  }

  .sidebar-tab {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
    padding: 0.625rem;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: #888;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .sidebar-tab:hover {
    color: #ccc;
    background: #1f1f1f;
  }

  .sidebar-tab.active {
    color: #fff;
    border-bottom-color: #3b82f6;
  }

  .badge {
    font-size: 0.625rem;
    padding: 0.125rem 0.375rem;
    background: #333;
    border-radius: 9999px;
  }

  .sidebar-tab.active .badge {
    background: #3b82f6;
  }

  .sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: 0.75rem;
  }

  .empty-sidebar,
  .loading-sidebar {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #666;
    text-align: center;
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid #333;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .link-group {
    margin-bottom: 1.5rem;
  }

  .link-group h4 {
    margin: 0 0 0.5rem 0;
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #888;
  }

  .link-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .link-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.375rem 0.5rem;
    background: transparent;
    border: none;
    color: #ccc;
    font-size: 0.8125rem;
    text-align: left;
    cursor: pointer;
    border-radius: 4px;
    transition: background 0.15s;
  }

  .link-item:hover {
    background: #2a2a2a;
    color: #fff;
  }

  .link-icon {
    font-size: 0.75rem;
    color: #3b82f6;
  }

  .link-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .empty-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 2rem 1rem;
    text-align: center;
  }

  .empty-section p {
    margin: 0 0 0.25rem 0;
    color: #888;
    font-size: 0.8125rem;
  }

  .hint {
    color: #666;
    font-size: 0.75rem;
  }

  .suggestion-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .suggestion-item {
    display: flex;
    gap: 0.5rem;
    padding: 0.75rem;
    background: #1f1f1f;
    border: 1px solid #2a2a2a;
    border-radius: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .suggestion-content {
    flex: 1;
  }

  .suggestion-type {
    font-size: 0.625rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #3b82f6;
    display: block;
    margin-bottom: 0.25rem;
  }

  .suggestion-text {
    margin: 0 0 0.25rem 0;
    font-size: 0.8125rem;
    color: #e5e5e5;
  }

  .suggestion-reason {
    font-size: 0.75rem;
    color: #888;
  }

  .suggestion-actions {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .action-btn {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #2a2a2a;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
  }

  .action-btn.accept {
    color: #10b981;
  }

  .action-btn.accept:hover {
    background: rgba(16, 185, 129, 0.2);
  }

  .action-btn.reject {
    color: #888;
  }

  .action-btn.reject:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }
</style>
