import requests
import json

URL = "https://api.app04.nbf.clh.no/api/v1/ta/TournamentStandings/"
PARAMS = {"tournamentId": 439465, "ttl": 180}
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tournament Standings</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #f0f2f5;
      display: flex;
      justify-content: center;
      padding: 40px 16px;
    }}
    .card {{
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0,0,0,.10);
      overflow: hidden;
      width: 100%;
      max-width: 780px;
    }}
    .card-header {{
      background: linear-gradient(135deg, #1a3233 0%, #285f6f 100%);
      color: #fff;
      padding: 20px 28px;
    }}
    .card-header h1 {{
      font-size: 1.3rem;
      font-weight: 700;
      letter-spacing: .5px;
    }}
    .card-header p {{
      font-size: .85rem;
      opacity: .75;
      margin-top: 4px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: .92rem;
    }}
    thead th {{
      background: #f7f8fa;
      color: #6b7280;
      font-size: .78rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: .6px;
      padding: 10px 14px;
      border-bottom: 2px solid #e5e7eb;
      text-align: center;
    }}
    thead th.col-team {{ text-align: left; }}
    @keyframes slideIn {{
      from {{ transform: translateX(-60px); opacity: 0; }}
      to   {{ transform: translateX(0);    opacity: 1; }}
    }}
    tbody tr {{
      border-bottom: 1px solid #f0f2f5;
      transition: background .15s;
      opacity: 0;
      animation: slideIn .4s ease forwards;
    }}
    tbody tr:nth-child(even) {{ background: #f0f7f9; }}
    tbody tr:nth-child(odd)  {{ background: #ffffff; }}
    tbody tr:last-child {{ border-bottom: none; }}
    tbody tr:hover {{ background: #eaf4f6; }}
    tbody tr.top3 td.col-pos {{ font-weight: 700; color: #285f6f; }}
    td {{
      padding: 11px 14px;
      text-align: center;
      color: #374151;
    }}
    td.col-pos {{ font-weight: 600; width: 42px; }}
    td.col-team {{
      text-align: left;
      font-weight: 500;
      color: #111827;
      min-width: 160px;
    }}
    td.col-pts {{
      font-weight: 700;
      color: #285f6f;
      font-size: 1rem;
    }}
    .medal {{ margin-right: 4px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="card-header">
      <h1>Tournament Standings</h1>
      <p>Tournament ID: {tournament_id} &nbsp;·&nbsp; {team_count} teams</p>
    </div>
    <table>
      <thead>
        <tr>
          <th class="col-pos">Pos</th>
          <th class="col-team">Team</th>
          <th>P</th>
          <th>W</th>
          <th>D</th>
          <th>L</th>
          <th>GF</th>
          <th>GA</th>
          <th>Pts</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </div>
</body>
</html>"""

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

def fetch_standings():
    resp = requests.get(URL, params=PARAMS, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    for key in ("standings", "data", "results"):
        if key in data:
            return data[key]
    raise ValueError(f"Unexpected response structure: {list(data.keys())}")

def build_row(entry: dict) -> str:
    pos  = entry.get("position", "")
    team = entry.get("orgName", "")
    p    = entry.get("matches", 0)
    w    = entry.get("victories", 0)
    d    = entry.get("draws", 0)
    l    = entry.get("losses", 0)
    gf   = entry.get("goalsScored", 0)
    ga   = entry.get("goalsConceeded", 0)
    pts  = entry.get("totalPoints", 0)

    medal = f'<span class="medal">{MEDALS[pos]}</span>' if pos in MEDALS else ""
    top3_class = " top3" if pos in MEDALS else ""

    delay = f"animation-delay: {(pos - 1) * 150}ms" if isinstance(pos, int) else ""
    return f"""        <tr class="{top3_class}" style="{delay}">
          <td class="col-pos">{pos}</td>
          <td class="col-team">{medal}{team}</td>
          <td>{p}</td>
          <td>{w}</td>
          <td>{d}</td>
          <td>{l}</td>
          <td>{gf}</td>
          <td>{ga}</td>
          <td class="col-pts">{pts}</td>
        </tr>"""

def generate_html(output_file="standings.html"):
    teams = fetch_standings()
    teams_sorted = sorted(teams, key=lambda x: x.get("position") or 999)

    rows = "\n".join(build_row(t) for t in teams_sorted)
    html = HTML_TEMPLATE.format(
        tournament_id=PARAMS["tournamentId"],
        team_count=len(teams),
        rows=rows,
    )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    generate_html()