import os
import tempfile
import unittest

from malttara.db import all_places, connect, emd_stats, meta_get, place_trend, region_names
from malttara.etl.mock_data import build_mock_db


class DbTest(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "t.sqlite")
        build_mock_db(self.path)
        self.conn = connect(self.path)

    def tearDown(self):
        self.conn.close()

    def test_mock_has_all_regions_and_categories(self):
        places = all_places(self.conn)
        self.assertEqual({p["region_id"] for p in places}, {"city", "west", "east", "south"})
        self.assertTrue({"해수욕장", "음식점", "카페"} <= {p["category"] for p in places})

    def test_mock_has_missing_indicators(self):
        places = all_places(self.conn)
        self.assertTrue(any(p["quiet_count"] is None for p in places))
        self.assertTrue(any(p["emd"] not in emd_stats(self.conn, None) for p in places))

    def test_emd_stats_month_fallback(self):
        annual = emd_stats(self.conn, None)
        self.assertTrue(annual)
        self.assertTrue(emd_stats(self.conn, 11))
        row = next(iter(annual.values()))
        self.assertEqual(row["source_id"], "563")
        self.assertIn("period", row)

    def test_trend_and_meta(self):
        with_trend = [p for p in all_places(self.conn) if place_trend(self.conn, p["place_id"])]
        self.assertEqual(len(with_trend), 2)
        self.assertEqual(meta_get(self.conn, "data_version"), "mock")
        self.assertEqual(region_names(self.conn)["south"], "중문·서귀포권")

    def test_mock_is_deterministic(self):
        other = os.path.join(tempfile.mkdtemp(), "u.sqlite")
        build_mock_db(other)
        c2 = connect(other)
        self.assertEqual(all_places(self.conn), all_places(c2))
        c2.close()


if __name__ == "__main__":
    unittest.main()
