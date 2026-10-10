from unittest.mock import patch

import numpy as np
from django.core.cache import cache
from django.test import TestCase

from .geo import parse_location
from .optimizer import NoFeasiblePlan, plan_fuel_stops


class OptimizerTests(TestCase):
    def test_short_trip_needs_no_stops(self):
        self.assertEqual(plan_fuel_stops([(100, 3.0)], 300), [])

    def test_skips_pricier_station_and_fills_at_cheapest_in_range(self):
        stops = plan_fuel_stops([(300, 4.0), (450, 3.0)], 800)
        self.assertEqual([s.price for s in stops], [3.0])
        self.assertAlmostEqual(stops[0].miles_bought, 300)   # arrives with 50 mi left, needs 350 to finish

    def test_buys_only_enough_to_reach_cheaper_station(self):
        stops = plan_fuel_stops([(300, 3.0), (600, 2.5)], 1000)
        self.assertEqual([s.price for s in stops], [3.0, 2.5])
        self.assertAlmostEqual(stops[0].miles_bought, 100)   # arrives with 200 mi left, needs 300 to reach the cheap stop
        self.assertAlmostEqual(stops[1].miles_bought, 400)

    def test_gap_too_large_raises(self):
        with self.assertRaises(NoFeasiblePlan):
            plan_fuel_stops([(100, 3.0)], 900)


class GeoTests(TestCase):
    def test_city_state(self):
        self.assertEqual(parse_location("Dallas, TX")[2], "Dallas, TX")
        self.assertEqual(parse_location("new york ny")[2], "New York, NY")
        self.assertEqual(parse_location("Chicago, Illinois")[2], "Chicago, IL")

    def test_bad_location(self):
        with self.assertRaises(ValueError):
            parse_location("Lagos, Nigeria")


def fake_route(start, finish):
    # straight-ish line, ~2,450 miles
    lat = np.linspace(start[0], finish[0], 400)
    lng = np.linspace(start[1], finish[1], 400)
    return {"coords": np.column_stack([lat, lng]), "miles": 2450.0, "hours": 37.0}


class ApiTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("planner.service.get_route", side_effect=fake_route)
    def test_route_endpoint(self, mock_route):
        r = self.client.get("/api/route/", {"start": "Los Angeles, CA", "finish": "New York, NY"})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(mock_route.call_count, 1)
        self.assertGreaterEqual(len(d["fuel_stops"]), 4)
        self.assertAlmostEqual(sum(f["cost"] for f in d["fuel_stops"]), d["total_fuel_cost"], delta=0.1)
        marks = [f["mile_marker"] for f in d["fuel_stops"]]
        self.assertEqual(marks, sorted(marks))
        # second identical request is served from cache -> no extra routing call
        self.client.get("/api/route/", {"start": "Los Angeles, CA", "finish": "New York, NY"})
        self.assertEqual(mock_route.call_count, 1)

    def test_validation(self):
        self.assertEqual(self.client.get("/api/route/").status_code, 400)
        r = self.client.get("/api/route/", {"start": "Nowhere", "finish": "Dallas, TX"})
        self.assertEqual(r.status_code, 400)
