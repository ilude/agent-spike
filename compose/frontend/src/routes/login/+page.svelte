<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth, isAuthenticated, isLoading, authError } from '$lib/stores/auth.js';

  let email = '';
  let password = '';
  let displayName = '';
  let inviteToken = '';
  let isRegisterMode = false;
  let registrationStatus = null;
  let localError = '';

  onMount(async () => {
    // If already authenticated, redirect to chat
    if ($isAuthenticated) {
      goto('/chat');
      return;
    }

    // Check registration status
    try {
      registrationStatus = await auth.checkRegistration();

      // If first user, switch to register mode
      if (registrationStatus.is_first_user) {
        isRegisterMode = true;
      }
    } catch (err) {
      localError = 'Could not connect to server';
    }
  });

  async function handleSubmit() {
    localError = '';

    try {
      if (isRegisterMode) {
        await auth.register(email, password, displayName || null, inviteToken || null);
      } else {
        await auth.login(email, password);
      }
      goto('/chat');
    } catch (err) {
      localError = err.message;
    }
  }

  function toggleMode() {
    isRegisterMode = !isRegisterMode;
    localError = '';
  }

  // Watch for auth errors
  $: error = localError || $authError;
</script>

<div class="login-container">
  <div class="login-card">
    <h1 class="logo">Mentat</h1>

    {#if registrationStatus?.is_first_user}
      <p class="first-user-notice">
        Welcome! Create the first account to become admin.
      </p>
    {/if}

    <h2>{isRegisterMode ? 'Create Account' : 'Sign In'}</h2>

    {#if error}
      <div class="error-message">{error}</div>
    {/if}

    <form on:submit|preventDefault={handleSubmit}>
      <div class="form-group">
        <label for="email">Email</label>
        <input
          type="email"
          id="email"
          bind:value={email}
          placeholder="you@example.com"
          required
          disabled={$isLoading}
        />
      </div>

      {#if isRegisterMode}
        <div class="form-group">
          <label for="displayName">Display Name (optional)</label>
          <input
            type="text"
            id="displayName"
            bind:value={displayName}
            placeholder="Your name"
            disabled={$isLoading}
          />
        </div>
      {/if}

      <div class="form-group">
        <label for="password">Password</label>
        <input
          type="password"
          id="password"
          bind:value={password}
          placeholder="••••••••"
          required
          disabled={$isLoading}
          minlength="8"
        />
      </div>

      {#if isRegisterMode && registrationStatus?.requires_invite}
        <div class="form-group">
          <label for="inviteToken">Invite Code</label>
          <input
            type="text"
            id="inviteToken"
            bind:value={inviteToken}
            placeholder="Enter your invite code"
            required
            disabled={$isLoading}
          />
        </div>
      {/if}

      <button type="submit" class="submit-btn" disabled={$isLoading}>
        {#if $isLoading}
          <span class="spinner-small"></span>
        {:else}
          {isRegisterMode ? 'Create Account' : 'Sign In'}
        {/if}
      </button>
    </form>

    {#if !registrationStatus?.is_first_user}
      <div class="toggle-mode">
        {#if isRegisterMode}
          Already have an account?
          <button type="button" on:click={toggleMode} disabled={$isLoading}>
            Sign In
          </button>
        {:else if registrationStatus?.is_open || registrationStatus?.requires_invite}
          Don't have an account?
          <button type="button" on:click={toggleMode} disabled={$isLoading}>
            Create Account
          </button>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .login-container {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 1rem;
    background: #0a0a0a;
  }

  .login-card {
    width: 100%;
    max-width: 400px;
    padding: 2rem;
    background: #111;
    border: 1px solid #222;
    border-radius: 0.75rem;
  }

  .logo {
    font-size: 2rem;
    font-weight: 700;
    text-align: center;
    margin: 0 0 0.5rem 0;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  h2 {
    font-size: 1.25rem;
    font-weight: 500;
    text-align: center;
    margin: 0 0 1.5rem 0;
    color: #888;
  }

  .first-user-notice {
    text-align: center;
    color: #22c55e;
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.3);
    border-radius: 0.5rem;
    padding: 0.75rem;
    margin-bottom: 1.5rem;
    font-size: 0.875rem;
  }

  .error-message {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #ef4444;
    padding: 0.75rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    font-size: 0.875rem;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    color: #888;
  }

  input {
    width: 100%;
    padding: 0.75rem 1rem;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 0.5rem;
    color: #e5e5e5;
    font-size: 1rem;
    transition: border-color 0.2s;
  }

  input:focus {
    outline: none;
    border-color: #3b82f6;
  }

  input:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  input::placeholder {
    color: #555;
  }

  .submit-btn {
    width: 100%;
    padding: 0.875rem;
    background: #3b82f6;
    border: none;
    border-radius: 0.5rem;
    color: white;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
    margin-top: 0.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  .submit-btn:hover:not(:disabled) {
    background: #2563eb;
  }

  .submit-btn:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .spinner-small {
    width: 18px;
    height: 18px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .toggle-mode {
    text-align: center;
    margin-top: 1.5rem;
    color: #666;
    font-size: 0.875rem;
  }

  .toggle-mode button {
    background: none;
    border: none;
    color: #3b82f6;
    cursor: pointer;
    font-size: 0.875rem;
    padding: 0;
    margin-left: 0.25rem;
  }

  .toggle-mode button:hover:not(:disabled) {
    text-decoration: underline;
  }

  .toggle-mode button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
</style>
