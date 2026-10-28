"""Score upcoming games using refreshed BigQuery statistics and the saved model."""

import argparse
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from model_features import DIFFERENCES, FEATURES, HITTER_FIELDS, LINEUP_WEIGHTS

ROOT = Path(__file__).resolve().parent
PITCHER_FIELDS = sorted(set(DIFFERENCES.values()) - set(HITTER_FIELDS))


def number(value):
    if value is None:
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Non-finite player statistic')
    return result


def validate_game(game, game_date):
    issues = list(game.get('issues', []))
    if game.get('game_date') != game_date.isoformat():
        issues.append('game_date_mismatch')
    if not game.get('ready_for_model'):
        issues.append('matchup_not_ready')
    for side in ('home', 'away'):
        team = game.get(side, {})
        lineup = team.get('lineup', [])
        if (len(lineup) != 9
                or {p.get('batting_order') for p in lineup} != set(range(1, 10))
                or len({p.get('player_id') for p in lineup}) != 9
                or any(type(p.get('player_id')) is not int or p['player_id'] <= 0 for p in lineup)):
            issues.append(f'{side}_lineup_invalid')
        starter = team.get('probable_starter', {}).get('player_id')
        if type(starter) is not int or starter <= 0:
            issues.append(f'{side}_starter_missing')
    return list(dict.fromkeys(issues))


def index_stats(rows, id_column):
    indexed = {}
    for raw in rows:
        row = {key.lower(): value for key, value in dict(raw).items()}
        player = int(row[id_column])
        if player in indexed:
            raise ValueError(f'Duplicate statistics for {id_column} {player}')
        indexed[player] = row
    return indexed


def fetch_stats(client, project, dataset, game_date, games, maximum_bytes_billed=None):
    from google.cloud import bigquery

    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.:-]*', project):
        raise ValueError('Invalid project ID')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', dataset):
        raise ValueError('Invalid dataset ID')
    results = []
    for table, id_column, fields in (
        ('game_log_final', 'batter', sorted(set(HITTER_FIELDS.values()))),
        ('pitcher_game_log_final', 'pitcher', PITCHER_FIELDS),
    ):
        ids = sorted({player for game in games for side in ('home', 'away')
                      for player in ([p['player_id'] for p in game[side]['lineup']]
                                     if id_column == 'batter' else
                                     [game[side]['probable_starter']['player_id']])})
        config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter('feature_date', 'DATE', game_date),
            bigquery.ArrayQueryParameter('player_ids', 'INT64', ids),
        ])
        if maximum_bytes_billed is not None:
            config.maximum_bytes_billed = maximum_bytes_billed
        sql = (f'SELECT {id_column}, ' + ', '.join(fields)
               + f' FROM `{project}.{dataset}.{table}`'
               + f' WHERE game_date = @feature_date AND {id_column} IN UNNEST(@player_ids)')
        results.append(index_stats(client.query(sql, job_config=config).result(), id_column))
    return results


def team_stats(team, hitters, pitchers):
    missing = [f'hitter_history_missing:{p["player_id"]}' for p in team['lineup']
               if p['player_id'] not in hitters]
    starter = team['probable_starter']['player_id']
    if starter not in pitchers:
        missing.append(f'starter_history_missing:{starter}')
    if missing:
        raise ValueError(', '.join(missing))
    values = {}
    # Match SQL AVG: multiply each slot's statistic, then average observed values.
    # Do not divide by sum(weights), which would change the training definition.
    for target, source in HITTER_FIELDS.items():
        observed = []
        for player in team['lineup']:
            value = number(hitters[player['player_id']][source])
            if value is not None:
                observed.append(value * LINEUP_WEIGHTS[player['batting_order'] - 1])
        values[target] = sum(observed) / len(observed) if observed else None
    values.update({field: number(pitchers[starter][field]) for field in PITCHER_FIELDS})
    return values


def build_features(game, hitters, pitchers):
    home = team_stats(game['home'], hitters, pitchers)
    away = team_stats(game['away'], hitters, pitchers)
    return {feature: (None if home[source] is None or away[source] is None
                      else home[source] - away[source])
            for feature, source in DIFFERENCES.items()}


def score_games(snapshot, game_date, artifact, hitters, pitchers):
    import pandas as pd

    if snapshot['requested_date'] != game_date.isoformat():
        raise ValueError('Matchups snapshot date does not match --date; refresh matchups first')
    if artifact.get('format_version') != 1 or artifact.get('features') != FEATURES:
        raise ValueError('Unsupported model artifact or feature order')
    model = artifact['model']
    win_column = list(model.classes_).index(1)
    output = []
    for game in snapshot['games']:
        result = {
            'game_id': game['game_id'], 'game_date': game.get('game_date'),
            'home_team': game.get('home', {}).get('team_name'),
            'away_team': game.get('away', {}).get('team_name'),
        }
        issues = validate_game(game, game_date)
        if not issues:
            try:
                features = build_features(game, hitters, pitchers)
            except ValueError as exc:
                issues.append(str(exc))
        if issues:
            result.update(status='skipped', issues=issues)
        else:
            frame = pd.DataFrame([features], columns=FEATURES)
            imputed = [name for name in FEATURES if pd.isna(frame.loc[0, name])]
            frame = frame.fillna(artifact['medians'])
            if frame.isna().any().any():
                raise ValueError('Model artifact lacks required missing-value medians')
            probability = float(model.predict_proba(artifact['scaler'].transform(frame))[0, win_column])
            if not math.isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError('Model returned an invalid probability')
            label = int(model.predict(artifact['scaler'].transform(frame))[0])
            result.update(status='predicted', home_win_probability=probability,
                          away_win_probability=1 - probability,
                          predicted_winner=result['home_team'] if label == 1 else result['away_team'],
                          imputed_features=imputed, features=features)
        output.append(result)
    return {
        'requested_date': game_date.isoformat(),
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'matchups_fetched_at_utc': snapshot.get('fetched_at_utc'),
        'model_metadata': artifact['metadata'], 'games': output,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--dataset', default='mlb_model_updated')
    parser.add_argument('--location')
    parser.add_argument('--date', type=date.fromisoformat)
    parser.add_argument('--matchups', type=Path, default=ROOT / 'matchups.json')
    parser.add_argument('--model', type=Path, default=ROOT / 'model.joblib')
    parser.add_argument('--output', type=Path, default=ROOT / 'predictions.json')
    parser.add_argument('--maximum-bytes-billed', type=int)
    args = parser.parse_args()
    if args.maximum_bytes_billed is not None and args.maximum_bytes_billed <= 0:
        parser.error('--maximum-bytes-billed must be positive')
    try:
        import joblib
        import sklearn

        game_date = args.date or datetime.now(ZoneInfo('America/New_York')).date()
        snapshot = json.loads(args.matchups.read_text(encoding='utf-8-sig'))
        if snapshot['requested_date'] != game_date.isoformat():
            raise ValueError('Matchups snapshot date does not match --date; refresh matchups first')
        # Load only a trusted local artifact produced by train_model.py.
        artifact = joblib.load(args.model)
        if artifact['metadata']['sklearn_version'] != sklearn.__version__:
            raise ValueError('scikit-learn version differs from the saved model; use requirements.txt')
        ready = [g for g in snapshot['games'] if not validate_game(g, game_date)]
        hitters, pitchers = {}, {}
        if ready:
            from google.cloud import bigquery
            client = bigquery.Client(project=args.project, location=args.location)
            hitters, pitchers = fetch_stats(client, args.project, args.dataset, game_date,
                                            ready, args.maximum_bytes_billed)
        result = score_games(snapshot, game_date, artifact, hitters, pitchers)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + '.tmp')
        temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        temporary.replace(args.output)
        for game in result['games']:
            print(f'{game["away_team"]} at {game["home_team"]}: ' + (
                f'home {game["home_win_probability"]:.1%}; pick {game["predicted_winner"]}'
                if game['status'] == 'predicted' else 'skipped: ' + ', '.join(game['issues'])))
        print(f'Saved {args.output.resolve()}')
    except Exception as exc:
        parser.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
