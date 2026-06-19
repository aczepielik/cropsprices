import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import '@testing-library/jest-dom/vitest';
import SnapshotView from './SnapshotView.svelte';
import type { PriceRecord } from '../lib/types';
import { wednesdayOfWeek } from '../lib/helpers';

afterEach(() => cleanup());

function makeRecord(place: string, date: string, min: number, max: number): PriceRecord {
  return {
    date: new Date(date + 'T00:00:00Z'),
    product: 'TestProduct',
    place,
    origin: 'KRAJOWE',
    price_min: min,
    price_max: max,
  };
}

// helper: Wednesday of the ISO week containing `date`
function weekWednesday(date: string): string {
  const d = new Date(date + 'T00:00:00Z');
  const date2 = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  date2.setUTCDate(date2.getUTCDate() + 4 - (date2.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(date2.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((date2.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return wednesdayOfWeek(date2.getUTCFullYear(), weekNo);
}

describe('SnapshotView week-based table', () => {
  // Records from two different weeks
  const records: PriceRecord[] = [
    // Week of 2026-01-12 (Mon Jan 12 – Sun Jan 18)
    makeRecord('Warszawa', '2026-01-12', 10, 12),
    makeRecord('Kraków', '2026-01-14', 8, 11),
    makeRecord('Gdańsk', '2026-01-16', 9, 13),
    // Wrocław has data in week 2 only
    makeRecord('Wrocław', '2026-01-20', 7, 10),
    // Week of 2026-01-19 (Mon Jan 19 – Sun Jan 25)
    makeRecord('Warszawa', '2026-01-19', 11, 14),
    makeRecord('Kraków', '2026-01-21', 9, 12),
  ];

  const week1Wed = weekWednesday('2026-01-12');
  const week2Wed = weekWednesday('2026-01-19');

  it('shows all selected markets with data from the same week even if on different days', () => {
    // Markets Warszawa, Kraków, Gdańsk have data in week 1 (different days)
    const selectedMarkets = new Set(['Warszawa', 'Kraków', 'Gdańsk']);

    render(SnapshotView, {
      props: { records, selectedDate: week1Wed, markets: selectedMarkets },
    });

    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(4); // header + 3

    expect(screen.getByText('Warszawa')).toBeInTheDocument();
    expect(screen.getByText('Kraków')).toBeInTheDocument();
    expect(screen.getByText('Gdańsk')).toBeInTheDocument();
    expect(screen.queryByText('Wrocław')).not.toBeInTheDocument();
  });

  it('shows selected markets with dash if they have no data in the selected week', () => {
    // Wrocław has no data in week 1
    const selectedMarkets = new Set(['Warszawa', 'Wrocław']);

    render(SnapshotView, {
      props: { records, selectedDate: week1Wed, markets: selectedMarkets },
    });

    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(3); // header + 2

    expect(screen.getByText('Warszawa')).toBeInTheDocument();
    expect(screen.getByText('Wrocław')).toBeInTheDocument();

    const wroclawRow = rows.find(r => r.textContent?.includes('Wrocław'));
    const cells = wroclawRow!.querySelectorAll('td');
    expect(cells[1].textContent).toBe('-');
  });

  it('aggregates all records within the week for each market', () => {
    const selectedMarkets = new Set(['Warszawa', 'Kraków', 'Gdańsk']);

    render(SnapshotView, {
      props: { records, selectedDate: week1Wed, markets: selectedMarkets },
    });

    // Warszawa has min=10, max=12 from one record in week 1
    // Kraków has min=8, max=11
    // Gdańsk has min=9, max=13
    // KPI range should be 8.00 – 13.00
    expect(screen.getByText('8.00 – 13.00 zł')).toBeInTheDocument();
  });

  it('slider shows all weeks regardless of market filter', () => {
    const selectedMarkets = new Set(['Warszawa']); // Only Warszawa

    const { container } = render(SnapshotView, {
      props: { records, selectedDate: week1Wed, markets: selectedMarkets },
    });

    // Slider should have range covering all weeks (2 weeks)
    const slider = container.querySelector('input[type="range"]') as HTMLInputElement;
    expect(slider).toBeInTheDocument();
    expect(Number(slider.max)).toBe(1); // 0-indexed, 2 weeks → max=1
  });

  it('shows no prices when records are empty', () => {
    render(SnapshotView, {
      props: { records: [], selectedDate: '', markets: new Set(['Warszawa']) },
    });

    expect(screen.getByText('Warszawa')).toBeInTheDocument();
    const dataCells = screen.getAllByRole('cell');
    const nonDashCells = dataCells.filter(c => c.textContent !== '-' && c.textContent !== 'Warszawa');
    expect(nonDashCells).toHaveLength(0);
  });

  it('renders the context chart with seasonal ribbons', () => {
    // Need data spanning multiple years for year-1 and year-2 ribbons
    const multiYearRecords: PriceRecord[] = [
      // Current year 2026
      makeRecord('Warszawa', '2026-01-12', 10, 12),
      makeRecord('Kraków', '2026-01-14', 8, 11),
      // Year -1: 2025 (52 weeks earlier)
      makeRecord('Warszawa', '2025-01-13', 9, 11),
      makeRecord('Kraków', '2025-01-15', 7, 10),
      // Year -2: 2024 (104 weeks earlier)
      makeRecord('Warszawa', '2024-01-15', 8, 10),
      makeRecord('Kraków', '2024-01-17', 6, 9),
    ];

    const { container } = render(SnapshotView, {
      props: {
        records: multiYearRecords,
        selectedDate: weekWednesday('2026-01-12'),
        markets: new Set(['Warszawa', 'Kraków']),
      },
    });

    // Chart should contain SVG with polygon elements (ribbons)
    const chartContainer = container.querySelector('.svg-chart-container');
    expect(chartContainer).toBeInTheDocument();
    const svg = chartContainer!.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // Should have polygon elements for the ribbons
    const polygons = svg!.querySelectorAll('polygon');
    expect(polygons.length).toBeGreaterThanOrEqual(1); // At least current year ribbon

    // Should have path elements for dashed midlines
    const paths = svg!.querySelectorAll('path');
    expect(paths.length).toBeGreaterThanOrEqual(1);
  });
});
