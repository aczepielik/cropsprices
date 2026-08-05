// vite.config.ts — Vite build tool configuration
//
// WHAT IS VITE? Vite (French for "fast") is a build tool that:
// - Runs a development server with hot module replacement (HMR)
//   → When you edit a file, only that file refreshes (not the whole page)
// - Bundles your code for production (minified, optimized)
//
// WHAT IS A PLUGIN? Vite plugins extend Vite's capabilities:
// - @tailwindcss/vite: Processes Tailwind CSS utility classes
// - @sveltejs/vite-plugin-svelte: Compiles .svelte files into JavaScript

import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  base: '/cropsprices/',
  plugins: [tailwindcss(), svelte()],
  // Vite serves static files from publicDir. The ETL pipeline writes Arrow
  // files to the project root's public/data/, not frontend/public/.
  // This path is relative to vite.config.ts (i.e. relative to frontend/).
  publicDir: '../public',
  resolve: {
    conditions: ['browser'],
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.{test,spec}.{js,ts}'],
  },
})
