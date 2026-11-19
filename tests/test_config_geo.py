import unittest

from malttara.config import load_config, load_env
from malttara.geo import centroid, haversine_km, pct_rank


class ConfigGeoTest(unittest.TestCase):
    def test_settings_values_from_spec(self):
        s = load_config("settings")
        self.assertEqual(s["weights"]["default"], [0.5, 0.15, 0.15, 0.2])   # 관심·분산·한적·인지도 (이슈 #16)
        self.assertEqual(s["weights"]["quiet"], [0.4, 0.25, 0.25, 0.1])
        self.assertAlmostEqual(sum(s["weights"]["default"]), 1.0)
        self.assertEqual(s["pace_k"], {"여유롭게": 3, "보통": 4, "빡빡하게": 5})
        self.assertEqual(s["max_daily_km"], 60)
        self.assertEqual(s["max_days"], 7)

    def test_regions_are_four(self):
        r = load_config("regions")
        self.assertEqual([x["region_id"] for x in r["regions"]], ["city", "west", "east", "south"])

    def test_haversine_known_distance(self):
        # 제주시청(33.4996,126.5312) ↔ 서귀포시청(33.2541,126.5600) ≈ 27.4km
        self.assertAlmostEqual(haversine_km(33.4996, 126.5312, 33.2541, 126.5600), 27.4, delta=0.5)

    def test_pct_rank(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(pct_rank(1.0, vals), 0.0)
        self.assertEqual(pct_rank(5.0, vals), 1.0)
        self.assertEqual(pct_rank(3.0, vals), 0.5)
        self.assertEqual(pct_rank(2.0, [2.0]), 0.5)

    def test_centroid(self):
        self.assertEqual(centroid([(33.0, 126.0), (33.2, 126.2)]), (33.1, 126.1))

    def test_load_env_missing_file(self):
        self.assertEqual(load_env("nope.env"), {})


if __name__ == "__main__":
    unittest.main()
