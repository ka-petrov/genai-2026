function toRad(deg: number): number {
  return deg * (Math.PI / 180);
}

export function haversineDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const R = 6371000;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/** Returns [lon, lat] pairs forming a closed circle for canvas projection. */
export function createCirclePoints(
  lat: number,
  lon: number,
  radiusM: number,
  segments = 64,
): [number, number][] {
  const coords: [number, number][] = [];
  for (let i = 0; i <= segments; i++) {
    const angle = (i / segments) * 2 * Math.PI;
    const dy = radiusM * Math.cos(angle);
    const dx = radiusM * Math.sin(angle);
    const pLat = lat + (dy / 6371000) * (180 / Math.PI);
    const pLon =
      lon + (dx / (6371000 * Math.cos(toRad(lat)))) * (180 / Math.PI);
    coords.push([pLon, pLat]);
  }
  return coords;
}

export function formatDistance(meters: number): string {
  if (meters < 1000) return `${Math.round(meters)}m`;
  return `${(meters / 1000).toFixed(1)}km`;
}
