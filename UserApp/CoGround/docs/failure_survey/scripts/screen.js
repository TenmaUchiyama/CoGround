// Merge pools and apply the automatic stage-1 filter.
const fs = require('fs'); const path = require('path'); const D = __dirname;
const pools = ['pool_snowball.json', 'pool_grid.json', 'pool_arxiv.json'].filter(f => fs.existsSync(path.join(D, f)));
const all = {};
for (const f of pools) for (const p of JSON.parse(fs.readFileSync(path.join(D, f)))) {
  if (!all[p.id]) all[p.id] = { ...p, src: [] };
  all[p.id].src.push(...p.src);
}
// dedupe by normalized title (arXiv and OpenAlex copies of the same paper)
const byT = {};
for (const p of Object.values(all)) {
  const k = (p.title || '').toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 80);
  if (!k) continue;
  if (!byT[k]) byT[k] = p; else { byT[k].src.push(...p.src); if (!byT[k].abstract) byT[k].abstract = p.abstract; byT[k].cites = Math.max(byT[k].cites || 0, p.cites || 0); }
}
const list = Object.values(byT);
const ROBOT = /\b(robot|robotic|robots|embodied|manipulat|ugv|uav|drone|humanoid|cobot|autonomous (system|vehicle|agent)|household agent|vision-language-action|VLA)\b/i;
const FAIL = /(failure|failures|fault|faults|error|errors|incapab|infeasib|mistake|breakdown|malfunction|unsafe|hazard|violation)/i;
const TAX = /(taxonom|classif|categor|typolog|ontolog|types of|kinds of|failure modes|error types|failure types|fault types|benchmark|dataset|survey|review)/i;
const pass = list.filter(p => {
  const t = (p.title || '') + ' ' + (p.abstract || '');
  return ROBOT.test(t) && FAIL.test(p.title + ' ' + (p.abstract || '').slice(0, 4000)) && TAX.test(t);
});
// rank: title mentions failure/error words first
const score = p => (FAIL.test(p.title) ? 2 : 0) + (TAX.test(p.title) ? 1 : 0);
pass.sort((a, b) => score(b) - score(a) || b.cites - a.cites);
fs.writeFileSync(path.join(D, 'stage1.json'), JSON.stringify(pass));
const strong = pass.filter(p => score(p) >= 2);
fs.writeFileSync(path.join(D, 'stage1_titles.tsv'), pass.map((p, i) => [i, p.year, p.cites, p.title].join('\t')).join('\n'));
console.log('merged', list.length, 'stage1', pass.length, 'failure-word-in-title', strong.length);
