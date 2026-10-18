import { CloudRain, CloudSun, Loader2, Sun, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { endpoints } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { config } from "../../lib/config";
import { cx } from "../../lib/format";

type WeatherPayload = {
  ok?: boolean;
  alert?: string | null;
  headline?: string | null;
  message?: string | null;
  temperature_c?: number;
  conditions?: string;
  summary?: string;
  error?: string;
  hint?: string;
};

type Coords = { lat: number; lng: number; label: "you" | "area" };

async function bootstrapCoords(): Promise<Coords | null> {
  if (config.mapCenter) {
    return { lat: config.mapCenter.lat, lng: config.mapCenter.lng, label: "area" };
  }
  try {
    const boot = await endpoints.bootstrap();
    const c = boot.map_center;
    if (c?.lat != null && c?.lng != null) {
      return { lat: c.lat, lng: c.lng, label: "area" };
    }
  } catch {
    /* ignore */
  }
  return null;
}

function tryGeolocation(): Promise<Coords | null> {
  if (!navigator.geolocation) return Promise.resolve(null);
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude, label: "you" }),
      () => resolve(null),
      { enableHighAccuracy: false, maximumAge: 600_000, timeout: 8_000 },
    );
  });
}

export function WeatherAlertBar() {
  const { user } = useAuth();
  const [data, setData] = useState<WeatherPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [locationLabel, setLocationLabel] = useState<"you" | "area">("area");
  const [alertDismissed, setAlertDismissed] = useState(false);
  const notifiedAlert = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchWeather(coords: Coords) {
      setLocationLabel(coords.label);
      try {
        const res = (await endpoints.weather(coords.lat, coords.lng)) as WeatherPayload;
        if (cancelled) return;
        setData(res);
        if (res.ok && res.alert && user?.id) {
          const key = `${res.alert}:${new Date().toISOString().slice(0, 10)}`;
          if (notifiedAlert.current !== key) {
            notifiedAlert.current = key;
            await endpoints.weatherCheck(coords.lat, coords.lng).catch(() => undefined);
          }
        }
      } catch {
        if (!cancelled) setData({ ok: false, error: "NETWORK" });
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    async function refresh() {
      setLoading(true);
      const area = await bootstrapCoords();
      if (cancelled) return;
      if (area) await fetchWeather(area);
      else if (!cancelled) {
        setData({ ok: false, error: "NO_LOCATION" });
        setLoading(false);
      }
      const geo = await tryGeolocation();
      if (cancelled || !geo) return;
      await fetchWeather(geo);
    }

    void refresh();
    const id = window.setInterval(() => void refresh(), 20 * 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [user?.id]);

  if (loading && !data) {
    return (
      <div className="border-b border-navy/8 bg-mint/25 px-4 py-2 dark:border-white/10 dark:bg-teal/10">
        <div className="mx-auto flex max-w-6xl items-center gap-2 text-xs text-navy/70 sm:text-sm">
          <Loader2 size={16} className="animate-spin text-teal" aria-hidden />
          Loading current weather…
        </div>
      </div>
    );
  }

  if (!data?.ok) {
    return (
      <div className="border-b border-amber-200/60 bg-amber-50/90 px-4 py-2 dark:border-amber-500/30 dark:bg-amber-950/40">
        <div className="mx-auto max-w-6xl text-xs text-navy dark:text-amber-50 sm:text-sm">
          <p className="flex items-center gap-2 font-semibold">
            <CloudSun size={18} className="shrink-0 text-amber-600" aria-hidden />
            Google Weather unavailable
          </p>
          <p className="mt-1 opacity-90">{data?.hint || data?.message || "Configure GOOGLE_SERVER_API_KEY on the backend."}</p>
        </div>
      </div>
    );
  }

  const summary =
    data.summary ||
    (data.temperature_c != null ? `${Math.round(Number(data.temperature_c))}°C` : data.conditions || "Weather");

  const showAlert = Boolean(data.alert) && !alertDismissed;
  const StatusIcon = data.alert === "heat" ? Sun : data.alert === "rain" ? CloudRain : CloudSun;

  return (
    <div className="border-b border-navy/8 bg-gradient-to-r from-white via-mint/30 to-white dark:border-white/10 dark:from-slate-950 dark:via-teal/10 dark:to-slate-950">
      <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-2 text-xs sm:text-sm">
        <StatusIcon
          size={18}
          className={cx(
            "shrink-0",
            data.alert === "rain" ? "text-sky-600" : data.alert === "heat" ? "text-amber-500" : "text-teal",
          )}
          aria-hidden
        />
        <p className="min-w-0 flex-1 font-medium text-navy dark:text-slate-100">
          <span className="text-navy/55 dark:text-slate-400">Near {locationLabel === "you" ? "you" : "service area"}: </span>
          <span className="font-semibold">{summary}</span>
        </p>
      </div>
      {showAlert ? (
        <div
          className={cx(
            "border-t px-4 py-2 text-xs sm:text-sm",
            data.alert === "rain"
              ? "border-sky/25 bg-sky/35 text-navy dark:bg-sky/15 dark:text-white"
              : "border-amber-200/50 bg-amber-50/90 text-navy dark:border-amber-500/25 dark:bg-amber-950/35 dark:text-amber-50",
          )}
          role="alert"
        >
          <div className="mx-auto flex max-w-6xl items-start gap-2">
            <div className="min-w-0 flex-1">
              <p className="font-bold">{data.headline}</p>
              <p className="mt-0.5 leading-relaxed opacity-90">{data.message}</p>
              {user ? <p className="mt-1 text-[10px] opacity-75 sm:text-xs">Saved to your notifications.</p> : null}
            </div>
            <button
              type="button"
              className="shrink-0 rounded-full p-1 opacity-70 transition hover:opacity-100"
              aria-label="Dismiss weather advisory"
              onClick={() => setAlertDismissed(true)}
            >
              <X size={16} />
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
