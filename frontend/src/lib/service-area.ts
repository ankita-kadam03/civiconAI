import { endpoints } from "./api";

export type MunicipalityBounds = {
  center?: { lat: number; lng: number };
  radius_m?: number;
  min_lat?: number;
  max_lat?: number;
  min_lng?: number;
  max_lng?: number;
};

let cached: MunicipalityBounds | null = null;

export function resetServiceAreaCache(): void {
  cached = null;
}

function distanceM(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const r = 6371000;
  const p1 = (lat1 * Math.PI) / 180;
  const p2 = (lat2 * Math.PI) / 180;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dLng / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(a));
}

export async function getMunicipalityBounds(): Promise<MunicipalityBounds | null> {
  if (cached) return cached;
  try {
    const boot = await endpoints.bootstrap();
    const b = boot.service_area?.municipality_bounds;
    if (b) {
      if (b.min_lat != null && b.max_lat != null && b.min_lng != null && b.max_lng != null) {
        cached = {
          min_lat: b.min_lat,
          max_lat: b.max_lat,
          min_lng: b.min_lng,
          max_lng: b.max_lng,
          center: b.center,
        };
        return cached;
      }
      if (b.center?.lat != null && b.center.lng != null && b.radius_m) {
        cached = { center: b.center, radius_m: b.radius_m };
        return cached;
      }
    }
  } catch {
    return null;
  }
  return null;
}

export function isInsideMunicipality(lat: number, lng: number, bounds: MunicipalityBounds): boolean {
  if (
    bounds.min_lat != null &&
    bounds.max_lat != null &&
    bounds.min_lng != null &&
    bounds.max_lng != null
  ) {
    return lat >= bounds.min_lat && lat <= bounds.max_lat && lng >= bounds.min_lng && lng <= bounds.max_lng;
  }
  if (bounds.center?.lat != null && bounds.center.lng != null && bounds.radius_m != null) {
    return distanceM(lat, lng, bounds.center.lat, bounds.center.lng) <= bounds.radius_m;
  }
  return true;
}

export function drawServiceAreaOverlay(
  mapsApi: NonNullable<Window["google"]>["maps"],
  map: GoogleMapHandle,
  bounds: MunicipalityBounds,
): void {
  const style = {
    strokeColor: "#2A9D8F",
    strokeOpacity: 0.65,
    strokeWeight: 2,
    fillColor: "#2A9D8F",
    fillOpacity: 0.08,
    clickable: false,
  };
  if (
    bounds.min_lat != null &&
    bounds.max_lat != null &&
    bounds.min_lng != null &&
    bounds.max_lng != null
  ) {
    new mapsApi.Rectangle({
      map,
      bounds: {
        north: bounds.max_lat,
        south: bounds.min_lat,
        east: bounds.max_lng,
        west: bounds.min_lng,
      },
      ...style,
    });
    return;
  }
  if (bounds.center?.lat != null && bounds.center.lng != null && bounds.radius_m != null) {
    new mapsApi.Circle({
      map,
      center: bounds.center,
      radius: bounds.radius_m,
      ...style,
    });
  }
}
