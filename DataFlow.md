# Data Flow Design

Data flow from Arrow files to each visualization in mock6.html: what files load, what filters apply, what is computed on the client, and caching strategy.

---

## 1. Data Scale

186 products (compound keys: name + unit + origin), 17 markets, 9 years (2018-2026). Products are seasonal — not all 186 have data every month. Total: **268 files, 5.3 MB**.

---

## 2. File Layout

Two tiers: **archive** (immutable, all past years concatenated) and **current year** (mutable, updates weekly).

```
public/data/
├── manifest.json
├── archive/
│   ├── Agrest-kg-KRAJOWE.arrow               # 2018-2025 data, all markets (~24 KB)
│   ├── Ananasy-szt.-IMPORTOWANE.arrow
│   └── ... (181 files)
└── 2026/
    ├── Agrest-kg-KRAJOWE.arrow               # 2026 data only, all markets (~13 KB)
    ├── Ananasy-szt.-IMPORTOWANE.arrow
    └── ... (87 files)
```

**Archive files** — one per product, all past years concatenated. Change once per year (January 1st merge). Immutable 364 days/year.

**Current-year files** — one per product, current year only. Grow weekly as new observations arrive.

**Product identity:** Compound key `(Product, Unit, Origin)` — e.g., "Rzodkiewka, kg, KRAJOWE" and "Rzodkiewka, pęczek, KRAJOWE" are separate files.

**Arrow columns:**

| Column | Type | Meaning |
|---|---|---|
| `date` | Date32 | Observation date |
| `product` | Utf8 (dictionary) | Product name |
| `place` | Utf8 (dictionary) | Market name |
| `origin` | Utf8 (dictionary) | KRAJOWE / IMPORTOWANE |
| `price_min` | Float32 | Minimum wholesale price (zł/kg) |
| `price_max` | Float32 | Maximum wholesale price (zł/kg) |

No `lookups.arrow`. No pre-aggregated files. No compression.

---

## 3. Filter Chain

```
Category (Kategoria)     → UI filter: determines which products appear in Product dropdown.
                               Does NOT filter Arrow data directly.

Origin (Pochodzenie)     → UI filter: declutters Product dropdown by origin.
                               Each combination is a distinct product. No Arrow filtering needed.

Product (Produkt)        → File-level filter: determines which archive/current-year files to load.
                               Product is built into the file name. No client-side filtering needed.

Markets (Rynki Hurtowe)  → Arrow filter: WHERE place IN selectedMarkets
                               Reduces rows ~4×. Heatmap re-aggregates on market toggle (client-side).

Date (Punkt Odniesienia) → Arrow filter: WHERE date = selected_date
                               Snapshot only. Reduces to ~(4 markets × 1 date) = 4 rows.
```

---

## 4. View-by-View Data Flow

### 4.1 Snapshot View

**Data needed:** 2-3 years around selected date for context chart.

**File loading:**
```
1. manifest.json                              → ~2 KB
2. archive/Truskawki-kg-KRAJOWE.arrow        → ~46 KB  (all past years)
3. 2026/Truskawki-kg-KRAJOWE.arrow           → ~9 KB   (current year)
   TOTAL: ~57 KB, 3 HTTP requests
```

**Client-side pipeline:**
```
archive + current-year files
  → Filter: place IN selectedMarkets
  → Split into:
      ├── [KPIs] Filter: date = selectedDate
      │     → Aggregate: MIN(price_min), MAX(price_max)
      │     → Compute spread, WoW delta
      │
      ├── [Context Chart] Filter: date IN [selectedDate ± N weeks]
      │     → Aggregate: MIN(price_min) per date, MAX(price_max) per date
      │     → Repeat for year-1 and year-2 (offset by -52 and -104 weeks)
      │
      └── [Market Table] Filter: date = selectedDate
            → Keep per-place rows
```

**Year boundaries:** Archive contains all years, so cross-boundary windows (e.g., Jan 15 needs Dec data) read from the same file.

### 4.2 Heatmap View

**Data needed:** ALL years for selected product. Week × Year grid.

**File loading:** Same 2 files as snapshot (archive + current-year). No additional requests.

**Client-side aggregation:**
```
archive + current-year files
  → Filter: place IN selectedMarkets
  → Group by (year, ISO_week):
      → cellVal = mean of (price_min + price_max) / 2
      → ribbonMin = min(price_min)
      → ribbonMax = max(price_max)
  → Normalize globally
  → Render: heat cells + marginal ribbons
```

**Market toggling:** Re-filter already-loaded data (0 KB), re-aggregate (<1ms).

---

## 5. Caching Strategy

### 5.1 Immutability

| File | Mutability | Change frequency |
|---|---|---|
| `archive/*.arrow` | Nearly immutable | Once per year (Jan 1st merge) |
| `YYYY/*.arrow` (current) | Mutable | Weekly (new observations) |
| `manifest.json` | Mutable | Weekly |

### 5.2 HTTP Cache Headers

```yaml
# Archive — immutable (re-validated ~once per year at most)
archive/*.arrow:
  Cache-Control: public, max-age=31536000, immutable

# Current year — re-validate weekly
2026/*.arrow:
  Cache-Control: no-cache
  ETag: "<hash>"

# Manifest — re-validate every visit
manifest.json:
  Cache-Control: no-cache
  ETag: "<hash>"
```

### 5.3 No IndexedDB

At 55 KB total load, HTTP cache is sufficient. IndexedDB saves ~7 ms on page refresh at the cost of ~100 lines of cache management code. Not worth it.

### 5.4 Loading Waterfall

```
First visit (cold cache):
  T+0ms     manifest.json (~2 KB)                    ← network
  T+10ms    [parallel] archive (~46 KB) + current (~9 KB) ← network
  T+50ms    ✅ renders (~57 KB total)

Page refresh (HTTP cache warm):
  T+0ms     manifest.json → 304 (0 KB)
            archive → immutable, no revalidation
            current → 304 if unchanged (0 KB)
  T+10ms    ✅ renders (0 KB transferred)

Market toggle:
  T+0ms     Re-filter loaded data (0 KB)
  T+1ms     Re-aggregate
  T+2ms     ✅ re-renders
```

---

## 6. January 1st Merge (Year Rollover)

When the year changes (2026 → 2027):

```
1. ETL detects year change
2. For each product:
   a. Read: archive/Truskawki-kg-KRAJOWE.arrow (2018-2025)
   b. Read: 2026/Truskawki-kg-KRAJOWE.arrow (full year)
   c. Concatenate into new archive/Truskawki-kg-KRAJOWE.arrow (2018-2026)
   d. Deploy new archive file
3. Delete: 2026/ directory
4. Create: 2027/ directory (empty, ready for weekly updates)
5. Update manifest.json: currentYear → 2027
```

Old archive files remain in CDN cache until `max-age` expires. Staleness window: 0-1 day (merge happens Jan 1, users unlikely to check crop prices that day).

---

## 7. Manifest Structure

```json
{
  "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
  "currentYear": 2026,
  "products": [
    {"name": "Rzodkiewka", "unit": "kg", "origin": "KRAJOWE", "category": "warzywa"},
    {"name": "Truskawki", "unit": "kg", "origin": "KRAJOWE", "category": "owoce"}
  ],
  "places": ["Białystok", "Bronisze", "Bydgoszcz", "Gdańsk", "Gorzów Wlkp.", "Kalisz", "Kielce", "Kraków", "Lublin", "Poznań", "Radom", "Rynek4", "Rzeszów", "Sandomierz", "Szczecin", "Wrocław", "Łódź"],
  "lastUpdate": "2026-06-18"
}
```
