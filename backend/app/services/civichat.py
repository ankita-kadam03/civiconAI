from __future__ import annotations

from app.db import Database
from app.domain.geo import distance_m


def civichat_reply(
    message: str,
    db: Database,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> str:
    text = (message or "").strip().lower()
    if not text:
        return "Ask me how to navigate Civicon or about recent public reports near you."

    nav_hints = (
        ("report", "Open **Report an issue** from the menu or go to `/app/report` to file a new civic report."),
        ("my report", "Open **My reports** (`/app/reports`) to see everything you submitted."),
        ("track", "Open **My reports** and tap a CIV reference to see the timeline."),
        ("profile", "Open **My account** (`/app/profile`) to update your display name and locality."),
        ("explore", "Open **Explore** (`/explore`) to browse public incidents on the map or list."),
        ("notification", "Tap the bell icon in the header for updates (`/app/notifications`)."),
        ("sign in", "Use **Sign in** (`/login`) or **Sign up** (`/signup`) from the home page."),
        ("home", "The home page (`/`) explains how Civicon works and shows public explore."),
        ("officer", "Officers use the L1 board (`/officer`) after signing in with an officer account."),
        ("admin", "Administrators use the admin dashboard (`/admin`)."),
    )
    for key, reply in nav_hints:
        if key in text:
            return reply.replace("**", "")

    wants_nearby = any(
        phrase in text
        for phrase in (
            "near me",
            "nearby",
            "around me",
            "latest report",
            "latest issue",
            "recent report",
            "recent issue",
            "what's open",
            "whats open",
        )
    )
    if wants_nearby:
        return _nearby_public_reports(db, latitude, longitude)

    if text in {"hi", "hello", "hey", "help", "thanks", "thank you"} or len(text.split()) <= 2 and "report" not in text:
        return "I can't help with that. I'm CiviChat — I only help with Civicon screen navigation and fetching recent public reports near your location."

    return (
        "I can't help with that. I'm CiviChat — I only help with Civicon UI navigation "
        "(try: \"how do I report\", \"my reports\", \"explore\") and recent public issues near you "
        "(try: \"latest reports near me\")."
    )


def _nearby_public_reports(db: Database, lat: float | None, lng: float | None) -> str:
    docs = list(db.col("complaints").find({"is_public": True}).sort("created_at", -1))
    if lat is not None and lng is not None:
        ranked: list[tuple[float, dict]] = []
        for doc in docs:
            dlat, dlng = doc.get("latitude"), doc.get("longitude")
            if dlat is None or dlng is None:
                continue
            ranked.append((distance_m(lat, lng, float(dlat), float(dlng)), doc))
        ranked.sort(key=lambda x: x[0])
        docs = [d for _, d in ranked[:5]] or docs[:5]
    else:
        docs = docs[:5]

    if not docs:
        return "No public reports are listed yet. You can be the first — open Report an issue from the menu."

    lines = ["Recent public reports" + (" near you" if lat is not None else "") + ":"]
    for doc in docs:
        ref = doc.get("reference") or "—"
        title = (doc.get("title") or "Untitled")[:60]
        locality = (doc.get("locality") or "").strip()
        extra = f" · {locality}" if locality else ""
        lines.append(f"• {ref}: {title}{extra} — open Explore and search {ref}.")
    return "\n".join(lines)
