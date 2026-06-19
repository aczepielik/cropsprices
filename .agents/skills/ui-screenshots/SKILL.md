---
name: ui-screenshots
description: Take multi-resolution screenshots of the frontend dashboard for visual review by agents
---

# UI Screenshot Skill

Automated Playwright screenshots of the cropsprices dashboard at desktop, tablet, and mobile
resolutions. Used by agents to visually judge the UI without requiring a human to open a browser.

## Quick Start

```bash
# From the project root:
node .agents/skills/ui-screenshots/screenshot.mjs
```

Screenshots are saved to `.agents/skills/ui-screenshots/resources/screenshots/`.

## What It Captures

**Two views** × **three breakpoints** = 6 screenshots per run:

| View | Description |
|------|-------------|
| Snapshot | KPI cards, context chart placeholder, market breakdown table |
| Heatmap | Week × Year SVG grid with color scale |

| Breakpoint | Width × Height | Emulates |
|------------|---------------|----------|
| Desktop | 1440 × 900 | Laptop / large monitor |
| Tablet | 768 × 1024 | iPad portrait |
| Mobile | 375 × 812 | iPhone portrait |

## Output

```
.agents/skills/ui-screenshots/resources/screenshots/
├── snapshot-desktop-1440x900.png
├── snapshot-tablet-768x1024.png
├── snapshot-mobile-375x812.png
├── heatmap-desktop-1440x900.png
├── heatmap-tablet-768x1024.png
└── heatmap-mobile-375x812.png
```

## How It Works

1. Starts the Vite dev server in the background (`npm run dev` in `frontend/`)
2. Waits for the server to be ready (polls localhost:5173)
3. For each breakpoint:
   - Resizes the viewport
   - Navigates to the app
   - Waits for data to load (manifest fetch + arrow decode)
   - Clicks the Snapshot tab → screenshot
   - Clicks the Heatmap tab → screenshot
4. Kills the dev server
5. Prints a summary of saved files

## Prerequisites

- Node.js 18+
- Playwright with Chromium installed (`.tools/node_modules/playwright`)
- Chromium browser cached at `~/.cache/ms-playwright/chromium-*`

## Using Screenshots for Review

After running the script, agents can use the `read` tool to view the PNG files:

```
read(.agents/skills/ui-screenshots/resources/screenshots/snapshot-desktop-1440x900.png)
```

This lets agents visually inspect layout, spacing, typography, color, and responsive
behavior without human intervention.

## Manual Override

To screenshot a specific URL or add custom wait conditions, edit `screenshot.mjs`
and modify the `VIEWS` or `BREAKPOINTS` arrays at the top of the file.
