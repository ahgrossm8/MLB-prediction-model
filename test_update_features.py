"""Offline checks for the statistics-only refresh boundary."""

import re
import unittest
import update_features as features


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.sql = features.load_sql(features.ROOT / "feature_refresh.sql",
                                     "example-project", "player_stats")

    def test_only_player_statistics_are_refreshed(self):
        tables = re.findall(r"create or replace table `example-project\.player_stats\.([a-z_0-9]+)`",
                            self.sql, re.I)
        self.assertEqual(tuple(tables), features.STAT_TABLES)
        self.assertNotIn("inputs_for_regression", self.sql)
        self.assertNotIn("lineup_orders", self.sql)
        self.assertNotIn("`mlb_model_updated.", self.sql)

    def test_target_date_exists_without_target_date_pitches(self):
        self.assertEqual(self.sql.count("UNION DISTINCT"), 3)
        self.assertIn("SELECT @feature_date AS game_date, batter", self.sql)
        self.assertIn("SELECT @feature_date AS game_date, pitcher", self.sql)
        self.assertIn("SELECT pitcher, @feature_date AS game_date", self.sql)
        self.assertEqual(self.sql.count("UNION ALL"), 2)
        self.assertEqual(self.sql.count("0 AS plate_appearances"), 2)
        self.assertIn("RANGE BETWEEN 30 PRECEDING AND 1 PRECEDING", self.sql)
        self.assertIn("AND b.game_date < d.game_date", self.sql)

    def test_observed_game_logs_have_no_placeholder_rows(self):
        for table in ("hitter_game_log", "pitcher_game_log"):
            body = self.sql.split(f".{table}` as", 1)[1].split(";", 1)[0]
            self.assertNotIn("UNION", body)
            self.assertNotIn("@feature_date", body)

    def test_anchor_columns_match_original_log_schema(self):
        original = (features.ROOT / "feature_refresh.sql").read_text(encoding="utf-8-sig")
        for table, counts in (("hitter_game_log", features.HITTER_COUNTS),
                              ("pitcher_game_log", features.PITCHER_COUNTS)):
            body = original.split(f".{table}` as", 1)[1].split(";", 1)[0]
            aliases = re.findall(r"\bas\s+([a-z_0-9]+)", body, re.I)
            self.assertEqual([name.lower() for name in aliases],
                             [name.lower() for name in counts])


if __name__ == "__main__":
    unittest.main()
