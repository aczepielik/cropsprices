<!--
  SnapshotStats.svelte — Stat row + context chart for the snapshot view.
  Lives in the center canvas column.
-->

<script lang="ts">
  import type { PriceRecord, ComparisonChange } from "../lib/types";
  import type { WeekRanges } from "../lib/arrow-loader";
  import { filterByWeek, allWeeks } from "../lib/filters";
  import {
    formatPrice,
    wednesdayOfWeek,
    weekKey,
    niceTicks,
    computeKpis,
    addWeeksToISO,
  } from "../lib/helpers";

  let {
    records,
    selectedDate = $bindable(),
    markets,
    weekRanges = null,
  }: {
    records: PriceRecord[];
    selectedDate: string;
    markets: Set<string>;
    weekRanges?: WeekRanges | null;
  } = $props();

  let filteredRecords = $derived(records.filter((r) => markets.has(r.place)));
  let allWeekList = $derived(allWeeks(filteredRecords));
  let weekLabels = $derived(
    allWeekList.map((w) => wednesdayOfWeek(w.year, w.week)),
  );

  let selectedWeek = $derived.by(() => {
    if (!selectedDate) return null;
    const idx = weekLabels.indexOf(selectedDate);
    if (idx >= 0 && idx < allWeekList.length) return allWeekList[idx];
    const d = new Date(selectedDate + "T00:00:00Z");
    const date = new Date(
      Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()),
    );
    date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
    const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
    const weekNo = Math.ceil(
      ((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7,
    );
    return { year: date.getUTCFullYear(), week: weekNo };
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
      if (weekLabels[sliderValue]) selectedDate = weekLabels[sliderValue];
    }
  }

  function goNextWeek() {
    if (sliderValue < allWeekList.length - 1) {
      sliderValue += 1;
      if (weekLabels[sliderValue]) selectedDate = weekLabels[sliderValue];
    }
  }

  function onDateSelectChange(e: Event) {
    const val = Number((e.target as HTMLSelectElement).value);
    sliderValue = val;
    if (weekLabels[val]) selectedDate = weekLabels[val];
  }

  let weekRecords = $derived.by(() => {
    if (!selectedWeek) return [];
    return filterByWeek(filteredRecords, selectedWeek.year, selectedWeek.week);
  });

  let filteredWeekRecords = $derived(weekRecords);

  let kpis = $derived.by(() => {
    const k = computeKpis(filteredWeekRecords);
    if (!k)
      return { priceRange: "–", spread: "–", overallMin: 0, overallMax: 0 };
    return k;
  });

  let ytyChange: ComparisonChange | null = $derived.by(() => {
    if (!selectedWeek || filteredRecords.length === 0) return null;

    const targetYear = selectedWeek.year - 1;

    const prevRecs = filterByWeek(
      filteredRecords,
      targetYear,
      selectedWeek.week,
    );

    if (weekRecords.length === 0 || prevRecs.length === 0) return null;

    const curLower = Math.min(...weekRecords.map((r) => r.price_min));
    const curUpper = Math.max(...weekRecords.map((r) => r.price_max));
    const prevLower = Math.min(...prevRecs.map((r) => r.price_min));
    const prevUpper = Math.max(...prevRecs.map((r) => r.price_max));

    return {
      prevLow: prevLower,
      prevUpper: prevUpper,
      lowerChange: curLower - prevLower,
      upperChange: curUpper - prevUpper,
      lowerPct: prevLower > 0 ? ((curLower - prevLower) / prevLower) * 100 : 0,
      upperPct: prevUpper > 0 ? ((curUpper - prevUpper) / prevUpper) * 100 : 0,
    };
  });

  let wowChange: ComparisonChange | null = $derived.by(() => {
    if (!selectedWeek || allWeekList.length < 2) return null;

    const prevWeek = allWeekList.find(
      (w) => w.year === selectedWeek!.year && w.week === selectedWeek!.week - 1,
    );
    if (!prevWeek) return null;

    const prevRecs = filterByWeek(filteredRecords, prevWeek.year, prevWeek.week);

    if (weekRecords.length === 0 || prevRecs.length === 0) return null;

    const curLower = Math.min(...weekRecords.map((r) => r.price_min));
    const curUpper = Math.max(...weekRecords.map((r) => r.price_max));
    const prevLower = Math.min(...prevRecs.map((r) => r.price_min));
    const prevUpper = Math.max(...prevRecs.map((r) => r.price_max));

    return {
      prevLow: prevLower,
      prevUpper: prevUpper,
      lowerChange: curLower - prevLower,
      upperChange: curUpper - prevUpper,
      lowerPct: prevLower > 0 ? ((curLower - prevLower) / prevLower) * 100 : 0,
      upperPct: prevUpper > 0 ? ((curUpper - prevUpper) / prevUpper) * 100 : 0,
    };
  });

  let contextWindow = $state(3);

  function getWeekSpreadMap(): Map<string, { min: number; max: number }> {
    if (weekRanges) {
      const map = new Map<string, { min: number; max: number }>();
      for (const [market, years] of Object.entries(weekRanges)) {
        if (!markets.has(market)) continue;
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
    const map = new Map<string, { min: number; max: number }>();
    for (const r of filteredRecords) {
      const d = r.date;
      const yearStart = new Date(d.getFullYear(), 0, 1);
      const weekNum = Math.ceil(
        ((d.getTime() - yearStart.getTime()) / 86400000 + d.getDay() + 1) / 7,
      );
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
  function getWeekSpread(yr: number, wk: number) {
    return weekSpreadMap.get(`${yr}-${wk}`) ?? null;
  }

  let chartData = $derived.by(() => {
    if (!selectedWeek) return null;
    const win = contextWindow; // 3
    const labels: string[] = [];
    const currentData: ({ min: number; max: number } | null)[] = [];
    const yr1Data: ({ min: number; max: number } | null)[] = [];

    // Center the window on the selected week's ISO week
    for (let delta = -win; delta <= win; delta++) {
      const { year: cy, week: cw } = addWeeksToISO(selectedWeek.year, selectedWeek.week, delta);
      labels.push(wednesdayOfWeek(cy, cw).slice(5));
      currentData.push(getWeekSpread(cy, cw));

      // Year-1: same ISO week number, previous calendar year
      const { year: y1y, week: y1w } = addWeeksToISO(selectedWeek.year - 1, selectedWeek.week, delta);
      yr1Data.push(getWeekSpread(y1y, y1w));
    }

    return { labels, currentData, yr1Data };
  });

  let globalYRange = $derived.by(() => {
    let gMin = Infinity,
      gMax = -Infinity;
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
    return {
      yMin: ticks[0] - range * 0.1,
      yMax: ticks[ticks.length - 1] + range * 0.1,
      ticks,
    };
  });

  let chartSvg = $derived.by(() => {
    if (!chartData || !globalYRange) return "";
    const { labels, currentData, yr1Data } = chartData;
    const n = labels.length;
    if (n === 0) return "";
    const w = 800,
      h = 320;
    const pad = { t: 20, r: 20, b: 40, l: 48 };
    const { yMin, yMax, ticks } = globalYRange;
    function getX(idx: number) {
      return pad.l + (idx / (n - 1 || 1)) * (w - pad.l - pad.r);
    }
    function getY(val: number) {
      return (
        pad.t + (1 - (val - yMin) / (yMax - yMin || 1)) * (h - pad.t - pad.b)
      );
    }

    let s = "";
    for (const v of ticks) {
      const y = getY(v);
      s += `<line x1="${pad.l}" y1="${y}" x2="${w - pad.r}" y2="${y}" stroke="var(--hairline)" stroke-width="1" />`;
      s += `<text x="${pad.l - 8}" y="${y + 4}" text-anchor="end" font-size="13" fill="var(--muted)">${v.toFixed(v % 1 === 0 ? 0 : 1)}</text>`;
    }

    // Past year: gray polygon with gap segments
    const pastSegs: { idx: number; pt: { min: number; max: number } }[][] = [];
    let curSeg: { idx: number; pt: { min: number; max: number } }[] = [];
    yr1Data.forEach((pt, i) => {
      if (pt) {
        curSeg.push({ idx: i, pt });
      } else {
        if (curSeg.length) { pastSegs.push(curSeg); curSeg = []; }
      }
    });
    if (curSeg.length) pastSegs.push(curSeg);

    for (const seg of pastSegs) {
      if (seg.length < 2) continue;
      let d = `M ${getX(seg[0].idx)} ${getY(seg[0].pt.max)}`;
      for (let i = 1; i < seg.length; i++) d += ` L ${getX(seg[i].idx)} ${getY(seg[i].pt.max)}`;
      for (let i = seg.length - 1; i >= 0; i--) d += ` L ${getX(seg[i].idx)} ${getY(seg[i].pt.min)}`;
      d += ' Z';
      s += `<path d="${d}" fill="var(--muted)" opacity="0.12" />`;
    }

    // Current year: pair of lines with gap segments
    const curSegs: { idx: number; pt: { min: number; max: number } }[][] = [];
    let cSeg: { idx: number; pt: { min: number; max: number } }[] = [];
    currentData.forEach((pt, i) => {
      if (pt) {
        cSeg.push({ idx: i, pt });
      } else {
        if (cSeg.length) { curSegs.push(cSeg); cSeg = []; }
      }
    });
    if (cSeg.length) curSegs.push(cSeg);

    for (const seg of curSegs) {
      if (seg.length < 2) continue;
      let dMax = `M ${getX(seg[0].idx)} ${getY(seg[0].pt.max)}`;
      let dMin = `M ${getX(seg[0].idx)} ${getY(seg[0].pt.min)}`;
      for (let i = 1; i < seg.length; i++) {
        dMax += ` L ${getX(seg[i].idx)} ${getY(seg[i].pt.max)}`;
        dMin += ` L ${getX(seg[i].idx)} ${getY(seg[i].pt.min)}`;
      }
      s += `<path d="${dMax}" fill="none" stroke="var(--ink)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />`;
      s += `<path d="${dMin}" fill="none" stroke="var(--ink)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />`;
    }

    // Crosshair dots at center (always index = contextWindow)
    const crosshairIdx = contextWindow;
    if (crosshairIdx >= 0 && crosshairIdx < n) {
      const cx = getX(crosshairIdx);
      const curPt = currentData[crosshairIdx];
      if (curPt) {
        s += `<circle cx="${cx}" cy="${getY(curPt.max)}" r="4.5" fill="var(--bg)" stroke="var(--accent)" stroke-width="2.5" />`;
        s += `<circle cx="${cx}" cy="${getY(curPt.min)}" r="4.5" fill="var(--bg)" stroke="var(--accent)" stroke-width="2.5" />`;
      }
    }

    // X-axis labels
    labels.forEach((label, i) => {
      if (label) {
        const isCenter = i === crosshairIdx;
        s += `<text x="${getX(i)}" y="${h - 12}" font-size="12" fill="${isCenter ? "var(--accent)" : "var(--muted)"}" font-weight="${isCenter ? "600" : "400"}" text-anchor="middle">${label}</text>`;
      }
    });
    return s;
  });
</script>

<!-- Stat Row -->
<div class="stat-row">
  <div class="date-widget">
    <span class="meta-label">Tydzień</span>
    <div class="date-selector-wrapper">
      <button
        class="date-nav-btn date-nav-prev"
        onclick={goPrevWeek}
        disabled={sliderValue <= 0}
        aria-label="Poprzedni tydzień"
      >
        <svg
          viewBox="0 0 24 24"
          width="17"
          height="17"
          stroke="currentColor"
          stroke-width="2.2"
          fill="none"
          stroke-linecap="round"
          stroke-linejoin="round"
          ><polyline points="15 18 9 12 15 6"></polyline></svg
        >
      </button>
      <div class="date-select-wrap">
        <select
          class="date-select tabular-nums"
          value={sliderValue}
          onchange={onDateSelectChange}
        >
          {#each weekLabels as label, idx}
            <option value={idx}>{label}</option>
          {/each}
        </select>
        <div class="date-select-arrow">
          <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </div>
      <button
        class="date-nav-btn date-nav-next"
        onclick={goNextWeek}
        disabled={sliderValue >= allWeekList.length - 1}
        aria-label="Następny tydzień"
      >
        <svg
          viewBox="0 0 24 24"
          width="17"
          height="17"
          stroke="currentColor"
          stroke-width="2.2"
          fill="none"
          stroke-linecap="round"
          stroke-linejoin="round"
          ><polyline points="9 18 15 12 9 6"></polyline></svg
        >
      </button>
    </div>
  </div>

  <div class="stat-block">
    <span class="meta-label">Przedział Cenowy</span>
    <div class="stat-value tabular-nums">{kpis.priceRange}</div>
    <div class="compare-group">
      <span class="compare-label">Tydzień wcześniej:</span>
      {#if wowChange}
        <div class="compare-row">
          <span class="compare-range"
            >{formatPrice(wowChange.prevLow)} - {formatPrice(
              wowChange.prevUpper,
            )}</span
          >
          <span class="compare-sep">|</span>
          <span class="compare-pair">
            <span
              class="compare-change"
              class:change-up={wowChange.lowerChange > 0}
              class:change-down={wowChange.lowerChange < 0}
              class:change-flat={wowChange.lowerChange === 0}
              >{wowChange.lowerChange > 0 ? "+" : ""}{wowChange.lowerChange === 0 ? "\u00a0" : ""}{formatPrice(
                wowChange.lowerChange,
              )}</span
            >
            <span
              class="compare-change"
              class:change-up={wowChange.upperChange > 0}
              class:change-down={wowChange.upperChange < 0}
              class:change-flat={wowChange.upperChange === 0}
              >{wowChange.upperChange > 0 ? "+" : ""}{wowChange.upperChange === 0 ? "\u00a0" : ""}{formatPrice(
                wowChange.upperChange,
              )}</span
            >
          </span>
          <span class="compare-sep">|</span>
          <span class="compare-pair">
            <span
              class="compare-pct"
              class:change-up={wowChange.lowerPct > 0}
              class:change-down={wowChange.lowerPct < 0}
              class:change-flat={wowChange.lowerPct === 0}
              >{wowChange.lowerPct > 0 ? "+" : ""}{wowChange.lowerPct === 0 ? "\u00a0" : ""}{wowChange.lowerPct.toFixed(
                1,
              )}%
              </span>
            <span
              class="compare-pct"
              class:change-up={wowChange.upperPct > 0}
              class:change-down={wowChange.upperPct < 0}
              class:change-flat={wowChange.upperPct === 0}
              >{wowChange.upperPct > 0 ? "+" : ""}{wowChange.upperPct === 0 ? "\u00a0" : ""}{wowChange.upperPct.toFixed(
                1,
              )}%
              </span>
          </span>
        </div>
      {:else}
        <div class="compare-row">
          <span class="compare-sep">Brak danych</span>
        </div>
      {/if}
    </div>
    <div class="compare-group">
      <span class="compare-label">Rok wcześniej:</span>
      {#if ytyChange}
        <div class="compare-row">
          <span class="compare-range"
            >{formatPrice(ytyChange.prevLow)} - {formatPrice(
              ytyChange.prevUpper,
            )}</span
          >
          <span class="compare-sep">|</span>
          <span class="compare-pair">
            <span
              class="compare-change"
              class:change-up={ytyChange.lowerChange > 0}
              class:change-down={ytyChange.lowerChange < 0}
              class:change-flat={ytyChange.lowerChange === 0}
            >
              {ytyChange.lowerChange > 0 ? "+" : ""}{ytyChange.lowerChange === 0 ? "\u00a0" : ""}{formatPrice(
                ytyChange.lowerChange,
              )}
            </span>
            <span
              class="compare-change"
              class:change-up={ytyChange.upperChange > 0}
              class:change-down={ytyChange.upperChange < 0}
              class:change-flat={ytyChange.upperChange === 0}
              >{ytyChange.upperChange > 0 ? "+" : ""}{ytyChange.upperChange === 0 ? "\u00a0" : ""}{formatPrice(
                ytyChange.upperChange,
              )}
            </span>
          </span>
          <span class="compare-sep">|</span>
          <span class="compare-pair">
            <span
              class="compare-pct"
              class:change-up={ytyChange.lowerPct > 0}
              class:change-down={ytyChange.lowerPct < 0}
              class:change-flat={ytyChange.lowerPct === 0}
              >{ytyChange.lowerPct > 0 ? "+" : ""}{ytyChange.lowerPct === 0 ? "\u00a0" : ""}{ytyChange.lowerPct.toFixed(
                1,
              )}%</span
            >
            <span
              class="compare-pct"
              class:change-up={ytyChange.upperPct > 0}
              class:change-down={ytyChange.upperPct < 0}
              class:change-flat={ytyChange.upperPct === 0}
              >{ytyChange.upperPct > 0 ? "+" : ""}{ytyChange.upperPct === 0 ? "\u00a0" : ""}{ytyChange.upperPct.toFixed(
                1,
              )}%</span
            >
          </span>
        </div>
      {:else}
        <div class="compare-row">
          <span class="compare-sep">Brak danych</span>
        </div>
      {/if}
    </div>
  </div>
</div>

<!-- Chart -->
{#if records.length > 0}
  <div class="chart-header">
    <div class="chart-title">
      Kontekst Sezonowy (+/-{contextWindow} Tygodni)
    </div>
    <div class="chart-legend">
      <div class="legend-item">
        <div class="legend-swatch past-swatch"></div>
        Rok wcześniej
      </div>
      <div class="legend-item">
        <div class="legend-swatch current-swatch"></div>
        Aktualny Rok
      </div>
    </div>
  </div>
  <div class="svg-chart-container">
    {#if chartSvg}
      <svg viewBox="0 0 800 320" preserveAspectRatio="xMidYMid meet"
        >{@html chartSvg}</svg
      >
    {:else}
      <svg viewBox="0 0 800 320" preserveAspectRatio="xMidYMid meet">
        <text
          x="400"
          y="160"
          text-anchor="middle"
          fill="var(--muted)"
          font-size="14">Brak danych w wybranym oknie czasowym</text
        >
      </svg>
    {/if}
  </div>
{:else}
  <div class="empty-state">
    <p class="empty-title">Brak danych</p>
    <p class="empty-desc">
      Dla wybranego produktu i rynków nie ma danych w archiwum. Wybierz inny
      produkt lub zmień filtrowanie rynków.
    </p>
  </div>
{/if}

<style>
  .stat-row {
    display: flex;
    align-items: stretch;
    padding-bottom: 24px;
    margin-bottom: 24px;
    border-bottom: 1px solid var(--hairline);
  }

  /* Date widget */
  .date-widget {
    flex: 0 0 160px;
    padding-right: 20px;
    border-right: 1px solid var(--hairline);
    display: flex;
    flex-direction: column;
    align-self: stretch;
  }

  .date-selector-wrapper {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 6px;
  }

  /* In wide screen: select on top row, both buttons on bottom row */
  .date-nav-prev { order: 1; }
  .date-nav-next { order: 2; }

  .date-nav-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 36px;
    flex: none;
    background: none;
    border: 1px solid var(--hairline-strong);
    border-radius: 6px;
    color: var(--ink);
    cursor: pointer;
    padding: 0;
    transition: border-color 0.15s ease;
  }

  .date-nav-btn:hover:not(:disabled) {
    border-color: var(--ink);
  }

  .date-nav-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .date-select-wrap {
    flex: 1 0 100%;
    min-width: 0;
    position: relative;
  }

  .date-select {
    width: 100%;
    min-width: 0;
    padding: 8px 30px 8px 10px;
    border: 1px solid var(--hairline-strong);
    border-radius: 6px;
    background-color: var(--bg);
    font-family: inherit;
    font-size: 13px;
    font-weight: 500;
    color: var(--ink);
    outline: none;
    -webkit-appearance: none;
    appearance: none;
    cursor: pointer;
    transition: border-color 0.15s ease;
  }

  .date-select:hover {
    border-color: var(--muted);
  }

  .date-select-arrow {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    pointer-events: none;
    color: var(--muted);
    display: flex;
  }

  /* Stat block */
  .stat-block {
    flex: 1 1 0%;
    padding-left: 20px;
    min-width: 0;
  }

  .stat-value {
    font-size: 32px;
    font-weight: 700;
    margin: 4px 0 16px;
    line-height: 1.1;
    color: var(--ink);
  }

  .compare-group {
    display: flex;
    align-items: baseline;
    gap: 16px;
    padding: 6px 0;
    flex-wrap: wrap;
  }

  .compare-group + .compare-group {
    border-top: 1px solid var(--hairline);
    margin-top: 2px;
  }

  .compare-label {
    font-size: 12px;
    color: var(--muted);
    width: 110px;
    flex-shrink: 0;
    white-space: nowrap;
  }

  /* Natural flex row layout */
  .compare-row {
    display: flex;
    align-items: center;
    gap: 12px;
    font-variant-numeric: tabular-nums;
  }

  .compare-range {
    font-size: 13px;
    font-weight: 600;
    color: var(--ink);
    white-space: nowrap;
  }

  .compare-sep {
    color: var(--hairline-strong);
    font-weight: 300;
    user-select: none;
    padding: 0 4px;
  }

  /* Tight flex pairs without text-align: right whitespace gaps */
  .compare-pair {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .compare-change,
  .compare-pct {
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
    text-align: left; /* Left-align so numbers sit right next to the separator */
  }

  /* Status Colors */
  .change-up {
    color: var(--accent);
  }
  .change-down {
    color: #2d7a4f;
  }
  .change-flat {
    color: var(--muted);
  }

  .meta-label {
    margin-bottom: 4px;
  }

  /* Chart Layout */
  .legend-swatch {
    width: 16px;
    height: 12px;
  }

  .past-swatch {
    background: var(--muted);
    opacity: 0.35;
  }

  .current-swatch {
    background: none;
    border: 2px solid var(--ink);
  }

  .svg-chart-container {
    width: 100%;
  }

  .svg-chart-container :global(text) {
    font-family: inherit;
  }

  /* Responsive breakpoints */
  @media (max-width: 1350px) {
    .stat-row {
      flex-direction: column;
      gap: 0;
      align-items: stretch;
    }

    .date-widget {
      flex: none;
      width: 100%;
      border-right: none;
      padding-right: 0;
      padding-bottom: 16px;
      margin-bottom: 16px;
      border-bottom: 1px solid var(--hairline);
    }

    .date-selector-wrapper {
      flex-wrap: nowrap;
      align-items: center;
      gap: 8px;
    }

    /* In row mode (narrow screen): natural DOM order [prev | select | next] */
    .date-nav-prev,
    .date-nav-next {
      order: 0;
    }

    .date-select-wrap {
      flex: 0 1 auto;
      max-width: 220px;
    }

    .stat-block {
      padding-left: 0;
    }
  }

  @media (max-width: 600px) {
    .stat-value {
      font-size: 26px;
    }

    .compare-group {
      flex-direction: column;
      align-items: flex-start;
      gap: 4px;
    }

    .compare-label {
      width: auto;
    }

    .compare-row {
      gap: 8px;
      flex-wrap: wrap;
    }

    .date-nav-btn {
      width: 44px;
      height: 40px;
    }

    .svg-chart-container :global(text) {
      font-size: 14px;
    }
  }

  @media (max-width: 400px) {
    .stat-value { font-size: 22px; }
    .compare-range { font-size: 12px; }
    .compare-change, .compare-pct { font-size: 12px; }
    .compare-label { font-size: 11px; }

    .svg-chart-container :global(text) {
      font-size: 14px;
    }
  }
</style>