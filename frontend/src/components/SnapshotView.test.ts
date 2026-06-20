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
    expect(cells[1].textContent).toBe('\u2013');
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

    // Slider should have range covering all weeks from ALL records
    // (allWeeks operates on unfiltered records, not market-filtered)
    const slider = container.querySelector('input[type="range"]') as HTMLInputElement;
    expect(slider).toBeInTheDocument();
    expect(Number(slider.max)).toBeGreaterThanOrEqual(1);
  });

  it('shows empty dashboard when records are empty', () => {
    render(SnapshotView, {
      props: { records: [], selectedDate: '', markets: new Set(['Warszawa']) },
    });

    // Empty records → empty dashboard, no table
    expect(screen.getByText('Brak danych')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('renders the context chart with seasonal ribbons', () => {
    // Generate 52+ weeks of data across 3 years so the context chart's
    // year-1 (-52 index) and year-2 (-104 index) lookups work.
    const multiYearRecords: PriceRecord[] = [];
    for (let w = 0; w < 55; w++) {
      const base = new Date(Date.UTC(2024, 5, 3)); // Jun 3 2024 (Mon)
      const d2024 = new Date(base.getTime());
      d2024.setUTCDate(d2024.getUTCDate() + w * 7);
      const d2025 = new Date(d2024.getTime());
      d2025.setUTCFullYear(d2025.getUTCFullYear() + 1);
      const d2026 = new Date(d2024.getTime());
      d2026.setUTCFullYear(d2026.getUTCFullYear() + 2);

      const fmt = (d: Date) => `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}-${String(d.getUTCDate()).padStart(2,'0')}`;
      const price = 8 + (w % 10) * 0.5;
      multiYearRecords.push(makeRecord('Warszawa', fmt(d2024), price - 2, price));
      multiYearRecords.push(makeRecord('Warszawa', fmt(d2025), price - 1, price + 1));
      multiYearRecords.push(makeRecord('Kraków', fmt(d2025), price - 1, price + 1));
      multiYearRecords.push(makeRecord('Warszawa', fmt(d2026), price, price + 2));
      multiYearRecords.push(makeRecord('Kraków', fmt(d2026), price, price + 2));
    }

    const { container } = render(SnapshotView, {
      props: {
        records: multiYearRecords,
        selectedDate: weekWednesday('2026-06-15'),
        markets: new Set(['Warszawa', 'Kraków']),
      },
    });

    const chartContainer = container.querySelector('.svg-chart-container');
    expect(chartContainer).toBeInTheDocument();
    const svg = chartContainer!.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // At least current year path (mean line or band)
    const paths = svg!.querySelectorAll('path');
    expect(paths.length).toBeGreaterThanOrEqual(1);
  });
});
