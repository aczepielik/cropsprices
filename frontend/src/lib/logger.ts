/**
 * Logger with debug/production levels.
 *
 * DEBUG logs are stripped in production builds by Vite's dead-code elimination
 * when `import.meta.env.MODE === 'production'`. In development, they appear
 * in the browser console with a component prefix.
 *
 * Usage:
 *   import { debug } from './logger';
 *   const log = debug('HeatmapView');
 *   log('cells computed', { count: cells.length });
 */

type LogFn = (message: string, data?: Record<string, unknown>) => void;

function noop() {}

const isDev = import.meta.env.DEV;

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

export function error(component: string): LogFn {
  return (message: string, data?: Record<string, unknown>) => {
    if (data) {
      console.error(`[${component}]`, message, data);
    } else {
      console.error(`[${component}]`, message);
    }
  };
}
