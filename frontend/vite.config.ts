import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
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
