// helpers.ts — Small utility functions used across the app.
//
// These are "pure functions" — they take input, return output, and don't
// touch the outside world. This makes them trivial to test and reuse.

/**
 * Convert a price value to a color for the heatmap.
 *
 * Uses linear interpolation between two colors:
 *   - Cool gray (#d8d3ca) for low prices
 *   - Warm beige (#ece1c8) for high prices
 *
 * The 't' variable is a value between 0 and 1 representing where the price
 * falls between the global min and max. This is called "normalization."
 *
 * Returns '#b0a89c' (gray) for missing data (NaN values).
 */
export function heatColor(value: number, min: number, max: number): string {
  if (isNaN(value)) return '#b0a89c';
  if (max === min) return '#d8e1d7';

  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));

  const stops = [
    [245, 240, 232],
    [215, 225, 200],
    [165, 200, 155],
    [100, 165, 110],
    [55, 120, 70],
    [30, 80, 48],
    [15, 50, 28],
  ];

  const seg = t * (stops.length - 1);
  const lo = Math.floor(seg);
  const hi = Math.min(lo + 1, stops.length - 1);
  const f = seg - lo;
  const r = Math.round(stops[lo][0] + (stops[hi][0] - stops[lo][0]) * f);
  const g = Math.round(stops[lo][1] + (stops[hi][1] - stops[lo][1]) * f);
  const b = Math.round(stops[lo][2] + (stops[hi][2] - stops[lo][2]) * f);
  return `rgb(${r},${g},${b})`;
}

/**
 * Generate "nice" tick marks for chart axes.
 *
 * Instead of showing 1.23456, 2.46912, 3.70368... we want 1, 2, 3, 4, 5.
 * This algorithm finds a "round" step size (1, 2, 5, 10, 20, 50, etc.)
 * and generates evenly spaced ticks.
 *
 * This is a common need in data visualization — every chart library has
 * some version of this algorithm.
 */
export function niceTicks(min: number, max: number, count: number = 5): number[] {
  if (max === min) return [min];

  // Raw step = how far apart ticks would be if we just divided evenly
  const step = (max - min) / (count - 1);

  // Find the "order of magnitude" — is this a 0-5 range? 0-50? 0-500?
  const niceStep = Math.pow(10, Math.floor(Math.log10(step)));

  // How does our raw step compare to the order of magnitude?
  const residual = step / niceStep;

  // Pick the nearest "nice" multiplier: 1, 2, 5, or 10
  let niceMultiplier: number;
  if (residual <= 1.5) niceMultiplier = 1;
  else if (residual <= 3) niceMultiplier = 2;
  else if (residual <= 7) niceMultiplier = 5;
  else niceMultiplier = 10;

  const finalStep = niceStep * niceMultiplier;

  // Round down to the nearest multiple of our step
  const niceMin = Math.floor(min / finalStep) * finalStep;

  // Generate ticks from niceMin up to niceMax
  const ticks: number[] = [];
  for (let v = niceMin; v <= max + finalStep * 0.5; v += finalStep) {
    ticks.push(Math.round(v * 1000) / 1000);  // Avoid floating point weirdness
  }
  return ticks;
}

/**
 * Format a Date for Polish locale display.
 * toLocaleDateString() handles all the localization for us.
 *
 * Output example: "15 sty 2026" (Polish month abbreviation)
 */
export function formatDate(d: Date): string {
  return d.toLocaleDateString('pl-PL', { day: 'numeric', month: 'short', year: 'numeric' });
}

/**
 * Format a number to 2 decimal places for price display.
 * toFixed() always returns exactly 2 digits after the decimal.
 *
 * Example: 2.5 → "2.50", 3 → "3.00"
 */
export function formatPrice(v: number): string {
  return v.toFixed(2);
}

/**
 * Get the ISO week number (1-53) for a date.
 * Week 1 is the week containing January 4th.
 * Used to position data in the heatmap grid (columns = weeks).
 */
export function getISOWeek(d: Date): number {
  const yearStart = new Date(d.getFullYear(), 0, 1);
  return Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + yearStart.getDay() + 1) / 7);
}

/**
 * Get the 4-digit year from a Date.
 * Trivial helper, but makes code more readable than calling d.getFullYear() everywhere.
 */
export function getYear(d: Date): number {
  return d.getFullYear();
}

/**
 * Compute ISO 8601 week-numbering year and week for a given Date.
 *
 * ISO weeks start on Monday. Week 1 is the week containing January 4th.
 * The week-numbering year can differ from the calendar year
 * (e.g., 2025-12-31 is ISO week 1 of 2026).
 */
export function isoWeekOf(d: Date): { year: number; week: number } {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  // Set to nearest Thursday (current date + 4 - current day of week, making Sunday = 7)
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return { year: date.getUTCFullYear(), week: weekNo };
}

/**
 * Return the Wednesday (YYYY-MM-DD) of the given ISO week.
 * Wednesday is day 3 of an ISO week (Mon=1 … Sun=7), the "center" day.
 */
export function wednesdayOfWeek(isoYear: number, week: number): string {
  // Jan 4 is always in ISO week 1 of its year.
  // From Jan 4, week W is at offset (W - 1) * 7 days. Wednesday is day offset 2.
  const jan4 = new Date(Date.UTC(isoYear, 0, 4));
  const dayOfWeekJan4 = jan4.getUTCDay() || 7; // 1=Mon … 7=Sun
  // Monday of week 1 is Jan 4 minus (dayOfWeekJan4 - 1) days
  const mondayW1 = new Date(jan4.getTime() - (dayOfWeekJan4 - 1) * 86400000);
  const wednesday = new Date(mondayW1.getTime() + (week - 1) * 7 * 86400000 + 2 * 86400000);
  return wednesday.toISOString().slice(0, 10);
}

/**
 * Return the Monday (YYYY-MM-DD) of the given ISO week.
 */
export function mondayOfWeek(isoYear: number, week: number): string {
  const jan4 = new Date(Date.UTC(isoYear, 0, 4));
  const dayOfWeekJan4 = jan4.getUTCDay() || 7;
  const mondayW1 = new Date(jan4.getTime() - (dayOfWeekJan4 - 1) * 86400000);
  const monday = new Date(mondayW1.getTime() + (week - 1) * 7 * 86400000);
  return monday.toISOString().slice(0, 10);
}

/**
 * Return the Sunday (YYYY-MM-DD) of the given ISO week.
 */
export function sundayOfWeek(isoYear: number, week: number): string {
  const jan4 = new Date(Date.UTC(isoYear, 0, 4));
  const dayOfWeekJan4 = jan4.getUTCDay() || 7;
  const mondayW1 = new Date(jan4.getTime() - (dayOfWeekJan4 - 1) * 86400000);
  const sunday = new Date(mondayW1.getTime() + (week - 1) * 7 * 86400000 + 6 * 86400000);
  return sunday.toISOString().slice(0, 10);
}

/**
 * Canonical week key for sorting and deduplication: "YYYY-Www".
 */
export function weekKey(isoYear: number, week: number): string {
  return `${isoYear}-W${String(week).padStart(2, '0')}`;
}

/**
 * Parse a week key "YYYY-Www" back into { year, week }.
 */
export function parseWeekKey(key: string): { year: number; week: number } {
  const [y, w] = key.split('-W');
  return { year: Number(y), week: Number(w) };
}
