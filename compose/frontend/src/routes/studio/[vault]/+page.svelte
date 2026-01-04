<script>
  import { activeNote } from '$lib/stores/studio.js';
  import MarkdownEditor from '$lib/components/studio/MarkdownEditor.svelte';
</script>

<div class="editor-container">
  {#if $activeNote}
    <MarkdownEditor note={$activeNote} />
  {:else}
    <div class="empty-editor">
      <div class="empty-icon">📝</div>
      <h2>No note selected</h2>
      <p>Select a note from the file tree or create a new one</p>
      <div class="shortcuts">
        <div class="shortcut">
          <kbd>Ctrl</kbd> + <kbd>N</kbd>
          <span>New note</span>
        </div>
        <div class="shortcut">
          <kbd>Ctrl</kbd> + <kbd>P</kbd>
          <span>Quick open</span>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .editor-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .empty-editor {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #888;
    text-align: center;
    padding: 2rem;
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
    opacity: 0.5;
  }

  .empty-editor h2 {
    margin: 0 0 0.5rem 0;
    color: #ccc;
    font-size: 1.25rem;
  }

  .empty-editor p {
    margin: 0 0 2rem 0;
    color: #666;
  }

  .shortcuts {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .shortcut {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8125rem;
    color: #666;
  }

  kbd {
    padding: 0.25rem 0.5rem;
    background: #2a2a2a;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    font-family: inherit;
    font-size: 0.75rem;
    color: #ccc;
  }
</style>
