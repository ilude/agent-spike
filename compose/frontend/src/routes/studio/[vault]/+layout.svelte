<script>
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { Splitpanes, Pane } from 'svelte-splitpanes';
  import {
    currentVault,
    fileTree,
    openTabs,
    activeTabId,
    activeNote,
    panelSizes,
    openNote,
    closeTab,
    closeAllTabs
  } from '$lib/stores/studio.js';
  import FileTree from '$lib/components/studio/FileTree.svelte';
  import TabBar from '$lib/components/studio/TabBar.svelte';
  import Sidebar from '$lib/components/studio/Sidebar.svelte';

  let loading = true;
  let error = '';

  // Get vault slug from URL
  $: vaultSlug = $page.params.vault;

  onMount(async () => {
    await loadVault();
  });

  onDestroy(() => {
    // Clean up on unmount
    currentVault.set(null);
    fileTree.set([]);
    closeAllTabs();
  });

  async function loadVault() {
    loading = true;
    error = '';
    try {
      const vault = await api.getVaultBySlug(vaultSlug);
      if (!vault) {
        error = 'Vault not found';
        loading = false;
        return;
      }
      currentVault.set(vault);

      // Load file tree
      const tree = await api.getVaultFileTree(vault.id);
      fileTree.set(tree);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function handleFileSelect(file) {
    if (file.type === 'file') {
      try {
        const note = await api.getNote(file.id);
        openNote(note);
      } catch (e) {
        console.error('Failed to load note:', e);
      }
    }
  }

  async function handleCreateNote(parentPath) {
    const name = prompt('Note name:');
    if (!name) return;

    const path = parentPath ? `${parentPath}/${name}.md` : `${name}.md`;
    try {
      const note = await api.createNote({
        vault_id: $currentVault.id,
        path,
        title: name,
        content: `# ${name}\n\n`
      });
      // Reload tree and open the new note
      const tree = await api.getVaultFileTree($currentVault.id);
      fileTree.set(tree);
      openNote(note);
    } catch (e) {
      alert('Failed to create note: ' + e.message);
    }
  }

  function handlePanelResize(event) {
    const sizes = event.detail;
    if (sizes && sizes.length === 3) {
      panelSizes.set({
        fileTree: sizes[0],
        editor: sizes[1],
        sidebar: sizes[2]
      });
    }
  }
</script>

{#if loading}
  <div class="loading-state">
    <div class="spinner"></div>
    <span>Loading vault...</span>
  </div>
{:else if error}
  <div class="error-state">
    <p>{error}</p>
    <a href="/studio">Back to vaults</a>
  </div>
{:else}
  <div class="workspace">
    <Splitpanes
      class="workspace-panes"
      on:resize={handlePanelResize}
    >
      <!-- File Tree Panel -->
      <Pane size={$panelSizes.fileTree} minSize={10} maxSize={40}>
        <div class="panel file-tree-panel">
          <div class="panel-header">
            <span class="panel-title">{$currentVault?.name || 'Files'}</span>
            <button class="icon-btn" on:click={() => handleCreateNote('')} title="New Note">
              +
            </button>
          </div>
          <div class="panel-content">
            <FileTree
              tree={$fileTree}
              on:select={(e) => handleFileSelect(e.detail)}
              on:create={(e) => handleCreateNote(e.detail)}
            />
          </div>
        </div>
      </Pane>

      <!-- Editor Panel -->
      <Pane size={$panelSizes.editor} minSize={30}>
        <div class="panel editor-panel">
          <TabBar
            tabs={$openTabs}
            activeId={$activeTabId}
            on:select={(e) => activeTabId.set(e.detail)}
            on:close={(e) => closeTab(e.detail)}
          />
          <div class="editor-content">
            <slot />
          </div>
        </div>
      </Pane>

      <!-- Sidebar Panel -->
      <Pane size={$panelSizes.sidebar} minSize={10} maxSize={40}>
        <Sidebar note={$activeNote} />
      </Pane>
    </Splitpanes>
  </div>
{/if}

<style>
  .loading-state,
  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 1rem;
    color: #888;
  }

  .error-state p {
    color: #f87171;
  }

  .error-state a {
    color: #3b82f6;
    text-decoration: none;
  }

  .error-state a:hover {
    text-decoration: underline;
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
    to { transform: rotate(360deg); }
  }

  .workspace {
    display: flex;
    flex: 1;
    height: 100%;
    overflow: hidden;
  }

  :global(.workspace-panes) {
    height: 100% !important;
  }

  :global(.splitpanes__splitter) {
    background: #2a2a2a !important;
    min-width: 4px !important;
    min-height: 4px !important;
  }

  :global(.splitpanes__splitter:hover) {
    background: #3b82f6 !important;
  }

  .panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #1a1a1a;
    border-right: 1px solid #2a2a2a;
  }

  .panel:last-child {
    border-right: none;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid #2a2a2a;
    background: #1f1f1f;
    height: 36px;
    flex-shrink: 0;
  }

  .panel-title {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #888;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .icon-btn {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: #888;
    font-size: 1rem;
    cursor: pointer;
    border-radius: 3px;
  }

  .icon-btn:hover {
    background: #2a2a2a;
    color: #fff;
  }

  .panel-content {
    flex: 1;
    overflow: auto;
  }

  .editor-panel {
    background: #0a0a0a;
  }

  .editor-content {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .file-tree-panel {
    background: #181818;
  }
</style>
