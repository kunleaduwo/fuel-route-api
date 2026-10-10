from dataclasses import dataclass
from functools import lru_cache

import csv
import numpy as np
from django.conf import settings


@dataclass
class Stations:
    name: list
    address: list
    city: list
    state: list
    price: np.ndarray
    lat: np.ndarray
    lng: np.ndarray



@lru_cache(maxsize=1)
def load_stations() -> Stations:
    """Loaded once per process, so requests never touch the disk or a database."""
    rows = list(csv.DictReader(open(settings.STATIONS_FILE, newline="", encoding="utf-8")))
    return Stations(
        name=[r["name"] for r in rows],
        address=[r["address"] for r in rows],
        city=[r["city"] for r in rows],
        state=[r["state"] for r in rows],
        price=np.array([float(r["price"]) for r in rows]),
        lat=np.array([float(r["lat"]) for r in rows]),
        lng=np.array([float(r["lng"]) for r in rows]),
    )
