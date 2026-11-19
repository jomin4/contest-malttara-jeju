"""Task 6: 경계 → map.json, 원본 → SQLite 빌드(합성 픽스처 tests/fixtures/raw_min)."""
import json
import os
import shutil
import tempfile
import unittest

from malttara.config import load_config
from malttara.db import all_places, connect, data_sources, emd_stats, meta_get, place_trend, region_names
from malttara.etl.boundaries import build_map, load_polygons, nearest_emd, simplify_ring
from malttara.etl.build_db import build_db
from malttara.etl.clean_places import emd_of_point

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
RAW = os.path.join(FIX, "raw_min")
GEO = os.path.join(RAW, "boundary", "HangJeongDong_min.geojson")


class TestBoundaries(unittest.TestCase):
    def test_load_polygons_jeju_only_lat_lon_order(self):
        polys = load_polygons(GEO)
        self.assertEqual(sorted(e for e, _ in polys), ["제주시 우도면", "제주시 일도1동", "제주시 한림읍"])
        rings = dict(polys)["제주시 한림읍"]
        self.assertEqual(rings[0][0], (33.38, 126.20))   # (lat, lon)
        self.assertEqual(emd_of_point(33.3934, 126.2396, polys), "제주시 한림읍")
        self.assertIsNone(emd_of_point(33.30, 126.40, polys))

    def test_load_polygons_alias(self):
        polys = load_polygons(GEO, {"제주시 일도1동": "제주시 일도동"})
        self.assertIn("제주시 일도동", dict(polys))

    def test_nearest_emd_just_outside_coast(self):
        polys = load_polygons(GEO)
        self.assertEqual(nearest_emd(33.379, 126.23, polys, 1.0), "제주시 한림읍")   # 남쪽 경계 밖 약 110m
        self.assertIsNone(nearest_emd(33.30, 126.23, polys, 1.0))

    def test_simplify_drops_collinear_point(self):
        ring = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
        self.assertEqual(simplify_ring(ring, 0.5), [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)])

    def test_build_map_excludes_islands_and_matches_contract(self):
        out = os.path.join(tempfile.mkdtemp(), "map.json")
        m = build_map(GEO, load_config("regions"), {}, out, 0.5)
        with open(out, encoding="utf-8") as f:
            self.assertEqual(json.load(f), m)
        self.assertEqual({e["emd"] for e in m["emds"]}, {"제주시 한림읍", "제주시 일도1동"})
        self.assertEqual({e["emd"]: e["region_id"] for e in m["emds"]},
                         {"제주시 한림읍": "west", "제주시 일도1동": "city"})
        w, h = m["view_box"].split()[2:]
        self.assertTrue(m["view_box"].startswith("0 0 "))
        self.assertEqual(int(w), 1000)
        self.assertGreater(int(h), 0)
        self.assertEqual([r["region_id"] for r in m["regions"]], ["city", "west", "east", "south"])
        west = [r for r in m["regions"] if r["region_id"] == "west"][0]
        self.assertTrue(west["d"].startswith("M"))
        self.assertEqual(set(m["project"]), {"min_lon", "max_lat", "scale"})
        # 투영식 확인: 경계 좌상단 점은 패딩 안쪽, 모든 path 점은 view_box 안
        for e in m["emds"]:
            nums = [float(v) for v in e["d"].replace("M", " ").replace("L", " ").replace("Z", " ").replace(",", " ").split()]
            xs, ys = nums[0::2], nums[1::2]
            self.assertTrue(all(0 <= x <= int(w) for x in xs) and all(0 <= y <= int(h) for y in ys))
            self.assertNotIn("126.23", e["d"])  # 위경도가 아니라 투영 좌표


class TestBuildDb(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.out, True)

    def _build(self, raw):
        stats = build_db(raw, os.path.join(self.out, "m.sqlite"), os.path.join(self.out, "map.json"), log=lambda *_: None)
        conn = connect(os.path.join(self.out, "m.sqlite"))
        self.addCleanup(conn.close)
        return stats, conn

    def test_build_db_from_minimal_raw(self):
        stats, conn = self._build(RAW)
        places = {p["name"]: p for p in all_places(conn)}
        self.assertEqual(set(places), {"협재해수욕장", "동문시장", "금능포구"})
        # 경계 밖(해안) 좌표는 틀릴 수 있는 지번주소(한경면)보다 가장 가까운 경계(1km 이내)를 따른다
        self.assertEqual((places["금능포구"]["emd"], places["금능포구"]["region_id"]), ("제주시 한림읍", "west"))
        self.assertIsNone(places["금능포구"]["quiet_count"])   # 1208 점 분포 밖 → 지표 없음
        hj = places["협재해수욕장"]
        self.assertEqual((hj["emd"], hj["region_id"]), ("제주시 한림읍", "west"))
        self.assertEqual(hj["quiet_count"], 2)
        self.assertEqual((hj["category"], hj["category_source"]), ("해수욕장", "hub_784"))
        self.assertEqual((places["동문시장"]["category"], places["동문시장"]["category_source"]), ("시장", "hub_858"))
        # 읍면동 지표: 부속섬(우도면) 제외
        st = emd_stats(conn, None)
        self.assertEqual(set(st), {"제주시 한림읍", "제주시 일도1동"})
        self.assertEqual(st["제주시 한림읍"]["period"], "2018-01~2018-02")
        # 입장객: 수작업표 없이 이름 일치 1건
        self.assertEqual(place_trend(conn, hj["place_id"]),
                         [{"year_month": "2009-01", "domestic": 1000, "foreign": 30, "source_id": "189,190"}])
        self.assertEqual(set(region_names(conn)), {"city", "west", "east", "south"})
        self.assertIsNotNone(meta_get(conn, "data_version"))
        src = {s["source_id"]: s for s in data_sources(conn)}
        self.assertEqual(src["563"]["rows"], 6)
        self.assertEqual(src["563"]["period_actual"], "2018-01~2018-02")
        self.assertEqual(src["1208"]["period_actual"], "2021-07~2021-12")
        self.assertEqual(src["189"]["period_actual"], "2009-01~2009-02")
        self.assertIn("1349", src)
        self.assertEqual(src["784"]["period_actual"], "2016~2016")
        # 단계별 건수
        self.assertEqual(stats["places"], 3)
        self.assertEqual(stats["places_emd_nearest"], 1)
        self.assertEqual(stats["places_island_emd_dropped"], 1)   # 주소는 성산읍이지만 좌표가 우도면
        self.assertEqual(stats["emds_with_stats"], 2)
        self.assertEqual(stats["places_with_quiet"], 2)
        self.assertEqual(stats["sights_matched"], 1)
        self.assertIn("tourapi", stats["skipped"])
        self.assertIn("hub_811", stats["skipped"])
        with open(os.path.join(self.out, "map.json"), encoding="utf-8") as f:
            m = json.load(f)
        self.assertTrue(m["emds"] and m["view_box"].startswith("0 0 "))

    def test_tourapi_restaurants_added_when_snapshot_exists(self):
        raw = os.path.join(self.out, "raw")
        shutil.copytree(RAW, raw)
        tour = [
            {"content_id": "111", "name": "모의식당", "lat": 33.5130, "lon": 126.5300, "content_type": "39",
             "cat1": "A05", "cat2": "A0502", "cat3": "A05020100", "category": "한식", "overview": "개요"},
            {"content_id": "222", "name": "협재해수욕장", "lat": 33.3935, "lon": 126.2397, "content_type": "12",
             "cat1": "A01", "cat2": "A0101", "cat3": "A01011200", "category": "해수욕장", "overview": "바다"},
            {"content_id": "333", "name": "동문시장", "lat": 33.5115, "lon": 126.5265, "content_type": "39",
             "cat1": "A05", "cat2": "A0502", "cat3": "A05020100", "category": "한식", "overview": None},
        ]
        with open(os.path.join(raw, "tourapi_jeju.json"), "w", encoding="utf-8") as f:
            json.dump(tour, f, ensure_ascii=False)
        stats, conn = self._build(raw)
        places = {p["place_id"]: p for p in all_places(conn)}
        self.assertIn("ptour-111", places)
        self.assertEqual(places["ptour-111"]["source"], "tourapi")
        self.assertEqual(places["ptour-111"]["emd"], "제주시 일도1동")
        self.assertEqual(places["ptour-111"]["category"], "한식")
        self.assertNotIn("ptour-333", places)          # 1349에 같은 장소가 있으면 추가하지 않는다
        hj = [p for p in places.values() if p["name"] == "협재해수욕장"][0]
        self.assertEqual((hj["category_source"], hj["overview"]), ("tourapi", "바다"))
        self.assertNotIn("tourapi", stats["skipped"])
        self.assertEqual(stats["places_tourapi_added"], 1)


if __name__ == "__main__":
    unittest.main()


class DedupSameNameRegionTest(unittest.TestCase):
    def test_keeps_reference_matched_record(self):
        from malttara.etl.build_db import dedup_same_name_region
        ps = [{"place_id": "p1349-00958", "name": "우진해장국", "region_id": "east", "category_source": "keyword"},
              {"place_id": "p1349-01437", "name": "우진해장국", "region_id": "city", "category_source": "keyword"},
              {"place_id": "p1349-00017", "name": "함덕해수욕장", "region_id": "east", "category_source": "keyword"},
              {"place_id": "p1349-04189", "name": "함덕 해수욕장", "region_id": "east", "category_source": "hub_784"}]
        kept = [p["place_id"] for p in dedup_same_name_region(ps, ["제주"])]
        self.assertEqual(kept, ["p1349-00958", "p1349-01437", "p1349-04189"])   # 권역이 다르면 둘 다 유지

    def test_coord_mismatch_with_two_refs_is_dropped(self):
        from malttara.etl.build_db import fix_coord_mismatch
        refs = [{"name": "우진해장국", "lat": 33.5030, "lon": 126.4966}, {"name": "우진해장국", "lat": 33.25, "lon": 126.56}]
        ps = [{"place_id": "a", "name": "우진해장국", "lat": 33.3871, "lon": 126.5841, "source": "1349"},
              {"place_id": "b", "name": "우진해장국", "lat": 33.5031, "lon": 126.4967, "source": "1349"},
              {"place_id": "c", "name": "다른식당", "lat": 33.3871, "lon": 126.5841, "source": "1349"}]
        out, moved, dropped = fix_coord_mismatch(ps, refs, ["제주"])
        self.assertEqual([p["place_id"] for p in out], ["b", "c"])
        self.assertEqual((moved, dropped), (0, 1))


class DataGapsBuildTest(unittest.TestCase):
    def test_relocate_when_single_reference(self):
        from malttara.etl.build_db import fix_coord_mismatch
        refs = [{"name": "제주 서귀포 산방산", "lat": 33.2424, "lon": 126.314},
                {"name": "우진해장국", "lat": 33.50, "lon": 126.49}, {"name": "우진해장국", "lat": 33.25, "lon": 126.56}]
        ps = [{"place_id": "a", "name": "산방산", "lat": 33.2142, "lon": 126.3310, "source": "1349"},
              {"place_id": "b", "name": "우진해장국", "lat": 33.387, "lon": 126.584, "source": "1349"}]
        out, moved, dropped = fix_coord_mismatch(ps, refs, ["서귀포시", "제주시", "서귀포", "제주"])
        self.assertEqual([(p["place_id"], p["lat"], p["lon"]) for p in out], [("a", 33.2424, 126.314)])
        self.assertEqual((moved, dropped), (1, 1))

    def test_category_display_names(self):
        from malttara.etl.build_db import display_category
        m = load_config("etl")["category_display"]
        self.assertEqual(display_category("해변. 해수욕장", m), "해수욕장")
        self.assertEqual(display_category("산, 고개, 오름, 봉우리", m), "오름·산")
        self.assertEqual(display_category("기타외국식", m), "외국식")
        self.assertEqual(display_category("박물관", m), "박물관")
        self.assertIsNone(display_category(None, m))

    def test_uncategorized_1349_out_of_scope(self):
        from malttara.etl.build_db import apply_scope
        ps = [{"place_id": "a", "category": None, "source": "1349", "region_id": "west"},
              {"place_id": "b", "category": "오름", "source": "1349", "region_id": "west"},
              {"place_id": "c", "category": "카페", "source": "tourapi", "region_id": None}]
        apply_scope(ps)
        self.assertEqual([p["in_scope"] for p in ps], [0, 1, 0])
