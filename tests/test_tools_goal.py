import unittest

from malttara.config import load_config
from malttara.tools.goal import merge_goal, parse_goal_rules, validate_goal

I = load_config("interests")


class GoalTest(unittest.TestCase):
    def test_profile1(self):
        g = parse_goal_rules("2박 3일 동안 바다를 보며 여유롭게 쉬고, 현지 음식도 먹고 싶어요", I)
        self.assertEqual((g["nights"], g["days"], g["pace"]), (2, 3, "여유롭게"))
        self.assertEqual(g["interests"], ["바다", "음식"])
        self.assertIsNone(g["transport"])
        self.assertIsNone(g["origin"])
        self.assertIsNone(g["month"])
        self.assertFalse(g["quiet_pref"])
        self.assertEqual(g["evidence"]["days"], "2박 3일")

    def test_profile2(self):
        g = parse_goal_rules("아이와 함께 1박 2일, 렌터카로 오름이랑 체험 위주로 다니고 싶어요", I)
        self.assertEqual((g["days"], g["transport"], g["companion"]), (2, "렌터카", "아이와 함께"))
        self.assertEqual(set(g["interests"]), {"오름", "체험·레저"})
        self.assertIsNone(g["pace"])

    def test_profile3_quiet(self):
        g = parse_goal_rules("혼자 3박 4일, 버스로 조용한 동네와 카페를 천천히 보고 싶어요", I)
        self.assertTrue(g["quiet_pref"])
        self.assertEqual(g["transport"], "버스")
        self.assertEqual(g["companion"], "혼자")
        self.assertIn("카페", g["interests"])
        self.assertEqual(g["days"], 4)

    def test_day_trip_month_origin(self):
        g = parse_goal_rules("11월에 당일로 제주시청에서 출발해서 빡빡하게 돌고 싶어요", I)
        self.assertEqual((g["nights"], g["days"], g["month"], g["pace"]), (0, 1, 11, "빡빡하게"))
        self.assertEqual(g["origin"], "제주시청")

    def test_missing_and_range(self):
        self.assertEqual(validate_goal(parse_goal_rules("바다 보고 싶어요", I)), ["days"])
        self.assertEqual(validate_goal(parse_goal_rules("10박 11일", I)), ["days_range"])
        self.assertEqual(validate_goal(parse_goal_rules("2박 3일", I)), [])

    def test_validate_fixes_nights(self):
        g = {"days": 3, "nights": 5}
        self.assertEqual(validate_goal(g), [])
        self.assertEqual(g["nights"], 2)

    def test_merge_rejects_unfounded_llm_value(self):
        rule = parse_goal_rules("2박 3일 바다", I)
        llm = dict(rule, origin="김포", evidence={"origin": "김포공항"})
        self.assertIsNone(merge_goal(llm, rule, "2박 3일 바다", I)[0]["origin"])

    def test_merge_accepts_founded_llm_value_and_filters_interests(self):
        text = "2박 3일 협재 쪽 숙소 잡았고 바다랑 우주여행"   # 규칙은 출발지를 못 찾는 문장
        self.assertIsNone(parse_goal_rules(text, I)["origin"])
        rule = parse_goal_rules(text, I)
        llm = dict(rule, origin="협재", interests=["바다", "우주여행"], evidence={"origin": "협재"})
        merged, used_llm = merge_goal(llm, rule, text, I)
        self.assertEqual(merged["origin"], "협재")
        self.assertEqual(merged["interests"], ["바다"])
        self.assertTrue(used_llm)

    def test_merge_none_llm_returns_rule(self):
        rule = parse_goal_rules("2박 3일", I)
        self.assertEqual(merge_goal(None, rule, "2박 3일", I), (rule, False))


if __name__ == "__main__":
    unittest.main()
