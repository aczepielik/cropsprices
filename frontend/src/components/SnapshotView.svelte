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
  import { filterByWeek, allWeeks } from '../lib/filters';
  import { formatPrice, wednesdayOfWeek, weekKey, parseWeekKey, niceTicks } from '../lib/helpers';

  let { records, selectedDate = $bindable(), markets }: {
    records: PriceRecord[];
    selectedDate: string;
    markets: Set<string>;
  } = $props();

  // All weeks from ALL records (unfiltered by market), sorted chronologically
  let allWeekList = $derived(allWeeks(records));

  // The display label for each week: Wednesday date string
  let weekLabels = $derived(
    allWeekList.map(w => wednesdayOfWeek(w.year, w.week))
  );

  // Map weekKey → index for fast lookup
  let weekIndexMap = $derived(() => {
    const m = new Map<string, number>();
    allWeekList.forEach((w, i) => m.set(weekKey(w.year, w.week), i));
    return m;
  });

  // Parse selectedDate (a Wednesday string) back to { year, week } for filtering
  let selectedWeek = $derived.by(() => {
    if (!selectedDate) return null;
    // Find which week this Wednesday belongs to
    const idx = weekLabels.indexOf(selectedDate);
    if (idx >= 0 && idx < allWeekList.length) return allWeekList[idx];
    // Fallback: compute from the date itself
    const d = new Date(selectedDate + 'T00:00:00Z');
    const { year, week } = (() => {
      const date = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
      date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
      const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
      const weekNo = Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
      return { year: date.getUTCFullYear(), week: weekNo };
    })();
    return { year, week };
  });

  let sliderValue = $state(0);

  $effect(() => {
    if (allWeekList.length === 0) {
      sliderValue = 0;
      return;
    }
    const idx = weekLabels.indexOf(selectedDate);
    sliderValue = idx >= 0 ? idx : allWeekList.length - 1;
  });

  function onSliderInput(e: Event) {
    const val = Number((e.target as HTMLInputElement).value);
    sliderValue = val;
    if (weekLabels[val]) {
      selectedDate = weekLabels[val];
    }
  }

  // Records for the currently selected week (all records, not market-filtered)
  let weekRecords = $derived.by(() => {
    if (!selectedWeek) return [];
    return filterByWeek(records, selectedWeek.year, selectedWeek.week);
  });

  // Market-filtered records for the selected week
  let filteredWeekRecords = $derived.by(() => {
    if (markets.size === 0) return weekRecords;
    return weekRecords.filter(r => markets.has(r.place));
  });

  let kpis = $derived.by(() => {
    const dayRecords = filteredWeekRecords;
    if (dayRecords.length === 0) {
      return { priceRange: '-', spread: '-', wowRange: '-' } as SnapshotKpis;
    }

    const mins = dayRecords.map(r => r.price_min);
    const maxs = dayRecords.map(r => r.price_max);
    const overallMin = Math.min(...mins);
    const overallMax = Math.max(...maxs);
    const spread = overallMax - overallMin;

    return {
      priceRange: `${formatPrice(overallMin)} – ${formatPrice(overallMax)} zł`,
      spread: `${formatPrice(spread)} zł`,
      wowRange: '',
    };
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
    return rows;
  });

  let wowChange = $derived.by(() => {
    if (!selectedWeek || allWeekList.length < 2) return null;
    const curIdx = allWeekList.findIndex(
      w => w.year === selectedWeek!.year && w.week === selectedWeek!.week
    );
    if (curIdx <= 0) return null;

    const prevWeek = allWeekList[curIdx - 1];
    const curRecs = filterByWeek(records, selectedWeek.year, selectedWeek.week)
      .filter(r => markets.size === 0 || markets.has(r.place));
    const prevRecs = filterByWeek(records, prevWeek.year, prevWeek.week)
      .filter(r => markets.size === 0 || markets.has(r.place));
    if (curRecs.length === 0 || prevRecs.length === 0) return null;

    const curMin = Math.min(...curRecs.map(r => r.price_min));
    const curMax = Math.max(...curRecs.map(r => r.price_max));
    const prevMin = Math.min(...prevRecs.map(r => r.price_min));
    const prevMax = Math.max(...prevRecs.map(r => r.price_max));

    return {
      minDiff: curMin - prevMin,
      maxDiff: curMax - prevMax,
    };
  });

  let contextWindow = $state(3);

  // Helper: get market-filtered national spread { min, max } for a given week
  function getWeekSpread(yr: number, wk: number): { min: number; max: number } | null {
    const recs = filterByWeek(records, yr, wk)
      .filter(r => markets.size === 0 || markets.has(r.place));
    if (recs.length === 0) return null;
    return {
      min: Math.min(...recs.map(r => r.price_min)),
      max: Math.max(...recs.map(r => r.price_max)),
    };
  }

  // Chart data: three series of { label, data[] } for current, year-1, year-2
  let chartData = $derived.by(() => {
    if (!selectedWeek) return null;
    const curIdx = allWeekList.findIndex(
      w => w.year === selectedWeek!.year && w.week === selectedWeek!.week
    );
    if (curIdx < 0) return null;

    const win = contextWindow;
    const labels: string[] = [];
    const currentData: ({ min: number; max: number } | null)[] = [];
    const yr1Data: ({ min: number; max: number } | null)[] = [];
    const yr2Data: ({ min: number; max: number } | null)[] = [];

    for (let i = -win; i <= win; i++) {
      const baseIdx = curIdx + i;
      if (baseIdx < 0 || baseIdx >= allWeekList.length) {
        labels.push('');
        currentData.push(null);
        yr1Data.push(null);
        yr2Data.push(null);
        continue;
      }

      const baseWeek = allWeekList[baseIdx];
      const label = wednesdayOfWeek(baseWeek.year, baseWeek.week).slice(5); // "MM-DD"
      labels.push(label);

      // Current year: same week index
      currentData.push(getWeekSpread(baseWeek.year, baseWeek.week));

      // Year -1: subtract ~52 weeks
      const yr1Idx = baseIdx - 52;
      yr1Data.push(yr1Idx >= 0 && yr1Idx < allWeekList.length
        ? getWeekSpread(allWeekList[yr1Idx].year, allWeekList[yr1Idx].week)
        : null);

      // Year -2: subtract ~104 weeks
      const yr2Idx = baseIdx - 104;
      yr2Data.push(yr2Idx >= 0 && yr2Idx < allWeekList.length
        ? getWeekSpread(allWeekList[yr2Idx].year, allWeekList[yr2Idx].week)
        : null);
    }

    return { labels, currentData, yr1Data, yr2Data };
  });

  // SVG chart rendering
  let chartSvg = $derived.by(() => {
    if (!chartData) return '';
    const { labels, currentData, yr1Data, yr2Data } = chartData;
    const n = labels.length;
    if (n === 0) return '';

    const w = 800;
    const h = 320;
    const pad = { t: 20, r: 20, b: 40, l: 48 };

    // Find global min/max across all three series
    let dataMin = Infinity;
    let dataMax = -Infinity;
    for (const ds of [currentData, yr1Data, yr2Data]) {
      for (const pt of ds) {
        if (pt) {
          if (pt.min < dataMin) dataMin = pt.min;
          if (pt.max > dataMax) dataMax = pt.max;
        }
      }
    }
    if (dataMin === Infinity) return '';

    const ticks = niceTicks(dataMin, dataMax, 5);
    const yMin = ticks[0];
    const yMax = ticks[ticks.length - 1];

    function getX(idx: number) { return pad.l + (idx / (n - 1 || 1)) * (w - pad.l - pad.r); }
    function getY(val: number) { return pad.t + (1 - (val - yMin) / (yMax - yMin || 1)) * (h - pad.t - pad.b); }

    function buildPolygon(dataset: ({ min: number; max: number } | null)[]) {
      const top: string[] = [];
      const bot: string[] = [];
      dataset.forEach((pt, i) => {
        if (pt) {
          top.push(`${getX(i)},${getY(pt.max)}`);
          bot.unshift(`${getX(i)},${getY(pt.min)}`);
        }
      });
      return top.length ? [...top, ...bot].join(' ') : '0,0';
    }

    function buildLine(dataset: ({ min: number; max: number } | null)[], accessor: (p: { min: number; max: number }) => number) {
      return dataset.map((pt, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${pt ? getY(accessor(pt)) : ''}`)
        .filter(s => !s.endsWith('NaN')).join(' ');
    }

    let s = '';

    // Grid lines + Y-axis ticks
    for (const v of ticks) {
      const y = getY(v);
      s += `<line x1="${pad.l}" y1="${y}" x2="${w - pad.r}" y2="${y}" stroke="var(--soft)" stroke-width="1" />`;
      s += `<text x="${pad.l - 8}" y="${y + 4}" text-anchor="end" font-size="11" fill="var(--muted)">${v.toFixed(v % 1 === 0 ? 0 : 1)}</text>`;
    }

    // Ribbons (back to front: year-2, year-1, current)
    s += `<polygon points="${buildPolygon(yr2Data)}" fill="var(--rust-soft)" opacity="0.22" />`;
    s += `<polygon points="${buildPolygon(yr1Data)}" fill="var(--blue-soft)" opacity="0.22" />`;
    s += `<polygon points="${buildPolygon(currentData)}" fill="var(--green-soft)" opacity="0.7" stroke="var(--green)" stroke-width="2.5" />`;

    // Midlines (dashed for past years)
    const mid = (p: { min: number; max: number }) => (p.min + p.max) / 2;
    s += `<path d="${buildLine(yr2Data, mid)}" fill="none" stroke="var(--rust)" stroke-width="1.2" opacity="0.4" stroke-dasharray="3,3" />`;
    s += `<path d="${buildLine(yr1Data, mid)}" fill="none" stroke="var(--blue)" stroke-width="1.2" opacity="0.4" stroke-dasharray="3,3" />`;

    // X-axis labels
    labels.forEach((label, i) => {
      if (label) {
        s += `<text x="${getX(i)}" y="${h - 12}" font-size="10" fill="var(--muted)" text-anchor="middle">${label}</text>`;
      }
    });

    return s;
  });
</script>

<main class="workspace-grid">
  <!-- Week Slider -->
  {#if allWeekList.length > 0}
    <div class="date-slider-zone">
      <span class="meta-label">Tydzień (Snapshot)</span>
      <div class="date-readout tabular-nums">
        {#if selectedWeek}
          {wednesdayOfWeek(selectedWeek.year, selectedWeek.week)}
        {:else}
          –
        {/if}
      </div>
      <div class="slider-track"></div>
      <input
        type="range"
        class="time-slider"
        min={0}
        max={Math.max(0, allWeekList.length - 1)}
        value={sliderValue}
        oninput={onSliderInput}
      />
    </div>
  {/if}

  <!-- KPI Cards -->
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
      {#if wowChange}
        <div class="kpi-value tabular-nums wow-row">
          <span class:wow-up={wowChange.minDiff > 0} class:wow-down={wowChange.minDiff < 0}>
            Min: {wowChange.minDiff > 0 ? '+' : ''}{formatPrice(wowChange.minDiff)} zł
          </span>
          <span class="wow-sep">|</span>
          <span class:wow-up={wowChange.maxDiff > 0} class:wow-down={wowChange.maxDiff < 0}>
            Max: {wowChange.maxDiff > 0 ? '+' : ''}{formatPrice(wowChange.maxDiff)} zł
          </span>
        </div>
      {:else}
        <div class="kpi-value tabular-nums muted">–</div>
      {/if}
      <div class="kpi-change">Zmiana podłogi i sufitu</div>
    </div>
  </div>

  <!-- Context Chart -->
  <div class="chart-box">
    <div class="chart-header">
      <div class="chart-title">Kontekst Sezonowy (+/-{contextWindow} Tygodni)</div>
      <div style="display: flex; align-items: center; gap: 24px;">
        <div class="micro-slider-container">
          <span class="meta-label" style="margin:0; font-size:10px;">Okno:</span>
          <input type="range" class="micro-slider" min={1} max={6} value={contextWindow}
            oninput={(e) => { contextWindow = Number((e.target as HTMLInputElement).value); }} />
        </div>
        <div class="chart-legend">
          <div class="legend-item"><div class="legend-color" style="background-color: var(--rust-soft); border-color: var(--rust);"></div>Rok -2</div>
          <div class="legend-item"><div class="legend-color" style="background-color: var(--blue-soft); border-color: var(--blue);"></div>Rok -1</div>
          <div class="legend-item"><div class="legend-color" style="background-color: var(--green-soft); border-color: var(--green);"></div>Aktualny Rok</div>
        </div>
      </div>
    </div>
    <div class="svg-chart-container">
      {#if chartSvg}
        <svg viewBox="0 0 800 320" preserveAspectRatio="xMidYMid meet">
          {@html chartSvg}
        </svg>
      {:else}
        <svg viewBox="0 0 800 320" preserveAspectRatio="xMidYMid meet">
          <text x="400" y="160" text-anchor="middle" fill="#6e6a61" font-size="14">
            Brak danych w wybranym oknie czasowym
          </text>
        </svg>
      {/if}
    </div>
  </div>

  <!-- Market Breakdown Table -->
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
            <td class="text-right tabular-nums">{row.priceMin !== null ? formatPrice(row.priceMin) : '-'}</td>
            <td class="text-right tabular-nums">{row.priceMax !== null ? formatPrice(row.priceMax) : '-'}</td>
            <td class="text-right tabular-nums">{row.spread !== null ? formatPrice(row.spread) : '-'}</td>
            <td class="text-right tabular-nums">{row.deviation !== null ? formatPrice(row.deviation) : '-'}</td>
          </tr>
        {/each}
        {#if marketRows.length === 0}
          <tr><td colspan="5" style="text-align: center; color: var(--muted);">Brak danych</td></tr>
        {/if}
      </tbody>
    </table>
  </div>
</main>

<style>
  .workspace-grid { display: flex; flex-direction: column; gap: 24px; }
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
  .chart-legend { display: flex; gap: 16px; font-size: 11px; font-weight: 500; }
  .legend-item { display: flex; align-items: center; gap: 6px; color: var(--muted); }
  .legend-color { width: 12px; height: 12px; border: 1px solid var(--rule); }
  .micro-slider-container { display: flex; align-items: center; gap: 8px; opacity: 0.7; }
  .micro-slider-container:hover { opacity: 1; }
  .micro-slider {
    width: 72px; height: 4px;
    -webkit-appearance: none; appearance: none;
    background: var(--rule); border-radius: 2px; outline: none;
  }
  .micro-slider::-webkit-slider-thumb {
    -webkit-appearance: none; width: 12px; height: 12px;
    background: var(--ink); border-radius: 50%;
  }
  .micro-slider::-moz-range-thumb {
    width: 12px; height: 12px;
    background: var(--ink); border-radius: 50%; border: none;
  }
  .table-zone {
    background-color: var(--surface); border: 1px solid var(--rule);
    overflow-x: auto; -webkit-overflow-scrolling: touch;
  }
  .table-header-bar {
    padding: 16px 20px; border-bottom: 1px solid var(--rule); background-color: var(--soft);
  }
  .data-table { width: 100%; border-collapse: collapse; min-width: 540px; }
  .data-table th {
    background-color: var(--soft); font-size: 11px; font-weight: 600; text-transform: uppercase;
    color: var(--muted); padding: 10px 20px; border-bottom: 1px solid var(--rule);
    white-space: nowrap;
  }
  .data-table td {
    padding: 12px 20px; border-bottom: 1px solid var(--soft); font-size: 13px;
    white-space: nowrap;
  }
  .text-right { text-align: right; }
  .tabular-nums { font-variant-numeric: tabular-nums; }

  .date-slider-zone {
    background-color: var(--surface);
    border: 1px solid var(--rule);
    padding: 16px 20px;
  }
  .date-readout {
    font-size: 14px;
    font-weight: 600;
    color: var(--green);
    margin-bottom: 10px;
    display: block;
  }
  .slider-track {
    height: 6px;
    border-radius: 3px;
    background: var(--soft);
    border: 1px solid var(--rule);
    position: relative;
  }
  .time-slider {
    width: 100%;
    -webkit-appearance: none;
    appearance: none;
    background: transparent;
    height: 22px;
    margin-top: -14px;
    display: block;
    position: relative;
    z-index: 2;
  }
  .time-slider::-webkit-slider-runnable-track { height: 6px; }
  .time-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    height: 18px;
    width: 18px;
    border-radius: 50%;
    background: var(--surface);
    border: 2px solid var(--green);
    box-shadow: 0 1px 3px rgba(0,0,0,0.15);
    cursor: pointer;
    margin-top: -6px;
  }
  .time-slider::-moz-range-thumb {
    height: 18px;
    width: 18px;
    border-radius: 50%;
    background: var(--surface);
    border: 2px solid var(--green);
    box-shadow: 0 1px 3px rgba(0,0,0,0.15);
    cursor: pointer;
  }
  .time-slider::-moz-range-track {
    height: 6px;
    background: var(--soft);
    border: 1px solid var(--rule);
    border-radius: 3px;
  }

  .wow-row {
    font-size: 14px;
    margin-top: 6px;
  }
  .wow-up { color: var(--rust); }
  .wow-down { color: var(--green); }
  .wow-sep { color: var(--muted); margin: 0 4px; }

  @media (max-width: 768px) {
    .kpi-row { grid-template-columns: 1fr; gap: 10px; }
    .kpi-value { font-size: 18px; }
    .chart-box { padding: 12px; }
    .chart-title { font-size: 13px; }
    .table-header-bar { padding: 12px 16px; }
    .data-table th, .data-table td { padding: 8px 12px; font-size: 12px; }
  }
  @media (min-width: 769px) and (max-width: 1024px) {
    .kpi-row { grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .kpi-value { font-size: 19px; }
  }
</style>
