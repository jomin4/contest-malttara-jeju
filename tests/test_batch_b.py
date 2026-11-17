import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from helpers import I, R, S, goal, mock_conn
from malttara.agent.batch_a import run_batch_a
from malttara.agent.batch_b import run_batch_b
from malttara.agent.llm import LLMClient
from malttara.agent.state import BatchState
from malttara.tools.compare import compare_itineraries
from malttara.tools.feedback import analyze_feedback, load_events, record_event

NO_LLM = LLMClient(None, None, None, 5)


class BatchBTest(unittest.TestCase):
    def setUp(self):
        self.conn, _ = mock_conn()

    def tearDown(self):
        self.conn.close()

    def run_a(self, g):
        return run_batch_a(self.conn, g, False, NO_LLM, S, I, R, BatchState("A", datetime(2026, 11, 17, 10, 0, 0)))

    def run_b(self, prev):
        st = BatchState("B", datetime(2026, 11, 17, 10, 5, 0), prev_batch_id=prev)
        return run_batch_b(self.conn, prev, NO_LLM, S, I, R, st), st

    def test_must_pinned_dislike_replaced(self):
        a = self.run_a(goal(days=2))
        d1 = a["itinerary"]["days"][0]["place_ids"]
        record_event(self.conn, a["batch_id"], d1[0], "feedback", "must")
        record_event(self.conn, a["batch_id"], d1[1], "feedback", "dislike")
        b, st = self.run_b(a["batch_id"])
        new_ids = [i for d in b["itinerary"]["days"] for i in d["place_ids"]]
        self.assertIn(d1[0], new_ids)
        self.assertNotIn(d1[1], new_ids)
        ch = {x["place_id"]: x for x in b["diff"]}
        self.assertEqual(ch[d1[0]]["change"], "pin")
        self.assertEqual(ch[d1[1]]["change"], "replace")
        self.assertIn(ch[d1[1]]["replaced_by"], b["places"])        # 계약 C3
        self.assertEqual(b["prev_batch_id"], a["batch_id"])
        self.assertEqual(b["kind"], "B")
        self.assertTrue(b["batch_id"].startswith("B-"))

    def test_last_feedback_wins(self):
        a = self.run_a(goal(days=1))
        pid = a["itinerary"]["days"][0]["place_ids"][0]
        record_event(self.conn, a["batch_id"], pid, "feedback", "dislike")
        record_event(self.conn, a["batch_id"], pid, "feedback", "must")
        fb = analyze_feedback(load_events(self.conn, a["batch_id"]), a["places"])
        self.assertEqual((fb["pinned"], fb["disliked"]), ({pid}, set()))

    def test_virtual_arrival_not_counted_as_preference(self):
        fb = analyze_feedback([{"place_id": "x", "type": "virtual_arrival", "value": None}], {})
        self.assertEqual((fb["pinned"], fb["disliked"], fb["liked_categories"], fb["arrived"]), (set(), set(), {}, {"x"}))

    def test_interest_boosts_category(self):
        a = self.run_a(goal(days=1))
        pid = a["itinerary"]["days"][0]["place_ids"][0]
        record_event(self.conn, a["batch_id"], pid, "feedback", "interest")
        fb = analyze_feedback(load_events(self.conn, a["batch_id"]), a["places"])
        self.assertEqual(fb["liked_categories"], {a["places"][pid]["category"]: 1})

    def test_no_feedback_keeps_everything(self):
        a = self.run_a(goal(days=2))
        b, _ = self.run_b(a["batch_id"])
        self.assertTrue(all(x["change"] == "keep" for x in b["diff"]))
        self.assertEqual(b["itinerary"]["days"], a["itinerary"]["days"])

    def test_unknown_prev_batch_fails(self):
        b, st = self.run_b("A-0000-000000")
        self.assertIsNone(b)
        self.assertTrue(st.done and st.error)

    def test_invalid_event_type_rejected(self):
        with self.assertRaises(ValueError):
            record_event(self.conn, "A-x", "p", "teleport", None)
        with self.assertRaises(ValueError):
            record_event(self.conn, "A-x", "p", "feedback", "love")

    def test_compare_remove_and_add(self):
        prev = {"days": [{"day": 1, "region_id": "x", "place_ids": ["a", "b"]}]}
        new = {"days": [{"day": 1, "region_id": "x", "place_ids": ["a", "c"]}]}
        fb = {"pinned": set(), "disliked": set(), "liked_categories": {}}
        diff = {x["place_id"]: x["change"] for x in compare_itineraries(prev, new, fb, {}, {"c": "카페"})}
        self.assertEqual(diff, {"a": "keep", "b": "remove", "c": "add"})


if __name__ == "__main__":
    unittest.main()
