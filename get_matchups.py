"""Fetch upcoming MLB games, probable starters, and published batting orders.

Usage: python get_matchups.py [--date YYYY-MM-DD] [--output matchups.json]
Uses only Python's standard library. No API key or config.py is required.
"""

import argparse
from datetime import date, datetime, timezone
import json
import logging
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


API_URL = "https://statsapi.mlb.com/api/v1"
LOGGER = logging.getLogger(__name__)


def fetch_json(path, params=None):
    """Retry temporary API failures; fail explicitly after three attempts."""
    url = f"{API_URL}/{path}"
    if params:
        url += "?" + urlencode(params)
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "MLB-Model-Automation/1.0"})
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise
            if attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def parse_lineup(team):
    """Keep the API's published batting order; never infer it from a roster."""
    players = team.get("players", {})
    lineup = []
    for slot, player_id in enumerate(team.get("battingOrder", []), start=1):
        player = players.get(f"ID{player_id}", {})
        lineup.append({
            "batting_order": slot,
            "player_id": player_id,
            "name": player.get("person", {}).get("fullName"),
            "position": player.get("position", {}).get("abbreviation"),
        })
    return lineup


def get_matchups(game_date):
    """Return a dated snapshot, including explicit incomplete-data flags."""
    schedule = fetch_json("schedule", {
        "sportId": 1, "date": game_date.isoformat(), "hydrate": "probablePitcher",
    })
    matchups = []
    for day in schedule.get("dates", []):
        for game in day.get("games", []):
            status = game.get("status", {})
            if status.get("abstractGameState") != "Preview":
                continue
            game_id = game["gamePk"]
            issues = []
            try:
                boxscore = fetch_json(f"game/{game_id}/boxscore")
            except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                LOGGER.warning("Game %s: cannot fetch lineups: %s", game_id, exc)
                boxscore = {}
                issues.append("lineup_fetch_failed")
            matchup = {
                "game_id": game_id,
                "game_date": game.get("officialDate", game_date.isoformat()),
                "start_time_utc": game.get("gameDate"),
                "status": status.get("detailedState"),
                "game_number": game.get("gameNumber"),
                "doubleheader": game.get("doubleHeader"),
                "venue": game.get("venue", {}).get("name"),
            }
            if status.get("codedGameState") not in ("S", "P"):
                issues.append("game_not_scheduled")
            for side in ("away", "home"):
                team = game["teams"][side]
                starter = team.get("probablePitcher", {})
                lineup = parse_lineup(boxscore.get("teams", {}).get(side, {}))
                complete = (len(lineup) == 9
                            and len({p["player_id"] for p in lineup}) == 9
                            and all(p["name"] for p in lineup))
                matchup[side] = {
                    "team_id": team["team"]["id"],
                    "team_name": team["team"]["name"],
                    "probable_starter": {
                        "player_id": starter.get("id"),
                        "name": starter.get("fullName"),
                    },
                    "starter_available": bool(starter.get("id")),
                    "lineup": lineup,
                    "lineup_complete": complete,
                }
                if not starter.get("id"):
                    issues.append(f"{side}_starter_missing")
                if not complete:
                    issues.append(f"{side}_lineup_incomplete")
            matchup["issues"] = issues
            matchup["ready_for_model"] = not issues
            matchups.append(matchup)
    return {
        "requested_date": game_date.isoformat(),
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "MLB Stats API",
        "games": matchups,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, help="YYYY-MM-DD; defaults to today in America/New_York")
    parser.add_argument("--output", type=Path, default=Path("matchups.json"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        game_date = args.date
        if game_date is None:
            game_date = datetime.now(ZoneInfo("America/New_York")).date()
        result = get_matchups(game_date)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Replace only after a successful fetch and complete serialization.
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        temporary.replace(args.output)
    except ZoneInfoNotFoundError:
        parser.exit(1, "ERROR: Timezone data unavailable. Install tzdata or pass --date YYYY-MM-DD.\n")
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    games = result["games"]
    LOGGER.info("%s: %s upcoming games; %s ready for model", game_date,
                len(games), sum(g["ready_for_model"] for g in games))
    for game in games:
        LOGGER.info("%s at %s: %s", game["away"]["team_name"],
                    game["home"]["team_name"], ", ".join(game["issues"]) or "ready")
    LOGGER.info("Saved %s", args.output.resolve())


if __name__ == "__main__":
    main()
