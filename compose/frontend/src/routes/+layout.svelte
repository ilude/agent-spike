<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { auth, isAuthenticated } from '$lib/stores/auth.js';

  // Public routes that don't require authentication
  const publicRoutes = ['/login', '/register'];

  let initialized = false;

  onMount(async () => {
    await auth.initialize();
    initialized = true;
  });

  // Watch for auth changes and redirect if needed
  $: if (initialized && !$isAuthenticated && !publicRoutes.includes($page.url.pathname)) {
    goto('/login');
  }
</script>

{#if !initialized}
  <div class="loading-screen">
    <div class="spinner"></div>
  </div>
{:else}
  <slot />
{/if}

<style>
  :global(html, body) {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow-x: hidden;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: #0a0a0a;
    color: #e5e5e5;
  }

  :global(*) {
    box-sizing: border-box;
  }

  .loading-screen {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    background: #0a0a0a;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #333;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
