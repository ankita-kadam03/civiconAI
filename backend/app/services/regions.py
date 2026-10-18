from __future__ import annotations

from app.db import Database
from app.domain.geo import bounds_center, distance_m, point_in_bounds
from app.errors import AppError


def region_center(region: dict) -> tuple[float, float] | None:
    lat, lng = region.get("latitude"), region.get("longitude")
    if lat is not None and lng is not None:
        return float(lat), float(lng)
    bounds = region.get("bounds")
    if isinstance(bounds, dict):
        return bounds_center(bounds)
    return None


def point_in_region(lat: float, lng: float, region: dict) -> bool:
    bounds = region.get("bounds")
    if isinstance(bounds, dict):
        return point_in_bounds(lat, lng, bounds)
    center = region_center(region)
    if not center:
        return False
    radius = float(region.get("radius_m") or 0)
    if radius <= 0:
        return False
    return distance_m(lat, lng, center[0], center[1]) <= radius


def municipality_region(db: Database) -> dict | None:
    doc = db.col("regions").find_one({"level": 3, "is_active": True})
    if doc:
        return doc
    return db.col("regions").find_one({"code": "municipality"})


def assert_in_municipality(db: Database, lat: float | None, lng: float | None) -> None:
    if lat is None or lng is None:
        raise AppError(
            "Pick a location inside the municipal service area on the map.",
            400,
            "LOCATION_OUTSIDE_SERVICE_AREA",
        )
    muni = municipality_region(db)
    if not muni:
        return
    if not point_in_region(lat, lng, muni):
        name = muni.get("name") or "municipal service area"
        raise AppError(
            f"That point is outside {name}. Choose a location where officers are assigned.",
            400,
            "LOCATION_OUTSIDE_SERVICE_AREA",
        )


def service_area_payload(db: Database) -> dict:
    regions = list(db.col("regions").find({"is_active": True}).sort("level", 1))
    out = []
    for r in regions:
        entry = {
            "id": r["_id"],
            "code": r.get("code"),
            "name": r.get("name"),
            "level": r.get("level"),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "radius_m": r.get("radius_m"),
        }
        rb = r.get("bounds")
        if isinstance(rb, dict):
            entry["bounds"] = rb
        out.append(entry)
    muni = municipality_region(db)
    bounds = None
    if muni:
        mb = muni.get("bounds")
        if isinstance(mb, dict):
            center = bounds_center(mb)
            bounds = dict(mb)
            if center:
                bounds["center"] = {"lat": center[0], "lng": center[1]}
        elif muni.get("latitude") is not None and muni.get("longitude") is not None:
            bounds = {
                "center": {"lat": float(muni["latitude"]), "lng": float(muni["longitude"])},
                "radius_m": float(muni.get("radius_m") or 40000),
            }
    return {"regions": out, "municipality_bounds": bounds}
