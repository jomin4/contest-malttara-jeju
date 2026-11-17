import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import I, R, S, goal, mock_conn
from malttara.regions import region_order
from malttara.tools.itinerary import create_itinerary
from malttara.tools.places import score_places, search_places
from malttara.tools.revise import ALLOWED_ACTIONS, apply_action, inject_error, rule_revision
from malttara.tools.validate import validate_itinerary


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.conn, _ = mock_conn()
        self.G = goal(days=2, pace="보통")
        self.scored = score_places(self.conn, self.G, S, I)
        self.P = {p["place_id"]: p for p in self.scored}
        general = search_places(self.conn, self.G, S, I, limit=500, scored=self.scored)
        self.CANDS = {}
        for p in general:
            self.CANDS.setdefault(p["region_id"], []).append(p)
        self.GOOD = create_itinerary(general, {}, self.G, S, region_order=region_order(R))
        self.FIRST = self.GOOD["days"][0]["place_ids"][0]

    def tearDown(self):
        self.conn.close()

    def types(self, it):
        return {v["type"] for v in validate_itinerary(it, self.P, self.G, S)}

    def test_good_itinerary_has_no_violations(self):
        self.assertEqual(validate_itinerary(self.GOOD, self.P, self.G, S), [])

    def test_injected_error_detected_then_fixed_by_rule(self):
        bad, pid = inject_error(self.GOOD, self.scored, self.P, S)
        self.assertIn(pid, bad["days"][0]["place_ids"])
        self.assertNotIn(pid, self.GOOD["days"][0]["place_ids"])    # 원본 불변
        v = validate_itinerary(bad, self.P, self.G, S)
        self.assertIn("regions", {x["type"] for x in v})
        act = rule_revision(bad, v, self.CANDS, self.P, set())
        self.assertEqual(act["type"], "replace")
        fixed = apply_action(bad, act, self.CANDS, self.P, set())
        self.assertNotIn(pid, fixed["days"][0]["place_ids"])
        self.assertNotIn("regions", self.types(fixed))

    def test_distance_violation_over_60(self):
        far = copy.deepcopy(self.P)
        ids = self.GOOD["days"][0]["place_ids"]
        far[ids[1]] = dict(far[ids[1]], lat=far[ids[1]]["lat"] + 0.7)   # 약 78km 북쪽
        v = [x for x in validate_itinerary(self.GOOD, far, self.G, S) if x["type"] == "distance"]
        self.assertEqual(v[0]["limit"], 60)
        self.assertGreater(v[0]["value"], 60)

    def test_duplicate_and_out_of_scope_have_place_id_and_null_values(self):
        it = copy.deepcopy(self.GOOD)
        it["days"][1]["place_ids"][0] = self.FIRST
        it["days"][1]["place_ids"][1] = "p-없는장소"
        v = {x["type"]: x for x in validate_itinerary(it, self.P, self.G, S)}
        self.assertEqual((v["duplicate"]["place_id"], v["duplicate"]["value"], v["duplicate"]["limit"]), (self.FIRST, None, None))
        self.assertEqual(v["out_of_scope"]["place_id"], "p-없는장소")

    def test_count_and_origin(self):
        it = copy.deepcopy(self.GOOD)
        it["days"][0]["place_ids"] = it["days"][0]["place_ids"][:2]
        v = {x["type"]: x for x in validate_itinerary(it, self.P, self.G, S, origin_xy=(33.0, 127.5))}
        self.assertEqual((v["count"]["value"], v["count"]["limit"]), (2, 4))
        self.assertEqual(v["origin"]["limit"], 30)

    def test_tight_pace_allows_two_regions(self):
        g = goal(days=2, pace="빡빡하게")
        bad, _ = inject_error(self.GOOD, self.scored, self.P, S)
        self.assertNotIn("regions", {x["type"] for x in validate_itinerary(bad, self.P, g, S)})

    def test_apply_action_rejects_unknown_or_pinned_or_foreign_replacement(self):
        other_region = next(r for r in self.CANDS if r != self.GOOD["days"][0]["region_id"])
        foreign = self.CANDS[other_region][-1]["place_id"]
        self.assertIsNone(apply_action(self.GOOD, {"type": "teleport", "day": 1, "place_id": self.FIRST}, self.CANDS, self.P, set()))
        self.assertIsNone(apply_action(self.GOOD, {"type": "remove", "day": 1, "place_id": self.FIRST}, self.CANDS, self.P, {self.FIRST}))
        self.assertIsNone(apply_action(self.GOOD, {"type": "replace", "day": 1, "place_id": self.FIRST, "replacement_id": foreign}, self.CANDS, self.P, set()))
        self.assertIsNone(apply_action(self.GOOD, {"type": "replace", "day": 9, "place_id": self.FIRST, "replacement_id": foreign}, self.CANDS, self.P, set()))
        self.assertEqual(set(ALLOWED_ACTIONS), {"replace", "reorder", "remove"})

    def test_apply_remove_and_reorder(self):
        rem = apply_action(self.GOOD, {"type": "remove", "day": 1, "place_id": self.FIRST}, self.CANDS, self.P, set())
        self.assertNotIn(self.FIRST, rem["days"][0]["place_ids"])
        ro = apply_action(self.GOOD, {"type": "reorder", "day": 1, "place_id": self.FIRST}, self.CANDS, self.P, set())
        self.assertEqual(set(ro["days"][0]["place_ids"]), set(self.GOOD["days"][0]["place_ids"]))

    def test_count_violation_not_fixable(self):
        v = [{"day": 1, "type": "count", "value": 2, "limit": 4, "place_id": None}]
        self.assertIsNone(rule_revision(self.GOOD, v, self.CANDS, self.P, set()))

    def test_rule_never_touches_pinned(self):
        bad, pid = inject_error(self.GOOD, self.scored, self.P, S)
        v = validate_itinerary(bad, self.P, self.G, S)
        act = rule_revision(bad, v, self.CANDS, self.P, {pid})
        self.assertTrue(act is None or act["place_id"] != pid)


if __name__ == "__main__":
    unittest.main()
