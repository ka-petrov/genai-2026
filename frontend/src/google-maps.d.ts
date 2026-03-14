declare namespace google.maps {
  class LatLng {
    lat(): number;
    lng(): number;
  }

  namespace places {
    class Autocomplete {
      constructor(input: HTMLInputElement, opts?: AutocompleteOptions);
      getPlace(): PlaceResult;
      addListener(event: string, handler: () => void): void;
    }

    interface AutocompleteOptions {
      types?: string[];
      fields?: string[];
      componentRestrictions?: { country: string | string[] };
    }

    interface PlaceResult {
      geometry?: {
        location?: LatLng;
      };
      formatted_address?: string;
      name?: string;
    }
  }
}
