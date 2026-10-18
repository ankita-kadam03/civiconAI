import { useEffect, useRef, useState } from "react";
import { getMapCenter, loadGoogleMaps } from "../lib/maps-loader";
import {
  drawServiceAreaOverlay,
  getMunicipalityBounds,
  isInsideMunicipality,
  type MunicipalityBounds,
} from "../lib/service-area";
import { endpoints } from "../lib/api";
import type { Complaint } from "../lib/types";
import { Button, Input } from "./ui";

function MapsUnavailable({ reason }: { reason: string }) {
  return (
    <div className="flex min-h-[18rem] items-center justify-center rounded-3xl border border-dashed border-navy/20 bg-foam px-6 text-center text-sm text-navy/70">
      {reason}
    </div>
  );
}

function triggerMapResize(map: GoogleMapHandle) {
  window.setTimeout(() => {
    const g = window.google?.maps;
    if (g?.event) g.event.trigger(map, "resize");
  }, 80);
}

/** Hero map: municipal boundary + public issue pins. */
export function HomePreviewMap() {
  const googleRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [caption, setCaption] = useState("Loading map…");

  useEffect(() => {
    let cancelled = false;

    async function resolveUserCenter(): Promise<{ lat: number; lng: number } | null> {
      if (!navigator.geolocation) return null;
      return new Promise((resolve) => {
        navigator.geolocation.getCurrentPosition(
          (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
          () => resolve(null),
          { enableHighAccuracy: true, timeout: 12000, maximumAge: 300000 },
        );
      });
    }

    async function boot() {
      setError("");
      const userCenter = await resolveUserCenter();
      if (cancelled) return;

      let center: { lat: number; lng: number };
      try {
        center = userCenter ?? (await getMapCenter());
      } catch {
        setError("Map center is not configured. Set DEFAULT_MAP_LAT and DEFAULT_MAP_LNG in backend/.env.");
        return;
      }
      setCaption(userCenter ? "Centered on your location." : "Showing the municipal service area.");

      const mapsApi = await loadGoogleMaps();
      if (cancelled) return;
      if (!mapsApi || !googleRef.current) {
        setError("Google Maps could not load. Check VITE_GOOGLE_MAPS_API_KEY.");
        return;
      }
      const map = new mapsApi.Map(googleRef.current, {
        center,
        zoom: userCenter ? 14 : 11,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        zoomControl: true,
      });
      triggerMapResize(map);
      if (userCenter) {
        new mapsApi.Marker({ map, position: userCenter, title: "You are here" });
      }
      const bounds = await getMunicipalityBounds();
      if (!cancelled && bounds) {
        drawServiceAreaOverlay(mapsApi, map, bounds);
      }
      try {
        const res = await endpoints.publicComplaints("?page_size=100");
        for (const item of res.items) {
          if (item.latitude == null || item.longitude == null) continue;
          const marker = new mapsApi.Marker({
            map,
            position: { lat: item.latitude, lng: item.longitude },
            title: item.title,
            icon: {
              path: mapsApi.SymbolPath.CIRCLE,
              scale: 9,
              fillColor: "#2A9D8F",
              fillOpacity: 1,
              strokeColor: "#1B2545",
              strokeWeight: 2,
            },
          });
          marker.addListener("click", () => {
            window.location.assign(`/explore/${item.reference}`);
          });
        }
        setCaption(
          res.items.length
            ? `${res.items.length} public issue${res.items.length === 1 ? "" : "s"} in Tambaram municipality.`
            : userCenter
              ? "Centered on your location."
              : "Showing the municipal service area.",
        );
      } catch {
        /* map still usable without pins */
      }
      setReady(true);
    }

    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <MapsUnavailable reason={error} />;
  return (
    <div className="space-y-2">
      <div
        ref={googleRef}
        className={`min-h-[16rem] w-full overflow-hidden rounded-3xl bg-foam md:min-h-[20rem] ${ready ? "" : "animate-pulse"}`}
      />
      <p className="text-center text-xs text-navy/55 dark:text-slate-400">{caption}</p>
    </div>
  );
}

export function IncidentMap({ incidents }: { incidents: Complaint[] }) {
  const points = incidents.filter((i) => i.latitude != null && i.longitude != null);
  const googleRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let map: GoogleMapHandle | null = null;
    async function boot() {
      setError("");
      let center: { lat: number; lng: number };
      try {
        center = await getMapCenter(points[0] ? { lat: points[0].latitude as number, lng: points[0].longitude as number } : undefined);
      } catch {
        setError("Map center is not configured. Set DEFAULT_MAP_LAT and DEFAULT_MAP_LNG in backend/.env, then restart the API.");
        return;
      }
      const mapsApi = await loadGoogleMaps();
      if (cancelled) return;
      if (!mapsApi || !googleRef.current) {
        setError("Google Maps could not load. Check VITE_GOOGLE_MAPS_API_KEY and enable Maps JavaScript API + billing.");
        return;
      }
      map = new mapsApi.Map(googleRef.current, {
        center,
        zoom: points.length ? 13 : 11,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
      });
      triggerMapResize(map);
      points.forEach((item) => {
        const marker = new mapsApi.Marker({
          map,
          position: { lat: item.latitude as number, lng: item.longitude as number },
          title: item.title,
        });
        marker.addListener("click", () => {
          window.location.assign(`/explore/${item.reference}`);
        });
      });
      setReady(true);
    }
    void boot();
    return () => {
      cancelled = true;
      map = null;
    };
  }, [incidents]);

  if (error) return <MapsUnavailable reason={error} />;
  return (
    <div
      ref={googleRef}
      className={`min-h-[20rem] w-full overflow-hidden rounded-3xl bg-foam ${ready ? "" : "animate-pulse"}`}
    />
  );
}

export function LocationPicker({
  latitude,
  longitude,
  locality,
  onChange,
  onBlocked,
}: {
  latitude?: number;
  longitude?: number;
  locality: string;
  onChange: (next: { latitude?: number; longitude?: number; locality?: string; address?: string }) => void;
  onBlocked?: (message: string) => void;
}) {
  const [error, setError] = useState("");
  const [tracking, setTracking] = useState(false);
  const [mapLoading, setMapLoading] = useState(true);
  const searchRef = useRef<HTMLInputElement>(null);
  const googleBox = useRef<HTMLDivElement>(null);
  const mapRef = useRef<GoogleMapHandle | null>(null);
  const markerRef = useRef<GoogleMarkerHandle | null>(null);
  const watchRef = useRef<number | null>(null);
  const boundsRef = useRef<MunicipalityBounds | null>(null);
  const [mapError, setMapError] = useState("");

  function validatePoint(lat: number, lng: number): boolean {
    const bounds = boundsRef.current;
    if (!bounds) return true;
    if (isInsideMunicipality(lat, lng, bounds)) return true;
    const msg = "That location is outside the municipal area where officers are available. Move the pin inside the service boundary.";
    setError(msg);
    onBlocked?.(msg);
    return false;
  }

  function applyPosition(lat: number, lng: number, accuracy?: number) {
    if (!validatePoint(lat, lng)) return;
    onChange({ latitude: lat, longitude: lng });
    mapRef.current?.panTo({ lat, lng });
    markerRef.current?.setPosition({ lat, lng });
    if (accuracy != null && accuracy > 80) {
      setError(`Location accuracy ~${Math.round(accuracy)} m — drag the pin if needed.`);
    } else {
      setError("");
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      setMapError("");
      setMapLoading(true);
      boundsRef.current = await getMunicipalityBounds();
      const mapsApi = await loadGoogleMaps();
      if (cancelled) return;
      if (!googleBox.current) {
        setMapLoading(false);
        return;
      }
      if (!mapsApi) {
        setMapError("Google Maps is required. Set VITE_GOOGLE_MAPS_API_KEY in frontend/.env.local and restart Vite.");
        setMapLoading(false);
        return;
      }
      let center: { lat: number; lng: number };
      try {
        center = await getMapCenter(
          latitude != null && longitude != null ? { lat: latitude, lng: longitude } : undefined,
        );
      } catch {
        setMapError("Map center missing. Set DEFAULT_MAP_LAT/LNG in backend/.env and matching VITE_DEFAULT_MAP_* in frontend/.env.local.");
        setMapLoading(false);
        return;
      }
      const map = new mapsApi.Map(googleBox.current, {
        center,
        zoom: 14,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
      });
      mapRef.current = map;
      const marker = new mapsApi.Marker({ map, position: center, draggable: true });
      markerRef.current = marker;
      triggerMapResize(map);
      const b = boundsRef.current;
      if (b) {
        drawServiceAreaOverlay(mapsApi, map, b);
      }
      mapsApi.event.addListener(map, "click", (...args: unknown[]) => {
        const event = args[0] as { latLng?: { lat: () => number; lng: () => number } };
        const lat = event.latLng?.lat();
        const lng = event.latLng?.lng();
        if (lat == null || lng == null) return;
        if (!validatePoint(lat, lng)) return;
        marker.setPosition({ lat, lng });
        onChange({ latitude: lat, longitude: lng });
      });
      marker.addListener("dragend", () => {
        const pos = (marker as unknown as { getPosition?: () => { lat: () => number; lng: () => number } }).getPosition?.();
        if (!pos) return;
        const lat = pos.lat();
        const lng = pos.lng();
        if (!validatePoint(lat, lng)) return;
        onChange({ latitude: lat, longitude: lng });
      });
      if (searchRef.current && mapsApi.places) {
        const auto = new mapsApi.places.Autocomplete(searchRef.current, { fields: ["formatted_address", "geometry", "name"] });
        auto.addListener("place_changed", () => {
          const place = auto.getPlace();
          const loc = place.geometry?.location;
          if (!loc) return;
          const next = { lat: loc.lat(), lng: loc.lng() };
          if (!validatePoint(next.lat, next.lng)) return;
          map.panTo(next);
          marker.setPosition(next);
          onChange({
            latitude: next.lat,
            longitude: next.lng,
            locality: place.name || locality,
            address: place.formatted_address,
          });
        });
      }
      setMapLoading(false);
    }
    void boot();
    return () => {
      cancelled = true;
      if (watchRef.current != null) navigator.geolocation.clearWatch(watchRef.current);
    };
  }, []);

  useEffect(() => {
    if (latitude == null || longitude == null || !mapRef.current || !markerRef.current) return;
    const next = { lat: latitude, lng: longitude };
    mapRef.current.panTo(next);
    markerRef.current.setPosition(next);
  }, [latitude, longitude]);

  function useMyLocation() {
    setError("");
    if (!navigator.geolocation) {
      setError("Geolocation is not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => applyPosition(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy),
      () => setError("Location permission denied. Search or tap inside the green boundary."),
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 },
    );
  }

  function toggleLive() {
    if (watchRef.current != null) {
      navigator.geolocation.clearWatch(watchRef.current);
      watchRef.current = null;
      setTracking(false);
      return;
    }
    if (!navigator.geolocation) {
      setError("Geolocation is not available in this browser.");
      return;
    }
    setTracking(true);
    watchRef.current = navigator.geolocation.watchPosition(
      (pos) => applyPosition(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy),
      () => {
        setError("Live tracking stopped.");
        setTracking(false);
        if (watchRef.current != null) navigator.geolocation.clearWatch(watchRef.current);
        watchRef.current = null;
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 25000 },
    );
  }

  return (
    <div className="space-y-3">
      <Input ref={searchRef} placeholder="Search inside the municipal service area" />
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="soft" onClick={useMyLocation}>
          Use my location
        </Button>
        <Button type="button" variant={tracking ? "primary" : "ghost"} onClick={toggleLive}>
          {tracking ? "Stop live tracking" : "Track live on map"}
        </Button>
      </div>
      <p className="text-xs text-navy/55">Reports and saved places must fall inside the teal boundary where L1–L3 officers operate.</p>
      {error ? <p className="text-sm text-amber-800">{error}</p> : null}
      {mapError ? (
        <MapsUnavailable reason={mapError} />
      ) : (
        <div className="relative min-h-[18rem] w-full overflow-hidden rounded-3xl bg-foam ring-1 ring-navy/10">
          {mapLoading ? <div className="absolute inset-0 animate-pulse bg-foam" aria-hidden /> : null}
          <div ref={googleBox} className="absolute inset-0 min-h-[18rem] w-full" />
        </div>
      )}
      <p className="text-xs text-navy/50">
        {latitude != null && longitude != null
          ? `Selected ${latitude.toFixed(5)}, ${longitude.toFixed(5)}${tracking ? " · updating live" : ""}`
          : "Tap inside the boundary, search, or use your location."}
      </p>
    </div>
  );
}
