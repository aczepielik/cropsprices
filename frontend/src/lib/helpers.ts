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
  if (isNaN(value)) return '#b0a89c';  // Missing data = gray
  if (max === min) return '#d8d3ca';   // All same price = neutral color

  // Normalize: where does this value sit between min and max? (0 to 1)
  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));

  // Linear interpolation between two RGB colors
  // Low prices → rgb(216, 225, 215) (cool gray)
  // High prices → rgb(236, 209, 198) (warm beige)
  const r = Math.round(216 + (236 - 216) * t);
  const g = Math.round(225 + (209 - 225) * t);
  const b = Math.round(215 + (198 - 215) * t);
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
