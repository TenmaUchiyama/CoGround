// Build ../included.csv from included_spec.txt. Titles not in the search pools are looked up in OpenAlex.
const fs = require('fs'); const oa = require('./oa.js');
const norm = t => (t || "").toLowerCase().replace(/[’']/g, "").replace(/[^a-z0-9-]/g, "");
const all = [];
for (const f of ['pool_snowball.json', 'pool_grid.json', 'pool_arxiv.json', 'pool_round2.json', 'pool_arxiv2.json'])
  if (fs.existsSync(f)) for (const p of JSON.parse(fs.readFileSync(f))) all.push(p);
const T = { 1: '人に聞いた調査', 2: 'レビュー・分類・理論', 3: 'データセット・ベンチマーク', 4: '手法' };
(async () => {
  const rows = [], miss = [];
  for (const l of fs.readFileSync('../data/included_spec.txt', 'utf8').split(/\r?\n/).filter(l => l && !l.startsWith('#'))) {
    const [ty, dom, t] = l.split('|'); const n = norm(t);
    let hits = all.filter(p => norm(p.title).startsWith(n)); let found = 'search';
    if (!hits.length) { hits = (await oa.titleSearch(t)).filter(p => norm(p.title).startsWith(n)); found = 'seed/manual'; }
    if (!hits.length) { miss.push(t); continue; }
    const p = hits.sort((a, b) => (!!b.doi - !!a.doi) || (b.cites || 0) - (a.cites || 0))[0];
    const link = p.doi || (p.id.startsWith('arXiv:') ? 'https://arxiv.org/abs/' + p.id.slice(6) : 'https://openalex.org/' + p.id);
    rows.push([T[ty], dom, p.year, p.title, (p.venue || '').replace(/arXiv \(Cornell University\)/, 'arXiv'), link, found]);
  }
  const esc = s => '"' + String(s ?? '').replace(/"/g, '""') + '"';
  fs.writeFileSync('../included.csv', '﻿type,domains,year,title,venue,link,found_by\n' + rows.map(r => r.map(esc).join(',')).join('\n'));
  console.log('rows', rows.length, 'missing', miss);
  const c = {}; rows.forEach(r => c[r[0]] = (c[r[0]] || 0) + 1); console.log(c);
  const d = {}; rows.forEach(r => r[1].split(',').forEach(x => d[x] = (d[x] || 0) + 1)); console.log(d);
})();
