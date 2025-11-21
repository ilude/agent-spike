<script>
  // Global layout - applied to all pages
</script>

<slot />

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: #0a0a0a;
    color: #e5e5e5;
  }

  :global(*) {
    box-sizing: border-box;
  }
</style>
