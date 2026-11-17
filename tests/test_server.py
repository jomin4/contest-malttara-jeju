import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from malttara.etl.mock_data import build_mock_db, build_mock_map
from malttara.server.app import make_server

GOAL = {"nights": 1, "days": 2, "pace": "보통", "interests": ["바다"], "quiet_pref": False, "transport": None,
        "companion": None, "origin": None, "month": None, "evidence": {}}


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = tempfile.mkdtemp()
        cls.static = os.path.join(d, "dist")
        os.makedirs(os.path.join(cls.static, "assets"))
        with open(os.path.join(cls.static, "index.html"), "w", encoding="utf-8") as f:
            f.write("<!doctype html><title>말따라 제주</title>")
        with open(os.path.join(cls.static, "assets", "app.js"), "w", encoding="utf-8") as f:
            f.write("console.log(1)")
        build_mock_db(os.path.join(d, "m.sqlite"))
        build_mock_map(os.path.join(d, "map.json"))
        cls.srv = make_server(os.path.join(d, "m.sqlite"), os.path.join(d, "map.json"), cls.static, "127.0.0.1", 0, {})
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def raw(self, path, data=None):
        req = urllib.request.Request(self.base + path, data=data, method="POST" if data is not None else "GET",
                                     headers={"Content-Type": "application/json"})
        try:
            return urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            return e

    def get(self, path):
        return json.loads(self.raw(path).read())

    def post(self, path, body):
        return json.loads(self.raw(path, json.dumps(body).encode()).read())

    def poll(self, bid):
        seen = []
        for _ in range(80):
            r = self.get(f"/api/batch/{bid}/events?after={len(seen)}")
            seen += r["events"]
            if r["done"]:
                r["events"] = seen
                return r
            time.sleep(0.25)
        self.fail("batch did not finish")

    def test_health_config(self):
        h = self.get("/api/health")
        self.assertTrue(h["ok"])
        self.assertFalse(h["llm_available"])
        self.assertEqual(h["data_version"], "mock")
        c = self.get("/api/config")
        self.assertEqual(c["max_days"], 7)
        self.assertEqual([r["region_id"] for r in c["regions"]], ["city", "west", "east", "south"])
        self.assertIn({"key": "음식", "slot": True}, c["interests"])

    def test_parse(self):
        r = self.post("/api/goal/parse", {"text": "2박 3일 바다 여유롭게"})
        self.assertEqual((r["goal"]["days"], r["missing"], r["actor"]), (3, [], "rule"))
        self.assertEqual(self.post("/api/goal/parse", {"text": "바다"})["missing"], ["days"])

    def test_bad_json_and_missing_key_are_400(self):
        r = self.raw("/api/goal/parse", b"{not json")
        self.assertEqual(r.status, 400)
        self.assertIn("error", json.loads(r.read()))
        self.assertEqual(self.raw("/api/goal/parse", json.dumps({}).encode()).status, 400)

    def test_batch_a_rejects_goal_without_days(self):
        r = self.raw("/api/batch/a", json.dumps({"goal": dict(GOAL, days=None, nights=None), "inject_error": False}).encode())
        self.assertEqual(r.status, 400)
        self.assertIn("기간", json.loads(r.read())["error"])

    def test_map_and_stats(self):
        m = self.get("/api/map")
        self.assertTrue(m["view_box"].startswith("0 0 "))
        self.assertTrue(m["emds"])
        self.assertEqual(len(m["regions"]), 4)
        self.assertEqual(self.get("/api/stats/emd")["source_id"], "563")
        self.assertEqual(sorted(self.get("/api/stats/emd?month=all")["months"], key=int), [str(i) for i in range(1, 13)])
        self.assertEqual(self.raw("/api/stats/emd?month=13").status, 400)

    def test_batch_a_poll_until_done_with_seq(self):
        bid = self.post("/api/batch/a", {"goal": GOAL, "inject_error": True})["batch_id"]
        r = self.poll(bid)
        self.assertIsNotNone(r["result"])
        self.assertIsNone(r["error"])
        self.assertEqual([e["seq"] for e in r["events"]], list(range(1, len(r["events"]) + 1)))
        self.assertEqual(self.get(f"/api/batch/{bid}/events?after={len(r['events'])}")["events"], [])

    def test_events_and_batch_b_and_trend_and_print(self):
        a = self.poll(self.post("/api/batch/a", {"goal": GOAL, "inject_error": False})["batch_id"])["result"]
        pid = a["itinerary"]["days"][0]["place_ids"][0]
        self.assertTrue(self.post("/api/events", {"batch_id": a["batch_id"], "place_id": pid, "type": "feedback", "value": "dislike"})["ok"])
        self.assertEqual(self.raw("/api/events", json.dumps({"batch_id": a["batch_id"], "place_id": pid, "type": "x", "value": None}).encode()).status, 400)
        b = self.poll(self.post("/api/batch/b", {"prev_batch_id": a["batch_id"]})["batch_id"])["result"]
        self.assertEqual(b["prev_batch_id"], a["batch_id"])
        t = self.get("/api/places/p-mock-city-03/trend")
        self.assertEqual(t["source_ids"], ["189", "190"])
        self.assertTrue(t["series"])
        self.assertEqual(self.get("/api/places/p-mock-west-00/trend")["series"], [])
        r = self.raw("/api/print/" + b["batch_id"])
        html = r.read().decode()
        self.assertIn("<html", html)
        self.assertNotIn("http", html)

    def test_unknown_batch_404(self):
        self.assertEqual(self.raw("/api/batch/A-0000-000000/events?after=0").status, 404)
        self.assertEqual(self.raw("/api/batch/b", json.dumps({"prev_batch_id": "A-0000-000000"}).encode()).status, 404)
        self.assertEqual(self.raw("/api/print/A-0000-000000").status, 404)
        self.assertEqual(self.raw("/api/nope").status, 404)

    def test_static_and_mime_and_fallback(self):
        r = self.raw("/assets/app.js")
        self.assertEqual(r.headers["Content-Type"], "text/javascript")
        idx = self.raw("/step-3")
        self.assertEqual(idx.headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("말따라 제주", idx.read().decode())

    def test_static_traversal_blocked(self):
        for p in ("/../config/settings.json", "/..%2F..%2Fconfig%2Fsettings.json", "/assets/../../m.sqlite"):
            self.assertNotIn(b'"weights"', self.raw(p).read())


if __name__ == "__main__":
    unittest.main()
