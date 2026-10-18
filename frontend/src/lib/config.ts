const env = import.meta.env;

function first(...values: Array<string | undefined>): string {
  for (const value of values) {
    if (value && value.trim()) return value.trim();
  }
  return "";
}

function parseCoord(raw: string | undefined): number | null {
  if (!raw?.trim()) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

const mapLat = parseCoord(first(env.VITE_DEFAULT_MAP_LAT, env.NEXT_PUBLIC_DEFAULT_MAP_LAT));
const mapLng = parseCoord(first(env.VITE_DEFAULT_MAP_LNG, env.NEXT_PUBLIC_DEFAULT_MAP_LNG));

export const config = {
  apiBase: first(env.VITE_API_BASE_URL, env.NEXT_PUBLIC_API_BASE_URL).replace(/\/$/, ""),
  mapsKey: first(env.VITE_GOOGLE_MAPS_API_KEY, env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY),
  mapCenter: mapLat != null && mapLng != null ? { lat: mapLat, lng: mapLng } : null,
  firebase: {
    apiKey: first(env.VITE_FIREBASE_API_KEY, env.NEXT_PUBLIC_FIREBASE_API_KEY),
    authDomain: first(env.VITE_FIREBASE_AUTH_DOMAIN, env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN),
    projectId: first(env.VITE_FIREBASE_PROJECT_ID, env.NEXT_PUBLIC_FIREBASE_PROJECT_ID),
    storageBucket: first(env.VITE_FIREBASE_STORAGE_BUCKET, env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET),
    messagingSenderId: first(env.VITE_FIREBASE_MESSAGING_SENDER_ID, env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID),
    appId: first(env.VITE_FIREBASE_APP_ID, env.NEXT_PUBLIC_FIREBASE_APP_ID),
    vapidKey: first(env.VITE_FIREBASE_VAPID_KEY, env.NEXT_PUBLIC_FIREBASE_VAPID_KEY),
  },
};
