"""직접 고르기(B 트랙 요청): GET /api/places 목록, Batch B picks 반영."""
import json
import os
import sys
import unittest
import urllib.parse
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from helpers import I, R, S, goal, mock_conn
from malttara.agent.batch_a import run_batch_a
from malttara.agent.batch_b import run_batch_b
from malttara.agent.llm import LLMClient
from malttara.agent.state import BatchState
from malttara.tools.places import score_places
from test_server import ServerTest

NO_LLM = LLMClient(None, None, None, 5)


class PicksBatchTest(unittest.TestCase):
    def setUp(self):
        self.conn, _ = mock_conn()

    def tearDown(self):
        self.conn.close()

    def run_ab(self, g, picks):
        a = run_batch_a(self.conn, g, False, NO_LLM, S, I, R, BatchState("A", datetime(2026, 11, 18, 10, 0, 0)))
        st = BatchState("B", datetime(2026, 11, 18, 10, 5, 0), prev_batch_id=a["batch_id"])
        return a, run_batch_b(self.conn, a["batch_id"], NO_LLM, S, I, R, st, picks=picks)

    def outside(self, a, g, region_id):
        used = {i for d in a["itinerary"]["days"] for i in d["place_ids"]}
        return next(p for p in score_places(self.conn, g, S, I) if p["region_id"] == region_id and p["place_id"] not in used)

    def test_pick_is_in_itinerary_pinned_and_count_kept(self):
        g = goal(days=2)
        a, _ = self.run_ab(g, [])
        day1 = a["itinerary"]["days"][0]
        p = self.outside(a, g, day1["region_id"])
        _, b = self.run_ab(g, [{"place_id": p["place_id"], "day": None}])
        d1 = next(d for d in b["itinerary"]["days"] if d["day"] == 1)
        self.assertIn(p["place_id"], d1["place_ids"])                       # 같은 권역 날에 들어감
        self.assertEqual(len(d1["place_ids"]), len(day1["place_ids"]))      # 하루 장소 수 유지(교체)
        reasons = {x["reason"] for x in b["diff"]}
        self.assertTrue(any("직접 고" in r for r in reasons))
        self.assertIn(p["place_id"], b["places"])

    def test_unknown_pick_ignored(self):
        _, b = self.run_ab(goal(days=2), [{"place_id": "nope", "day": 1}])
        self.assertNotIn("nope", [i for d in b["itinerary"]["days"] for i in d["place_ids"]])


class PlacesApiTest(ServerTest):
    def test_places_list_filters_and_validation(self):
        r = self.get("/api/places?limit=5")
        self.assertGreater(r["total"], 0)
        self.assertLessEqual(len(r["items"]), 5)
        self.assertIn("indicators", r["items"][0])
        rid = r["items"][0]["region_id"]
        f = self.get("/api/places?" + urllib.parse.urlencode({"region": rid, "sort": "name"}))
        self.assertTrue(all(x["region_id"] == rid for x in f["items"]))
        names = [x["name"] for x in f["items"]]
        self.assertEqual(names, sorted(names))
        q = self.get("/api/places?" + urllib.parse.urlencode({"q": r["items"][0]["name"][:2]}))
        self.assertGreater(q["total"], 0)
        self.assertEqual(self.raw("/api/places?sort=bad").status, 400)
        self.assertEqual(self.raw("/api/places?batch_id=X-0").status, 404)
        self.assertIn("picks", self.get("/api/config")["supports"])

    def test_batch_b_rejects_bad_picks(self):
        a = self.post("/api/batch/a", {"goal": {"days": 1, "interests": []}})
        self.poll(a["batch_id"])
        bad = self.raw("/api/batch/b", json.dumps({"prev_batch_id": a["batch_id"], "picks": [{"day": 1}]}).encode())
        self.assertEqual(bad.status, 400)


del ServerTest   # 같은 테스트를 두 번 돌리지 않게

if __name__ == "__main__":
    unittest.main()
