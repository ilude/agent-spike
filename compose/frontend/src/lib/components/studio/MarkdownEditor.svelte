<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { EditorView, basicSetup } from 'codemirror';
  import { EditorState, Compartment } from '@codemirror/state';
  import { markdown } from '@codemirror/lang-markdown';
  import { oneDark } from '@codemirror/theme-one-dark';
  import { keymap } from '@codemirror/view';
  import { autocompletion, CompletionContext } from '@codemirror/autocomplete';
  import { api } from '$lib/api.js';
  import { updateNoteInTabs, currentVault } from '$lib/stores/studio.js';

  export let note;

  const dispatch = createEventDispatcher();

  let editorContainer;
  let editorView;
  let content = '';
  let isDirty = false;
  let saving = false;
  let previewMode = false;
  let previewHtml = '';
  let saveTimeout;

  // Wiki-link autocomplete
  async function wikiLinkCompletions(context) {
    // Check if we're inside [[ ]]
    const before = context.matchBefore(/\[\[[\w\s-]*/);
    if (!before) return null;

    // Get search text after [[
    const searchText = before.text.slice(2);

    try {
      // Search notes in current vault
      const results = await api.searchNotes($currentVault.id, searchText);

      return {
        from: before.from + 2, // Start after [[
        options: results.map(note => ({
          label: note.title || note.path,
          type: 'text',
          apply: `${note.title || note.path}]]`,
          detail: note.path
        })),
        validFor: /^[\w\s-]*$/
      };
    } catch (e) {
      console.error('Failed to fetch completions:', e);
      return null;
    }
  }

  // Create editor
  onMount(() => {
    content = note?.content || '';

    const state = EditorState.create({
      doc: content,
      extensions: [
        basicSetup,
        markdown(),
        oneDark,
        EditorView.lineWrapping,
        autocompletion({
          override: [wikiLinkCompletions]
        }),
        keymap.of([
          {
            key: 'Mod-s',
            run: () => {
              saveNote();
              return true;
            }
          }
        ]),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            const newContent = update.state.doc.toString();
            if (newContent !== content) {
              content = newContent;
              isDirty = true;
              scheduleAutoSave();
            }
          }
        })
      ]
    });

    editorView = new EditorView({
      state,
      parent: editorContainer
    });
  });

  onDestroy(() => {
    if (editorView) {
      editorView.destroy();
    }
    if (saveTimeout) {
      clearTimeout(saveTimeout);
    }
  });

  // Update editor when note changes
  $: if (editorView && note?.id) {
    const currentContent = editorView.state.doc.toString();
    if (note.content !== currentContent && !isDirty) {
      editorView.dispatch({
        changes: {
          from: 0,
          to: currentContent.length,
          insert: note.content || ''
        }
      });
      content = note.content || '';
    }
  }

  function scheduleAutoSave() {
    if (saveTimeout) {
      clearTimeout(saveTimeout);
    }
    saveTimeout = setTimeout(() => {
      saveNote();
    }, 2000); // Auto-save after 2s of inactivity
  }

  async function saveNote() {
    if (!isDirty || saving || !note?.id) return;

    saving = true;
    try {
      const updated = await api.updateNote(note.id, { content });
      isDirty = false;
      updateNoteInTabs(updated);
    } catch (e) {
      console.error('Failed to save:', e);
    } finally {
      saving = false;
    }
  }

  function togglePreview() {
    previewMode = !previewMode;
    if (previewMode) {
      renderPreview();
    }
  }

  function renderPreview() {
    // Simple markdown to HTML (basic implementation)
    let html = content;

    // Headings
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Bold and italic
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Wiki links
    html = html.replace(/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g, (match, target, display) => {
      const label = display || target;
      return `<a href="#" class="wiki-link" data-target="${target}">${label}</a>`;
    });

    // Regular links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

    // Code blocks
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Lists
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

    // Paragraphs
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p>(<h[1-6]>)/g, '$1');
    html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
    html = html.replace(/<p>(<ul>)/g, '$1');
    html = html.replace(/(<\/ul>)<\/p>/g, '$1');
    html = html.replace(/<p>(<pre>)/g, '$1');
    html = html.replace(/(<\/pre>)<\/p>/g, '$1');

    previewHtml = html;
  }

  function getStatusText() {
    if (saving) return 'Saving...';
    if (isDirty) return 'Unsaved changes';
    return 'Saved';
  }
</script>

<div class="editor-wrapper">
  <div class="editor-toolbar">
    <div class="toolbar-left">
      <span class="note-title">{note?.title || 'Untitled'}</span>
      <span class="note-path">{note?.path}</span>
    </div>
    <div class="toolbar-right">
      <span class="save-status" class:dirty={isDirty} class:saving={saving}>
        {getStatusText()}
      </span>
      <button
        class="toolbar-btn"
        class:active={previewMode}
        on:click={togglePreview}
        title="Toggle Preview"
      >
        {previewMode ? '✏️ Edit' : '👁️ Preview'}
      </button>
      <button
        class="toolbar-btn primary"
        on:click={saveNote}
        disabled={!isDirty || saving}
      >
        Save
      </button>
    </div>
  </div>

  <div class="editor-body">
    {#if previewMode}
      <div class="preview-container">
        {@html previewHtml}
      </div>
    {:else}
      <div class="codemirror-container" bind:this={editorContainer}></div>
    {/if}
  </div>
</div>

<style>
  .editor-wrapper {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #0a0a0a;
  }

  .editor-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 1rem;
    background: #1a1a1a;
    border-bottom: 1px solid #2a2a2a;
    flex-shrink: 0;
  }

  .toolbar-left {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    overflow: hidden;
  }

  .note-title {
    font-weight: 600;
    color: #e5e5e5;
    white-space: nowrap;
  }

  .note-path {
    font-size: 0.75rem;
    color: #666;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
  }

  .save-status {
    font-size: 0.75rem;
    color: #10b981;
    transition: color 0.2s;
  }

  .save-status.dirty {
    color: #f59e0b;
  }

  .save-status.saving {
    color: #3b82f6;
  }

  .toolbar-btn {
    padding: 0.375rem 0.75rem;
    background: #2a2a2a;
    border: none;
    border-radius: 4px;
    color: #a0a0a0;
    font-size: 0.8125rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .toolbar-btn:hover:not(:disabled) {
    background: #3a3a3a;
    color: #e5e5e5;
  }

  .toolbar-btn.active {
    background: #3b82f6;
    color: white;
  }

  .toolbar-btn.primary {
    background: #3b82f6;
    color: white;
  }

  .toolbar-btn.primary:hover:not(:disabled) {
    background: #2563eb;
  }

  .toolbar-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .editor-body {
    flex: 1;
    overflow: hidden;
  }

  .codemirror-container {
    height: 100%;
  }

  /* CodeMirror styling overrides */
  .codemirror-container :global(.cm-editor) {
    height: 100%;
    font-size: 14px;
  }

  .codemirror-container :global(.cm-scroller) {
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  }

  .codemirror-container :global(.cm-content) {
    padding: 1rem;
  }

  .codemirror-container :global(.cm-gutters) {
    background: #1a1a1a;
    border-right: 1px solid #2a2a2a;
  }

  /* Autocomplete styling */
  .codemirror-container :global(.cm-tooltip-autocomplete) {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 4px !important;
  }

  .codemirror-container :global(.cm-tooltip-autocomplete ul li) {
    padding: 4px 8px !important;
    color: #e5e5e5;
  }

  .codemirror-container :global(.cm-tooltip-autocomplete ul li[aria-selected="true"]) {
    background: #3b82f6 !important;
    color: white;
  }

  /* Preview styling */
  .preview-container {
    height: 100%;
    overflow-y: auto;
    padding: 2rem;
    color: #e5e5e5;
    line-height: 1.7;
  }

  .preview-container :global(h1) {
    font-size: 2rem;
    margin: 0 0 1rem 0;
    color: #fff;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.5rem;
  }

  .preview-container :global(h2) {
    font-size: 1.5rem;
    margin: 1.5rem 0 0.75rem 0;
    color: #fff;
  }

  .preview-container :global(h3) {
    font-size: 1.25rem;
    margin: 1.25rem 0 0.5rem 0;
    color: #fff;
  }

  .preview-container :global(p) {
    margin: 0 0 1rem 0;
  }

  .preview-container :global(code) {
    background: #2a2a2a;
    padding: 0.125rem 0.375rem;
    border-radius: 3px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.875em;
  }

  .preview-container :global(pre) {
    background: #1a1a1a;
    padding: 1rem;
    border-radius: 6px;
    overflow-x: auto;
    margin: 1rem 0;
  }

  .preview-container :global(pre code) {
    background: transparent;
    padding: 0;
  }

  .preview-container :global(ul) {
    margin: 0 0 1rem 0;
    padding-left: 1.5rem;
  }

  .preview-container :global(li) {
    margin: 0.25rem 0;
  }

  .preview-container :global(a) {
    color: #3b82f6;
    text-decoration: none;
  }

  .preview-container :global(a:hover) {
    text-decoration: underline;
  }

  .preview-container :global(.wiki-link) {
    color: #10b981;
    background: rgba(16, 185, 129, 0.1);
    padding: 0.125rem 0.375rem;
    border-radius: 3px;
  }

  .preview-container :global(.wiki-link:hover) {
    background: rgba(16, 185, 129, 0.2);
  }

  .preview-container :global(strong) {
    color: #fff;
  }

  .preview-container :global(em) {
    font-style: italic;
    color: #ccc;
  }
</style>
