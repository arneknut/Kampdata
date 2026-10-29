"""
Parser for NBF Bandy Tournament Teams API
Endpoint: /api/v1/nbf/bandy/tournament/teams/{tournament_id}
"""

import argparse

import requests
import json
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://api.app04.nbf.clh.no/api/v1/nbf/bandy"
TOURNAMENT_ID = 0
TTL = 180

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "NBF-Parser/1.0",
}


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class Team:
    id: Optional[int] = None
    name: Optional[str] = None
    short_name: Optional[str] = None
    club_id: Optional[int] = None
    club_name: Optional[str] = None
    logo_url: Optional[str] = None
    group: Optional[str] = None
    # Store any extra fields we didn't anticipate
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Team":
        known = {
            "id":         d.get("id") or d.get("teamId"),
            "name":       d.get("name") or d.get("teamName"),
            "short_name": d.get("shortName") or d.get("abbr"),
            "club_id":    d.get("clubId"),
            "club_name":  d.get("clubName"),
            "logo_url":   d.get("logoUrl") or d.get("logo") or d.get("crestUrl"),
            "group":      d.get("group") or d.get("groupName"),
        }
        used_keys = {"id", "teamId", "name", "teamName", "shortName", "abbr",
                     "clubId", "clubName", "logoUrl", "logo", "crestUrl",
                     "group", "groupName"}
        extra = {k: v for k, v in d.items() if k not in used_keys}
        return cls(**known, extra=extra)

    def display(self) -> str:
        parts = [f"  [{self.id}] {self.name}"]
        if self.short_name:
            parts.append(f"        Short name : {self.short_name}")
        if self.club_name:
            parts.append(f"        Club       : {self.club_name} (id={self.club_id})")
        if self.group:
            parts.append(f"        Group      : {self.group}")
        if self.logo_url:
            parts.append(f"        Logo       : {self.logo_url}")
        if self.extra:
            parts.append(f"        Extra      : {self.extra}")
        return "\n".join(parts)


# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch_tournament_teams(tournament_id: int, ttl: int = TTL) -> dict:
    url = f"{BASE_URL}/tournament/teams/{tournament_id}"
    params = {"ttl": ttl}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ── Parse ─────────────────────────────────────────────────────────────────────

def parse_teams(data: dict) -> list[Team]:
    """
    Handles multiple common response shapes:
      - {"teams": [...]}
      - {"data": {"teams": [...]}}
      - {"data": [...]}
      - [...]   (bare list)
    """
    if isinstance(data, list):
        raw_teams = data
    elif "teams" in data:
        raw_teams = data["teams"]
    elif "data" in data:
        inner = data["data"]
        raw_teams = inner.get("teams", inner) if isinstance(inner, dict) else inner
    else:
        # Fall back: grab the first list value found
        raw_teams = next((v for v in data.values() if isinstance(v, list)), [])

    return [Team.from_dict(t) for t in raw_teams if isinstance(t, dict)]


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(teams: list[Team], tournament_id: int, raw: dict) -> None:
    print("=" * 60)
    print(f"  NBF Bandy — Tournament {tournament_id}")
    print(f"  Fetched : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Teams   : {len(teams)}")
    print("=" * 60)

    if not teams:
        print("  ⚠  No teams found. Raw response keys:", list(raw.keys()))
        return

    # Group by group/division if available
    groups: dict[str, list[Team]] = {}
    for t in teams:
        key = t.group or "—"
        groups.setdefault(key, []).append(t)

    for grp, members in sorted(groups.items()):
        print(f"\n  Group: {grp}  ({len(members)} teams)")
        print("  " + "-" * 40)
        for t in members:
            print(t.display())

    print("\n" + "=" * 60)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:

    parser = argparse.ArgumentParser(
        description="Henter spillerstatistikk"
    )
    parser.add_argument(
        "--tournament-id", type=int, default=0,
        help="Kamp-ID fra URL-fragmentet (standard: 8357726)"
    )
    parser.add_argument(
        "--output", default="Spillere.json",
        help="Filnavn for JSON-utdata (standard: Spillere.json)"
    )
    args = parser.parse_args()

    print(f"Fetching tournament {args.tournament_id} …")
    try:
        raw = fetch_tournament_teams(args.tournament_id)
    except requests.HTTPError as e:
        print(f"HTTP error: {e.response.status_code} — {e.response.text}")
        return
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return

    # Optionally save raw response for inspection
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    print(f"Raw response saved to {args.output}")

    teams = parse_teams(raw)
    print_report(teams, args.tournament_id, raw)


if __name__ == "__main__":
    main()