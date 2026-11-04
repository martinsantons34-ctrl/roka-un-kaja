// Flashscore supplement for clubs whose domestic league ESPN does not cover.
// Reads a JSON array of team names on stdin, prints JSON {teams:{name:{fsName, league, games:[...]}}, leagues:{key:{name, rows}}}.
// Needs Playwright (global install) and Chromium at /opt/pw-browsers/chromium.
import { createRequire } from 'module';
import { execSync } from 'child_process';
const require = createRequire(import.meta.url);
let pw;
try { pw = require('playwright'); } catch { pw = require(execSync('npm root -g').toString().trim() + '/playwright'); }
const { chromium } = pw;

const names = JSON.parse(await new Promise(r => { let s = ''; process.stdin.on('data', d => s += d); process.stdin.on('end', () => r(s)); }));
const BASE = 'https://www.flashscore.com';
const norm = s => s.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/\b(fc|fk|sk|cf)\b/g, '').replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim();

async function findTeam(name) {
  const u = `https://s.livesport.services/api/v2/search/?q=${encodeURIComponent(name)}&lang-id=1&type-ids=2&project-type-id=1&project-id=2&sport-ids=1`;
  const list = await (await fetch(u)).json();
  const ok = list.filter(x => !/\b(U\d\d|W|B|2|II)\b/.test(x.name));
  const n = norm(name);
  return ok.find(x => norm(x.name) === n) || ok.find(x => norm(x.name).includes(n.split(' ')[0])) || ok[0];
}

function compName(title, country) {
  if (/champions league/i.test(title)) return 'UEFA Champions League';
  if (/europa league/i.test(title)) return 'UEFA Europa League';
  if (/conference league/i.test(title)) return 'UEFA Conference League';
  if (/friendly/i.test(title)) return 'Club Friendly';
  return title;
}

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const out = { teams: {}, leagues: {} };
const now = new Date();
for (const name of names) {
  try {
    const t = await findTeam(name);
    if (!t) { console.error('NOT FOUND', name); continue; }
    await page.goto(`${BASE}/team/${t.url}/${t.id}/results/`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('.event__match', { timeout: 20000 });
    const rows = await page.evaluate(() => {
      const res = []; let comp = null, country = null, href = null;
      for (const el of document.querySelectorAll('.headerLeague__wrapper, .event__match')) {
        if (el.classList.contains('headerLeague__wrapper')) {
          const a = el.querySelector('.headerLeague__title');
          comp = a ? a.textContent.trim() : ''; href = a ? a.getAttribute('href') : null;
          const c = el.querySelector('.headerLeague__category-text'); country = c ? c.textContent.trim() : '';
          continue;
        }
        const q = s => { const x = el.querySelector(s); return x ? x.textContent.trim() : ''; };
        const nm = s => { const x = el.querySelector(s + ' [class*="wcl-name"]') || el.querySelector(s); return x ? x.textContent.trim() : ''; };
        res.push({ comp, country, href, date: q('.event__stageTime, .event__time'), home: nm('.event__homeParticipant'), away: nm('.event__awayParticipant'), hs: q('.event__score--home'), as: q('.event__score--away') });
      }
      return res;
    });
    const games = [];
    let league = null;
    for (const r of rows) {
      if (!/^\d+$/.test(r.hs) || !/^\d+$/.test(r.as)) continue;
      const m = r.date.match(/(\d{2})\.(\d{2})\.(\d{4})?/); if (!m) continue;
      let y = m[3] ? +m[3] : now.getFullYear();
      if (!m[3] && +m[2] > now.getMonth() + 1) y -= 1;
      games.push({ date: `${y}-${m[2]}-${m[1]}`, comp: compName(r.comp, r.country), home: r.home, away: r.away, hs: +r.hs, as: +r.as });
      if (!league && r.href && !/^(EUROPE|WORLD)$/i.test(r.country) && !/cup|pokal|friendly|super ?cup/i.test(r.comp)) league = { title: r.comp, href: r.href, country: r.country };
    }
    out.teams[name] = { fsName: t.name, games: games.slice(0, 20), league: league ? league.href : null };
    if (league && !out.leagues[league.href]) {
      await page.goto(`${BASE}${league.href}standings/`, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForSelector('.ui-table__row', { timeout: 20000 });
      const table = await page.evaluate(() => [...document.querySelectorAll('.ui-table__row')].map(r => {
        const v = [...r.querySelectorAll('.table__cell--value')].map(x => x.textContent.trim());
        const a = r.querySelector('.tableCellParticipant__name');
        const gd = v[5] && /^\d/.test(v[5]) && v[5] !== '0' ? '+' + v[5] : v[5];
        return { rank: parseInt(r.querySelector('.tableCellRank')?.textContent) || 0, team: a ? a.textContent.trim() : '', gp: v[0], w: v[1], d: v[2], l: v[3], gd, pts: v[6] };
      }));
      const title = await page.evaluate(() => document.querySelector('.heading__name')?.textContent.trim() || '');
      const cc = (league.country || '').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
      out.leagues[league.href] = { name: `${title || league.title}${cc ? ' (' + cc + ')' : ''}`, rows: table };
    }
    console.error('OK', name, '->', t.name, games.length, 'games, league', league && league.title);
  } catch (e) { console.error('FAIL', name, e.message); }
}
await browser.close();
process.stdout.write(JSON.stringify(out));
