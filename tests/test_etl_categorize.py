import unittest

from malttara.config import load_config
from malttara.etl.categorize import categorize_places, match_reference

CFG = load_config("etl")


class EtlCategorizeTest(unittest.TestCase):
    def test_exact_name_within_300m_matches(self):
        p = {"name": "협재해수욕장", "lat": 33.3934, "lon": 126.2396}
        refs = [{"name": "협재 해수욕장", "lat": 33.3940, "lon": 126.2400, "category": "해수욕장"}]
        self.assertEqual(match_reference(p, refs, CFG["match"], ["제주"])["category"], "해수욕장")

    def test_far_same_name_does_not_match(self):
        p = {"name": "협재해수욕장", "lat": 33.3934, "lon": 126.2396}
        refs = [{"name": "협재해수욕장", "lat": 33.4100, "lon": 126.2600, "category": "해수욕장"}]  # ~2.6km
        self.assertIsNone(match_reference(p, refs, CFG["match"], ["제주"]))

    def test_fuzzy_within_100m_nearest(self):
        p = {"name": "새별오름", "lat": 33.3660, "lon": 126.3570}
        refs = [
            {"name": "새별오름 주차장", "lat": 33.3665, "lon": 126.3572, "category": "주차장"},   # ~60m, 유사도 0.73(더 멂)
            {"name": "새별오름입구", "lat": 33.3661, "lon": 126.3571, "category": "오름"},       # ~15m, 유사도 0.8
        ]
        self.assertEqual(match_reference(p, refs, CFG["match"], ["제주"])["category"], "오름")

    def test_fuzzy_beyond_100m_does_not_match(self):
        p = {"name": "새별오름", "lat": 33.3660, "lon": 126.3570}
        refs = [{"name": "새별오름입구", "lat": 33.3680, "lon": 126.3570, "category": "오름"}]  # ~220m
        self.assertIsNone(match_reference(p, refs, CFG["match"], ["제주"]))

    def test_ref_without_coords_exact_name_only(self):
        p = {"name": "제주 함덕해수욕장", "lat": 33.5430, "lon": 126.6690}
        refs = [{"name": "함덕해수욕장", "lat": None, "lon": None, "category": "해수욕장"},
                {"name": "함덕", "category": "포구"}]
        self.assertEqual(match_reference(p, refs, CFG["match"], ["제주"])["category"], "해수욕장")
        self.assertIsNone(match_reference({"name": "함덕해변", "lat": 33.5, "lon": 126.6},
                                          [{"name": "함덕해수욕장", "category": "해수욕장"}], CFG["match"], ["제주"]))

    def test_categorize_order_and_keyword_fallback(self):
        places = [{"place_id": "a", "name": "새별오름", "lat": 33.36, "lon": 126.35},
                  {"place_id": "b", "name": "이름없는곳", "lat": 33.40, "lon": 126.40}]
        counts = categorize_places(places, [("tourapi", []), ("hub_811", [])], CFG)
        self.assertEqual(places[0]["category_source"], "keyword")
        self.assertEqual(places[0]["category"], "오름")
        self.assertEqual(places[1]["category_source"], "none")
        self.assertIsNone(places[1]["category"])
        self.assertEqual(counts["keyword"], 1)
        self.assertEqual(counts["none"], 1)

    def test_categorize_first_set_wins_overview_only_tourapi(self):
        places = [{"place_id": "a", "name": "새별오름", "lat": 33.3660, "lon": 126.3570},
                  {"place_id": "b", "name": "제주돌문화공원", "lat": 33.4440, "lon": 126.6610}]
        sets = [
            ("tourapi", [{"name": "새별오름", "lat": 33.3661, "lon": 126.3571, "category": "산", "overview": "개요"}]),
            ("hub_811", [{"name": "새별오름", "lat": 33.3661, "lon": 126.3571, "category": "오름", "overview": "무시"},
                         {"name": "돌문화공원", "lat": 33.4441, "lon": 126.6611, "category": "공원", "overview": "무시"}]),
        ]
        counts = categorize_places(places, sets, CFG)
        self.assertEqual((places[0]["category"], places[0]["category_source"], places[0]["overview"]),
                         ("산", "tourapi", "개요"))
        self.assertEqual((places[1]["category"], places[1]["category_source"]), ("공원", "hub_811"))
        self.assertIsNone(places[1].get("overview"))
        self.assertEqual(counts["tourapi"], 1)
        self.assertEqual(counts["hub_811"], 1)


if __name__ == "__main__":
    unittest.main()


class KeywordRuleTest(unittest.TestCase):
    def test_food_words_win_and_scenery_needs_suffix(self):
        places = [{"place_id": "a", "name": "삼화포구횟집", "lat": 33.5, "lon": 126.6},
                  {"place_id": "b", "name": "준반점(아점/ 함덕해수욕장에 위치)", "lat": 33.5, "lon": 126.6},
                  {"place_id": "c", "name": "협재해수욕장", "lat": 33.5, "lon": 126.6},
                  {"place_id": "d", "name": "오름카페 바람", "lat": 33.5, "lon": 126.6},
                  {"place_id": "e", "name": "새별오름 (나홀로나무)", "lat": 33.5, "lon": 126.6}]
        categorize_places(places, [], load_config("etl"))
        self.assertEqual([p["category"] for p in places], ["음식점", "음식점", "해수욕장", "카페", "오름"])
