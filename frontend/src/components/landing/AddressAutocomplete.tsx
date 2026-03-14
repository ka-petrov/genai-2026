import { useEffect, useRef, useState, useCallback } from "react";
import { PinIcon } from "../../ds";

const GOOGLE_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

interface Props {
  value: string;
  onChange: (value: string) => void;
  onPlaceSelect: (coords: { lat: number; lon: number } | null) => void;
}

let scriptLoadPromise: Promise<void> | null = null;

function loadGoogleMapsScript(): Promise<void> {
  if (scriptLoadPromise) return scriptLoadPromise;
  if (window.google?.maps?.places) return Promise.resolve();

  scriptLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_API_KEY}&libraries=places`;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google Maps"));
    document.head.appendChild(script);
  });
  return scriptLoadPromise;
}

export default function AddressAutocomplete({
  value,
  onChange,
  onPlaceSelect,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);
  const [apiReady, setApiReady] = useState(false);

  useEffect(() => {
    if (!GOOGLE_API_KEY) return;
    loadGoogleMapsScript()
      .then(() => setApiReady(true))
      .catch(() => {});
  }, []);

  const handlePlaceChanged = useCallback(() => {
    const ac = autocompleteRef.current;
    if (!ac) return;
    const place = ac.getPlace();
    if (place?.geometry?.location) {
      const lat = place.geometry.location.lat();
      const lon = place.geometry.location.lng();
      onChange(place.formatted_address ?? place.name ?? value);
      onPlaceSelect({ lat, lon });
    }
  }, [onChange, onPlaceSelect, value]);

  useEffect(() => {
    if (!apiReady || !inputRef.current || autocompleteRef.current) return;
    const ac = new google.maps.places.Autocomplete(inputRef.current, {
      types: ["geocode"],
      fields: ["geometry", "formatted_address", "name"],
    });
    ac.addListener("place_changed", handlePlaceChanged);
    autocompleteRef.current = ac;
  }, [apiReady, handlePlaceChanged]);

  return (
    <div className="relative">
      <div className="absolute left-4 top-1/2 -translate-y-1/2 text-fg-muted pointer-events-none">
        <PinIcon className="w-4 h-4" />
      </div>
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          onPlaceSelect(null);
        }}
        placeholder="Enter an address (optional)"
        className="w-full bg-surface-sunken border border-border-strong rounded-xl pl-10 pr-4 py-3 text-sm text-fg-secondary placeholder:text-fg-faint focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-transparent transition-all"
      />
    </div>
  );
}
