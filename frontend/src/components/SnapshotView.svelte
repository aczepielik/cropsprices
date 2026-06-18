<!--
  SnapshotView.svelte — "Current snapshot" view showing today's market state.

  This view displays:
  1. KPI cards (price range, spread, week-over-week change)
  2. Context chart (placeholder — will show ±3 weeks across 3 years)
  3. Market breakdown table (per-marketplace min/max/spread)

  DATA FLOW:
  Receives `records` (all price data for selected product) and `selectedDate`.
  Uses $derived() to compute KPIs and table rows — these recalculate automatically
  when records or date change.
-->

<script lang="ts">
  import type { PriceRecord, SnapshotKpis, MarketRow } from '../lib/types';
  import { filterByDate, aggregateByDate } from '../lib/filters';
  import { formatPrice, formatDate } from '../lib/helpers';

  // Props from parent
  let { records, selectedDate }: {
    records: PriceRecord[];
    selectedDate: string;
  } = $props();

  // $derived.by() — like $derived() but for complex calculations.
  // Recalculates whenever `records` or `selectedDate` changes.
  let kpis = $derived.by(() => {
    const dayRecords = filterByDate(records, selectedDate);
    if (dayRecords.length === 0) {
      return { priceRange: '-', spread: '-', wowRange: '-' } as SnapshotKpis;
    }

    // Find the overall min and max across all marketplaces for this date
    const mins = dayRecords.map(r => r.price_min);
    const maxs = dayRecords.map(r => r.price_max);
    const overallMin = Math.min(...mins);
    const overallMax = Math.max(...maxs);
    const spread = overallMax - overallMin;

    return {
      priceRange: `${formatPrice(overallMin)} - ${formatPrice(overallMax)} zł`,
      spread: `${formatPrice(spread)} zł`,
      wowRange: `+12.5%`,  // TODO: calculate actual WoW change
    };
  });

  // Compute per-marketplace breakdown
  let marketRows = $derived.by(() => {
    const dayRecords = filterByDate(records, selectedDate);

    // Group records by marketplace
    const byPlace = new Map<string, PriceRecord[]>();
    for (const r of dayRecords) {
      if (!byPlace.has(r.place)) byPlace.set(r.place, []);
      byPlace.get(r.place)!.push(r);
    }

    // Calculate min, max, spread for each marketplace
    const rows: MarketRow[] = [];
    let globalMin = Infinity;
    for (const [place, recs] of byPlace) {
      const min = Math.min(...recs.map(r => r.price_min));
      const max = Math.max(...recs.map(r => r.price_max));
      globalMin = Math.min(globalMin, min);
      rows.push({ place, priceMin: min, priceMax: max, spread: max - min, deviation: 0 });
    }

    // Calculate deviation from global minimum for each marketplace
    // This shows how much more expensive each marketplace is compared to the cheapest
    for (const row of rows) {
      row.deviation = row.priceMin - globalMin;
    }
    return rows;
  });
</script>

<main class="workspace-grid active">
  <!-- KPI Cards — three summary metrics across the top -->
  <div class="kpi-row">
    <div class="kpi-card">
      <span class="meta-label">Przedział Cenowy (Wybrane Rynki)</span>
      <div class="kpi-value tabular-nums">{kpis.priceRange}</div>
      <div class="kpi-change muted">Stan na wybraną datę</div>
    </div>
    <div class="kpi-card">
      <span class="meta-label">Rozpiętość (Spread)</span>
      <div class="kpi-value tabular-nums">{kpis.spread}</div>
      <div class="kpi-change">Zróżnicowanie rynkowe (max-min)</div>
    </div>
    <div class="kpi-card">
      <span class="meta-label">Dynamika Zmian WoW</span>
      <div class="kpi-value tabular-nums" style="font-size: 18px;">{kpis.wowRange}</div>
      <div class="kpi-change">Zmiana podłogi i sufitu</div>
    </div>
  </div>

  <!-- Context Chart — placeholder for seasonal comparison chart -->
  <div class="chart-box">
    <div class="chart-header">
      <div class="chart-title">Kontekst Sezonowy (+/-3 Tygodnie)</div>
    </div>
    <div class="svg-chart-container" style="height: 320px;">
      <svg viewBox="0 0 800 320">
        <text x="400" y="160" text-anchor="middle" fill="#6e6a61" font-size="14">
          Context chart - to be implemented
        </text>
      </svg>
    </div>
  </div>

  <!-- Market Breakdown Table — per-marketplace price details -->
  <div class="table-zone">
    <div class="table-header-bar">
      <span class="meta-label" style="margin-bottom:0;">Przekrój Rynków</span>
    </div>
    <table class="data-table">
      <thead>
        <tr>
          <th>Rynek Hurtowy</th>
          <th class="text-right">Cena Min (zl)</th>
          <th class="text-right">Cena Max (zl)</th>
          <th class="text-right">Rozpietosc (Spread)</th>
          <th class="text-right">Odchylenie od min. wybranych</th>
        </tr>
      </thead>
      <tbody>
        {#each marketRows as row}
          <tr>
            <td>{row.place}</td>
            <td class="text-right tabular-nums">{formatPrice(row.priceMin)}</td>
            <td class="text-right tabular-nums">{formatPrice(row.priceMax)}</td>
            <td class="text-right tabular-nums">{formatPrice(row.spread)}</td>
            <td class="text-right tabular-nums">{formatPrice(row.deviation)}</td>
          </tr>
        {/each}
        {#if marketRows.length === 0}
          <tr><td colspan="5" style="text-align: center; color: var(--muted);">Brak danych dla wybranej daty</td></tr>
        {/if}
      </tbody>
    </table>
  </div>
</main>

<style>
  .workspace-grid { display: none; flex-direction: column; gap: 24px; }
  .workspace-grid.active { display: flex; }
  .kpi-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
  .kpi-card {
    background-color: var(--surface); border: 1px solid var(--rule); padding: 16px;
  }
  .kpi-value { font-size: 22px; font-weight: 600; margin-top: 4px; }
  .kpi-change { font-size: 12px; margin-top: 6px; }
  .muted { color: var(--muted); }
  .meta-label {
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--muted); margin-bottom: 6px; display: block;
  }
  .chart-box {
    background-color: var(--surface); border: 1px solid var(--rule); padding: 20px;
  }
  .chart-header {
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 16px; flex-wrap: wrap; gap: 12px;
  }
  .chart-title { font-size: 14px; font-weight: 600; color: var(--ink); }
  .svg-chart-container { width: 100%; position: relative; }
  .table-zone { background-color: var(--surface); border: 1px solid var(--rule); }
  .table-header-bar {
    padding: 16px 20px; border-bottom: 1px solid var(--rule); background-color: var(--soft);
  }
  .data-table { width: 100%; border-collapse: collapse; }
  .data-table th {
    background-color: var(--soft); font-size: 11px; font-weight: 600; text-transform: uppercase;
    color: var(--muted); padding: 10px 20px; border-bottom: 1px solid var(--rule);
  }
  .data-table td {
    padding: 12px 20px; border-bottom: 1px solid var(--soft); font-size: 13px;
  }
  .text-right { text-align: right; }
  .tabular-nums { font-variant-numeric: tabular-nums; }
</style>
