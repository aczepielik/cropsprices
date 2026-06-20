// arrow-loader.ts — Handles loading data from Apache Arrow files on the server.
//
// WHAT IS ARROW? Apache Arrow is a columnar data format — think of it like a
// super-efficient spreadsheet. It's much faster to load than CSV or JSON because
// the data is stored in a binary format that computers can read directly.
//
// HOW IT WORKS:
// 1. We fetch a .arrow file over HTTP (just like fetching an image)
// 2. We decode it into a table using the apache-arrow library
// 3. We convert rows into plain JavaScript objects (PriceRecord[])
//
// DATA LAYOUT on disk:
//   /data/manifest.json          — metadata (product list, years, markets)
//   /data/archive/               — all historical data (one file per product)
//   /data/2026/                  — current year data (one file per product)
//
// Each Arrow file is named like: "Truskawki-kg-KRAJOWE.arrow"
// (product unit origin)

import { tableFromIPC } from 'apache-arrow';
import type { Manifest, PriceRecord } from './types';
import { debug } from './logger';

const log = debug('arrow-loader');

// Base URL for data files. In dev, Vite serves these from /public/data/.
// In production, they're served from the same domain root.
const DATA_BASE = '/data';

// Cache the manifest so we only fetch it once per page load.
// Using `undefined` instead of `null` so the `if (manifestCache)` check works.
let manifestCache: Manifest | undefined;

/**
 * Load the manifest.json — our "table of contents" for all available data.
 * Called once at app startup. Subsequent calls return the cached copy.
 */
export async function loadManifest(): Promise<Manifest> {
  if (manifestCache) return manifestCache;
  const res = await fetch(`${DATA_BASE}/manifest.json`);
  const data: Manifest = await res.json();
  manifestCache = data;
  return data;
}

/**
 * Product names in the manifest sometimes contain commas (e.g. "Jabłka, kg").
 * Arrow file names can't have commas, so we replace them with hyphens:
 * "Jabłka, kg" → "Jabłka-kg". The unit and origin are appended separately
 * by arrowFilePath(), so we only need to handle the name here.
 */
function productNameForFile(name: string): string {
  return name.replace(/,/g, '-');
}

/**
 * Build the URL path to an Arrow file for a specific product.
 *
 * Examples:
 *   arrowFilePath("Truskawki", "kg", "KRAJOWE")       → "/data/archive/Truskawki-kg-KRAJOWE.arrow"
 *   arrowFilePath("Truskawki", "kg", "KRAJOWE", 2026)  → "/data/2026/Truskawki-kg-KRAJOWE.arrow"
 */
function arrowFilePath(name: string, unit: string, origin: string, year?: number): string {
  const productSlug = productNameForFile(name);
  const fileSlug = `${productSlug}-${unit}-${origin}.arrow`;
  if (year) {
    return `${DATA_BASE}/${year}/${fileSlug}`;
  }
  return `${DATA_BASE}/archive/${fileSlug}`;
}

/**
 * Fetch and decode a single Arrow file into an array of PriceRecord objects.
 *
 * The `arrow.tableFromIPC()` call is the magic — it takes raw bytes from the
 * network and gives us a structured table we can iterate over.
 *
 * Returns [] if the file doesn't exist (some products don't have data for all years).
 */
export async function loadArrowFile(path: string): Promise<PriceRecord[]> {
  const res = await fetch(path);
  if (!res.ok) return [];  // File not found is normal — not all products have data every year

  // Convert the response to raw bytes (ArrayBuffer)
  const buffer = await res.arrayBuffer();

  // Decode Arrow IPC format into a table
  let table;
  try {
    table = tableFromIPC(buffer);
  } catch (e) {
    log('failed to decode arrow file', { path, error: String(e) });
    return [];  // Corrupt or non-Arrow file (e.g. HTML fallback) — treat as no data
  }

  // Convert Arrow table rows into plain JS objects
  const records: PriceRecord[] = [];
  for (let i = 0; i < table.numRows; i++) {
    // .getChild() gets a column by name, .get(i) gets the value at row i
    const dateVal = table.getChild('date')?.get(i);
    const product = table.getChild('product')?.get(i) as string;
    const place = table.getChild('place')?.get(i) as string;
    const origin = table.getChild('origin')?.get(i) as string;
    const priceMin = table.getChild('price_min')?.get(i) as number;
    const priceMax = table.getChild('price_max')?.get(i) as number;

    records.push({
      // Arrow dates can come back as Date objects or as numbers (days since epoch)
      date: dateVal instanceof Date ? dateVal : new Date(dateVal as number),
      product,
      place,
      origin,
      price_min: priceMin,
      price_max: priceMax,
    });
  }
  return records;
}

/**
 * Load all data for a specific product: both historical archive AND current year.
 *
 * Promise.all() runs both fetches in parallel — this is ~2x faster than fetching
 * them one after another. The browser can handle multiple HTTP requests at once.
 *
 * Returns a combined array sorted by date (archive first, then current year).
 */
export async function loadProductData(
  name: string,
  unit: string,
  origin: string,
  currentYear: number,
): Promise<PriceRecord[]> {
  const [archive, current] = await Promise.all([
    loadArrowFile(arrowFilePath(name, unit, origin)),        // historical data
    loadArrowFile(arrowFilePath(name, unit, origin, currentYear)),  // current year
  ]);
  return [...archive, ...current];  // Spread operator: combines both arrays
}

/**
 * Pre-aggregated week ranges for a product, keyed by market → year → week.
 *
 * Structure: { "Bronisze": { "2024": { "3": {"min": 2.5, "max": 4.2}, ... }, ... }, ... }
 *
 * This is computed during ETL and shipped as a tiny JSON (~1-3KB per product).
 * The frontend loads this instead of iterating 2500+ raw records at runtime.
 */
export type WeekRanges = Record<string, Record<string, Record<string, { min: number; max: number }>>>;

let weekRangesCache = new Map<string, WeekRanges>();

function weekRangesFilePath(name: string, unit: string, origin: string, year?: number): string {
  const slug = productNameForFile(name);
  const fileSlug = `${slug}-${unit}-${origin}.weeks.json`;
  if (year) {
    return `${DATA_BASE}/${year}/${fileSlug}`;
  }
  return `${DATA_BASE}/archive/${fileSlug}`;
}

/**
 * Load pre-aggregated week ranges for a product (archive + current year).
 *
 * Merges both files into a single WeekRanges object. If a file is missing,
 * that portion is simply skipped (some products don't have data for all years).
 *
 * Returns null if neither file exists (product has no data at all).
 */
export async function loadWeekRanges(
  name: string,
  unit: string,
  origin: string,
  currentYear: number,
): Promise<WeekRanges | null> {
  const cacheKey = `${name}-${unit}-${origin}`;
  const cached = weekRangesCache.get(cacheKey);
  if (cached) return cached;

  const [archiveRes, currentRes] = await Promise.all([
    fetch(weekRangesFilePath(name, unit, origin)).then(r => r.ok ? r.json() : null),
    fetch(weekRangesFilePath(name, unit, origin, currentYear)).then(r => r.ok ? r.json() : null),
  ]);

  if (!archiveRes && !currentRes) return null;

  // Merge: current year data overrides archive for overlapping weeks
  const merged: WeekRanges = {};
  for (const source of [archiveRes, currentRes]) {
    if (!source) continue;
    for (const [market, years] of Object.entries(source)) {
      const m = (merged[market] ??= {});
      for (const [year, weeks] of Object.entries(years)) {
        const y = (m[year] ??= {});
        Object.assign(y, weeks);
      }
    }
  }

  weekRangesCache.set(cacheKey, merged);
  return merged;
}
