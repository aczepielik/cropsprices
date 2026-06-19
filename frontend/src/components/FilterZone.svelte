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
      <select class="select" onchange={onCategoryChange}>
        <option value="owoce" selected={filters.category === 'owoce'}>Owoce</option>
        <option value="warzywa" selected={filters.category === 'warzywa'}>Warzywa</option>
      </select>
    </div>
    <div class="filter-group">
      <span class="meta-label">Pochodzenie</span>
      <select class="select" onchange={onOriginChange}>
        <option value="KRAJOWE" selected={filters.origin === 'KRAJOWE'}>Krajowe</option>
        <option value="IMPORTOWANE" selected={filters.origin === 'IMPORTOWANE'}>Importowane</option>
      </select>
    </div>
    <div class="filter-group">
      <span class="meta-label">Produkt</span>
      <select class="select" onchange={onProductChange}>
        <option value="-1" selected={filters.product === null}>Wybierz produkt...</option>
        {#each categoryProducts as product, i}
          <option value={i} selected={filters.product?.name === product.name && filters.product?.unit === product.unit}>
            {product.name} ({product.unit})
          </option>
        {/each}
      </select>
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
    background-color: var(--surface); border: 1px solid var(--rule); padding: 12px;
  }
  .selectors-row {
    display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px;
    padding-bottom: 12px; border-bottom: 1px solid var(--rule);
  }
  .meta-label {
    font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--muted); margin-bottom: 3px; display: block;
  }
  .select {
    width: 100%; padding: 6px 8px;
    border: 1px solid var(--rule); background-color: var(--surface);
    font-family: inherit; font-size: 12px; color: var(--ink); outline: none;
  }
  .filter-group-markets {
    margin-top: 4px;
  }
  .markets-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 4px;
  }
  .markets-header .meta-label { margin-bottom: 0; }
  .checkbox-group {
    display: flex; flex-direction: column; gap: 4px; margin-top: 4px;
    max-height: 220px; overflow-y: auto;
  }
  .checkbox-item {
    display: flex; align-items: center; gap: 6px;
    cursor: pointer; font-size: 12px;
  }
  .checkbox-item input { accent-color: var(--green); }
  .market-actions { display: flex; gap: 4px; }
  .action-btn {
    font-size: 10px; padding: 2px 6px; border: 1px solid var(--rule);
    background: var(--soft); cursor: pointer;
  }

  @media (max-width: 1024px) {
    .filter-zone { padding: 14px; }
    .selectors-row { gap: 10px; padding-bottom: 14px; }
    .select { font-size: 14px; padding: 8px 10px; }
    .checkbox-item { font-size: 14px; }
    .checkbox-group { max-height: 180px; }
    .action-btn { min-height: 32px; padding: 4px 10px; }
  }
</style>
