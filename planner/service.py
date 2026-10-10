import hashlib
import time

import numpy as np
from django.conf import settings
from django.core.cache import cache
from scipy.spatial import cKDTree

from .geo import parse_location
from .optimizer import plan_fuel_stops
from .routing import get_route
from .stations import load_stations

MILES_PER_DEG_LAT = 69.0
GRID_MILES = 0.5



def _densify(coords, total_miles):
    """Resample the route every GRID_MILES so nearest-point maths is accurate on long straights."""
    lat0 = np.radians(coords[:, 0].mean())
    xy = np.column_stack([coords[:, 1] * np.cos(lat0), coords[:, 0]]) * MILES_PER_DEG_LAT
    seg = np.hypot(*np.diff(xy, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    cum *= total_miles / cum[-1]                       # align with the API's driven distance
    grid = np.unique(np.append(np.arange(0, total_miles, GRID_MILES), total_miles))
    lat = np.interp(grid, cum, coords[:, 0])
    lng = np.interp(grid, cum, coords[:, 1])
    return grid, lat, lng, lat0


def plan_trip(start_text, finish_text):
    t0 = time.perf_counter()
    cache_key = "plan:" + hashlib.md5(f"{start_text.strip().lower()}|{finish_text.strip().lower()}".encode()).hexdigest()
    if (hit := cache.get(cache_key)):
        return {**hit, "cached": True, "elapsed_ms": round((time.perf_counter() - t0) * 1000)}

    s_lat, s_lng, s_label = parse_location(start_text)
    f_lat, f_lng, f_label = parse_location(finish_text)
    route = get_route((s_lat, s_lng), (f_lat, f_lng))          # <- the single external API call
    total = route["miles"]

    grid, r_lat, r_lng, lat0 = _densify(route["coords"], total)
    to_xy = lambda lat, lng: np.column_stack([np.asarray(lng) * np.cos(lat0), np.asarray(lat)]) * MILES_PER_DEG_LAT
    tree = cKDTree(to_xy(r_lat, r_lng))

    st = load_stations()
    offset, idx = tree.query(to_xy(st.lat, st.lng), distance_upper_bound=settings.MAX_STATION_OFFSET_MILES)
    near = np.where(idx < len(grid))[0]
    near = near[np.argsort(grid[idx[near]], kind="stable")]
    miles = grid[idx[near]]

    stops = plan_fuel_stops(list(zip(miles, st.price[near])), total, settings.VEHICLE_RANGE_MILES)

    fuel_stops, cost = [], 0.0
    for s in stops:
        k = near[s.index]
        gallons = s.miles_bought / settings.VEHICLE_MPG
        c = gallons * s.price
        cost += c
        fuel_stops.append({
            "name": st.name[k], "address": st.address[k], "city": st.city[k], "state": st.state[k],
            "lat": float(st.lat[k]), "lng": float(st.lng[k]),
            "mile_marker": round(s.mile, 1), "offset_from_route_miles": round(float(offset[k]), 1),
            "price_per_gallon": round(s.price, 3), "gallons_purchased": round(gallons, 2), "cost": round(c, 2),
        })

    step = max(1, int(1 / GRID_MILES))                         # ~1 mile resolution for the map line
    line = np.column_stack([r_lng, r_lat])[::step]
    line = np.vstack([line, [r_lng[-1], r_lat[-1]]])
    result = {
        "start": {"label": s_label, "lat": s_lat, "lng": s_lng},
        "finish": {"label": f_label, "lat": f_lat, "lng": f_lng},
        "distance_miles": round(total, 1),
        "duration_hours": round(route["hours"], 1),
        "fuel_stops": fuel_stops,
        "total_gallons_purchased": round(sum(f["gallons_purchased"] for f in fuel_stops), 2),
        "total_fuel_cost": round(cost, 2),
        "assumptions": {
            "vehicle_range_miles": settings.VEHICLE_RANGE_MILES, "mpg": settings.VEHICLE_MPG,
            "starts_with_full_tank": True, "cost_covers": "fuel bought at the stops listed",
            "max_station_offset_miles": settings.MAX_STATION_OFFSET_MILES,
        },
        "route_geojson": {"type": "Feature", "properties": {},
                          "geometry": {"type": "LineString", "coordinates": np.round(line, 5).tolist()}},
        "routing_api_calls": 1,
    }
    cache.set(cache_key, result, 60 * 60)
    return {**result, "cached": False, "elapsed_ms": round((time.perf_counter() - t0) * 1000)}
