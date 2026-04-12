import requests
import json
from dataclasses import dataclass, field
from typing import Optional
from tabulate import tabulate  # pip install tabulate


URL = "https://api.app04.nbf.clh.no/api/v1/nbf/bandy/tournament/players/439465?ttl=180"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}


@dataclass
class Player:
    id: Optional[int] = None
    name: str = ""
    first_name: str = ""
    last_name: str = ""
    jersey_number: Optional[int] = None
    position: str = ""
    team: str = ""
    team_id: Optional[int] = None
    nationality: str = ""
    date_of_birth: str = ""
    goals: int = 0
    assists: int = 0
    games_played: int = 0
    utvisning_5Min: int = 0
    utvisning_10Min: int = 0
    utvisning_RedCard: int = 0
    utvisning_min: int = 0
    
    extra: dict = field(default_factory=dict)  # catch-all for unknown fields

    @property
    def full_name(self) -> str:
        if self.name:
            return self.name
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def points(self) -> int:
        return self.goals + self.assists


def fetch(url: str) -> dict:
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()


def extract_players(data: dict | list) -> list[Player]:
    """
    Handles several common response shapes:
      - {"players": [...]}
      - {"data": {"players": [...]}}
      - {"data": [...]}
      - [...]  (top-level list)
    """
    # Unwrap common envelope patterns
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        raw = (
            data.get("players")
            or data.get("data", {}).get("players")
            or (data.get("data") if isinstance(data.get("data"), list) else None)
            or data.get("results")
            or data.get("items")
            or []
        )
    else:
        raise ValueError(f"Unexpected top-level type: {type(data)}")

    return [parse_player(p) for p in raw]


def _get(*keys, src: dict, default=None):
    """Try multiple key names, return first match."""
    for k in keys:
        if k in src:
            return src[k]
    return default


def parse_player(p: dict) -> Player:
    known_keys = set()

    def pick(*keys, default=None):
        for k in keys:
            known_keys.add(k)
            if k in p:
                return p[k]
        return default

    player = Player(
        id=pick("id", "playerId", "player_id"),
        name=pick("name", "fullName", "full_name", default=""),
        first_name=pick("firstName", "first_name", "forename", default=""),
        last_name=pick("lastName", "last_name", "surname", default=""),
        jersey_number=pick("jerseyNumber", "jersey_number", "shirtNumber", "number"),
        position=pick("position", "positionName", "role", default=""),
        team=pick("orgName", "teamName", "team_name", "club", default=""),
        team_id=pick("teamId", "team_id", "clubId"),
        nationality=pick("nationality", "country", "nation", default=""),
        date_of_birth=pick("dateOfBirth", "date_of_birth", "dob", "birthdate", default=""),
        goals=int(pick("goals", "goalsScored", "g", default=0) or 0),
        assists=int(pick("assistances", "a", default=0) or 0),
        games_played=int(pick("games", "games_played", "matches", "mp", default=0) or 0),

      
        utvisning_5Min=int(pick("uT5", "utvisning5Min", "5Min", default=0) or 0),
        utvisning_10Min=int(pick("uT10", "utvisning10Min", "10Min", default=0) or 0),
        utvisning_RedCard=int(pick("utGrov", "utvisningRedCard", "RedCard", default=0) or 0),
        utvisning_min=int(pick("pim", "utvisning_min", "min", default=0) or 0),

    )

    # Store any unrecognised fields for inspection
    player.extra = {k: v for k, v in p.items() if k not in known_keys}

    return player


def display(players: list[Player], top: int = 20) -> None:
    if not players:
        print("No players found.")
        return

    top_players = sorted(players, key=lambda x: x.points, reverse=True)[:top]

    rows = [
        [
            rank,
            p.full_name,
            p.team,
            p.games_played,
            p.goals,
            p.assists,
            p.points,
            p.utvisning_min,
        ]
        for rank, p in enumerate(top_players, start=1)
    ]

    headers = ["#", "Navn", "Klubb", "Kamper", "Mål", "Assist", "Poeng", "Utv",]
    print(f"Top {top} players (by points):\n")
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))
    print(f"\nShowing {len(top_players)} of {len(players)} total players")


def save_json(players: list[Player], path: str = "SpillerStatistikk.json") -> None:
    out = []
    for p in players:
        d = p.__dict__.copy()
        d["full_name"] = p.full_name
        d["points"] = p.points
        out.append(d)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(players)} players → {path}")


def main():
    print(f"Fetching: {URL}\n")
    data = fetch(URL)

    # Uncomment to inspect raw response:
    # print(json.dumps(data, indent=2, ensure_ascii=False))

    players = extract_players(data)

    if players and players[0].extra:
        print("ℹ️  Unknown fields detected in first player (check .extra):")
        print(json.dumps(players[0].extra, indent=2, ensure_ascii=False), "\n")

    display(players)
    save_json(players)


if __name__ == "__main__":
    main()