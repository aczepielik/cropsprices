import { describe, it, expect, vi, beforeEach } from 'vitest';
import { loadArrowFile, loadProductData, loadManifest, loadWeekRanges, resetForTesting } from './arrow-loader';

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

    const result = await loadProductData('Nonexistent', 'kg', 'KRAJOWE', 2026, 2025);
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

    const result = await loadProductData('Corrupt', 'kg', 'KRAJOWE', 2026, 2025);
    expect(result).toEqual([]);
  });
});

describe('cache versioning', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetForTesting();
  });

  it('loadArrowFile appends archiveVersion for archive paths', async () => {
    // First load manifest to set versions
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        years: [2025, 2026], currentYear: 2026, archiveYear: 2025,
        products: [], places: [], lastUpdate: '2026-09-01T00:00:00Z',
        archiveVersion: 'abc123def456',
      }),
    });
    await loadManifest();

    // Reset to track the arrow fetch
    mockFetch.mockReset();
    const garbage = new Uint8Array(100).fill(0x42);
    mockFetch.mockResolvedValue({
      ok: true,
      arrayBuffer: () => Promise.resolve(garbage.buffer),
    });

    await loadArrowFile('/data/archive-2025/Test-kg-KRAJOWE.arrow');

    const calledUrl = mockFetch.mock.calls[0][0];
    expect(calledUrl).toContain('?v=abc123def456');
  });

  it('loadArrowFile appends lastUpdate for current year paths', async () => {
    // Load manifest
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        years: [2026], currentYear: 2026, archiveYear: 2025,
        products: [], places: [], lastUpdate: '2026-09-04T12:00:00Z',
        archiveVersion: 'abc123def456',
      }),
    });
    await loadManifest();

    mockFetch.mockReset();
    const garbage = new Uint8Array(100).fill(0x42);
    mockFetch.mockResolvedValue({
      ok: true,
      arrayBuffer: () => Promise.resolve(garbage.buffer),
    });

    await loadArrowFile('/data/2026/Test-kg-KRAJOWE.arrow');

    const calledUrl = mockFetch.mock.calls[0][0];
    expect(calledUrl).toContain('?v=2026-09-04T12:00:00Z');
    expect(calledUrl).not.toContain('abc123def456');
  });

  it('loadArrowFile uses archiveVersion for all archive subpaths', async () => {
    // Load manifest
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        years: [2025, 2026], currentYear: 2026, archiveYear: 2025,
        products: [], places: [], lastUpdate: '2026-09-04T12:00:00Z',
        archiveVersion: 'aaa111bbb222',
      }),
    });
    await loadManifest();

    mockFetch.mockReset();
    const garbage = new Uint8Array(100).fill(0x42);
    mockFetch.mockResolvedValue({
      ok: true,
      arrayBuffer: () => Promise.resolve(garbage.buffer),
    });

    // Archive subpath (not just archive-2025)
    await loadArrowFile('/data/archive-2020/Old-kg-KRAJOWE.arrow');

    const calledUrl = mockFetch.mock.calls[0][0];
    expect(calledUrl).toContain('?v=aaa111bbb222');
    expect(calledUrl).not.toContain('2026-09-04');
  });
});
