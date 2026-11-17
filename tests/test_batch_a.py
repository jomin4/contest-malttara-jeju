import json
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from helpers import I, R, S, goal, mock_conn
from malttara.agent.batch_a import run_batch_a
from malttara.agent.llm import LLMClient
from malttara.agent.planner import accept_plan, plan_tasks_rules
from malttara.agent.state import BatchState
from malttara.tools.explain import explain_place, export_travel_plan
from malttara.tools.quests import generate_quests, quest_label

NO_LLM = LLMClient(None, None, None, 5)


class BatchATest(unittest.TestCase):
    def setUp(self):
        self.conn, _ = mock_conn()

    def tearDown(self):
        self.conn.close()

    def run_a(self, g, inject=False, llm=NO_LLM):
        st = BatchState("A", datetime(2026, 11, 16, 19, 39, 16))
        res = run_batch_a(self.conn, g, inject, llm, S, I, R, st)
        return res, st.events_after(0), st

    def plan(self, ev):
        return {(e["tool"], e["status"]) for e in ev if e["status"] in ("add", "skip")}

    def test_profiles_produce_different_tool_plans(self):
        _, e1, _ = self.run_a(goal(days=3, pace="여유롭게", interests=["바다", "음식"]))
        _, e3, _ = self.run_a(goal(days=4, interests=["카페"], quiet_pref=True))
        self.assertIn(("search_slot", "add"), self.plan(e1))
        self.assertIn(("get_region_data", "skip"), self.plan(e1))
        self.assertIn(("get_region_data", "add"), self.plan(e3))
        self.assertNotEqual(self.plan(e1), self.plan(e3))

    def test_events_seq_starts_at_1_and_increments(self):
        _, ev, st = self.run_a(goal(days=2))
        self.assertEqual([e["seq"] for e in ev], list(range(1, len(ev) + 1)))
        self.assertEqual(st.events_after(3)[0]["seq"], 4)
        self.assertTrue(all(e["batch_id"] == st.batch_id for e in ev))

    def test_inject_error_shows_fail_then_fix(self):
        res, ev, _ = self.run_a(goal(days=2), inject=True)
        st = [e["status"] for e in ev if e["tool"] in ("validate_itinerary", "revise_itinerary")]
        self.assertIn("fail", st)
        self.assertIn("fix", st)
        self.assertFalse([v for v in res["violations_remaining"] if v["type"] == "regions"])

    def test_result_shape_matches_contract(self):
        res, _, st = self.run_a(goal(days=2))
        for k in ("batch_id", "kind", "prev_batch_id", "goal", "itinerary", "places", "routes", "violations_remaining",
                  "explanations", "summary", "quests", "alternatives", "quality", "diff"):
            self.assertIn(k, res)
        self.assertTrue(res["batch_id"].startswith("A-1116-193916"))
        self.assertEqual(res["kind"], "A")
        self.assertIsNone(res["diff"])
        ids = [i for d in res["itinerary"]["days"] for i in d["place_ids"]]
        alts = [a for v in res["alternatives"].values() for a in v]
        self.assertTrue(set(ids) | set(alts) <= set(res["places"]))      # 계약 C3
        p = res["places"][ids[0]]
        for k in ("place_id", "name", "lat", "lon", "emd", "region_id", "region_name", "category",
                  "category_source", "overview", "source", "score", "interest", "spread", "quiet", "indicators", "has_trend"):
            self.assertIn(k, p)
        row = self.conn.execute("select kind, result_json from batches where batch_id=?", (res["batch_id"],)).fetchone()
        self.assertEqual(json.loads(row["result_json"])["batch_id"], res["batch_id"])

    def test_all_actors_rule_without_llm(self):
        _, ev, _ = self.run_a(goal(days=2))
        self.assertNotIn("llm", {e["actor"] for e in ev})

    def test_broken_llm_falls_back_everywhere(self):
        def boom(*a):
            raise OSError("offline")
        res, ev, _ = self.run_a(goal(days=2), inject=True, llm=LLMClient("k", "http://x", "m", 1, transport=boom))
        self.assertNotIn("llm", {e["actor"] for e in ev})
        self.assertTrue(res["itinerary"]["days"])

    def test_explanations_never_claim_place_is_quiet(self):
        res, _, _ = self.run_a(goal(days=2, quiet_pref=True))
        self.assertFalse(any("한적" in s for ss in res["explanations"].values() for s in ss))

    def test_too_few_candidates_leaves_count_violation_not_crash(self):
        res, ev, _ = self.run_a(goal(days=7, pace="빡빡하게", interests=["카페"]))
        self.assertIsInstance(res["violations_remaining"], list)
        self.assertEqual(len(res["itinerary"]["days"]), 7)

    def test_invalid_goal_fails_batch(self):
        g = goal()
        g["days"] = None
        res, ev, st = self.run_a(g)
        self.assertIsNone(res)
        self.assertTrue(st.done)
        self.assertIn("기간", st.error)

    def test_plan_rules_and_accept(self):
        items = plan_tasks_rules(goal(interests=["음식"], origin="모의", month=11), False)
        tools = {(i["tool"], i["action"]) for i in items}
        self.assertIn(("search_slot", "add"), tools)
        self.assertIn(("origin_check", "add"), tools)
        self.assertIn(("analyze_tourism", "skip"), tools)
        self.assertTrue(accept_plan({"items": items}))
        self.assertFalse(accept_plan({"items": [{"tool": "rm_rf", "action": "add", "reason": "x", "params": {}}]}))

    def test_quest_label(self):
        self.assertEqual(quest_label("제주 민속자연사박물관 (본관)"), "제주 민속자연사박물관")
        self.assertEqual(quest_label("아주아주긴이름의관광지입니다요 정말로"), "아주아주긴이름의관광지입")
        res, _, _ = self.run_a(goal(days=2))
        q = generate_quests(res["itinerary"], res["places"])
        self.assertEqual([i["place_id"] for i in q[0]["items"]], res["itinerary"]["days"][0]["place_ids"])

    def test_explain_and_print(self):
        res, _, _ = self.run_a(goal(days=1, interests=["바다"]))
        pid = res["itinerary"]["days"][0]["place_ids"][0]
        lines = explain_place(res["places"][pid], res["goal"], I)
        self.assertTrue(any("563" in s for s in lines) and any("1208" in s for s in lines))
        html = export_travel_plan(res, [{"source_id": "563", "name": "모의", "period_actual": "2018-01~2022-09"}])
        self.assertIn("<html", html)
        self.assertIn("도로거리·이동시간 아님", html)
        self.assertNotIn("http", html)


if __name__ == "__main__":
    unittest.main()
