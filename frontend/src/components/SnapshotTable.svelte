<!--
  SnapshotTable.svelte — Market breakdown table for the snapshot view.
  Lives in the right column.
-->

<script lang="ts">
  import type { PriceRecord, MarketRow } from '../lib/types';
  import { filterByWeek, allWeeks } from '../lib/filters';
  import { formatPrice, wednesdayOfWeek, sortMarketRows } from '../lib/helpers';

  let { records, selectedDate, markets }: {
    records: PriceRecord[];
    selectedDate: string;
    markets: Set<string>;
  } = $props();

  let filteredRecords = $derived(records.filter(r => markets.has(r.place)));
  let allWeekList = $derived(allWeeks(filteredRecords));
  let weekLabels = $derived(allWeekList.map(w => wednesdayOfWeek(w.year, w.week)));

  let selectedWeek = $derived.by(() => {
    if (!selectedDate) return null;
    const idx = weekLabels.indexOf(selectedDate);
    if (idx >= 0 && idx < allWeekList.length) return allWeekList[idx];
    const d = new Date(selectedDate + 'T00:00:00Z');
    const date = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
    const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
    const weekNo = Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
    return { year: date.getUTCFullYear(), week: weekNo };
  });

  let weekRecords = $derived.by(() => {
    if (!selectedWeek) return [];
    return filterByWeek(records, selectedWeek.year, selectedWeek.week);
  });

  let marketRows = $derived.by(() => {
    const byPlace = new Map<string, PriceRecord[]>();
    for (const r of weekRecords) {
      if (!byPlace.has(r.place)) byPlace.set(r.place, []);
      byPlace.get(r.place)!.push(r);
    }
    const rows: MarketRow[] = [];
    let globalMin = Infinity;
    for (const place of markets) {
      const recs = byPlace.get(place);
      if (recs && recs.length > 0) {
        const min = Math.min(...recs.map(r => r.price_min));
        const max = Math.max(...recs.map(r => r.price_max));
        globalMin = Math.min(globalMin, min);
        rows.push({ place, priceMin: min, priceMax: max, spread: max - min, deviation: 0 });
      } else {
        rows.push({ place, priceMin: null, priceMax: null, spread: null, deviation: null });
      }
    }
    for (const row of rows) {
      if (row.priceMin !== null && globalMin < Infinity) {
        row.deviation = row.priceMin - globalMin;
      }
    }
    sortMarketRows(rows);
    return rows;
  });
</script>

<!-- <div class="table-header-bar">
  <span class="meta-label">Przegląd Rynków</span>
</div> -->
<table class="data-table">
  <thead>
    <tr>
      <th>Rynek Hurtowy</th>
      <th class="text-right">Min (zł)</th>
      <th class="text-right">Max (zł)</th>
      <th class="text-right">Spread</th>
      <th class="text-right">Odch.</th>
    </tr>
  </thead>
  <tbody>
    {#each marketRows as row}
      <tr>
        <td>{row.place}</td>
        <td class="text-right tabular-nums">{row.priceMin !== null ? formatPrice(row.priceMin) : '–'}</td>
        <td class="text-right tabular-nums">{row.priceMax !== null ? formatPrice(row.priceMax) : '–'}</td>
        <td class="text-right tabular-nums">{row.spread !== null ? formatPrice(row.spread) : '–'}</td>
        <td class="text-right tabular-nums">{row.deviation !== null ? (row.deviation === 0 ? '0.00' : `${row.deviation > 0 ? '+' : ''}${formatPrice(row.deviation)}`) : '–'}</td>
      </tr>
    {/each}
    {#if marketRows.length === 0}
      <tr><td colspan="5" style="text-align: center; color: var(--muted); padding: 24px;">Brak danych</td></tr>
    {/if}
  </tbody>
</table>

<style>
  .table-header-bar { margin-bottom: 18px; }
  .meta-label { margin-bottom: 0; }

  .data-table { width: 100%; border-collapse: collapse; }
  .data-table th {
    font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--muted); padding: 0 8px 10px 0; border-bottom: 1px solid var(--hairline-strong);
    white-space: nowrap; text-align: left;
  }
  .data-table td {
    padding: 10px 8px 10px 0; border-bottom: 1px solid var(--hairline);
    font-size: 13px; font-weight: 400; white-space: nowrap; color: var(--ink);
  }
  .data-table tr:last-child td { border-bottom: none; }
  .text-right { text-align: right !important; }
  .tabular-nums { font-variant-numeric: tabular-nums; }
</style>
