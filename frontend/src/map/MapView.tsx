import { useEffect, useRef, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { haversineDistance, createCirclePoints, formatDistance } from "./geo";
import type { MapInteractionState } from "../types";

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

const MAP_STYLE =
  (import.meta.env.VITE_MAP_STYLE_URL as string | undefined) ??
  "https://tiles.openfreemap.org/styles/liberty";

interface Props {
  interaction: MapInteractionState;
  onPinSet: (lat: number, lon: number) => void;
  onRadiusSet: (lat: number, lon: number, radiusM: number) => void;
  onReset: () => void;
  visible: boolean;
  flyToOnMount?: { lat: number; lon: number };
}

export default function MapView({
  interaction,
  onPinSet,
  onRadiusSet,
  onReset,
  visible,
  flyToOnMount,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasOverlayRef = useRef<HTMLCanvasElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const previewMarkerRef = useRef<maplibregl.Marker | null>(null);

  const previewCircleRef = useRef<{
    lat: number;
    lon: number;
    radiusM: number;
  } | null>(null);

  const drawCircleOnCanvas = useCallback(
    (
      circle: { lat: number; lon: number; radiusM: number },
      style: { fill: string; fillOpacity: number; stroke: string; strokeWidth: number; dash?: number[] },
    ) => {
      const map = mapRef.current;
      const canvas = canvasOverlayRef.current;
      if (!map || !canvas) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);

      ctx.clearRect(0, 0, rect.width, rect.height);

      const points = createCirclePoints(circle.lat, circle.lon, circle.radiusM);
      const projected = points.map((p) => map.project([p[0], p[1]]));

      if (projected.length < 2) return;

      ctx.beginPath();
      ctx.moveTo(projected[0]!.x, projected[0]!.y);
      for (let i = 1; i < projected.length; i++) {
        ctx.lineTo(projected[i]!.x, projected[i]!.y);
      }
      ctx.closePath();

      ctx.fillStyle = style.fill;
      ctx.globalAlpha = style.fillOpacity;
      ctx.fill();

      ctx.globalAlpha = 1;
      ctx.strokeStyle = style.stroke;
      ctx.lineWidth = style.strokeWidth;
      if (style.dash) {
        ctx.setLineDash(style.dash);
      } else {
        ctx.setLineDash([]);
      }
      ctx.stroke();
    },
    [],
  );

  const redrawOverlay = useCallback(() => {
    const canvas = canvasOverlayRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, rect.width, rect.height);

    const circleFill = cssVar("--color-map-circle-fill") || "#3b82f6";
    const circleStroke = cssVar("--color-map-circle-stroke") || "#2563eb";

    if (interaction.step === "radius_set") {
      drawCircleOnCanvas(
        { lat: interaction.lat, lon: interaction.lon, radiusM: interaction.radius_m },
        { fill: circleFill, fillOpacity: 0.15, stroke: circleStroke, strokeWidth: 2 },
      );
    }

    if (previewCircleRef.current && interaction.step === "pin_set") {
      drawCircleOnCanvas(previewCircleRef.current, {
        fill: circleFill,
        fillOpacity: 0.1,
        stroke: circleFill,
        strokeWidth: 1.5,
        dash: [6, 4],
      });
    }
  }, [interaction, drawCircleOnCanvas]);

  // ---- initialize map ----
  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: [-79.3957, 43.6629],
      zoom: 15,
      attributionControl: false,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // ---- redraw overlay on map move/zoom ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const handler = () => redrawOverlay();
    map.on("move", handler);
    map.on("zoom", handler);
    map.on("resize", handler);
    return () => {
      map.off("move", handler);
      map.off("zoom", handler);
      map.off("resize", handler);
    };
  }, [redrawOverlay]);

  // ---- resize on visibility toggle ----
  useEffect(() => {
    if (visible) {
      setTimeout(() => {
        mapRef.current?.resize();
        redrawOverlay();
      }, 0);
    }
  }, [visible, redrawOverlay]);

  // ---- cursor style ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const canvas = map.getCanvas();
    if (interaction.step === "idle" || interaction.step === "pin_set") {
      canvas.style.cursor = "crosshair";
    } else {
      canvas.style.cursor = "";
    }
  }, [interaction.step]);

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
      if (previewMarkerRef.current) {
        previewMarkerRef.current.remove();
        previewMarkerRef.current = null;
      }
      previewCircleRef.current = null;
      redrawOverlay();
      return;
    }

    const onMove = (e: maplibregl.MapMouseEvent) => {
      const { lat, lng: lon } = e.lngLat;
      const r = Math.max(50, haversineDistance(interaction.lat, interaction.lon, lat, lon));

      if (!previewMarkerRef.current) {
        const el = document.createElement("div");
        el.className = "radius-label-marker";
        previewMarkerRef.current = new maplibregl.Marker({ element: el })
          .setLngLat([lon, lat])
          .addTo(map);
      } else {
        previewMarkerRef.current.setLngLat([lon, lat]);
      }
      previewMarkerRef.current.getElement().textContent = formatDistance(r);

      previewCircleRef.current = { lat: interaction.lat, lon: interaction.lon, radiusM: r };
      redrawOverlay();
    };

    map.on("mousemove", onMove);
    return () => {
      map.off("mousemove", onMove);
    };
  }, [interaction, redrawOverlay]);

  // ---- pin marker ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }

    if (interaction.step === "pin_set" || interaction.step === "radius_set") {
      const pinColor = cssVar("--color-map-pin") || "#ef4444";
      markerRef.current = new maplibregl.Marker({ color: pinColor })
        .setLngLat([interaction.lon, interaction.lat])
        .addTo(map);
    }
  }, [interaction]);

  // ---- draw confirmed circle ----
  useEffect(() => {
    redrawOverlay();
  }, [interaction, redrawOverlay]);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- fly to landing-page geocoded location ----
  useEffect(() => {
    if (!flyToOnMount) return;
    const map = mapRef.current;
    if (!map) return;
    const fly = () =>
      map.flyTo({
        center: [flyToOnMount.lon, flyToOnMount.lat],
        zoom: 15,
        duration: 1200,
      });
    if (map.isStyleLoaded()) fly();
    else map.once("load", fly);
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
      <div ref={containerRef} className="w-full h-full" />
      <canvas
        ref={canvasOverlayRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ zIndex: 1 }}
      />

      {instruction && (
        <div
          className="absolute top-4 left-1/2 -translate-x-1/2 bg-surface-base/80 backdrop-blur text-fg px-5 py-2.5 rounded-full text-sm font-medium shadow-lg pointer-events-none select-none border border-border-default"
          style={{ zIndex: 2 }}
        >
          {instruction}
        </div>
      )}

      {interaction.step === "radius_set" && (
        <div
          className="absolute top-4 left-1/2 -translate-x-1/2 flex items-center gap-2"
          style={{ zIndex: 2 }}
        >
          <span className="bg-accent text-fg px-4 py-2 rounded-full text-sm font-semibold shadow-lg">
            {formatDistance(interaction.radius_m)} radius
          </span>
          <button
            onClick={onReset}
            className="bg-surface-raised/90 backdrop-blur text-fg-secondary px-4 py-2 rounded-full text-sm font-medium shadow-lg border border-border-default hover:bg-surface-overlay transition-colors cursor-pointer"
          >
            Reset
          </button>
        </div>
      )}
    </div>
  );
}

function radiusToZoom(radiusM: number): number {
  const km = radiusM / 1000;
  if (km < 0.2) return 16;
  if (km < 0.5) return 15;
  if (km < 1) return 14;
  if (km < 2) return 13;
  if (km < 5) return 12;
  return 11;
}
