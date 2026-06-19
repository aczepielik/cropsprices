// filters.ts — Data transformation functions.
//
// This module contains pure functions that take data in, return data out.
// No side effects, no network calls, no DOM manipulation.
//
// WHY PURE FUNCTIONS? They're easy to test (same input → same output),
// easy to understand, and impossible to break accidentally.

import type { PriceRecord, Filters, Product, Manifest } from './types';
import { isoWeekOf } from './helpers';

/**
 * Keep only records from selected marketplaces.
 *
 * Set.has() is O(1) — instant lookup regardless of how many markets we have.
 * Using an array.includes() would be O(n) — slower for large lists.
 *
 * If no markets are selected (empty Set), return all records — don't filter to nothing.
 */
export function filterByMarkets(records: PriceRecord[], markets: Set<string>): PriceRecord[] {
  if (markets.size === 0) return records;
  return records.filter(r => markets.has(r.place));
}

/**
 * Keep only records matching a specific date (YYYY-MM-DD string).
 *
 * We compare the ISO date string (first 10 chars) rather than the full datetime
 * because the source data has timestamps but we only care about the day.
 */
export function filterByDate(records: PriceRecord[], date: string): PriceRecord[] {
  return records.filter(r => r.date.toISOString().slice(0, 10) === date);
}

/**
 * Keep only records whose date falls within the given ISO week.
 * Multiple dates in the same week (e.g. Mon from market A, Wed from market B)
 * are all included — that's the whole point of weekly analysis.
 */
export function filterByWeek(records: PriceRecord[], isoYear: number, week: number): PriceRecord[] {
  return records.filter(r => {
    const { year, week: w } = isoWeekOf(r.date);
    return year === isoYear && w === week;
  });
}

/**
 * Collect all distinct ISO weeks present in the records, sorted chronologically.
 * Returns an array of { year, week } objects.
 */
export function allWeeks(records: PriceRecord[]): { year: number; week: number }[] {
  const seen = new Map<string, { year: number; week: number }>();
  for (const r of records) {
    const { year, week } = isoWeekOf(r.date);
    const key = `${year}-W${week}`;
    if (!seen.has(key)) seen.set(key, { year, week });
  }
  return [...seen.values()].sort((a, b) => a.year - b.year || a.week - b.week);
}

/**
 * Get all products belonging to a specific category and origin.
 * Used to populate the product dropdown after the user picks a category and origin.
 */
export function productsForCategory(manifest: Manifest, category: string, origin: string): Product[] {
  return manifest.products.filter(p => p.category === category && p.origin === origin);
}

/**
 * Get unique origin values (KRAJOWE/IMPORTOWANE) from a list of products.
 * The [...new Set()] trick: Set removes duplicates, then we spread back to array.
 */
export function originsForProducts(products: Product[]): string[] {
  return [...new Set(products.map(p => p.origin))];
}

/**
 * Group records by date, keeping the min and max price across all marketplaces.
 *
 * Returns a Map where keys are "YYYY-MM-DD" strings and values are {min, max}.
 * Used by the context chart to show price ranges over time.
 *
 * Example output:
 *   "2026-01-15" → { min: 2.5, max: 4.2 }
 *   "2026-01-22" → { min: 2.8, max: 4.5 }
 */
export function aggregateByDate(records: PriceRecord[]): Map<string, { min: number; max: number }> {
  const map = new Map<string, { min: number; max: number }>();
  for (const r of records) {
    const key = r.date.toISOString().slice(0, 10);
    const existing = map.get(key);
    if (existing) {
      // Update existing entry with new min/max
      existing.min = Math.min(existing.min, r.price_min);
      existing.max = Math.max(existing.max, r.price_max);
    } else {
      // First record for this date
      map.set(key, { min: r.price_min, max: r.price_max });
    }
  }
  return map;
}

/**
 * Group records by (year, ISO week) for the heatmap.
 *
 * The heatmap shows a grid: rows = years, columns = weeks (1-53).
 * Each cell's color represents the average price for that week across all markets.
 * "ribbonMin" and "ribbonMax" are used to draw the marginal ribbons on the edges.
 *
 * Returns a Map where keys are "YYYY-WW" (e.g. "2026-3") and values contain
 * the average price, min ribbon, and max ribbon for that week.
 */
export function aggregateByWeekYear(records: PriceRecord[]): Map<string, { value: number; ribbonMin: number; ribbonMax: number }> {
  // Three parallel maps: one for mid prices, one for min prices, one for max prices
  const groups = new Map<string, number[]>();
  const minGroups = new Map<string, number[]>();
  const maxGroups = new Map<string, number[]>();

  for (const r of records) {
    const d = r.date;
    // Calculate ISO week number from date
    const yearStart = new Date(d.getFullYear(), 0, 1);
    const weekNum = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + yearStart.getDay() + 1) / 7);
    const key = `${d.getFullYear()}-${weekNum}`;

    // Mid price = average of min and max (the dot in the center of each heatmap cell)
    const mid = (r.price_min + r.price_max) / 2;
    if (!groups.has(key)) {
      groups.set(key, []);
      minGroups.set(key, []);
      maxGroups.set(key, []);
    }
    groups.get(key)!.push(mid);      // ! = "trust me, this exists" (TypeScript assertion)
    minGroups.get(key)!.push(r.price_min);
    maxGroups.get(key)!.push(r.price_max);
  }

  // Now compute averages and extremes for each week
  const result = new Map<string, { value: number; ribbonMin: number; ribbonMax: number }>();
  for (const [key, vals] of groups) {
    const mins = minGroups.get(key)!;
    const maxs = maxGroups.get(key)!;
    result.set(key, {
      value: vals.reduce((a, b) => a + b, 0) / vals.length,  // Average of mid prices
      ribbonMin: Math.min(...mins),   // Lowest min price across markets
      ribbonMax: Math.max(...maxs),   // Highest max price across markets
    });
  }
  return result;
}

/**
 * Precompute a lookup map of market-filtered min/max spread for every (year, week).
 *
 * This replaces the per-week filterByWeek() calls in SnapshotView with a single
 * O(n) pass over records, making chart rendering O(1) per lookup instead of O(n).
 *
 * Returns a Map keyed by "YYYY-WW" → { min, max }.
 */
export function buildWeekSpreadMap(
  records: PriceRecord[],
  markets: Set<string>
): Map<string, { min: number; max: number }> {
  const map = new Map<string, { min: number; max: number }>();
  for (const r of records) {
    if (markets.size > 0 && !markets.has(r.place)) continue;
    const { year, week } = isoWeekOf(r.date);
    const key = `${year}-${week}`;
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
