<!--
  Sidebar.svelte — Tab navigation between Snapshot and Heatmap views.

  Simplified: no collapse behavior, fixed 240px width.
  Dark active state matching the new mock design.
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

<span class="meta-label">Tryb Analizy</span>
<nav class="workspace-nav">
  {#each tabs as tab}
    <button
      class="tab-item"
      class:active={activeView === tab.id}
      onclick={() => selectTab(tab.id)}
    >
      {tab.label}
    </button>
  {/each}
</nav>

<style>
  .meta-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    display: block;
    margin-bottom: 10px;
  }

  .workspace-nav {
    display: flex;
    flex-direction: column;
    margin-bottom: 32px;
    gap: 6px;
  }

  .tab-item {
    display: block;
    width: 100%;
    text-align: left;
    padding: 12px 14px;
    background: none;
    border: none;
    border-radius: 6px;
    color: var(--ink);
    font-family: var(--font-sans);
    font-weight: 500;
    font-size: 13px;
    cursor: pointer;
    transition: background-color 0.12s ease;
  }

  .tab-item:hover {
    background-color: var(--hairline);
  }

  .tab-item.active {
    background-color: var(--active);
    color: var(--bg);
    font-weight: 600;
  }

  @media (max-width: 850px) {
    .tab-item { font-size: 14px; padding: 14px 16px; }
    .workspace-nav { margin-bottom: 24px; }
  }
</style>
