"""Uzbūvē betsafe.json (Betsafe tirgi un idejas katrai spēlei) no tools/betsafe_scrape.js datiem.

python3 tools/betsafe_markets.py <neapstrādātie.json> <idejas.json> <kārta>
idejas.json: {"<mājinieki bets.json>": [["1x2"|"btts"|"ah"|"h3", "home"|"away"|"y"|"n"|"home:-1.5", "Nosaukums", "Kāpēc (latviski)"], ...]}
Spēles bez jauniem datiem saglabā iepriekšējos betsafe.json datus.
"""
import json, sys, datetime

raw = json.load(open(sys.argv[1])); tipsin = json.load(open(sys.argv[2])); md = int(sys.argv[3])
bets = json.load(open("bets.json")); rnd = next(r for r in bets["rounds"] if r["md"] == md)
try: old = json.load(open("betsafe.json"))
except Exception: old = {}
oldm = old.get("matches", {}) if old.get("md") == md else {}
ln = lambda s: s.replace("-", "−").replace(".", ",")
MK = {"1x2": "Mača uzvarētājs", "btts": "Abas komandas gūs vārtus", "ah": "Aziātiskais handikaps", "h3": "Handikaps (3 virzienu)"}
out = {"source": "Betsafe.lv", "updatedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "md": md, "matches": {}}
vals = [v for v in raw.values() if v.get("h") and v.get("o")]
for m in rnd["matches"]:
    key = f"{m['home']}|{m['away']}|{m['kickoff'][:10]}"
    o = m["odds"]; v = next((x for x in vals if x["o"] == [o.get("1"), o.get("X"), o.get("2")]), None)
    if not v:
        if key in oldm: out["matches"][key] = oldm[key]
        continue
    H, A, bh, ba = m["home"], m["away"], v["h"], v["a"]
    team = lambda n: H if n == bh else A if n == ba else n
    mk = []
    if v.get("btts"): mk.append({"id": "btts", "name": "Abas komandas gūs vārtus", "sels": [{"id": "y", "label": "Jā", "odds": v["btts"][0]}, {"id": "n", "label": "Nē", "odds": v["btts"][1]}]})
    if v.get("ou25"): mk.append({"id": "ou25", "name": "Vārti kopā: 2,5", "sels": [{"id": "o", "label": "Vairāk par 2,5", "odds": v["ou25"][0]}, {"id": "u", "label": "Mazāk par 2,5", "odds": v["ou25"][1]}]})
    if v.get("dc"): mk.append({"id": "dc", "name": "Dubultā iespēja", "sels": [{"id": "1X", "label": "1X", "odds": v["dc"][0]}, {"id": "12", "label": "12", "odds": v["dc"][1]}, {"id": "X2", "label": "X2", "odds": v["dc"][2]}]})
    h3 = sorted([x for x in v.get("h3", []) if x[0] != "Draw" and 1.3 <= x[2] <= 4.5], key=lambda x: abs(x[2] - 2.0))[:4]
    h3.sort(key=lambda x: (x[0] != bh, float(x[1])))
    if h3: mk.append({"id": "h3", "name": "Handikaps (3 virzienu)", "sels": [{"id": ("home" if x[0] == bh else "away") + ":" + x[1], "label": f"{team(x[0])} {ln(x[1])}", "odds": x[2]} for x in h3]})
    ah = v.get("ah", []); pairs = sorted([ah[i:i + 2] for i in range(0, len(ah) - 1, 2)], key=lambda p: abs(p[0][2] - p[1][2]))[:3]
    pairs.sort(key=lambda p: float(p[0][1]) if p[0][0] == bh else -float(p[0][1]))
    if pairs: mk.append({"id": "ah", "name": "Aziātiskais handikaps", "sels": [{"id": ("home" if x[0] == bh else "away") + ":" + x[1], "label": f"{team(x[0])} {ln(x[1])}", "odds": x[2]} for p in pairs for x in p]})
    def find(mid, sid):
        if mid == "1x2": return {"home": o["1"], "away": o["2"]}.get(sid)
        if mid == "btts": return v["btts"][0 if sid == "y" else 1] if v.get("btts") else None
        side, line = sid.split(":"); nm = bh if side == "home" else ba
        return next((x[2] for x in v.get(mid, []) if x[0] == nm and x[1] == line), None)
    tips = []
    for mid, sid, label, why in tipsin.get(H, []):
        od = find(mid, sid)
        if od is None: print("idejai nav koeficienta:", H, mid, sid, file=sys.stderr); continue
        tips.append({"id": {"home": "1", "away": "2"}[sid] if mid == "1x2" else f"{mid}:{sid}", "label": label, "odds": od, "why": why, "market": MK[mid]})
    out["matches"][key] = {"markets": mk, "tips": tips}
json.dump(out, open("betsafe.json", "w"), ensure_ascii=False, indent=1)
print(len(out["matches"]), "spēles betsafe.json")
