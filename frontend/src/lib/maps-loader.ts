import { config } from "./config";

let bootstrapCenter: { lat: number; lng: number } | null = null;

declare global {
  interface Window {
    __civiconMapsReady?: () => void;
  }
}

export async function fetchBootstrapCenter(): Promise<{ lat: number; lng: number } | null> {
  if (bootstrapCenter) return bootstrapCenter;
  if (config.mapCenter) {
    bootstrapCenter = config.mapCenter;
    return bootstrapCenter;
  }
  if (!config.apiBase) return null;
  try {
    const res = await fetch(`${config.apiBase}/api/public/bootstrap`);
    if (!res.ok) return null;
    const body = (await res.json()) as { map_center?: { lat: number; lng: number } | null };
    if (body.map_center?.lat != null && body.map_center?.lng != null) {
      bootstrapCenter = { lat: body.map_center.lat, lng: body.map_center.lng };
      return bootstrapCenter;
    }
  } catch {
    return null;
  }
  return null;
}

export async function getMapCenter(preferred?: { lat: number; lng: number }): Promise<{ lat: number; lng: number }> {
  if (preferred) return preferred;
  const fromApi = await fetchBootstrapCenter();
  if (fromApi) return fromApi;
  throw new Error("Map center is not configured. Set DEFAULT_MAP_LAT and DEFAULT_MAP_LNG in backend/.env or VITE_DEFAULT_MAP_* in frontend/.env.local.");
}

export async function loadGoogleMaps(): Promise<NonNullable<Window["google"]>["maps"] | null> {
  const key = config.mapsKey?.trim();
  if (!key) return null;
  if (window.google?.maps) return window.google.maps;

  return new Promise((resolve) => {
    const finish = () => resolve(window.google?.maps ?? null);

    const existing = document.getElementById("civicon-maps") as HTMLScriptElement | null;
    if (existing) {
      if (window.google?.maps) {
        finish();
        return;
      }
      existing.addEventListener("load", finish);
      existing.addEventListener("error", () => resolve(null));
      window.setTimeout(finish, 8000);
      return;
    }

    window.__civiconMapsReady = () => {
      delete window.__civiconMapsReady;
      finish();
    };

    const script = document.createElement("script");
    script.id = "civicon-maps";
    script.async = true;
    script.defer = true;
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&libraries=places&loading=async&callback=__civiconMapsReady`;
    script.onerror = () => resolve(null);
    document.head.appendChild(script);
  });
}
