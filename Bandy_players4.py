"""
Henter spillernummer og navn for bortelaget i en bandykamp
fra bandyforbundet.no sitt kampsenter, og lagrer resultatet som JSON.

Avhengigheter:
    pip install requests

Bruk:
    python bandy_players.py
    python bandy_players.py --match-id 8357726 --output spillere.json
"""

import argparse
import json
import sys
import requests

NIF_API_BASE = "https://api.app04.nbf.clh.no/api/v1/ta/MatchTeamMembers"

DOMMERE_API = "https://api.app04.nbf.clh.no/api/v1/ta/MatchReferee?matchId=8357726"
MATCH_INFO =  "https://api.app04.nbf.clh.no/api/v1/ta/Match/?matchId=8357726"
LINEUP_INFO = "https://api.app04.nbf.clh.no/api/v1/ta/MatchTeamMembers/8357726"

HEADERS = {
    "Accept": "application/json",
    "Referer": "https://bandyforbundet.no/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
}


def fetch_json(url: str) -> any:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_match_info(match_id: int) -> dict:
    """Henter kampinfo for å finne bortelagets teamOrgId."""
    return fetch_json("https://api.app04.nbf.clh.no/api/v1/ta/Match/?matchId=8357726")


def fetch_referees(match_id: int) -> list[dict]:
    """Henter dommerlisten for kampen."""
    url = f"https://api.app04.nbf.clh.no/api/v1/ta/MatchReferee?matchId={match_id}"
    return fetch_json(url)


def extract_referees(raw: list[dict]) -> list[dict]:
    return [
        {
            "refereeId": r.get("refereeId"),
            "firstName": r.get("firstName", ""),
            "lastName": r.get("lastName", ""),
            "fullName": f"{r.get('firstName', '')} {r.get('lastName', '')}".strip(),
            "refereeType": r.get("refereeType"),
            "orgName": r.get("orgName"),
        }
        for r in raw
    ]


def fetch_lineups(match_id: int) -> list[dict]:
    """Henter spillerlisten (flat liste med teamOrgId per spiller)."""
    return fetch_json(f"{NIF_API_BASE}/{match_id}")


def extract_team_players(org_id: int, name: str, players: list[dict]) -> dict:
    """Filtrerer spillerlisten på teamOrgId og returnerer lag + spillere."""
    team_players = [
        {
            "number": p.get("number"),
            "firstName": p.get("firstName", ""),
            "lastName": p.get("lastName", ""),
            "fullName": f"{p.get('firstName', '')} {p.get('lastName', '')}".strip(),
            "position": p.get("position"),
            "captain": p.get("captain", False),
            "played": p.get("played", False),
        }
        for p in players
        if p.get("teamOrgId") == org_id
    ]
    team_players.sort(
        key=lambda x: (x["number"] is None, int(x["number"]) if str(x.get("number", "")).isdigit() else float("inf"))
    )
    return {"teamOrgId": org_id, "team": name, "players": team_players}


def extract_teams(match_info: dict, players: list[dict]) -> tuple[dict, dict]:
    """Returnerer (hjemmelag, bortelag) med sine spillere."""
    home = extract_team_players(
        match_info.get("hometeamId"),
        match_info.get("hometeam") or "Ukjent hjemmelag",
        players,
    )
    away = extract_team_players(
        match_info.get("awayteamId"),
        match_info.get("awayteam") or "Ukjent bortelag",
        players,
    )
    return home, away


def main():
    parser = argparse.ArgumentParser(
        description="Hent spillernummer og navn for bortelaget i en bandykamp."
    )
    parser.add_argument(
        "--match-id", type=int, default=8357726,
        help="Kamp-ID fra URL-fragmentet (standard: 8357726)"
    )
    parser.add_argument(
        "--output", default="Spillere.json",
        help="Filnavn for JSON-utdata (standard: Spillere.json)"
    )
    args = parser.parse_args()

    print(f"Henter kampinfo for kamp-ID {args.match_id} …")
    try:
        match_info = fetch_match_info(args.match_id)
        print("Henter spillerliste …")
        players = fetch_lineups(args.match_id)
        print("Henter dommerliste …")
        raw_refs = fetch_referees(args.match_id)
    except requests.HTTPError as e:
        print(f"HTTP-feil: {e}", file=sys.stderr)
        print(
            "Tips: Inspiser nettverkstrafikken i nettleseren (F12 → Network)\n"
            "og finn kall til 'nif.no' eller 'sportsadmin' for riktig URL.",
            file=sys.stderr,
        )
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Nettverksfeil: {e}", file=sys.stderr)
        sys.exit(1)

    home, away = extract_teams(match_info, players)
    result = {
        "matchId": args.match_id,
        "homeTeam": home,
        "awayTeam": away,
        "referees": extract_referees(raw_refs),
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Hjemmelag : {result['homeTeam']['team']} — {len(result['homeTeam']['players'])} spillere")
    print(f"Bortelag  : {result['awayTeam']['team']} — {len(result['awayTeam']['players'])} spillere")
    print(f"Dommere   : {len(result['referees'])} funnet")
    print(f"Lagret til: {args.output}")

    for label, team in [("Hjemmelag", result["homeTeam"]), ("Bortelag", result["awayTeam"])]:
        print(f"\n{label} – første 5 spillere:")
        for p in team["players"][:5]:
            print(f"  #{str(p['number']):>3}  {p['fullName']}  ({p['position']})")

    print("\nDommere:")
    for r in result["referees"]:
        print(f"  {r['refereeType']:20}  {r['fullName']}  ({r['orgName']})")


if __name__ == "__main__":
    main()