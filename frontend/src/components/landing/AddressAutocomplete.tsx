import { useEffect, useRef, useState, useCallback } from "react";

const GOOGLE_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as
  | string
  | undefined;

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
      <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
        <svg
          className="w-4 h-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z"
          />
        </svg>
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
        className="w-full bg-[#2a2d35] border border-[#3a3d45] rounded-xl pl-10 pr-4 py-3 text-sm text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent transition-all"
      />
    </div>
  );
}
