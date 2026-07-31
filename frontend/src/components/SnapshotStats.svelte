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
    mergeEnvelope,
    computeKpis,
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

  let allWeekList = $derived(allWeeks(records));
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
    return filterByWeek(records, selectedWeek.year, selectedWeek.week);
  });

  let filteredWeekRecords = $derived.by(() => {
    if (markets.size === 0) return weekRecords;
    return weekRecords.filter((r) => markets.has(r.place));
  });

  let kpis = $derived.by(() => {
    const k = computeKpis(filteredWeekRecords);
    if (!k)
      return { priceRange: "–", spread: "–", overallMin: 0, overallMax: 0 };
    return k;
  });

  let ytyChange: ComparisonChange | null = $derived.by(() => {
    if (!selectedWeek || records.length === 0) return null;

    const targetYear = selectedWeek.year - 1;

    const curRecs = filterByWeek(
      records,
      selectedWeek.year,
      selectedWeek.week,
    ).filter((r) => markets.size === 0 || markets.has(r.place));

    const prevRecs = filterByWeek(
      records,
      targetYear,
      selectedWeek.week,
    ).filter((r) => markets.size === 0 || markets.has(r.place));

    if (curRecs.length === 0 || prevRecs.length === 0) return null;

    const curLower = Math.min(...curRecs.map((r) => r.price_min));
    const curUpper = Math.max(...curRecs.map((r) => r.price_max));
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

    const curRecs = filterByWeek(
      records,
      selectedWeek.year,
      selectedWeek.week,
    ).filter((r) => markets.size === 0 || markets.has(r.place));

    const prevRecs = filterByWeek(records, prevWeek.year, prevWeek.week).filter(
      (r) => markets.size === 0 || markets.has(r.place),
    );

    if (curRecs.length === 0 || prevRecs.length === 0) return null;

    const curLower = Math.min(...curRecs.map((r) => r.price_min));
    const curUpper = Math.max(...curRecs.map((r) => r.price_max));
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
    const map = new Map<string, { min: number; max: number }>();
    for (const r of records) {
      if (markets.size > 0 && !markets.has(r.place)) continue;
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
    const curIdx = allWeekList.findIndex(
      (w) => w.year === selectedWeek!.year && w.week === selectedWeek!.week,
    );
    if (curIdx < 0) return null;
    const win = contextWindow;
    const listLen = allWeekList.length;
    let startIdx = curIdx - win;
    let endIdx = curIdx + win;
    if (startIdx < 0) {
      startIdx = 0;
      endIdx = Math.min(win * 2, listLen - 1);
    }
    if (endIdx >= listLen) {
      endIdx = listLen - 1;
      startIdx = Math.max(0, endIdx - win * 2);
    }
    const labels: string[] = [];
    const currentData: ({ min: number; max: number } | null)[] = [];
    const yr1Data: ({ min: number; max: number } | null)[] = [];
    const yr2Data: ({ min: number; max: number } | null)[] = [];
    for (let i = startIdx; i <= endIdx; i++) {
      if (i < 0 || i >= allWeekList.length) {
        labels.push("");
        currentData.push(null);
        yr1Data.push(null);
        yr2Data.push(null);
        continue;
      }
      const baseWeek = allWeekList[i];
      labels.push(wednesdayOfWeek(baseWeek.year, baseWeek.week).slice(5));
      currentData.push(getWeekSpread(baseWeek.year, baseWeek.week));
      const yr1Idx = i - 52;
      yr1Data.push(
        yr1Idx >= 0 && yr1Idx < allWeekList.length
          ? getWeekSpread(allWeekList[yr1Idx].year, allWeekList[yr1Idx].week)
          : null,
      );
      const yr2Idx = i - 104;
      yr2Data.push(
        yr2Idx >= 0 && yr2Idx < allWeekList.length
          ? getWeekSpread(allWeekList[yr2Idx].year, allWeekList[yr2Idx].week)
          : null,
      );
    }
    return { labels, currentData, yr1Data, yr2Data, startIdx };
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
    const { labels, currentData, yr1Data, yr2Data, startIdx } = chartData;
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
    function buildLinePath(
      dataset: ({ min: number; max: number } | null)[],
      type: "min" | "max",
    ) {
      const pts: string[] = [];
      dataset.forEach((pt, i) => {
        if (pt)
          pts.push(
            `${pts.length === 0 ? "M" : "L"} ${getX(i)} ${getY(pt[type])}`,
          );
      });
      return pts.join(" ");
    }
    let crosshairIdx = -1;
    if (selectedWeek) {
      const curIdx = allWeekList.findIndex(
        (w) => w.year === selectedWeek!.year && w.week === selectedWeek!.week,
      );
      crosshairIdx = curIdx - startIdx;
      if (crosshairIdx < 0 || crosshairIdx >= n) crosshairIdx = -1;
    }
    let s = "";
    for (const v of ticks) {
      const y = getY(v);
      s += `<line x1="${pad.l}" y1="${y}" x2="${w - pad.r}" y2="${y}" stroke="var(--hairline)" stroke-width="1" />`;
      s += `<text x="${pad.l - 8}" y="${y + 4}" text-anchor="end" font-size="12" fill="var(--muted)">${v.toFixed(v % 1 === 0 ? 0 : 1)}</text>`;
    }
    // Past years: dashed
    const pastTopPath = buildLinePath(yr1Data, "max");
    const pastBotPath = buildLinePath(yr1Data, "min");
    if (pastTopPath)
      s += `<path d="${pastTopPath}" fill="none" stroke="var(--muted)" stroke-width="1.5" stroke-dasharray="4,4" stroke-linejoin="round" />`;
    if (pastBotPath)
      s += `<path d="${pastBotPath}" fill="none" stroke="var(--muted)" stroke-width="1.5" stroke-dasharray="4,4" stroke-linejoin="round" />`;
    // Current year: solid
    const curTopPath = buildLinePath(currentData, "max");
    const curBotPath = buildLinePath(currentData, "min");
    if (curTopPath)
      s += `<path d="${curTopPath}" fill="none" stroke="var(--ink)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />`;
    if (curBotPath)
      s += `<path d="${curBotPath}" fill="none" stroke="var(--ink)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />`;
    // Crosshair dots
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
        s += `<text x="${getX(i)}" y="${h - 12}" font-size="11" fill="${isCenter ? "var(--accent)" : "var(--muted)"}" font-weight="${isCenter ? "600" : "400"}" text-anchor="middle">${label}</text>`;
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
          width="15"
          height="15"
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
      </div>
      <button
        class="date-nav-btn date-nav-next"
        onclick={goNextWeek}
        disabled={sliderValue >= allWeekList.length - 1}
        aria-label="Następny tydzień"
      >
        <svg
          viewBox="0 0 24 24"
          width="15"
          height="15"
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
              >{wowChange.lowerChange > 0 ? "+" : ""}{formatPrice(
                wowChange.lowerChange,
              )}</span
            >
            <span
              class="compare-change"
              class:change-up={wowChange.upperChange > 0}
              class:change-down={wowChange.upperChange < 0}
              class:change-flat={wowChange.upperChange === 0}
              >{wowChange.upperChange > 0 ? "+" : ""}{formatPrice(
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
              >{wowChange.lowerPct > 0 ? "+" : ""}{wowChange.lowerPct.toFixed(
                1,
              )}%
              </span>
            <span
              class="compare-pct"
              class:change-up={wowChange.upperPct > 0}
              class:change-down={wowChange.upperPct < 0}
              class:change-flat={wowChange.upperPct === 0}
              >{wowChange.upperPct > 0 ? "+" : ""}{wowChange.upperPct.toFixed(
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
              {ytyChange.lowerChange > 0 ? "+" : ""}{formatPrice(
                ytyChange.lowerChange,
              )}
            </span>
            <span
              class="compare-change"
              class:change-up={ytyChange.upperChange > 0}
              class:change-down={ytyChange.upperChange < 0}
              class:change-flat={ytyChange.upperChange === 0}
              >{ytyChange.upperChange > 0 ? "+" : ""}{formatPrice(
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
              >{ytyChange.lowerPct > 0 ? "+" : ""}{ytyChange.lowerPct.toFixed(
                1,
              )}%</span
            >
            <span
              class="compare-pct"
              class:change-up={ytyChange.upperPct > 0}
              class:change-down={ytyChange.upperPct < 0}
              class:change-flat={ytyChange.upperPct === 0}
              >{ytyChange.upperPct > 0 ? "+" : ""}{ytyChange.upperPct.toFixed(
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
        Lata ubiegłe
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
    width: 36px;
    height: 32px;
    flex: none;
    background: none;
    border: 1px solid var(--hairline-strong);
    border-radius: 6px;
    color: var(--ink);
    cursor: pointer;
    padding: 0;
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
  }

  .date-select {
    width: 100%;
    min-width: 0;
    font-family: inherit;
    font-size: 16px;
    font-weight: 600;
    color: var(--ink);
    background: none;
    border: none;
    outline: none;
    cursor: pointer;
    text-align: left;
    text-overflow: ellipsis;
    white-space: nowrap;
    overflow: hidden;
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
    height: 0;
    border-top: 2px solid;
  }

  .past-swatch {
    border-color: var(--muted);
    border-top-style: dashed;
  }

  .current-swatch {
    border-color: var(--ink);
  }

  .svg-chart-container {
    width: 100%;
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
      flex: 1 1 0%;
      min-width: 0;
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
      height: 36px;
    }
  }
</style>