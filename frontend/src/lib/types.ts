// types.ts — Central type definitions for the entire frontend.
//
// WHY: TypeScript interfaces let us catch bugs at compile time instead of runtime.
// For example, if you misspell "price_min" as "price_mim", TypeScript will error
// immediately rather than silently producing undefined values at runtime.
//
// All components and lib modules import from here, so there's one source of truth
// for what our data looks like.

// Union types: Category can ONLY be 'owoce' (fruits) or 'warzywa' (vegetables).
// This prevents typos like 'fruit' or 'Owoce' from silently slipping through.
export type Category = 'owoce' | 'warzywa';
export type Origin = 'KRAJOWE' | 'IMPORTOWANE';

// Interface = a shape that objects must follow.
// Think of it as a contract: every Product MUST have name, unit, origin, and category.
export interface Product {
  name: string;
  unit: string;
  origin: Origin;
  category: Category;
}

// The manifest.json is our "table of contents" — it lists all available products,
// marketplaces, and years. We load it once at startup and use it to populate filters.
export interface Manifest {
  years: number[];
  currentYear: number;
  products: Product[];
  places: string[];
  lastUpdate: string;
}

// A single row of price data from an Arrow file.
// Each row = one product at one marketplace on one date, with min and max prices.
export interface PriceRecord {
  date: Date;
  product: string;
  place: string;
  origin: string;
  price_min: number;
  price_max: number;
}

// All filter state lives here. When the user changes a filter (e.g. picks a new product),
// we update this object and re-fetch/re-compute the data.
export interface Filters {
  category: Category;
  origin: Origin;
  product: Product | null;
  markets: Set<string>;  // Set = unique values, fast .has() lookups
  date: string;          // ISO date string like "2026-01-15"
  windowWeeks: number;   // How many weeks ± around the selected date to show in context chart
}

// Two views the user can switch between via the sidebar tabs.
export type ViewMode = 'snapshot' | 'heatmap';

// KPI = Key Performance Indicator — the summary cards at the top of the snapshot view.
export interface SnapshotKpis {
  priceRange: string;
  spread: string;
  wowRange: string;  // WoW = Week over Week change
}

// A single change in price between two periods, used for the "compare" section of the snapshot view.
export interface ComparisonChange {
  prevLow: number;
  prevUpper: number;
  lowerChange: number;
  upperChange: number;
  lowerPct: number;
  upperPct: number;
}

// One row in the market breakdown table.
export interface MarketRow {
  place: string;
  priceMin: number | null;
  priceMax: number | null;
  spread: number | null;
  deviation: number | null;
}

// One cell in the heatmap grid (week × year).
export interface HeatmapCell {
  year: number;
  week: number;       // 1-53 (ISO week numbers)
  value: number;      // Average price across selected markets
  ribbonMin: number;  // Lowest price_min across markets for this week
  ribbonMax: number;  // Highest price_max across markets for this week
}
