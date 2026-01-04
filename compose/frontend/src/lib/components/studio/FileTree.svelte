<script>
  import { createEventDispatcher } from 'svelte';

  export let tree = [];
  export let depth = 0;

  const dispatch = createEventDispatcher();

  // Track expanded folders
  let expandedFolders = new Set();

  function toggleFolder(node) {
    if (expandedFolders.has(node.path)) {
      expandedFolders.delete(node.path);
    } else {
      expandedFolders.add(node.path);
    }
    expandedFolders = expandedFolders; // trigger reactivity
  }

  function handleClick(node) {
    if (node.type === 'folder') {
      toggleFolder(node);
    } else {
      dispatch('select', node);
    }
  }

  function handleContextMenu(e, node) {
    e.preventDefault();
    // Future: show context menu
    if (node.type === 'folder') {
      dispatch('create', node.path);
    }
  }

  function getIcon(node) {
    if (node.type === 'folder') {
      return expandedFolders.has(node.path) ? '📂' : '📁';
    }
    // File icon based on extension
    if (node.name.endsWith('.md')) return '📝';
    return '📄';
  }
</script>

<ul class="tree-list" style="--depth: {depth}">
  {#each tree as node (node.path || node.name)}
    <li class="tree-item">
      <button
        class="tree-node"
        class:folder={node.type === 'folder'}
        class:file={node.type === 'file'}
        on:click={() => handleClick(node)}
        on:contextmenu={(e) => handleContextMenu(e, node)}
      >
        <span class="tree-icon">{getIcon(node)}</span>
        <span class="tree-name">{node.name}</span>
      </button>

      {#if node.type === 'folder' && node.children && expandedFolders.has(node.path)}
        <svelte:self
          tree={node.children}
          depth={depth + 1}
          on:select
          on:create
        />
      {/if}
    </li>
  {/each}
</ul>

{#if tree.length === 0 && depth === 0}
  <div class="empty-tree">
    <p>No notes yet</p>
    <button class="create-first" on:click={() => dispatch('create', '')}>
      Create your first note
    </button>
  </div>
{/if}

<style>
  .tree-list {
    list-style: none;
    margin: 0;
    padding: 0;
    padding-left: calc(var(--depth) * 0.75rem);
  }

  .tree-item {
    margin: 0;
    padding: 0;
  }

  .tree-node {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    width: 100%;
    padding: 0.25rem 0.5rem;
    background: transparent;
    border: none;
    color: #ccc;
    font-size: 0.8125rem;
    text-align: left;
    cursor: pointer;
    border-radius: 3px;
    transition: background 0.15s;
  }

  .tree-node:hover {
    background: #2a2a2a;
  }

  .tree-node.folder {
    color: #888;
  }

  .tree-node.file:hover {
    color: #fff;
  }

  .tree-icon {
    font-size: 0.875rem;
    flex-shrink: 0;
  }

  .tree-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .empty-tree {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 2rem 1rem;
    color: #666;
    text-align: center;
  }

  .empty-tree p {
    margin: 0 0 0.75rem 0;
    font-size: 0.8125rem;
  }

  .create-first {
    padding: 0.5rem 1rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 0.375rem;
    font-size: 0.75rem;
    cursor: pointer;
    transition: background 0.2s;
  }

  .create-first:hover {
    background: #2563eb;
  }
</style>
