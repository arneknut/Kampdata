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
    return fetch_json(f"https://api.app04.nbf.clh.no/api/v1/ta/Match/?matchId=8357726")


def fetch_lineups(match_id: int) -> list[dict]:
    """Henter spillerlisten (flat liste med teamOrgId per spiller)."""
    return fetch_json(f"{NIF_API_BASE}/{match_id}")


def extract_away_players(match_info: dict, players: list[dict]) -> dict:
    """
    Finner bortelagets teamOrgId fra kampinfo og filtrerer
    spillerlisten deretter.
    """
    away_org_id = (
        match_info.get("awayTeamOrgId")
        or match_info.get("awayTeam", {}).get("orgId")
        or match_info.get("awayTeam", {}).get("teamOrgId")
    )
    away_name = (
        match_info.get("awayTeamName")
        or match_info.get("awayTeam", {}).get("name")
        or "Ukjent bortelag"
    )

    if away_org_id is None:
        # Fallback: det laget med flest spillere som ikke er hjemmelaget
        home_org_id = (
            match_info.get("homeTeamOrgId")
            or match_info.get("homeTeam", {}).get("orgId")
        )
        team_ids = {p["teamOrgId"] for p in players if p.get("teamOrgId")}
        away_org_id = next(
            (tid for tid in team_ids if tid != home_org_id), None
        )

    away_players = [
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
        if p.get("teamOrgId") == away_org_id
    ]

    # Sorter på nummer (None bakerst)
    away_players.sort(
        key=lambda x: (x["number"] is None, int(x["number"]) if str(x.get("number", "")).isdigit() else float("inf"))
    )

    return {
        "teamOrgId": away_org_id,
        "team": away_name,
        "players": away_players,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Hent spillernummer og navn for bortelaget i en bandykamp."
    )
    parser.add_argument(
        "--match-id", type=int, default=8357726,
        help="Kamp-ID fra URL-fragmentet (standard: 8357726)"
    )
    parser.add_argument(
        "--output", default="bortelag_spillere.json",
        help="Filnavn for JSON-utdata (standard: bortelag_spillere.json)"
    )
    args = parser.parse_args()

    print(f"Henter kampinfo for kamp-ID {args.match_id} …")
    try:
        match_info = fetch_match_info(args.match_id)
        print("Henter spillerliste …")
        players = fetch_lineups(args.match_id)
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

    result = extract_away_players(match_info, players)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Bortelag  : {result['team']} (orgId: {result['teamOrgId']})")
    print(f"Spillere  : {len(result['players'])} funnet")
    print(f"Lagret til: {args.output}")

    print("\nFørste 5 spillere:")
    for p in result["players"][:5]:
        print(f"  #{str(p['number']):>3}  {p['fullName']}  ({p['position']})")


if __name__ == "__main__":
    main()