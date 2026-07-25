import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import '@testing-library/jest-dom/vitest';
import HeatmapView from './HeatmapView.svelte';
import type { PriceRecord } from '../lib/types';

class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', MockResizeObserver);

afterEach(() => cleanup());

function makeRecord(place: string, product: string, date: string, min: number, max: number): PriceRecord {
  return {
    date: new Date(date + 'T00:00:00Z'),
    product,
    place,
    origin: 'KRAJOWE',
    price_min: min,
    price_max: max,
  };
}

const defaultMarkets = new Set(['Bronisze', 'Kalisz', 'Poznań', 'Łódź']);

describe('HeatmapView empty state', () => {
  it('shows empty state when records exist but none match selected markets', () => {
    const gruszkiRecords: PriceRecord[] = [
      makeRecord('Bronisze', 'Gruszki', '2026-01-12', 4, 6),
      makeRecord('Kalisz', 'Gruszki', '2026-01-14', 5, 7),
      makeRecord('Bronisze', 'Gruszki', '2026-01-19', 4.5, 6.5),
      makeRecord('Kalisz', 'Gruszki', '2026-01-21', 5.5, 7.5),
    ];
    render(HeatmapView, {
      props: { records: gruszkiRecords, markets: defaultMarkets },
    });
    expect(document.querySelector('.empty-state')).not.toBeInTheDocument();
    expect(document.querySelector('.heatmap-scroll')).toBeInTheDocument();
  });

  it('shows empty state when no data matches selected markets', () => {
    const brzoskwinieRecords: PriceRecord[] = [
      makeRecord('Białystok', 'Brzoskwinie', '2026-01-12', 8, 10),
      makeRecord('Gdańsk', 'Brzoskwinie', '2026-01-14', 9, 11),
      makeRecord('Białystok', 'Brzoskwinie', '2026-01-19', 8.5, 10.5),
    ];
    render(HeatmapView, {
      props: { records: brzoskwinieRecords, markets: defaultMarkets },
    });
    expect(document.querySelector('.empty-state')).toBeInTheDocument();
    expect(document.querySelector('.heatmap-scroll')).not.toBeInTheDocument();
  });

  it('shows data when product has data for selected markets', () => {
    const malinyRecords: PriceRecord[] = [
      makeRecord('Bronisze', 'Maliny', '2026-06-01', 20, 30),
      makeRecord('Poznań', 'Maliny', '2026-06-03', 22, 28),
      makeRecord('Bronisze', 'Maliny', '2026-06-08', 21, 29),
      makeRecord('Poznań', 'Maliny', '2026-06-10', 23, 27),
    ];
    render(HeatmapView, {
      props: { records: malinyRecords, markets: defaultMarkets },
    });
    expect(document.querySelector('.empty-state')).not.toBeInTheDocument();
    expect(document.querySelector('.heatmap-scroll')).toBeInTheDocument();
  });

  it('shows empty state when records array is empty', () => {
    render(HeatmapView, {
      props: { records: [], markets: defaultMarkets },
    });
    expect(document.querySelector('.empty-state')).toBeInTheDocument();
  });

  it('re-renders correctly when props change', async () => {
    const gruszkiRecords: PriceRecord[] = [
      makeRecord('Bronisze', 'Gruszki', '2026-01-12', 4, 6),
      makeRecord('Kalisz', 'Gruszki', '2026-01-14', 5, 7),
    ];
    const { rerender } = render(HeatmapView, {
      props: { records: gruszkiRecords, markets: defaultMarkets },
    });
    expect(document.querySelector('.heatmap-scroll')).toBeInTheDocument();

    const brzoskwinieRecords: PriceRecord[] = [
      makeRecord('Białystok', 'Brzoskwinie', '2026-01-12', 8, 10),
      makeRecord('Gdańsk', 'Brzoskwinie', '2026-01-14', 9, 11),
    ];
    await rerender({ records: brzoskwinieRecords, markets: defaultMarkets });
    expect(document.querySelector('.empty-state')).toBeInTheDocument();
    expect(document.querySelector('.heatmap-scroll')).not.toBeInTheDocument();
  });
});
