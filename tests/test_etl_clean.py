import unittest

from malttara.config import load_config
from malttara.etl.clean_places import (
    assign_region,
    clean_1349,
    emd_of_point,
    is_island,
    is_non_place,
    parse_emd,
)
from malttara.etl.names import name_similarity, normalize_name


class EtlCleanTest(unittest.TestCase):
    def test_clean_1349_drops_outside_island_nonplace(self):
        rows = [
            {"장소명": "협재해수욕장", "지번주소": "제주특별자치도 제주시 한림읍 협재리 2447", "위도": "33.3934", "경도": "126.2396"},
            {"장소명": "대구공항", "지번주소": "대구광역시 동구 지저동 400-5", "위도": "35.8998", "경도": "128.6373"},
            {"장소명": "렌트카반납", "지번주소": "제주특별자치도 제주시 용담2동 1032-4", "위도": "33.5159", "경도": "126.5032"},
            {"장소명": "우도봉", "지번주소": "제주특별자치도 제주시 우도면 연평리 산1", "위도": "33.4990", "경도": "126.9680"},
        ]
        out = clean_1349(rows, load_config("etl"), load_config("regions"), {}, polygons=None)  # 경계 없으면 주소 폴백
        self.assertEqual([p["name"] for p in out], ["협재해수욕장"])
        self.assertEqual(out[0]["emd"], "제주시 한림읍")
        self.assertEqual(out[0]["region_id"], "west")
        self.assertEqual(out[0]["place_id"], "p1349-00001")
        self.assertEqual(out[0]["source"], "1349")
        self.assertEqual(out[0]["in_scope"], 1)

    def test_clean_1349_dedup_same_name_within_50m(self):
        rows = [
            {"장소명": "협재해수욕장", "지번주소": "제주특별자치도 제주시 한림읍 협재리 2447", "위도": "33.3934", "경도": "126.2396"},
            {"장소명": "협재 해수욕장", "지번주소": "제주특별자치도 제주시 한림읍 협재리 2448", "위도": "33.3935", "경도": "126.2397"},
            {"장소명": "협재해수욕장", "지번주소": "제주특별자치도 제주시 한림읍 협재리 9", "위도": "33.4100", "경도": "126.2600"},
        ]
        out = clean_1349(rows, load_config("etl"), load_config("regions"), {})
        self.assertEqual([p["place_id"] for p in out], ["p1349-00001", "p1349-00003"])

    def test_clean_1349_uses_polygons_over_address(self):
        # 지번주소가 틀려도 좌표가 들어간 경계의 읍면동을 쓴다
        sq = [("제주시 구좌읍", [[(33.50, 126.70), (33.50, 126.80), (33.60, 126.80), (33.60, 126.70)]])]
        rows = [{"장소명": "김녕해수욕장", "지번주소": "제주특별자치도 제주시 오라동 34-14", "위도": "33.5577", "경도": "126.7594"}]
        out = clean_1349(rows, load_config("etl"), load_config("regions"), {}, polygons=sq)
        self.assertEqual(out[0]["emd"], "제주시 구좌읍")
        self.assertEqual(out[0]["region_id"], "east")

    def test_normalize_name(self):
        self.assertEqual(normalize_name("제주 민속자연사박물관 (본관)", ["제주"]), "민속자연사박물관")
        self.assertEqual(normalize_name("Jeju Café!", []), "jejucafé")

    def test_name_similarity(self):
        self.assertEqual(name_similarity("협재 해수욕장", "협재해수욕장"), 1.0)
        self.assertLess(name_similarity("협재해수욕장", "만장굴"), 0.3)

    def test_parse_emd(self):
        self.assertEqual(parse_emd("제주특별자치도 제주시 한림읍 협재리 2447", {}), "제주시 한림읍")
        self.assertEqual(parse_emd("제주특별자치도 제주시 용담2동 1032", {}), "제주시 용담2동")
        self.assertIsNone(parse_emd("대구광역시 동구 지저동 400-5", {}))
        self.assertIsNone(parse_emd("", {}))

    def test_parse_emd_alias_first(self):
        alias = {"제주시 영평동": "제주시 아라동"}
        self.assertEqual(parse_emd("제주특별자치도 제주시 영평동 2181", alias), "제주시 아라동")

    def test_parse_emd_dong(self):
        self.assertEqual(parse_emd("제주특별자치도 서귀포시 서홍동 1", {}), "서귀포시 서홍동")
        self.assertEqual(assign_region("서귀포시 서홍동", load_config("regions")), "south")

    def test_assign_region(self):
        r = load_config("regions")
        self.assertEqual(assign_region("제주시 용담2동", r), "city")
        self.assertEqual(assign_region("서귀포시 남원읍", r), "south")
        self.assertEqual(assign_region("제주시 구좌읍", r), "east")
        self.assertIsNone(assign_region("제주시 우도면", r))
        self.assertIsNone(assign_region(None, r))

    def test_emd_of_point_square(self):
        sq = [("제주시 테스트동", [[(33.0, 126.0), (33.0, 126.1), (33.1, 126.1), (33.1, 126.0)]])]
        self.assertEqual(emd_of_point(33.05, 126.05, sq), "제주시 테스트동")
        self.assertIsNone(emd_of_point(33.2, 126.05, sq))

    def test_emd_of_point_multipolygon(self):
        # 한 읍면동이 여러 고리(섬 포함)를 가질 수 있다
        poly = [("제주시 여러동", [[(33.0, 126.0), (33.0, 126.1), (33.1, 126.1), (33.1, 126.0)],
                                [(33.3, 126.3), (33.3, 126.4), (33.4, 126.4), (33.4, 126.3)]])]
        self.assertEqual(emd_of_point(33.35, 126.35, poly), "제주시 여러동")

    def test_is_island_and_non_place(self):
        cfg = load_config("etl")
        self.assertTrue(is_island("제주특별자치도 제주시 우도면 연평리 1", 33.50, 126.95, cfg))
        self.assertTrue(is_island("제주특별자치도 제주시 한림읍 협재리 1", 33.4069, 126.2270, cfg))  # 비양도 원
        self.assertFalse(is_island("제주특별자치도 제주시 한림읍 협재리 2447", 33.3934, 126.2396, cfg))
        self.assertTrue(is_non_place("제주공항 주차장", cfg))
        self.assertFalse(is_non_place("협재해수욕장", cfg))


if __name__ == "__main__":
    unittest.main()


class RealDataQualityTest(unittest.TestCase):
    """실데이터 점검에서 나온 문제(11/17): 같은 장소 반복, 무의미한 이름, 섬 이름, 숙소·식사 기록."""

    def rows(self, items):
        return [{"장소명": n, "지번주소": "제주특별자치도 제주시 조천읍 함덕리 1", "위도": str(a), "경도": str(b)} for n, a, b in items]

    def test_same_name_within_2km_is_one_place(self):
        out = clean_1349(self.rows([("함덕해수욕장", 33.5430, 126.6690), ("함덕 해수욕장", 33.5480, 126.6750),
                                    ("함덕해수욕장", 33.4000, 126.3000)]),
                         load_config("etl"), load_config("regions"), {}, polygons=None)
        self.assertEqual(len(out), 2)          # 1km 안 둘은 하나, 20km 밖 하나는 별개

    def test_junk_and_island_names_and_non_places_dropped(self):
        out = clean_1349(self.rows([("dd", 33.5, 126.6), ("123", 33.5, 126.61), ("몰라", 33.5, 126.62),
                                    ("TERER", 33.5, 126.63), ("가파도", 33.3, 126.27), ("숙소(아일랜드힐)", 33.5, 126.64),
                                    ("점심식사", 33.5, 126.65), ("팜파스", 33.5, 126.66)]),
                         load_config("etl"), load_config("regions"), {}, polygons=None)
        self.assertEqual([p["name"] for p in out], ["팜파스"])

    def test_facility_words_area_names_and_near_prefix_duplicates(self):
        out = clean_1349(self.rows([("성판악 입구", 33.3850, 126.6200), ("성판악매표소", 33.3852, 126.6202),
                                    ("성판악코스안내", 33.3853, 126.6203), ("대정읍", 33.22, 126.25),
                                    ("관음사코스~성판악코스", 33.42, 126.55), ("윗세오름", 33.36, 126.53)]),
                         load_config("etl"), load_config("regions"), {}, polygons=None)
        self.assertEqual([p["name"] for p in out], ["윗세오름"])
