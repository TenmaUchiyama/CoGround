const fs=require('fs');const norm=t=>(t||'').toLowerCase().replace(/[^a-z0-9]/g,'');
const all=[];for(const f of ['pool_snowball.json','pool_grid.json','pool_arxiv.json','pool_round2.json','pool_arxiv2.json'])if(fs.existsSync(f))for(const p of JSON.parse(fs.readFileSync(f)))all.push(p);
const lines=fs.readFileSync(process.argv[2],'utf8').split('\n').filter(Boolean);const [a,b]=[+process.argv[3]||0,+process.argv[4]||9999];
lines.slice(a,b).forEach((t,i)=>{const n=norm(t);const h=all.filter(p=>norm(p.title).startsWith(n)).sort((x,y)=>(y.abstract||'').length-(x.abstract||'').length)[0];
 if(!h){console.log(a+i,'MISSING',t);return;}console.log(`${a+i}. [${h.year}|${(h.venue||'').slice(0,30)}] ${h.title}\n   ${(h.abstract||'(no abstract)').slice(0,+process.env.N||380)}`);});
