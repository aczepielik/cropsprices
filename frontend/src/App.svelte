<!--
  App.svelte — The root component of the entire application.

  This is the "brain" of the app. It:
  1. Loads the manifest (metadata about all available data)
  2. Manages global state (which product, which markets, which date)
  3. Loads Arrow data when filters change
  4. Switches between Snapshot and Heatmap views

  STATE MANAGEMENT in Svelte 5:
  - $state() — reactive variable. When it changes, the UI re-renders automatically.
  - $derived() — computed value. Recalculates when its dependencies change.
  - $effect() — runs code when dependencies change (like useEffect in React).
  - $bindable() — lets parent components read/write a child's prop (two-way binding).

  Think of it like a spreadsheet: when you change a cell value, dependent cells
  update automatically. Svelte does the same thing with UI components.
-->

<script lang="ts">
  import { onMount } from 'svelte';
  import type { Manifest, Product, PriceRecord, Filters, ViewMode } from './lib/types';
  import { loadManifest, loadProductData } from './lib/arrow-loader';
  import { isoWeekOf, wednesdayOfWeek } from './lib/helpers';
  import Sidebar from './components/Sidebar.svelte';
  import FilterZone from './components/FilterZone.svelte';
  import SnapshotView from './components/SnapshotView.svelte';
  import HeatmapView from './components/HeatmapView.svelte';

  let manifest = $state<Manifest | null>(null);
  let activeView = $state<ViewMode>('snapshot');
  let records = $state<PriceRecord[]>([]);
  let loading = $state(true);
  let sidebarOpen = $state(false);
  let loadGeneration = 0;

  let filters = $state<Filters>({
    category: 'owoce',
    origin: 'KRAJOWE',
    product: null,
    markets: new Set<string>(),
    date: '',
    windowWeeks: 3,
  });

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }

  function closeSidebar() {
    sidebarOpen = false;
  }

  onMount(async () => {
    manifest = await loadManifest();

    if (manifest.places.length > 0) {
      filters.markets = new Set(manifest.places.slice(0, 4));
    }

    const defaultProduct = manifest.products.find(
      p => p.name === 'Truskawki' && p.unit === 'kg' && p.origin === 'KRAJOWE'
    ) ?? manifest.products[0];

    if (defaultProduct) {
      filters.product = defaultProduct;
      await loadData();
    }
    loading = false;
  });

  async function loadData() {
    if (!manifest || !filters.product) {
      records = [];
      filters.date = '';
      return;
    }

    // Clear state synchronously so views never show stale data
    records = [];
    filters.date = '';
    loading = true;

    const gen = ++loadGeneration;
    const result = await loadProductData(
      filters.product.name,
      filters.product.unit,
      filters.product.origin,
      manifest.currentYear,
    );

    // Discard stale response — only the latest generation matters
    if (gen !== loadGeneration) return;

    records = result;

    if (records.length > 0) {
      let latestYear = 0;
      let latestWeek = 0;
      for (const r of records) {
        const { year, week } = isoWeekOf(r.date);
        if (year > latestYear || (year === latestYear && week > latestWeek)) {
          latestYear = year;
          latestWeek = week;
        }
      }
      filters.date = wednesdayOfWeek(latestYear, latestWeek);
    } else {
      filters.date = '';
    }
    loading = false;
  }

  async function onFilterChange() {
    if (!filters.product) {
      records = [];
      filters.date = '';
      return;
    }
    await loadData();
  }
</script>

<!-- Header with mobile hamburger -->
<div class="header-bar">
  <h1>Notowania Rolne <span class="header-sub">| BIULETYN RYNKOWY</span></h1>
  <button class="hamburger" onclick={toggleSidebar} aria-label="Menu">
    <span class="hamburger-line"></span>
    <span class="hamburger-line"></span>
    <span class="hamburger-line"></span>
  </button>
</div>

{#if manifest}
  <!-- Mobile sidebar overlay backdrop -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="sidebar-overlay" class:open={sidebarOpen} onclick={closeSidebar}></div>

  <div class="layout-container">
    <div class="sidebar-col" class:open={sidebarOpen}>
      <Sidebar bind:activeView {onFilterChange} {closeSidebar} />
      <FilterZone {manifest} bind:filters {onFilterChange} />
    </div>

    <div class="canvas">
      {#if activeView === 'snapshot'}
        <SnapshotView {records} bind:selectedDate={filters.date} markets={filters.markets} />
      {:else}
        <HeatmapView {records} markets={filters.markets} />
      {/if}
    </div>
  </div>
{:else if loading}
  <p style="text-align: center; color: var(--muted); padding: 48px;">Ładowanie danych...</p>
{:else}
  <p style="text-align: center; color: var(--muted); padding: 48px;">Nie załadowano manifestu.</p>
{/if}

<style>
  .header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 24px;
  }
  .header-bar h1 { margin-bottom: 0; border-bottom: none; padding-bottom: 0; }

  .hamburger {
    display: none;
    flex-direction: column;
    justify-content: center;
    gap: 5px;
    width: 40px;
    height: 40px;
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 4px;
    cursor: pointer;
    padding: 8px;
    flex-shrink: 0;
  }
  .hamburger-line {
    display: block;
    width: 100%;
    height: 2px;
    background: var(--ink);
    border-radius: 1px;
  }

  .sidebar-col {
    width: 300px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  @media (max-width: 768px) {
    .header-bar { margin-bottom: 12px; }
    .hamburger { display: flex; }
    .sidebar-col {
      position: fixed;
      top: 0;
      left: 0;
      bottom: 0;
      width: 300px;
      max-width: 85vw;
      background: var(--bg);
      z-index: 100;
      transform: translateX(-100%);
      transition: transform 0.25s ease;
      overflow-y: auto;
      padding: 16px;
      border-right: 1px solid var(--rule);
    }
    .sidebar-col.open {
      transform: translateX(0);
    }
  }
</style>
