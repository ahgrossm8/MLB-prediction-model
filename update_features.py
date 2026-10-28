"""Refresh player statistics only; matchup assembly belongs in predict.py."""

import argparse
from datetime import date, datetime
import logging
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
LOGGER = logging.getLogger(__name__)
TABLE_PATTERN = r"create or replace table `mlb_model_updated\.([a-z_0-9]+)` as"
STAT_TABLES = (
    "hitter_game_log", "advanced_daily_metrics", "game_log_advanced_stage",
    "game_log_final", "pitcher_game_log", "advanced_daily_pitcher_metrics",
    "pitch_detailed", "game_log_pitcher_advanced_stage", "pitcher_game_log_final",
)
HITTER_COUNTS = ("plate_appearances at_bats hits walks IBB singles doubles triples home_runs "
                 "strikeouts total_bases hbp SH SF swings misses in_play est_distance_traveled "
                 "total_launch_speed total_launch_angle").split()
PITCHER_COUNTS = ["outs_recorded", "innings", "runs_allowed", "pitches",
                  "release_speed", "balls", "strikes"] + HITTER_COUNTS


def date_anchors(table, player, columns):
    """Supply target dates inside rolling calculations; never persist fake logs.

    All windows exclude the target date, so anchor zeros do not enter statistics.
    """
    replacements = ["@feature_date AS game_date"] + [f"0 AS {name}" for name in columns]
    return (
        f"(SELECT * FROM `{table}` WHERE game_date < @feature_date\n"
        "UNION ALL\nSELECT * REPLACE(" + ", ".join(replacements) + ")\n"
        f"FROM `{table}`\n"
        "WHERE game_date >= DATE_SUB(@feature_date, INTERVAL 30 DAY)\n"
        "AND game_date < @feature_date\n"
        f"QUALIFY ROW_NUMBER() OVER (PARTITION BY {player} ORDER BY game_date DESC) = 1)"
    )


def load_sql(path, project, dataset):
    """Run only the nine player-statistics statements from the supplied SQL."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.:-]*", project):
        raise ValueError("Invalid project ID")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", dataset):
        raise ValueError("Invalid dataset ID")
    original = path.read_text(encoding="utf-8-sig")
    matches = list(re.finditer(TABLE_PATTERN, original, flags=re.I))
    if tuple(match[1] for match in matches[:9]) != STAT_TABLES:
        raise ValueError("SQL must begin with the expected nine player-statistics tables")
    source = "`mlb_model_updated.pitch_level_data_2023_to_present`"
    statements = []
    for index, match in enumerate(matches[:9]):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(original)
        statement = original[match.start():end]
        name = match[1]
        if name in ("advanced_daily_metrics", "advanced_daily_pitcher_metrics", "pitch_detailed"):
            player = "batter" if name == "advanced_daily_metrics" else "pitcher"
            projection = f"@feature_date AS game_date, {player}"
            if name == "pitch_detailed":
                projection = "pitcher, @feature_date AS game_date"
            extension = (
                f"{source}\nWHERE game_date <= @feature_date\n"
                f"UNION DISTINCT\nSELECT {projection}\nFROM {source}\n"
                "WHERE game_date >= DATE_SUB(@feature_date, INTERVAL 30 DAY)\n"
                "AND game_date < @feature_date"
            )
            if source not in statement:
                raise ValueError(f"Missing date source in {name}")
            statement = statement.replace(source, extension, 1)
        for stage, table, player, counts in (
            ("game_log_advanced_stage", "hitter_game_log", "batter", HITTER_COUNTS),
            ("game_log_pitcher_advanced_stage", "pitcher_game_log", "pitcher", PITCHER_COUNTS),
        ):
            if name == stage:
                reference = f"`mlb_model_updated.{table}`"
                if statement.count(reference) != 1:
                    raise ValueError(f"Expected one rolling source in {name}")
                statement = statement.replace(reference, date_anchors(
                    f"mlb_model_updated.{table}", player, counts))
        statements.append(statement.replace("`mlb_model_updated.", f"`{project}.{dataset}."))
    return "\n".join(statements)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--dataset", default="mlb_model_updated")
    parser.add_argument("--location", help="BigQuery dataset location, e.g. US")
    parser.add_argument("--date", type=date.fromisoformat,
                        help="YYYY-MM-DD; defaults to today in America/New_York")
    parser.add_argument("--sql", type=Path, default=ROOT / "feature_refresh.sql")
    parser.add_argument("--maximum-bytes-billed", type=int)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if args.maximum_bytes_billed is not None and args.maximum_bytes_billed <= 0:
        parser.error("--maximum-bytes-billed must be positive")
    try:
        feature_date = args.date or datetime.now(ZoneInfo("America/New_York")).date()
        sql = load_sql(args.sql, args.project, args.dataset)
        from google.cloud import bigquery
        client = bigquery.Client(project=args.project, location=args.location)
        config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("feature_date", "DATE", feature_date),
        ])
        if args.maximum_bytes_billed is not None:
            config.maximum_bytes_billed = args.maximum_bytes_billed
        LOGGER.info("Refreshing player statistics for %s", feature_date)
        job = client.query(sql, job_config=config)
        LOGGER.info("BigQuery job: %s", job.job_id)
        job.result()
        LOGGER.info("Refreshed %s player-statistics tables", len(STAT_TABLES))
        LOGGER.info("Prediction statistics: %s.%s.game_log_final and pitcher_game_log_final; game_date = %s",
                    args.project, args.dataset, feature_date)
    except ImportError:
        parser.exit(1, "ERROR: Install the client: python -m pip install google-cloud-bigquery\n")
    except Exception as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
