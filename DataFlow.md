# Data Flow Design

This document traces the exact data flow from Arrow files to each visualization in mock6.html, answering: what files load, what filters apply, what is pre-calculated vs computed on the client, and what the tradeoffs are.

---

## 1. Raw Schema (from NewArchitecture.md, refined for monthly partitioning)

### Original Design (from NewArchitecture.md)

```
public/data/
├── manifest.json                    # Metadata: available years, products, last update
├── lookups.arrow                    # Shared dictionary tables (products, places, origins)
├── prices_2019.arrow                # ALL products, ALL markets, ALL origins for 2019
├── prices_2020.arrow                # Same structure, 2020
├── ...
└── prices_2025.arrow                # Current year
```

**Problem with year-based partitioning:** Each `prices_YYYY.arrow` contains ALL products for the entire year (~200 KB). This is wasteful because:
- Snapshot only needs 2-3 months of data (not the full year)
- Heatmap only needs aggregated weekly cells (not raw per-market rows)
- Context chart crosses year boundaries (January ±7 weeks needs December of previous year)

**See Section 4 for the refined monthly partitioning strategy.**

### Recommended File Layout (Monthly Partitioning)

```
public/data/
├── manifest.json                              # Metadata
├── lookups.arrow                              # Shared dictionaries (~50 KB)
├── weekly_prices_{YYYY}_{product}.arrow       # Pre-aggregated weekly cells (~1 KB each)
├── prices_{YYYY}_{MM}_{product}.arrow         # Raw monthly data (~2 KB each)
│   ├── prices_2025_01_strawberries.arrow
│   ├── prices_2025_02_strawberries.arrow
│   ├── ...
│   └── prices_2019_12_onions.arrow
```

**Critical detail:** Each `prices_{YYYY}_{MM}_{product}.arrow` contains rows for **one product, one month, all markets and origins**. Product filtering is built into the file structure.

### Arrow Columns per Row

| Column       | Type    | Meaning                                         |
|--------------|---------|--------------------------------------------------|
| `date`       | Date64  | Observation date (YYYY-MM-DD)                   |
| `product_id` | UInt16  | FK → `lookups.products`                          |
| `place_id`   | UInt16  | FK → `lookups.places`                            |
| `origin_id`  | UInt8   | FK → `lookups.origins` (KRAJOWE / IMPORTOWANE)   |
| `price_min`  | Float32 | Minimum wholesale price (zł/kg)                 |
| `price_max`  | Float32 | Maximum wholesale price (zł/kg)                 |

### Lookup Tables (in `lookups.arrow`)

| Table       | Columns                        |
|-------------|--------------------------------|
| `products`  | `product_id`, `name`, `unit`, `category` |
| `places`    | `place_id`, `name`             |
| `origins`   | `origin_id`, `name`            |

---

## 2. Filter Chain (from mock6.html)

The sidebar defines a strict filter cascade. Each filter narrows the working dataset:

```
Category (Kategoria)     → UI filter: determines which products appear in Product dropdown
                               Does NOT filter Arrow data directly.
                               "Owoce" shows fruit products, "Warzywa" shows vegetable products.

Origin (Pochodzenie)     → UI filter: declutters Product dropdown by origin.
                               "Krajowe" shows domestic products, "Importowane" shows imported.
                               Each combination is a distinct product_id (e.g., "Truskawki krajowe"
                               ≠ "Truskawki importowane"). No Arrow filtering needed.

Product (Produkt)        → File-level filter: determines which monthly files to load.
                               With monthly partitioning, product is built into the file name.
                               No client-side filtering needed.

Markets (Rynki Hurtowe)  → Arrow filter: WHERE place_id IN [selected market IDs]
                               Reduces dataset from ~40-60 rows/month to ~16-24 rows/month
                               (4 markets × ~4 weeks × 2 origins ≈ 32 rows).

Date (Punkt Odniesienia) → Arrow filter: WHERE date = selected_date
                               Snapshot only. Reduces to ~(4 markets × 1 origin) = 4 rows.
```

**Effective row counts (1 product, 4 markets, 1 month):**

| Filter Stage              | Approximate Rows |
|---------------------------|------------------|
| Raw monthly file          | ~40-60           |
| After market filter       | ~16-24           |
| After date filter (snap)  | ~4-8             |

**For full-year context (1 product, 4 markets, 12 months):**
~192-288 rows across 12 monthly files

---

## 3. View-by-View Data Flow

### 3.1 Snapshot View (Widok Aktualny)

**Data needed:** 2-3 months around selected date (current + previous years for context chart).

**File loading sequence (with monthly partitioning):**
```
1. manifest.json                              → 1 KB    (know which months/products exist)
2. lookups.arrow                              → 50 KB   (decode product_id, place_id to names)
3. prices_{YYYY}_{MM}_{product}.arrow         → ~2 KB each
   For Jan 15, 2025, ±7 weeks, 3-year context:
   - prices_2025_01_strawberries.arrow        (current month)
   - prices_2025_02_strawberries.arrow        (next month for +7 weeks)
   - prices_2024_12_strawberries.arrow        (prev year Dec for -7 weeks)
   - prices_2024_01_strawberries.arrow        (year-1 same month)
   - prices_2023_12_strawberries.arrow        (year-2 Dec)
   - prices_2023_01_strawberries.arrow        (year-2 same month)
   TOTAL: ~12 KB raw + 51 KB lookup = ~63 KB
```

**Filter + compute pipeline:**
```
Monthly files for selected product
  → Filter: place_id IN selectedMarkets
  → Split into:
      ├── [KPIs] Filter: date = selectedDate
      │     → Aggregate across markets: MIN(price_min), MAX(price_max)
      │     → Compute spread: MAX - MIN
      │     → If prevDate exists: compute WoW Δ for floor and ceiling
      │
      ├── [Context Chart] For each date in [selectedDate - N weeks .. selectedDate + N weeks]:
      │     → Filter: date = eachDate
      │     → Aggregate: MIN(price_min) per date, MAX(price_max) per date
      │     → Repeat for year-1 and year-2 (offset by -52 and -104 weeks)
      │     → ⚠ REQUIRES: monthly files from previous years (lazy-loaded)
      │
      └── [Market Table] Filter: date = selectedDate
            → Keep per-place rows (no aggregation)
            → Compute: spread per market, deviation from national min
```

**Key insight for Context Chart — year boundary crossing:**
The context chart shows ±N weeks around the selected date across 3 years. The window can cross year boundaries:
- If selectedDate = Jan 15, 2025, window ±7 weeks → needs Dec 2024 + Jan–Feb 2025
- If selectedDate = Jan 15, 2025, window ±3 weeks → needs late Dec 2024 + Jan 2025
- If selectedDate = Jun 15, 2025, window ±7 weeks → needs May–Jul 2025 + same months in 2024, 2023

**The context chart always needs at least one month from the previous year when the date is near year boundaries.** Monthly partitioning handles this naturally — just load the specific months needed across year boundaries.

**Revised Snapshot file loading (monthly partitioning):**
```
Initial load (snapshot view):
  manifest.json + lookups.arrow + ~6-8 monthly files = ~63 KB

When switching to heatmap (lazy):
  + 7 weekly pre-agg files = +7 KB
  Total for full session: ~70 KB

Advantage: loads only the months needed, not entire years
```

### 3.2 Heatmap View (Mapa Cieplna)

**Data needed:** ALL available years for the selected product. The heatmap is a Week × Year grid — it must show every year side by side.

**File loading sequence (with pre-aggregated weekly files):**
```
1. manifest.json                              → 1 KB     (know available years)
2. lookups.arrow                              → 50 KB    (decode IDs)
3. weekly_prices_{YYYY}_{product}.arrow       → ~1 KB each
   For strawberries, 7 years:
   - weekly_prices_2019_strawberries.arrow
   - weekly_prices_2020_strawberries.arrow
   - ...
   - weekly_prices_2025_strawberries.arrow
   TOTAL: ~7 KB pre-agg + 51 KB lookup = ~58 KB
```

**Why pre-aggregated weekly files?** The heatmap only needs 5 values per week×year cell: cellVal, ribbonMin, ribbonMax, ribbonAvg. Pre-computing these in the ETL reduces the heatmap payload from ~168 KB (84 monthly raw files) to ~7 KB (7 weekly files).

**Filter + compute pipeline:**
```
weekly_prices_{YYYY}_{product}.arrow (for each year)
  → Already filtered by product (built into file name)
  → Client applies market filter if needed (pre-agg includes all markets)
  → Compute global normalization:
      → globalCellMin = MIN(all cellVal)
      → globalCellMax = MAX(all cellVal)
      → globalPriceMin = MIN(all ribbonMin)
      → globalPriceMax = MAX(all ribbonMax)
  → Render:
      ├── Heat cells: cellVal → color scale
      ├── Bottom marginal: ribbonMin/Max → area paths over weeks
      └── Right marginal: year-level overallMin/Max → horizontal bands
```

**Row count for heatmap (1 product, 4 markets, 7 years):**
```
With pre-aggregated weekly files:
  Per year: 53 weeks × 5 columns (week, cellVal, ribbonMin, ribbonMax, ribbonAvg) = 53 rows
  7 years: 371 rows total
  At 20 bytes/row ≈ ~7 KB (matches file size estimate)

With raw monthly files (fallback):
  Per year: ~480-720 rows (12 months × 40-60 rows/month)
  7 years: ~3,360-5,040 rows
  Client must GroupBy(week) to aggregate
```

---

## 4. Strategy Analysis

### 4.1 Constraints Recap

| Constraint | Implication |
|---|---|
| **Snapshot needs ±N weeks across year boundaries** | January date with ±7 weeks requires Dec (prev year) + Jan–Feb (current year). Cannot partition purely by year. |
| **Heatmap needs ALL years** | Week × Year grid requires every year's data side by side. |
| **Data is low-volume** | ~50K rows/year, ~350K rows total for 7 years. ~200 KB raw per year. |
| **Data is weekly updated** | ETL runs weekly. Pre-computation cost is negligible. |
| **ETL is cheap** | Python + PyArrow on GitHub Actions. Can generate many file types without concern. |
| **6 products, ~15 markets** | Product filtering reduces data ~6×. Market filtering reduces ~4× further. |

### 4.2 The Year-Partitioning Problem

The original `NewArchitecture.md` design partitions by year: `prices_YYYY.arrow`. This creates two issues:

1. **Snapshot waste:** Loading `prices_2024.arrow` (200 KB) when only Dec 2024 is needed (~17 KB). The context chart for a January date only needs 1-2 months from the previous year, but loads the entire year.

2. **Heatmap is all-or-nothing:** Must load all 7 year files (1.4 MB) even though the heatmap only needs aggregated weekly cells.

**Key insight: Year partitioning is the wrong granularity for this data.**

### 4.3 Monthly Partitioning

Instead of splitting by year, split by **product × month**. Each file contains all markets and origins for one product in one month.

**File naming:** `prices_{YYYY}_{MM}_{product_key}.arrow`

**Row count per file:**
```
Per month, 1 product, 4 markets, 2 origins:
  ~4 weeks × 4 markets × 2 origins = ~32 rows
  × some weeks may have 2 observations ≈ ~40-60 rows
  At 24 bytes/row (Date64 + 3×UInt16 + 2×Float32) ≈ ~1.2 KB raw
  With Arrow IPC overhead ≈ ~1.5-2 KB per file
```

**Full inventory:**
```
7 years × 12 months × 6 products = 504 files
Each ~2 KB → total ~1 MB (same as 5 year-files, but with surgical access)
```

**What each view loads:**

**Snapshot (date = Jan 15, 2025, window ±7 weeks):**
```
Current year:  prices_2025_01_strawberries.arrow  (~2 KB)
               prices_2025_02_strawberries.arrow  (~2 KB)
Previous year: prices_2024_12_strawberries.arrow  (~2 KB)
               prices_2024_11_strawberries.arrow  (~2 KB)  ← for year-1 context
               prices_2023_12_strawberries.arrow  (~2 KB)  ← for year-2 context
               prices_2023_11_strawberries.arrow  (~2 KB)  ← for year-2 context
               prices_2024_01_strawberries.arrow  (~2 KB)  ← for year-1 same-month context
               prices_2023_01_strawberries.arrow  (~2 KB)  ← for year-2 same-month context
Total: ~16 KB + lookups (50 KB) + manifest (1 KB) = ~67 KB
```

**Heatmap (strawberries, all years):**
```
12 months × 7 years = 84 files × ~2 KB = ~168 KB
+ lookups (50 KB) + manifest (1 KB) = ~219 KB
```

**Heatmap with pre-aggregated weekly cells:**
```
7 years × 53 weekly rows × 20 bytes ≈ ~1 KB per year
Total: 7 × 1 KB = ~7 KB
+ lookups (50 KB) + manifest (1 KB) = ~58 KB
```

### 4.4 Strategy Options

#### Option 1: Monthly Partitioning Only (No Pre-aggregation)

**ETL produces:** `prices_{YYYY}_{MM}_{product}.arrow` (504 files)

| View | Files loaded | Total size |
|---|---|---|
| Snapshot (±7 weeks, 3 years) | ~8 monthly files | ~16 KB |
| Heatmap (all years) | 84 monthly files | ~168 KB |
| Product switch | re-filter in-memory | 0 KB |

**Pros:**
- Single file type, simple ETL
- Snapshot is extremely small (~16 KB)
- Handles year boundaries naturally
- Full raw data available for any drill-down

**Cons:**
- Heatmap loads 84 small files (many HTTP requests, even with HTTP/2)
- Client must compute weekly aggregates for heatmap (cheap but non-trivial)
- 504 files to manage on CDN

#### Option 2: Monthly Partitioning + Pre-aggregated Weekly (Recommended)

**ETL produces:**
```
prices_{YYYY}_{MM}_{product}.arrow          # Raw monthly (for snapshots)
weekly_prices_{YYYY}_{product}.arrow        # Pre-aggregated weekly (for heatmaps)
```
prices_{YYYY}_{MM}_{product}.arrow          # Raw monthly (all origins, for snapshots)
weekly_prices_{YYYY}_{product}_{origin}.arrow # Pre-aggregated weekly per origin (for heatmaps)
```

**weekly_prices schema:**
| Column       | Type    | Meaning                                |
|--------------|---------|----------------------------------------|
| `week`       | UInt8   | ISO week number (1-53)                 |
| `cellVal`    | Float32 | Average midprice across markets        |
| `ribbonMin`  | Float32 | Min price_min across markets           |
| `ribbonMax`  | Float32 | Max price_max across markets           |
| `ribbonAvg`  | Float32 | Average of min/max across markets      |

**File count:**
```
Monthly raw:    7 years × 12 months × 6 products = 504 files × ~2 KB = ~1 MB
Weekly pre-agg: 7 years × 6 products = 42 files × ~1 KB = ~42 KB
Total: ~1.04 MB across 546 files
```

**What each view loads:**

| View | Files loaded | Total size | Client computation |
|---|---|---|---|
| Snapshot (±7 weeks, 3 years) | ~8 monthly files | ~16 KB | KPIs, context chart, market table |
| Heatmap (all years) | 7 weekly files | ~7 KB | Color normalization only |
| Product switch (heatmap) | 0 (already loaded) | 0 KB | Re-normalize |
| Product switch (snapshot) | ~8 monthly files | ~16 KB | Full recompute |

**Pros:**
- Heatmap is ~7 KB (vs 168 KB without pre-agg) — near-instant
- Snapshot is ~16 KB — near-instant
- Both views use dedicated file types optimized for their access pattern
- ETL is cheap: weekly_prices is a simple GroupBy on the monthly data
- Graceful degradation: if weekly_prices missing, compute from monthly files

**Cons:**
- Two file types to maintain
- 546 files total (but ETL generates them automatically)
- Adding a new product requires generating 12 monthly + 1 weekly file per year

#### Option 3: Monthly Partitioning + Pre-aggregated Snapshot KPIs

**ETL produces:**
```
prices_{YYYY}_{MM}_{product}.arrow          # Raw monthly
weekly_prices_{YYYY}_{product}.arrow        # Pre-aggregated weekly (for heatmaps)
snapshot_kpi_{YYYY}_{MM}_{product}.arrow    # Pre-computed daily national aggregates
```

**snapshot_kpi schema:**
| Column        | Type    | Meaning                                |
|---------------|---------|----------------------------------------|
| `date`        | Date64  | Observation date                       |
| `natMin`      | Float32 | MIN(price_min) across all markets      |
| `natMax`      | Float32 | MAX(price_max) across all markets      |
| `natSpread`   | Float32 | natMax - natMin                        |
| `marketCount` | UInt8   | Number of markets reporting            |

**What each view loads:**

| View | Files loaded | Total size |
|---|---|---|
| Snapshot KPIs | ~8 snapshot_kpi files | ~8 KB |
| Snapshot market table | ~8 monthly raw files | ~16 KB |
| Snapshot context chart | ~8 snapshot_kpi files (from prev years) | ~8 KB |
| Heatmap | 7 weekly files | ~7 KB |

**Full snapshot (KPIs + context + market table):** ~32 KB
**Heatmap:** ~7 KB

**Pros:**
- Fastest possible snapshot (KPIs pre-computed, no client aggregation)
- Market table still uses raw data (needed for per-market breakdown)
- Clean separation: pre-agg for aggregates, raw for drill-down

**Cons:**
- Three file types to maintain
- snapshot_kpi must be regenerated if raw data changes
- Most complex ETL of all options

### 4.5 Comparison Matrix

| Criterion | 1: Monthly Only | 2: Monthly + Weekly | 3: Monthly + Weekly + KPI |
|---|---|---|---|
| **Snapshot load** | ~16 KB | ~16 KB | ~8 KB (KPIs) + ~16 KB (table) |
| **Heatmap load** | ~168 KB | ~7 KB | ~7 KB |
| **Total files** | 504 | 546 | 588 |
| **Total size** | ~1 MB | ~1.04 MB | ~1.08 MB |
| **ETL complexity** | ★☆☆ simple | ★★☆ moderate | ★★★ complex |
| **Client computation** | moderate | minimal | minimal |
| **Flexibility** | ★★★ max | ★★☆ good | ★★☆ good |
| **Graceful degradation** | N/A | monthly fallback | monthly fallback |

### 4.6 Recommendation: Option 2 (Monthly + Weekly Pre-agg)

**Why Option 2 over Option 1:**
The heatmap needs all years. With monthly files, that's 84 HTTP requests for ~168 KB. With pre-aggregated weekly files, it's 7 requests for ~7 KB. The ETL cost is negligible (GroupBy on data that already exists). The client benefit is massive (near-instant heatmap render).

**Why Option 2 over Option 3:**
The snapshot KPIs are cheap to compute client-side from 8 monthly files (~16 rows after filtering). Pre-computing them saves ~5 KB of transfer but adds a third file type and ETL complexity. Not worth it for this data volume.

**Why monthly partitioning over yearly:**
- Snapshot context chart needs months across year boundaries (Jan ±7 weeks → Dec prev year)
- Yearly files load 200 KB when only ~17 KB is needed
- Monthly files give surgical access to exactly the date range needed
- 504 files sounds like many, but ETL generates them all automatically
- Origin is part of product identity — "Truskawki krajowe" and "Truskawki importowane" are separate products with different product_ids

**Implementation plan:**
1. **ETL (Phase 2):** Generate monthly raw files + weekly pre-aggregated files
2. **Frontend loading layer (Phase 3):**
   - `loadSnapshotView(product, date, windowWeeks)` → compute required months, fetch in parallel
   - `loadHeatmapView(product)` → fetch 7 weekly pre-agg files in parallel
   - Cache all loaded buffers in React state
3. **Manifest structure:**
```json
{
  "years": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
  "products": ["strawberries_krajowe", "strawberries_importowane", "apples_krajowe", ...],
  "months": {"2019": [1,2,3,...,12], "2020": [1,2,3,...,12], ...},
  "lastUpdate": "2025-06-15"
}
```

**Loading waterfall (Option 2):**
```
Snapshot (first load):
  T+0ms     manifest.json (1 KB)
  T+10ms    lookups.arrow (50 KB)
  T+30ms    [parallel] 8 monthly files (16 KB)
  T+50ms    ✅ Snapshot renders (67 KB total)

Heatmap (first load):
  T+0ms     manifest.json (1 KB)           ← already cached
  T+0ms     lookups.arrow (50 KB)          ← already cached
  T+20ms    [parallel] 7 weekly files (7 KB)
  T+40ms    ✅ Heatmap renders (58 KB total)
```

---

## 5. IndexedDB Caching Strategy

### 5.1 Immutability Insight

Past data is immutable. Once a year closes (Jan 1 next year), all 12 monthly files and the weekly pre-agg file for that year will never change again. The only files that change are:

| File type | Mutability | Change frequency |
|---|---|---|
| `manifest.json` | Mutable | Weekly (new data added) |
| `lookups.arrow` | Mutable | Rarely (new products/markets added) |
| `prices_{YYYY}_{MM}_{product}.arrow` for current month | Mutable | Weekly (new observations appended) |
| `prices_{YYYY}_{MM}_{product}.arrow` for past months | **Immutable** | Never |
| `weekly_prices_{YYYY}_{product}.arrow` for past years | **Immutable** | Never |
| `weekly_prices_{currentYear}_{product}.arrow` | Mutable | Weekly (new weeks added) |

**Key: ~95% of files are immutable after their year closes.**

### 5.2 Cache Layers

```
┌─────────────────────────────────────────────────┐
│  Layer 1: In-memory (React state)               │
│  - Currently viewed data                        │
│  - Fastest access (0ms)                         │
│  - Lost on page refresh                         │
├─────────────────────────────────────────────────┤
│  Layer 2: IndexedDB                              │
│  - All loaded Arrow buffers                     │
│  - Persists across page refreshes               │
│  - Fast access (~1-5ms)                         │
│  - ~1 MB total for full dataset                 │
├─────────────────────────────────────────────────┤
│  Layer 3: HTTP cache (CDN/browser)              │
│  - All files served with appropriate headers    │
│  - Immutable files: Cache-Control: max-age=31536000, immutable
│  - Mutable files: Cache-Control: no-cache       │
└─────────────────────────────────────────────────┘
```

### 5.3 IndexedDB Schema

```typescript
interface CachedArrow {
  key: string;           // e.g., "prices_2024_01_strawberries"
  data: ArrayBuffer;     // Raw Arrow IPC bytes
  etag: string;          // From HTTP response (for cache validation)
  cachedAt: number;      // Timestamp of cache write
  immutable: boolean;    // True if year < currentYear
}

// Store names:
// "arrows"       — monthly raw files + weekly pre-agg files
// "manifest"     — latest manifest.json
// "lookups"      — lookups.arrow
```

### 5.4 Cache-Control Headers (CDN)

```yaml
# Immutable past data (forever cache)
prices_2019_*.arrow:   Cache-Control: public, max-age=31536000, immutable
prices_2020_*.arrow:   Cache-Control: public, max-age=31536000, immutable
...
prices_2024_*.arrow:   Cache-Control: public, max-age=31536000, immutable
weekly_prices_2019_*.arrow: Cache-Control: public, max-age=31536000, immutable
...
weekly_prices_2024_*.arrow: Cache-Control: public, max-age=31536000, immutable

# Current year — mutable (weekly updates)
prices_2025_*.arrow:   Cache-Control: public, max-age=604800  # 1 week
weekly_prices_2025_*.arrow: Cache-Control: public, max-age=604800

# Manifest & lookups — mutable
manifest.json:         Cache-Control: no-cache
lookups.arrow:         Cache-Control: public, max-age=86400  # 1 day
```

### 5.5 Fetch Strategy

```typescript
async function fetchArrow(key: string, immutable: boolean): Promise<ArrayBuffer> {
  // 1. Check in-memory cache
  if (memoryCache.has(key)) return memoryCache.get(key);

  // 2. Check IndexedDB
  const cached = await idb.get(key);
  if (cached) {
    if (immutable) {
      // Immutable file never changes — use cached version
      memoryCache.set(key, cached.data);
      return cached.data;
    }
    // Mutable file — validate with ETag
    const response = await fetch(`/data/${key}.arrow`, {
      headers: { 'If-None-Match': cached.etag }
    });
    if (response.status === 304) {
      // Not modified — cached version is current
      memoryCache.set(key, cached.data);
      return cached.data;
    }
    // Modified — update cache
    const newData = await response.arrayBuffer();
    await idb.put({ key, data: newData, etag: response.headers.get('etag'), immutable: false });
    memoryCache.set(key, newData);
    return newData;
  }

  // 3. Cache miss — fetch from network
  const response = await fetch(`/data/${key}.arrow`);
  const data = await response.arrayBuffer();
  await idb.put({ key, data, etag: response.headers.get('etag'), immutable });
  memoryCache.set(key, data);
  return data;
}
```

### 5.6 Loading Waterfall with IndexedDB

```
First visit (cold cache):
  T+0ms     manifest.json (1 KB)              ← network
  T+10ms    lookups.arrow (50 KB)              ← network
  T+30ms    [parallel] 8 monthly files (16 KB) ← network
  T+50ms    ✅ Snapshot renders (67 KB total)
  T+50ms    Write all to IndexedDB

Subsequent visit (warm cache):
  T+0ms     manifest.json (1 KB)              ← network (no-cache)
  T+5ms     lookups.arrow (50 KB)             ← IndexedDB
  T+5ms     [parallel] 8 monthly files (16 KB)← IndexedDB
  T+10ms    ✅ Snapshot renders (67 KB total)

Heatmap (warm cache):
  T+0ms     [parallel] 7 weekly files (7 KB)  ← IndexedDB
  T+5ms     ✅ Heatmap renders (58 KB total)

Current month update scenario:
  T+0ms     manifest.json                     ← network (checks for new data)
  T+10ms    prices_2025_06_strawberries.arrow ← network (ETag check, gets fresh data)
  T+10ms    [parallel] 7 past monthly files   ← IndexedDB (immutable, instant)
  T+15ms    ✅ Snapshot renders
```

### 5.7 Cache Size Budget

```
Full dataset (7 years × 6 products):
  Monthly raw:    504 files × ~2 KB = ~1 MB
  Weekly pre-agg: 42 files × ~1 KB  = ~42 KB
  Lookups:        1 file × ~50 KB   = ~50 KB
  Manifest:       1 file × ~1 KB    = ~1 KB
  ─────────────────────────────────────────
  Total IndexedDB: ~1.1 MB

This is tiny for IndexedDB (typical limit is 50% of disk space).
```
