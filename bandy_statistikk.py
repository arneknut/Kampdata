"""
Bandy standings parser for:
https://bandyforbundet.no/bandy/?page_id=6321
    #/sport/151/season/201066/region/439446/tournament/439465/tab/3

The page is a JavaScript SPA powered by the SportsAdmin (livestats.no) backend.
Two approaches are provided:
  1. Direct API  – fast, no browser needed (may require a valid session/CORS header)
  2. Playwright  – headless browser, works when the API is locked down

Install deps:
    pip install requests playwright pandas
    playwright install chromium       # only needed for approach 2
"""

import json
import requests
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

# ── URL parameters extracted from the hash ──────────────────────────────────
SPORT_ID      = 151
SEASON_ID     = 201066
REGION_ID     = 439446
TOURNAMENT_ID = 439465

# ── 1. Direct API approach ───────────────────────────────────────────────────
# SportsAdmin exposes data through livestats.no (common Norwegian sports API).
# The endpoints below follow the pattern used by similar Norwegian sport sites.

BASE_API = "https://www.livestats.no/components/sport"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://bandyforbundet.no/",
    "Origin":  "https://bandyforbundet.no",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
}

def fetch_standings_api() -> Optional[list[dict]]:
    """Try to pull standings directly from the SportsAdmin/livestats API."""
    url = (
        f"{BASE_API}/{SPORT_ID}/season/{SEASON_ID}"
        f"/region/{REGION_ID}/tournament/{TOURNAMENT_ID}/standing"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[API] Failed: {e}")
        return None


def fetch_matches_api() -> Optional[list[dict]]:
    """Fetch match schedule / results from the same API."""
    url = (
        f"{BASE_API}/{SPORT_ID}/season/{SEASON_ID}"
        f"/region/{REGION_ID}/tournament/{TOURNAMENT_ID}"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[API] Matches failed: {e}")
        return None


# ── 2. Playwright (browser) approach ─────────────────────────────────────────
PAGE_URL = (
    "https://bandyforbundet.no/bandy/?page_id=6321"
    "#/sport/151/season/201066/region/439446/tournament/439465/tab/3"
)

def fetch_standings_browser() -> Optional[list[dict]]:
    """
    Launch a headless Chromium browser, navigate to the SPA, wait for the
    standings table to render, and scrape the data.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return None

    captured = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx     = browser.new_context()
        page    = ctx.new_page()

        # Intercept API responses to grab raw JSON
        def on_response(resp):
            if "standing" in resp.url or "tournament" in resp.url:
                try:
                    data = resp.json()
                    if isinstance(data, list) and data:
                        captured.extend(data)
                except Exception:
                    pass

        page.on("response", on_response)
        page.goto(PAGE_URL, wait_until="networkidle", timeout=60_000)

        # Also try scraping the rendered DOM as a fallback
        rows = page.query_selector_all("table tr")
        dom_rows = []
        for row in rows:
            cells = [c.inner_text().strip() for c in row.query_selector_all("td, th")]
            if cells:
                dom_rows.append(cells)

        browser.close()

    if captured:
        return captured
    if dom_rows:
        # Convert DOM table to list of dicts using first row as header
        hdr  = dom_rows[0]
        data = [dict(zip(hdr, r)) for r in dom_rows[1:] if len(r) == len(hdr)]
        return data

    return None


# ── Parsers ───────────────────────────────────────────────────────────────────

@dataclass
class Standing:
    rank:        int
    team:        str
    played:      int
    wins:        int
    draws:       int
    losses:      int
    goals_for:   int
    goals_against: int
    goal_diff:   int
    points:      int
    extra:       dict = field(default_factory=dict)


def parse_standings(raw: list[dict]) -> list[Standing]:
    """
    Map raw JSON fields to Standing objects.
    Field names vary slightly between SportsAdmin versions; we try common names.
    """
    standings = []
    for i, item in enumerate(raw, 1):
        def g(*keys, default=0):
            for k in keys:
                v = item.get(k)
                if v is not None:
                    try:
                        return int(v)
                    except (ValueError, TypeError):
                        return v
            return default

        team_name = (
            item.get("teamName")
            or item.get("name")
            or item.get("team", {}).get("name", f"Team {i}")
        )
        gf = g("goalsFor",     "scoredGoals",    "goals_for",     "goalsScored")
        ga = g("goalsAgainst", "concededGoals",  "goals_against", "goalsConceded")

        s = Standing(
            rank          = g("position", "rank", default=i),
            team          = team_name,
            played        = g("matchesPlayed", "played", "gamesPlayed", "pld"),
            wins          = g("wins",   "won",  "w"),
            draws         = g("draws",  "draw", "d"),
            losses        = g("losses", "lost", "l"),
            goals_for     = gf,
            goals_against = ga,
            goal_diff     = gf - ga,
            points        = g("points", "pts",  "point"),
        )
        standings.append(s)

    standings.sort(key=lambda x: x.rank)
    return standings


def standings_to_df(standings: list[Standing]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "#":   s.rank,
            "Team": s.team,
            "P":   s.played,
            "W":   s.wins,
            "D":   s.draws,
            "L":   s.losses,
            "GF":  s.goals_for,
            "GA":  s.goals_against,
            "GD":  s.goal_diff,
            "Pts": s.points,
        }
        for s in standings
    ])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Bandy Standings Parser ===\n")

    # Try fast API first
    raw = fetch_standings_api()

    if not raw:
        print("Falling back to browser scraping (Playwright)…")
        raw = fetch_standings_browser()

    if not raw:
        print("Could not retrieve data. Check your network / install Playwright.")
        return

    # Pretty-print raw JSON (first entry for inspection)
    print("Raw sample (first entry):")
    print(json.dumps(raw[0], indent=2, ensure_ascii=False))
    print()

    # Parse into structured objects
    standings = parse_standings(raw)
    df = standings_to_df(standings)

    print("Standings table:")
    print(df.to_string(index=False))
    print()

    # Save to CSV
    out = f"bandy_standings_tournament_{TOURNAMENT_ID}.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Saved → {out}")

    # Also fetch matches if available
    matches_raw = fetch_matches_api()
    if matches_raw:
        print(f"\nFetched {len(matches_raw)} match records.")
        # Flatten common fields
        match_rows = []
        for m in matches_raw:
            match_rows.append({
                "matchId":   m.get("matchId") or m.get("id"),
                "date":      m.get("date") or m.get("matchDate"),
                "home":      (m.get("homeTeam") or {}).get("name", m.get("homeTeamName", "")),
                "away":      (m.get("awayTeam") or {}).get("name", m.get("awayTeamName", "")),
                "homeScore": m.get("homeScore") or m.get("homeGoals"),
                "awayScore": m.get("awayScore") or m.get("awayGoals"),
                "status":    m.get("status") or m.get("matchStatus"),
            })
        mdf = pd.DataFrame(match_rows)
        mout = f"bandy_matches_tournament_{TOURNAMENT_ID}.csv"
        mdf.to_csv(mout, index=False, encoding="utf-8-sig")
        print(f"Saved → {mout}")


if __name__ == "__main__":
    main()