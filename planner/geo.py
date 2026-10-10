"""Offline 'geocoding': turns "Dallas, TX" (or "32.77,-96.79") into coordinates.

Doing this locally means the only external call per request is the routing call.
"""
import csv
import re
from functools import lru_cache
from django.conf import settings


def norm_city(name: str) -> str:
    s = str(name).lower().replace(".", "")
    s = re.sub(r"\bsaint\b", "st", s)
    s = re.sub(r"\bft\b", "fort", s)
    s = re.sub(r"\bmt\b", "mount", s)
    s = re.sub(r"[^a-z ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=1)
def _load_cities():
    by_key, state_names = {}, {}
    with open(settings.CITIES_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (norm_city(row["city"]), row["state"])
            by_key.setdefault(key, (float(row["lat"]), float(row["lng"])))
            state_names[row["state_name"].lower()] = row["state"]
    return by_key, state_names


def parse_location(text: str):
    """Return (lat, lng, label). Raises ValueError with a helpful message."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Location is empty.")

    m = re.fullmatch(r"(-?\d+(\.\d+)?)\s*,\s*(-?\d+(\.\d+)?)", text)
    if m:
        lat, lng = float(m.group(1)), float(m.group(3))
        if not (17 <= lat <= 72 and -180 <= lng <= -65):
            raise ValueError(f"Coordinates '{text}' are outside the USA.")
        return lat, lng, text

    cities, state_names = _load_cities()
    if "," in text:
        city, state = [p.strip() for p in text.rsplit(",", 1)]
        splits = [(city, state)]
    else:
        tokens = text.split()
        splits = [(" ".join(tokens[:-k]), " ".join(tokens[-k:])) for k in (1, 2, 3) if len(tokens) > k]

    for city, state in splits:
        code = state.upper() if len(state) == 2 else state_names.get(state.lower())
        if code and (norm_city(city), code) in cities:
            lat, lng = cities[(norm_city(city), code)]
            return lat, lng, f"{city.title()}, {code}"
    raise ValueError(f"Could not find '{text}'. Use 'City, ST' (e.g. 'Dallas, TX') or 'lat,lng'.")
