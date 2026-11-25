// arXiv API search for recent preprints (OpenAlex lags on these).
const fs = require('fs'); const path = require('path'); const D = __dirname;
const qs = process.env.QFILE ? JSON.parse(fs.readFileSync(path.join(D, process.env.QFILE))) : [
  'abs:robot AND abs:failure AND abs:taxonomy',
  'abs:robot AND abs:failure AND abs:categories',
  'abs:robot AND abs:failure AND abs:"failure modes"',
  'abs:robot AND abs:error AND abs:taxonomy',
  'abs:robot AND abs:infeasible AND abs:instruction',
  'abs:robot AND abs:failure AND abs:explanation',
  'abs:manipulation AND abs:failure AND abs:dataset AND abs:reasoning',
  'abs:embodied AND abs:planning AND abs:"error types"',
  'abs:"vision-language-action" AND abs:"failure modes"',
  'abs:robot AND abs:failure AND abs:recovery AND abs:language',
  'abs:robot AND abs:incapability',
  'abs:embodied AND abs:safety AND abs:benchmark AND abs:household',
];
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const pool = {}; const log = [];
  for (const q of qs) {
    const url = `http://export.arxiv.org/api/query?search_query=${encodeURIComponent(q)}&start=0&max_results=150&sortBy=relevance`;
    const x = await (await fetch(url)).text();
    const total = +(x.match(/<opensearch:totalResults[^>]*>(\d+)/) || [])[1];
    const entries = x.split('<entry>').slice(1);
    for (const e of entries) {
      const id = 'arXiv:' + (e.match(/<id>http[^<]*abs\/([^<v]+)/) || [])[1];
      const title = (e.match(/<title>([\s\S]*?)<\/title>/) || [])[1].replace(/\s+/g, ' ').trim();
      const abstract = (e.match(/<summary>([\s\S]*?)<\/summary>/) || [])[1].replace(/\s+/g, ' ').trim();
      const year = +(e.match(/<published>(\d{4})/) || [])[1];
      if (!pool[id]) pool[id] = { id, title, abstract, year, cites: 0, venue: 'arXiv', src: [] };
      pool[id].src.push('arxiv:' + q);
    }
    log.push({ q, total, got: entries.length }); console.log(total, entries.length, q);
    await sleep(3500);
  }
  fs.writeFileSync(path.join(D, '' + (process.env.OUT || "pool_arxiv.json") + ''), JSON.stringify(Object.values(pool)));
  fs.writeFileSync(path.join(D, 'arxiv_log.json'), JSON.stringify(log, null, 1));
  console.log('arxiv pool', Object.keys(pool).length);
})();
