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

  // Props from parent
  let { manifest, filters = $bindable(), onFilterChange }: {
    manifest: Manifest;
    filters: Filters;
    onFilterChange: () => void;
  } = $props();

  // $derived() — automatically recalculates when category OR origin changes.
  // This gives us the filtered product list for the dropdown.
  let categoryProducts = $derived(
    manifest ? productsForCategory(manifest, filters.category, filters.origin) : []
  );

  /**
   * Handle category dropdown change.
   * When category changes, we must reset origin and product selection
   * (the origin options and available products change with category).
   */
  function onCategoryChange(e: Event) {
    filters.category = (e.target as HTMLSelectElement).value as Category;
    filters.product = null;
    onFilterChange();
  }

  /**
   * Handle origin dropdown change.
   * When origin changes, we must reset product selection
   * (the same product name exists in both KRAJOWE and IMPORTOWANE).
   */
  function onOriginChange(e: Event) {
    filters.origin = (e.target as HTMLSelectElement).value as Origin;
    filters.product = null;
    onFilterChange();
  }

  /**
   * Handle product dropdown change.
   * The dropdown value is an index into categoryProducts, not the product itself.
   */
  function onProductChange(e: Event) {
    const idx = Number((e.target as HTMLSelectElement).value);
    filters.product = categoryProducts[idx] ?? null;  // ?? = nullish coalescing
    onFilterChange();
  }

  /**
   * Toggle a single marketplace checkbox.
   * Sets are mutated directly, then we create a new object reference
   * to trigger Svelte's reactivity (mutating a Set alone won't trigger re-renders).
   */
  function onMarketToggle(place: string) {
    if (filters.markets.has(place)) {
      filters.markets.delete(place);
    } else {
      filters.markets.add(place);
    }
    // Creating a new object reference triggers Svelte's reactivity.
    // Without this, Svelte wouldn't know the Set changed.
    filters = { ...filters };
    onFilterChange();
  }

  function selectAllMarkets() {
    manifest.places.forEach(p => filters.markets.add(p));
    filters = { ...filters };
    onFilterChange();
  }

  function deselectAllMarkets() {
    filters.markets.clear();
    filters = { ...filters };
    onFilterChange();
  }
</script>

<div class="filter-zone">
  <h2>Parametry</h2>

  <!-- 1. Category selector -->
  <div class="filter-group">
    <span class="meta-label">Kategoria</span>
    <select class="select" onchange={onCategoryChange}>
      <option value="owoce" selected={filters.category === 'owoce'}>Owoce</option>
      <option value="warzywa" selected={filters.category === 'warzywa'}>Warzywa</option>
    </select>
  </div>

  <!-- 2. Origin selector — domestic vs imported -->
  <div class="filter-group">
    <span class="meta-label">Pochodzenie</span>
    <select class="select" onchange={onOriginChange}>
      <option value="KRAJOWE" selected={filters.origin === 'KRAJOWE'}>Krajowe</option>
      <option value="IMPORTOWANE" selected={filters.origin === 'IMPORTOWANE'}>Importowane</option>
    </select>
  </div>

  <!-- 3. Product selector — filtered by category + origin -->
  <div class="filter-group">
    <span class="meta-label">Produkt</span>
    <select class="select" onchange={onProductChange}>
      <option value="-1">Wybierz produkt...</option>
      {#each categoryProducts as product, i}
        <option value={i}>
          {product.name} ({product.unit})
        </option>
      {/each}
    </select>
  </div>

  <!-- Marketplace checkboxes with select/deselect all -->
  <div class="filter-group">
    <span class="meta-label">Rynki Hurtowe</span>
    <div class="market-actions">
      <button onclick={selectAllMarkets} class="action-btn">Zaznacz wszystkie</button>
      <button onclick={deselectAllMarkets} class="action-btn">Odznacz wszystkie</button>
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
    background-color: var(--surface); border: 1px solid var(--rule); padding: 20px;
  }
  .filter-group { margin-bottom: 20px; }
  .meta-label {
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--muted); margin-bottom: 6px; display: block;
  }
  .select {
    width: 100%; padding: 8px 12px;
    border: 1px solid var(--rule); background-color: var(--surface);
    font-family: inherit; font-size: 13px; color: var(--ink); outline: none;
  }
  /* Scrollable checkbox list for many marketplaces */
  .checkbox-group {
    display: flex; flex-direction: column; gap: 8px; margin-top: 6px;
    max-height: 200px; overflow-y: auto;
  }
  .checkbox-item {
    display: flex; align-items: center; gap: 8px;
    cursor: pointer; font-size: 13px;
  }
  .checkbox-item input { accent-color: var(--green); }
  .market-actions { display: flex; gap: 8px; margin-bottom: 8px; }
  .action-btn {
    font-size: 11px; padding: 2px 8px; border: 1px solid var(--rule);
    background: var(--soft); cursor: pointer;
  }
</style>
