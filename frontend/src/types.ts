export interface RegionSpec {
  lat: number;
  lon: number;
  radius_m: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AssistantTurnStructured {
  answer: string;
  reasoning_summary: string;
  evidence: string[];
  limitations: string[];
  confidence: "low" | "medium" | "high";
}

export interface RegionProfile {
  center: { lat: number; lon: number };
  radius_m: number;
  counts: Record<string, number>;
  nearest: Record<string, unknown>;
  mobility: Record<string, unknown>;
  land_use: Record<string, unknown>;
  poi_examples: Record<string, unknown>;
  data_quality_notes: string[];
}

export interface ContextResponse {
  context_id: string;
  region_profile: RegionProfile;
  map_features: GeoFeature[];
  meta: {
    cache_hit: boolean;
    data_sources: string[];
    request_id: string;
  };
}

export interface GeoFeature {
  type: "Feature";
  geometry: {
    type: string;
    coordinates: unknown;
  };
  properties: Record<string, unknown>;
}

export interface ChatThread {
  id: string;
  region: RegionSpec;
  context_id: string;
  messages: ChatMessage[];
  created_at: number;
}

export type MapInteractionState =
  | { step: "idle" }
  | { step: "pin_set"; lat: number; lon: number }
  | { step: "radius_set"; lat: number; lon: number; radius_m: number };
