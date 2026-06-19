#!/usr/bin/env node
// screenshot.mjs — Automated multi-resolution screenshots of the cropsprices dashboard.
//
// WHY this exists: Agents can't open a browser to visually inspect the UI.
// This script starts the dev server, takes screenshots at 3 breakpoints × 2 views,
// and saves them as PNGs that agents can read with the `read` tool.
//
// Usage: node .agents/skills/ui-screenshots/screenshot.mjs

import { chromium } from '../../../.tools/node_modules/playwright/index.mjs';
import { spawn, execSync } from 'child_process';
import { existsSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import net from 'net';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = join(__dirname, 'resources', 'screenshots');
const FRONTEND_DIR = join(__dirname, '..', '..', '..', 'frontend');
const DEV_PORT = 5173;

const BREAKPOINTS = [
  { name: 'desktop',       width: 1440, height: 900 },
  { name: 'tablet-v',      width: 768,  height: 1024 },
  { name: 'tablet-h',      width: 1024, height: 768 },
  { name: 'mobile',        width: 375,  height: 812 },
];

const VIEWS = [
  { name: 'snapshot', tabLabel: 'Widok Aktualny' },
  { name: 'heatmap',  tabLabel: 'Mapa Cieplna' },
];

/**
 * Check if a port is already in use.
 */
function isPortInUse(port) {
  return new Promise(resolve => {
    const server = net.createServer();
    server.once('error', () => resolve(true));
    server.once('listening', () => { server.close(); resolve(false); });
    server.listen(port);
  });
}

/**
 * Find an available port starting from the preferred port.
 */
async function findAvailablePort(preferred) {
  if (!(await isPortInUse(preferred))) return preferred;
  // Kill whatever is on the preferred port
  try {
    execSync(`lsof -ti :${preferred} | xargs kill -9 2>/dev/null`, { stdio: 'ignore' });
    await new Promise(r => setTimeout(r, 500));
  } catch { /* process may have already exited */ }
  return preferred;
}

/**
 * Wait for the Vite dev server to be ready.
 */
async function waitForDevServer(url, timeoutMs = 30_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return true;
    } catch { /* not ready */ }
    await new Promise(r => setTimeout(r, 500));
  }
  throw new Error(`Dev server did not start within ${timeoutMs}ms at ${url}`);
}

/**
 * Start the Vite dev server as a background process.
 */
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

async function takeScreenshot(page, filePath) {
  await page.screenshot({ path: filePath, fullPage: true });
  console.log(`  ✓ ${filePath}`);
}

/**
 * Wait for the dashboard to be interactive.
 * Checks for either the layout (data loaded) or the loading/error text.
 */
async function waitForApp(page) {
  try {
    await page.waitForSelector('.layout-container, p', { timeout: 15_000 });
  } catch {
    // Timeout — take screenshot anyway to see what state the page is in
  }
  await page.waitForTimeout(3_000);
}

async function main() {
  if (!existsSync(SCREENSHOT_DIR)) {
    mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }

  let server = null;
  let serverUrl = null;

  try {
    const port = await findAvailablePort(DEV_PORT);
    server = startDevServer(port);
    serverUrl = `http://localhost:${port}`;
    await waitForDevServer(serverUrl);
    console.log(`Dev server ready at ${serverUrl}.\n`);

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto(serverUrl, { waitUntil: 'networkidle' });
    await waitForApp(page);

    for (const bp of BREAKPOINTS) {
      console.log(`[${bp.name}] ${bp.width}×${bp.height}`);
      await page.setViewportSize({ width: bp.width, height: bp.height });
      await page.waitForTimeout(500);

      const hamburger = page.locator('.hamburger');
      const isMobile = await hamburger.isVisible();

      // Reset to snapshot view at the start of each breakpoint
      // to avoid stale view state from a previous breakpoint
      const snapshotTab = page.locator('button', { hasText: 'Widok Aktualny' });
      if (isMobile) {
        if (await snapshotTab.isVisible()) {
          await snapshotTab.click({ force: true });
        } else {
          await hamburger.click();
          await page.waitForTimeout(300);
          await snapshotTab.click({ force: true });
        }
      } else {
        if (await snapshotTab.isVisible()) {
          await snapshotTab.click();
        }
      }
      await page.waitForTimeout(500);

      for (let vi = 0; vi < VIEWS.length; vi++) {
        const view = VIEWS[vi];

        if (isMobile) {
          if (vi > 0) {
            // Open sidebar drawer to switch view
            await hamburger.click();
            await page.waitForTimeout(300);
          }
          const tab = page.locator('button', { hasText: view.tabLabel });
          if (vi > 0 && await tab.isVisible()) {
            await tab.click({ force: true });
            await page.waitForTimeout(500);
          }
        } else {
          const tab = page.locator('button', { hasText: view.tabLabel });
          if (await tab.isVisible()) {
            await tab.click();
            await page.waitForTimeout(500);
          }
        }

        const fileName = `${view.name}-${bp.name}-${bp.width}x${bp.height}.png`;
        await takeScreenshot(page, join(SCREENSHOT_DIR, fileName));
      }
      console.log('');
    }

    await browser.close();
    console.log(`Done! Screenshots saved to:\n${SCREENSHOT_DIR}`);
  } finally {
    if (server) server.kill('SIGTERM');
  }
}

main().catch(err => {
  console.error('Screenshot script failed:', err);
  process.exit(1);
});
