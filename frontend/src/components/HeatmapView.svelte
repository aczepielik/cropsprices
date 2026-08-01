<!--
  HeatmapView.svelte — Seasonal heatmap showing price patterns across years.

  New design: warm amber → rust sequential color ramp (replaces green).
  Legend row below the chart. Thin hairline rules.
-->

<script lang="ts">
  import type { PriceRecord, HeatmapCell } from '../lib/types';
  import { aggregateByWeekYear, filterByMarkets } from '../lib/filters';
  import { getISOWeek, getYear, niceTicks } from '../lib/helpers';
  import { debug } from '../lib/logger';

  const log = debug('HeatmapView');

  let { records, markets }: {
    records: PriceRecord[];
    markets: Set<string>;
  } = $props();

  let containerEl: HTMLDivElement;
  let containerWidth = $state(960);

  // Warm amber → rust sequential color ramp (matching the mock)
  function heatColor(value: number, min: number, max: number): string {
    if (isNaN(value)) return '#f0ece3';
    if (max === min) return '#f6ecd9';
    const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
    const stops = [
      [246, 236, 217],
      [234, 182, 118],
      [209, 115, 47],
      [168, 70, 31],
      [92, 35, 17],
    ];
    const seg = t * (stops.length - 1);
    const i = Math.min(stops.length - 2, Math.floor(seg));
    const f = seg - i;
    const c0 = stops[i], c1 = stops[i + 1];
    const r = Math.round(c0[0] + (c1[0] - c0[0]) * f);
    const g = Math.round(c0[1] + (c1[1] - c0[1]) * f);
    const b = Math.round(c0[2] + (c1[2] - c0[2]) * f);
    return `rgb(${r},${g},${b})`;
  }

  let cells = $derived.by(() => {
    const filtered = filterByMarkets(records, markets);
    const agg = aggregateByWeekYear(filtered);
    const result: HeatmapCell[] = [];
    let globalMin = Infinity;
    let globalMax = -Infinity;
    for (const [key, data] of agg) {
      const [yearStr, weekStr] = key.split('-');
      result.push({ year: Number(yearStr), week: Number(weekStr), ...data });
      globalMin = Math.min(globalMin, data.ribbonMin);
      globalMax = Math.max(globalMax, data.ribbonMax);
    }
    log('cells computed', { recordsLen: records.length, cellsLen: result.length });
    return { cells: result, globalMin, globalMax };
  });

  const years = $derived([...new Set(cells.cells.map(c => c.year))].sort());
  const MAX_WEEKS = 53;

  const monthNames = ['Sty','Lut','Mar','Kwi','Maj','Cze','Lip','Sie','Wrz','Paź','Lis','Gru'];
  const monthStarts = [1, 5, 9, 14, 18, 23, 27, 32, 36, 41, 45, 49];

  interface CellData {
    year: number;
    week: number;
    value: number;
    ribbonMin: number;
    ribbonMax: number;
  }

  let cellMap = $derived(() => {
    const m = new Map<string, CellData>();
    for (const c of cells.cells) {
      m.set(`${c.year}-${c.week}`, c);
    }
    return m;
  });

  let globalPriceMin = $derived(() => {
    let v = Infinity;
    for (const c of cells.cells) {
      if (c.ribbonMin < v) v = c.ribbonMin;
    }
    return v;
  });

  let globalPriceMax = $derived(() => {
    let v = -Infinity;
    for (const c of cells.cells) {
      if (c.ribbonMax > v) v = c.ribbonMax;
    }
    return v;
  });

  let yearAgg = $derived(() => {
    const agg = new Map<number, { overallMin: number; overallMax: number }>();
    for (const yr of years) {
      agg.set(yr, { overallMin: Infinity, overallMax: -Infinity });
    }
    for (const c of cells.cells) {
      const a = agg.get(c.year)!;
      if (c.ribbonMin < a.overallMin) a.overallMin = c.ribbonMin;
      if (c.ribbonMax > a.overallMax) a.overallMax = c.ribbonMax;
    }
    return agg;
  });

  const currentYear = $derived(years.length > 0 ? years[years.length - 1] : 0);

  $effect(() => {
    if (!containerEl) return;
    const ro = new ResizeObserver(entries => {
      for (const entry of entries) {
        containerWidth = entry.contentRect.width || 960;
      }
    });
    ro.observe(containerEl);
    return () => ro.disconnect();
  });

  let svgMarkup = $derived.by(() => {
    const cw = containerWidth;
    const cMap = cellMap();
    const yrList = years;
    const pMin = globalPriceMin();
    const pMax = globalPriceMax();
    const yAgg = yearAgg();
    if (yrList.length === 0 || cells.cells.length === 0) return '';

    const hmML = 56;
    const hmMT = 40;
    const cellW = Math.max(10, Math.min(18, (cw - hmML - 220) / MAX_WEEKS));
    const cellH = 32;
    const hmW = MAX_WEEKS * cellW;
    const hmH = yrList.length * cellH;
    const hmR = hmML + hmW;
    const hmB = hmMT + hmH;
    const gap = 32;
    const bmT = hmB + 46;
    const bmH = 140;
    const bmB = bmT + bmH;
    const rmL = hmR + gap;
    const rmW = 150;
    const svgW = rmL + rmW + 20;
    const svgH = bmB + 16;

    function weekX(wn: number) { return hmML + (wn - 0.5) * cellW; }
    function yearMidY(idx: number) { return hmMT + (idx + 0.5) * cellH; }
    function priceY(val: number) { return bmB - ((val - bmYMin) / (bmYMax - bmYMin || 1)) * bmH; }
    function priceX(val: number) { return rmL + ((val - pMin) / (pMax - pMin || 1)) * rmW; }

    let s = '';

    // Month gridlines
    monthStarts.forEach((w, mi) => {
      if (w <= MAX_WEEKS) {
        const x = weekX(w);
        s += `<line x1="${x}" y1="${hmMT}" x2="${x}" y2="${hmB}" stroke="var(--missing)" stroke-width="1" />`;
        s += `<text x="${x + 2}" y="${hmMT - 10}" font-size="12" fill="var(--muted)" text-anchor="start" font-weight="400">${monthNames[mi]}</text>`;
      }
    });

    // Year rows + labels
    yrList.forEach((yr, yi) => {
      const y = hmMT + yi * cellH;
      s += `<line x1="${hmML}" y1="${y}" x2="${hmR}" y2="${y}" stroke="var(--missing)" stroke-width="0.75" />`;
      s += `<text x="${hmML - 10}" y="${yearMidY(yi) + 4}" font-size="13" font-weight="500" fill="var(--ink)" text-anchor="end">${yr}</text>`;
    });
    s += `<line x1="${hmML}" y1="${hmB}" x2="${hmR}" y2="${hmB}" stroke="var(--hairline-strong)" stroke-width="1" />`;

    // Blank cells
    yrList.forEach((yr, yi) => {
      for (let w = 1; w <= MAX_WEEKS; w++) {
        if (!cMap.has(`${yr}-${w}`)) {
          const x = hmML + (w - 1) * cellW;
          const y = hmMT + yi * cellH;
          s += `<rect x="${x + 1}" y="${y + 2}" width="${Math.max(1, cellW - 2)}" height="${cellH - 4}" fill="#f5f2ec" />`;
        }
      }
    });

    // Heat cells
    for (const c of cells.cells) {
      const yi = yrList.indexOf(c.year);
      if (yi < 0) continue;
      const t = (c.value - pMin) / (pMax - pMin || 1);
      const x = hmML + (c.week - 1) * cellW;
      const y = hmMT + yi * cellH;
      s += `<rect x="${x + 1}" y="${y + 2}" width="${Math.max(1, cellW - 2)}" height="${cellH - 4}" fill="${heatColor(c.value, pMin, pMax)}"><title>${c.year} T${c.week}: ${c.value.toFixed(2)} zł</title></rect>`;
    }

    // Week labels
    for (let w = 1; w <= MAX_WEEKS; w += 4) {
      s += `<text x="${weekX(w)}" y="${hmB + 16}" font-size="11" fill="var(--muted)" text-anchor="middle">T${w}</text>`;
    }

    // ── BOTTOM MARGINAL ──
    s += `<text x="${hmML}" y="${bmT - 12}" font-size="12" fill="var(--ink)">Zakres cen (min\u2013max) (z\u0142)</text>`;
    s += `<line x1="${hmML}" y1="${bmB}" x2="${hmR}" y2="${bmB}" stroke="var(--hairline-strong)" stroke-width="1" />`;

    const bmTicks = niceTicks(pMin, pMax, 4);
    const bmDataRange = bmTicks[bmTicks.length - 1] - bmTicks[0];
    const bmYMin = bmTicks[0] - bmDataRange * 0.1;
    const bmYMax = bmTicks[bmTicks.length - 1] + bmDataRange * 0.1;
    bmTicks.forEach(pv => {
      const y = priceY(pv);
      s += `<line x1="${hmML}" y1="${y}" x2="${hmR}" y2="${y}" stroke="var(--missing)" stroke-width="0.75" />`;
      s += `<text x="${hmML - 6}" y="${y + 4}" font-size="11" fill="var(--muted)" text-anchor="end">${pv.toFixed(pv % 1 === 0 ? 0 : 1)}</text>`;
    });

    // Past years band
    const pastWeeks = new Map<number, { ribbonMin: number; ribbonMax: number }>();
    for (const c of cells.cells) {
      if (c.year === currentYear) continue;
      const existing = pastWeeks.get(c.week);
      if (existing) {
        existing.ribbonMin = Math.min(existing.ribbonMin, c.ribbonMin);
        existing.ribbonMax = Math.max(existing.ribbonMax, c.ribbonMax);
      } else {
        pastWeeks.set(c.week, { ribbonMin: c.ribbonMin, ribbonMax: c.ribbonMax });
      }
    }
    const pastSorted = [...pastWeeks.entries()].sort((a, b) => a[0] - b[0]);
    const pastSegs: { week: number; ribbonMin: number; ribbonMax: number }[][] = [];
    let cur: { week: number; ribbonMin: number; ribbonMax: number }[] = [];
    for (const [w, v] of pastSorted) {
      if (cur.length && w - cur[cur.length - 1].week > 1) { pastSegs.push(cur); cur = []; }
      cur.push({ week: w, ribbonMin: v.ribbonMin, ribbonMax: v.ribbonMax });
    }
    if (cur.length) pastSegs.push(cur);
    for (const seg of pastSegs) {
      if (seg.length < 2) continue;
      let d = `M ${weekX(seg[0].week)} ${priceY(seg[0].ribbonMax)}`;
      for (let i = 1; i < seg.length; i++) d += ` L ${weekX(seg[i].week)} ${priceY(seg[i].ribbonMax)}`;
      for (let i = seg.length - 1; i >= 0; i--) d += ` L ${weekX(seg[i].week)} ${priceY(seg[i].ribbonMin)}`;
      d += ' Z';
      s += `<path d="${d}" fill="var(--muted)" opacity="0.12" />`;
    }

    // Current year band
    const curWeeks = cells.cells.filter(c => c.year === currentYear).sort((a, b) => a.week - b.week);
    const curSegs: { week: number; ribbonMin: number; ribbonMax: number }[][] = [];
    let seg: { week: number; ribbonMin: number; ribbonMax: number }[] = [];
    for (const c of curWeeks) {
      if (seg.length && c.week - seg[seg.length - 1].week > 1) { curSegs.push(seg); seg = []; }
      seg.push({ week: c.week, ribbonMin: c.ribbonMin, ribbonMax: c.ribbonMax });
    }
    if (seg.length) curSegs.push(seg);
    for (const s2 of curSegs) {
      if (s2.length < 2) continue;
      let dMax = `M ${weekX(s2[0].week)} ${priceY(s2[0].ribbonMax)}`;
      let dMin = `M ${weekX(s2[0].week)} ${priceY(s2[0].ribbonMin)}`;
      for (let i = 1; i < s2.length; i++) {
        dMax += ` L ${weekX(s2[i].week)} ${priceY(s2[i].ribbonMax)}`;
        dMin += ` L ${weekX(s2[i].week)} ${priceY(s2[i].ribbonMin)}`;
      }
      s += `<path d="${dMax}" fill="none" stroke="var(--ink)" stroke-width="1.5" />`;
      s += `<path d="${dMin}" fill="none" stroke="var(--ink)" stroke-width="1.5" />`;
    }

    // ── RIGHT MARGINAL ──
    s += `<text x="${rmL}" y="${hmMT - 12}" font-size="12" fill="var(--ink)">Cena wg roku (zł)</text>`;
    s += `<line x1="${rmL}" y1="${hmB}" x2="${rmL + rmW}" y2="${hmB}" stroke="var(--hairline-strong)" stroke-width="1" />`;

    const rmTicks = niceTicks(pMin, pMax, 3);
    rmTicks.forEach(pv => {
      const x = priceX(pv);
      s += `<line x1="${x}" y1="${hmMT}" x2="${x}" y2="${hmB}" stroke="var(--missing)" stroke-width="0.75" />`;
      s += `<text x="${x}" y="${hmB + 16}" font-size="11" fill="var(--muted)" text-anchor="middle">${pv.toFixed(pv % 1 === 0 ? 0 : 1)}</text>`;
    });

    const bandH = Math.min(cellH * 0.5, 15);
    yrList.forEach((yr, yi) => {
      const a = yAgg.get(yr)!;
      const ya = yearMidY(yi);
      const x1 = priceX(a.overallMin);
      const x2 = priceX(a.overallMax);
      const isCurrent = yr === currentYear;
      const label = `${a.overallMin.toFixed(1)}\u2013${a.overallMax.toFixed(1)}`;
      if (isCurrent) {
        s += `<rect x="${x1}" y="${ya - bandH/2}" width="${Math.max(2, x2 - x1)}" height="${bandH}" rx="2" fill="var(--accent)" opacity="0.16" stroke="var(--ink)" stroke-width="1.25" />`;
        s += `<text x="${Math.min(x2 + 6, rmL + rmW - label.length * 5.5 - 2)}" y="${ya + 3}" font-size="10" font-weight="600" fill="var(--ink)" text-anchor="start">${label}</text>`;
      } else {
        s += `<rect x="${x1}" y="${ya - bandH/2}" width="${Math.max(2, x2 - x1)}" height="${bandH}" rx="2" fill="var(--muted)" opacity="0.10" stroke="var(--muted)" stroke-width="0.5" />`;
        s += `<text x="${Math.min(x2 + 6, rmL + rmW - label.length * 5.5 - 2)}" y="${ya + 3}" font-size="10" fill="var(--muted)" text-anchor="start">${label}</text>`;
      }
    });

    return `<svg viewBox="0 0 ${svgW} ${svgH}" preserveAspectRatio="xMidYMid meet">${s}</svg>`;
  });
</script>

<div class="chart-header">
  <div class="chart-title">Mapa Cieplna Sezonowa (Tydzień × Rok)</div>
</div>

{#if cells.cells.length === 0}
  <div class="empty-state">
    <p class="empty-title">Brak danych</p>
    <p class="empty-desc">Dla wybranego produktu i rynków nie ma danych w archiwum. Wybierz inny produkt lub zmień filtrowanie rynków.</p>
  </div>
{:else}
  <div class="heatmap-scroll" bind:this={containerEl}>
    {@html svgMarkup}
  </div>
{/if}

<!-- Legend row -->
<div class="legend-row">
  <div class="legend-item"><div class="legend-swatch legend-gradient"></div>Śr. cena tyg. (niska → wysoka)</div>
  <div class="legend-item"><div class="legend-swatch legend-missing"></div>Brak danych</div>
  <div class="legend-item"><div class="legend-swatch legend-current"></div>Rok bieżący (zakres)</div>
  <div class="legend-item"><div class="legend-swatch legend-past"></div>Lata ubiegłe (zakres)</div>
</div>

<style>
  .heatmap-scroll {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    width: 100%;
  }

  .heatmap-scroll :global(svg) {
    width: 100%;
    height: auto;
  }

  .legend-item {
    gap: 8px;
    font-size: 12px;
    color: var(--muted);
  }

  .legend-gradient {
    background: linear-gradient(to right, #f6ecd9, #eab676, #d1732f, #a8461f, #5c2311);
  }

  .legend-missing { background: var(--missing); }
  .legend-current { background: none; border: 2px solid var(--ink); }
  .legend-past { background: var(--muted); opacity: 0.35; }

  @media (max-width: 768px) {
    .legend-row { gap: 16px; }
    .empty-state { padding: 40px 16px; }
  }
</style>
