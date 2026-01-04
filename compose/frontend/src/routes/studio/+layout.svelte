<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
</script>

<div class="studio-shell">
  <header class="studio-header">
    <a href="/" class="logo">Mentat</a>
    <nav class="studio-nav">
      <a href="/" class="nav-link">Dashboard</a>
      <a href="/chat" class="nav-link">Chat</a>
      <a href="/studio" class="nav-link active">Studio</a>
    </nav>
  </header>

  <main class="studio-main">
    <slot />
  </main>
</div>

<style>
  .studio-shell {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: #0a0a0a;
  }

  .studio-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 1rem;
    background: #1a1a1a;
    border-bottom: 1px solid #2a2a2a;
    height: 48px;
    flex-shrink: 0;
  }

  .logo {
    font-size: 1.25rem;
    font-weight: 700;
    color: #3b82f6;
    text-decoration: none;
  }

  .logo:hover {
    color: #60a5fa;
  }

  .studio-nav {
    display: flex;
    gap: 0.5rem;
  }

  .nav-link {
    color: #888;
    text-decoration: none;
    padding: 0.375rem 0.75rem;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .nav-link:hover {
    color: #fff;
    background: #2a2a2a;
  }

  .nav-link.active {
    color: #3b82f6;
    background: rgba(59, 130, 246, 0.1);
  }

  .studio-main {
    flex: 1;
    overflow: hidden;
    display: flex;
  }
</style>
