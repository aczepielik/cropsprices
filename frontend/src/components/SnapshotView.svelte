<!--
  SnapshotView.svelte — "Current snapshot" view showing today's market state.

  This view displays:
  1. KPI cards (price range, YoY change, WoW change, date selector)
  2. Context chart (shows +/-3 weeks across 3 years)
  3. Market breakdown table (per-marketplace min/max/spread/deviation)

  DATA FLOW:
  Receives `records` (all price data for selected product) and `selectedDate`.
  Uses $derived() to compute KPIs and table rows — these recalculate automatically
  when records or date change.
-->

<script lang="ts">
  import type { PriceRecord, SnapshotKpis, MarketRow } from '../lib/types';
  import type { WeekRanges } from '../lib/arrow-loader';
  import { filterByWeek, allWeeks } from '../lib/filters';
  import { formatPrice, wednesdayOfWeek, weekKey, niceTicks, mergeEnvelope, sortMarketRows, computeKpis } from '../lib/helpers';

  let { records, selectedDate = $bindable(), markets, weekRanges = null }: {
    records: PriceRecord[];
    selectedDate: string;
    markets: Set<string>;
    weekRanges?: WeekRanges | null;
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

  function goPrevWeek() {
    if (sliderValue > 0) {
      sliderValue -= 1;
      if (weekLabels[sliderValue]) {
        selectedDate = weekLabels[sliderValue];
      }
    }
  }

  function goNextWeek() {
    if (sliderValue < allWeekList.length - 1) {
      sliderValue += 1;
      if (weekLabels[sliderValue]) {
        selectedDate = weekLabels[sliderValue];
      }
    }
  }

  function onDateSelectChange(e: Event) {
    const val = Number((e.target as HTMLSelectElement).value);
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
    const k = computeKpis(filteredWeekRecords);
    if (!k) return { priceRange: '–', spread: '–', overallMin: 0, overallMax: 0 };
    return k;
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

  // Year-over-Year (YoY) change: comparing the average price of current week to same week last year
  let ytyChange = $derived.by(() => {
    if (!selectedWeek || records.length === 0) return null;
    const targetYear = selectedWeek.year - 1;
    const targetWeek = selectedWeek.week;

    const curRecs = filterByWeek(records, selectedWeek.year, selectedWeek.week)
      .filter(r => markets.size === 0 || markets.has(r.place));
    const prevRecs = filterByWeek(records, targetYear, targetWeek)
      .filter(r => markets.size === 0 || markets.has(r.place));

    if (curRecs.length === 0 || prevRecs.length === 0) return null;

    const curAvg = curRecs.reduce((sum, r) => sum + (r.price_min + r.price_max) / 2, 0) / curRecs.length;
    const prevAvg = prevRecs.reduce((sum, r) => sum + (r.price_min + r.price_max) / 2, 0) / prevRecs.length;
    const avgDiff = curAvg - prevAvg;
    const pctDiff = prevAvg > 0 ? (avgDiff / prevAvg) * 100 : 0;

    return {
      avgDiff,
      pctDiff,
    };
  });

  // Week-over-Week (WoW) change: comparing the average price of current week to previous week
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

    const curAvg = curRecs.reduce((sum, r) => sum + (r.price_min + r.price_max) / 2, 0) / curRecs.length;
    const prevAvg = prevRecs.reduce((sum, r) => sum + (r.price_min + r.price_max) / 2, 0) / prevRecs.length;
    const avgDiff = curAvg - prevAvg;
    const pctDiff = prevAvg > 0 ? (avgDiff / prevAvg) * 100 : 0;

    return {
      avgDiff,
      pctDiff,
    };
  });

  let contextWindow = $state(3);

  // Merge pre-aggregated week ranges from loaded markets into a single flat map.
  // If weekRanges is null (fallback), derive from raw records.
  function getWeekSpreadMap(): Map<string, { min: number; max: number }> {
    if (weekRanges) {
      const map = new Map<string, { min: number; max: number }>();
      for (const [market, years] of Object.entries(weekRanges)) {
        if (markets.size > 0 && !markets.has(market)) continue;
        for (const [year, weeks] of Object.entries(years)) {
          for (const [week, range] of Object.entries(weeks)) {
            const key = `${year}-${week}`;
            const existing = map.get(key);
            if (existing) {
              if (range.min < existing.min) existing.min = range.min;
              if (range.max > existing.max) existing.max = range.max;
            } else {
              map.set(key, { min: range.min, max: range.max });
            }
          }
        }
      }
      return map;
    }
    // Fallback: build from raw records (slow path, shouldn't happen in normal flow)
    const map = new Map<string, { min: number; max: number }>();
    for (const r of records) {
      if (markets.size > 0 && !markets.has(r.place)) continue;
      const d = r.date;
      const yearStart = new Date(d.getFullYear(), 0, 1);
      const weekNum = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + d.getDay() + 1) / 7);
      const key = `${d.getFullYear()}-${weekNum}`;
      const existing = map.get(key);
      if (existing) {
        if (r.price_min < existing.min) existing.min = r.price_min;
        if (r.price_max > existing.max) existing.max = r.price_max;
      } else {
        map.set(key, { min: r.price_min, max: r.price_max });
      }
    }
    return map;
  }

  let weekSpreadMap = $derived(getWeekSpreadMap());

  function getWeekSpread(yr: number, wk: number): { min: number; max: number } | null {
    return weekSpreadMap.get(`${yr}-${wk}`) ?? null;
  }

  // Chart data: three series of { label, data[] } for current, year-1, year-2
  let chartData = $derived.by(() => {
    if (!selectedWeek) return null;
    const curIdx = allWeekList.findIndex(
      w => w.year === selectedWeek!.year && w.week === selectedWeek!.week
    );
    if (curIdx < 0) return null;

    const win = contextWindow;
    // Clamp window to available data — shift if near edges
    const listLen = allWeekList.length;
    let startIdx = curIdx - win;
    let endIdx = curIdx + win;
    if (startIdx < 0) { startIdx = 0; endIdx = Math.min(win * 2, listLen - 1); }
    if (endIdx >= listLen) { endIdx = listLen - 1; startIdx = Math.max(0, endIdx - win * 2); }

    const labels: string[] = [];
    const currentData: ({ min: number; max: number } | null)[] = [];
    const yr1Data: ({ min: number; max: number } | null)[] = [];
    const yr2Data: ({ min: number; max: number } | null)[] = [];

    for (let i = startIdx; i <= endIdx; i++) {
      if (i < 0 || i >= allWeekList.length) {
        labels.push('');
        currentData.push(null);
        yr1Data.push(null);
        yr2Data.push(null);
        continue;
      }

      const baseWeek = allWeekList[i];
      const label = wednesdayOfWeek(baseWeek.year, baseWeek.week).slice(5); // "MM-DD"
      labels.push(label);

      // Current year: same week index
      currentData.push(getWeekSpread(baseWeek.year, baseWeek.week));

      // Year -1: subtract ~52 weeks
      const yr1Idx = i - 52;
      yr1Data.push(yr1Idx >= 0 && yr1Idx < allWeekList.length
        ? getWeekSpread(allWeekList[yr1Idx].year, allWeekList[yr1Idx].week)
        : null);

      // Year -2: subtract ~104 weeks
      const yr2Idx = i - 104;
      yr2Data.push(yr2Idx >= 0 && yr2Idx < allWeekList.length
        ? getWeekSpread(allWeekList[yr2Idx].year, allWeekList[yr2Idx].week)
        : null);
    }

    return { labels, currentData, yr1Data, yr2Data, startIdx };
  });

  // Global Y-axis range across ALL data (so the axis doesn't rescale on slider drag)
  let globalYRange = $derived.by(() => {
    let gMin = Infinity;
    let gMax = -Infinity;
    for (const w of allWeekList) {
      const spread = getWeekSpread(w.year, w.week);
      if (spread) {
        if (spread.min < gMin) gMin = spread.min;
        if (spread.max > gMax) gMax = spread.max;
      }
    }
    if (gMin === Infinity) return null;
    const ticks = niceTicks(gMin, gMax, 5);
    const range = ticks[ticks.length - 1] - ticks[0];
    return { yMin: ticks[0] - range * 0.1, yMax: ticks[ticks.length - 1] + range * 0.1, ticks };
  });

  // SVG chart rendering — shaded bands
  let chartSvg = $derived.by(() => {
    if (!chartData || !globalYRange) return '';
    const { labels, currentData, yr1Data, yr2Data, startIdx } = chartData;
    const n = labels.length;
    if (n === 0) return '';

    const w = 800;
    const h = 320;
    const pad = { t: 20, r: 20, b: 40, l: 48 };

    const { yMin, yMax, ticks } = globalYRange;

    function getX(idx: number) { return pad.l + (idx / (n - 1 || 1)) * (w - pad.l - pad.r); }
    function getY(val: number) { return pad.t + (1 - (val - yMin) / (yMax - yMin || 1)) * (h - pad.t - pad.b); }

    function buildBand(dataset: ({ min: number; max: number } | null)[]) {
      const topPts: string[] = [];
      const botPts: string[] = [];
      dataset.forEach((pt, i) => {
        if (pt) {
          topPts.push(`${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(pt.max)}`);
          botPts.unshift(`L ${getX(i)} ${getY(pt.min)}`);
        }
      });
      if (topPts.length < 2) return '';
      return topPts.join(' ') + ' ' + botPts.join(' ') + ' Z';
    }

    function buildLinePath(dataset: ({ min: number; max: number } | null)[], type: 'min' | 'max') {
      const pts: string[] = [];
      dataset.forEach((pt, i) => {
        if (pt) {
          pts.push(`${pts.length === 0 ? 'M' : 'L'} ${getX(i)} ${getY(pt[type])}`);
        }
      });
      return pts.join(' ');
    }

    let crosshairIdx = -1;
    if (selectedWeek) {
      const curIdx = allWeekList.findIndex(
        w => w.year === selectedWeek!.year && w.week === selectedWeek!.week
      );
      crosshairIdx = curIdx - startIdx;
      if (crosshairIdx < 0 || crosshairIdx >= n) crosshairIdx = -1;
    }

    let s = '';

    for (const v of ticks) {
      const y = getY(v);
      s += `<line x1="${pad.l}" y1="${y}" x2="${w - pad.r}" y2="${y}" stroke="var(--soft)" stroke-width="1" />`;
      s += `<text x="${pad.l - 8}" y="${y + 4}" text-anchor="end" font-size="11" fill="var(--muted)">${v.toFixed(v % 1 === 0 ? 0 : 1)}</text>`;
    }
    s += `<text x="14" y="${(pad.t + h - pad.b) / 2}" font-size="11" fill="var(--muted)" text-anchor="middle" transform="rotate(-90, 14, ${(pad.t + h - pad.b) / 2})">Cena (zł)</text>`;

    const pastEnvelope = mergeEnvelope(yr1Data, yr2Data);
    const validPastWeeks = pastEnvelope.filter(Boolean).length;

    // Draw vertical crosshair guide
    if (crosshairIdx >= 0 && crosshairIdx < n) {
      const cx = getX(crosshairIdx);
      s += `<line x1="${cx}" y1="${pad.t}" x2="${cx}" y2="${h - pad.b}" stroke="var(--green)" stroke-width="1.5" opacity="0.35" stroke-dasharray="4,4" />`;
    }

    // Draw past years envelope band and borders
    if (validPastWeeks >= 3) {
      const bandPath = buildBand(pastEnvelope);
      if (bandPath) {
        s += `<path d="${bandPath}" fill="var(--muted)" opacity="0.08" />`;
      }
      const pastTopPath = buildLinePath(pastEnvelope, 'max');
      const pastBotPath = buildLinePath(pastEnvelope, 'min');
      if (pastTopPath) {
        s += `<path d="${pastTopPath}" fill="none" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3,3" opacity="0.4" stroke-linejoin="round" />`;
      }
      if (pastBotPath) {
        s += `<path d="${pastBotPath}" fill="none" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3,3" opacity="0.4" stroke-linejoin="round" />`;
      }
    }

    // Draw current year band and outlines
    const curBand = buildBand(currentData);
    if (curBand) {
      s += `<path d="${curBand}" fill="var(--green)" opacity="0.15" />`;
    }
    const curTopPath = buildLinePath(currentData, 'max');
    const curBotPath = buildLinePath(currentData, 'min');
    if (curTopPath) {
      s += `<path d="${curTopPath}" fill="none" stroke="var(--green)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />`;
    }
    if (curBotPath) {
      s += `<path d="${curBotPath}" fill="none" stroke="var(--green)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />`;
    }

    // Highlight current selected week value nodes
    if (crosshairIdx >= 0 && crosshairIdx < n) {
      const cx = getX(crosshairIdx);
      const curPt = currentData[crosshairIdx];
      if (curPt) {
        s += `<circle cx="${cx}" cy="${getY(curPt.max)}" r="5" fill="var(--surface)" stroke="var(--green)" stroke-width="2.5" />`;
        s += `<circle cx="${cx}" cy="${getY(curPt.min)}" r="5" fill="var(--surface)" stroke="var(--green)" stroke-width="2.5" />`;
      }
    }

    // Date X-axis labels
    labels.forEach((label, i) => {
      if (label) {
        const isCenter = i === crosshairIdx;
        s += `<text x="${getX(i)}" y="${h - 12}" font-size="10" fill="${isCenter ? 'var(--green)' : 'var(--muted)'}" font-weight="${isCenter ? '600' : '400'}" text-anchor="middle">${label}</text>`;
      }
    });

    return s;
  });
</script>

<main class="workspace-grid">
  <!-- KPI Grid (first — these answer "what's happening?") -->
  <div class="kpi-grid">
    <div class="kpi-card">
      <span class="meta-label">Przedział Cenowy</span>
      <div class="kpi-value tabular-nums">{kpis.priceRange}</div>
      <div class="kpi-change muted">Rozpiętość (Spread): {kpis.spread}</div>
    </div>

    <div class="kpi-card">
      <span class="meta-label">Dynamika YoY (Rok-do-Roku)</span>
      {#if ytyChange}
        <div class="kpi-value tabular-nums YoY-row" class:value-up={ytyChange.avgDiff > 0} class:value-down={ytyChange.avgDiff < 0}>
          {ytyChange.avgDiff > 0 ? '+' : ''}{formatPrice(ytyChange.avgDiff)} zł
        </div>
        <div class="kpi-change" class:value-up={ytyChange.avgDiff > 0} class:value-down={ytyChange.avgDiff < 0}>
          {ytyChange.pctDiff > 0 ? '+' : ''}{ytyChange.pctDiff.toFixed(1)}% vs ubiegły rok
        </div>
      {:else}
        <div class="kpi-value tabular-nums muted">–</div>
        <div class="kpi-change muted">Brak danych historycznych</div>
      {/if}
    </div>

    <div class="kpi-card">
      <span class="meta-label">Dynamika WoW (Tydzień-do-Tygodnia)</span>
      {#if wowChange}
        <div class="kpi-value tabular-nums wow-row" class:value-up={wowChange.avgDiff > 0} class:value-down={wowChange.avgDiff < 0}>
          {wowChange.avgDiff > 0 ? '+' : ''}{formatPrice(wowChange.avgDiff)} zł
        </div>
        <div class="kpi-change" class:value-up={wowChange.avgDiff > 0} class:value-down={wowChange.avgDiff < 0}>
          {wowChange.pctDiff > 0 ? '+' : ''}{wowChange.pctDiff.toFixed(1)}% vs poprz. tydzień
        </div>
      {:else}
        <div class="kpi-value tabular-nums muted">–</div>
        <div class="kpi-change muted">Brak danych z poprz. tyg.</div>
      {/if}
    </div>

    <!-- Date selector (answers "when?") -->
    <div class="kpi-card date-card">
      <span class="meta-label">Tydzień (Snapshot)</span>
      <div class="date-selector-wrapper">
        <button
          class="date-nav-btn"
          onclick={goPrevWeek}
          disabled={sliderValue <= 0}
          aria-label="Poprzedni tydzień"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>

        <div class="date-select-container">
          <select class="date-select tabular-nums" value={sliderValue} onchange={onDateSelectChange}>
            {#each weekLabels as label, idx}
              <option value={idx}>{label}</option>
            {/each}
          </select>
          <div class="select-arrow">
            <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
        </div>

        <button
          class="date-nav-btn"
          onclick={goNextWeek}
          disabled={sliderValue >= allWeekList.length - 1}
          aria-label="Następny tydzień"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>
      <div class="kpi-change muted">Wybierz lub przełącz datę</div>
    </div>
  </div>

  <!-- Dashboard layout: Side-by-side elements on desktop -->
  <div class="dashboard-content">
    <!-- Context Chart -->
    <div class="chart-box">
      <div class="chart-header">
        <div class="chart-title">Kontekst Sezonowy (+/-{contextWindow} Tygodni)</div>
        <div class="chart-actions">
          <div class="micro-slider-container">
            <span class="meta-label">Okno:</span>
            <input type="range" class="micro-slider" min={1} max={6} value={contextWindow}
              oninput={(e) => { contextWindow = Number((e.target as HTMLInputElement).value); }} />
          </div>
          <div class="chart-legend">
            <div class="legend-item"><div class="legend-swatch past-swatch"></div>Lata ubiegłe</div>
            <div class="legend-item"><div class="legend-swatch current-swatch"></div>Aktualny Rok</div>
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
        <span class="meta-label">Przekrój Rynków</span>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>Rynek Hurtowy</th>
            <th class="text-right">Min (zł)</th>
            <th class="text-right">Max (zł)</th>
            <th class="text-right">Spread (zł)</th>
            <th class="text-right">Odchylenie (zł)</th>
          </tr>
        </thead>
        <tbody>
          {#each marketRows as row}
            <tr>
              <td>{row.place}</td>
              <td class="text-right tabular-nums">{row.priceMin !== null ? formatPrice(row.priceMin) : '–'}</td>
              <td class="text-right tabular-nums">{row.priceMax !== null ? formatPrice(row.priceMax) : '–'}</td>
              <td class="text-right tabular-nums">{row.spread !== null ? formatPrice(row.spread) : '–'}</td>
              <td class="text-right tabular-nums">{row.deviation !== null ? (row.deviation === 0 ? '0.00' : `+${formatPrice(row.deviation)}`) : '–'}</td>
            </tr>
          {/each}
          {#if marketRows.length === 0}
            <tr><td colspan="5" style="text-align: center; color: var(--muted); padding: 24px;">Brak danych</td></tr>
          {/if}
        </tbody>
      </table>
    </div>
  </div>
</main>

<style>
  .workspace-grid {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  /* KPI Grid */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
  }

  .kpi-card {
    background-color: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 6px;
    padding: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 106px;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
  }

  .kpi-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
    border-color: var(--muted);
  }

  .kpi-value {
    font-size: 26px;
    font-weight: 700;
    margin: 4px 0;
    line-height: 1.2;
    color: var(--ink);
  }

  .kpi-change {
    font-size: 11px;
    font-weight: 500;
    margin-top: 2px;
  }

  .muted {
    color: var(--muted);
  }

  .meta-label {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    display: block;
  }

  /* Compact Date Picker styles */
  .date-card {
    background-color: var(--pale);
  }

  .date-selector-wrapper {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 4px 0;
  }

  .date-nav-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 4px;
    color: var(--ink);
    cursor: pointer;
    transition: all 0.15s ease;
    padding: 0;
    flex-shrink: 0;
  }

  .date-nav-btn:hover:not(:disabled) {
    background: var(--green-soft);
    border-color: var(--green);
    color: var(--green);
  }

  .date-nav-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
    background: var(--pale);
  }

  .date-select-container {
    position: relative;
    flex-grow: 1;
    display: flex;
    align-items: center;
    min-width: 0;
  }

  .date-select {
    width: 100%;
    height: 28px;
    padding: 0 24px 0 8px;
    font-family: inherit;
    font-size: 13px;
    font-weight: 600;
    color: var(--green);
    background: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 4px;
    cursor: pointer;
    -webkit-appearance: none;
    appearance: none;
    outline: none;
    text-overflow: ellipsis;
    white-space: nowrap;
    overflow: hidden;
  }

  .date-select:focus {
    border-color: var(--green);
  }

  .select-arrow {
    position: absolute;
    right: 8px;
    pointer-events: none;
    color: var(--green);
    display: flex;
    align-items: center;
  }

  /* Dynamika coloring */
  .value-up {
    color: var(--green) !important;
  }

  .value-down {
    color: var(--rust) !important;
  }

  /* Content Row (side by side layout) */
  .dashboard-content {
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 20px;
    align-items: start;
  }

  /* Chart Box */
  .chart-box {
    background-color: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 6px;
    padding: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
  }

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
  }

  .chart-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--ink);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .chart-actions {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .svg-chart-container {
    width: 100%;
    position: relative;
  }

  .chart-legend {
    display: flex;
    gap: 12px;
    font-size: 11px;
    font-weight: 500;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
    color: var(--muted);
  }

  .legend-swatch {
    width: 10px;
    height: 10px;
    border-radius: 2px;
  }

  .past-swatch {
    background: var(--muted);
    opacity: 0.15;
  }

  .current-swatch {
    background: var(--green);
    opacity: 0.3;
  }

  .micro-slider-container {
    display: flex;
    align-items: center;
    gap: 6px;
    opacity: 0.8;
  }

  .micro-slider-container .meta-label {
    font-size: 10px;
  }

  .micro-slider {
    width: 60px;
    height: 4px;
    -webkit-appearance: none;
    appearance: none;
    background: var(--rule);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
  }

  .micro-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 10px;
    height: 10px;
    background: var(--ink);
    border-radius: 50%;
  }

  .micro-slider::-moz-range-thumb {
    width: 10px;
    height: 10px;
    background: var(--ink);
    border-radius: 50%;
    border: none;
  }

  /* Table Zone */
  .table-zone {
    background-color: var(--surface);
    border: 1px solid var(--rule);
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    overflow: hidden;
  }

  .table-header-bar {
    padding: 12px 16px;
    border-bottom: 1px solid var(--rule);
    background-color: var(--soft);
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
  }

  .data-table th {
    background-color: var(--surface);
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    padding: 10px 16px;
    border-bottom: 1px solid var(--rule);
    white-space: nowrap;
    text-align: left;
  }

  .data-table td {
    padding: 10px 16px;
    border-bottom: 1px solid var(--soft);
    font-size: 12px;
    white-space: nowrap;
    color: var(--ink);
  }

  .data-table tr:hover td {
    background-color: var(--pale);
  }

  .text-right {
    text-align: right !important;
  }

  .tabular-nums {
    font-variant-numeric: tabular-nums;
  }

  /* Responsive Design */
  @media (max-width: 1200px) {
    .dashboard-content {
      grid-template-columns: 1fr;
      gap: 20px;
    }
  }

  @media (max-width: 1024px) {
    .kpi-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
    }
  }

  @media (max-width: 576px) {
    .kpi-grid {
      grid-template-columns: 1fr;
      gap: 10px;
    }
    .kpi-value {
      font-size: 22px;
    }
    .dashboard-content {
      gap: 16px;
    }
    .chart-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }
    .chart-actions {
      width: 100%;
      justify-content: space-between;
    }
    .data-table th, .data-table td {
      padding: 8px 10px;
      font-size: 11px;
    }
  }
</style>
