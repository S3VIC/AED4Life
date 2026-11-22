const RT={g:null,box:null,busy:null};
class Heap{constructor(){this.k=[];this.v=[]}push(key,val){const k=this.k,v=this.v;let i=k.length;k.push(key);v.push(val);while(i>0){const p=(i-1)>>1;if(k[p]<=k[i])break;[k[p],k[i]]=[k[i],k[p]];[v[p],v[i]]=[v[i],v[p]];i=p}}
  pop(){const k=this.k,v=this.v,top=v[0],tk=k[0],lk=k.pop(),lv=v.pop();if(k.length){k[0]=lk;v[0]=lv;let i=0;for(;;){const l=2*i+1,r=l+1;let m=i;if(l<k.length&&k[l]<k[m])m=l;if(r<k.length&&k[r]<k[m])m=r;if(m===i)break;[k[m],k[i]]=[k[i],k[m]];[v[m],v[i]]=[v[i],v[m]];i=m}}return [tk,top]}get size(){return this.k.length}}
const NOWALK=/^(motorway|motorway_link|trunk|trunk_link|construction|proposed|raceway|bus_guideway|abandoned|platform)$/;
async function rtGraph(c,rad){const m=rad/111320,ml=m/Math.cos(c.la*Math.PI/180);
  if(RT.g&&RT.box&&c.la-m>RT.box[0]&&c.la+m<RT.box[2]&&c.lo-ml>RT.box[1]&&c.lo+ml<RT.box[3])return RT.g;
  if(RT.busy)return RT.busy;
  const box=[c.la-m*1.25,c.lo-ml*1.25,c.la+m*1.25,c.lo+ml*1.25].map(x=>+x.toFixed(5));
  const q=`[out:json][timeout:20];way["highway"](${box.join(',')});out body;>;out skel qt;`;
  RT.busy=(async()=>{try{const ctl=new AbortController();setTimeout(()=>ctl.abort(),20000);
      const j=await(await fetch('https://overpass-api.de/api/interpreter',{method:'POST',body:'data='+encodeURIComponent(q),headers:{'Content-Type':'application/x-www-form-urlencoded'},signal:ctl.signal})).json();
      const idx=new Map(),la=[],lo=[];for(const e of j.elements)if(e.type==='node'){idx.set(e.id,la.length);la.push(e.lat);lo.push(e.lon)}
      const adj=la.map(()=>[]),names=[''],nameId=new Map([['',0]]);
      for(const w of j.elements){if(w.type!=='way')continue;const t=w.tags||{};if(NOWALK.test(t.highway||'')||t.foot==='no'||(/^(private|no)$/.test(t.access||'')&&!/^(yes|designated|permissive)$/.test(t.foot||'')))continue;
        const nm=t.name||'';if(!nameId.has(nm)){nameId.set(nm,names.length);names.push(nm)}const ni=nameId.get(nm),f=t.highway==='steps'?1.4:1;
        for(let i=1;i<w.nodes.length;i++){const a=idx.get(w.nodes[i-1]),b=idx.get(w.nodes[i]);if(a==null||b==null)continue;const d=dist({la:la[a],lo:lo[a]},{la:la[b],lo:lo[b]})*f;adj[a].push(b,d,ni);adj[b].push(a,d,ni)}}
      RT.g={la:Float64Array.from(la),lo:Float64Array.from(lo),adj,names,n:la.length};RT.box=box;return RT.g}catch{return null}finally{RT.busy=null}})();
  return RT.busy}
function rtSnap(g,p){let best=-1,bd=Infinity;const k=Math.cos(p.la*Math.PI/180);for(let i=0;i<g.n;i++){if(!g.adj[i].length)continue;const dy=g.la[i]-p.la,dx=(g.lo[i]-p.lo)*k,d=dy*dy+dx*dx;if(d<bd){bd=d;best=i}}return best<0?null:{i:best,d:Math.sqrt(bd)*111320}}
function rtDijkstra(g,s,maxD,targets){const D=new Float64Array(g.n).fill(Infinity),h=new Heap();D[s]=0;h.push(0,s);let left=targets.size;
  while(h.size){const [d,u]=h.pop();if(d>D[u])continue;if(d>maxD)break;if(targets.has(u)&&--left<=0)break;const a=g.adj[u];for(let j=0;j<a.length;j+=3){const v=a[j],nd=d+a[j+1];if(nd<D[v]){D[v]=nd;h.push(nd,v)}}}return D}
function rtAstar(g,s,t){const G0=new Float64Array(g.n).fill(Infinity),P=new Int32Array(g.n).fill(-1),PN=new Int32Array(g.n),h=new Heap(),T={la:g.la[t],lo:g.lo[t]};
  const H=i=>dist({la:g.la[i],lo:g.lo[i]},T);G0[s]=0;h.push(H(s),s);const closed=new Uint8Array(g.n);
  while(h.size){const [,u]=h.pop();if(closed[u])continue;closed[u]=1;if(u===t)break;const a=g.adj[u];
    for(let j=0;j<a.length;j+=3){const v=a[j],nd=G0[u]+a[j+1];if(nd<G0[v]){G0[v]=nd;P[v]=u;PN[v]=a[j+2];h.push(nd+H(v),v)}}}
  if(G0[t]===Infinity)return null;const path=[],nm=[];for(let v=t;v!==-1;v=P[v]){path.push(v);nm.push(PN[v])}path.reverse();nm.reverse();return {path,nm,len:G0[t]}}
function rtSteps(g,res,from,to){const P=res.path,pt=i=>({la:g.la[P[i]],lo:g.lo[P[i]]}),name=i=>g.names[res.nm[i]]||'';
  const coords=[[from.lo,from.la],...P.map(i=>[g.lo[i],g.la[i]]),[to.lo,to.la]];
  const steps=[{name:name(1),distance:dist(from,pt(0)),maneuver:{type:'depart',location:[from.lo,from.la]}}];let cur=steps[0];
  for(let i=1;i<P.length;i++){const seg=dist(pt(i-1),pt(i));
    if(i<P.length-1){cur.distance+=seg;const b1=brg(pt(i-1),pt(i)),b2=brg(pt(i),pt(i+1)),d=((b2-b1+540)%360)-180,ad=Math.abs(d);
      const nmCh=name(i+1)&&name(i+1)!==name(i);
      if((ad>40||(nmCh&&ad>25))&&cur.distance>8){const mod=(ad<60?'slight ':ad>140?'sharp ':'')+(d<0?'left':'right');cur={name:name(i+1),distance:0,maneuver:{type:'turn',modifier:mod,location:[g.lo[P[i]],g.la[P[i]]]}};steps.push(cur)}}
    else cur.distance+=seg}
  cur.distance+=dist(pt(P.length-1),to);steps.push({name:'',distance:0,maneuver:{type:'arrive',location:[to.lo,to.la]}});return {coords,steps}}
async function gChoose(){if(G.explicit||!G.gps)return;const now=new Date(),here={la:me.la,lo:me.lo};
  const all=live(AED).filter(r=>state(r,now)[0]!=='off').map(r=>({r,s:dist(here,{la:r.lat,lo:r.lon})})).sort((a,b)=>a.s-b.s).slice(0,25);if(!all.length)return;
  const rad=Math.min(2200,Math.max(500,all[Math.min(all.length-1,7)].s*1.2+200));const g=await rtGraph(here,rad);
  let cands;if(g){const us=rtSnap(g,here),snaps=all.map(o=>rtSnap(g,{la:o.r.lat,lo:o.r.lon}));const D=us?rtDijkstra(g,us.i,rad*2,new Set(snaps.filter(Boolean).map(x=>x.i))):null;
      cands=all.map((o,k)=>{const sn=snaps[k],w=D&&sn&&D[sn.i]<Infinity?D[sn.i]+us.d+sn.d:o.s*1.4;return {...o,w,graph:!!(D&&sn&&D[sn.i]<Infinity)}})}
  else cands=all.map(o=>({...o,w:o.s*1.4,graph:false}));
  const ver=r=>r.status_rekordu==='zweryfikowany';
  for(const c of cands)c.eff=c.w+(ver(c.r)?0:250)+((+c.r.wskaznik_jakosci||0)<40?300:0);
  cands.sort((a,b)=>a.eff-b.eff);const best=cands[0],closest=[...cands].sort((a,b)=>a.w-b.w)[0];G.cands=cands;
  const why=$('#gwhy');if(why){why.hidden=closest.r.id_aed===best.r.id_aed;if(!why.hidden)why.textContent=`Bliżej jest „${closest.r.nazwa_obiektu}” (${fmtM(closest.w)}), ale ${ver(closest.r)?'ma niską ocenę jakości danych':'nie jest potwierdzony'} – prowadzimy do pewniejszego.`}
  if(best.r.id_aed!==G.id)gRetarget(best.r);else gRoute()}
