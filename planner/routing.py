"""One call to a free routing API per (start, finish) pair; results are cached."""
import numpy as np
import requests
from django.conf import settings
from django.core.cache import cache

METERS_PER_MILE = 1609.344


class RoutingError(Exception):
    pass


def _ors(start, finish):
    if not settings.ORS_API_KEY:
        raise RoutingError("ORS_API_KEY is not set. Add it to your .env file.")
    r = requests.post(
        "https://api.openrouteservice.org/v2/directions/driving-car/geojson",
        headers={"Authorization": settings.ORS_API_KEY},
        # radiuses -1 = snap to the nearest road at any distance (city centres are rarely on a road)
        json={"coordinates": [[start[1], start[0]], [finish[1], finish[0]]], "radiuses": [-1, -1]},
        timeout=30,
    )
    if r.status_code != 200:
        raise RoutingError(f"Routing API error {r.status_code}: {r.text[:200]}")
    feat = r.json()["features"][0]
    return feat["geometry"]["coordinates"], feat["properties"]["summary"]




def _osrm(start, finish):
    url = f"{settings.OSRM_BASE_URL}/route/v1/driving/{start[1]},{start[0]};{finish[1]},{finish[0]}"
    r = requests.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=30)
    if r.status_code != 200:
        raise RoutingError(f"Routing API error {r.status_code}: {r.text[:200]}")
    route = r.json()["routes"][0]
    return route["geometry"]["coordinates"], route


def get_route(start, finish):
    """Return dict(coords=ndarray[N,2] of (lat,lng), miles, hours)."""
    key = f"route:{start[0]:.3f},{start[1]:.3f}:{finish[0]:.3f},{finish[1]:.3f}"
    hit = cache.get(key)
    if hit:
        return hit
    try:
        fn = _ors if settings.ROUTING_PROVIDER == "ors" else _osrm
        lnglat, summary = fn(start, finish)
    except requests.RequestException as exc:
        raise RoutingError(f"Could not reach routing API: {exc}") from exc
    arr = np.asarray(lnglat, dtype=float)[:, :2]
    route = {
        "coords": arr[:, ::-1].copy(),                 # -> (lat, lng)
        "miles": summary["distance"] / METERS_PER_MILE,
        "hours": summary["duration"] / 3600,
    }
    cache.set(key, route, 60 * 60 * 24)
    return route
