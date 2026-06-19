import { describe, it, expect } from 'vitest';
import {
  heatColor,
  mergeEnvelope,
  sortMarketRows,
  computeKpis,
  niceTicks,
  isoWeekOf,
  wednesdayOfWeek,
  formatPrice,
} from './helpers';
import { filterByWeek, allWeeks, filterByMarkets, productsForCategory, aggregateByWeekYear } from './filters';
import type { PriceRecord, Product } from './types';

// ── heatColor ──

describe('heatColor', () => {
  it('returns grey for NaN', () => {
    expect(heatColor(NaN, 0, 100)).toBe('#b0a89c');
  });

  it('returns green-soft when min === max', () => {
    expect(heatColor(50, 50, 50)).toBe('#d8e1d7');
  });

  it('returns lightest green at t=0', () => {
    const c = heatColor(0, 0, 100);
    // Lowest stop is [170,195,155] → should be close to that
    const match = c.match(/rgb\((\d+),(\d+),(\d+)\)/);
    expect(match).toBeTruthy();
    const [, r, g, b] = match!.map(Number);
    expect(r).toBeGreaterThanOrEqual(160);
    expect(g).toBeGreaterThanOrEqual(185);
  });

  it('returns darkest green at t=1', () => {
    const c = heatColor(100, 0, 100);
    const match = c.match(/rgb\((\d+),(\d+),(\d+)\)/);
    expect(match).toBeTruthy();
    const [, r, g, b] = match!.map(Number);
    expect(r).toBeLessThanOrEqual(20);
    expect(g).toBeLessThanOrEqual(60);
  });

  it('clamps below min to t=0', () => {
    expect(heatColor(-10, 0, 100)).toBe(heatColor(0, 0, 100));
  });

  it('clamps above max to t=1', () => {
    expect(heatColor(200, 0, 100)).toBe(heatColor(100, 0, 100));
  });

  it('interpolates at midpoint', () => {
    const c = heatColor(50, 0, 100);
    // Should be between the lightest and darkest stops
    expect(c).toMatch(/^rgb\(\d+,\d+,\d+\)$/);
  });
});

// ── mergeEnvelope ──

describe('mergeEnvelope', () => {
  it('merges two overlapping series', () => {
    const a = [{ min: 8, max: 12 }, { min: 10, max: 14 }, null];
    const b = [null, { min: 6, max: 11 }, { min: 9, max: 13 }];
    const result = mergeEnvelope(a, b);
    expect(result).toEqual([
      { min: 8, max: 12 },
      { min: 6, max: 14 },
      { min: 9, max: 13 },
    ]);
  });

  it('returns all null when both series are all null', () => {
    const result = mergeEnvelope([null, null], [null, null]);
    expect(result).toEqual([null, null]);
  });

  it('handles series of different lengths', () => {
    const a = [{ min: 1, max: 5 }];
    const b = [{ min: 2, max: 6 }, { min: 3, max: 7 }];
    const result = mergeEnvelope(a, b);
    expect(result).toEqual([
      { min: 1, max: 6 },
      { min: 3, max: 7 },
    ]);
  });

  it('handles empty arrays', () => {
    expect(mergeEnvelope([], [])).toEqual([]);
  });

  it('takes min-of-min and max-of-max', () => {
    const a = [{ min: 5, max: 20 }];
    const b = [{ min: 3, max: 25 }];
    const result = mergeEnvelope(a, b);
    expect(result[0]).toEqual({ min: 3, max: 25 });
  });
});

// ── sortMarketRows ──

describe('sortMarketRows', () => {
  it('sorts markets with data before markets without', () => {
    const rows = [
      { place: 'Alpha', priceMin: null },
      { place: 'Beta', priceMin: 10 },
      { place: 'Gamma', priceMin: null },
      { place: 'Delta', priceMin: 8 },
    ];
    sortMarketRows(rows);
    expect(rows.map(r => r.place)).toEqual(['Beta', 'Delta', 'Alpha', 'Gamma']);
  });

  it('sorts alphabetically within each group', () => {
    const rows = [
      { place: 'Zebra', priceMin: 5 },
      { place: 'Apple', priceMin: 3 },
      { place: 'Mango', priceMin: null },
    ];
    sortMarketRows(rows);
    expect(rows.map(r => r.place)).toEqual(['Apple', 'Zebra', 'Mango']);
  });

  it('handles empty array', () => {
    const rows: { place: string; priceMin: number | null }[] = [];
    sortMarketRows(rows);
    expect(rows).toEqual([]);
  });
});

// ── computeKpis ──

describe('computeKpis', () => {
  it('returns null for empty records', () => {
    expect(computeKpis([])).toBeNull();
  });

  it('computes range and spread', () => {
    const result = computeKpis([
      { price_min: 8, price_max: 12 },
      { price_min: 10, price_max: 15 },
    ]);
    expect(result).toEqual({
      priceRange: '8.00 – 15.00 zł',
      spread: '7.00 zł',
      overallMin: 8,
      overallMax: 15,
    });
  });

  it('handles single record', () => {
    const result = computeKpis([{ price_min: 5, price_max: 10 }]);
    expect(result!.overallMin).toBe(5);
    expect(result!.overallMax).toBe(10);
    expect(result!.spread).toBe('5.00 zł');
  });
});

// ── niceTicks ──

describe('niceTicks', () => {
  it('generates round ticks for 0-100 range', () => {
    const ticks = niceTicks(0, 100, 5);
    expect(ticks[0]).toBeLessThanOrEqual(0);
    expect(ticks[ticks.length - 1]).toBeGreaterThanOrEqual(100);
    // Ticks should be evenly spaced
    const step = ticks[1] - ticks[0];
    for (let i = 2; i < ticks.length; i++) {
      expect(ticks[i] - ticks[i - 1]).toBeCloseTo(step, 5);
    }
  });

  it('returns single tick when min === max', () => {
    expect(niceTicks(5, 5)).toEqual([5]);
  });
});

// ── isoWeekOf + wednesdayOfWeek ──

describe('isoWeekOf', () => {
  it('returns correct ISO week for a known date', () => {
    // 2026-01-12 is Monday of ISO week 3 of 2026
    const d = new Date('2026-01-12T00:00:00Z');
    const { year, week } = isoWeekOf(d);
    expect(year).toBe(2026);
    expect(week).toBe(3);
  });
});

describe('wednesdayOfWeek', () => {
  it('returns Wednesday of the given ISO week', () => {
    const wed = wednesdayOfWeek(2026, 3);
    expect(wed).toBe('2026-01-14');
  });
});

// ── formatPrice ──

describe('formatPrice', () => {
  it('formats to 2 decimal places', () => {
    expect(formatPrice(5)).toBe('5.00');
    expect(formatPrice(3.14159)).toBe('3.14');
    expect(formatPrice(0)).toBe('0.00');
  });
});

// ── filterByWeek ──

describe('filterByWeek', () => {
  const records: PriceRecord[] = [
    { date: new Date('2026-01-12T00:00:00Z'), product: 'A', place: 'X', origin: 'KRAJOWE', price_min: 10, price_max: 12 },
    { date: new Date('2026-01-14T00:00:00Z'), product: 'A', place: 'Y', origin: 'KRAJOWE', price_min: 8, price_max: 11 },
    { date: new Date('2026-01-19T00:00:00Z'), product: 'A', place: 'X', origin: 'KRAJOWE', price_min: 11, price_max: 14 },
  ];

  it('filters records by ISO week', () => {
    const result = filterByWeek(records, 2026, 3);
    expect(result).toHaveLength(2);
  });

  it('returns empty for week with no data', () => {
    const result = filterByWeek(records, 2026, 10);
    expect(result).toHaveLength(0);
  });
});

// ── allWeeks ──

describe('allWeeks', () => {
  it('returns distinct weeks sorted chronologically', () => {
    const records: PriceRecord[] = [
      { date: new Date('2026-01-19T00:00:00Z'), product: 'A', place: 'X', origin: 'KRAJOWE', price_min: 10, price_max: 12 },
      { date: new Date('2026-01-12T00:00:00Z'), product: 'A', place: 'X', origin: 'KRAJOWE', price_min: 10, price_max: 12 },
    ];
    const weeks = allWeeks(records);
    expect(weeks).toHaveLength(2);
    expect(weeks[0].week).toBeLessThan(weeks[1].week);
  });
});

// ── filterByMarkets ──

describe('filterByMarkets', () => {
  const records: PriceRecord[] = [
    { date: new Date('2026-01-12T00:00:00Z'), product: 'A', place: 'Warszawa', origin: 'KRAJOWE', price_min: 10, price_max: 12 },
    { date: new Date('2026-01-12T00:00:00Z'), product: 'A', place: 'Kraków', origin: 'KRAJOWE', price_min: 8, price_max: 11 },
  ];

  it('returns all records when markets is empty', () => {
    expect(filterByMarkets(records, new Set())).toHaveLength(2);
  });

  it('filters to selected markets', () => {
    expect(filterByMarkets(records, new Set(['Warszawa']))).toHaveLength(1);
  });
});

// ── productsForCategory ──

describe('productsForCategory', () => {
  const manifest = {
    years: [2026],
    currentYear: 2026,
    products: [
      { name: 'Truskawki', unit: 'kg', origin: 'KRAJOWE' as const, category: 'owoce' as const },
      { name: 'Banany', unit: 'kg', origin: 'IMPORTOWANE' as const, category: 'owoce' as const },
      { name: 'Ziemniaki', unit: 'kg', origin: 'KRAJOWE' as const, category: 'warzywa' as const },
    ],
    places: [],
    lastUpdate: '2026-06-19',
  };

  it('filters by category and origin', () => {
    const result = productsForCategory(manifest, 'owoce', 'KRAJOWE');
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('Truskawki');
  });

  it('returns empty for non-matching combination', () => {
    expect(productsForCategory(manifest, 'warzywa', 'IMPORTOWANE')).toHaveLength(0);
  });
});

// ── aggregateByWeekYear ──

describe('aggregateByWeekYear', () => {
  it('groups records by year-week and computes averages', () => {
    const records: PriceRecord[] = [
      { date: new Date('2026-01-12T00:00:00Z'), product: 'A', place: 'X', origin: 'KRAJOWE', price_min: 8, price_max: 12 },
      { date: new Date('2026-01-14T00:00:00Z'), product: 'A', place: 'Y', origin: 'KRAJOWE', price_min: 10, price_max: 14 },
    ];
    const result = aggregateByWeekYear(records);
    expect(result.size).toBe(1);
    const vals = [...result.values()][0];
    // mid1 = (8+12)/2 = 10, mid2 = (10+14)/2 = 12 → avg = 11
    expect(vals.value).toBe(11);
    expect(vals.ribbonMin).toBe(8);
    expect(vals.ribbonMax).toBe(14);
  });

  it('returns empty map for empty records', () => {
    expect(aggregateByWeekYear([]).size).toBe(0);
  });
});
