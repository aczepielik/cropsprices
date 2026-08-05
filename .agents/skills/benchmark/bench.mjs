#!/usr/bin/env node
// bench.mjs — Profile dashboard load times and product-change latency.
//
// Usage: node .agents/skills/benchmark/bench.mjs
//
// Starts a Vite dev server (or reuses an existing one), runs Playwright,
// measures per-stage timing, and prints a summary.

import { chromium } from '../../../.tools/node_modules/playwright/index.mjs';
import { spawn, execSync } from 'child_process';
import net from 'net';
import { dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const FRONTEND_DIR = join(__dirname, '..', '..', '..', 'frontend');
const DEV_PORT = 5173;

function join(...parts) { return parts.join('/'); }

function isPortInUse(port) {
  return new Promise(resolve => {
    const server = net.createServer();
    server.once('error', () => resolve(true));
    server.once('listening', () => { server.close(); resolve(false); });
    server.listen(port);
  });
}

async function waitForDevServer(url, timeoutMs = 30_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return true;
    } catch { /* not ready */ }
    await new Promise(r => setTimeout(r, 500));
  }
  throw new Error(`Dev server did not start within ${timeoutMs}ms`);
}

function startDevServer(port) {
  console.log(`Starting Vite dev server on port ${port}...`);
  const child = spawn('npm', ['run', 'dev', '--', '--port', String(port)], {
    cwd: FRONTEND_DIR,
    stdio: 'pipe',
    shell: true,
  });
  child.stdout?.on('data', d => process.stdout.write(d));
  child.stderr?.on('data', d => process.stderr.write(d));
  return child;
}

async function main() {
  let server = null;
  let serverUrl = null;

  try {
    let port = DEV_PORT;
    if (await isPortInUse(port)) {
      try { execSync(`lsof -ti :${port} | xargs kill -9 2>/dev/null`, { stdio: 'ignore' }); } catch {}
      await new Promise(r => setTimeout(r, 1000));
    }
    server = startDevServer(port);
    serverUrl = `http://localhost:${port}`;
    await waitForDevServer(serverUrl);
    console.log(`Server ready at ${serverUrl}\n`);

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    // Throttle CPU to 4x slowdown (simulates mid-range mobile like Pixel 7)
    const cdp = await context.newCDPSession(page);
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });

    // ── Phase 1: Initial Load ──
    console.log('=== Initial Load ===');
    const t0 = Date.now();
    await page.goto(serverUrl, { waitUntil: 'networkidle' });
    console.log('networkidle: ' + (Date.now() - t0) + ' ms');

    try {
      await page.waitForFunction(() => {
        const k = document.querySelector('.stat-value');
        return k && k.textContent.includes('zł') && !k.textContent.startsWith('-');
      }, { timeout: 10000 });
      console.log('KPI data ready: ' + (Date.now() - t0) + ' ms');
    } catch {
      console.log('KPI TIMEOUT (no data for default product/markets)');
    }

    const initResources = await page.evaluate(() =>
      performance.getEntriesByType('resource')
        .filter(e => e.name.includes('.arrow') || e.name.includes('manifest'))
        .map(e => ({
          name: decodeURIComponent(e.name.split('/').pop()),
          duration: Math.round(e.duration),
          size: e.transferSize,
        }))
    );
    console.log('Resources:');
    for (const r of initResources) {
      console.log(`  ${r.name}: ${r.duration} ms (${(r.size / 1024).toFixed(1)} KB)`);
    }

    // ── Phase 2: Product Change ──
    console.log('\n=== Product Change ===');
    const productSelect = await page.$('.filter-group:nth-child(3) select');
    if (productSelect) {
      const options = await productSelect.$$eval('option', opts =>
        opts.map((o, i) => `${i}: ${o.textContent.trim()}`).slice(0, 8)
      );
      console.log('Options (first 8): ' + options.join(', '));

      // Reset performance entries
      await page.evaluate(() => performance.clearResourceTimings());

      const t1 = Date.now();
      await productSelect.selectOption({ index: 3 });
      console.log('selectOption: ' + (Date.now() - t1) + ' ms');

      let resolved = false;
      for (let i = 0; i < 50; i++) {
        await page.waitForTimeout(200);
        const snap = await page.evaluate(() => {
          const kpis = [...document.querySelectorAll('.stat-value')].map(e => e.textContent);
          const hasBanner = !!document.querySelector('.empty-banner');
          return { kpis, hasBanner };
        });
        const elapsed = Date.now() - t1;
        if (snap.kpis[0]?.includes('zł') && !snap.kpis[0]?.startsWith('-')) {
          console.log(`T+${elapsed}ms: KPI=${snap.kpis[0]}`);
          console.log(`=== RESOLVED in ${elapsed} ms ===`);
          resolved = true;
          break;
        }
        if (elapsed > 10000) {
          console.log(`TIMEOUT after 10s. Final: ${JSON.stringify(snap)}`);
          break;
        }
      }

      const changeResources = await page.evaluate(() =>
        performance.getEntriesByType('resource')
          .filter(e => e.name.includes('.arrow'))
          .map(e => ({
            name: decodeURIComponent(e.name.split('/').pop()),
            duration: Math.round(e.duration),
            size: e.transferSize,
          }))
      );
      console.log('Arrow fetches:');
      for (const r of changeResources) {
        console.log(`  ${r.name}: ${r.duration} ms (${(r.size / 1024).toFixed(1)} KB)`);
      }
    }

    // ── Phase 3: Week navigation latency ──
    console.log('\n=== Week Navigation Latency ===');
    // Navigate to a mid-range week so both prev/next buttons are enabled
    const selectEl = await page.$('.date-select');
    if (selectEl) {
      const optCount = await selectEl.evaluate(el => el.options.length);
      if (optCount > 2) {
        const midIdx = Math.floor(optCount / 2);
        await selectEl.selectOption({ index: midIdx });
        await page.waitForTimeout(200);
      }
    }

    const nextBtn = await page.$('.date-nav-next:not([disabled])');
    const prevBtn = await page.$('.date-nav-prev:not([disabled])');
    const navBtn = nextBtn || prevBtn;

    if (navBtn) {
      await page.evaluate(() => performance.clearMarks());

      const navTimes = [];
      for (let i = 0; i < 20; i++) {
        await navBtn.click();
        await page.waitForTimeout(50);
        const duration = await page.evaluate(() => {
          const entries = performance.getEntriesByName("nav-update");
          return entries.length > 0 ? entries[entries.length - 1].duration : null;
        });
        if (duration !== null) navTimes.push(Math.round(duration));
      }
      const sorted = [...navTimes].sort((a, b) => a - b);
      const median = sorted[Math.floor(sorted.length / 2)] || 0;
      const p95 = sorted[Math.floor(sorted.length * 0.95)] || 0;
      const max = sorted.length > 0 ? sorted[sorted.length - 1] : 0;
      console.log(`Nav clicks (20 runs): ${navTimes.join(', ')} ms`);
      console.log(`Median: ${median} ms, P95: ${p95} ms, Max: ${max} ms`);
    } else {
      console.log('No enabled nav button found — skipping');
    }

    // ── Phase 4: JS-only benchmarks (no network) ──
    console.log('\n=== JS Derived Cascade (in-browser) ===');
    const jsTimings = await page.evaluate(() => {
      const results = {};

      const svgContainer = document.querySelector('.svg-chart-container');
      if (svgContainer) {
        const t0 = performance.now();
        svgContainer.getBoundingClientRect();
        results.layoutRecalc = Math.round(performance.now() - t0);
      }

      const svgEl = document.querySelector('.svg-chart-container svg');
      if (svgEl) {
        results.svgElementCount = svgEl.querySelectorAll('*').length;
        results.svgPathCount = svgEl.querySelectorAll('path').length;
        results.svgTextCount = svgEl.querySelectorAll('text').length;
        results.svgLineCount = svgEl.querySelectorAll('line').length;
      }

      return results;
    });
    console.log(`Layout recalc: ${jsTimings.layoutRecalc} ms`);
    console.log(`SVG elements: ${jsTimings.svgElementCount || 0} (paths: ${jsTimings.svgPathCount || 0}, texts: ${jsTimings.svgTextCount || 0}, lines: ${jsTimings.svgLineCount || 0})`);

    await browser.close();
    console.log('\nDone.');
  } finally {
    if (server) server.kill('SIGTERM');
  }
}

main().catch(err => {
  console.error('Benchmark failed:', err);
  process.exit(1);
});
