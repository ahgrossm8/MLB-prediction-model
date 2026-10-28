# Updating player statistics

`update_features.py` refreshes nine hitter/pitcher statistics tables in BigQuery.
It runs only the player-statistics section of `feature_refresh.sql`. The original
SQL is retained as the reference for the trained model's feature definitions.
The three `inputs_for_regression*` tables are not rebuilt by this script.

Install `google-cloud-bigquery` and configure Google Application Default
Credentials with access to your dataset. Then run:

```powershell
python update_features.py --project YOUR_PROJECT_ID
```

Use `--date YYYY-MM-DD` to select a statistics date; the default is today in
America/New_York. If timezone data is unavailable, pass `--date` or install
`tzdata`. Optional settings: `--dataset`, `--location`, `--sql`, and
`--maximum-bytes-billed`.

The raw `pitch_level_data_2023_to_present` table must already be current.
This script does not download pitches, read matchups, assemble team features,
write prediction JSON, or apply a model. Game-input assembly and model execution
belong in `predict.py`; see `PREDICT.md` for the saved model and daily commands. The old
`--history-only`, `--upcoming-only`, `--matchups`, and `--output` options are removed.

For predictions, query `game_log_final` and `pitcher_game_log_final` using
`game_date =` the selected date and player IDs from `matchups.json`. Their rolling
statistics use the preceding 30 calendar days and exclude the selected date.
Calculation dates are added for players with prior-month history even when they
have not played on the selected date. Zero-count date anchors exist only inside
rolling calculations, never in persisted game logs, and are excluded by the
windows. Players without prior-month history have no target-date row; missing
history must be handled explicitly in `predict.py`.

The original statistical formulas are preserved, including the ERA/WHIP
calculations. Raw game logs retain observed history; final rolling outputs cover
historical dates through the selected date plus the selected date's statistics.
Tables are replaced in sequence; if a query fails, earlier updates may already
persist. Live BigQuery execution still requires validation against your dataset.

Offline checks:

```powershell
python -m unittest test_update_features.py -v
```
