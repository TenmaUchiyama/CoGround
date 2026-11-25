// Merge pools and apply the automatic stage-1 filter for the household-rule survey.
const fs = require('fs'); const path = require('path'); const D = __dirname;
const pools = ['pool_snowball.json', 'pool_grid.json', 'pool_arxiv.json', 'pool_round2.json', 'pool_arxiv2.json'].filter(f => fs.existsSync(path.join(D, f)));
const all = {};
for (const f of pools) for (const p of JSON.parse(fs.readFileSync(path.join(D, f)))) {
  if (!all[p.id]) all[p.id] = { ...p, src: [] };
  all[p.id].src.push(...p.src);
}
const byT = {};
for (const p of Object.values(all)) {
  const k = (p.title || '').toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 80);
  if (!k) continue;
  if (!byT[k]) byT[k] = p; else { byT[k].src.push(...p.src); if (!byT[k].abstract) byT[k].abstract = p.abstract; byT[k].cites = Math.max(byT[k].cites || 0, p.cites || 0); }
}
const list = Object.values(byT);
const ROBOT = /\b(robot|robotic|robots|embodied|humanoid|household agent|home assistant|domestic agent|vision-language-action|VLA)/i;
const RULE = /(norm|norms|normative|rule|rules|etiquette|privacy|ownership|permissib|prohibit|obligat|constitution|ethic|moral|values?\b|preference|appropriat|acceptab|expectation|safety|hazard|boundar|consent|social convention|courtes|polite)/i;
const HOME = /(household|home|domestic|house|family|kitchen|elder|older adult|living|daily life|everyday|tidy|assistive)/i;
const pass = list.filter(p => {
  const t = (p.title || '') + ' ' + (p.abstract || '');
  return ROBOT.test(t) && RULE.test(t) && HOME.test(t);
});
const RT = /(norm|rule|etiquette|privacy|ownership|permiss|constitution|ethic|moral|preference|appropriat|expectation|safety|hazard)/i;
const score = p => (RT.test(p.title) ? 2 : 0) + (HOME.test(p.title) ? 1 : 0);
pass.sort((a, b) => score(b) - score(a) || b.cites - a.cites);
fs.writeFileSync(path.join(D, 'stage1.json'), JSON.stringify(pass));
fs.writeFileSync(path.join(D, 'stage1_titles.tsv'), pass.map((p, i) => [i, score(p), p.year, p.cites, p.title].join('\t')).join('\n'));
console.log('merged', list.length, 'stage1', pass.length, 'score3', pass.filter(p => score(p) === 3).length, 'score>=2', pass.filter(p => score(p) >= 2).length);
