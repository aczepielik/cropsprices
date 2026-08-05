<!--
  FilterZone.svelte — Category, origin, product, and marketplace filter controls.

  Plain bordered dropdowns matching the new mock design.
  No card wrapper — just selectors and checkboxes.
-->

<script lang="ts">
  import type { Manifest, Product, Category, Origin, Filters } from '../lib/types';
  import { productsForCategory } from '../lib/filters';
  import { WHITELISTED_PRODUCTS, WHITELISTED_MARKETS } from '../lib/whitelist';

  let { manifest, filters = $bindable(), onFilterChange, onMarketsChange }: {
    manifest: Manifest;
    filters: Filters;
    onFilterChange: () => void;
    onMarketsChange: () => void;
  } = $props();

  let categoryProducts = $derived(
    manifest ? productsForCategory(manifest, filters.category, filters.origin) : []
  );

  let visibleProducts = $derived(
    filters.showSparse
      ? categoryProducts
      : categoryProducts.filter(p => WHITELISTED_PRODUCTS.has(`${p.name}|${p.unit}|${p.origin}`))
  );

  let visiblePlaces = $derived(
    filters.showSparse
      ? manifest.places
      : manifest.places.filter(p => WHITELISTED_MARKETS.has(p))
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
    filters.product = visibleProducts[idx] ?? null;
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
    onMarketsChange();
  }

  function selectAllMarkets() {
    filters = { ...filters, markets: new Set(visiblePlaces) };
    onMarketsChange();
  }

  function deselectAllMarkets() {
    filters = { ...filters, markets: new Set<string>() };
    onMarketsChange();
  }

  function toggleShowSparse() {
    filters.showSparse = !filters.showSparse;
    // If turning off sparse and current product is not whitelisted, reset selection
    if (!filters.showSparse && filters.product) {
      const key = `${filters.product.name}|${filters.product.unit}|${filters.product.origin}`;
      if (!WHITELISTED_PRODUCTS.has(key)) {
        filters.product = null;
      }
    }
    onFilterChange();
  }
</script>

<div class="filter-zone">
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
          {#each visibleProducts as product, i}
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

  <div class="filter-group-sparse">
    <label class="checkbox-item sparse-toggle">
      <input
        type="checkbox"
        checked={filters.showSparse}
        onchange={toggleShowSparse}
      />
      Pokaż produkty i rynki z małą ilością danych
    </label>
  </div>

  <div class="filter-group-markets">
    <div class="markets-header">
      <span class="meta-label">Rynki Hurtowe</span>
      <div class="market-actions">
        <button onclick={selectAllMarkets} class="action-btn">Wszystkie</button>
        <button onclick={deselectAllMarkets} class="action-btn">Żadne</button>
      </div>
    </div>
    <div class="checkbox-group">
      {#each visiblePlaces as place}
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
    margin-bottom: 28px;
  }

  .filter-group-sparse {
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--hairline);
  }

  .sparse-toggle {
    font-size: 12px;
    color: var(--muted);
    line-height: 1.4;
  }

  .selectors-row {
    display: flex;
    flex-direction: column;
    gap: 16px;
    margin-bottom: 28px;
  }

  .meta-label {
    margin-bottom: 10px;
  }

  .select-container {
    position: relative;
    display: flex;
    align-items: center;
  }

  .select {
    width: 100%;
    padding: 8px 30px 8px 10px;
    border: 1px solid var(--hairline-strong);
    border-radius: 6px;
    background-color: var(--bg);
    font-family: inherit;
    font-size: 13px;
    font-weight: 400;
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

  .select-arrow {
    position: absolute;
    right: 10px;
    pointer-events: none;
    color: var(--muted);
    display: flex;
  }

  .filter-group-markets {
    margin-top: 4px;
  }

  .markets-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .markets-header .meta-label {
    margin-bottom: 0;
  }

  .market-actions {
    display: flex;
    gap: 10px;
  }

  .action-btn {
    font-size: 11px;
    font-weight: 500;
    padding: 0;
    border: none;
    background: none;
    color: var(--muted);
    cursor: pointer;
  }

  .action-btn:hover {
    color: var(--ink);
  }

  .checkbox-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
    max-height: 220px;
    overflow-y: auto;
  }

  .checkbox-item {
    display: flex;
    align-items: center;
    gap: 9px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 400;
  }

  .checkbox-item input {
    accent-color: var(--ink);
    cursor: pointer;
    width: 14px;
    height: 14px;
  }

  @media (max-width: 1180px) {
    .select { font-size: 14px; padding: 10px 30px 10px 10px; }
    .checkbox-item { font-size: 14px; }
    .checkbox-group { max-height: 180px; }
  }
</style>
