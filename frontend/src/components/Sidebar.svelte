<!--
  Sidebar.svelte — Tab navigation between Snapshot and Heatmap views.
  Collapsible on desktop: compact mode shows only tabs, expanded mode shows tabs + label.
-->

<script lang="ts">
  import type { ViewMode } from '../lib/types';

  let { activeView = $bindable(), onFilterChange, closeSidebar, sidebarCollapsed = false, onToggleCollapse }: {
    activeView: ViewMode;
    onFilterChange: () => void;
    closeSidebar?: () => void;
    sidebarCollapsed?: boolean;
    onToggleCollapse?: () => void;
  } = $props();

  const tabs: { id: ViewMode; label: string; short: string }[] = [
    { id: 'snapshot', label: 'Widok Aktualny (Snapshot)', short: 'Snapshot' },
    { id: 'heatmap', label: 'Mapa Cieplna (Heatmap)', short: 'Heatmap' },
  ];

  function selectTab(id: ViewMode) {
    activeView = id;
    closeSidebar?.();
  }
</script>

  <aside class="sidebar" class:collapsed={sidebarCollapsed}>
  <div class="sidebar-top">
    {#if sidebarCollapsed}
      <span class="meta-label" style="writing-mode: vertical-lr; text-orientation: mixed; transform: rotate(180deg); font-size: 9px; letter-spacing: 0.12em;">FILTRY</span>
    {:else}
      <span class="meta-label">Tryb Analizy</span>
    {/if}
    <div class="sidebar-actions">
      {#if onToggleCollapse}
        <button class="collapse-btn" onclick={onToggleCollapse} aria-label={sidebarCollapsed ? 'Rozwiń panel' : 'Zwiń panel'}>
          {sidebarCollapsed ? '»' : '«'}
        </button>
      {/if}
      {#if closeSidebar}
        <button class="close-btn" onclick={closeSidebar} aria-label="Zamknij menu">&times;</button>
      {/if}
    </div>
  </div>
  <nav class="workspace-nav">
    {#each tabs as tab}
      <button
        class="tab-item"
        class:active={activeView === tab.id}
        onclick={() => selectTab(tab.id)}
        title={sidebarCollapsed ? tab.label : undefined}
      >
        {sidebarCollapsed ? tab.short : tab.label}
      </button>
    {/each}
  </nav>
</aside>

<style>
  .sidebar { width: 300px; flex-shrink: 0; transition: width 0.2s ease; }
  .sidebar.collapsed { width: 56px; }

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
    white-space: nowrap; overflow: hidden;
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
  .sidebar-actions { display: flex; gap: 2px; align-items: center; }
  .collapse-btn, .close-btn {
    background: none; border: none; font-size: 16px;
    color: var(--muted); cursor: pointer; padding: 2px 4px; line-height: 1;
  }
  .collapse-btn:hover, .close-btn:hover { color: var(--ink); }
  .close-btn { display: none; }

  .collapsed .tab-item {
    padding: 12px 8px; text-align: center; font-size: 11px;
  }
  .collapsed .tab-item.active {
    padding-left: 4px; border-left: 3px solid var(--green);
  }

  @media (max-width: 1024px) {
    .meta-label { font-size: 10px; }
    .tab-item { font-size: 14px; padding: 12px 14px; }
    .workspace-nav { margin-bottom: 16px; }
    .close-btn { display: block; }
    .collapse-btn { display: none; }
    .sidebar-top { margin-bottom: 12px; }
  }
</style>
