# Frontend

Svelte + TypeScript dashboard for crop prices.

## Prerequisites

- Node.js 18+

## Setup

```bash
cd frontend
npm install
```

## Local development

```bash
npm run dev
```

Opens at `http://localhost:5173`.

The dev server reads Arrow files from `public/data/`. That data is already generated — no backend server needed.

### Updating the data (optional)

If you need to refresh the data from the source API, run the Python ETL pipeline:

```bash
# From project root
cd ..
pip install -e .
bulk-get-resources
bulk-process-resources
build-arrow-db
```

This re-fetches Excel bulletins and rebuilds the Arrow files in `public/data/`. Only needed if the upstream data has changed.

## Build

```bash
npm run build
```

Output goes to `dist/`.

## Type check

```bash
npm run check
```
