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
  import type { Manifest, PriceRecord, Filters, ViewMode } from './lib/types';
  import { loadManifest, loadProductData, loadWeekRanges } from './lib/arrow-loader';
  import type { WeekRanges } from './lib/arrow-loader';
  import { isoWeekOf, wednesdayOfWeek } from './lib/helpers';
  import { debug, error } from './lib/logger';
  import Sidebar from './components/Sidebar.svelte';
  import FilterZone from './components/FilterZone.svelte';
  import SnapshotView from './components/SnapshotView.svelte';
  import HeatmapView from './components/HeatmapView.svelte';

  const log = debug('App');
  const logError = error('App');

  let manifest = $state<Manifest | null>(null);
  let activeView = $state<ViewMode>('snapshot');
  let records = $state<PriceRecord[]>([]);
  let weekRanges = $state<WeekRanges | null>(null);
  let loadState = $state<'idle' | 'loading' | 'loaded'>('idle');
  let sidebarOpen = $state(false);
  let sidebarCollapsed = $state(false);
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

  function toggleSidebarCollapse() {
    sidebarCollapsed = !sidebarCollapsed;
  }

  onMount(async () => {
    manifest = await loadManifest();

    // Default to the 4 markets with the best data coverage across products
    const bestMarkets = ['Bronisze', 'Kalisz', 'Poznań', 'Łódź'];
    const defaultMarkets = manifest.places.filter(p => bestMarkets.includes(p));
    if (defaultMarkets.length > 0) {
      filters.markets = new Set(defaultMarkets);
    } else if (manifest.places.length > 0) {
      filters.markets = new Set(manifest.places.slice(0, 4));
    }

    // Default to the owoce/KRAJOWE product with the best recent data coverage
    const defaultProduct = manifest.products.find(
      p => p.name === 'Gruszki' && p.unit === 'kg' && p.origin === 'KRAJOWE'
    ) ?? manifest.products[0];

    if (defaultProduct) {
      filters.product = defaultProduct;
      await loadData();
    }
    loadState = 'loaded';
  });

  async function loadData() {
    if (!manifest || !filters.product) {
      records = [];
      filters.date = '';
      loadState = 'loaded';
      return;
    }

    loadState = 'loading';
    log('start', { product: filters.product.name });

    const gen = ++loadGeneration;
    let result: PriceRecord[] = [];
    let ranges: WeekRanges | null = null;
    try {
      [result, ranges] = await Promise.all([
        loadProductData(
          filters.product.name,
          filters.product.unit,
          filters.product.origin,
          manifest.currentYear,
        ),
        loadWeekRanges(
          filters.product.name,
          filters.product.unit,
          filters.product.origin,
          manifest.currentYear,
        ),
      ]);
    } catch (e) {
      logError('load failed', { error: String(e) });
    }

    // Discard stale response — only the latest generation matters
    if (gen !== loadGeneration) {
      log('stale response discarded', { gen, loadGeneration });
      return;
    }

    records = result;
    weekRanges = ranges;
    log('complete', { product: filters.product.name, recordsLen: records.length });

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
    loadState = 'loaded';
  }

  async function onFilterChange() {
    if (!filters.product) {
      records = [];
      filters.date = '';
      loadState = 'loaded';
      return;
    }
    await loadData();
  }
</script>

<!-- Header with mobile hamburger -->
<div class="masthead">
  <div class="masthead-left">
    <div class="masthead-title-row">
      <h1 class="masthead-title">Notowania Rolne</h1>
      <div class="masthead-divider" aria-hidden="true"></div>
      <span class="masthead-subtitle">Biuletyn Rynkowy</span>
    </div>
    {#if manifest}
      <div class="masthead-meta">
        <span>Aktualizacja: {new Date(manifest.lastUpdate).toLocaleDateString('pl-PL', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
        {#if filters.product}
          <span class="masthead-sep" aria-hidden="true">·</span>
          <span>{filters.category === 'owoce' ? 'Owoce' : 'Warzywa'}</span>
          <span class="masthead-sep" aria-hidden="true">·</span>
          <span>{filters.origin === 'KRAJOWE' ? 'Krajowe' : 'Importowane'}</span>
          <span class="masthead-sep" aria-hidden="true">·</span>
          <span class="masthead-product">{filters.product.name} ({filters.product.unit})</span>
        {/if}
      </div>
    {/if}
  </div>
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
    <div class="sidebar-col" class:open={sidebarOpen} class:collapsed={sidebarCollapsed}>
      <Sidebar bind:activeView {onFilterChange} {closeSidebar} {sidebarCollapsed} onToggleCollapse={toggleSidebarCollapse} />
      {#if !sidebarCollapsed}
        <FilterZone {manifest} bind:filters {onFilterChange} />
      {/if}
    </div>

    <div class="canvas">
      {#if activeView === 'snapshot'}
        <SnapshotView {records} bind:selectedDate={filters.date} markets={filters.markets} {weekRanges} />
      {:else}
        <HeatmapView {records} markets={filters.markets} />
      {/if}
    </div>
  </div>
{:else if loadState === 'loading' || loadState === 'idle'}
  <p style="text-align: center; color: var(--muted); padding: 48px;">Ładowanie danych...</p>
{:else}
  <p style="text-align: center; color: var(--muted); padding: 48px;">Nie załadowano manifestu.</p>
{/if}

<style>
  .masthead {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 24px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--rule);
  }

  .masthead-left {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .masthead-title-row {
    display: flex;
    align-items: baseline;
    gap: 12px;
    flex-wrap: wrap;
  }

  .masthead-title {
    font-family: var(--font-serif);
    font-size: 32px;
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.1;
    margin: 0;
    border: none;
    padding: 0;
  }

  .masthead-divider {
    width: 1px;
    height: 24px;
    background: var(--muted);
    opacity: 0.4;
    align-self: center;
    flex-shrink: 0;
  }

  .masthead-subtitle {
    font-family: var(--font-sans);
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    align-self: center;
    white-space: nowrap;
  }

  .masthead-meta {
    font-size: 12px;
    color: var(--muted);
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
  }

  .masthead-sep {
    opacity: 0.5;
  }

  .masthead-product {
    font-weight: 500;
    color: var(--ink);
  }

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
    margin-bottom: 4px;
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
    transition: width 0.2s ease;
  }
  .sidebar-col.collapsed {
    width: 56px;
  }

  @media (max-width: 1024px) {
    .masthead { margin-bottom: 16px; }
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
