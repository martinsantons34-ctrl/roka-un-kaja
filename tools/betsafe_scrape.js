// Betsafe.lv Čempionu līgas tirgi: palaid Claude pārlūkā (javascript_exec) uz Betsafe Čempionu līgas lapas
// https://www.betsafe.lv/en/sportsbook/football/champions-league/champions-league?tab=liveAndUpcoming
// 1. reizē: `await __bsInit()` (savāc spēļu event-id); tad atkārto `await __bsGo(3)`, līdz atgriež tukšu sarakstu;
// beigās `JSON.stringify(__bsRes)` = neapstrādātie dati tools/betsafe_markets.py skriptam.
window.__bsTxt = function txt(n) { let s = ""; for (const c of n.childNodes) { if (c.nodeType === 3) s += c.textContent + " "; else if (c.nodeType === 1 && c.tagName !== "STYLE" && c.tagName !== "SCRIPT") { if (c.shadowRoot) s += txt(c.shadowRoot); s += txt(c); } } return s; };
window.__bsInit = async function () {
  const sc = (n, o) => { for (const c of n.querySelectorAll("*")) { if (c.scrollHeight > c.clientHeight + 50 && /(auto|scroll)/.test(getComputedStyle(c).overflowY)) o.push(c); if (c.shadowRoot) sc(c.shadowRoot, o); } return o; };
  const rows = (n, o) => { for (const c of n.querySelectorAll("*")) { if (c.tagName === "OBG-EVENT-ROW-CONTAINER") o.push(c.getAttribute("event-id")); if (c.shadowRoot) rows(c.shadowRoot, o); } return o; };
  const ids = new Set();
  for (let k = 0; k < 12; k++) { rows(document, []).forEach(i => ids.add(i)); window.scrollTo(0, document.body.scrollHeight); sc(document, []).forEach(e => e.scrollTop = e.scrollHeight); await new Promise(r => setTimeout(r, 2000)); }
  rows(document, []).forEach(i => ids.add(i));
  window.__bsIds = [...ids]; window.__bsRes = window.__bsRes || {}; return window.__bsIds.length;
};
window.__bsOne = async function (prevHead) {
  const T = () => window.__bsTxt(document.body).replace(/\s+/g, " ");
  const head = () => { const t = T(), i = t.indexOf("Match Result Money"); return i < 0 ? "" : t.slice(i, i + 120); };
  let t = ""; for (let k = 0; k < 20; k++) { const h = head(); t = T(); if (h && h !== prevHead && t.includes("Both teams to score Yes")) break; await new Promise(r => setTimeout(r, 1000)); }
  const i = t.indexOf("Match Result Money"); if (i < 0) return { head: "" };
  const main = t.slice(i, t.indexOf("The score displayed", i)), f = Number, R = {};
  let m = main.match(/Match Result Money Placed [\d% ]+ (.+?) ([\d.]+) Draw ([\d.]+) (.+?) ([\d.]+) /); if (m) { R.h = m[1]; R.a = m[4]; R.o = [f(m[2]), f(m[3]), f(m[5])]; }
  m = main.match(/Total Goals Over 2\.5 ([\d.]+) Under 2\.5 ([\d.]+)/); if (m) R.ou25 = [f(m[1]), f(m[2])];
  m = main.match(/Both teams to score Yes ([\d.]+) No ([\d.]+)/); if (m) R.btts = [f(m[1]), f(m[2])];
  m = main.match(/Double chance .+? or Draw ([\d.]+) .+? or .+? ([\d.]+) Draw or .+? ([\d.]+)/); if (m) R.dc = [f(m[1]), f(m[2]), f(m[3])];
  const hb = ((main.match(/Handicap \(3-way\) (.+?) Both teams to score/) || [])[1] || "") + " ";
  R.h3 = [...hb.matchAll(/(.+?) ([+-]\d+) ([\d.]+) /g)].map(x => [x[1].trim(), x[2], f(x[3])]);
  const leaf = (n, o) => { for (const c of n.querySelectorAll("*")) { if (c.childElementCount === 0 && c.textContent.trim() === "Handicaps") o.push(c); if (c.shadowRoot) leaf(c.shadowRoot, o); } return o; };
  const L = leaf(document, []); if (L.length) { L[0].click(); for (let k = 0; k < 8; k++) { await new Promise(r => setTimeout(r, 1000)); t = T(); if (t.includes("Asian Handicap")) break; } }
  const j = t.indexOf("Asian Handicap"); R.ah = [];
  if (j >= 0) for (const x of t.slice(j + 15, j + 700).matchAll(/(.+?) ([+-]\d+(?:\.\d+)?) ([\d.]+) /g)) { if (x[1].trim().split(" ").length > 4) break; R.ah.push([x[1].trim(), x[2], f(x[3])]); if (R.ah.length >= 12) break; }
  R.head = head(); return R;
};
window.__bsGo = async function (n) {
  const out = [];
  for (const id of window.__bsIds) {
    if (window.__bsRes[id] && window.__bsRes[id].h) continue; if (out.length >= n) break;
    history.pushState({}, "", "/en/sportsbook/football/champions-league/champions-league/m?eventId=" + id); dispatchEvent(new PopStateEvent("popstate", { state: {} }));
    await new Promise(r => setTimeout(r, 1500));
    const R = await window.__bsOne(window.__bsLast || ""); window.__bsLast = R.head; delete R.head;
    window.__bsRes[id] = R.h ? R : { failed: true }; out.push(id + " " + (R.h ? R.h + " - " + R.a : "NEIZDEVĀS"));
  }
  return out;
};
"ok";
