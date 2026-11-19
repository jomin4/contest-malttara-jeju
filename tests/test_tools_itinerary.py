import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import I, R, S, goal, mock_conn
from malttara.regions import region_order
from malttara.tools.itinerary import create_itinerary, order_nearest, pace_k, resolve_origin
from malttara.tools.places import score_places, search_places
from malttara.tools.route import calculate_route


class ItineraryTest(unittest.TestCase):
    def setUp(self):
        self.conn, _ = mock_conn()

    def tearDown(self):
        self.conn.close()

    def make(self, g):
        scored = score_places(self.conn, g, S, I)
        self.P = {p["place_id"]: p for p in scored}
        general = search_places(self.conn, g, S, I, limit=500, scored=scored)
        slots = {k: search_places(self.conn, g, S, I, slot=k, limit=500, scored=scored)
                 for k in g["interests"] if I["interests"][k].get("slot")}
        return create_itinerary(general, slots, g, S, region_order=region_order(R))

    def test_pace_k(self):
        self.assertEqual(pace_k(goal(pace="여유롭게"), S), 3)
        self.assertEqual(pace_k(goal(pace=None), S), 4)

    def test_k_per_pace_and_one_region_per_day(self):
        it = self.make(goal(days=2, pace="여유롭게"))
        self.assertEqual([d["day"] for d in it["days"]], [1, 2])
        self.assertTrue(all(len(d["place_ids"]) == 3 for d in it["days"]))
        for d in it["days"]:
            self.assertEqual({self.P[i]["region_id"] for i in d["place_ids"]}, {d["region_id"]})

    def test_no_duplicates_and_cycle_when_few_regions(self):
        it = self.make(goal(days=6, pace="보통"))   # 모의 권역 4개 < 6일
        ids = [i for d in it["days"] for i in d["place_ids"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(it["days"]), 6)

    def test_food_slot_one_per_day_at_cheapest_position(self):
        it = self.make(goal(days=2, pace="보통", interests=["바다", "음식"]))
        for d in it["days"]:
            cats = [self.P[i]["category"] for i in d["place_ids"]]
            self.assertEqual(cats.count("음식점"), 1)
            self.assertEqual(len(cats), 4)

    def test_insert_best_minimizes_added_distance(self):
        from malttara.tools.itinerary import _insert_best
        pts = {"a": {"lat": 33.0, "lon": 126.0}, "b": {"lat": 33.0, "lon": 126.2}, "f": {"lat": 33.0, "lon": 126.1},
               "far": {"lat": 33.0, "lon": 126.5}}
        self.assertEqual(_insert_best(["a", "b"], "f", pts), ["a", "f", "b"])
        self.assertEqual(_insert_best(["a", "b"], "far", pts), ["a", "b", "far"])

    def test_food_and_cafe_slots(self):
        it = self.make(goal(days=1, pace="보통", interests=["음식", "카페"]))
        cats = [self.P[i]["category"] for i in it["days"][0]["place_ids"]]
        self.assertEqual((cats.count("음식점"), cats.count("카페"), len(cats)), (1, 1, 4))

    def test_order_nearest_from_start(self):
        pts = {"a": {"lat": 33.0, "lon": 126.0}, "b": {"lat": 33.0, "lon": 126.2}, "c": {"lat": 33.0, "lon": 126.1}}
        self.assertEqual(order_nearest(["a", "b", "c"], pts, None), ["a", "c", "b"])
        self.assertEqual(order_nearest(["a", "b", "c"], pts, (33.0, 126.25)), ["b", "c", "a"])

    def test_route_totals(self):
        pts = {"a": {"lat": 33.0, "lon": 126.0}, "b": {"lat": 33.0, "lon": 126.1}, "c": {"lat": 33.1, "lon": 126.1}}
        r = calculate_route({"days": [{"day": 1, "region_id": "x", "place_ids": ["a", "b", "c"]}]}, pts)
        self.assertEqual(len(r[0]["legs_km"]), 2)
        self.assertEqual(r[0]["total_km"], round(sum(r[0]["legs_km"]), 1))
        single = calculate_route({"days": [{"day": 1, "region_id": "x", "place_ids": ["a"]}]}, pts)
        self.assertEqual(single[0], {"day": 1, "legs_km": [], "total_km": 0.0})

    def test_resolve_origin(self):
        self.assertIsNotNone(resolve_origin(self.conn, "모의 해변 west-00"))
        self.assertIsNone(resolve_origin(self.conn, "없는곳"))
        self.assertIsNone(resolve_origin(self.conn, None))

    def test_empty_candidates_gives_empty_days_not_crash(self):
        it = create_itinerary([], {}, goal(days=2), S, region_order=region_order(R))
        self.assertEqual([d["place_ids"] for d in it["days"]], [[], []])


if __name__ == "__main__":
    unittest.main()


class NearDuplicateNameTest(unittest.TestCase):
    def test_three_char_name_contained_is_duplicate(self):
        from malttara.tools.itinerary import is_duplicate
        a = {"place_id": "a", "name": "한라산", "lat": 33.36, "lon": 126.53}
        b = {"place_id": "b", "name": "한라산 트레킹", "lat": 33.40, "lon": 126.60}
        self.assertTrue(is_duplicate(b, [a]))

