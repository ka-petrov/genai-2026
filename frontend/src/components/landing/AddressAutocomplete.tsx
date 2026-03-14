import { useEffect, useRef, useState, useCallback } from "react";
import { PinIcon } from "../../ds";
import {
  geocodeAutocomplete,
  geocodePlaceDetails,
  type PlacePrediction,
} from "../../api/client";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onPlaceSelect: (coords: { lat: number; lon: number } | null) => void;
}

export default function AddressAutocomplete({
  value,
  onChange,
  onPlaceSelect,
}: Props) {
  const [predictions, setPredictions] = useState<PlacePrediction[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [resolving, setResolving] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const sessionTokenRef = useRef(crypto.randomUUID());
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  const fetchPredictions = useCallback(
    (input: string) => {
      clearTimeout(debounceRef.current);
      if (input.length < 2) {
        setPredictions([]);
        setOpen(false);
        return;
      }
      setLoading(true);
      setOpen(true);
      debounceRef.current = setTimeout(async () => {
        const results = await geocodeAutocomplete(
          input,
          sessionTokenRef.current,
        );
        setPredictions(results);
        setOpen(results.length > 0);
        setLoading(false);
      }, 300);
    },
    [],
  );

  const handleSelect = useCallback(
    async (prediction: PlacePrediction) => {
      onChange(prediction.description);
      setOpen(false);
      setPredictions([]);
      setResolving(true);

      const details = await geocodePlaceDetails(
        prediction.place_id,
        sessionTokenRef.current,
      );
      // Reset session token after a complete autocomplete+details cycle
      sessionTokenRef.current = crypto.randomUUID();

      if (details) {
        onPlaceSelect({ lat: details.lat, lon: details.lon });
      }
      setResolving(false);
    },
    [onChange, onPlaceSelect],
  );

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={wrapperRef} className="relative">
      <div className="absolute left-4 top-1/2 -translate-y-1/2 text-fg-muted pointer-events-none">
        {resolving ? (
          <div className="w-4 h-4 border-2 border-fg-muted/30 border-t-fg-muted rounded-full animate-spin" />
        ) : (
          <PinIcon className="w-4 h-4" />
        )}
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          onPlaceSelect(null);
          fetchPredictions(e.target.value);
        }}
        onFocus={() => {
          if (predictions.length > 0) setOpen(true);
        }}
        placeholder="Enter an address (optional)"
        className="w-full bg-surface-sunken border border-border-strong rounded-xl pl-10 pr-4 py-3 text-sm text-fg-secondary placeholder:text-fg-faint focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-transparent transition-all"
      />

      {open && (predictions.length > 0 || loading) && (
        <ul className="absolute z-50 mt-1 w-full rounded-xl border border-border-default bg-surface-raised shadow-lg overflow-hidden">
          {predictions.map((p) => (
            <li key={p.place_id}>
              <button
                type="button"
                className="w-full px-4 py-2.5 text-left text-sm text-fg hover:bg-surface-sunken transition-colors cursor-pointer"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => handleSelect(p)}
              >
                {p.description}
              </button>
            </li>
          ))}
          {loading && (
            <li className="px-4 py-2 text-xs text-fg-muted flex items-center gap-2">
              <div className="w-3 h-3 border-2 border-fg-muted/30 border-t-fg-muted rounded-full animate-spin" />
              Searching...
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
