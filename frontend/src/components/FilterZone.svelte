<!--
  FilterZone.svelte — Category, origin, product, and marketplace filter controls.

  This component has three cascading selectors:
  1. Kategoria (Category) — "Owoce" (fruits) or "Warzywa" (vegetables)
  2. Pochodzenie (Origin) — "Krajowe" (domestic) or "Importowane" (imported)
  3. Produkt (Product) — filtered by both category AND origin above

  And a marketplace checkbox list for toggling which markets to include.

  DATA FLOW:
  Parent (App.svelte) owns the filters state and passes it down via props.
  When the user changes a filter, this component calls onFilterChange()
  to notify the parent, which then re-fetches/re-computes data.

  This is "lifting state up" — a core React/Svelte pattern. The state lives
  in the parent so both Sidebar and FilterZone can access it.
-->

<script lang="ts">
  import type { Manifest, Product, Category, Origin, Filters } from '../lib/types';
  import { productsForCategory } from '../lib/filters';

  let { manifest, filters = $bindable(), onFilterChange }: {
    manifest: Manifest;
    filters: Filters;
    onFilterChange: () => void;
  } = $props();

  let categoryProducts = $derived(
    manifest ? productsForCategory(manifest, filters.category, filters.origin) : []
  );

  function onCategoryChange(e: Event) {
    filters.category = (e.target as HTMLSelectElement).value as Category;
    filters.product = null;
    onFilterChange();
  }

  function onOriginChange(e: Event) {
    filters.origin = (e.target as HTMLSelectElement).value as Origin;
    filters.product = null;
    onFilterChange();
  }

  function onProductChange(e: Event) {
    const idx = Number((e.target as HTMLSelectElement).value);
    filters.product = categoryProducts[idx] ?? null;
    onFilterChange();
  }

  function onMarketToggle(place: string) {
    const next = new Set(filters.markets);
    if (next.has(place)) {
      next.delete(place);
    } else {
      next.add(place);
    }
    filters = { ...filters, markets: next };
    onFilterChange();
  }

  function selectAllMarkets() {
    filters = { ...filters, markets: new Set(manifest.places) };
    onFilterChange();
  }

  function deselectAllMarkets() {
    filters = { ...filters, markets: new Set<string>() };
    onFilterChange();
  }
</script>

<div class="filter-zone">
  <!-- Compact cascading selectors -->
  <div class="selectors-row">
    <div class="filter-group">
      <span class="meta-label">Kategoria</span>
      <div class="select-container">
        <select class="select" onchange={onCategoryChange}>
          <option value="owoce" selected={filters.category === 'owoce'}>Owoce</option>
          <option value="warzywa" selected={filters.category === 'warzywa'}>Warzywa</option>
        </select>
        <div class="select-arrow">
          <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </div>
    </div>
    <div class="filter-group">
      <span class="meta-label">Pochodzenie</span>
      <div class="select-container">
        <select class="select" onchange={onOriginChange}>
          <option value="KRAJOWE" selected={filters.origin === 'KRAJOWE'}>Krajowe</option>
          <option value="IMPORTOWANE" selected={filters.origin === 'IMPORTOWANE'}>Importowane</option>
        </select>
        <div class="select-arrow">
          <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </div>
    </div>
    <div class="filter-group">
      <span class="meta-label">Produkt</span>
      <div class="select-container">
        <select class="select" onchange={onProductChange}>
          <option value="-1" selected={filters.product === null}>Wybierz produkt...</option>
          {#each categoryProducts as product, i}
            <option value={i} selected={filters.product?.name === product.name && filters.product?.unit === product.unit}>
              {product.name} ({product.unit})
            </option>
          {/each}
        </select>
        <div class="select-arrow">
          <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </div>
    </div>
  </div>

  <!-- Marketplace checkboxes -->
  <div class="filter-group-markets">
    <div class="markets-header">
      <span class="meta-label">Rynki Hurtowe</span>
      <div class="market-actions">
        <button onclick={selectAllMarkets} class="action-btn">Wszystkie</button>
        <button onclick={deselectAllMarkets} class="action-btn">Żadne</button>
      </div>
    </div>
    <div class="checkbox-group">
      {#each manifest.places as place}
        <label class="checkbox-item">
          <input
            type="checkbox"
            checked={filters.markets.has(place)}
            onchange={() => onMarketToggle(place)}
          />
          {place}
        </label>
      {/each}
    </div>
  </div>
</div>

<style>
  .filter-zone {
    background-color: var(--surface);
    border: 1px solid var(--rule);
    padding: 16px;
    border-radius: 6px;
  }
  .selectors-row {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--rule);
  }
  .meta-label {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 4px;
    display: block;
  }
  .select-container {
    position: relative;
    width: 100%;
    display: flex;
    align-items: center;
  }
  .select {
    width: 100%;
    padding: 7px 28px 7px 10px;
    border: 1px solid var(--rule);
    border-radius: 4px;
    background-color: var(--surface);
    font-family: inherit;
    font-size: 13px;
    color: var(--ink);
    outline: none;
    -webkit-appearance: none;
    appearance: none;
    cursor: pointer;
    transition: border-color 0.15s ease;
  }
  .select:hover {
    border-color: var(--muted);
  }
  .select:focus {
    border-color: var(--green);
  }
  .select-arrow {
    position: absolute;
    right: 8px;
    pointer-events: none;
    color: var(--muted);
    display: flex;
    align-items: center;
  }
  .filter-group-markets {
    margin-top: 4px;
  }
  .markets-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  .markets-header .meta-label { margin-bottom: 0; }
  .checkbox-group {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-top: 4px;
    max-height: 220px;
    overflow-y: auto;
  }
  .checkbox-item {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    font-size: 13px;
    padding: 3px 4px;
    border-radius: 3px;
    transition: background-color 0.1s ease;
  }
  .checkbox-item:hover {
    background-color: var(--pale);
  }
  .checkbox-item input {
    accent-color: var(--green);
    cursor: pointer;
    width: 14px;
    height: 14px;
  }
  .market-actions { display: flex; gap: 6px; }
  .action-btn {
    font-size: 10px;
    font-weight: 500;
    padding: 3px 8px;
    border: 1px solid var(--rule);
    border-radius: 3px;
    background: var(--surface);
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .action-btn:hover {
    background: var(--green-soft);
    border-color: var(--green);
    color: var(--green);
  }

  @media (max-width: 1024px) {
    .filter-zone { padding: 16px; }
    .selectors-row { gap: 12px; padding-bottom: 16px; }
    .select { font-size: 14px; padding: 9px 28px 9px 10px; }
    .checkbox-item { font-size: 14px; padding: 4px 6px; }
    .checkbox-group { max-height: 180px; }
    .action-btn { min-height: 32px; padding: 4px 10px; }
  }
</style>
