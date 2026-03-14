import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { haversineDistance, createCirclePolygon, formatDistance } from "./geo";
import type { MapInteractionState } from "../types";

const MAP_STYLE =
  (import.meta.env.VITE_MAP_STYLE_URL as string | undefined) ??
  "https://tiles.openfreemap.org/styles/liberty";

const CIRCLE_SOURCE = "radius-circle";
const CIRCLE_FILL = "radius-fill";
const CIRCLE_LINE = "radius-stroke";
const RADIUS_LABEL = "radius-label";

interface Props {
  interaction: MapInteractionState;
  onPinSet: (lat: number, lon: number) => void;
  onRadiusSet: (lat: number, lon: number, radiusM: number) => void;
  onReset: () => void;
  visible: boolean;
}

export default function MapView({
  interaction,
  onPinSet,
  onRadiusSet,
  onReset,
  visible,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const previewMarkerRef = useRef<maplibregl.Marker | null>(null);
  const previewCircleAdded = useRef(false);

  // ---- initialize map ----
  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: [13.4, 52.52],
      zoom: 13,
      attributionControl: true,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // ---- resize on visibility toggle ----
  useEffect(() => {
    if (visible) {
      setTimeout(() => mapRef.current?.resize(), 0);
    }
  }, [visible]);

  // ---- click handler ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const onClick = (e: maplibregl.MapMouseEvent) => {
      const { lat, lng: lon } = e.lngLat;
      if (interaction.step === "idle") {
        onPinSet(lat, lon);
      } else if (interaction.step === "pin_set") {
        const r = haversineDistance(interaction.lat, interaction.lon, lat, lon);
        onRadiusSet(interaction.lat, interaction.lon, Math.max(50, r));
      }
    };

    map.on("click", onClick);
    return () => {
      map.off("click", onClick);
    };
  }, [interaction, onPinSet, onRadiusSet]);

  // ---- live radius preview on mouse move ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (interaction.step !== "pin_set") {
      // clean up preview if it exists
      if (previewMarkerRef.current) {
        previewMarkerRef.current.remove();
        previewMarkerRef.current = null;
      }
      if (previewCircleAdded.current) {
        removeCircleLayers(map, "preview-circle", "preview-fill", "preview-stroke", "preview-label");
        previewCircleAdded.current = false;
      }
      return;
    }

    const onMove = (e: maplibregl.MapMouseEvent) => {
      const { lat, lng: lon } = e.lngLat;
      const r = Math.max(50, haversineDistance(interaction.lat, interaction.lon, lat, lon));
      const circle = createCirclePolygon(interaction.lat, interaction.lon, r);

      if (!previewMarkerRef.current) {
        const el = document.createElement("div");
        el.className = "radius-label-marker";
        previewMarkerRef.current = new maplibregl.Marker({ element: el })
          .setLngLat([lon, lat])
          .addTo(map);
      } else {
        previewMarkerRef.current.setLngLat([lon, lat]);
      }
      const labelEl = previewMarkerRef.current.getElement();
      labelEl.textContent = formatDistance(r);

      const src = map.getSource("preview-circle") as maplibregl.GeoJSONSource | undefined;
      if (src) {
        src.setData(circle);
      } else if (map.isStyleLoaded()) {
        map.addSource("preview-circle", { type: "geojson", data: circle });
        map.addLayer({
          id: "preview-fill",
          type: "fill",
          source: "preview-circle",
          paint: { "fill-color": "#3b82f6", "fill-opacity": 0.08 },
        });
        map.addLayer({
          id: "preview-stroke",
          type: "line",
          source: "preview-circle",
          paint: {
            "line-color": "#3b82f6",
            "line-width": 1.5,
            "line-dasharray": [4, 3],
          },
        });
        previewCircleAdded.current = true;
      }
    };

    map.on("mousemove", onMove);
    return () => {
      map.off("mousemove", onMove);
    };
  }, [interaction]);

  // ---- pin marker ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }

    if (interaction.step === "pin_set" || interaction.step === "radius_set") {
      markerRef.current = new maplibregl.Marker({ color: "#ef4444" })
        .setLngLat([interaction.lon, interaction.lat])
        .addTo(map);
    }
  }, [interaction]);

  // ---- confirmed radius circle ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const draw = () => {
      removeCircleLayers(map, CIRCLE_SOURCE, CIRCLE_FILL, CIRCLE_LINE, RADIUS_LABEL);

      if (interaction.step === "radius_set") {
        const circle = createCirclePolygon(
          interaction.lat,
          interaction.lon,
          interaction.radius_m,
        );
        map.addSource(CIRCLE_SOURCE, { type: "geojson", data: circle });
        map.addLayer({
          id: CIRCLE_FILL,
          type: "fill",
          source: CIRCLE_SOURCE,
          paint: { "fill-color": "#3b82f6", "fill-opacity": 0.15 },
        });
        map.addLayer({
          id: CIRCLE_LINE,
          type: "line",
          source: CIRCLE_SOURCE,
          paint: { "line-color": "#2563eb", "line-width": 2 },
        });
      }
    };

    if (map.isStyleLoaded()) {
      draw();
    } else {
      map.once("load", draw);
    }
  }, [interaction]);

  // ---- fly to pin on restore ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (interaction.step === "radius_set") {
      const fly = () =>
        map.flyTo({
          center: [interaction.lon, interaction.lat],
          zoom: radiusToZoom(interaction.radius_m),
          duration: 1200,
        });
      if (map.isStyleLoaded()) fly();
      else map.once("load", fly);
    }
    // only on mount-like restore, not every interaction change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const instruction =
    interaction.step === "idle"
      ? "Click on the map to drop a pin"
      : interaction.step === "pin_set"
        ? "Click again to set the search radius"
        : null;

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="absolute inset-0" />

      {instruction && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 bg-black/75 text-white px-5 py-2.5 rounded-full text-sm font-medium shadow-lg pointer-events-none select-none">
          {instruction}
        </div>
      )}

      {interaction.step === "radius_set" && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-2">
          <span className="bg-blue-600 text-white px-4 py-2 rounded-full text-sm font-semibold shadow-lg">
            {formatDistance(interaction.radius_m)} radius
          </span>
          <button
            onClick={onReset}
            className="bg-white/90 backdrop-blur text-gray-700 px-4 py-2 rounded-full text-sm font-medium shadow-lg hover:bg-white transition-colors cursor-pointer"
          >
            Reset
          </button>
        </div>
      )}
    </div>
  );
}

function removeCircleLayers(
  map: maplibregl.Map,
  source: string,
  ...layers: string[]
) {
  for (const id of layers) {
    if (map.getLayer(id)) map.removeLayer(id);
  }
  if (map.getSource(source)) map.removeSource(source);
}

function radiusToZoom(radiusM: number): number {
  // rough heuristic: show the circle with some padding
  const km = radiusM / 1000;
  if (km < 0.2) return 16;
  if (km < 0.5) return 15;
  if (km < 1) return 14;
  if (km < 2) return 13;
  if (km < 5) return 12;
  return 11;
}
