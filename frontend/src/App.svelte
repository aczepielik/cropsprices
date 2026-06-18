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
  import Sidebar from './components/Sidebar.svelte';
  import FilterZone from './components/FilterZone.svelte';
  import SnapshotView from './components/SnapshotView.svelte';
  import HeatmapView from './components/HeatmapView.svelte';

  // $state() makes these variables reactive — when they change, the UI updates.
  let manifest = $state<Manifest | null>(null);  // null until loaded
  let activeView = $state<ViewMode>('snapshot');  // which tab is active
  let records = $state<PriceRecord[]>([]);        // price data for selected product
  let loading = $state(true);                      // true while fetching data

  // All filter state in one object. When any filter changes, we re-fetch data.
  let filters = $state<Filters>({
    category: 'owoce',           // default to fruits
    origin: 'KRAJOWE',           // default to domestic
    product: null,               // will be set after manifest loads
    markets: new Set<string>(),  // empty until manifest loads
    date: '',                    // will be set to most recent date after data loads
    windowWeeks: 3,              // ±3 weeks around selected date for context chart
  });

  // onMount runs once when the component first appears on screen.
  // This is where we fetch initial data — similar to componentDidMount in React.
  onMount(async () => {
    // Step 1: Load the manifest (table of contents for all data)
    manifest = await loadManifest();

    // Step 2: Pre-select the first 4 marketplaces
    if (manifest.places.length > 0) {
      filters.markets = new Set(manifest.places.slice(0, 4));
    }

    // Step 3: Pick a default product (Truskawki = Strawberries, popular in Poland)
    const defaultProduct = manifest.products.find(
      p => p.name === 'Truskawki' && p.unit === 'kg' && p.origin === 'KRAJOWE'
    ) ?? manifest.products[0];  // fallback to first product if Truskawki not found

    if (defaultProduct) {
      filters.product = defaultProduct;
      await loadData();  // Fetch the actual price data
    }
    loading = false;
  });

  /**
   * Fetch Arrow data for the currently selected product.
   * Called on startup and whenever the user changes the product filter.
   */
  async function loadData() {
    if (!manifest || !filters.product) return;
    loading = true;

    // loadProductData fetches two files in parallel (archive + current year)
    records = await loadProductData(
      filters.product.name,
      filters.product.unit,
      filters.product.origin,
      manifest.currentYear,
    );

    // Auto-select the most recent date after loading new data
    if (records.length > 0) {
      const dates = [...new Set(records.map(r => r.date.toISOString().slice(0, 10)))].sort();
      filters.date = dates[dates.length - 1];  // last date = most recent
    }
    loading = false;
  }

  /**
   * Called by child components when any filter changes.
   * Re-fetches data for the new product (market toggles don't need re-fetching
   * because all markets are in the same Arrow file).
   */
  async function onFilterChange() {
    if (filters.product) {
      await loadData();
    }
  }
</script>

<!-- The header — stays fixed at the top -->
<h1>Notowania Rolne <span style="font-weight: 300; font-size: 16px; color: var(--muted);">| BIULETYN RYNKOWY</span></h1>

{#if manifest}
  <!-- Main layout: sidebar (filters) + canvas (visualization) -->
  <div class="layout-container">
    <div class="sidebar-col">
      <!-- Sidebar: tab navigation between Snapshot and Heatmap views -->
      <Sidebar bind:activeView {onFilterChange} />
      <!-- FilterZone: category, product, and market selectors -->
      <FilterZone {manifest} bind:filters {onFilterChange} />
    </div>

    <div class="canvas">
      <!-- Show the active view based on which tab is selected -->
      {#if activeView === 'snapshot'}
        <SnapshotView {records} selectedDate={filters.date} />
      {:else}
        <HeatmapView {records} markets={filters.markets} />
      {/if}
    </div>
  </div>
{:else if loading}
  <!-- Loading state while manifest is being fetched -->
  <p style="text-align: center; color: var(--muted); padding: 48px;">Ładowanie danych...</p>
{:else}
  <!-- Error state if manifest failed to load -->
  <p style="text-align: center; color: var(--muted); padding: 48px;">Nie załadowano manifestu.</p>
{/if}

<style>
  .sidebar-col {
    width: 300px;
    flex-shrink: 0;  /* Don't let the sidebar shrink — keep it at 300px */
    display: flex;
    flex-direction: column;
    gap: 0;
  }
</style>
