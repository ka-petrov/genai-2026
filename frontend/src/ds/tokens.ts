/**
 * Design-system colour palette.
 *
 * Every colour used across the app is defined here. To iterate on the theme,
 * edit these values — they are injected as CSS custom properties at the root
 * and consumed via Tailwind utilities (e.g. `bg-surface-base`, `text-fg`,
 * `border-panel`).
 */

export const palette = {
  // ── Backgrounds / surfaces ────────────────────────────────────────────
  "surface-base": "#0a0e1a",
  "surface-raised": "#111827",
  "surface-overlay": "#1a1d25",
  "surface-sunken": "#2a2d35",

  // ── Borders ───────────────────────────────────────────────────────────
  "border-default": "#1e2433",
  "border-subtle": "#2a2d35",
  "border-strong": "#3a3d45",

  // ── Foreground / text ─────────────────────────────────────────────────
  fg: "#ffffff",
  "fg-secondary": "#d1d5db",
  "fg-muted": "#9ca3af",
  "fg-faint": "#6b7280",

  // ── Accent (primary interactive colour) ───────────────────────────────
  accent: "#2563eb",
  "accent-hover": "#3b82f6",
  "accent-subtle": "rgba(37, 99, 235, 0.10)",
  "accent-text": "#60a5fa",

  // ── Accent gradient endpoints (hero heading, etc.) ────────────────────
  "gradient-from": "#60a5fa",
  "gradient-to": "#22d3ee",

  // ── Chat bubbles ──────────────────────────────────────────────────────
  "bubble-user": "#2563eb",
  "bubble-user-text": "#ffffff",
  "bubble-assistant": "#1e2433",
  "bubble-assistant-text": "#e5e7eb",

  // ── Status ────────────────────────────────────────────────────────────
  "status-success": "#22c55e",
  "status-success-subtle": "rgba(34, 197, 94, 0.10)",
  "status-error": "#ef4444",
  "status-error-subtle": "rgba(239, 68, 68, 0.10)",
  "status-error-text": "#fca5a5",

  // ── Map-specific ──────────────────────────────────────────────────────
  "map-pin": "#ef4444",
  "map-circle-fill": "#3b82f6",
  "map-circle-stroke": "#2563eb",
} as const;

export type TokenName = keyof typeof palette;
