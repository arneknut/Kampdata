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

# ── NIF Sport API ──────────────────────────────────────────────────────────────
# Kampsenteret er en SPA som kaller NIF sitt sports-API i bakgrunnen.
# Base-URL og match-ID hentes fra hash-fragmentet i nettleseren:
#   #/sport/151/season/.../match/<MATCH_ID>/tab/2
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


def fetch_match_lineups(match_id: int) -> dict:
    """Kaller NIF-API-et og returnerer rå lineup-data for kampen."""
#    url = f"{NIF_API_BASE}/matches/{match_id}/lineups"
    url = f"{NIF_API_BASE}/{match_id}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def extract_away_team(data: dict) -> dict:
    """
    Trekker ut bortelagets navn og spillerliste fra lineup-responsen.
    Returnerer et dict med 'team' og 'players'.
    """
    # NIF-API returnerer typisk {"homeTeam": {...}, "awayTeam": {...}}
    away = data.get("teamOrgId") or data.get("away_team") or {}

    team_name = (
        away.get("teamName")
        or away.get("name")
        or away.get("team_name")
        or "Ukjent bortelag"
    )

    raw_players = (
        away.get("players")
        or away.get("lineup")
        or away.get("participants")
        or []
    )

    players = []
    for p in raw_players:
        number = (
            p.get("shirtNumber")
            or p.get("shirt_number")
            or p.get("jerseyNumber")
            or p.get("number")
        )
        first = p.get("firstName") or p.get("first_name") or ""
        last  = p.get("lastName")  or p.get("last_name")  or ""
        name  = p.get("name") or p.get("fullName") or f"{first} {last}".strip()

        players.append({
            "number": number,
            "name": name,
        })

    # Sorter på spillernummer (None havner bakerst)
    players.sort(key=lambda x: (x["number"] is None, x["number"]))
    return {"team": team_name, "players": players}


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
    parser.add_argument(
        "--pretty", action="store_true", default=True,
        help="Pen formatering av JSON (standard: på)"
    )
    args = parser.parse_args()

    print(f"Henter lineup for kamp-ID {args.match_id} …")
    try:
        raw = fetch_match_lineups(args.match_id)
    except requests.HTTPError as e:
        print(f"HTTP-feil: {e}", file=sys.stderr)
        print(
            "Tips: API-endepunktet kan kreve autentisering eller ha endret seg.\n"
            "Prøv å inspisere nettverkstrafikken i nettleseren (F12 → Network)\n"
            "og finn kall til 'nif.no' eller 'sportsadmin' for riktig URL.",
            file=sys.stderr,
        )
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Nettverksfeil: {e}", file=sys.stderr)
        sys.exit(1)

    result = extract_away_team(raw)

    indent = 2 if args.pretty else None
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=indent)

    print(f"Bortelag : {result['team']}")
    print(f"Spillere : {len(result['players'])} funnet")
    print(f"Lagret til: {args.output}")

    # Forhåndsvisning
    print("\nFørste 5 spillere:")
    for p in result["players"][:5]:
        print(f"  #{p['number']:>3}  {p['name']}")


if __name__ == "__main__":
    main()