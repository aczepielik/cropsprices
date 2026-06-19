<!--
  Sidebar.svelte — Tab navigation between Snapshot and Heatmap views.

  This is a simple component that shows two buttons. The active tab gets
  a green left border (accent color) to match the mock6.html design.

  PROPS (data passed from parent):
  - activeView: which tab is currently selected
  - onFilterChange: callback function to notify parent of changes

  $bindable() means the parent can both read AND write activeView.
  Without $bindable(), the parent could only read it.
-->

<script lang="ts">
  import type { ViewMode } from '../lib/types';

  let { activeView = $bindable(), onFilterChange, closeSidebar }: {
    activeView: ViewMode;
    onFilterChange: () => void;
    closeSidebar?: () => void;
  } = $props();

  const tabs: { id: ViewMode; label: string }[] = [
    { id: 'snapshot', label: 'Widok Aktualny (Snapshot)' },
    { id: 'heatmap', label: 'Mapa Cieplna (Heatmap)' },
  ];

  function selectTab(id: ViewMode) {
    activeView = id;
    closeSidebar?.();
  }
</script>

<aside class="sidebar">
  <div class="sidebar-top">
    <span class="meta-label">Tryb Analizy</span>
    {#if closeSidebar}
      <button class="close-btn" onclick={closeSidebar} aria-label="Zamknij menu">&times;</button>
    {/if}
  </div>
  <nav class="workspace-nav">
    <!-- {#each} is Svelte's loop syntax — like .map() in JavaScript -->
    {#each tabs as tab}
      <!-- class:active = Svelte directive: adds the "active" CSS class when the expression is true -->
      <button
        class="tab-item"
        class:active={activeView === tab.id}
        onclick={() => selectTab(tab.id)}
      >
        {tab.label}
      </button>
    {/each}
  </nav>
</aside>

<style>
  .sidebar { width: 300px; flex-shrink: 0; }

  .meta-label {
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--muted); margin-bottom: 6px; display: block;
  }

  .workspace-nav {
    display: flex; flex-direction: column;
    border: 1px solid var(--rule); background-color: var(--surface);
    margin-bottom: 24px;
  }

  .tab-item {
    display: block; padding: 14px 16px; text-align: left;
    background: none; border: none; border-bottom: 1px solid var(--rule);
    color: var(--ink); font-weight: 500; font-size: 13px;
    cursor: pointer; transition: background-color 0.15s;
  }
  .tab-item:last-child { border-bottom: none; }
  .tab-item:hover { background-color: var(--soft); }
  .tab-item.active {
    background-color: var(--soft); border-left: 4px solid var(--green);
    font-weight: 600; padding-left: 12px;
  }

  .sidebar-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  .close-btn {
    display: none;
    background: none;
    border: none;
    font-size: 24px;
    color: var(--muted);
    cursor: pointer;
    padding: 0 4px;
    line-height: 1;
  }

  @media (max-width: 768px) {
    .meta-label { font-size: 10px; }
    .tab-item { font-size: 14px; padding: 12px 14px; }
    .workspace-nav { margin-bottom: 16px; }
    .close-btn { display: block; }
    .sidebar-top { margin-bottom: 12px; }
  }
</style>
