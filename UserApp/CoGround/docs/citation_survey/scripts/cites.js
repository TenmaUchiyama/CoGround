// Forward-citation survey (2026-11-23): who cites the norm-representation / rule-checking seeds,
// and which of those are about household robots, HRI or AR.
// usage: node cites.js        -> ../data/seeds.json, ../data/pool_cites.json, ../data/search_log.json
// No contact e-mail is sent to OpenAlex.
const fs = require('fs'); const path = require('path'); const D = path.join(__dirname, '..', 'data');
const SEEDS = [
  { key: 'Malle2019', doi: '10.1145/3306618.3314252' },
  { key: 'Malle2017', title: 'Networks of Social and Moral Norms in Human and Robot Agents' },
  { key: 'Kasenberg2018', title: 'Norm Conflict Resolution in Stochastic Domains' },
  { key: 'ThatsMine', id: 'W2964255654' },
  { key: 'VeriPlan', title: 'VeriPlan: Integrating Formal Verification and LLMs into End-User Planning' },
  { key: 'MARCER', title: 'MARCER Multimodal Augmented Reality for Composing and Executing Robot Tasks' },
  { key: 'SafetyChip', title: 'Plug in the Safety Chip: Enforcing Constraints for LLM-driven Robot Agents' },
];
const SEARCHES = [
  '"institutional grammar" robot',
  '"institutional grammar" agent norms',
  'household robot rules user-defined natural language verification',
  'end-user robot constraints correct misinterpretation household',
  'robot norm representation household deontic context',
  'augmented reality robot plan preview rule violation',
];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const get = async url => { for (let i = 0; i < 6; i++) { const r = await fetch(url); if (r.ok) return r.json(); await sleep(4000 * (i + 1)); } throw new Error('fail ' + url); };
const abs = inv => { if (!inv) return ''; const a = []; for (const w in inv) for (const i of inv[w]) a[i] = w; return a.join(' '); };
const slim = (w, src) => ({ id: w.id.replace('https://openalex.org/', ''), title: w.title, year: w.publication_year, cites: w.cited_by_count,
  venue: (w.primary_location && w.primary_location.source && w.primary_location.source.display_name) || '', doi: w.doi || '', abstract: abs(w.abstract_inverted_index), src: [src] });
(async () => {
  const seeds = [], pool = {}, log = [];
  const add = (w, src) => { const s = slim(w, src); if (pool[s.id]) pool[s.id].src.push(src); else pool[s.id] = s; };
  for (const s of SEEDS) {
    let w;
    if (s.id) w = await get('https://api.openalex.org/works/' + s.id);
    else if (s.doi) w = await get('https://api.openalex.org/works/https://doi.org/' + s.doi);
    else { const j = await get('https://api.openalex.org/works?per-page=5&filter=title.search:' + encodeURIComponent(s.title.replace(/[:,!']/g, ' '))); w = j.results.sort((a, b) => b.cited_by_count - a.cited_by_count)[0]; }
    if (!w) { seeds.push({ key: s.key, found: false }); console.log('SEED NOT FOUND', s.key); continue; }
    const id = w.id.replace('https://openalex.org/', '');
    seeds.push({ key: s.key, found: true, id, title: w.title, year: w.publication_year, cites: w.cited_by_count });
    let cursor = '*', n = 0;
    while (cursor) {
      const j = await get(`https://api.openalex.org/works?filter=cites:${id}&per-page=200&cursor=${encodeURIComponent(cursor)}`);
      for (const c of j.results) { add(c, 'cites:' + s.key); n++; }
      cursor = j.results.length ? j.meta.next_cursor : null; await sleep(300);
    }
    console.log(s.key, '|', w.title, '|', w.publication_year, '| cited_by', w.cited_by_count, '| fetched', n);
  }
  for (const q of SEARCHES) {
    const j = await get('https://api.openalex.org/works?per-page=50&search=' + encodeURIComponent(q));
    for (const c of j.results) add(c, 'search:' + q);
    log.push({ q, total: j.meta.count, got: j.results.length }); console.log(j.meta.count, j.results.length, q); await sleep(300);
  }
  fs.writeFileSync(path.join(D, 'seeds.json'), JSON.stringify(seeds, null, 1));
  fs.writeFileSync(path.join(D, 'search_log.json'), JSON.stringify(log, null, 1));
  fs.writeFileSync(path.join(D, 'pool_cites.json'), JSON.stringify(Object.values(pool)));
  console.log('pool', Object.keys(pool).length);
})();
