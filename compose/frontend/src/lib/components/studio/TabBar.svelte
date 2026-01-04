<script>
  import { createEventDispatcher } from 'svelte';

  export let tabs = [];
  export let activeId = null;

  const dispatch = createEventDispatcher();

  function selectTab(tab) {
    dispatch('select', tab.id);
  }

  function closeTab(e, tab) {
    e.stopPropagation();
    dispatch('close', tab.id);
  }

  function getTabName(tab) {
    // Extract filename from path
    if (tab.path) {
      const parts = tab.path.split('/');
      return parts[parts.length - 1].replace('.md', '');
    }
    return tab.title || 'Untitled';
  }
</script>

<div class="tab-bar">
  {#if tabs.length === 0}
    <div class="tab-placeholder">
      <span>No open files</span>
    </div>
  {:else}
    <div class="tabs">
      {#each tabs as tab (tab.id)}
        <div
          class="tab"
          class:active={tab.id === activeId}
          role="tab"
          tabindex="0"
          on:click={() => selectTab(tab)}
          on:keydown={(e) => e.key === 'Enter' && selectTab(tab)}
        >
          <span class="tab-name">{getTabName(tab)}</span>
          <button
            class="tab-close"
            on:click={(e) => closeTab(e, tab)}
            title="Close"
          >
            ×
          </button>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .tab-bar {
    display: flex;
    align-items: center;
    height: 36px;
    background: #1a1a1a;
    border-bottom: 1px solid #2a2a2a;
    flex-shrink: 0;
  }

  .tab-placeholder {
    display: flex;
    align-items: center;
    padding: 0 1rem;
    color: #666;
    font-size: 0.8125rem;
  }

  .tabs {
    display: flex;
    overflow-x: auto;
    max-width: 100%;
  }

  .tabs::-webkit-scrollbar {
    height: 2px;
  }

  .tabs::-webkit-scrollbar-track {
    background: transparent;
  }

  .tabs::-webkit-scrollbar-thumb {
    background: #333;
  }

  .tab {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0 0.75rem;
    height: 36px;
    background: transparent;
    border: none;
    border-right: 1px solid #2a2a2a;
    color: #888;
    font-size: 0.8125rem;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s;
  }

  .tab:hover {
    background: #222;
    color: #ccc;
  }

  .tab.active {
    background: #0a0a0a;
    color: #fff;
    border-bottom: 2px solid #3b82f6;
  }

  .tab-name {
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .tab-close {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    background: transparent;
    border: none;
    color: #666;
    font-size: 1rem;
    cursor: pointer;
    border-radius: 3px;
    padding: 0;
    opacity: 0;
    transition: all 0.15s;
  }

  .tab:hover .tab-close,
  .tab.active .tab-close {
    opacity: 1;
  }

  .tab-close:hover {
    background: #333;
    color: #fff;
  }
</style>
