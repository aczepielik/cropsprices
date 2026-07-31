<!--
  SnapshotTable.svelte — Market breakdown table for the snapshot view.
  Lives in the right column.
-->

<script lang="ts">
  import type { PriceRecord } from '../lib/types';
  import { filterByWeek, allWeeks } from '../lib/filters';
  import { formatPrice, wednesdayOfWeek } from '../lib/helpers';

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

  function range(recs: PriceRecord[]): string | null {
    if (recs.length === 0) return null;
    const min = Math.min(...recs.map(r => r.price_min));
    const max = Math.max(...recs.map(r => r.price_max));
    return `${formatPrice(min)} – ${formatPrice(max)}`;
  }

  interface MarketRow {
    place: string;
    current: string | null;
    wow: string | null;
    yoy: string | null;
  }

  let marketRows = $derived.by(() => {
    if (!selectedWeek) return [];

    const rows: MarketRow[] = [];
    for (const place of markets) {
      const curRecs = filterByWeek(filteredRecords, selectedWeek.year, selectedWeek.week)
        .filter(r => r.place === place);

      if (curRecs.length === 0) {
        rows.push({ place, current: null, wow: null, yoy: null });
        continue;
      }

      const current = range(curRecs);

      const prevWeek = allWeekList.find(
        w => w.year === selectedWeek!.year && w.week === selectedWeek!.week - 1,
      );
      const wowRecs = prevWeek
        ? filterByWeek(filteredRecords, prevWeek.year, prevWeek.week).filter(r => r.place === place)
        : [];
      const wow = range(wowRecs);

      const yoyRecs = filterByWeek(
        filteredRecords, selectedWeek.year - 1, selectedWeek.week,
      ).filter(r => r.place === place);
      const yoy = range(yoyRecs);

      rows.push({ place, current, wow, yoy });
    }

    rows.sort((a, b) => {
      if (a.current !== null && b.current === null) return -1;
      if (a.current === null && b.current !== null) return 1;
      return a.place.localeCompare(b.place);
    });

    return rows;
  });
</script>

<table class="data-table">
  <thead>
    <tr>
      <th>Rynek<br>Hurtowy</th>
      <th class="text-right">Bieżący<br>Tydzień</th>
      <th class="text-right">Tydzień<br>Wcześniej</th>
      <th class="text-right">Rok<br>Wcześniej</th>
    </tr>
  </thead>
  <tbody>
    {#each marketRows as row}
      <tr>
        <td>{row.place}</td>
        <td class="text-right tabular-nums">{row.current ?? '–'}</td>
        <td class="text-right tabular-nums">{row.wow ?? '–'}</td>
        <td class="text-right tabular-nums">{row.yoy ?? '–'}</td>
      </tr>
    {/each}
    {#if marketRows.length === 0}
      <tr><td colspan="4" class="empty-cell">Brak danych</td></tr>
    {/if}
  </tbody>
</table>

<style>
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
  .empty-cell { text-align: center; color: var(--muted); padding: 24px; }

  @media (max-width: 450px) {
    .data-table th { font-size: 10px; }
    .data-table td { font-size: 11px; padding: 8px 6px 8px 0; }
  }
</style>
