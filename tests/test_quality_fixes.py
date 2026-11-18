"""일정 품질 보완(B 검증 중 발견): 권역 없는 장소로 하루 만들기 금지, 같은 곳의 다른 기록 중복 금지."""
import unittest

from malttara.tools.itinerary import create_itinerary, is_duplicate

S = {"pace_k": {"여유롭게": 3, "보통": 4, "빡빡하게": 5}, "default_pace": "보통"}


def P(pid, name, lat, lon, region="west", score=1.0, slot=None):
    return {"place_id": pid, "name": name, "lat": lat, "lon": lon, "region_id": region, "score": score, "slot": slot}


class DuplicateTest(unittest.TestCase):
    def test_same_place_variants(self):
        a = P("a", "삼양해수욕장", 33.5250, 126.5860)
        self.assertTrue(is_duplicate(P("b", "삼양 검은모래해변", 33.5262, 126.5870), [a]))       # 0.5km 안
        self.assertTrue(is_duplicate(P("c", "제주절물휴양림", 33.4241, 126.6244), [P("d", "정물자연휴양림", 33.4356, 126.6282)]))  # 오타
        self.assertTrue(is_duplicate(P("e", "제주맥주양조장", 33.40, 126.30), [P("f", "제주맥주", 33.45, 126.35)]))           # 포함
        self.assertTrue(is_duplicate(P("g", "윗세오름", 33.36168, 126.51804), [P("h", "위세오름", 33.36152, 126.51812)]))

    def test_not_duplicates(self):
        beach = P("a", "협재해수욕장", 33.394, 126.239)
        self.assertFalse(is_duplicate(P("b", "협재칼국수", 33.395, 126.240, slot="음식"), [beach]))  # 음식은 해변 옆 허용
        self.assertFalse(is_duplicate(P("c", "한림공원", 33.389, 126.239), [beach]))                  # 0.5km 넘음
        self.assertFalse(is_duplicate(P("d", "새별오름", 33.366, 126.357), [P("e", "금오름", 33.355, 126.306)]))


class ItineraryTest(unittest.TestCase):
    def test_region_none_never_a_day(self):
        c = [P(f"w{i}", f"서부{i}", 33.30 + i * 0.01, 126.20, "west", 0.9) for i in range(3)]
        c += [P(f"e{i}", f"동부{i}", 33.45 + i * 0.01, 126.80, "east", 0.8) for i in range(3)]
        c += [P("n1", "제주도", 33.38, 126.55, None, 1.0), P("n2", "산방산", 33.24, 126.31, None, 1.0)]
        it = create_itinerary(c, {}, {"days": 5, "pace": "여유롭게"}, S)
        self.assertTrue(all(d["region_id"] is not None for d in it["days"]))
        ids = [i for d in it["days"] for i in d["place_ids"]]
        self.assertNotIn("n1", ids)
        self.assertNotIn("n2", ids)

    def test_no_duplicate_records_in_day(self):
        c = [P("a", "삼양해수욕장", 33.5250, 126.5860, "city", 1.0), P("b", "삼양 검은모래해변", 33.5262, 126.5870, "city", 0.99),
             P("c", "사라봉", 33.517, 126.543, "city", 0.5), P("d", "별도봉", 33.519, 126.552, "city", 0.4)]
        it = create_itinerary(c, {}, {"days": 1, "pace": "여유롭게"}, S)
        ids = it["days"][0]["place_ids"]
        self.assertIn("a", ids)
        self.assertNotIn("b", ids)
        self.assertEqual(len(ids), 3)


if __name__ == "__main__":
    unittest.main()
