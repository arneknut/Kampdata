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


def fetch_lineups(match_id: int) -> list[dict]:
    """Henter spillerlisten (flat liste med teamOrgId per spiller)."""
    return fetch_json(f"{NIF_API_BASE}/{match_id}")

def fetch_referees(match_id: int) -> list[dict]:
    """Henter dommere for kampen."""
    return fetch_json(f"{DOMMERE_API}")


def extract_away_players(match_info: dict, players: list[dict]) -> dict:
    """
    Finner bortelagets teamOrgId fra kampinfo og filtrerer
    spillerlisten deretter.
    """
    away_org_id = match_info.get("awayteamId")
    away_name   = match_info.get("awayteam") or "Ukjent bortelag"

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

def extract_home_players(match_info: dict, players: list[dict]) -> dict:
    """
    Finner hjemmelagets teamOrgId fra kampinfo og filtrerer
    spillerlisten deretter.
    """
    home_org_id = match_info.get("hometeamId")
    home_name   = match_info.get("hometeam") or "Ukjent hjemmelag"

    home_players = [
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
        if p.get("teamOrgId") == home_org_id
    ]

    # Sorter på nummer (None bakerst)
    home_players.sort(
        key=lambda x: (x["number"] is None, int(x["number"]) if str(x.get("number", "")).isdigit() else float("inf"))
    )

    return {
        "teamOrgId": home_org_id,
        "team": home_name,
        "players": home_players,
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

    resultAway = extract_away_players(match_info, players)

    """with open(args.output, "w", encoding="utf-8") as f:"""
    with open("Spillere-Bortelag.json", "w", encoding="utf-8") as f:
        json.dump(resultAway, f, ensure_ascii=False, indent=2)

    print(f"Bortelag  : {resultAway['team']} (orgId: {resultAway['teamOrgId']})")
    print(f"Spillere  : {len(resultAway['players'])} funnet")
    print(f"Lagret til: Spillere-Bortelag.json")

    print("\nBortelag - Spillere:")
    for p in resultAway["players"]:
        print(f"  #{str(p['number']):>3}  {p['fullName']}  ({p['position']})")


    resultHome = extract_home_players(match_info, players)

    """with open(args.output, "w", encoding="utf-8") as f:"""
    with open("Spillere-Hjemmelag.json", "w", encoding="utf-8") as f:
         json.dump(resultHome, f, ensure_ascii=False, indent=2)

    print(f"Hjemmelag : {resultHome['team']} (orgId: {resultHome['teamOrgId']})")
    print(f"Spillere  : {len(resultHome['players'])} funnet")
    print(f"Lagret til: Spillere-Hjemmelag.json")

    print("\nHjemmelag - Spillere:")
    for p in resultHome["players"]:
        print(f"  #{str(p['number']):>3}  {p['fullName']}  ({p['position']})")


if __name__ == "__main__":
    main()