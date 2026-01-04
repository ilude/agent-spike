<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  let vaults = [];
  let loading = true;
  let error = '';
  let showCreateModal = false;
  let newVaultName = '';
  let creating = false;

  onMount(async () => {
    await loadVaults();
  });

  async function loadVaults() {
    loading = true;
    try {
      vaults = await api.listVaults();
      error = '';
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function createVault() {
    if (!newVaultName.trim() || creating) return;
    creating = true;
    try {
      const vault = await api.createVault({ name: newVaultName.trim() });
      showCreateModal = false;
      newVaultName = '';
      goto(`/studio/${vault.slug}`);
    } catch (e) {
      error = e.message;
    } finally {
      creating = false;
    }
  }

  async function deleteVault(vault) {
    if (!confirm(`Delete vault "${vault.name}"? This cannot be undone.`)) return;
    try {
      await api.deleteVault(vault.id);
      await loadVaults();
    } catch (e) {
      error = e.message;
    }
  }

  function handleKeypress(e) {
    if (e.key === 'Enter') {
      createVault();
    } else if (e.key === 'Escape') {
      showCreateModal = false;
    }
  }
</script>

<div class="vault-selector">
  <div class="vault-header">
    <h1>Vaults</h1>
    <button class="create-btn" on:click={() => showCreateModal = true}>
      + New Vault
    </button>
  </div>

  {#if error}
    <div class="error-message">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">
      <div class="spinner"></div>
      <span>Loading vaults...</span>
    </div>
  {:else if vaults.length === 0}
    <div class="empty-state">
      <div class="empty-icon">📚</div>
      <h2>No vaults yet</h2>
      <p>Create your first vault to start taking notes</p>
      <button class="create-btn primary" on:click={() => showCreateModal = true}>
        Create Vault
      </button>
    </div>
  {:else}
    <div class="vault-grid">
      {#each vaults as vault}
        <a href="/studio/{vault.slug}" class="vault-card">
          <div class="vault-icon">📁</div>
          <div class="vault-info">
            <h3>{vault.name}</h3>
            <span class="vault-meta">{vault.note_count || 0} notes</span>
          </div>
          <button
            class="vault-delete"
            on:click|preventDefault|stopPropagation={() => deleteVault(vault)}
          >
            ×
          </button>
        </a>
      {/each}
    </div>
  {/if}
</div>

{#if showCreateModal}
  <div class="modal-overlay" on:click={() => showCreateModal = false}>
    <div class="modal" on:click|stopPropagation>
      <h2>Create New Vault</h2>
      <input
        type="text"
        bind:value={newVaultName}
        on:keydown={handleKeypress}
        placeholder="Vault name..."
        autofocus
        disabled={creating}
      />
      <div class="modal-actions">
        <button class="btn secondary" on:click={() => showCreateModal = false}>
          Cancel
        </button>
        <button
          class="btn primary"
          on:click={createVault}
          disabled={!newVaultName.trim() || creating}
        >
          {creating ? 'Creating...' : 'Create'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .vault-selector {
    flex: 1;
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
  }

  .vault-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }

  h1 {
    font-size: 2rem;
    margin: 0;
    color: #fff;
  }

  .create-btn {
    padding: 0.75rem 1.25rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 0.5rem;
    font-weight: 600;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.2s;
  }

  .create-btn:hover {
    background: #2563eb;
  }

  .create-btn.primary {
    padding: 1rem 2rem;
    font-size: 1rem;
  }

  .error-message {
    padding: 1rem;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 0.5rem;
    color: #f87171;
    margin-bottom: 1rem;
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
    to { transform: rotate(360deg); }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem 2rem;
    text-align: center;
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  .empty-state h2 {
    margin: 0 0 0.5rem 0;
    color: #fff;
  }

  .empty-state p {
    color: #888;
    margin: 0 0 1.5rem 0;
  }

  .vault-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
  }

  .vault-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.25rem;
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 0.75rem;
    text-decoration: none;
    color: inherit;
    transition: all 0.2s;
    position: relative;
  }

  .vault-card:hover {
    border-color: #3b82f6;
    background: #1f1f1f;
  }

  .vault-icon {
    font-size: 2rem;
    opacity: 0.8;
  }

  .vault-info {
    flex: 1;
  }

  .vault-info h3 {
    margin: 0 0 0.25rem 0;
    font-size: 1.125rem;
    color: #fff;
  }

  .vault-meta {
    font-size: 0.75rem;
    color: #888;
  }

  .vault-delete {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    width: 24px;
    height: 24px;
    background: transparent;
    border: none;
    color: #666;
    font-size: 1.25rem;
    cursor: pointer;
    border-radius: 4px;
    opacity: 0;
    transition: all 0.2s;
  }

  .vault-card:hover .vault-delete {
    opacity: 1;
  }

  .vault-delete:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }

  /* Modal */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 0.75rem;
    padding: 1.5rem;
    width: 100%;
    max-width: 400px;
  }

  .modal h2 {
    margin: 0 0 1rem 0;
    font-size: 1.25rem;
    color: #fff;
  }

  .modal input {
    width: 100%;
    padding: 0.75rem 1rem;
    background: #0a0a0a;
    border: 1px solid #2a2a2a;
    border-radius: 0.5rem;
    color: #e5e5e5;
    font-size: 1rem;
    margin-bottom: 1rem;
  }

  .modal input:focus {
    outline: none;
    border-color: #3b82f6;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  .btn {
    padding: 0.625rem 1rem;
    border: none;
    border-radius: 0.5rem;
    font-weight: 600;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn.primary {
    background: #3b82f6;
    color: white;
  }

  .btn.primary:hover:not(:disabled) {
    background: #2563eb;
  }

  .btn.primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn.secondary {
    background: #2a2a2a;
    color: #a0a0a0;
  }

  .btn.secondary:hover {
    background: #3a3a3a;
    color: #e5e5e5;
  }
</style>
