#!/usr/bin/env python3
"""Build h2h.json for the betting page from ESPN's public soccer API.

For every match of the given rounds in bets.json it finds the ESPN event and team ids,
then collects: each team's recent results (all competitions), past meetings of the two
teams, and both teams' domestic league tables.

Usage: python3 tools/h2h.py [md ...]   (default: the "current" round in bets.json)
"""
import json, sys, time, difflib, unicodedata, urllib.request
from datetime import datetime, timezone

API = "https://site.api.espn.com/apis/site/v2/sports/soccer"
FORM_N, H2H_SEASONS = 15, 8
_cache = {}

def get(url):
    if url in _cache: return _cache[url]
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "roka-un-kaja/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                _cache[url] = json.load(r); time.sleep(0.15); return _cache[url]
        except Exception as e:
            err = e; time.sleep(1 + attempt * 2)
    print("WARN", url, err, file=sys.stderr); _cache[url] = {}; return {}

def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    for w in ("fc ", " fc", "cf ", "sk ", " fk", "fk ", "club ", "afc ", "sc "): s = s.replace(w, " ")
    return " ".join(s.replace(".", " ").replace("/", " ").split())

ALIAS = {"atleti": "atletico madrid", "paris": "paris saint-germain", "man utd": "manchester united", "man city": "manchester city",
         "inter": "internazionale", "b. dortmund": "borussia dortmund", "s. bratislava": "slovan bratislava",
         "leipzig": "rb leipzig", "bayern munchen": "bayern munich", "slavia praha": "slavia prague", "lask": "lask linz"}

def sim(a, b):
    a, b = norm(ALIAS.get(norm(a), a)), norm(b)
    return 1.0 if a == b or a in b or b in a else difflib.SequenceMatcher(None, a, b).ratio()

def score(c):
    v = (c.get("score") or {})
    v = v.get("displayValue") if isinstance(v, dict) else v
    try: return int(float(v))
    except (TypeError, ValueError): return None

def team_games(tid, seasons):
    """Completed games for a team, newest first, across all competitions."""
    out = {}
    urls = [f"{API}/all/teams/{tid}/schedule"] + [f"{API}/all/teams/{tid}/schedule?season={s}" for s in seasons] \
         + [f"{API}/uefa.champions/teams/{tid}/schedule"]
    for u in urls:
        for e in get(u).get("events", []):
            c = e["competitions"][0]
            if not c.get("status", {}).get("type", {}).get("completed"): continue
            cs = {x["homeAway"]: x for x in c["competitors"]}
            if "home" not in cs or "away" not in cs: continue
            hs, as_ = score(cs["home"]), score(cs["away"])
            if hs is None or as_ is None: continue
            lg = e.get("league") or {}
            out[e["id"]] = {"date": e["date"][:10], "comp": lg.get("abbreviation") or lg.get("name") or "",
                            "home": cs["home"]["team"]["displayName"], "homeId": cs["home"]["team"]["id"],
                            "away": cs["away"]["team"]["displayName"], "awayId": cs["away"]["team"]["id"], "hs": hs, "as": as_}
    return sorted(out.values(), key=lambda g: g["date"], reverse=True)

def res_for(g, tid):
    me, op = (g["hs"], g["as"]) if g["homeId"] == tid else (g["as"], g["hs"])
    return "U" if me > op else "Z" if me < op else "N"

def standings(slug):
    d = get(f"https://site.api.espn.com/apis/v2/sports/soccer/{slug}/standings")
    groups = d.get("children") or []
    tables = []
    for ch in groups:
        rows = []
        for e in ch.get("standings", {}).get("entries", []):
            st = {s.get("name"): s.get("displayValue") for s in e.get("stats", [])}
            rows.append({"rank": int(st.get("rank") or 0), "id": e["team"]["id"], "team": e["team"]["displayName"],
                         "gp": st.get("gamesPlayed"), "w": st.get("wins"), "d": st.get("ties"), "l": st.get("losses"),
                         "gd": st.get("pointDifferential"), "pts": st.get("points")})
        rows.sort(key=lambda r: r["rank"] or 99)
        tables.append({"name": ch.get("name") or d.get("name"), "rows": rows})
    return {"name": d.get("name") or slug, "tables": tables}

def main():
    bets = json.load(open("bets.json", encoding="utf-8"))
    mds = [int(a) for a in sys.argv[1:]] or [bets["current"]]
    try: out = json.load(open("h2h.json", encoding="utf-8"))
    except Exception: out = {}
    out.setdefault("teams", {}); out.setdefault("leagues", {}); out.setdefault("pairs", {})
    now = datetime.now(timezone.utc); seasons = [now.year - 1 - i for i in range(H2H_SEASONS)]
    for rnd in bets["rounds"]:
        if rnd["md"] not in mds: continue
        events = {}
        for day in sorted({m["kickoff"][:10] for m in rnd["matches"]}):
            for e in get(f"{API}/uefa.champions/scoreboard?dates={day.replace('-', '')}").get("events", []):
                cs = {x["homeAway"]: x["team"] for x in e["competitions"][0]["competitors"]}
                events[e["id"]] = (day, cs["home"], cs["away"])
        for m in rnd["matches"]:
            cand = [(sim(m["home"], h["displayName"]) + sim(m["away"], a["displayName"]), eid, h, a)
                    for eid, (day, h, a) in events.items() if day == m["kickoff"][:10]]
            if not cand: print("NO EVENT", m["home"], m["away"], file=sys.stderr); continue
            s, eid, h, a = max(cand, key=lambda x: x[0])
            if s < 1.2: print("WEAK MATCH", m["home"], m["away"], h["displayName"], a["displayName"], s, file=sys.stderr)
            m["espn"] = {"event": eid, "home": h["id"], "away": a["id"]}
            for t in (h, a):
                tid = t["id"]
                info = get(f"{API}/all/teams/{tid}").get("team", {})
                slug = (info.get("defaultLeague") or {}).get("slug")
                if slug and slug.startswith("uefa."): slug = None  # ESPN has no domestic league for this club
                games = team_games(tid, seasons[:2])
                out["teams"][tid] = {"name": t["displayName"], "league": slug, "domestic": bool(slug),
                                     "form": [dict(g, res=res_for(g, tid)) for g in games[:FORM_N]]}
                if slug and slug not in out["leagues"]: out["leagues"][slug] = standings(slug)
            pair = [g for g in team_games(h["id"], seasons) if a["id"] in (g["homeId"], g["awayId"])]
            out["pairs"][f'{h["id"]}-{a["id"]}'] = pair[:12]
            print(f'{m["home"]} – {m["away"]}: h2h {len(pair)}, form {len(out["teams"][h["id"]]["form"])}/{len(out["teams"][a["id"]]["form"])}')
    out["generatedAt"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    json.dump(out, open("h2h.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(bets, open("bets.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2); open("bets.json", "a").write("\n")

if __name__ == "__main__":
    main()
