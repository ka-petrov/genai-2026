import type {
  RegionSpec,
  ChatMessage,
  ContextResponse,
} from "../types";

export interface StreamEvent {
  event:
    | "response.started"
    | "response.delta"
    | "response.completed"
    | "response.error";
  data: Record<string, unknown>;
}

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== "false";

export async function createContext(
  region: RegionSpec,
): Promise<ContextResponse> {
  if (USE_MOCKS) return mockCreateContext(region);

  const res = await fetch("/api/contexts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ region }),
  });
  if (!res.ok) throw new Error(`Context creation failed: ${res.status}`);
  return res.json() as Promise<ContextResponse>;
}

export async function* streamChat(
  contextId: string,
  messages: ChatMessage[],
): AsyncGenerator<StreamEvent> {
  if (USE_MOCKS) {
    yield* mockStreamChat(messages);
    return;
  }

  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ context_id: contextId, messages }),
  });

  if (!res.ok || !res.body)
    throw new Error(`Stream request failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    let eventType = "";
    let dataStr = "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        dataStr += line.slice(6);
      } else if (line === "" && eventType && dataStr) {
        yield {
          event: eventType as StreamEvent["event"],
          data: JSON.parse(dataStr) as Record<string, unknown>,
        };
        eventType = "";
        dataStr = "";
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Geocode (proxied through backend)
// ---------------------------------------------------------------------------

export interface PlacePrediction {
  place_id: string;
  description: string;
}

export interface PlaceDetails {
  lat: number;
  lon: number;
  formatted_address: string | null;
  name: string | null;
}

export async function geocodeAutocomplete(
  input: string,
  sessionToken?: string,
): Promise<PlacePrediction[]> {
  const params = new URLSearchParams({ input });
  if (sessionToken) params.set("session_token", sessionToken);

  const res = await fetch(`/api/geocode/autocomplete?${params}`);
  if (!res.ok) return [];

  const json = (await res.json()) as {
    predictions: PlacePrediction[];
    status: string;
  };
  return json.predictions;
}

export async function geocodePlaceDetails(
  placeId: string,
  sessionToken?: string,
): Promise<PlaceDetails | null> {
  const params = new URLSearchParams({ place_id: placeId });
  if (sessionToken) params.set("session_token", sessionToken);

  const res = await fetch(`/api/geocode/place?${params}`);
  if (!res.ok) return null;

  const json = (await res.json()) as {
    result: PlaceDetails | null;
    status: string;
  };
  return json.result;
}

// ---------------------------------------------------------------------------
// Mock implementations
// ---------------------------------------------------------------------------

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function mockCreateContext(
  region: RegionSpec,
): Promise<ContextResponse> {
  await sleep(600);
  return {
    context_id: `ctx_${crypto.randomUUID().slice(0, 8)}`,
    region_profile: {
      center: { lat: region.lat, lon: region.lon },
      radius_m: region.radius_m,
      counts: {
        restaurants: 34,
        cafes: 12,
        schools: 5,
        parks: 8,
        bus_stops: 17,
        supermarkets: 6,
      },
      nearest: {},
      mobility: { bus_stops: 17, bike_parking: 23 },
      land_use: {},
      poi_examples: {},
      data_quality_notes: ["Mock data for development"],
    },
    map_features: [],
    meta: {
      cache_hit: false,
      data_sources: ["mock"],
      request_id: crypto.randomUUID(),
    },
  };
}

async function* mockStreamChat(
  messages: ChatMessage[],
): AsyncGenerator<StreamEvent> {
  yield {
    event: "response.started",
    data: { request_id: crypto.randomUUID(), model_id: "mock-model" },
  };

  const lastMsg = messages[messages.length - 1];
  const answer = pickMockAnswer(lastMsg?.content ?? "");

  for (const ch of answer) {
    await sleep(12 + Math.random() * 20);
    yield { event: "response.delta", data: { text: ch } };
  }

  yield {
    event: "response.completed",
    data: {
      answer,
      reasoning_summary:
        "Based on amenity density, transit access, and local services within the selected radius.",
      evidence: [
        "34 restaurants and 12 cafes within radius",
        "17 bus stops indicating good transit coverage",
        "8 parks and green spaces nearby",
        "5 schools in the area",
      ],
      limitations: [
        "Using mock data for development",
        "Real analysis requires live data sources",
      ],
      confidence: "medium",
    },
  };
}

function pickMockAnswer(query: string): string {
  const q = query.toLowerCase();

  if (q.includes("walk"))
    return "This area appears to be moderately walkable. With 34 restaurants, 12 cafes, and 6 supermarkets within your selected radius, daily amenities are accessible on foot. The presence of 17 bus stops suggests good transit coverage as a supplement to walking. There are also 8 parks nearby, which indicates pleasant walking routes are likely available. However, actual walkability depends on sidewalk infrastructure and road crossings, which require more detailed analysis.";

  if (q.includes("famil") || q.includes("kid") || q.includes("school"))
    return "This area shows several family-friendly indicators. There are 5 schools within the radius, along with 8 parks and green spaces that provide recreation areas for children. The 6 supermarkets make daily shopping convenient, and 17 bus stops offer transit options for school commutes. The restaurant and cafe density (34 and 12 respectively) suggests an active neighborhood with dining options. For a complete family suitability assessment, additional factors like noise levels, safety statistics, and healthcare proximity would be needed.";

  if (
    q.includes("transit") ||
    q.includes("transport") ||
    q.includes("bus") ||
    q.includes("commut")
  )
    return "Transit coverage in this area looks promising. With 17 bus stops within the selected radius, there are multiple transit options available. The bike parking count of 23 also suggests the area supports multimodal transportation. For a complete transit assessment, you'd want to consider service frequency, route coverage, and connections to major employment centers. The density of amenities (34 restaurants, 12 cafes, 6 supermarkets) near transit stops is a positive indicator of transit-oriented development.";

  if (q.includes("safe") || q.includes("quiet") || q.includes("noise"))
    return "Based on the available data, this area has characteristics that typically correlate with a relatively safe and livable environment. The presence of 8 parks, 5 schools, and active commercial zones with 34 restaurants and 12 cafes suggests a well-used public realm, which generally deters antisocial behavior. However, our current data sources do not include crime statistics, noise measurements, or street lighting data. A more comprehensive safety assessment would require additional data layers beyond what OSM provides.";

  return `Based on the available data for this area, I can see a well-served neighborhood with 34 restaurants, 12 cafes, 6 supermarkets, and 8 parks within your selected radius. Transit connectivity is supported by 17 bus stops. The area has 5 schools and 23 bike parking spots, suggesting it serves both residential and commuter needs. This gives a generally positive picture of local amenities and services, though a more specific analysis would depend on your particular priorities and needs.`;
}

