import { writable, derived } from 'svelte/store';

// Current vault
export const currentVault = writable(null);

// File tree from API
export const fileTree = writable([]);

// Open tabs (array of note objects)
export const openTabs = writable([]);

// Active tab (note id)
export const activeTabId = writable(null);

// Derived: active note object
export const activeNote = derived(
  [openTabs, activeTabId],
  ([$openTabs, $activeTabId]) => {
    return $openTabs.find(tab => tab.id === $activeTabId) || null;
  }
);

// Panel sizes (persisted to localStorage)
const defaultPanelSizes = { fileTree: 20, editor: 60, sidebar: 20 };

function createPanelSizes() {
  let initial = defaultPanelSizes;
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('studio-panel-sizes');
    if (saved) {
      try {
        initial = JSON.parse(saved);
      } catch {}
    }
  }

  const { subscribe, set, update } = writable(initial);

  return {
    subscribe,
    set: (value) => {
      if (typeof window !== 'undefined') {
        localStorage.setItem('studio-panel-sizes', JSON.stringify(value));
      }
      set(value);
    },
    update,
    reset: () => {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('studio-panel-sizes');
      }
      set(defaultPanelSizes);
    }
  };
}

export const panelSizes = createPanelSizes();

// Sidebar mode: 'backlinks' | 'suggestions' | 'outline'
export const sidebarMode = writable('backlinks');

// Tab management functions
export function openNote(note) {
  openTabs.update(tabs => {
    const existing = tabs.find(t => t.id === note.id);
    if (existing) {
      activeTabId.set(note.id);
      return tabs;
    }
    activeTabId.set(note.id);
    return [...tabs, note];
  });
}

export function closeTab(noteId) {
  openTabs.update(tabs => {
    const idx = tabs.findIndex(t => t.id === noteId);
    const newTabs = tabs.filter(t => t.id !== noteId);

    // If closing active tab, switch to adjacent tab
    activeTabId.update(current => {
      if (current === noteId && newTabs.length > 0) {
        const newIdx = Math.min(idx, newTabs.length - 1);
        return newTabs[newIdx].id;
      }
      return newTabs.length > 0 ? current : null;
    });

    return newTabs;
  });
}

export function closeAllTabs() {
  openTabs.set([]);
  activeTabId.set(null);
}

// Update a note in the tabs (after save)
export function updateNoteInTabs(updatedNote) {
  openTabs.update(tabs =>
    tabs.map(t => t.id === updatedNote.id ? updatedNote : t)
  );
}
