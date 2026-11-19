"""인수 테스트 10종(기획문서_v0 6.1) + 실행 중 코드 표준 라이브러리 검사.

모의 DB(tests/helpers.py)로 돌린다. 점수 공식은 바뀔 수 있으므로 정확한 점수·장소 ID 대신 동작을 검사한다.
실행: PYTHONPATH=src python -m unittest tests.test_acceptance -v
"""
import ast
import os
import pathlib
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from helpers import I, R, S, goal, mock_conn
from malttara.agent.batch_a import run_batch_a
from malttara.agent.batch_b import run_batch_b
from malttara.agent.llm import LLMClient, client_from_env
from malttara.agent.state import BatchState
from malttara.db import data_sources
from malttara.tools.explain import export_travel_plan
from malttara.tools.feedback import analyze_feedback, load_events, record_event
from malttara.tools.goal import merge_goal, parse_goal_rules
from malttara.tools.places import score_places
from malttara.tools.quests import generate_quests

ROOT = pathlib.Path(__file__).resolve().parent.parent
NO_LLM = LLMClient(None, None, None, 5)


def day_ids(res, day_index=None):
    days = res["itinerary"]["days"]
    if day_index is not None:
        return list(days[day_index]["place_ids"])
    return [pid for d in days for pid in d["place_ids"]]


class Acceptance(unittest.TestCase):
    def setUp(self):
        self.conn, _ = mock_conn()
        self._sec = 0

    def tearDown(self):
        self.conn.close()

    def _state(self, kind, prev=None):
        self._sec += 1                      # 배치마다 다른 시각 → 다른 batch_id
        return BatchState(kind, datetime(2026, 11, 19, 10, 0, self._sec), prev_batch_id=prev)

    def run_a(self, g, inject=False, llm=NO_LLM):
        st = self._state("A")
        res = run_batch_a(self.conn, g, inject, llm, S, I, R, st)
        return res, st

    def run_b(self, prev, llm=NO_LLM):
        st = self._state("B", prev)
        res = run_batch_b(self.conn, prev, llm, S, I, R, st)
        return res, st

    # 1. 취향이 바뀌면 추천 결과가 바뀌는가
    def test_01_preference_changes_result(self):
        sea, _ = self.run_a(goal(days=2, pace="여유롭게", interests=["바다"]))
        forest, _ = self.run_a(goal(days=2, pace="여유롭게", interests=["숲"]))
        self.assertNotEqual(set(day_ids(sea, 0)), set(day_ids(forest, 0)))      # 1일차 장소 집합이 다르다
        sea_cats = set(I["interests"]["바다"]["categories"])
        forest_cats = set(I["interests"]["숲"]["categories"])
        self.assertIn(sea["places"][day_ids(sea, 0)[0]]["category"], sea_cats)
        self.assertIn(forest["places"][day_ids(forest, 0)[0]]["category"], forest_cats)

    # 2. 같은 조건에서 같은 결과가 나오는가
    def test_02_same_input_same_result(self):
        g = goal(days=3, pace="여유롭게", interests=["바다", "음식"])
        a1, _ = self.run_a(dict(g))
        a2, _ = self.run_a(dict(g))
        self.assertNotEqual(a1["batch_id"], a2["batch_id"])
        self.assertEqual(a1["itinerary"], a2["itinerary"])
        self.assertEqual(a1["routes"], a2["routes"])
        self.assertEqual(a1["alternatives"], a2["alternatives"])
        r1 = [p["place_id"] for p in score_places(self.conn, g, S, I)]
        r2 = [p["place_id"] for p in score_places(self.conn, g, S, I)]
        self.assertEqual(r1, r2)

    # 3. 추천을 거부하면 적절한 대안을 주는가
    def test_03_rejection_gives_alternative(self):
        a, _ = self.run_a(goal(days=2))
        target = day_ids(a, 0)[0]
        region = a["places"][target]["region_id"]
        self.assertTrue(a["alternatives"].get(target))                       # 거부 전에도 대안이 보인다
        self.assertTrue(all(a["places"][x]["region_id"] == region for x in a["alternatives"][target]))
        record_event(self.conn, a["batch_id"], target, "feedback", "dislike")
        b, st = self.run_b(a["batch_id"])
        self.assertIsNotNone(b, st.error)
        self.assertNotIn(target, day_ids(b))
        ch = {x["place_id"]: x for x in b["diff"]}
        self.assertEqual(ch[target]["change"], "replace")
        new = ch[target]["replaced_by"]
        self.assertIn(new, b["places"])
        self.assertNotEqual(new, target)
        self.assertEqual(b["places"][new]["region_id"], region)                # 같은 권역 대안
        self.assertEqual(len(day_ids(b)), len(day_ids(a)))                     # 하루 장소 수 유지

    # 4. 데이터셋 지표가 바뀌면 추천에 반영되는가
    def test_04_indicator_change_changes_rank(self):
        g = goal(interests=["바다"], quiet_pref=True)
        before = score_places(self.conn, g, S, I)
        max_q = max(p["quiet_count"] for p in before if p["quiet_count"] is not None)
        target = next(p for p in before if p["quiet_count"] is not None and p["quiet_count"] < max_q)
        rank_before = [p["place_id"] for p in before].index(target["place_id"])
        self.conn.execute("UPDATE places SET quiet_count = ? WHERE place_id = ?", (max_q + 1000, target["place_id"]))
        self.conn.commit()
        after = score_places(self.conn, g, S, I)
        rank_after = [p["place_id"] for p in after].index(target["place_id"])
        moved = next(p for p in after if p["place_id"] == target["place_id"])
        self.assertLess(moved["quiet"], target["quiet"])
        self.assertEqual(moved["indicators"]["nearby"]["quiet_count"], max_q + 1000)
        self.assertGreater(rank_after, rank_before)                           # 체류 거점이 많아지면 순위 하락

    # 5. 필수 데이터가 빠졌을 때 안전하게 처리하는가
    def test_05_missing_data_safe(self):
        self.conn.execute("DELETE FROM emd_stats")
        self.conn.commit()
        res, st = self.run_a(goal(days=2, quiet_pref=True))
        self.assertIsNotNone(res, st.error)
        self.assertTrue(st.done)
        self.assertTrue(all(d["place_ids"] for d in res["itinerary"]["days"]))
        self.assertGreater(res["quality"]["no_region_indicator"], 0)
        for pid in day_ids(res):
            reg = res["places"][pid]["indicators"]["region"]
            self.assertTrue(reg["missing"])
            self.assertIsNone(reg["visit_ratio"])                             # 없는 값을 지어내지 않는다

    # 6. LLM 실행에 실패해도 핵심 서비스가 동작하는가
    def test_06_llm_failure_still_works(self):
        def boom(*a):
            raise OSError("LLM 서버 응답 없음")
        broken = LLMClient("test-key", "http://llm.invalid", "m", 1, transport=boom)
        self.assertTrue(broken.available)
        self.assertIsNone(broken.chat_json("s", "u", {"type": "object"}))
        res, st = self.run_a(goal(days=2, interests=["바다"]), inject=True, llm=broken)
        self.assertIsNotNone(res, st.error)
        actors = {e["actor"] for e in st.events_after(0)}
        self.assertNotIn("llm", actors)
        self.assertIn("rule", actors)
        self.assertTrue(day_ids(res))
        self.assertTrue(res["summary"])
        record_event(self.conn, res["batch_id"], day_ids(res)[0], "feedback", "dislike")
        b, st_b = self.run_b(res["batch_id"], llm=broken)
        self.assertIsNotNone(b, st_b.error)
        self.assertNotIn("llm", {e["actor"] for e in st_b.events_after(0)})

    # 7. 인터넷을 끊어도 필수 기능이 동작하는가(규칙 기반 모드)
    def test_07_offline_rule_mode(self):
        llm = client_from_env({}, S)                                          # .env에 AI 키 없음
        self.assertFalse(llm.available)
        text = "2박 3일 바다 보러 여유롭게"
        rule = parse_goal_rules(text, I)
        g, used = merge_goal(None, rule, text, I)
        self.assertFalse(used)
        self.assertEqual(g["days"], 3)
        self.assertIn("바다", g["interests"])
        res, st = self.run_a(g, llm=llm)
        self.assertIsNotNone(res, st.error)
        self.assertEqual(len(res["itinerary"]["days"]), 3)
        self.assertNotIn("llm", {e["actor"] for e in st.events_after(0)})
        b, st_b = self.run_b(res["batch_id"], llm=llm)
        self.assertIsNotNone(b, st_b.error)

    # 8. 게임과 대시보드(목록)에서 같은 분석 결과가 나오는가
    def test_08_game_and_list_same_analysis(self):
        res, _ = self.run_a(goal(days=3, interests=["바다", "음식"]))
        self.assertEqual(len(res["quests"]), len(res["itinerary"]["days"]))
        for q, d in zip(res["quests"], res["itinerary"]["days"]):
            self.assertEqual(q["day"], d["day"])
            self.assertEqual([i["place_id"] for i in q["items"]], d["place_ids"])
        self.assertEqual(generate_quests(res["itinerary"], res["places"]), res["quests"])

    # 9. 데이터 출처와 기준 시점을 확인할 수 있는가
    def test_09_sources_and_period_visible(self):
        res, _ = self.run_a(goal(days=2, quiet_pref=True))
        for pid, p in res["places"].items():
            reg, near = p["indicators"]["region"], p["indicators"]["nearby"]
            self.assertEqual(reg["source_id"], "563")
            self.assertEqual(near["source_id"], "1208")
            for ind in (reg, near):
                self.assertTrue(ind["period"] or ind["missing"], pid)
        html = export_travel_plan(res, data_sources(self.conn))
        self.assertIn("563", html)
        self.assertIn("1208", html)
        self.assertIn("2018-01~2022-09", html)                               # 기준 시점(모의 DB 값)
        self.assertIn("개별 장소의 속성이 아닙니다", html)

    # 10. 가상 탐험 기록과 실제 방문 기록을 구분하는가
    def test_10_virtual_vs_visited_separate(self):
        res, _ = self.run_a(goal(days=2))
        ids = day_ids(res)
        bid = res["batch_id"]
        record_event(self.conn, bid, ids[0], "virtual_arrival", None)
        record_event(self.conn, bid, ids[1], "visited", None)

        def by_type(t):
            return [r["place_id"] for r in self.conn.execute(
                "SELECT place_id FROM user_interactions WHERE batch_id = ? AND type = ?", (bid, t))]
        self.assertEqual(by_type("virtual_arrival"), [ids[0]])
        self.assertEqual(by_type("visited"), [ids[1]])
        fb = analyze_feedback(load_events(self.conn, bid), res["places"])
        self.assertEqual((fb["pinned"], fb["disliked"], fb["liked_categories"]), (set(), set(), {}))
        self.assertEqual(fb["arrived"], {ids[0]})                             # 실제 방문은 가상 도착에 섞이지 않는다
        b, _ = self.run_b(bid)
        self.assertTrue(all(x["change"] == "keep" for x in b["diff"]))         # 선호 집계·경로에 미반영

    # 11. 실행 중 코드는 표준 라이브러리만 import한다(D17)
    def test_11_runtime_imports_stdlib_only(self):
        src = ROOT / "src" / "malttara"
        files = [f for f in src.rglob("*.py") if "etl" not in f.parts or f.name in ("mock_data.py", "__init__.py")]
        files.append(ROOT / "run.py")
        bad = set()
        for f in files:
            for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module or ""]
                else:
                    names = []
                bad |= {n.split(".")[0] for n in names
                        if n and n.split(".")[0] not in sys.stdlib_module_names and n.split(".")[0] != "malttara"}
        self.assertEqual(bad, set())


if __name__ == "__main__":
    unittest.main()
