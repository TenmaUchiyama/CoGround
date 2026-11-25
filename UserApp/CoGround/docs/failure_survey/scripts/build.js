// Build the included-paper list (included.csv) from included_spec.txt and the search pools.
const fs=require("fs");const norm=t=>(t||"").toLowerCase().replace(/[^a-z0-9]/g,"");
const all=[];for(const f of ["pool_snowball.json","pool_grid.json","pool_arxiv.json","pool_round2.json","pool_arxiv2.json"])for(const p of JSON.parse(fs.readFileSync(f)))all.push(p);
const spec=fs.readFileSync("included_spec.txt","utf8").split("\n").filter(l=>l&&!l.startsWith("#"));
const rows=[];const miss=[];
for(const l of spec){const [tier,cats,ver,t]=l.split("|");const n=norm(t);const hits=all.filter(p=>norm(p.title).startsWith(n)||norm(p.title).includes(n));
 if(!hits.length){miss.push(t);continue;}
 const p=hits.sort((a,b)=>(norm(b.title).startsWith(n)-norm(a.title).startsWith(n))||(b.cites||0)-(a.cites||0))[0];
 const src=new Set();hits.filter(h=>norm(h.title)===norm(p.title)).forEach(h=>h.src.forEach(s=>src.add(s.startsWith("q:")?"keyword":s.startsWith("arxiv")?"arXiv":s.startsWith("ref")?"reference":"citation")));
 const link=p.doi||(p.id.startsWith("arXiv:")?"https://arxiv.org/abs/"+p.id.slice(6):"https://openalex.org/"+p.id);
 rows.push({tier,cats,ver,title:p.title,year:p.year,venue:(p.venue||"").replace(/arXiv \(Cornell University\)/,"arXiv"),link,found:[...src].sort().join("+")});}
const man=[["2","H","abs","DESPITE (planning safety benchmark: infeasible / feasible-but-unsafe / safe)",2026,"arXiv","https://arxiv.org/abs/2604.18463","manual"],["2","G,A","abs","Defining Boundaries: A Spectrum of Task Feasibility for Large Language Models",2024,"arXiv","https://arxiv.org/abs/2408.05873","manual"],["2","A,B","prior review","Model Reconciliation through Explainability and Collaborative Recovery in Assistive Robotics",2026,"ICRA","https://arxiv.org/abs/2601.06552","manual"]];
for(const m of man)rows.push({tier:m[0],cats:m[1],ver:m[2],title:m[3],year:m[4],venue:m[5],link:m[6],found:m[7]});
console.log("rows",rows.length,"tier1",rows.filter(r=>r.tier==="1").length,"missing",miss);
const esc=s=>"\""+String(s).replace(/"/g,"\"\"")+"\"";
fs.writeFileSync("included.csv","tier,categories,verification,year,title,venue,link,found_by\n"+rows.map(r=>[r.tier,r.cats,r.ver,r.year,r.title,r.venue,r.link,r.found].map(esc).join(",")).join("\n"));
const c={};rows.forEach(r=>(r.cats==="all"?["A","B","C","D","E","F","G","H"]:r.cats.split(",")).forEach(x=>c[x]=(c[x]||0)+1));console.log(c);
const f={};rows.forEach(r=>r.found.split("+").forEach(x=>f[x]=(f[x]||0)+1));console.log(f);
rows.forEach(r=>{if(/AGENTSAFE|Safety at Scale/.test(r.title))console.log(r.title,r.link)});
