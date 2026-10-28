# Run daily predictions

For the optional hourly March-November schedule and Gmail recipient setup,
see [EMAIL_AUTOMATION.md](EMAIL_AUTOMATION.md). Manual runs below do not send
email unless `--email` is supplied.

Run the full pipeline with one command from the project folder:

```powershell
.\.venv\Scripts\python.exe main.py --project project-d31ef9de-ef00-481f-ae3
```

`main.py` runs `get_matchups.py`, `update_features.py`, and `predict.py` in that
order using the same Python environment and date. It stops if any script fails,
then prints probabilities, picks, and skipped-game reasons after a successful run.
Raw pitch data must already be current. Run before first pitch once lineups are
published. The default date is today in America/New_York; use `--date YYYY-MM-DD`
to choose another date. Options include `--dataset`, `--location`, `--matchups`,
`--model`, `--sql`, `--output`, and `--maximum-bytes-billed` (per query/job,
not a total pipeline budget). A failure does not undo earlier steps or remove
older output files; only a completed run prints the final results summary.

The individual commands below remain available for troubleshooting.

Use `.venv\Scripts\python.exe` for the commands below. Install dependencies with
`python -m pip install -r requirements.txt` in a Python environment if necessary.

The saved `model.joblib` reproduces the notebook's existing 31-feature logistic
regression, original 80/20 stratified split, full-data median fill, StandardScaler,
and C=0.1. It includes the fitted scaler, medians, feature order, and metadata.
It is fitted on the original training split, not refitted on all rows.
`model.metadata.json` records metrics and the training CSV fingerprint.
Library versions can cause small differences from the notebook's stored results.
The original random-split metrics are reproduction results, not a chronological
backtest. Training does not run during daily predictions.

To recreate the artifact once:

```powershell
.\.venv\Scripts\python.exe train_model.py --csv "C:\Users\ahgro\Downloads\MLB Game Winner Model\MLB_Model_Regression_Inputs.csv"
```

For each prediction date, run these in sequence with the same date:

```powershell
.\.venv\Scripts\python.exe get_matchups.py --date 2026-10-18
.\.venv\Scripts\python.exe update_features.py --project project-d31ef9de-ef00-481f-ae3 --date 2026-10-18
.\.venv\Scripts\python.exe predict.py --project project-d31ef9de-ef00-481f-ae3 --date 2026-10-18
```

BigQuery uses Application Default Credentials and the `mlb_model_updated`
dataset. `predict.py` only reads the two final player-statistics tables for the
requested date and listed player IDs. Optional flags include `--dataset`,
`--location`, `--maximum-bytes-billed`, `--matchups`, `--model`, and `--output`.
Refresh matchups again when batting orders or probable starters change.

`predictions.json` contains one entry per game, home and away win probabilities,
the winner pick, feature values, and any median-imputed features. It uses one
home-minus-away feature row per game, matching the reference SQL's home-only
`inputs_for_regression2` table; away probability is 1 minus home probability.
The training CSV was verified against the live `inputs_for_regression2` table:
all 7,594 rows and 36 columns matched within numeric tolerance.

Lineup statistics use the nine original slot weights and SQL-style averaging.
Missing lineups, starters, or player-history rows produce explicit skipped
entries. Individual null statistics follow SQL averaging and the notebook's
saved median fill. Stale snapshot dates fail without replacing existing output.
A prediction can only be produced once a game has complete inputs. No live
BigQuery validation is implied by the offline tests.

Only load model artifacts you trust; joblib deserializes Python objects.

Offline checks after creating the model:

```powershell
.\.venv\Scripts\python.exe -m unittest test_update_features test_predict -v
```
