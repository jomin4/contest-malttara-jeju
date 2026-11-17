import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import I, S, goal, mock_conn
from malttara.tools.places import (analyze_tourism, check_data_quality, get_region_data,
                                   get_region_data_all, score_places, search_places)


class PlacesTest(unittest.TestCase):
    def setUp(self):
        self.conn, _ = mock_conn()

    def tearDown(self):
        self.conn.close()

    def ids(self, ps):
        return [p["place_id"] for p in ps]

    def test_interest_drives_rank(self):
        sea = score_places(self.conn, goal(interests=["바다"]), S, I)
        self.assertIn(sea[0]["category"], I["interests"]["바다"]["categories"])
        self.assertEqual(sea[0]["interest"], 1.0)

    def test_quiet_pref_changes_weights_and_order(self):
        base = self.ids(score_places(self.conn, goal(interests=["바다"]), S, I))
        quiet = self.ids(score_places(self.conn, goal(interests=["바다"], quiet_pref=True), S, I))
        self.assertNotEqual(base, quiet)

    def test_missing_indicator_is_neutral_and_flagged(self):
        ps = score_places(self.conn, goal(), S, I)
        nearby_missing = [p for p in ps if p["indicators"]["nearby"]["missing"]]
        region_missing = [p for p in ps if p["indicators"]["region"]["missing"]]
        self.assertTrue(nearby_missing and region_missing)
        self.assertEqual(nearby_missing[0]["quiet"], 0.5)
        self.assertIsNone(nearby_missing[0]["indicators"]["nearby"]["quiet_count"])
        self.assertEqual(region_missing[0]["spread"], 0.5)

    def test_no_interest_means_all_one_and_tie_by_id(self):
        ps = score_places(self.conn, goal(), S, I)
        self.assertTrue(all(p["interest"] == 1.0 for p in ps))
        for i in range(len(ps) - 1):
            a, b = ps[i], ps[i + 1]
            self.assertTrue(a["score"] > b["score"] or (a["score"] == b["score"] and a["place_id"] < b["place_id"]))

    def test_same_input_same_ranking(self):
        a = score_places(self.conn, goal(interests=["숲"]), S, I)
        b = score_places(self.conn, goal(interests=["숲"]), S, I)
        self.assertEqual(self.ids(a), self.ids(b))

    def test_region_and_nearby_indicators_are_separate_keys(self):
        p = score_places(self.conn, goal(), S, I)[0]
        self.assertEqual(p["indicators"]["region"]["source_id"], "563")
        self.assertEqual(p["indicators"]["nearby"]["source_id"], "1208")
        self.assertEqual(p["indicators"]["nearby"]["radius_km"], 1.0)
        self.assertIn("region_name", p)

    def test_boost_caps_at_1_2(self):
        ps = score_places(self.conn, goal(interests=["바다"]), S, I, boosts={"해수욕장": 0.5})
        self.assertEqual(max(p["interest"] for p in ps), 1.2)

    def test_search_slot_separation(self):
        g = goal(interests=["바다", "음식"])
        general = search_places(self.conn, g, S, I)
        food = search_places(self.conn, g, S, I, slot="음식")
        self.assertNotIn("음식점", {p["category"] for p in general})
        self.assertEqual({p["category"] for p in food}, {"음식점"})
        west = search_places(self.conn, g, S, I, region_ids=["west"], exclude_ids={"p-mock-west-00"})
        self.assertEqual({p["region_id"] for p in west}, {"west"})
        self.assertNotIn("p-mock-west-00", self.ids(west))

    def test_region_data_and_month(self):
        d = get_region_data(self.conn, None, S)
        self.assertEqual(d["source_id"], "563")
        self.assertTrue(all("region_id" in it and "pct" in it for it in d["items"]))
        d11 = get_region_data(self.conn, 11, S)
        self.assertNotEqual(d["items"][0]["visit_ratio"], d11["items"][0]["visit_ratio"])
        allm = get_region_data_all(self.conn, S)
        self.assertEqual(sorted(allm["months"], key=int), [str(m) for m in range(1, 13)])
        self.assertEqual(allm["months"]["1"], [])   # 모의 데이터는 11월만 있음

    def test_quality_and_tourism(self):
        ps = score_places(self.conn, goal(), S, I)
        q = check_data_quality(ps)
        self.assertGreater(q["no_nearby_indicator"], 0)
        self.assertGreater(q["no_region_indicator"], 0)
        t = analyze_tourism(self.conn, [p["place_id"] for p in ps])
        self.assertEqual(set(t), {"p-mock-city-03", "p-mock-east-01"})
        self.assertEqual(t["p-mock-city-03"]["source_ids"], ["189", "190"])


if __name__ == "__main__":
    unittest.main()
