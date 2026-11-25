// Second pass: papers with strong rule words (norm / etiquette / ownership / constitution / deontic) about robots, without the home requirement.
const fs=require('fs');const s1=new Set(JSON.parse(fs.readFileSync('stage1.json')).map(p=>p.id));
const pools=['pool_snowball.json','pool_grid.json','pool_arxiv.json','pool_round2.json','pool_arxiv2.json'].filter(f=>fs.existsSync(f));
const byT={};for(const f of pools)for(const p of JSON.parse(fs.readFileSync(f))){const k=(p.title||'').toLowerCase().replace(/[^a-z0-9]/g,'').slice(0,80);if(k&&!byT[k])byT[k]=p;}
const ROBOT=/\b(robot|robots|robotic|embodied)/i;
const STRONG=/(\bnorms?\b|normative|etiquette|ownership|constitution|deontic|permissib|social convention|rule[- ]following|house rules|unspoken|commonsense (constraints|safety))/i;
const out=Object.values(byT).filter(p=>!s1.has(p.id)&&ROBOT.test(p.title+' '+(p.abstract||''))&&STRONG.test(p.title+' '+(p.abstract||'').slice(0,3000)));
out.sort((a,b)=>(STRONG.test(b.title)-STRONG.test(a.title))||b.cites-a.cites);
fs.writeFileSync('stage1b.json',JSON.stringify(out));
console.log(out.length);out.forEach((p,i)=>console.log(i+'|'+p.year+'|'+p.cites+'|'+(p.title||'').slice(0,100)));
