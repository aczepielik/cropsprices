<script lang="ts">
  import type { PriceRecord, HeatmapCell } from '../lib/types';
  import { aggregateByWeekYear, filterByMarkets } from '../lib/filters';
  import { heatColor, getISOWeek, getYear, niceTicks } from '../lib/helpers';

  let { records, markets }: {
    records: PriceRecord[];
    markets: Set<string>;
  } = $props();

  let containerEl: HTMLDivElement;
  let containerWidth = $state(960);

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
    const hmMT = 44;
    const cellW = Math.max(10, Math.min(18, (cw - hmML - 220) / MAX_WEEKS));
    const cellH = 34;
    const hmW = MAX_WEEKS * cellW;
    const hmH = yrList.length * cellH;
    const hmR = hmML + hmW;
    const hmB = hmMT + hmH;
    const gap = 32;
    const bmT = hmB + 50;
    const bmH = 160;
    const bmB = bmT + bmH;
    const rmL = hmR + gap;
    const rmW = 150;
    const svgW = rmL + rmW + 20;
    const svgH = bmB + 70;

    function weekX(wn: number) { return hmML + (wn - 0.5) * cellW; }
    function yearMidY(idx: number) { return hmMT + (idx + 0.5) * cellH; }
    function priceY(val: number) { return bmB - ((val - pMin) / (pMax - pMin || 1)) * bmH; }
    function priceX(val: number) { return rmL + ((val - pMin) / (pMax - pMin || 1)) * rmW; }

    let s = '';

    s += `<defs>`;
    s += `<clipPath id="clip-bm"><rect x="${hmML}" y="${bmT}" width="${hmW}" height="${bmH}" /></clipPath>`;
    s += `<clipPath id="clip-rm"><rect x="${rmL}" y="${hmMT}" width="${rmW}" height="${hmH}" /></clipPath>`;
    s += `<linearGradient id="hg" x1="0" y1="0" x2="1" y2="0">`;
    for (let i = 0; i <= 10; i++) s += `<stop offset="${i*10}%" stop-color="${heatColor(pMin + (pMax - pMin) * i / 10, pMin, pMax)}" />`;
    s += `</linearGradient></defs>`;

    // Month ticks and labels
    monthStarts.forEach((w, mi) => {
      if (w <= MAX_WEEKS) {
        const x = weekX(w);
        s += `<line x1="${x}" y1="${hmMT}" x2="${x}" y2="${hmB}" stroke="var(--soft)" stroke-width="1" />`;
        s += `<text x="${x + 2}" y="${hmMT - 10}" font-size="11" fill="var(--muted)" text-anchor="start" font-weight="500">${monthNames[mi]}</text>`;
      }
    });

    // Year rows
    yrList.forEach((yr, yi) => {
      const y = hmMT + yi * cellH;
      s += `<line x1="${hmML}" y1="${y}" x2="${hmR}" y2="${y}" stroke="var(--rule)" stroke-width="0.5" />`;
      s += `<text x="${hmML - 10}" y="${yearMidY(yi) + 4}" font-size="13" font-weight="600" fill="var(--ink)" text-anchor="end">${yr}</text>`;
    });
    s += `<line x1="${hmML}" y1="${hmB}" x2="${hmR}" y2="${hmB}" stroke="var(--rule)" stroke-width="0.5" />`;

    // Blank cells (off-season)
    yrList.forEach((yr, yi) => {
      for (let w = 1; w <= MAX_WEEKS; w++) {
        if (!cMap.has(`${yr}-${w}`)) {
          const x = hmML + (w - 1) * cellW;
          const y = hmMT + yi * cellH;
          s += `<rect x="${x + 1}" y="${y + 2}" width="${Math.max(1, cellW - 2)}" height="${cellH - 4}" rx="1" fill="var(--pale)" />`;
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
      s += `<rect x="${x + 1}" y="${y + 2}" width="${Math.max(1, cellW - 2)}" height="${cellH - 4}" rx="2" fill="${heatColor(c.value, pMin, pMax)}"><title>${c.year} T${c.week}: ${c.value.toFixed(2)} zł</title></rect>`;
    }

    // Week labels
    for (let w = 1; w <= MAX_WEEKS; w += 4) {
      s += `<text x="${weekX(w)}" y="${hmB + 16}" font-size="10" fill="var(--muted)" text-anchor="middle">T${w}</text>`;
    }

    // Bottom marginal: weekly price ribbons
    s += `<text x="${hmML}" y="${bmT - 14}" font-size="12" font-weight="600" fill="var(--muted)">Cena (zł) — wstęgi tygodniowe</text>`;
    s += `<rect x="${hmML}" y="${bmT}" width="${hmW}" height="${bmH}" fill="var(--bg)" stroke="var(--rule)" stroke-width="0.5" />`;

    const bmTicks = niceTicks(pMin, pMax, 4);
    bmTicks.forEach(pv => {
      const y = priceY(pv);
      s += `<line x1="${hmML}" y1="${y}" x2="${hmR}" y2="${y}" stroke="var(--soft)" stroke-width="0.5" />`;
      s += `<text x="${hmML - 6}" y="${y + 3}" font-size="10" fill="var(--muted)" text-anchor="end">${pv.toFixed(pv % 1 === 0 ? 0 : 1)}</text>`;
    });

    s += `<g clip-path="url(#clip-bm)">`;
    // Past years: grey ribbons
    for (const yr of yrList) {
      if (yr === currentYear) continue;
      const weeks = cells.cells.filter(c => c.year === yr).sort((a, b) => a.week - b.week);
      if (weeks.length < 2) continue;
      let d = `M ${weekX(weeks[0].week)} ${priceY(weeks[0].ribbonMax)}`;
      for (let i = 1; i < weeks.length; i++) d += ` L ${weekX(weeks[i].week)} ${priceY(weeks[i].ribbonMax)}`;
      for (let i = weeks.length - 1; i >= 0; i--) d += ` L ${weekX(weeks[i].week)} ${priceY(weeks[i].ribbonMin)}`;
      d += ' Z';
      s += `<path d="${d}" fill="rgba(150,145,140,0.40)" stroke="rgba(130,125,120,0.70)" stroke-width="1" />`;
    }
    // Current year: green ribbon
    const curWeeks = cells.cells.filter(c => c.year === currentYear).sort((a, b) => a.week - b.week);
    if (curWeeks.length >= 2) {
      let d = `M ${weekX(curWeeks[0].week)} ${priceY(curWeeks[0].ribbonMax)}`;
      for (let i = 1; i < curWeeks.length; i++) d += ` L ${weekX(curWeeks[i].week)} ${priceY(curWeeks[i].ribbonMax)}`;
      for (let i = curWeeks.length - 1; i >= 0; i--) d += ` L ${weekX(curWeeks[i].week)} ${priceY(curWeeks[i].ribbonMin)}`;
      d += ' Z';
      s += `<path d="${d}" fill="rgba(57,107,81,0.15)" stroke="var(--green)" stroke-width="2.5" />`;
    }
    s += `</g>`;

    // Right marginal: yearly mini ranges
    s += `<text x="${rmL}" y="${hmMT - 14}" font-size="12" font-weight="600" fill="var(--muted)">Cena (zł) — wg roku</text>`;
    s += `<rect x="${rmL}" y="${hmMT}" width="${rmW}" height="${hmH}" fill="var(--bg)" stroke="var(--rule)" stroke-width="0.5" />`;

    const rmTicks = niceTicks(pMin, pMax, 3);
    rmTicks.forEach(pv => {
      const x = priceX(pv);
      s += `<line x1="${x}" y1="${hmMT}" x2="${x}" y2="${hmB}" stroke="var(--soft)" stroke-width="0.5" />`;
      s += `<text x="${x}" y="${hmB + 16}" font-size="10" fill="var(--muted)" text-anchor="middle">${pv.toFixed(pv % 1 === 0 ? 0 : 1)}</text>`;
    });

    s += `<g clip-path="url(#clip-rm)">`;
    const bandH = Math.min(cellH * 0.5, 16);
    yrList.forEach((yr, yi) => {
      if (yr === currentYear) return;
      const a = yAgg.get(yr)!;
      const ya = yearMidY(yi);
      const x1 = priceX(a.overallMin);
      const x2 = priceX(a.overallMax);
      s += `<rect x="${x1}" y="${ya - bandH/2}" width="${Math.max(2, x2 - x1)}" height="${bandH}" rx="3" fill="rgba(160,155,145,0.22)" stroke="rgba(130,125,120,0.5)" stroke-width="1" />`;
      s += `<text x="${rmL + rmW - 6}" y="${ya + 3}" font-size="10" fill="var(--muted)" text-anchor="end">${a.overallMin.toFixed(1)}–${a.overallMax.toFixed(1)}</text>`;
    });
    const curA = yAgg.get(currentYear);
    if (curA) {
      const ya = yearMidY(yrList.indexOf(currentYear));
      const x1 = priceX(curA.overallMin);
      const x2 = priceX(curA.overallMax);
      s += `<rect x="${x1}" y="${ya - bandH/2}" width="${Math.max(2, x2 - x1)}" height="${bandH}" rx="3" fill="rgba(57,107,81,0.12)" stroke="var(--green)" stroke-width="2" />`;
      s += `<text x="${rmL + rmW - 6}" y="${ya + 3}" font-size="10" fill="var(--green)" font-weight="600" text-anchor="end">${curA.overallMin.toFixed(1)}–${curA.overallMax.toFixed(1)}</text>`;
    }
    s += `</g>`;

    // Legend
    const legY = bmB + 34;
    const legW = 200, legH = 12, legX = hmML;
    s += `<rect x="${legX}" y="${legY}" width="${legW}" height="${legH}" rx="2" fill="url(#hg)" stroke="var(--rule)" />`;
    s += `<text x="${legX}" y="${legY + legH + 15}" font-size="11" fill="var(--muted)">${pMin.toFixed(1)} zł</text>`;
    s += `<text x="${legX + legW}" y="${legY + legH + 15}" font-size="11" fill="var(--muted)" text-anchor="end">${pMax.toFixed(1)} zł</text>`;
    s += `<text x="${legX + legW/2}" y="${legY + legH + 15}" font-size="11" fill="var(--muted)" text-anchor="middle" font-weight="500">Śr. cena</text>`;
    s += `<rect x="${legX + legW + 32}" y="${legY + 2}" width="${legH - 4}" height="${legH - 4}" rx="1" fill="var(--pale)" stroke="var(--rule)" />`;
    s += `<text x="${legX + legW + 32 + legH + 4}" y="${legY + legH - 1}" font-size="11" fill="var(--muted)">Brak danych</text>`;

    return `<svg viewBox="0 0 ${svgW} ${svgH}" preserveAspectRatio="xMidYMid meet">${s}</svg>`;
  });
</script>

<main class="workspace-grid">
  <div class="chart-box">
    <div class="chart-header">
      <div class="chart-title">Mapa Cieplna Sezonowa (Tydzień × Rok)</div>
      <div class="chart-legend">
        <div class="legend-item"><div class="legend-color" style="background-color: rgba(160,155,145,0.35);"></div>Minione lata</div>
        <div class="legend-item"><div class="legend-color" style="background: transparent; border: 2px solid var(--green);"></div>Rok bieżący</div>
      </div>
    </div>
    <div class="heatmap-scroll" bind:this={containerEl}>
      {@html svgMarkup}
    </div>
  </div>
</main>

<style>
  .workspace-grid { display: flex; flex-direction: column; gap: 24px; }
  .chart-box {
    background-color: var(--surface); border: 1px solid var(--rule); padding: 20px;
  }
  .chart-header {
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 16px; flex-wrap: wrap; gap: 12px;
  }
  .chart-title { font-size: 14px; font-weight: 600; color: var(--ink); }
  .chart-legend { display: flex; gap: 16px; font-size: 11px; font-weight: 500; }
  .legend-item { display: flex; align-items: center; gap: 6px; color: var(--muted); }
  .legend-color { width: 12px; height: 12px; border: 1px solid var(--rule); }
  .heatmap-scroll {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    width: 100%;
  }
  .heatmap-scroll :global(svg) {
    width: 100%;
    height: auto;
    min-width: 600px;
  }

  @media (max-width: 768px) {
    .chart-box { padding: 12px; }
    .chart-title { font-size: 13px; }
  }
</style>
