from __future__ import annotations

import json
import uuid
from pathlib import Path

from app.config import get_settings
from app.db import Database
from app.domain.geo import bounds_center
from app.security import hash_password, now_utc

SERVICE_AREA_JSON = Path(__file__).resolve().parent / "data" / "service_area.json"

DEPARTMENTS = [
    {"code": "PWD", "name": "Public Works", "description": "Roads, footpaths, and civil infrastructure", "contact_hint": "Ward engineer"},
    {"code": "SAN", "name": "Sanitation", "description": "Garbage collection and cleanliness", "contact_hint": "Sanitation inspector"},
    {"code": "WTR", "name": "Water Supply", "description": "Leakage, shortage, and quality", "contact_hint": "Water duty officer"},
    {"code": "ELC", "name": "Street Lighting", "description": "Streetlights and electrical fittings", "contact_hint": "Electrical subdivision"},
    {"code": "TRF", "name": "Traffic Engineering", "description": "Signs, signals, and junctions", "contact_hint": "Traffic cell"},
    {"code": "PRK", "name": "Parks & Gardens", "description": "Parks, playgrounds, and public spaces", "contact_hint": "Garden superintendent"},
    {"code": "GEN", "name": "General Administration", "description": "Uncategorised civic issues", "contact_hint": "Municipal helpdesk"},
]

CATEGORIES = [
    {"slug": "potholes", "name": "Potholes & damaged roads", "icon": "road", "department_code": "PWD", "review_hours": 24, "resolve_hours": 168},
    {"slug": "garbage", "name": "Garbage & sanitation", "icon": "trash-2", "department_code": "SAN", "review_hours": 12, "resolve_hours": 72},
    {"slug": "water", "name": "Water leakage & supply", "icon": "droplets", "department_code": "WTR", "review_hours": 8, "resolve_hours": 48},
    {"slug": "drainage", "name": "Blocked drainage & sewage", "icon": "waves", "department_code": "PWD", "review_hours": 8, "resolve_hours": 72},
    {"slug": "streetlights", "name": "Broken streetlights", "icon": "lamp", "department_code": "ELC", "review_hours": 24, "resolve_hours": 96},
    {"slug": "traffic-signs", "name": "Damaged traffic signs", "icon": "signpost", "department_code": "TRF", "review_hours": 24, "resolve_hours": 120},
    {"slug": "parks", "name": "Parks & public spaces", "icon": "trees", "department_code": "PRK", "review_hours": 48, "resolve_hours": 240},
    {"slug": "infrastructure", "name": "Public infrastructure damage", "icon": "building-2", "department_code": "PWD", "review_hours": 24, "resolve_hours": 168},
    {"slug": "other", "name": "Other civic problems", "icon": "map-pin", "department_code": "GEN", "review_hours": 24, "resolve_hours": 168},
    {"slug": "electrical", "name": "Live wires & electrical hazards", "icon": "zap", "department_code": "ELC", "review_hours": 1, "resolve_hours": 8},
    {"slug": "flooding", "name": "Flooding into homes or roads", "icon": "waves", "department_code": "PWD", "review_hours": 2, "resolve_hours": 24},
]

CATEGORY_DESCRIPTIONS = {
    "potholes": "Broken carriageways, craters and unsafe road edges.",
    "garbage": "Overflowing bins, dumping and unclean public corners.",
    "water": "Leaks, shortage and unsafe standing water.",
    "drainage": "Blocked drains, sewage overflow and waterlogging.",
    "streetlights": "Dark stretches and failed lamps after dusk.",
    "traffic-signs": "Missing or damaged signs and signals.",
    "parks": "Play equipment, greenery and public seating.",
    "infrastructure": "Footpaths, railings, walls and civic assets.",
    "other": "Anything else that needs a civic desk.",
    "electrical": "Exposed wiring, live cables and shock risk.",
    "flooding": "Water entering homes, shops or main roads.",
}


def _id() -> str:
    return uuid.uuid4().hex


def _load_service_area_spec() -> dict | None:
    if not SERVICE_AREA_JSON.is_file():
        return None
    try:
        return json.loads(SERVICE_AREA_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _region_doc(
    *,
    rid: str,
    code: str,
    name: str,
    level: int,
    parent_id: str | None,
    bounds: dict,
    state: str | None,
    settings,
    now,
) -> dict:
    center = bounds_center(bounds)
    lat, lng = center if center else (None, None)
    doc = {
        "_id": rid,
        "code": code,
        "name": name,
        "level": level,
        "parent_id": parent_id,
        "latitude": lat,
        "longitude": lng,
        "bounds": bounds,
        "google_cloud_location": settings.google_cloud_location,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    if state:
        doc["state"] = state
    return doc


def _seed_regions_from_json(db: Database, settings, data: dict) -> dict[str, dict]:
    now = now_utc()
    state = data.get("state")
    by_code: dict[str, dict] = {}
    for district_spec in data.get("districts") or []:
        d_bounds = district_spec.get("bounds") or {}
        district_id: str | None = None
        district_doc: dict | None = None
        for muni_spec in district_spec.get("municipalities") or []:
            muni_id = _id()
            m_bounds = muni_spec.get("bounds") or {}
            muni_name = muni_spec.get("name") or settings.service_area_name or "Municipal service area"
            muni_doc = _region_doc(
                rid=muni_id,
                code=muni_spec.get("id") or settings.service_area_code or "municipality",
                name=muni_name,
                level=3,
                parent_id=None,
                bounds=m_bounds,
                state=state,
                settings=settings,
                now=now,
            )
            db.col("regions").insert_one(muni_doc)
            by_code[muni_doc["code"]] = muni_doc

            if district_doc is None:
                district_id = _id()
                district_doc = _region_doc(
                    rid=district_id,
                    code=district_spec.get("id") or "district",
                    name=district_spec.get("name") or "District",
                    level=2,
                    parent_id=muni_id,
                    bounds=d_bounds,
                    state=state,
                    settings=settings,
                    now=now,
                )
                db.col("regions").insert_one(district_doc)
                by_code[district_doc["code"]] = district_doc

            for ward_spec in muni_spec.get("wards") or []:
                ward_id = _id()
                w_bounds = ward_spec.get("bounds") or {}
                ward_doc = _region_doc(
                    rid=ward_id,
                    code=ward_spec.get("id") or _id(),
                    name=ward_spec.get("name") or "Ward",
                    level=1,
                    parent_id=district_id or muni_id,
                    bounds=w_bounds,
                    state=state,
                    settings=settings,
                    now=now,
                )
                db.col("regions").insert_one(ward_doc)
                by_code[ward_doc["code"]] = ward_doc
    return by_code


def _seed_regions_legacy(db: Database, settings) -> dict[str, dict]:
    center = settings.map_center
    if not center:
        return {}
    lat0, lng0 = center
    now = now_utc()
    specs = [
        {
            "code": "municipality",
            "name": settings.service_area_name or "Municipal service area",
            "level": 3,
            "parent_id": None,
            "latitude": lat0,
            "longitude": lng0,
            "radius_m": settings.region_l3_radius_m,
        },
        {
            "code": "district",
            "name": "Regional district (L2)",
            "level": 2,
            "parent_id": None,
            "latitude": lat0,
            "longitude": lng0,
            "radius_m": settings.region_l2_radius_m,
        },
        {
            "code": "ward_north",
            "name": "Ward North (L1)",
            "level": 1,
            "parent_id": None,
            "latitude": lat0 + settings.region_l1_a_lat_offset,
            "longitude": lng0 + settings.region_l1_a_lng_offset,
            "radius_m": settings.region_l1_radius_m,
        },
        {
            "code": "ward_south",
            "name": "Ward South (L1)",
            "level": 1,
            "parent_id": None,
            "latitude": lat0 + settings.region_l1_b_lat_offset,
            "longitude": lng0 + settings.region_l1_b_lng_offset,
            "radius_m": settings.region_l1_radius_m,
        },
    ]
    by_code: dict[str, dict] = {}
    muni_id = _id()
    for spec in specs:
        rid = muni_id if spec["code"] == "municipality" else _id()
        if spec["code"] == "municipality":
            muni_id = rid
        parent = muni_id if spec["level"] < 3 else None
        if spec["code"] == "district":
            parent = muni_id
        if spec["code"].startswith("ward"):
            parent = None
        doc = {
            "_id": rid,
            "code": spec["code"],
            "name": spec["name"],
            "level": spec["level"],
            "parent_id": parent if spec["code"] != "municipality" else None,
            "latitude": spec["latitude"],
            "longitude": spec["longitude"],
            "radius_m": spec["radius_m"],
            "google_cloud_location": settings.google_cloud_location,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        db.col("regions").insert_one(doc)
        by_code[spec["code"]] = doc
    district = by_code.get("district")
    muni = by_code.get("municipality")
    if district and muni:
        db.col("regions").update_one({"_id": district["_id"]}, {"$set": {"parent_id": muni["_id"]}})
        district["parent_id"] = muni["_id"]
    for code in ("ward_north", "ward_south"):
        ward = by_code.get(code)
        if ward and district:
            db.col("regions").update_one({"_id": ward["_id"]}, {"$set": {"parent_id": district["_id"]}})
            ward["parent_id"] = district["_id"]
    return by_code


def _seed_regions(db: Database, settings) -> dict[str, dict]:
    if db.col("regions").count_documents({}) > 0:
        by_code = {r["code"]: r for r in db.col("regions").find({})}
        return by_code
    area = _load_service_area_spec()
    if area and area.get("districts"):
        return _seed_regions_from_json(db, settings, area)
    return _seed_regions_legacy(db, settings)


def _bootstrap_region_refs(db: Database, regions: dict[str, dict]) -> dict[str, dict | None]:
    def pick(*codes: str) -> dict | None:
        for code in codes:
            if code in regions:
                return regions[code]
        for code in codes:
            doc = db.col("regions").find_one({"code": code})
            if doc:
                return doc
        return None

    muni = (
        pick("tambaram", "municipality")
        or db.col("regions").find_one({"level": 3, "is_active": True})
        or db.col("regions").find_one({"code": "municipality"})
    )
    return {
        "ward_n": pick("old-pallavaram-area-a", "ward_north"),
        "ward_s": pick("old-pallavaram-area-b", "ward_south"),
        "district": pick("chengalpattu", "district"),
        "muni": muni,
    }


def _bootstrap_home_coords(region: dict | None, muni: dict | None) -> tuple[float | None, float | None]:
    if not region:
        return None, None
    from app.services.regions import point_in_region

    lat, lng = region.get("latitude"), region.get("longitude")
    if lat is None or lng is None:
        return None, None
    if muni and not point_in_region(float(lat), float(lng), muni):
        lat, lng = muni.get("latitude"), muni.get("longitude")
    return lat, lng


def resync_regions_from_service_area(db: Database, settings) -> dict[str, dict]:
    area = _load_service_area_spec()
    if not area or not area.get("districts"):
        return _seed_regions(db, settings)
    db.col("regions").delete_many({})
    regions = _seed_regions_from_json(db, settings, area)
    _sync_bootstrap_user_regions(db, settings, regions)
    return regions


def _sync_bootstrap_user_regions(db: Database, settings, regions: dict[str, dict]) -> None:
    if not db.col("users").find_one({"bootstrap_account": True}):
        return
    refs = _bootstrap_region_refs(db, regions)
    muni = refs["muni"]
    now = now_utc()
    updates: list[tuple[str, dict | None, int]] = [
        (settings.seed_officer_l1_a_email, refs["ward_n"], 1),
        (settings.seed_officer_l1_b_email, refs["ward_s"], 1),
        (settings.seed_officer_l2_email, refs["district"], 2),
        (settings.seed_officer_l3_email, refs["muni"], 3),
        (settings.seed_citizen_1_email, refs["muni"], 0),
        (settings.seed_citizen_2_email, refs["muni"], 0),
    ]
    for email, region, authority_level in updates:
        if not region:
            continue
        home_lat, home_lng = _bootstrap_home_coords(region, muni)
        db.col("users").update_one(
            {"email": email.lower(), "bootstrap_account": True},
            {
                "$set": {
                    "region_id": region["_id"],
                    "authority_level": authority_level,
                    "home_latitude": home_lat,
                    "home_longitude": home_lng,
                    "updated_at": now,
                }
            },
        )


def seed_if_needed(db: Database) -> None:
    settings = get_settings()
    if settings.fresh_start:
        db.reset_all()

    if settings.resync_service_area and not settings.fresh_start:
        regions = resync_regions_from_service_area(db, settings)
    else:
        regions = _seed_regions(db, settings)

    if db.col("departments").count_documents({}) == 0:
        now = now_utc()
        for dept in DEPARTMENTS:
            db.col("departments").insert_one(
                {
                    "_id": _id(),
                    **dept,
                    "created_at": now,
                    "updated_at": now,
                }
            )
    if db.col("categories").count_documents({}) == 0:
        now = now_utc()
        depts = {d["code"]: d for d in db.col("departments").find({})}
        for cat in CATEGORIES:
            dept = depts[cat["department_code"]]
            db.col("categories").insert_one(
                {
                    "_id": _id(),
                    "name": cat["name"],
                    "slug": cat["slug"],
                    "icon": cat["icon"],
                    "description": CATEGORY_DESCRIPTIONS.get(cat["slug"], cat["name"]),
                    "department_id": dept["_id"],
                    "department_code": cat["department_code"],
                    "review_hours": cat["review_hours"],
                    "resolve_hours": cat["resolve_hours"],
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
    if db.col("escalation_rules").count_documents({}) == 0:
        now = now_utc()
        db.col("escalation_rules").insert_one(
            {
                "_id": _id(),
                "category_id": None,
                "severity": None,
                "level": 1,
                "review_hours": 24,
                "resolve_hours": 168,
                "reason": "Default municipal SLA",
                "is_active": True,
                "created_at": now,
            }
        )

    if settings.seed_bootstrap_users.lower() != "yes":
        return
    if db.col("users").find_one({"bootstrap_account": True}):
        return

    password = settings.bootstrap_user_password
    if not password:
        return
    pwd_hash = hash_password(password)
    now = now_utc()
    pwd_dept = db.col("departments").find_one({"code": "PWD"})
    refs = _bootstrap_region_refs(db, regions)
    ward_n, ward_s, district, muni = refs["ward_n"], refs["ward_s"], refs["district"], refs["muni"]
    l2_home_lat, l2_home_lng = _bootstrap_home_coords(district, muni)

    def user_doc(
        email: str,
        role: str,
        *,
        region_id: str | None,
        authority_level: int,
        home_lat: float | None,
        home_lng: float | None,
    ) -> dict:
        label = role.replace("_", " ").title()
        return {
            "_id": _id(),
            "email": email.lower(),
            "display_name": label,
            "phone": "+9190000" + str(abs(hash(email)) % 10000).zfill(4),
            "role": role,
            "department_id": pwd_dept["_id"] if pwd_dept and role == "OFFICER" else None,
            "region_id": region_id,
            "authority_level": authority_level,
            "home_latitude": home_lat,
            "home_longitude": home_lng,
            "locality": label,
            "password_hash": pwd_hash,
            "is_active": True,
            "bootstrap_account": True,
            "fcm_tokens": [],
            "created_at": now,
            "updated_at": now,
        }

    accounts = [
        user_doc(
            settings.seed_officer_l1_a_email,
            "OFFICER",
            region_id=ward_n["_id"] if ward_n else None,
            authority_level=1,
            home_lat=ward_n.get("latitude") if ward_n else None,
            home_lng=ward_n.get("longitude") if ward_n else None,
        ),
        user_doc(
            settings.seed_officer_l1_b_email,
            "OFFICER",
            region_id=ward_s["_id"] if ward_s else None,
            authority_level=1,
            home_lat=ward_s.get("latitude") if ward_s else None,
            home_lng=ward_s.get("longitude") if ward_s else None,
        ),
        user_doc(
            settings.seed_officer_l2_email,
            "ADMIN_L2",
            region_id=district["_id"] if district else None,
            authority_level=2,
            home_lat=l2_home_lat,
            home_lng=l2_home_lng,
        ),
        user_doc(
            settings.seed_officer_l3_email,
            "ADMIN_L3",
            region_id=muni["_id"] if muni else None,
            authority_level=3,
            home_lat=muni.get("latitude") if muni else None,
            home_lng=muni.get("longitude") if muni else None,
        ),
        user_doc(
            settings.seed_citizen_1_email,
            "CITIZEN",
            region_id=muni["_id"] if muni else None,
            authority_level=0,
            home_lat=None,
            home_lng=None,
        ),
        user_doc(
            settings.seed_citizen_2_email,
            "CITIZEN",
            region_id=muni["_id"] if muni else None,
            authority_level=0,
            home_lat=None,
            home_lng=None,
        ),
    ]
    for doc in accounts:
        db.col("users").insert_one(doc)
