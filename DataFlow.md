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
├── 2018/
│   ├── 07/
│   │   ├── 2018-07-03-Banany-kg-KRAJOWE.arrow
│   │   ├── 2018-07-03-Banany-kg-IMPORTOWANE.arrow
│   │   ├── 2018-07-10-Banany-kg-KRAJOWE.arrow
│   │   └── ...
│   └── 08/
│       └── ...
├── 2019/
│   ├── 01/
│   └── ...
└── 2026/
    └── 05/
        └── ...
```

**Critical detail:** Each file contains data for **one date, one product, one unit, one origin, all markets**. The product identity is the compound key `(Product, Unit, Origin)` — e.g., "Rzodkiewka, kg, KRAJOWE" and "Rzodkiewka, pęczek, KRAJOWE" are separate products in separate files.

**No `lookups.arrow`** — columns use Arrow dictionary encoding (inline dictionaries for product, place, origin).
**No weekly pre-agg files** — heatmap aggregates from monthly files client-side (enables market toggling).

### Arrow Columns per Row

| Column      | Type              | Meaning                                         |
|-------------|-------------------|--------------------------------------------------|
| `date`      | Date64            | Observation date (YYYY-MM-DD)                   |
| `product`   | Utf8 (dictionary) | Product name (e.g., "Truskawki krajowe")        |
| `place`     | Utf8 (dictionary) | Market name (e.g., "Bronisze")                  |
| `origin`    | Utf8 (dictionary) | KRAJOWE / IMPORTOWANE                           |
| `price_min` | Float32           | Minimum wholesale price (zł/kg)                 |
| `price_max` | Float32           | Maximum wholesale price (zł/kg)                 |

All string columns use Arrow dictionary encoding. Frontend extracts unique values directly from loaded data for filter dropdowns.

---

## 2. Filter Chain (from mock6.html)

The sidebar defines a strict filter cascade. Each filter narrows the working dataset:

```
Category (Kategoria)     → UI filter: determines which products appear in Product dropdown
                               Does NOT filter Arrow data directly.
                               "Owoce" shows fruit products, "Warzywa" shows vegetable products.

Origin (Pochodzenie)     → UI filter: declutters Product dropdown by origin.
                               "Krajowe" shows domestic products, "Importowane" shows imported.
                               Each combination is a distinct product (e.g., "Truskawki krajowe"
                               ≠ "Truskawki importowane"). No Arrow filtering needed.

Product (Produkt)        → File-level filter: determines which monthly files to load.
                               With monthly partitioning, product is built into the file name.
                               No client-side filtering needed.

Markets (Rynki Hurtowe)  → Arrow filter: WHERE place IN selectedMarkets
                               Reduces dataset from ~40-60 rows/month to ~16-24 rows/month
                               (4 markets × ~4 weeks × 2 origins ≈ 32 rows).
                               Heatmap re-aggregates on market toggle (client-side).

Date (Punkt Odniesienia) → Arrow filter: WHERE date = selected_date
                               Snapshot only. Reduces to ~(4 markets × 1 origin) = 4 rows.
```

**Effective row counts (1 product, 4 selected markets, 1 month):**

| Filter Stage              | Approximate Rows |
|---------------------------|------------------|
| Raw monthly file          | ~80-120          |
| After market filter       | ~30-45           |
| After date filter (snap)  | ~4-8             |

**For full-year context (1 product, 4 markets, 12 months):**
~360-540 rows across 12 monthly files

---

## 3. View-by-View Data Flow

### 3.1 Snapshot View (Widok Aktualny)

**Data needed:** 2-3 months around selected date (current + previous years for context chart).

**File loading sequence (with monthly partitioning):**
```
1. manifest.json                              → 1 KB    (know which months/products exist)
2. prices_{YYYY}_{MM}_{product}.arrow         → ~2 KB each
   For Jan 15, 2025, ±7 weeks, 3-year context:
   - prices_2025_01_strawberries.arrow        (current month)
   - prices_2025_02_strawberries.arrow        (next month for +7 weeks)
   - prices_2024_12_strawberries.arrow        (prev year Dec for -7 weeks)
   - prices_2024_01_strawberries.arrow        (year-1 same month)
   - prices_2023_12_strawberries.arrow        (year-2 Dec)
   - prices_2023_01_strawberries.arrow        (year-2 same month)
   TOTAL: ~12 KB
```

**Filter + compute pipeline:**
```
Monthly files for selected product
  → Filter: place IN selectedMarkets
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
  manifest.json + ~6-8 monthly files = ~13 KB

When switching to heatmap (lazy):
  + all monthly files for product = +~168 KB
  Total for full session: ~181 KB

Heatmap supports market toggling (client re-aggregates from raw data)
```

### 3.2 Heatmap View (Mapa Cieplna)

**Data needed:** ALL available years for the selected product. The heatmap is a Week × Year grid — it must show every year side by side.

**File loading sequence (monthly files, client-side aggregation):**
```
1. manifest.json                              → 1 KB     (know available years)
2. prices_{YYYY}_{MM}_{product}.arrow         → ~2 KB each
   For strawberries, 7 years × 12 months:
   - prices_2019_01_strawberries.arrow through prices_2019_12_strawberries.arrow
   - ...
   - prices_2025_01_strawberries.arrow through prices_2025_06_strawberries.arrow
   TOTAL: ~84 files × ~2 KB = ~168 KB
```

**Why client-side aggregation?** Market toggling requires re-computing heatmap cells from the selected subset of markets. Pre-aggregated weekly files bake in all markets and can't be filtered. Loading monthly files (~168 KB total) is fast enough, and the client aggregation is trivial (group by ISO week, compute mean/min/max).

**Filter + compute pipeline:**
```
All monthly files for selected product
  → Filter: place IN selectedMarkets (client-side)
  → Group by (year, ISO_week):
      → cellVal = mean of (price_min + price_max) / 2 across filtered rows
      → ribbonMin = min(price_min) across filtered rows
      → ribbonMax = max(price_max) across filtered rows
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

**Row count for heatmap (1 product, 7 years):**
```
Monthly files: 7 years × ~480 rows/year = ~3,360 rows total
After market filter (4 markets): ~1,344 rows
Client groups by week: 7 years × 53 weeks = 371 cells
Cost: trivial (<1ms on modern hardware)
```

---

## 4. Strategy Analysis

### 4.1 Constraints Recap

| Constraint | Implication |
|---|---|
| **Snapshot needs ±N weeks across year boundaries** | January date with ±7 weeks requires Dec (prev year) + Jan–Feb (current year). Cannot partition purely by year. |
| **Heatmap needs ALL years** | Week × Year grid requires every year's data side by side. |
| **Data is low-volume** | ~50K rows/year, ~350K rows total for 7 years. ~2 KB per monthly file. |
| **Data is weekly updated** | ETL runs weekly. Pre-computation cost is negligible. |
| **ETL is cheap** | Python + PyArrow on GitHub Actions. Can generate many file types without concern. |
| **60 products, ~11 markets** | Product filtering via file names. Market filtering reduces rows ~4×. |

### 4.2 The Year-Partitioning Problem

The original `NewArchitecture.md` design partitions by year: `prices_YYYY.arrow`. This creates two issues:

1. **Snapshot waste:** Loading `prices_2024.arrow` (200 KB) when only Dec 2024 is needed (~17 KB). The context chart for a January date only needs 1-2 months from the previous year, but loads the entire year.

2. **Heatmap is all-or-nothing:** Must load all 7 year files (1.4 MB) even though the heatmap only needs aggregated weekly cells.

**Key insight: Year partitioning is the wrong granularity for this data.**

### 4.3 Monthly Partitioning

Instead of splitting by year, split by **product × month**, with files further distinguished by date and compound product identity (Product, Unit, Origin). Each file contains all markets for one date, one product, one unit, one origin.

**Directory layout:** `{YYYY}/{MM}/{date}-{product}-{unit}-{origin}.arrow`

**Row count per file:**
```
Per file, 1 date, 1 product, 1 unit, 1 origin, all markets:
  ~11 markets = ~11 rows
  At ~16 bytes/row (Date64 + 3×dict_indices + 2×Float32) ≈ ~0.2 KB raw
  With Arrow IPC overhead ≈ ~0.3 KB per file
```

**Full inventory:**
```
~8 years × 12 months × ~60 products = ~5,760 files
Each ~2 KB → total ~11 MB (surgical access to any month/product)
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
Total: ~16 KB + manifest (1 KB) = ~17 KB
```

**Heatmap (strawberries, all years):**
```
12 months × 7 years = 84 files × ~2 KB = ~168 KB
+ manifest (1 KB) = ~169 KB
```

**Heatmap with pre-aggregated weekly cells (NOT recommended — breaks market toggling):**
```
7 years × 53 weekly rows × 20 bytes ≈ ~1 KB per year
Total: 7 × 1 KB = ~7 KB
+ manifest (1 KB) = ~8 KB
```

### 4.4 Strategy Options

#### Option 1: Monthly Partitioning Only (Recommended)

**ETL produces:** `{YYYY}/{MM}/{date}-{product}-{unit}-{origin}.arrow` (~500+ files)

| View | Files loaded | Total size | Client computation |
|---|---|---|---|
| Snapshot (±7 weeks, 3 years) | ~8 monthly dirs (all dates × product × unit × origin) | ~16 KB | KPIs, context chart, market table |
| Heatmap (all years) | 84 monthly dirs | ~168 KB | GroupBy week, color normalization |
| Market toggle (heatmap) | 0 (already loaded) | 0 KB | Re-filter + re-aggregate |
| Product switch | re-fetch monthly files | ~16-168 KB | Full recompute |

**Pros:**
- Single file type, simple ETL
- Snapshot is extremely small (~16 KB)
- Handles year boundaries naturally
- Full raw data available for any drill-down
- Market toggling works (client re-aggregates from raw)
- ~168 KB for heatmap is fast on modern hardware

**Cons:**
- Heatmap loads 84 small files (many HTTP requests, even with HTTP/2)
- Client must compute weekly aggregates for heatmap (trivial, <1ms)
- 504 files to manage on CDN

#### Option 2: Monthly Partitioning + Pre-aggregated Weekly

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
- **Market toggling broken** — pre-agg bakes in all markets, can't re-filter
- Two file types to maintain
- 546 files total (but ETL generates them automatically)
- Adding a new product requires generating 12 monthly files per year

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
| **Market toggling** | ✅ works | ❌ broken | ❌ broken |
| **Total files** | 504 | 546 | 588 |
| **Total size** | ~1 MB | ~1.04 MB | ~1.08 MB |
| **ETL complexity** | ★☆☆ simple | ★★☆ moderate | ★★★ complex |
| **Client computation** | moderate (trivial) | minimal | minimal |
| **Flexibility** | ★★★ max | ★★☆ good | ★★☆ good |

### 4.6 Recommendation: Option 1 (Monthly Only, Client-side Aggregation)

**Why Option 1 over Option 2:**
Market toggling is a core feature of the heatmap (mock6.html implements it). Pre-aggregated weekly files bake in all markets and can't be re-filtered. Loading all monthly files (~168 KB) is fast, and the client aggregation is trivial (<1ms). Option 1 preserves full interactivity.

**Why monthly partitioning over yearly:**
- Snapshot context chart needs months across year boundaries (Jan ±7 weeks → Dec prev year)
- Yearly files load 200 KB when only ~17 KB is needed
- Monthly files give surgical access to exactly the date range needed
- 504 files sounds like many, but ETL generates them all automatically
- Origin is part of product identity — "Truskawki krajowe" and "Truskawki importowane" are separate products with different product names

**Why dictionary-encoded strings over FK + lookups.arrow:**
- Only 68 products, 11 places, 2 origins — small enough for inline dictionaries
- Eliminates a separate file and ID-mapping complexity
- Frontend reads strings directly from Arrow, no join needed

**Implementation plan:**
1. **ETL (Phase 2):** Generate monthly files with dictionary-encoded columns
2. **Frontend loading layer (Phase 3):**
   - `loadSnapshotView(product, date, windowWeeks)` → compute required months, fetch in parallel
   - `loadHeatmapView(product)` → fetch all monthly files for product, aggregate client-side
   - Cache all loaded buffers in Svelte stores + IndexedDB
3. **Manifest structure:**
```json
{
  "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
  "products": [
    {"name": "Rzodkiewka", "unit": "kg", "origin": "KRAJOWE", "category": "warzywa"},
    {"name": "Rzodkiewka", "unit": "pęczek", "origin": "KRAJOWE", "category": "warzywa"},
    {"name": "Truskawki", "unit": "kg", "origin": "KRAJOWE", "category": "owoce"}
  ],
  "places": ["Białystok", "Bronisze", "Łódź", "Poznań", "Warszawa", "Wrocław"],
  "lastUpdate": "2026-06-18"
}
```
**Product identity:** The compound key `(name, unit, origin)` uniquely identifies a product.

**Loading waterfall:**
```
Snapshot (first load):
  T+0ms     manifest.json (1 KB)
  T+10ms    [parallel] 8 monthly files (16 KB)
  T+30ms    ✅ Snapshot renders (17 KB total)

Heatmap (first load):
  T+0ms     manifest.json (1 KB)           ← already cached
  T+10ms    [parallel] 84 monthly files (168 KB)
  T+50ms    Client groups by week, normalizes
  T+60ms    ✅ Heatmap renders

Market toggle (warm):
  T+0ms     Re-filter loaded data (0 KB)
  T+1ms     Re-aggregate by week
  T+2ms     ✅ Heatmap re-renders
```

---

## 5. IndexedDB Caching Strategy

### 5.1 Immutability Insight

Past data is immutable. Once a year closes (Jan 1 next year), all 12 monthly files for that year will never change again. The only files that change are:

| File type | Mutability | Change frequency |
|---|---|---|
| `manifest.json` | Mutable | Weekly (new data added) |
| `{YYYY}/{MM}/{date}-{product}-{unit}-{origin}.arrow` for current month | Mutable | Weekly (new observations appended) |
| `{YYYY}/{MM}/{date}-{product}-{unit}-{origin}.arrow` for past months | **Immutable** | Never |

**Key: ~95% of files are immutable after their year closes.**

### 5.2 Cache Layers

```
┌─────────────────────────────────────────────────┐
│  Layer 1: In-memory (Svelte store)              │
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
// "arrows"       — monthly raw files
// "manifest"     — latest manifest.json
```

### 5.4 Cache-Control Headers (CDN)

```yaml
# Immutable past data (forever cache)
2018/**/*.arrow:   Cache-Control: public, max-age=31536000, immutable
2019/**/*.arrow:   Cache-Control: public, max-age=31536000, immutable
...
2024/**/*.arrow:   Cache-Control: public, max-age=31536000, immutable

# Current year — mutable (weekly updates)
2026/**/*.arrow:   Cache-Control: public, max-age=604800  # 1 week

# Manifest — mutable
manifest.json:     Cache-Control: no-cache
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
  T+10ms    [parallel] 8 monthly files (16 KB) ← network
  T+30ms    ✅ Snapshot renders (17 KB total)
  T+30ms    Write all to IndexedDB

Subsequent visit (warm cache):
  T+0ms     manifest.json (1 KB)              ← network (no-cache)
  T+5ms     [parallel] 8 monthly files (16 KB)← IndexedDB
  T+10ms    ✅ Snapshot renders (17 KB total)

Heatmap (warm cache):
  T+0ms     [parallel] 84 monthly files (168 KB) ← IndexedDB
  T+5ms     Client aggregates by week
  T+10ms    ✅ Heatmap renders

Market toggle (warm):
  T+0ms     Re-filter loaded data (0 KB)
  T+1ms     Re-aggregate by week
  T+2ms     ✅ Heatmap re-renders

Current month update scenario:
  T+0ms     manifest.json                               ← network (checks for new data)
  T+10ms    2026/06/17-Truskawki-kg-KRAJOWE.arrow      ← network (ETag check, gets fresh data)
  T+10ms    [parallel] 7 past monthly dirs              ← IndexedDB (immutable, instant)
  T+15ms    ✅ Snapshot renders
```

### 5.7 Cache Size Budget

```
Full dataset (7 years × many products):
  Monthly raw:    ~500+ files × ~0.3 KB = ~150 KB
  Manifest:       1 file × ~1 KB        = ~1 KB
  ─────────────────────────────────────────
  Total IndexedDB: ~1 MB

This is tiny for IndexedDB (typical limit is 50% of disk space).
```
