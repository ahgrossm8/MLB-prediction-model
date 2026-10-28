"""Fetch matchups, refresh player statistics, and print MLB predictions."""

import argparse
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from datetime import date, datetime
import json
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent


@contextmanager
def pipeline_lock():
    """Keep manual and scheduled runs from emailing the same games together."""
    import msvcrt
    with (ROOT / '.pipeline.lock').open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise ValueError('Another pipeline run is already active') from None
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def run_step(script, arguments):
    """Use this Python environment and stop the pipeline if the script fails."""
    print(f'\nRunning {script}...', flush=True)
    subprocess.run([sys.executable, str(ROOT / script), *arguments], check=True,
                   stdout=sys.stdout, stderr=sys.stderr)


def print_predictions(output):
    """Display the predictions written by predict.py."""
    result = json.loads(output.read_text(encoding='utf-8'))
    print(f'\nMLB Predictions — {result["requested_date"]}')
    if not result['games']:
        print('No upcoming games found.')
    for game in result['games']:
        print(f'\n{game["away_team"]} at {game["home_team"]}')
        if game['status'] == 'predicted':
            print(f'  {game["away_team"]}: {game["away_win_probability"]:.1%}')
            print(f'  {game["home_team"]}: {game["home_win_probability"]:.1%}')
            print(f'  Pick: {game["predicted_winner"]}')
            if game['imputed_features']:
                print('  Features filled with training medians: '
                      + ', '.join(game['imputed_features']))
        else:
            print('  Prediction unavailable: ' + ', '.join(game['issues']))
    print(f'\nResults saved to {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--dataset', default='mlb_model_updated')
    parser.add_argument('--location')
    parser.add_argument('--date', type=date.fromisoformat,
                        help='YYYY-MM-DD; defaults to today in America/New_York')
    parser.add_argument('--matchups', type=Path, default=ROOT / 'matchups.json')
    parser.add_argument('--model', type=Path, default=ROOT / 'model.joblib')
    parser.add_argument('--sql', type=Path, default=ROOT / 'feature_refresh.sql')
    parser.add_argument('--output', type=Path, default=ROOT / 'predictions.json')
    parser.add_argument('--maximum-bytes-billed', type=int)
    parser.add_argument('--email', action='store_true', help='Email new predictions to configured recipients')
    parser.add_argument('--email-config', type=Path, default=ROOT / 'email_config.json')
    parser.add_argument('--scheduled', action='store_true', help='Skip December through February')
    args = parser.parse_args()
    if args.maximum_bytes_billed is not None and args.maximum_bytes_billed <= 0:
        parser.error('--maximum-bytes-billed must be positive')
    try:
        # Resolve once so all three scripts use the same date, even at midnight.
        game_date = args.date or datetime.now(ZoneInfo('America/New_York')).date()
        if args.scheduled and game_date.month not in range(3, 12):
            print('Offseason: hourly checks run only March through November.')
            return
        matchups, model, sql, output = (
            path.resolve() for path in (args.matchups, args.model, args.sql, args.output))
        if len({matchups, model, sql, output}) != 4:
            raise ValueError('Matchups, model, SQL, and output paths must be different')
        for path in (model, sql):
            if not path.is_file():
                raise ValueError(f'Required file not found: {path}')
        common = ['--project', args.project, '--dataset', args.dataset,
                  '--date', game_date.isoformat()]
        if args.location:
            common += ['--location', args.location]
        if args.maximum_bytes_billed is not None:
            common += ['--maximum-bytes-billed', str(args.maximum_bytes_billed)]
        with pipeline_lock():
            print(f'MLB pipeline — {game_date}\nRaw pitch data must already be current.', flush=True)
            run_step('get_matchups.py', ['--date', game_date.isoformat(), '--output', str(matchups)])
            email_config = None
            if args.email:
                from send_email import load_config, load_state, load_password, unsent_games
                email_config = load_config(args.email_config)
                snapshot = json.loads(matchups.read_text(encoding='utf-8-sig'))
                if snapshot['requested_date'] != game_date.isoformat():
                    raise ValueError('Matchup date does not match this run')
                from predict import validate_game
                ready = [g for g in snapshot['games'] if not validate_game(g, game_date)]
                if not unsent_games(ready, email_config['recipients'], load_state(ROOT / 'email_state.json')):
                    print('No new games with complete inputs. No statistics refresh or email needed.')
                    return
                load_password()  # Fail before refreshing tables if sending is not configured.
            run_step('update_features.py', common + ['--sql', str(sql)])
            run_step('predict.py', common + ['--matchups', str(matchups),
                                           '--model', str(model), '--output', str(output)])
            print_predictions(output)
            if args.email:
                from send_email import send_new_predictions
                result = json.loads(output.read_text(encoding='utf-8'))
                send_new_predictions(result, email_config)
    except subprocess.CalledProcessError as exc:
        parser.exit(1, f'ERROR: Pipeline stopped because {Path(exc.cmd[1]).name} failed '
                    f'(exit code {exc.returncode}). Later steps were not run.\n')
    except KeyboardInterrupt:
        parser.exit(130, '\nPipeline interrupted.\n')
    except Exception as exc:
        parser.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    if '--scheduled' in sys.argv:
        with (ROOT / 'pipeline.log').open('a', encoding='utf-8', buffering=1) as log:
            with redirect_stdout(log), redirect_stderr(log):
                print(f'\nHourly check started: {datetime.now(ZoneInfo("America/New_York")).isoformat()}')
                main()
    else:
        main()
