<script>
  // Global layout - applied to all pages
</script>

<slot />

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
</style>
