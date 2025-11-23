<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { auth, currentUser } from '$lib/stores/auth.js';
  import { api } from '$lib/api.js';

  export let show = false;

  const dispatch = createEventDispatcher();

  // Sections
  const sections = [
    { id: 'profile', label: 'Profile', icon: '👤' },
    { id: 'models', label: 'Models', icon: '🤖' },
    { id: 'environment', label: 'Environment', icon: '🔑' },
    { id: 'preferences', label: 'Preferences', icon: '⚙️' },
  ];

  // Admin-only sections
  const adminSections = [
    { id: 'users', label: 'Users', icon: '👥' },
    { id: 'system', label: 'System', icon: '🔧' },
  ];

  let activeSection = 'profile';
  let loading = false;
  let error = '';
  let success = '';

  // Profile state
  let displayName = '';
  let email = '';
  let currentPassword = '';
  let newPassword = '';
  let confirmPassword = '';

  // API Keys state
  let apiKeys = [];
  let newApiKeys = { anthropic: '', openai: '', openrouter: '', youtube: '' };

  // Model configuration state
  let ollamaUrl = 'http://localhost:11434';

  // Admin state
  let users = [];
  let inviteEmail = '';
  let invites = [];

  // Preferences state
  let enableLlmFilenames = false;
  let filenameGenerationModel = 'ollama:llama3.2';
  let availableModels = []; // Models fetched from API

  // Custom prompt state
  const DEFAULT_FILENAME_PROMPT = `Generate a short, descriptive filename for this {content_type}.
Requirements:
- 3-6 words maximum
- Lowercase only
- Use hyphens between words
- No file extension
- Filesystem-safe (no special characters)
- Descriptive of the main topic

Content:
{content}

Return ONLY the filename, nothing else.`;

  let customPrompt = '';
  let showPromptEditor = false;
  let editingPrompt = ''; // Working copy while editing

  $: isAdmin = $currentUser?.role === 'admin';
  $: allSections = isAdmin ? [...sections, ...adminSections] : sections;

  onMount(() => {
    // Set token getter for API
    api.setTokenGetter(() => auth.getToken());

    // Load preferences from localStorage
    const savedLlmFilenames = localStorage.getItem('mentat_enable_llm_filenames');
    if (savedLlmFilenames !== null) {
      enableLlmFilenames = savedLlmFilenames === 'true';
    }
    const savedFilenameModel = localStorage.getItem('mentat_filename_model');
    if (savedFilenameModel) {
      filenameGenerationModel = savedFilenameModel;
    }

    // Load model configuration from localStorage
    const savedOllamaUrl = localStorage.getItem('mentat_ollama_url');
    if (savedOllamaUrl) {
      ollamaUrl = savedOllamaUrl;
    }

    // Load custom prompt from localStorage
    const savedPrompt = localStorage.getItem('mentat_filename_prompt');
    if (savedPrompt) {
      customPrompt = savedPrompt;
    }
  });

  $: if (show && $currentUser) {
    displayName = $currentUser.display_name || '';
    email = $currentUser.email || '';
    loadSectionData(activeSection);
  }

  async function loadSectionData(section) {
    error = '';
    loading = true;

    try {
      switch (section) {
        case 'models':
        case 'environment':
          apiKeys = await api.getApiKeys();
          break;
        case 'preferences':
          // Fetch available models for filename generation
          try {
            const response = await fetch(`${api.baseURL}/chat/models`);
            if (response.ok) {
              const data = await response.json();
              // Filter to show only Ollama models and free OpenRouter models
              availableModels = (data.models || []).filter(m =>
                m.provider === 'ollama' ||
                (m.provider === 'openrouter' && m.id.includes(':free'))
              );
              // Validate saved model - if not available, select first Ollama model
              if (availableModels.length > 0) {
                const savedModel = availableModels.find(m => m.id === filenameGenerationModel);
                if (!savedModel) {
                  const firstOllama = availableModels.find(m => m.provider === 'ollama');
                  filenameGenerationModel = firstOllama?.id || availableModels[0].id;
                  localStorage.setItem('mentat_filename_model', filenameGenerationModel);
                }
              }
            }
          } catch (e) {
            console.error('Failed to fetch models:', e);
          }
          break;
        case 'users':
          if (isAdmin) {
            users = await api.listUsers();
            invites = await api.listInvites();
          }
          break;
      }
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  function close() {
    show = false;
    dispatch('close');
  }

  function selectSection(id) {
    activeSection = id;
    error = '';
    success = '';
    loadSectionData(id);
  }

  // Profile handlers
  async function updateProfile() {
    error = '';
    success = '';
    loading = true;

    try {
      await auth.updateProfile({ display_name: displayName, email });
      success = 'Profile updated';
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function changePassword() {
    error = '';
    success = '';

    if (newPassword !== confirmPassword) {
      error = 'Passwords do not match';
      return;
    }

    if (newPassword.length < 8) {
      error = 'Password must be at least 8 characters';
      return;
    }

    loading = true;

    try {
      await auth.changePassword(currentPassword, newPassword);
      success = 'Password changed';
      currentPassword = '';
      newPassword = '';
      confirmPassword = '';
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  // API Keys handlers
  async function updateApiKey(provider) {
    const key = newApiKeys[provider];
    if (!key) return;

    error = '';
    loading = true;

    try {
      await api.updateApiKeys({ [provider]: key });
      apiKeys = await api.getApiKeys();
      newApiKeys[provider] = '';
      success = `${provider} key updated`;
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  // Admin handlers
  async function createInvite() {
    error = '';
    loading = true;

    try {
      await api.createInvite(inviteEmail || null);
      invites = await api.listInvites();
      inviteEmail = '';
      success = 'Invite created';
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function deleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user?')) return;

    error = '';
    loading = true;

    try {
      await api.deleteUser(userId);
      users = await api.listUsers();
      success = 'User deleted';
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  function handleLogout() {
    auth.logout();
    close();
  }

  // Prompt editor handlers
  function openPromptEditor() {
    editingPrompt = customPrompt || DEFAULT_FILENAME_PROMPT;
    showPromptEditor = true;
  }

  function savePrompt() {
    customPrompt = editingPrompt;
    localStorage.setItem('mentat_filename_prompt', customPrompt);
    showPromptEditor = false;
  }

  function resetPromptToDefault() {
    editingPrompt = DEFAULT_FILENAME_PROMPT;
  }

  function cancelPromptEdit() {
    showPromptEditor = false;
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') close();
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if show}
  <div class="modal-overlay" on:click={close} on:keydown={handleKeydown} role="button" tabindex="0">
    <div class="modal" on:click|stopPropagation role="dialog" aria-modal="true">
      <div class="modal-header">
        <h2>Settings</h2>
        <button class="close-btn" on:click={close} aria-label="Close">×</button>
      </div>

      <div class="modal-body">
        <!-- Sidebar -->
        <div class="sidebar">
          {#each allSections as section}
            <button
              class="section-btn"
              class:active={activeSection === section.id}
              on:click={() => selectSection(section.id)}
            >
              <span class="icon">{section.icon}</span>
              {section.label}
            </button>
          {/each}

          <div class="sidebar-footer">
            <button class="logout-btn" on:click={handleLogout}>
              Logout
            </button>
          </div>
        </div>

        <!-- Content -->
        <div class="content">
          {#if error}
            <div class="error">{error}</div>
          {/if}
          {#if success}
            <div class="success">{success}</div>
          {/if}

          {#if activeSection === 'profile'}
            <h3>Profile</h3>
            <div class="form-group">
              <label for="displayName">Display Name</label>
              <input id="displayName" type="text" bind:value={displayName} disabled={loading} />
            </div>
            <div class="form-group">
              <label for="email">Email</label>
              <input id="email" type="email" bind:value={email} disabled={loading} />
            </div>
            <button class="primary-btn" on:click={updateProfile} disabled={loading}>
              Save Profile
            </button>

            <hr />

            <h3>Change Password</h3>
            <div class="form-group">
              <label for="currentPassword">Current Password</label>
              <input id="currentPassword" type="password" bind:value={currentPassword} disabled={loading} />
            </div>
            <div class="form-group">
              <label for="newPassword">New Password</label>
              <input id="newPassword" type="password" bind:value={newPassword} disabled={loading} />
            </div>
            <div class="form-group">
              <label for="confirmPassword">Confirm Password</label>
              <input id="confirmPassword" type="password" bind:value={confirmPassword} disabled={loading} />
            </div>
            <button class="primary-btn" on:click={changePassword} disabled={loading}>
              Change Password
            </button>

          {:else if activeSection === 'models'}
            <h3>Model API Keys</h3>
            <p class="description">Configure API keys for AI model providers.</p>

            {#each apiKeys.filter(k => k.provider !== 'youtube') as key}
              <div class="api-key-row">
                <div class="key-info">
                  <span class="provider">{key.provider}</span>
                  {#if key.configured}
                    <span class="status configured">Configured</span>
                  {:else}
                    <span class="status not-configured">Not configured</span>
                  {/if}
                </div>
                <div class="key-input">
                  <input
                    type="password"
                    placeholder="Enter new key..."
                    bind:value={newApiKeys[key.provider]}
                    disabled={loading}
                  />
                  <button
                    class="small-btn"
                    on:click={() => updateApiKey(key.provider)}
                    disabled={loading || !newApiKeys[key.provider]}
                  >
                    {key.configured ? 'Update' : 'Add'}
                  </button>
                </div>
              </div>
            {/each}

            <hr />

            <h3>Ollama Configuration</h3>
            <p class="description">Ollama runs locally and doesn't require an API key.</p>

            <div class="form-group">
              <label for="ollamaUrl">Ollama URL</label>
              <input
                id="ollamaUrl"
                type="text"
                bind:value={ollamaUrl}
                on:change={() => localStorage.setItem('mentat_ollama_url', ollamaUrl)}
                placeholder="http://localhost:11434"
              />
            </div>

          {:else if activeSection === 'environment'}
            <h3>Environment Variables</h3>
            <p class="description">Configure API keys for external services.</p>

            {#each apiKeys.filter(k => k.provider === 'youtube') as key}
              <div class="api-key-row">
                <div class="key-info">
                  <span class="provider">YouTube Data API</span>
                  {#if key.configured}
                    <span class="status configured">Configured</span>
                  {:else}
                    <span class="status not-configured">Not configured</span>
                  {/if}
                </div>
                <div class="key-input">
                  <input
                    type="password"
                    placeholder="Enter YouTube API key..."
                    bind:value={newApiKeys[key.provider]}
                    disabled={loading}
                  />
                  <button
                    class="small-btn"
                    on:click={() => updateApiKey(key.provider)}
                    disabled={loading || !newApiKeys[key.provider]}
                  >
                    {key.configured ? 'Update' : 'Add'}
                  </button>
                </div>
              </div>
            {/each}

          {:else if activeSection === 'preferences'}
            <h3>Export Settings</h3>
            <p class="description">Configure how conversations and messages are exported.</p>

            <div class="preference-row">
              <div class="preference-info">
                <span class="preference-label">AI-generated filenames</span>
                <span class="preference-description">Use an LLM to generate descriptive filenames when exporting</span>
              </div>
              <label class="toggle">
                <input
                  type="checkbox"
                  bind:checked={enableLlmFilenames}
                  on:change={() => localStorage.setItem('mentat_enable_llm_filenames', enableLlmFilenames)}
                />
                <span class="slider"></span>
              </label>
            </div>

            {#if enableLlmFilenames}
              <div class="preference-subgroup">
                <div class="preference-row sub">
                  <div class="preference-info">
                    <span class="preference-label">Filename generation model</span>
                    <span class="preference-description">Model used to generate export filenames</span>
                  </div>
                  <select
                    class="model-select"
                    bind:value={filenameGenerationModel}
                    on:change={() => localStorage.setItem('mentat_filename_model', filenameGenerationModel)}
                  >
                    {#if availableModels.filter(m => m.provider === 'ollama').length > 0}
                      <optgroup label="Local (Ollama)">
                        {#each availableModels.filter(m => m.provider === 'ollama') as model}
                          <option value={model.id}>{model.name}</option>
                        {/each}
                      </optgroup>
                    {/if}
                    {#if availableModels.filter(m => m.provider === 'openrouter').length > 0}
                      <optgroup label="OpenRouter (Free)">
                        {#each availableModels.filter(m => m.provider === 'openrouter') as model}
                          <option value={model.id}>{model.name}</option>
                        {/each}
                      </optgroup>
                    {/if}
                    {#if availableModels.length === 0}
                      <option value="" disabled>Loading models...</option>
                    {/if}
                  </select>
                </div>

                <div class="preference-row sub">
                  <div class="preference-info">
                    <span class="preference-label">Custom prompt</span>
                    <span class="preference-description">
                      {customPrompt ? 'Using custom prompt' : 'Using default prompt'}
                    </span>
                  </div>
                  <button class="secondary-btn" on:click={openPromptEditor}>
                    Customize
                  </button>
                </div>
              </div>
            {/if}

          {:else if activeSection === 'users' && isAdmin}
            <h3>Users</h3>
            <div class="users-list">
              {#each users as user}
                <div class="user-row">
                  <div class="user-info">
                    <span class="user-name">{user.display_name}</span>
                    <span class="user-email">{user.email}</span>
                    <span class="user-role" class:admin={user.role === 'admin'}>{user.role}</span>
                  </div>
                  {#if user.id !== $currentUser?.id}
                    <button class="danger-btn small-btn" on:click={() => deleteUser(user.id)}>
                      Delete
                    </button>
                  {/if}
                </div>
              {/each}
            </div>

            <hr />

            <h3>Invites</h3>
            <div class="form-group inline">
              <input
                type="email"
                placeholder="Email (optional)"
                bind:value={inviteEmail}
                disabled={loading}
              />
              <button class="primary-btn" on:click={createInvite} disabled={loading}>
                Create Invite
              </button>
            </div>

            {#if invites.length > 0}
              <div class="invites-list">
                {#each invites as invite}
                  <div class="invite-row" class:used={invite.used}>
                    <span class="invite-token">{invite.token.slice(0, 12)}...</span>
                    {#if invite.email}
                      <span class="invite-email">for {invite.email}</span>
                    {/if}
                    <span class="invite-status">{invite.used ? 'Used' : 'Active'}</span>
                  </div>
                {/each}
              </div>
            {/if}

          {:else if activeSection === 'system' && isAdmin}
            <h3>System Configuration</h3>
            <p class="description">System settings. Coming soon...</p>
          {/if}
        </div>
      </div>
    </div>
  </div>

  <!-- Prompt Editor Sub-Modal -->
  {#if showPromptEditor}
    <div class="sub-modal-overlay" on:click={cancelPromptEdit} on:keydown={(e) => e.key === 'Escape' && cancelPromptEdit()} role="button" tabindex="0">
      <div class="sub-modal" on:click|stopPropagation role="dialog" aria-modal="true">
        <div class="sub-modal-header">
          <h3>Customize Filename Prompt</h3>
          <button class="close-btn" on:click={cancelPromptEdit} aria-label="Close">×</button>
        </div>
        <div class="sub-modal-body">
          <p class="prompt-help">
            Use <code>{'{content_type}'}</code> for "message" or "conversation" and <code>{'{content}'}</code> for the content snippet.
          </p>
          <textarea
            class="prompt-textarea"
            bind:value={editingPrompt}
            rows="14"
            placeholder="Enter your custom prompt..."
          ></textarea>
        </div>
        <div class="sub-modal-footer">
          <button class="secondary-btn" on:click={resetPromptToDefault}>
            Reset to Default
          </button>
          <div class="footer-right">
            <button class="secondary-btn" on:click={cancelPromptEdit}>
              Cancel
            </button>
            <button class="primary-btn" on:click={savePrompt}>
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}
{/if}

<style>
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: #111;
    border: 1px solid #222;
    border-radius: 0.75rem;
    width: 90%;
    max-width: 800px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #222;
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.25rem;
  }

  .close-btn {
    background: none;
    border: none;
    color: #888;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0;
    line-height: 1;
  }

  .close-btn:hover {
    color: #e5e5e5;
  }

  .modal-body {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  .sidebar {
    width: 180px;
    border-right: 1px solid #222;
    padding: 0.5rem;
    display: flex;
    flex-direction: column;
  }

  .section-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.75rem 1rem;
    background: transparent;
    border: none;
    border-radius: 0.375rem;
    color: #888;
    font-size: 0.875rem;
    cursor: pointer;
    text-align: left;
  }

  .section-btn:hover {
    background: #1a1a1a;
    color: #e5e5e5;
  }

  .section-btn.active {
    background: #1a1a1a;
    color: #3b82f6;
  }

  .icon {
    font-size: 1rem;
  }

  .sidebar-footer {
    margin-top: auto;
    padding-top: 0.5rem;
    border-top: 1px solid #222;
  }

  .logout-btn {
    width: 100%;
    padding: 0.75rem 1rem;
    background: transparent;
    border: none;
    border-radius: 0.375rem;
    color: #ef4444;
    font-size: 0.875rem;
    cursor: pointer;
    text-align: left;
  }

  .logout-btn:hover {
    background: rgba(239, 68, 68, 0.1);
  }

  .content {
    flex: 1;
    padding: 1.5rem;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: #333 #1a1a1a;
  }

  .content::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  .content::-webkit-scrollbar-track {
    background: #1a1a1a;
  }

  .content::-webkit-scrollbar-thumb {
    background: #333;
    border-radius: 4px;
  }

  .content::-webkit-scrollbar-thumb:hover {
    background: #444;
  }

  .content h3 {
    margin: 0 0 1rem 0;
    font-size: 1rem;
    color: #e5e5e5;
  }

  .description {
    color: #666;
    font-size: 0.875rem;
    margin-bottom: 1rem;
  }

  .error {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #ef4444;
    padding: 0.75rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    font-size: 0.875rem;
  }

  .success {
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.3);
    color: #22c55e;
    padding: 0.75rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    font-size: 0.875rem;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  .form-group.inline {
    display: flex;
    gap: 0.5rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    color: #888;
  }

  input {
    width: 100%;
    padding: 0.625rem 0.875rem;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 0.375rem;
    color: #e5e5e5;
    font-size: 0.875rem;
  }

  input:focus {
    outline: none;
    border-color: #3b82f6;
  }

  input:disabled {
    opacity: 0.6;
  }

  hr {
    border: none;
    border-top: 1px solid #222;
    margin: 1.5rem 0;
  }

  .primary-btn {
    padding: 0.625rem 1rem;
    background: #3b82f6;
    border: none;
    border-radius: 0.375rem;
    color: white;
    font-size: 0.875rem;
    cursor: pointer;
  }

  .primary-btn:hover:not(:disabled) {
    background: #2563eb;
  }

  .primary-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .small-btn {
    padding: 0.375rem 0.75rem;
    font-size: 0.75rem;
  }

  .danger-btn {
    background: transparent;
    border: 1px solid #ef4444;
    color: #ef4444;
    border-radius: 0.375rem;
    cursor: pointer;
  }

  .danger-btn:hover {
    background: rgba(239, 68, 68, 0.1);
  }

  /* API Keys */
  .api-key-row {
    padding: 0.75rem 0;
    border-bottom: 1px solid #222;
  }

  .key-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
  }

  .provider {
    font-weight: 500;
    text-transform: capitalize;
  }

  .status {
    font-size: 0.75rem;
    padding: 0.125rem 0.5rem;
    border-radius: 0.25rem;
  }

  .status.configured {
    background: rgba(34, 197, 94, 0.2);
    color: #22c55e;
  }

  .status.not-configured {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }

  .masked {
    color: #666;
    font-family: monospace;
    font-size: 0.75rem;
  }

  .key-input {
    display: flex;
    gap: 0.5rem;
  }

  /* Preferences */
  .preference-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 0;
    border-bottom: 1px solid #222;
  }

  .preference-row.sub {
    border-bottom: none;
    padding: 0.5rem 0 0.5rem 1rem;
  }

  .preference-subgroup {
    border-bottom: 1px solid #222;
    padding-bottom: 0.5rem;
  }

  .preference-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .preference-label {
    font-weight: 500;
    color: #e5e5e5;
  }

  .preference-description {
    font-size: 0.75rem;
    color: #666;
  }

  .toggle {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
    flex-shrink: 0;
  }

  .toggle input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #333;
    transition: 0.2s;
    border-radius: 24px;
  }

  .slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: #666;
    transition: 0.2s;
    border-radius: 50%;
  }

  .toggle input:checked + .slider {
    background-color: #3b82f6;
  }

  .toggle input:checked + .slider:before {
    transform: translateX(20px);
    background-color: white;
  }

  .model-select {
    padding: 0.5rem 0.75rem;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 0.375rem;
    color: #e5e5e5;
    font-size: 0.875rem;
    min-width: 160px;
  }

  .model-select:focus {
    outline: none;
    border-color: #3b82f6;
  }

  .model-select optgroup {
    background: #1a1a1a;
    color: #888;
  }

  .model-select option {
    background: #1a1a1a;
    color: #e5e5e5;
    padding: 0.5rem;
  }

  /* Users */
  .users-list, .invites-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .user-row, .invite-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    background: #1a1a1a;
    border-radius: 0.375rem;
  }

  .user-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .user-name {
    font-weight: 500;
  }

  .user-email {
    color: #666;
    font-size: 0.875rem;
  }

  .user-role {
    font-size: 0.75rem;
    padding: 0.125rem 0.5rem;
    background: #333;
    border-radius: 0.25rem;
  }

  .user-role.admin {
    background: rgba(59, 130, 246, 0.2);
    color: #3b82f6;
  }

  .invite-row.used {
    opacity: 0.5;
  }

  .invite-token {
    font-family: monospace;
    font-size: 0.875rem;
  }

  .invite-email {
    color: #666;
    font-size: 0.875rem;
  }

  .invite-status {
    font-size: 0.75rem;
    padding: 0.125rem 0.5rem;
    background: #333;
    border-radius: 0.25rem;
  }

  /* Secondary button */
  .secondary-btn {
    padding: 0.5rem 1rem;
    background: transparent;
    border: 1px solid #444;
    border-radius: 0.375rem;
    color: #e5e5e5;
    font-size: 0.875rem;
    cursor: pointer;
  }

  .secondary-btn:hover {
    background: #222;
    border-color: #555;
  }

  /* Sub-modal (Prompt Editor) */
  .sub-modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1100;
  }

  .sub-modal {
    background: #111;
    border: 1px solid #333;
    border-radius: 0.75rem;
    width: 90%;
    max-width: 600px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
  }

  .sub-modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #222;
  }

  .sub-modal-header h3 {
    margin: 0;
    font-size: 1.125rem;
    color: #e5e5e5;
  }

  .sub-modal-body {
    padding: 1.5rem;
    overflow-y: auto;
  }

  .prompt-help {
    font-size: 0.875rem;
    color: #888;
    margin-bottom: 1rem;
  }

  .prompt-help code {
    background: #222;
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    font-family: monospace;
    color: #3b82f6;
  }

  .prompt-textarea {
    width: 100%;
    padding: 0.75rem;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 0.375rem;
    color: #e5e5e5;
    font-family: monospace;
    font-size: 0.8125rem;
    line-height: 1.5;
    resize: vertical;
    min-height: 200px;
  }

  .prompt-textarea:focus {
    outline: none;
    border-color: #3b82f6;
  }

  .sub-modal-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-top: 1px solid #222;
  }

  .footer-right {
    display: flex;
    gap: 0.5rem;
  }
</style>
