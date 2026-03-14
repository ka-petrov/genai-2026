/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** OpenStreetMap / vector tile style URL for MapLibre GL. */
  readonly VITE_MAP_STYLE_URL?: string;

  /** Google Maps JavaScript API key (Places Autocomplete on landing page). */
  readonly VITE_GOOGLE_MAPS_API_KEY?: string;

  /**
   * When set to "false", the frontend calls real backend APIs.
   * Any other value (or unset) enables built-in mock responses.
   */
  readonly VITE_USE_MOCKS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
