# MLB Game Winner Prediction Model

A Python and SQL project that predicts MLB game winners using recent hitter and starting-pitcher performance. The pipeline retrieves matchups, refreshes player statistics in Google BigQuery, generates win probabilities, and optionally emails predictions to subscribers.

## Project Overview

This project connects statistical modeling with an automated daily workflow. It combines player-level statistics with batting lineups and starting-pitcher matchups to create game-level features for a logistic regression model.

The project demonstrates:

- SQL feature engineering using rolling player-performance windows.
- Python data processing and machine learning.
- Integration with Google BigQuery.
- Automated prediction generation and email delivery.
- Input validation, error handling, and offline tests.

## How It Works

1. **Retrieve matchups:** Fetch scheduled games, batting lineups, and probable starting pitchers.
2. **Refresh features:** Run SQL in BigQuery to calculate recent player statistics.
3. **Build model inputs:** Combine lineup-weighted hitter statistics and starting-pitcher statistics into home-minus-away differences.
4. **Generate predictions:** Apply the saved model to produce home and away win probabilities and a predicted winner.
5. **Distribute results:** Optionally email new predictions to configured recipients.

Games with incomplete lineups, missing starters, or missing player-history records are skipped with explicit reasons.

## Feature Engineering

The model uses **31 features** representing differences between the home and away teams.

Hitter features include:

- Batting average, on-base percentage, slugging percentage, and OPS.
- Strikeout and whiff rates.
- Exit velocity, launch angle, and batted-ball distance.

Starting-pitcher features include:

- ERA, WHIP, and opponent hitting statistics.
- Strikeout and whiff rates.
- Pitch velocity and movement.
- Quality-of-contact statistics allowed.

Player statistics use rolling 30-day windows. Hitter statistics are combined using batting-order weights to represent each team's lineup.

## Model and Evaluation

The model is a logistic regression with standardized features and median imputation for missing numerical values.

| Item | Value |
| --- | --- |
| Dataset size | 7,594 game records |
| Date range | March 20, 2023–May 25, 2026 |
| Number of features | 31 |
| Training records | 6,075 |
| Test records | 1,519 |
| Evaluation split | Random stratified 80/20 |
| Test accuracy | 54.2% |
| Test ROC AUC | 0.565 |

**Evaluation limitations:** These metrics reproduce the original random-split evaluation; they are not a chronological backtest. Missing-value medians were calculated using the full dataset before splitting, so the evaluation is not fully isolated from the test set. The results do not establish a betting advantage or improvement over a simple baseline.

The saved model includes the fitted scaler, imputation values, feature order, and training metadata. Daily prediction runs reuse this artifact rather than retraining the model.

## Prediction Output

For each game with complete inputs, the pipeline produces:

- Home and away team names.
- Home and away win probabilities.
- Predicted winner.
- Model feature values.
- A record of any median-imputed features.

Skipped games include explanations of the missing or invalid inputs. Results are saved as JSON and displayed in the terminal. Optional email automation distributes new predictions while tracking previous deliveries to avoid duplicates.

## Repository Guide

| File | Purpose |
| --- | --- |
| `main.py` | Orchestrates the daily prediction pipeline. |
| `get_matchups.py` | Retrieves matchups, lineups, and starting pitchers. |
| `feature_refresh.sql` | Calculates player-performance features in BigQuery. |
| `update_features.py` | Runs the feature-refresh process. |
| `model_features.py` | Defines model features and lineup weights. |
| `train_model.py` | Trains and saves the logistic regression artifact. |
| `predict.py` | Generates game-level predictions. |
| `model.metadata.json` | Records training details and evaluation metrics. |
| `send_email.py` | Sends predictions to configured recipients. |
| `setup_automation.ps1` | Configures scheduled execution on Windows. |
| `test_*.py` | Contains offline tests for pipeline components. |

## Setup and Usage

The current automation workflow is designed for Windows and PowerShell.

Running the pipeline requires:

- Python and the packages listed in `requirements.txt`.
- Google Cloud credentials and access to the required BigQuery tables.
- Current underlying pitch data.
- A saved model artifact, which can be recreated using the training CSV.
- Email configuration and credentials if email delivery is enabled.

The repository is not a standalone dataset or a fully self-contained demo. Running it requires the associated data and environment setup.

Detailed instructions:

- [Run predictions and recreate the model](PREDICT.md)
- [Refresh player features](FEATURE_REFRESH.md)
- [Configure email delivery and scheduling](EMAIL_AUTOMATION.md)

## Future Improvements

- Evaluate performance using a chronological holdout or walk-forward back testing.
- Fit missing-value imputation using training data only.
- Compare predictions against simple baselines, including always picking the home team.
- Evaluate probability quality using log loss, Brier score, and calibration plots.
- Track predictions against actual outcomes over time.
