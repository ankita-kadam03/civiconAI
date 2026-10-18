from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6_371_000
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    chord = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lng / 2) ** 2
    return 2 * radius * asin(sqrt(chord))


def bounds_center(bounds: dict) -> tuple[float, float] | None:
    try:
        min_lat = float(bounds["min_lat"])
        max_lat = float(bounds["max_lat"])
        min_lng = float(bounds["min_lng"])
        max_lng = float(bounds["max_lng"])
    except (KeyError, TypeError, ValueError):
        return None
    return (min_lat + max_lat) / 2, (min_lng + max_lng) / 2


def point_in_bounds(lat: float, lng: float, bounds: dict) -> bool:
    try:
        min_lat = float(bounds["min_lat"])
        max_lat = float(bounds["max_lat"])
        min_lng = float(bounds["min_lng"])
        max_lng = float(bounds["max_lng"])
    except (KeyError, TypeError, ValueError):
        return False
    return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng


def encode_geohash(lat: float, lng: float, precision: int = 9) -> str:
    lat_range = [-90.0, 90.0]
    lng_range = [-180.0, 180.0]
    bits = (16, 8, 4, 2, 1)
    chars: list[str] = []
    bit = 0
    value = 0
    even = True
    while len(chars) < precision:
        if even:
            mid = (lng_range[0] + lng_range[1]) / 2
            if lng >= mid:
                value |= bits[bit]
                lng_range[0] = mid
            else:
                lng_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                value |= bits[bit]
                lat_range[0] = mid
            else:
                lat_range[1] = mid
        even = not even
        if bit < 4:
            bit += 1
        else:
            chars.append(_BASE32[value])
            bit = 0
            value = 0
    return "".join(chars)
