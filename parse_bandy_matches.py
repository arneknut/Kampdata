"""
parse_bandy_matches.py
======================
Fetches all matches for tournament 439465 from the NBF API and saves
them to matches.json in the same directory.

API endpoint:
  https://api.app04.nbf.clh.no/api/v1/ta/TournamentMatches/
  ?tournamentId=439465&ttl=180

Requirements
------------
pip install requests
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import requests

# ── Config ────────────────────────────────────────────────────────────────────
TOURNAMENT_ID = 439465
TTL           = 180
API_URL       = (
    f"https://api.app04.nbf.clh.no/api/v1/ta/TournamentMatches/"
    f"?tournamentId={TOURNAMENT_ID}&ttl={TTL}"
)
OUTPUT_FILE   = Path(__file__).parent / "matches.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BandyMatchScraper/1.0)",
    "Accept":     "application/json",
    "Referer":    "https://bandyforbundet.no/",
    "Origin":     "https://bandyforbundet.no",
}


# ── Fetch ─────────────────────────────────────────────────────────────────────
def fetch_matches() -> list:
    print(f"Fetching: {API_URL}")
    r = requests.get(API_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()

    if isinstance(data, list):
        return data
    for key in ("matches", "data", "items", "results", "Matches", "Data"):
        if key in data and isinstance(data[key], list):
            return data[key]
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"Unexpected response shape: {type(data)}")


# ── Normalise ─────────────────────────────────────────────────────────────────
def pick(d, *keys):
    for k in keys:
        v = d.get(k)
        if v is not None:
            return v
    return None


def normalise(raw):
    home = pick(raw, "homeTeam", "HomeTeam", "home_team", "Home")
    away = pick(raw, "awayTeam", "AwayTeam", "away_team", "Away")

    if isinstance(home, dict):
        home = home.get("name") or home.get("Name") or home.get("shortName") or str(home)
    if isinstance(away, dict):
        away = away.get("name") or away.get("Name") or away.get("shortName") or str(away)

    result = pick(raw, "result", "Result", "score", "Score")
    if isinstance(result, dict):
        hs  = result.get("homeScore", result.get("home", result.get("HomeScore", "")))
        as_ = result.get("awayScore", result.get("away", result.get("AwayScore", "")))
        result = f"{hs} - {as_}" if (hs != "" and as_ != "") else None

    raw_dt = pick(raw, "matchDate", "MatchDate", "date", "Date",
                  "startTime", "StartTime", "kickOff", "KickOff",
                  "scheduledTime", "ScheduledTime")
    match_date = match_time = None
    if isinstance(raw_dt, str) and raw_dt:
        try:
            dt = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
            match_date = dt.strftime("%Y-%m-%d")
            match_time = dt.strftime("%H:%M")
        except ValueError:
            match_date = raw_dt

    venue = pick(raw, "venue", "Venue", "arena", "Arena",
                 "location", "Location", "facility", "Facility")
    if isinstance(venue, dict):
        venue = venue.get("name") or venue.get("Name") or str(venue)

    return {
        "id":            pick(raw, "id", "Id", "matchId", "MatchId", "gameId"),
        "round":         pick(raw, "round", "Round", "matchRound", "MatchRound", "week"),
        "date":          match_date,
        "time":          match_time,
        "home_team":     home,
        "away_team":     away,
        "result":        result,
        "home_score":    pick(raw, "homeScore", "HomeScore", "home_score"),
        "away_score":    pick(raw, "awayScore", "AwayScore", "away_score"),
        "venue":         venue,
        "status":        pick(raw, "status", "Status", "matchStatus", "MatchStatus"),
        "tournament_id": TOURNAMENT_ID,
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\nBandy Match Scraper")
    print(f"Output : {OUTPUT_FILE}\n")

    try:
        raw_matches = fetch_matches()
    except requests.HTTPError as e:
        print(f"HTTP error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    matches = [normalise(m) for m in raw_matches]

    output = {
        "scraped_at":    datetime.utcnow().isoformat() + "Z",
        "api_url":       API_URL,
        "tournament_id": TOURNAMENT_ID,
        "match_count":   len(matches),
        "matches":       matches,
    }

    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Saved {len(matches)} matches → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
