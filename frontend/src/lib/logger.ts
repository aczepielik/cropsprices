/**
 * Logger with debug/production levels.
 *
 * WHAT IS A LOGGER? A helper that prints messages to the browser console.
 * Unlike console.log(), this logger:
 * - Adds component prefixes (e.g., "[App] start")
 * - Strips debug logs in production builds (smaller bundle)
 * - Provides both debug and error levels
 *
 * HOW IT WORKS:
 * - debug() returns a function that logs to console.log() in dev mode
 * - In production, debug() returns a "noop" (no-operation) function
 * - Vite's tree-shaking removes the entire debug() code path in production
 *   because the `if (!isDev) return noop` makes it dead code
 *
 * WHY USE THIS INSTEAD OF console.log() DIRECTLY?
 * 1. Production builds don't include debug logs (smaller, faster)
 * 2. Component prefixes make logs easier to trace (e.g., "[HeatmapView] cells computed")
 * 3. Consistent logging format across the app
 *
 * Usage:
 *   import { debug } from './logger';
 *   const log = debug('HeatmapView');
 *   log('cells computed', { count: cells.length });
 */

// A log function takes a message string and optional data object
type LogFn = (message: string, data?: Record<string, unknown>) => void;

// "noop" = no-operation function — does nothing, returns nothing
// Used in production mode to silently discard debug logs
function noop() {}

// Check if we're in development mode (Vite sets this automatically)
// In production, this is false and debug() returns noop
const isDev = import.meta.env.DEV;

/**
 * Create a debug logger for a component.
 *
 * In development: logs to console.log() with component prefix.
 * In production: returns a silent no-op function (tree-shaken away).
 *
 * @param component - Name of the component (used in log prefix)
 * @returns A log function that accepts a message and optional data
 */
export function debug(component: string): LogFn {
  if (!isDev) return noop;
  return (message: string, data?: Record<string, unknown>) => {
    if (data) {
      console.log(`[${component}]`, message, data);
    } else {
      console.log(`[${component}]`, message);
    }
  };
}

/**
 * Create an error logger for a component.
 *
 * Always logs (both dev and production) — errors should never be silent.
 * Uses console.error() for better stack traces in dev tools.
 *
 * @param component - Name of the component (used in log prefix)
 * @returns A log function that accepts a message and optional data
 */
export function error(component: string): LogFn {
  return (message: string, data?: Record<string, unknown>) => {
    if (data) {
      console.error(`[${component}]`, message, data);
    } else {
      console.error(`[${component}]`, message);
    }
  };
}
