// OpenAlex helper for the failure-taxonomy survey.
// usage: node oa.js seeds | snowball | grid
const fs = require('fs');
const path = require('path');
const DIR = __dirname;
const BASE = 'https://api.openalex.org';
const SEL = 'id,doi,display_name,publication_year,cited_by_count,primary_location,abstract_inverted_index,referenced_works,type';
let calls = 0;

async function get(url) {
  for (let i = 0; i < 5; i++) {
    calls++;
    const r = await fetch(url);
    if (r.status === 429 || r.status >= 500) { await new Promise(s => setTimeout(s, 2000 * (i + 1))); continue; }
    if (!r.ok) throw new Error(r.status + ' ' + url);
    return r.json();
  }
  throw new Error('retries exhausted ' + url);
}
function abs(inv) {
  if (!inv) return '';
  const w = [];
  for (const [k, ps] of Object.entries(inv)) for (const p of ps) w[p] = k;
  return w.join(' ');
}
function slim(x) {
  return {
    id: x.id.replace('https://openalex.org/', ''), title: x.display_name, year: x.publication_year,
    cites: x.cited_by_count, doi: x.doi, venue: x.primary_location?.source?.display_name || '',
    type: x.type, abstract: abs(x.abstract_inverted_index), refs: (x.referenced_works || []).map(r => r.replace('https://openalex.org/', '')),
  };
}
async function byIds(ids) {
  const out = [];
  for (let i = 0; i < ids.length; i += 50) {
    const chunk = ids.slice(i, i + 50);
    const j = await get(`${BASE}/works?filter=openalex_id:${chunk.join('|')}&per_page=50&select=${SEL}`);
    out.push(...j.results.map(slim));
  }
  return out;
}
async function citing(id, max = 2000) {
  const out = [];
  for (let page = 1; out.length < max; page++) {
    const j = await get(`${BASE}/works?filter=cites:${id}&per_page=200&page=${page}&select=${SEL}`);
    out.push(...j.results.map(slim));
    if (j.results.length < 200) break;
  }
  return out;
}
async function search(q, n = 200, filter = '') {
  const f = filter ? `&filter=${filter}` : '';
  const j = await get(`${BASE}/works?search=${encodeURIComponent(q)}&per_page=${n}${f}&select=${SEL}`);
  return { count: j.meta.count, results: j.results.map(slim) };
}
async function titleSearch(t) {
  const j = await get(`${BASE}/works?filter=title.search:${encodeURIComponent(t.replace(/[,:?]/g, ' '))}&per_page=3&select=${SEL}`);
  return j.results.map(slim);
}
module.exports = { get, byIds, citing, search, titleSearch, slim, calls: () => calls, DIR };

async function main() {
  const cmd = process.argv[2];
  if (cmd === 'seeds') {
    const seeds = JSON.parse(fs.readFileSync(path.join(DIR, 'seed_titles.json'), 'utf8'));
    const res = [];
    for (const t of seeds) {
      const hits = await titleSearch(t);
      res.push({ query: t, hits: hits.map(h => ({ id: h.id, title: h.title, year: h.year, cites: h.cites, nrefs: h.refs.length })) });
    }
    fs.writeFileSync(path.join(DIR, 'seed_hits.json'), JSON.stringify(res, null, 1));
    for (const r of res) console.log('Q:', r.query, '\n   ', r.hits.map(h => `${h.id} | ${h.year} | c${h.cites} r${h.nrefs} | ${h.title}`).join('\n    '));
  }
  if (cmd === 'snowball') {
    const ids = process.argv.slice(3);
    const seeds = await byIds(ids);
    const pool = {};
    const add = (p, src) => { if (!pool[p.id]) pool[p.id] = { ...p, src: [] }; pool[p.id].src.push(src); };
    for (const s of seeds) {
      const refs = await byIds(s.refs);
      refs.forEach(p => add(p, 'ref:' + s.id));
      const cit = await citing(s.id);
      cit.forEach(p => add(p, 'cit:' + s.id));
      console.log(s.id, s.title.slice(0, 50), 'refs', refs.length, 'citing', cit.length);
    }
    fs.writeFileSync(path.join(DIR, process.env.OUT || 'pool_snowball.json'), JSON.stringify(Object.values(pool)));
    console.log('pool', Object.keys(pool).length, 'calls', calls);
  }
  if (cmd === 'grid') {
    const qs = JSON.parse(fs.readFileSync(path.join(DIR, 'grid.json'), 'utf8'));
    const pool = {}; const log = [];
    for (const q of qs) {
      const r = await search(q, 200);
      log.push({ q, count: r.count, got: r.results.length });
      r.results.forEach(p => { if (!pool[p.id]) pool[p.id] = { ...p, src: [] }; pool[p.id].src.push('q:' + q); });
    }
    fs.writeFileSync(path.join(DIR, 'pool_grid.json'), JSON.stringify(Object.values(pool)));
    fs.writeFileSync(path.join(DIR, 'grid_log.json'), JSON.stringify(log, null, 1));
    log.forEach(l => console.log(l.count, l.got, l.q));
    console.log('pool', Object.keys(pool).length, 'calls', calls);
  }
}
if (require.main === module) main().catch(e => { console.error(e); process.exit(1); });
