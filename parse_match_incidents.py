import requests
import argparse
import json
from itertools import groupby


INCIDENT_TYPES = {"Mål", "Utvisning", "Straffeslag"}


def fetch_incidents(match_id: int, ttl: int = 180) -> list:
    url = "https://api.app04.nbf.clh.no/api/v1/ta/MatchIncidents/"
    params = {"matchId": match_id, "ttl": ttl}
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MatchParser/1.0)",
        "Accept": "application/json",
    }
    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else data.get("matchIncidents", data.get("data", []))


def format_group(minute, incidents: list) -> str:
    minute_str = f"{minute}'" if minute is not None else "—'"
    lines = [
        f"  {'═'*42}",
        f"  Minute {minute_str}  ({len(incidents)} incident{'s' if len(incidents) > 1 else ''})",
        f"  {'─'*42}",
    ]
    for inc in incidents:
        name = f"{inc.get('firstName', '')} {inc.get('lastName', '')}".strip() or "—"
        team = inc.get("team", "—")
        incident_type = inc.get("incidentType", "—")
        subtype = inc.get("incidentSubType") or "—"
        incident_id = inc.get("matchIncidentId", "—")
        icon = "⚽" if incident_type == "Mål" else "🟥"
        lines.append(f"  {icon} {incident_type:<12} {subtype:<18} {name}  (Team {team},  ID: {incident_id})")
    return "\n".join(lines)


def full_name(inc: dict) -> str | None:
    name = f"{inc.get('firstName', '') or ''} {inc.get('lastName', '') or ''}".strip()
    return name or None


def merge_incidents(incidents: list) -> list:
    """Merge Mål, Straffeslag and Utvisning sub-records each into a single record."""
    goals       = [inc for inc in incidents if inc.get("incidentType") == "Mål"]
    straffe     = [inc for inc in incidents if inc.get("incidentType") == "Straffeslag"]
    utvisnings  = [inc for inc in incidents if inc.get("incidentType") == "Utvisning"]
    others      = [inc for inc in incidents if inc.get("incidentType") not in ("Mål", "Straffeslag", "Utvisning")]

    result = []

    def merge_maal_like(group, incident_type):
        base   = next((inc for inc in group if not inc.get("incidentSubType")), group[0])
        scorer = next((inc for inc in group if inc.get("incidentSubType") == "Målscorer"), None)
        assist = next((inc for inc in group if inc.get("incidentSubType") == "Assist"), None)
        return {
            "matchIncidentId":  base.get("matchIncidentId"),
            "incidentType":     incident_type,
            "incidentSubType1": scorer.get("incidentSubType") if scorer else None,
            "fullName1":        full_name(scorer) if scorer else None,
            "incidentSubType2": assist.get("incidentSubType") if assist else None,
            "fullName2":        full_name(assist) if assist else None,
            "team":             base.get("team"),
            "time":             base.get("time"),
            "period":           base.get("period"),
            "personId":         scorer.get("personId") if scorer else base.get("personId"),
        }

    # --- Merge Mål ---
    if goals:
        result.append(merge_maal_like(goals, "Mål"))

    # --- Merge Straffeslag ---
    if straffe:
        parent = next((inc for inc in straffe if not inc.get("parentId")), straffe[0])
        child  = next((inc for inc in straffe if inc.get("parentId")), None)
        named  = child if child else parent
        result.append({
            "matchIncidentId":  parent.get("matchIncidentId"),
            "incidentType":     "Straffeslag",
            "incidentSubType":  parent.get("incidentSubType"),
            "fullName":         full_name(named),
            "team":             parent.get("team"),
            "time":             parent.get("time"),
            "period":           parent.get("period"),
            "personId":         named.get("personId"),
        })

    # --- Merge Utvisning ---
    if utvisnings:
        parent = next((inc for inc in utvisnings if not inc.get("parentId")), utvisnings[0])
        child  = next((inc for inc in utvisnings if inc.get("parentId")), None)
        named  = child if child else parent
        result.append({
            "matchIncidentId":  parent.get("matchIncidentId"),
            "incidentType":     "Utvisning",
            "incidentSubType1": parent.get("incidentSubType"),
            "incidentSubType2": child.get("incidentSubType") if child else None,
            "fullName":         full_name(named),
            "team":             parent.get("team"),
            "time":             parent.get("time"),
            "period":           parent.get("period"),
            "personId":         named.get("personId"),
        })

    return result + others


def main():
    parser = argparse.ArgumentParser(description="Fetch and display recent match incidents.")
    parser.add_argument("match_id", type=int, help="Match ID to fetch incidents for")
    parser.add_argument("--ttl", type=int, default=180, help="Cache TTL in seconds (default: 180)")
    parser.add_argument("--top", type=int, default=5, help="Number of most recent minute-groups to show (default: 5)")
    args = parser.parse_args()

    print(f"Fetching incidents for match {args.match_id} …\n")

    try:
        incidents = fetch_incidents(args.match_id, args.ttl)
    except requests.HTTPError as e:
        print(f"HTTP error: {e}")
        return
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return

    if not incidents:
        print("No incidents returned.")
        return

    filtered = [inc for inc in incidents if inc.get("incidentType") in INCIDENT_TYPES]

    print(f"Total incidents : {len(incidents)}")
    print(f"Mål + Utvisning + Straffeslag : {len(filtered)}")

    if not filtered:
        print("No matching incidents found.")
        return

    sorted_incidents = sorted(
        filtered,
        key=lambda x: (x.get("time") is not None, x.get("time", 0)),
        reverse=True,
    )

    groups = [(minute, list(group)) for minute, group in groupby(sorted_incidents, key=lambda x: x.get("time"))]
    recent_groups = groups if args.top == 0 else groups[:args.top]
    label = "ALL" if args.top == 0 else str(args.top)

    print(f"\n{'═'*44}")
    print(f"  {label} MOST RECENT EVENTS (grouped by minute)")
    print(f"{'═'*44}")
    for minute, group_incidents in recent_groups:
        print(format_group(minute, group_incidents))
    print(f"  {'═'*42}\n")

    # Write results to JSON file
    output = {
        "matchId": args.match_id,
        "totalIncidents": len(incidents),
        "filteredIncidents": len(filtered),
        "groups": [
            {
                "minute": minute,
                "incidents": merge_incidents(group_incidents),
            }
            for minute, group_incidents in recent_groups
        ],
    }

    json_file = f"incidents_{args.match_id}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Results written to {json_file}")


if __name__ == "__main__":
    main()