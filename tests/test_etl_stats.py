import os
import tempfile
import unittest

from malttara.etl.emd_stats import aggregate_563
from malttara.etl.quiet import quiet_counts, read_1208_points
from malttara.etl.sights import aggregate_sights, match_sights

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


class EtlStatsTest(unittest.TestCase):
    def test_aggregate_563_month_and_annual(self):
        rows = aggregate_563(FIX + "/563_sample.csv", {})
        m0 = [r for r in rows if r["emd"] == "서귀포시 남원읍" and r["month"] == 0][0]
        self.assertAlmostEqual(m0["visit_ratio"], m0["visit_pop"] / m0["resident_pop"])
        self.assertEqual(m0["period"], "2018-01~2018-02")
        self.assertEqual({r["month"] for r in rows if r["emd"] == "서귀포시 남원읍"}, {0, 1, 2})

    def test_aggregate_563_values(self):
        rows = {(r["emd"], r["month"]): r for r in aggregate_563(FIX + "/563_sample.csv", {})}
        nw1 = rows[("서귀포시 남원읍", 1)]
        self.assertAlmostEqual(nw1["visit_pop"], 80.0)       # 성별 합
        self.assertAlmostEqual(nw1["resident_pop"], 200.0)
        self.assertAlmostEqual(nw1["visit_ratio"], 0.4)
        nw0 = rows[("서귀포시 남원읍", 0)]
        self.assertAlmostEqual(nw0["visit_pop"], 140.0)      # 연월 평균 (80+200)/2
        self.assertAlmostEqual(nw0["resident_pop"], 300.0)
        self.assertEqual(nw0["source_id"], "563")
        self.assertIsNone(rows[("제주시 애월읍", 1)]["visit_ratio"])  # 거주 0 → None

    def test_aggregate_563_alias(self):
        rows = aggregate_563(FIX + "/563_sample.csv", {"제주시 애월읍": "제주시 애월읍(통합)"})
        self.assertIn("제주시 애월읍(통합)", {r["emd"] for r in rows})
        self.assertNotIn("제주시 애월읍", {r["emd"] for r in rows})

    def test_quiet_counts_radius(self):
        places = [{"place_id": "a", "lat": 33.40, "lon": 126.40}, {"place_id": "far", "lat": 33.10, "lon": 126.10}]
        pts = [(33.401, 126.401), (33.405, 126.405), (33.50, 126.50)]
        c = quiet_counts(places, pts, 1.0)
        self.assertEqual(c["a"], 2)
        self.assertNotIn("far", c)

    def test_quiet_counts_zero_inside_bbox(self):
        places = [{"place_id": "mid", "lat": 33.45, "lon": 126.45}]
        pts = [(33.40, 126.40), (33.50, 126.50)]
        self.assertEqual(quiet_counts(places, pts, 1.0), {"mid": 0})

    def test_read_1208_points_skips_blank(self):
        pts = list(read_1208_points([FIX + "/1208_sample.csv"]))
        self.assertEqual(len(pts), 4)
        self.assertEqual(pts[0], (33.401, 126.401))  # (위도, 경도)

    def test_match_sights_strips_suffix(self):
        places = [{"place_id": "p1", "name": "만장굴"}]
        self.assertEqual(match_sights(["만장굴관광지"], places, {}, ["제주"]), {"만장굴관광지": "p1"})

    def test_match_sights_manual_first_and_unmatched(self):
        places = [{"place_id": "p1", "name": "국립제주박물관"}, {"place_id": "p2", "name": "미니랜드"}]
        got = match_sights(["(주)제주미니미니랜드", "국립제주박물관", "없는곳"], places,
                           {"(주)제주미니미니랜드": "p2"}, ["제주"])
        self.assertEqual(got, {"(주)제주미니미니랜드": "p2", "국립제주박물관": "p1"})

    def test_aggregate_sights_dates_and_encodings(self):
        d = tempfile.mkdtemp()
        dom, frn = os.path.join(d, "189.csv"), os.path.join(d, "190.csv")
        with open(dom, "w", encoding="cp949", newline="") as f:
            f.write("날짜,관광지명,관광객수\n2009.01,만장굴관광지,1000\n2009.02,만장굴관광지,\"1,200\"\n2009.01,없는곳,5\n")
        with open(frn, "w", encoding="utf-8-sig", newline="") as f:
            f.write("날짜,관광지명,관광객수\n200901,만장굴관광지,30\n")
        rows = aggregate_sights({"domestic": dom, "foreign": frn}, {"만장굴관광지": "p1"})
        self.assertEqual(rows, [
            {"place_id": "p1", "year_month": "2009-01", "domestic": 1000, "foreign": 30, "source_id": "189,190"},
            {"place_id": "p1", "year_month": "2009-02", "domestic": 1200, "foreign": None, "source_id": "189,190"},
        ])


if __name__ == "__main__":
    unittest.main()


class SightsAmbiguityTest(unittest.TestCase):
    def test_ambiguous_name_resolved_by_category(self):
        from malttara.etl.sights import match_sights
        places = [{"place_id": "a", "name": "비자림", "category": None}, {"place_id": "b", "name": "비자림", "category": "숲"}]
        self.assertEqual(match_sights(["비자림"], places, {}, ["제주"]), {"비자림": "b"})
