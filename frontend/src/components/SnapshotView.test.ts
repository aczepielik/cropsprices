import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import '@testing-library/jest-dom/vitest';
import SnapshotStats from './SnapshotStats.svelte';
import SnapshotTable from './SnapshotTable.svelte';
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

function weekWednesday(date: string): string {
  const d = new Date(date + 'T00:00:00Z');
  const date2 = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  date2.setUTCDate(date2.getUTCDate() + 4 - (date2.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(date2.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((date2.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return wednesdayOfWeek(date2.getUTCFullYear(), weekNo);
}

const records: PriceRecord[] = [
  makeRecord('Warszawa', '2026-01-12', 10, 12),
  makeRecord('Kraków', '2026-01-14', 8, 11),
  makeRecord('Gdańsk', '2026-01-16', 9, 13),
  makeRecord('Wrocław', '2026-01-20', 7, 10),
  makeRecord('Warszawa', '2026-01-19', 11, 14),
  makeRecord('Kraków', '2026-01-21', 9, 12),
];

const week1Wed = weekWednesday('2026-01-12');

describe('SnapshotTable', () => {
  it('shows all selected markets with data from the same week', () => {
    const selectedMarkets = new Set(['Warszawa', 'Kraków', 'Gdańsk']);
    render(SnapshotTable, {
      props: { records, selectedDate: week1Wed, markets: selectedMarkets },
    });
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(4);
    expect(screen.getByText('Warszawa')).toBeInTheDocument();
    expect(screen.getByText('Kraków')).toBeInTheDocument();
    expect(screen.getByText('Gdańsk')).toBeInTheDocument();
    expect(screen.queryByText('Wrocław')).not.toBeInTheDocument();
  });

  it('shows dash for markets with no data in the selected week', () => {
    const selectedMarkets = new Set(['Warszawa', 'Wrocław']);
    render(SnapshotTable, {
      props: { records, selectedDate: week1Wed, markets: selectedMarkets },
    });
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(3);
    expect(screen.getByText('Wrocław')).toBeInTheDocument();
    const wroclawRow = rows.find(r => r.textContent?.includes('Wrocław'));
    const cells = wroclawRow!.querySelectorAll('td');
    expect(cells[1].textContent).toBe('\u2013');
  });
});

describe('SnapshotStats', () => {
  it('shows KPI range for selected week', () => {
    const selectedMarkets = new Set(['Warszawa', 'Kraków', 'Gdańsk']);
    render(SnapshotStats, {
      props: { records, selectedDate: week1Wed, markets: selectedMarkets },
    });
    expect(screen.getByText('8.00 – 13.00 zł')).toBeInTheDocument();
  });

  it('shows empty state when records are empty', () => {
    render(SnapshotStats, {
      props: { records: [], selectedDate: '', markets: new Set(['Warszawa']) },
    });
    expect(screen.getByText('Dla wybranego produktu i rynków nie ma danych w archiwum. Wybierz inny produkt lub zmień filtrowanie rynków.')).toBeInTheDocument();
  });

  it('renders the context chart', () => {
    const multiYearRecords: PriceRecord[] = [];
    for (let w = 0; w < 55; w++) {
      const base = new Date(Date.UTC(2024, 5, 3));
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
    const { container } = render(SnapshotStats, {
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
    const paths = svg!.querySelectorAll('path');
    expect(paths.length).toBeGreaterThanOrEqual(1);
  });
});
