import { describe, it, expect, vi, beforeEach } from 'vitest';
import { loadArrowFile, loadProductData, loadManifest } from './arrow-loader';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('loadArrowFile', () => {
  it('returns empty array for 404 responses', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 404 });

    const result = await loadArrowFile('/data/archive/Nonexistent-kg-KRAJOWE.arrow');
    expect(result).toEqual([]);
  });

  it('returns empty array for corrupt Arrow data', async () => {
    // Return HTML (like a SPA fallback) instead of Arrow data
    const html = '<html><body>Not found</body></html>';
    const buffer = new TextEncoder().encode(html).buffer;
    mockFetch.mockResolvedValue({
      ok: true,
      arrayBuffer: () => Promise.resolve(buffer),
    });

    const result = await loadArrowFile('/data/archive/Corrupt-kg-KRAJOWE.arrow');
    expect(result).toEqual([]);
  });

  it('returns empty array for truncated Arrow data', async () => {
    // 751 bytes of garbage — similar to the Brzoskwinie bug
    const garbage = new Uint8Array(751).fill(0x42);
    mockFetch.mockResolvedValue({
      ok: true,
      arrayBuffer: () => Promise.resolve(garbage.buffer),
    });

    const result = await loadArrowFile('/data/archive/Truncated-kg-KRAJOWE.arrow');
    expect(result).toEqual([]);
  });
});

describe('loadProductData', () => {
  it('returns empty array when both archive and current are missing', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 404 });

    const result = await loadProductData('Nonexistent', 'kg', 'KRAJOWE', 2026);
    expect(result).toEqual([]);
  });

  it('returns empty array when archive is corrupt', async () => {
    let callCount = 0;
    mockFetch.mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        // Archive: corrupt
        const garbage = new Uint8Array(100).fill(0x42);
        return Promise.resolve({
          ok: true,
          arrayBuffer: () => Promise.resolve(garbage.buffer),
        });
      }
      // Current: 404
      return Promise.resolve({ ok: false, status: 404 });
    });

    const result = await loadProductData('Corrupt', 'kg', 'KRAJOWE', 2026);
    expect(result).toEqual([]);
  });
});
