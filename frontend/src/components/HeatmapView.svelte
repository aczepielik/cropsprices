<!--
  HeatmapView.svelte — Seasonal heatmap visualization (Week × Year grid).

  This is the core visualization of the app. It shows:
  - Rows = years (2018-2026)
  - Columns = ISO weeks (1-53)
  - Color intensity = average price across selected marketplaces
  - Green border = current year (2026)

  HOW IT WORKS:
  1. Filter records by selected marketplaces
  2. Group by (year, week) and compute average price
  3. Normalize colors globally (across ALL years) for fair comparison
  4. Render SVG rectangles with computed colors

  SVG RENDERING:
  We use raw SVG instead of a charting library because:
  - The heatmap is a custom layout (not a standard chart type)
  - We need pixel-perfect control over cell positioning
  - The total SVG is small (~50 cells × ~8 years = ~400 rects)
-->

<script lang="ts">
  import type { PriceRecord, HeatmapCell } from '../lib/types';
  import { aggregateByWeekYear, filterByMarkets } from '../lib/filters';
  import { heatColor, getISOWeek, getYear, niceTicks } from '../lib/helpers';

  // Props from parent
  let { records, markets }: {
    records: PriceRecord[];
    markets: Set<string>;
  } = $props();

  // $derived.by() — recomputes when records or markets change
  let cells = $derived.by(() => {
    // Step 1: Filter to selected marketplaces only
    const filtered = filterByMarkets(records, markets);

    // Step 2: Group by (year, week) and aggregate
    const agg = aggregateByWeekYear(filtered);

    // Step 3: Convert Map to array and find global min/max for color normalization
    const result: HeatmapCell[] = [];
    let globalMin = Infinity;
    let globalMax = -Infinity;
    for (const [key, data] of agg) {
      const [yearStr, weekStr] = key.split('-');
      const year = Number(yearStr);
      const week = Number(weekStr);
      result.push({ year, week, ...data });
      globalMin = Math.min(globalMin, data.ribbonMin);
      globalMax = Math.max(globalMax, data.ribbonMax);
    }
    return { cells: result, globalMin, globalMax };
  });

  // Constants for SVG layout
  const CELL_SIZE = 36;  // Width/height of each cell in pixels
  const GAP = 2;         // Space between cells
  const WEEKS = 53;      // Maximum ISO weeks in a year

  // Extract unique years and sort them chronologically
  const years = $derived([...new Set(cells.cells.map(c => c.year))].sort());

  /**
   * Get the fill color for a heatmap cell.
   * Uses the global min/max to normalize across all years.
   */
  function cellColor(c: HeatmapCell): string {
    return heatColor(c.value, cells.globalMin, cells.globalMax);
  }
</script>

<main class="workspace-grid">
  <div class="chart-box">
    <div class="chart-header">
      <div class="chart-title">Mapa Cieplna Sezonowa (Tydzien x Rok)</div>
    </div>
    <div class="heatmap-scroll">
      <!-- SVG dimensions calculated from data: width = weeks × cell size, height = years × cell size -->
      <svg
        width={(WEEKS + 1) * (CELL_SIZE + GAP) + 60}
        height={years.length * (CELL_SIZE + GAP) + 40}
      >
        {#each years as year, yi}
          <!-- Year label on the left -->
          <text
            x={0}
            y={yi * (CELL_SIZE + GAP) + CELL_SIZE / 2 + 4}
            font-size="11"
            fill="var(--muted)"
          >
            {year}
          </text>

          <!-- Render one cell per week -->
          {#each Array(WEEKS) as _, wi}
            <!-- Find the data for this specific year+week combination -->
            {@const c = cells.cells.find(c => c.year === year && c.week === wi + 1)}
            <rect
              x={60 + wi * (CELL_SIZE + GAP)}
              y={yi * (CELL_SIZE + GAP)}
              width={CELL_SIZE}
              height={CELL_SIZE}
              rx={2}
              fill={c ? cellColor(c) : 'var(--pale)'}
              stroke={year === 2026 ? 'var(--green)' : 'none'}
              stroke-width={year === 2026 ? 2 : 0}
            />
          {/each}
        {/each}
      </svg>
    </div>
  </div>
</main>

<style>
  .workspace-grid { display: none; flex-direction: column; gap: 24px; }
  .chart-box {
    background-color: var(--surface); border: 1px solid var(--rule); padding: 20px;
  }
  .chart-header {
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 16px; flex-wrap: wrap; gap: 12px;
  }
  .chart-title { font-size: 14px; font-weight: 600; color: var(--ink); }
  .heatmap-scroll { overflow-x: auto; }
</style>
