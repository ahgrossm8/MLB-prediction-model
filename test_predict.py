"""Offline checks for training-schema parity and prediction boundaries."""

from copy import deepcopy
from datetime import date
from pathlib import Path
import re
import unittest

from model_features import DIFFERENCES, FEATURES, HITTER_FIELDS, LINEUP_WEIGHTS
import predict


class PredictionTests(unittest.TestCase):
    def setUp(self):
        self.day = date(2026, 10, 18)
        def team(offset):
            return {'team_name': str(offset), 'probable_starter': {'player_id': offset + 20},
                    'lineup': [{'player_id': offset + i, 'batting_order': i} for i in range(1, 10)]}
        self.game = {'game_id': 1, 'game_date': self.day.isoformat(),
                     'ready_for_model': True, 'issues': [], 'home': team(0), 'away': team(100)}
        self.hitters = {offset+i: {field: float(i) for field in HITTER_FIELDS.values()}
                        for offset in (0, 100) for i in range(1, 10)}
        self.pitchers = {20: dict.fromkeys(predict.PITCHER_FIELDS, 3.),
                         120: dict.fromkeys(predict.PITCHER_FIELDS, 5.)}

    def test_definitions_match_reference_sql(self):
        sql = Path('feature_refresh.sql').read_text(encoding='utf-8-sig')
        section = sql.split('create or replace table `mlb_model_updated.inputs_for_regression` as')[1]
        pairs = re.findall(r's1\.(\w+) - s2\.\w+ as (\w+)', section.split('from `')[0])
        self.assertEqual(DIFFERENCES, {alias: source for source, alias in pairs})
        self.assertEqual(list(DIFFERENCES), FEATURES)
        self.assertEqual(len(FEATURES), 31)

    def test_lineup_slot_weights_and_home_orientation(self):
        values = predict.team_stats(self.game['home'], self.hitters, self.pitchers)
        self.assertAlmostEqual(values['proj_team_avg'], sum((i+1)*w for i,w in enumerate(LINEUP_WEIGHTS))/9)
        self.game['home']['lineup'].reverse()
        self.assertEqual(values, predict.team_stats(self.game['home'], self.hitters, self.pitchers))
        features = predict.build_features(self.game, self.hitters, self.pitchers)
        self.assertEqual(features['proj_avg_diff'], 0)
        self.assertEqual(features['proj_sp_era_diff'], -2)

    def test_missing_player_history_blocks_game(self):
        del self.hitters[1]
        with self.assertRaisesRegex(ValueError, 'hitter_history_missing:1'):
            predict.build_features(self.game, self.hitters, self.pitchers)

    def test_null_statistics_follow_sql_average(self):
        self.hitters[1]['avg_last_30_days'] = None
        values = predict.team_stats(self.game['home'], self.hitters, self.pitchers)
        self.assertAlmostEqual(values['proj_team_avg'], sum((i+1)*w for i,w in enumerate(LINEUP_WEIGHTS) if i)/8)
        self.pitchers[20]['era_30d'] = None
        self.assertIsNone(predict.build_features(self.game, self.hitters, self.pitchers)['proj_sp_era_diff'])

    def test_invalid_lineup_and_date(self):
        self.assertEqual(predict.validate_game(self.game, self.day), [])
        bad = deepcopy(self.game)
        bad['home']['lineup'][0]['batting_order'] = 2
        self.assertIn('home_lineup_invalid', predict.validate_game(bad, self.day))
        self.assertIn('game_date_mismatch', predict.validate_game(self.game, date(2026, 10, 19)))

    def test_duplicate_rows_fail_and_case_normalizes(self):
        self.assertEqual(predict.index_stats([{'pitcher': 20, 'ERA_30d': 3}], 'pitcher')[20]['era_30d'], 3)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            predict.index_stats([{'batter': 1}, {'batter': 1}], 'batter')

    def test_saved_model_scores_and_skips(self):
        import joblib
        artifact = joblib.load('model.joblib')
        snapshot = {'requested_date': self.day.isoformat(), 'games': [self.game]}
        result = predict.score_games(snapshot, self.day, artifact, self.hitters, self.pitchers)['games'][0]
        self.assertEqual(result['status'], 'predicted')
        self.assertAlmostEqual(result['home_win_probability'] + result['away_win_probability'], 1)
        self.pitchers[20]['era_30d'] = None
        result = predict.score_games(snapshot, self.day, artifact, self.hitters, self.pitchers)['games'][0]
        self.assertIn('proj_sp_era_diff', result['imputed_features'])
        del self.hitters[1]
        result = predict.score_games(snapshot, self.day, artifact, self.hitters, self.pitchers)['games'][0]
        self.assertEqual(result['status'], 'skipped')
        snapshot['requested_date'] = '2026-10-17'
        with self.assertRaisesRegex(ValueError, 'snapshot date'):
            predict.score_games(snapshot, self.day, artifact, self.hitters, self.pitchers)


if __name__ == '__main__':
    unittest.main()
