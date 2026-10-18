/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_GOOGLE_MAPS_API_KEY?: string;
  readonly VITE_FIREBASE_API_KEY?: string;
  readonly VITE_FIREBASE_AUTH_DOMAIN?: string;
  readonly VITE_FIREBASE_PROJECT_ID?: string;
  readonly VITE_FIREBASE_STORAGE_BUCKET?: string;
  readonly VITE_FIREBASE_MESSAGING_SENDER_ID?: string;
  readonly VITE_FIREBASE_APP_ID?: string;
  readonly VITE_FIREBASE_VAPID_KEY?: string;
  readonly VITE_DEFAULT_MAP_LAT?: string;
  readonly VITE_DEFAULT_MAP_LNG?: string;
  readonly NEXT_PUBLIC_API_BASE_URL?: string;
  readonly NEXT_PUBLIC_GOOGLE_MAPS_API_KEY?: string;
  readonly NEXT_PUBLIC_DEMO_MODE?: string;
  readonly NEXT_PUBLIC_DEMO_PASSWORD?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface Window {
  google?: {
    maps: {
      Map: new (el: HTMLElement, opts: Record<string, unknown>) => GoogleMapHandle;
      Marker: new (opts: Record<string, unknown>) => GoogleMarkerHandle;
      LatLng: new (lat: number, lng: number) => { lat: () => number; lng: () => number };
      event: {
        addListener: (target: unknown, name: string, handler: (...args: unknown[]) => void) => void;
        trigger: (target: unknown, name: string) => void;
      };
      Circle: new (opts: Record<string, unknown>) => unknown;
      Rectangle: new (opts: Record<string, unknown>) => unknown;
      SymbolPath: { CIRCLE: number; BACKWARD_CLOSED_ARROW: number };
      places?: {
        Autocomplete: new (
          input: HTMLInputElement,
          opts?: Record<string, unknown>,
        ) => {
          addListener: (name: string, handler: () => void) => void;
          getPlace: () => {
            formatted_address?: string;
            geometry?: { location?: { lat: () => number; lng: () => number } };
            name?: string;
          };
        };
      };
    };
  };
}

interface GoogleMapHandle {
  setCenter: (c: { lat: number; lng: number }) => void;
  panTo: (c: { lat: number; lng: number }) => void;
  setZoom: (z: number) => void;
}

interface GoogleMarkerHandle {
  setPosition: (c: { lat: number; lng: number }) => void;
  setMap: (map: GoogleMapHandle | null) => void;
  addListener: (name: string, handler: () => void) => void;
}
