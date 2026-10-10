
import csv

from django.conf import settings
from django.core.management.base import BaseCommand

from planner.geo import _load_cities, norm_city


class Command(BaseCommand):
    help = "Build data/stations.csv (deduplicated, geocoded) from the raw fuel price file."

    def handle(self, *args, **opts):
        cities, _ = _load_cities()
        best, skipped = {}, 0
        with open(settings.RAW_FUEL_FILE, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                state = row["State"].strip()
                coords = cities.get((norm_city(row["City"]), state))
                if not coords:
                    skipped += 1  # Canadian stops or cities we can't match
                    continue
                # The file has duplicate stops; keep the cheapest price per ID + address.
                key = (row["OPIS Truckstop ID"], row["Address"].strip())
                price = float(row["Retail Price"])
                if key not in best or price < best[key]["price"]:
                    best[key] = {
                        "name": row["Truckstop Name"].strip(), "address": row["Address"].strip(),
                        "city": row["City"].strip(), "state": state, "price": round(price, 4),
                        "lat": coords[0], "lng": coords[1],
                    }
        with open(settings.STATIONS_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["name", "address", "city", "state", "price", "lat", "lng"])
            w.writeheader()
            w.writerows(best.values())
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(best)} stations ({skipped} rows skipped)."))
