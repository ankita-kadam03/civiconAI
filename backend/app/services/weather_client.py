from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

log = logging.getLogger("civicon.weather_client")

RAIN_HOUR_MM = 7.6
RAIN_SUM_MM = 10.0
HEAT_C = 40.0
GOOGLE_WEATHER_BASE = "https://weather.googleapis.com/v1"


def fetch_forecast(lat: float, lng: float) -> dict[str, Any]:
    """Google Maps Platform Weather API only (server key required)."""
    payload, err = _fetch_google_bundle(lat, lng)
    if payload:
        return payload
    return {"_error": err or "GOOGLE_WEATHER_UNAVAILABLE"}


def fetch_current(lat: float, lng: float) -> dict[str, Any]:
    data = fetch_forecast(lat, lng)
    if data.get("_error"):
        return {
            "ok": False,
            "error": data["_error"].get("code") if isinstance(data["_error"], dict) else "GOOGLE_WEATHER_UNAVAILABLE",
            "message": data["_error"].get("message") if isinstance(data["_error"], dict) else str(data["_error"]),
            "hint": data["_error"].get("hint") if isinstance(data["_error"], dict) else _default_hint(),
            "provider": "google_weather",
        }
    current = data.get("current") or {}
    alert = weather_alert_kind(data)
    return {
        "ok": True,
        "provider": "google_weather",
        "temperature_c": current.get("temperature_2m") or current.get("temperature"),
        "precipitation": current.get("precipitation"),
        "weather_code": current.get("weather_code"),
        "conditions": condition_label(current, alert),
        "summary": current_summary(current, alert),
        "alert": alert,
        "headline": alert_headline(alert) if alert else None,
        "message": alert_message(alert, current) if alert else None,
    }


def _default_hint() -> str:
    return (
        "Set GOOGLE_SERVER_API_KEY in backend/.env (server key with Weather API enabled). "
        "Browser Maps keys blocked by HTTP referrer cannot call the backend."
    )


def _server_api_key() -> str:
    settings = get_settings()
    for candidate in (
        getattr(settings, "google_server_api_key", "") or "",
        settings.google_maps_api_key or "",
    ):
        if candidate.strip():
            return candidate.strip()
    return ""


def _parse_google_error(status: int, body: dict) -> dict[str, str]:
    err = body.get("error") or {}
    message = str(err.get("message") or f"HTTP {status}")
    code = "GOOGLE_WEATHER_DENIED"
    hint = _default_hint()
    details = err.get("details") or []
    for item in details:
        if not isinstance(item, dict):
            continue
        reason = item.get("reason") or ""
        if reason == "API_KEY_HTTP_REFERRER_BLOCKED":
            code = "GOOGLE_KEY_REFERRER_BLOCKED"
            hint = (
                "Your key is restricted to websites (HTTP referrer). Create a separate "
                "GOOGLE_SERVER_API_KEY for the backend: Application restriction = IP address "
                "(or None for local dev), API restriction = Weather API."
            )
        elif "SERVICE_DISABLED" in reason or "has not been used" in message.lower():
            code = "GOOGLE_WEATHER_API_DISABLED"
            hint = (
                "Enable Weather API on your GCP project: "
                "https://console.cloud.google.com/apis/library/weather.googleapis.com "
                f"(project {settings_project_hint()})."
            )
    return {"code": code, "message": message, "hint": hint}


def settings_project_hint() -> str:
    return (get_settings().google_cloud_project or get_settings().firebase_project_resolved or "your-project").strip()


def _google_get(path: str, params: dict[str, Any]) -> tuple[dict | None, dict | None]:
    key = _server_api_key()
    if not key:
        return None, {"code": "GOOGLE_KEY_MISSING", "message": "No Google API key configured", "hint": _default_hint()}
    url = f"{GOOGLE_WEATHER_BASE}/{path}"
    params = {**params, "key": key}
    try:
        with httpx.Client(timeout=12.0) as client:
            res = client.get(url, params=params)
            body = res.json() if res.content else {}
            if res.status_code >= 400:
                parsed = _parse_google_error(res.status_code, body if isinstance(body, dict) else {})
                log.warning("google_weather_http status=%s code=%s", res.status_code, parsed.get("code"))
                return None, parsed
            return body if isinstance(body, dict) else {}, None
    except Exception as exc:  # noqa: BLE001
        log.warning("google_weather_failed error=%s", type(exc).__name__)
        return None, {"code": "GOOGLE_WEATHER_NETWORK", "message": type(exc).__name__, "hint": _default_hint()}


def _fetch_google_bundle(lat: float, lng: float) -> tuple[dict[str, Any] | None, dict | None]:
    loc = {"location.latitude": lat, "location.longitude": lng}
    current_body, err = _google_get("currentConditions:lookup", loc)
    if err:
        return None, err
    hours_body, hours_err = _google_get("forecast/hours:lookup", {**loc, "hours": 12})
    current = current_body.get("currentConditions") or current_body
    temp = current.get("temperature") or {}
    temp_c = temp.get("degrees") if isinstance(temp, dict) else temp
    precip = current.get("precipitation") or {}
    precip_mm = precip.get("quantity") if isinstance(precip, dict) else precip
    condition = (current.get("weatherCondition") or {}).get("type") if isinstance(current.get("weatherCondition"), dict) else None

    hourly_temps: list[float] = []
    hourly_precip: list[float] = []
    if not hours_err and hours_body:
        for hour in hours_body.get("forecastHours") or hours_body.get("hours") or []:
            if not isinstance(hour, dict):
                continue
            t = hour.get("temperature") or {}
            t_val = t.get("degrees") if isinstance(t, dict) else t
            if t_val is not None:
                hourly_temps.append(float(t_val))
            p = hour.get("precipitation") or {}
            p_val = p.get("quantity") if isinstance(p, dict) else p
            if p_val is not None:
                hourly_precip.append(float(p_val))
    if not hourly_temps and temp_c is not None:
        hourly_temps = [float(temp_c)] * 6
    if not hourly_precip:
        hourly_precip = [float(precip_mm or 0)] * 6

    return (
        {
            "provider": "google_weather",
            "current": {
                "temperature_2m": temp_c,
                "precipitation": precip_mm,
                "weather_code": condition,
            },
            "hourly": {
                "temperature_2m": hourly_temps,
                "precipitation": hourly_precip,
            },
        },
        None,
    )


def condition_label(current: dict, alert: str | None) -> str:
    if alert == "rain":
        return "Heavy rain likely"
    if alert == "heat":
        return "High heat"
    code = current.get("weather_code")
    if isinstance(code, str) and code:
        return code.replace("_", " ").title()
    precip = float(current.get("precipitation") or 0)
    if precip >= 0.5:
        return "Rain nearby"
    return "Fair conditions"


def current_summary(current: dict, alert: str | None) -> str:
    temp = current.get("temperature_2m") or current.get("temperature")
    label = condition_label(current, alert)
    if temp is None:
        return label
    try:
        t = round(float(temp))
    except (TypeError, ValueError):
        return label
    return f"{t}°C · {label}"


def weather_alert_kind(payload: dict) -> str | None:
    hourly = payload.get("hourly") or {}
    temps = hourly.get("temperature_2m") or hourly.get("temperature") or []
    rain = hourly.get("precipitation") or hourly.get("rain") or []
    if rain and (
        sum(float(x or 0) for x in rain[:6]) >= RAIN_SUM_MM
        or any(float(x or 0) >= RAIN_HOUR_MM for x in rain[:6])
    ):
        return "rain"
    if temps and any(float(x or 0) >= HEAT_C for x in temps[:6]):
        return "heat"
    current = payload.get("current") or {}
    if float(current.get("precipitation") or 0) >= RAIN_HOUR_MM:
        return "rain"
    return None


def alert_headline(kind: str | None) -> str:
    if kind == "rain":
        return "Heavy rain expected near you"
    if kind == "heat":
        return "High heat expected near you"
    return "Weather advisory"


def alert_message(kind: str | None, current: dict) -> str:
    temp = current.get("temperature_2m") or current.get("temperature")
    precip = current.get("precipitation")
    if kind == "rain":
        base = "Drainage and road issues may worsen. Avoid flooded areas and report blocked drains."
        if precip is not None:
            return f"{base} Current precipitation: {precip} mm."
        return base
    if kind == "heat":
        base = "Stay hydrated. Report failed streetlights or electrical hazards promptly."
        if temp is not None:
            return f"{base} Current temperature: {temp}°C."
        return base
    return "Check local conditions before travelling."
