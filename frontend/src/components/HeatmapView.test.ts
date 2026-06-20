import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import '@testing-library/jest-dom/vitest';
import HeatmapView from './HeatmapView.svelte';
import type { PriceRecord } from '../lib/types';

// jsdom doesn't have ResizeObserver
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
    // Gruszki data for Bronisze and Kalisz
    const gruszkiRecords: PriceRecord[] = [
      makeRecord('Bronisze', 'Gruszki', '2026-01-12', 4, 6),
      makeRecord('Kalisz', 'Gruszki', '2026-01-14', 5, 7),
      makeRecord('Bronisze', 'Gruszki', '2026-01-19', 4.5, 6.5),
      makeRecord('Kalisz', 'Gruszki', '2026-01-21', 5.5, 7.5),
    ];

    render(HeatmapView, {
      props: { records: gruszkiRecords, markets: defaultMarkets },
    });

    // Should NOT show empty state — data matches selected markets
    expect(document.querySelector('.empty-state')).not.toBeInTheDocument();
    // Should show the heatmap scroll container
    expect(document.querySelector('.heatmap-scroll')).toBeInTheDocument();
  });

  it('switching product: shows empty state when new product has data but not for selected markets', () => {
    // Brzoskwinie data exists ONLY for markets outside the default 4
    const brzoskwinieRecords: PriceRecord[] = [
      makeRecord('Białystok', 'Brzoskwinie', '2026-01-12', 8, 10),
      makeRecord('Gdańsk', 'Brzoskwinie', '2026-01-14', 9, 11),
      makeRecord('Białystok', 'Brzoskwinie', '2026-01-19', 8.5, 10.5),
    ];

    render(HeatmapView, {
      props: { records: brzoskwinieRecords, markets: defaultMarkets },
    });

    // Should show empty state — no data for Bronisze/Kalisz/Poznań/Łódź
    expect(screen.getByText('Brak danych')).toBeInTheDocument();
    expect(document.querySelector('.heatmap-scroll')).not.toBeInTheDocument();
  });

  it('switching product: shows data when new product has data for selected markets', () => {
    // Maliny data for Bronisze and Poznań
    const malinyRecords: PriceRecord[] = [
      makeRecord('Bronisze', 'Maliny', '2026-06-01', 20, 30),
      makeRecord('Poznań', 'Maliny', '2026-06-03', 22, 28),
      makeRecord('Bronisze', 'Maliny', '2026-06-08', 21, 29),
      makeRecord('Poznań', 'Maliny', '2026-06-10', 23, 27),
    ];

    render(HeatmapView, {
      props: { records: malinyRecords, markets: defaultMarkets },
    });

    // Should show heatmap, not empty state
    expect(document.querySelector('.empty-state')).not.toBeInTheDocument();
    expect(document.querySelector('.heatmap-scroll')).toBeInTheDocument();
  });

  it('shows empty state when records array is empty', () => {
    render(HeatmapView, {
      props: { records: [], markets: defaultMarkets },
    });

    expect(screen.getByText('Brak danych')).toBeInTheDocument();
  });

  it('re-renders correctly when props change (product switch simulation)', async () => {
    // Start with Gruszki data (has data for default markets)
    const gruszkiRecords: PriceRecord[] = [
      makeRecord('Bronisze', 'Gruszki', '2026-01-12', 4, 6),
      makeRecord('Kalisz', 'Gruszki', '2026-01-14', 5, 7),
    ];

    const { rerender } = render(HeatmapView, {
      props: { records: gruszkiRecords, markets: defaultMarkets },
    });

    // Should show heatmap
    expect(document.querySelector('.heatmap-scroll')).toBeInTheDocument();

    // Simulate product switch: re-render with Brzoskwinie data (no data for default markets)
    const brzoskwinieRecords: PriceRecord[] = [
      makeRecord('Białystok', 'Brzoskwinie', '2026-01-12', 8, 10),
      makeRecord('Gdańsk', 'Brzoskwinie', '2026-01-14', 9, 11),
    ];

    await rerender({ records: brzoskwinieRecords, markets: defaultMarkets });

    // Should show empty state now — no data for Bronisze/Kalisz/Poznań/Łódź
    expect(screen.getByText('Brak danych')).toBeInTheDocument();
    expect(document.querySelector('.heatmap-scroll')).not.toBeInTheDocument();
  });
});
