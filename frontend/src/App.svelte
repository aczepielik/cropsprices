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
  import SnapshotStats from './components/SnapshotStats.svelte';
  import SnapshotTable from './components/SnapshotTable.svelte';
  import HeatmapView from './components/HeatmapView.svelte';

  const log = debug('App');
  const logError = error('App');

  let manifest = $state<Manifest | null>(null);
  let activeView = $state<ViewMode>('snapshot');
  let records = $state<PriceRecord[]>([]);
  let weekRanges = $state<WeekRanges | null>(null);
  let loadState = $state<'idle' | 'loading' | 'loaded'>('idle');
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
    console.log('[loadData] called', { product: filters.product?.name, hasManifest: !!manifest });
    if (!manifest || !filters.product) {
      console.log('[loadData] early return — no product or manifest');
      records = [];
      filters.date = '';
      loadState = 'loaded';
      return;
    }

    loadState = 'loading';
    log('start', { product: filters.product.name });

    const gen = ++loadGeneration;
    console.log('[loadData] gen incremented', { gen, loadGeneration });
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
      console.error('[loadData] fetch failed', e);
      logError('load failed', { error: String(e) });
    }

    console.log('[loadData] fetch done', { gen, loadGeneration, recordsLen: result.length, stale: gen !== loadGeneration });

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
    console.log('[onFilterChange]', { product: filters.product?.name ?? null });
    if (!filters.product) {
      console.log('[onFilterChange] clearing records — no product');
      records = [];
      filters.date = '';
      loadState = 'loaded';
      return;
    }
    await loadData();
  }
</script>
<div class="app-shell">
<!-- Masthead: editorial newspaper-style header -->
<div class="masthead">
  <div class="masthead-text">
    <h1 class="masthead-title">Notowania Rolne</h1>
    <div class="masthead-subtitle">Biuletyn Rynkowy</div>
    {#if manifest}
      <div class="masthead-meta">
        Aktualizacja: {new Date(manifest.lastUpdate).toLocaleDateString('pl-PL', { year: 'numeric', month: 'long', day: 'numeric' })}
        {#if filters.product}
          <span class="masthead-sep" aria-hidden="true">&middot;</span>
          <span>{filters.category === 'owoce' ? 'Owoce' : 'Warzywa'}</span>
          <span class="masthead-sep" aria-hidden="true">&middot;</span>
          <span>{filters.origin === 'KRAJOWE' ? 'Krajowe' : 'Importowane'}</span>
          <span class="masthead-sep" aria-hidden="true">&middot;</span>
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
    <!-- Sidebar column -->
    <div class="sidebar-col" class:open={sidebarOpen}>
      <Sidebar bind:activeView {onFilterChange} {closeSidebar} />
      <FilterZone {manifest} bind:filters {onFilterChange} />
    </div>

    {#if activeView === 'snapshot'}
      <!-- Snapshot: 3-column layout (sidebar | canvas | table) -->
      <div class="canvas">
        <SnapshotStats {records} bind:selectedDate={filters.date} markets={filters.markets} {weekRanges} />
      </div>
      <div class="table-col">
        <SnapshotTable {records} selectedDate={filters.date} markets={filters.markets} />
      </div>
    {:else}
      <!-- Heatmap: 2-column layout (sidebar | canvas) -->
      <div class="canvas" style="border-left: 1px solid var(--hairline-strong);">
        <HeatmapView {records} markets={filters.markets} />
      </div>
    {/if}
  </div>
{:else if loadState === 'loading' || loadState === 'idle'}
  <p style="text-align: center; color: var(--muted); padding: 48px;">Ładowanie danych...</p>
{:else}
  <p style="text-align: center; color: var(--muted); padding: 48px;">Nie załadowano manifestu.</p>
{/if}
</div>

<style>
  /* ── Masthead ── */
  .masthead { margin-bottom: 40px; display: flex; align-items: flex-start; justify-content: space-between; }

  .masthead-text { flex: 1 1 auto; }

  .masthead-title {
    font-family: var(--font-display);
    font-size: 52px;
    line-height: 1;
    letter-spacing: -0.005em;
    text-transform: uppercase;
    margin-bottom: 8px;
    border: none;
    padding: 0;
  }

  .masthead-subtitle {
    font-size: 19px;
    font-weight: 400;
    letter-spacing: 0.01em;
    color: var(--ink);
    margin-bottom: 10px;
  }

  .masthead-meta {
    font-size: 13px;
    color: var(--muted);
    display: flex;
    gap: 0;
    flex-wrap: wrap;
    align-items: center;
  }

  .masthead-sep {
    margin: 0 6px;
    opacity: 0.5;
  }

  .masthead-product {
    color: var(--ink);
    font-weight: 500;
  }

  /* ── Hamburger ── */
  .hamburger {
    display: none;
    flex-direction: column;
    justify-content: center;
    gap: 4px;
    width: 40px;
    height: 40px;
    padding: 8px;
    background: none;
    border: 1px solid var(--hairline-strong);
    border-radius: 6px;
    cursor: pointer;
    flex-shrink: 0;
  }
  .hamburger-line {
    display: block;
    width: 100%;
    height: 2px;
    background: var(--ink);
    border-radius: 1px;
  }
  .hamburger:hover { border-color: var(--ink); }

  /* ── Layout ── */
  .sidebar-col {
    width: 240px;
    flex-shrink: 0;
    padding-right: 40px;
  }

  .canvas {
    padding: 0 40px;
    border-left: 1px solid var(--hairline-strong);
    border-right: 1px solid var(--hairline-strong);
  }

  .table-col {
    width: 400px;
    flex-shrink: 0;
    padding-left: 40px;
  }

  @media (max-width: 1180px) {
    .hamburger { display: flex; }
    .masthead { margin-bottom: 24px; }
    .masthead-title { font-size: 32px; }
    .masthead-subtitle { font-size: 16px; }
    .sidebar-col {
      position: fixed;
      top: 0;
      left: 0;
      bottom: 0;
      width: 280px;
      max-width: 85vw;
      background: var(--bg);
      z-index: 100;
      transform: translateX(-100%);
      transition: transform 0.25s ease;
      overflow-y: auto;
      padding: 24px 20px;
      border-right: 1px solid var(--hairline);
    }
    .sidebar-col.open {
      transform: translateX(0);
    }
    .canvas {
      border-left: none;
      border-right: none;
      padding: 0;
    }
    .table-col {
      width: 100%;
      padding: 0;
    }
  }
</style>
