/**
 * src/config.js
 *
 * ONE place that decides where the backend lives. Previously three files
 * each guessed differently (window.location.host, a hardcoded
 * localhost:8000, and a bare relative path), so the catalog loaded while
 * the socket silently failed.
 *
 * VITE_API_BASE empty  -> same origin (dev proxy, or prod behind FastAPI)
 * VITE_API_BASE set    -> absolute, e.g. http://59.103.233.98:7072
 */

const RAW = (import.meta.env.VITE_API_BASE ?? '').trim().replace(/\/+$/, '');

export const API_BASE = RAW;

/** Path the FastAPI WebSocket router is mounted at. If you include the
 *  router with prefix="/api" this must become "/api/ws". */
export const WS_PATH = (import.meta.env.VITE_WS_PATH ?? '/ws').trim();

export const apiUrl = (path) =>
  `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`;

export const WS_URL = (() => {
  if (API_BASE) return `${API_BASE.replace(/^http/, 'ws')}${WS_PATH}`;
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}${WS_PATH}`;
})();

/**
 * getUserMedia is gated behind a secure context. On http:// served from an
 * IP the microphone is blocked by the browser with no useful error, so the
 * UI checks this and explains instead of failing silently.
 */
export const MIC_AVAILABLE =
  typeof navigator !== 'undefined' &&
  !!navigator.mediaDevices?.getUserMedia &&
  (window.isSecureContext || window.location.hostname === 'localhost');

/**
 * A page served over https cannot open ws:// or fetch http://. Detect the
 * mismatch up front rather than letting every request die in the console.
 */
export const MIXED_CONTENT =
  window.location.protocol === 'https:' && API_BASE.startsWith('http://');
