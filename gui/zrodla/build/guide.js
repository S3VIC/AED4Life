const GL='pl';
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
      let j=null;for(const h of ['https://overpass-api.de/api/interpreter','https://maps.mail.ru/osm/tools/overpass/api/interpreter','https://overpass.private.coffee/api/interpreter']){try{const c2=new AbortController();const tm=setTimeout(()=>c2.abort(),9000);const r=await fetch(h,{method:'POST',body:'data='+encodeURIComponent(q),headers:{'Content-Type':'application/x-www-form-urlencoded'},signal:c2.signal});clearTimeout(tm);if(r.ok){j=await r.json();break}}catch{}}if(!j)throw 0;
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
async function gChoose(){if(G.explicit||G.apiPick||!G.gps)return;const now=new Date(),here={la:me.la,lo:me.lo};
  const all=live(AED).filter(r=>state(r,now)[0]!=='off').map(r=>({r,s:dist(here,{la:r.lat,lo:r.lon})})).sort((a,b)=>a.s-b.s).slice(0,25);if(!all.length)return;
  const rad=Math.min(2200,Math.max(500,all[Math.min(all.length-1,7)].s*1.2+200));const g=await rtGraph(here,rad);
  let cands;if(g){const us=rtSnap(g,here),snaps=all.map(o=>rtSnap(g,{la:o.r.lat,lo:o.r.lon}));const D=us?rtDijkstra(g,us.i,rad*2,new Set(snaps.filter(Boolean).map(x=>x.i))):null;
      cands=all.map((o,k)=>{const sn=snaps[k],w=D&&sn&&D[sn.i]<Infinity?D[sn.i]+us.d+sn.d:o.s*1.4;return {...o,w,graph:!!(D&&sn&&D[sn.i]<Infinity)}})}
  else cands=all.map(o=>({...o,w:o.s*1.4,graph:false}));
  const ver=r=>r.status_rekordu==='zweryfikowany';
  for(const c of cands)c.eff=c.w+(ver(c.r)?0:250)+((+c.r.wskaznik_jakosci||0)<40?300:0);
  cands.sort((a,b)=>a.eff-b.eff);const best=cands[0],closest=[...cands].sort((a,b)=>a.w-b.w)[0];G.cands=cands;
  const why=$('#gwhy');if(why){why.hidden=closest.r.id_aed===best.r.id_aed;if(!why.hidden)why.textContent=`Bliżej (${fmtM(closest.w)}) jest AED, który ${[!ver(closest.r)&&ver(best.r)?'nie jest potwierdzony':'',(+closest.r.wskaznik_jakosci||0)<40?'ma niepewne dane':''].filter(Boolean).join(' i ')||'jest mniej pewny'}.`}
  if(G.explicit||G.apiPick)return;if(best.r.id_aed!==G.id)gRetarget(best.r);else gRoute()}

const GT={pl:{close:'Zamknij',route:'Szukam trasy…',noroute:'Bez trasy, idź w kierunku strzałki',left:'zostało',min:'min',tabNav:'Droga',tabAed:'Użyj AED',tabCpr:'Uciskanie',at:'Jestem przy AED',voice:'Głos',compass:'Włącz kompas',arrive:'Jesteś przy AED. Otwórz szafkę, włącz urządzenie i słuchaj poleceń.',arriveT:'Jesteś na miejscu',gm:'Problem z mapą? Otwórz w Google Maps',start:'Start',stop:'Stop',count:'uciśnięć',beat:'Uciskaj w rytm: 110 na minutę',floor:'piętro',call:'Po wybraniu 112 włącz głośnik i wróć do tej strony. Rozmowa trwa w tle.',head:'Idź w kierunku strzałki',dirs:['na północ','na północny wschód','na wschód','na południowy wschód','na południe','na południowy zachód','na zachód','na północny zachód'],
 m:{left:'Skręć w lewo','slight left':'Lekko w lewo','sharp left':'Ostro w lewo',right:'Skręć w prawo','slight right':'Lekko w prawo','sharp right':'Ostro w prawo',straight:'Idź prosto',uturn:'Zawróć'},dep:'Ruszaj',arr:'AED na miejscu',round:'Przejdź przez rondo',in:'za'},
en:{close:'Close',route:'Finding route…',noroute:'No route, follow the arrow',left:'left',min:'min',tabNav:'Route',tabAed:'Use the AED',tabCpr:'Compressions',at:'I am at the AED',voice:'Voice',compass:'Enable compass',arrive:'You are at the AED. Open the cabinet, switch it on and follow its instructions.',arriveT:'You have arrived',gm:'Map problem? Open in Google Maps',start:'Start',stop:'Stop',count:'compressions',beat:'Push to the beat: 110 per minute',floor:'floor',call:'After dialling 112 turn on the speaker and come back here. The call keeps going.',head:'Walk where the arrow points',dirs:['north','north-east','east','south-east','south','south-west','west','north-west'],
 m:{left:'Turn left','slight left':'Bear left','sharp left':'Sharp left',right:'Turn right','slight right':'Bear right','sharp right':'Sharp right',straight:'Go straight',uturn:'Turn around'},dep:'Start',arr:'AED here',round:'Take the roundabout',in:'in'}};
const G={map:null,id:null,r:null,watch:null,route:null,steps:[],idx:0,line:null,meM:null,acc:null,aedM:null,lastRoute:0,heading:null,voice:false,said:'',arrived:false,wake:null,met:null,cnt:0,tab:'nav',follow:true};
const gt=()=>GT[GL]||GT.pl;
const gMinZ=()=>{if(G.map&&G.map.getZoom()<14)G.map.setZoom(14,{animate:false})};
const gSayM=m=>GL!=='pl'?(m<1000?`${Math.max(10,Math.round(m/10)*10)} meters`:`${(m/1000).toFixed(1)} kilometers`):(m<1000?`${Math.max(10,Math.round(m/10)*10)} metrów`:`${(m/1000).toFixed(1).replace('.',',')} kilometra`);
const gCnt=n=>GL!=='pl'?`${n} ${gt().count}`:`${n} ${n===1?'uciśnięcie':(n%10>=2&&n%10<=4&&(n%100<12||n%100>14))?'uciśnięcia':'uciśnięć'}`;
const gPad=()=>({paddingTopLeft:[40,matchMedia('(max-aspect-ratio:1/1)').matches?150:60],paddingBottomRight:[60,(()=>{if(matchMedia('(max-aspect-ratio:1/1)').matches)return ($('#gpanel').offsetHeight||300)+30;const c=document.querySelector('.gcard');return c&&getComputedStyle(c).position==='absolute'?c.offsetHeight+40:70})()],maxZoom:17});
const brg=(a,b)=>{const t=Math.PI/180,y=Math.sin((b.lo-a.lo)*t)*Math.cos(b.la*t),x=Math.cos(a.la*t)*Math.sin(b.la*t)-Math.sin(a.la*t)*Math.cos(b.la*t)*Math.cos((b.lo-a.lo)*t);return(Math.atan2(y,x)/t+360)%360};
const segD=(p,a,b)=>{const k=Math.cos(p.la*Math.PI/180),ax=(a.lo-p.lo)*k,ay=a.la-p.la,bx=(b.lo-p.lo)*k,by=b.la-p.la,dx=bx-ax,dy=by-ay,l=dx*dx+dy*dy;let u=l?-(ax*dx+ay*dy)/l:0;u=Math.max(0,Math.min(1,u));return Math.hypot(ax+u*dx,ay+u*dy)*111320};
const fmtM=m=>m<1000?`${Math.round(m/5)*5||5} m`:`${(m/1000).toFixed(1).replace('.',',')} km`;
function gPick(id){const now=new Date();if(id){const r=AED.find(a=>a.id_aed===id);if(r)return r}
  return live(AED).filter(r=>r.status_rekordu==='zweryfikowany').map(r=>({r,s:state(r,now),d:dist(me,{la:r.lat,lo:r.lon})})).filter(o=>o.s[0]!=='off').sort((a,b)=>a.d-b.d)[0]?.r||null}
function gOpen(id){G.explicit=!!id;const _v=$('#v-prowadz');if(_v.classList.contains('navonly')!==G.explicit){_v.classList.toggle('navonly',G.explicit);setTimeout(()=>G.map&&G.map.invalidateSize(),60)}const r=gPick(id);if(!r){location.hash='ratunek';return}
  const fresh=G.id!==r.id_aed;G.id=r.id_aed;G.r=r;if(fresh){G.route=null;G.steps=[];G.idx=0;G.arrived=false;G.said='';G.follow=false;gTab(window.pzNoAsk?'aed':'call')}
  $('#gname').innerHTML=`<b>${esc(r.nazwa_obiektu)}</b>${r.opis_dojscia?`<span>${esc(r.opis_dojscia)}</span>`:''}${r.poziom_pietro!==''&&r.poziom_pietro!=null?`<span>${gt().floor} ${esc(String(r.poziom_pietro))}</span>`:''}`;
  $('#ggm').href=mapsUrl(r);gAedAddr(r);gMapInit();gWake(true);
  if(!G.gps)gNoGps();if(!navigator.geolocation)gNoGps({code:1});else if(G.watch==null){const onFix=p=>{const first=!G.gps;G.gps=true;$('#gnogps').hidden=true;const nf={la:p.coords.latitude,lo:p.coords.longitude};const hd=p.coords.heading,sp=p.coords.speed;if(hd!=null&&!isNaN(hd)&&sp!=null&&sp>0.6){G.course=hd;G.courseAt=Date.now()}else if(G.prevFix&&dist(G.prevFix,nf)>=6&&p.coords.accuracy<40){G.course=brg(G.prevFix,nf);G.courseAt=Date.now()}if(!G.prevFix||dist(G.prevFix,nf)>=6)G.prevFix=nf;me={...nf,src:'GPS'};G.accR=p.coords.accuracy;saveMe();
    if(first){if(!G.explicit){gRoute();gChoose();apiNearest(me).then(r=>{if(r&&!G.explicit){G.apiPick=true;if(r.id_aed!==G.id)gGoTo(r)}})}else{gRoute();G.map&&G.map.fitBounds([[me.la,me.lo],[G.r.lat,G.r.lon]],gPad());gMinZ()}}else if(RT.g&&(!G.pAt||dist(G.pAt,me)>6))gRoute();gTick()};G.watch=navigator.geolocation.watchPosition(onFix,e=>{if(!G.gps)gNoGps(e)},{enableHighAccuracy:true,maximumAge:3000,timeout:20000});navigator.geolocation.getCurrentPosition(p=>{if(!G.gps)onFix(p)},()=>{},{enableHighAccuracy:false,maximumAge:600000,timeout:8000})}
  setTimeout(()=>{G.map&&G.map.invalidateSize();if(fresh&&G.map)G.map.fitBounds([[me.la,me.lo],[r.lat,r.lon]],gPad());gMinZ();gMinZ()},60);
  gRoute();gTick();gAskShow()}
function gNoGps(e){const n=$('#gnogps');n.hidden=false;n.textContent=GL==='pl'?(e&&e.code===1?'Brak zgody na lokalizację. Dotknij mapy w miejscu, gdzie jesteś (albo zezwól na lokalizację w pasku adresu).':'Szukam Twojej lokalizacji… Jeśli to trwa, dotknij mapy w miejscu, gdzie jesteś.'):(e&&e.code===1?'Location blocked. Tap the map where you are.':'Finding your location… or tap the map where you are.')}
async function gAedAddr(r){if(r.ulica||r._adr!==undefined){gAedShow(r);return}r._adr='';try{const ctl=new AbortController();setTimeout(()=>ctl.abort(),6000);const j=await(await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=18&addressdetails=1&accept-language=pl&lat=${r.lat}&lon=${r.lon}`,{signal:ctl.signal})).json();const a=j.address||{};
  r._adr=[j.name&&!/^\d/.test(j.name)?j.name:'',[a.road||a.pedestrian||a.footway||'',a.house_number||''].join(' ').trim(),a.city||a.town||a.village||''].filter(Boolean).join(', ')}catch{}gAedShow(r)}
function gAedAdrTxt(r){return r.ulica?`${r.ulica} ${r.numer_budynku||''}`.trim()+(r.miejscowosc?`, ${r.miejscowosc}`:''):(r._adr||'')}
function gAedShow(r){if(G.r!==r)return;gOpenInfo(r);const ad=gAedAdrTxt(r);$('#gname').innerHTML=`<b>${esc(r.nazwa_obiektu)}</b>${ad?`<span>${esc(ad)}</span>`:''}${r.opis_dojscia&&!r.nazwa_obiektu.toLowerCase().includes(r.opis_dojscia.slice(0,20).toLowerCase())?`<span>${esc(r.opis_dojscia)}</span>`:''}${r.poziom_pietro!==''&&r.poziom_pietro!=null?`<span>${gt().floor} ${esc(String(r.poziom_pietro))}</span>`:''}`;gTick()}
function gRetarget(r){G.id=r.id_aed;G.r=r;G.route=null;G.steps=[];G.idx=0;G.arrived=false;G.said='';G.follow=false;G.fitted=null;
  $('#gname').innerHTML=`<b>${esc(r.nazwa_obiektu)}</b>${r.opis_dojscia?`<span>${esc(r.opis_dojscia)}</span>`:''}${r.poziom_pietro!==''&&r.poziom_pietro!=null?`<span>${gt().floor} ${esc(String(r.poziom_pietro))}</span>`:''}`;$('#ggm').href=mapsUrl(r);gAedAddr(r);
  G.map&&G.map.fitBounds([[me.la,me.lo],[r.lat,r.lon]],gPad());gMinZ();gRoute();gTick()}
function gClose(){G.gps=false;if(G.watch!=null){navigator.geolocation.clearWatch(G.watch);G.watch=null}gWake(false);gMet(false);try{speechSynthesis.cancel()}catch{}}
async function gWake(on){try{if(on&&!G.wake&&navigator.wakeLock){G.wake=await navigator.wakeLock.request('screen');G.wake.addEventListener('release',()=>G.wake=null)}if(!on&&G.wake){await G.wake.release();G.wake=null}}catch{}}
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&$('#v-prowadz').classList.contains('on'))gWake(true)});
function gMapInit(){if(G.map||!window.L)return;G.map=LF.map('gmap',{zoomControl:false,attributionControl:true}).setView([me.la,me.lo],17);G.map.attributionControl.setPrefix('');
  if(location.protocol!=='file:')LF.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,referrerPolicy:'strict-origin-when-cross-origin',attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(G.map);
  G.map.on('click',e=>{if(G.gps){const t={la:e.latlng.lat,lo:e.latlng.lng},px=G.map.latLngToContainerPoint(e.latlng);const c=live(AED).filter(r=>r.status_sprawnosci!=='niesprawny').map(r=>({r,d:dist(t,{la:r.lat,lo:r.lon}),pd:px.distanceTo(G.map.latLngToContainerPoint([r.lat,r.lon]))})).filter(o=>o.pd<60).sort((a,b)=>a.d-b.d)[0];if(c&&c.r.id_aed!==G.id)gGoTo(c.r);return}me={la:e.latlng.lat,lo:e.latlng.lng,src:'wskazano na mapie'};saveMe();$('#gnogps').hidden=true;G.gps=false;if(G.explicit){gRetarget(G.r)}else{G.gps=true;G.tapped=true;gChoose();G.gps=false}});G.map.on('dragstart',()=>{G.follow=false;$('#grec').setAttribute('aria-pressed','false')})}
function gDraw(){if(!G.map)return;if(G.route&&G.fitted!==G.id){G.fitted=G.id;try{G.map.fitBounds(LF.latLngBounds(G.route.map(([lo,la])=>[la,lo])),gPad())}catch{}}const r=G.r,me2=[me.la,me.lo];
  if(!G.aedM)G.aedM=LF.marker([r.lat,r.lon],{icon:LF.divIcon({className:'gaed',html:'<span>AED</span>',iconSize:matchMedia('(max-aspect-ratio:1/1)').matches?[34,34]:[46,46],iconAnchor:matchMedia('(max-aspect-ratio:1/1)').matches?[17,34]:[23,46]})}).addTo(G.map);else G.aedM.setLatLng([r.lat,r.lon]);
  const pts=G.route?G.route.map(([lo,la])=>[la,lo]):[me2,[r.lat,r.lon]];
  if(!G.line){G.line=LF.polyline(pts,{color:'#1a73e8',weight:7,opacity:.9,lineCap:'round'}).addTo(G.map)}else G.line.setLatLngs(pts);G.line.setStyle({dashArray:G.route?null:'2 12'});
  if(!G.meM)G.meM=LF.marker(me2,{icon:LF.divIcon({className:'medot',html:'<b></b><s></s><i></i>',iconSize:[18,18]}),zIndexOffset:1000,keyboard:false}).addTo(G.map);else G.meM.setLatLng(me2);gMeHead();gNearDraw();
  if(G.accR){if(!G.acc)G.acc=LF.circle(me2,{radius:G.accR,color:'#1a73e8',weight:1,opacity:.4,fillOpacity:.1,interactive:false}).addTo(G.map);else G.acc.setLatLng(me2).setRadius(G.accR)}
  if(G.follow)G.map.panTo(me2,{animate:true})}
async function gRoute(){const r=G.r;if(!r)return;G.lastRoute=Date.now();const id=r.id_aed,here={la:me.la,lo:me.lo},to={la:+r.lat,lo:+r.lon};G.pAt=here;
  const g=RT.g,inBox=p=>RT.box&&p.la>RT.box[0]&&p.la<RT.box[2]&&p.lo>RT.box[1]&&p.lo<RT.box[3];
  if(g&&inBox(here)&&inBox(to)){const a=rtSnap(g,here),b=rtSnap(g,to);const res=a&&b?rtAstar(g,a.i,b.i):null;
    if(res){const x=rtSteps(g,res,here,to);G.route=x.coords;G.steps=x.steps;G.idx=0;G.rsrc=`Trasa: A* po grafie pieszym OSM (${g.n.toLocaleString('pl')} węzłów), liczona na żywo`;gTick();return}}
  try{const ctl=new AbortController();setTimeout(()=>ctl.abort(),7000);
    const j=await (await fetch(`https://routing.openstreetmap.de/routed-foot/route/v1/driving/${me.lo},${me.la};${r.lon},${r.lat}?overview=full&geometries=geojson&steps=true`,{signal:ctl.signal})).json();
    if(G.id!==id)return;const rt=j.routes?.[0];if(!rt)throw 0;G.route=rt.geometry.coordinates;G.steps=rt.legs[0].steps;G.idx=0;G.rsrc='Trasa: serwer OSRM (zapasowy)'}catch{if(G.id===id){G.route=null;G.steps=[];G.rsrc='Brak trasy – linia prosta do AED'}}
  gTick()}
function gInstr(s){const t=gt(),m=s.maneuver||{};if(m.type==='arrive')return t.arr;if(m.type==='depart')return `${t.dep}${s.name?' · '+s.name:''}`;
  let x=m.type==='roundabout'||m.type==='rotary'?t.round:(t.m[m.modifier]||t.m.straight);return x+(s.name?' · '+s.name:'')}
function gTick(){const r=G.r;if(!r||!$('#v-prowadz').classList.contains('on'))return;const t=gt(),here={la:me.la,lo:me.lo},aed={la:r.lat,lo:r.lon};gDraw();
  const dA=dist(here,aed);let remain=dA,target=aed,text=t.noroute;
  if(G.route){let off=Infinity;const P=G.route.map(([lo,la])=>({la,lo}));for(let i=1;i<P.length;i++)off=Math.min(off,segD(here,P[i-1],P[i]));
    if(off>40&&Date.now()-G.lastRoute>15000){gRoute();}
    while(G.idx<G.steps.length-1&&dist(here,{la:G.steps[G.idx+1].maneuver.location[1],lo:G.steps[G.idx+1].maneuver.location[0]})<15)G.idx++;
    const nx=G.steps[Math.min(G.idx+1,G.steps.length-1)];if(nx){const loc={la:nx.maneuver.location[1],lo:nx.maneuver.location[0]};const dn=dist(here,loc);target=loc;
      remain=dn+G.steps.slice(G.idx+2).reduce((a,s)=>a+s.distance,0);text=nx.maneuver.type==='arrive'?(dn<25?t.arr:`${GL==='pl'?'Idź prosto do AED':'Go straight to the AED'} · ${fmtM(dn)}`):`${t.in} ${fmtM(dn)}: ${gInstr(nx)}`;
      const key=nx.maneuver.location.map(v=>v.toFixed(5)).join(',');G.spk=G.spk||new Set();
      if(nx.maneuver.type!=='arrive'){if(!G.spk.has(key+'a')&&dn>=35){G.spk.add(key+'a');gSay(`${GL==='pl'?'Za':'In'} ${gSayM(dn)}, ${gInstr(nx).replace(' · ',', ')}`)}
        if(dn<35&&!G.spk.has(key+'n')){G.spk.add(key+'n');G.spk.add(key+'a');gSay(gInstr(nx).replace(' · ',', '))}}
      else if(!G.spk.has('arrv'+G.id)&&dn>=25){G.spk.add('arrv'+G.id);gSay(GL==='pl'?`Idź prosto. AED za ${gSayM(dn)}.`:`Go straight. AED in ${gSayM(dn)}.`)}}}
  else{const b=brg(here,aed),dir=t.dirs[Math.round(b/45)%8];text=GL==='pl'?`Idź ${dir}`:`Walk ${dir}`;const k='dir'+G.id+dir+Math.round(dA/100);G.spk=G.spk||new Set();if(!G.spk.has(k)){G.spk.add(k);gSay(GL==='pl'?`Idź ${dir}. AED za ${gSayM(dA)}.`:`Walk ${dir}. AED in ${gSayM(dA)}.`)}}
  G.remain=remain;$('#gm').textContent=fmtM(remain);$('#grsrc').textContent=G.rsrc||'';$('#gt').textContent=`${t.left} · ok. ${Math.max(1,Math.round(remain/80))} ${t.min}`;$('#ginstr').textContent=text;$('.gcard .gdist>div').dataset.i=text.replace(/^za ([^:]+): (.*)$/,'$2 za $1');
  G.b=brg(here,target);gArrow();if(G.gps)gAddr();$('#gsayaed').innerHTML=`<span><b>„Najbliższy AED: ${esc(gAedAdrTxt(r)||r.nazwa_obiektu)} – ${fmtM(dA)} stąd.”</b> Powiedz, czy ktoś po niego idzie.</span>`;if(!G.addrTxt)$('#gsayaddr').textContent=`${me.la.toFixed(5)}, ${me.lo.toFixed(5)}`;
  const far=$('#gfar');if(far){const isFar=G.gps&&dA>AED_MAX;far.hidden=!isFar;if(isFar)far.innerHTML=(GL==='pl'?`AED jest daleko (${fmtM(dA)}). Zacznij uciskać klatkę piersiową, a po AED niech idzie ktoś inny. `:`The AED is far (${fmtM(dA)}). Start chest compressions and send someone else for the AED. `)+`<button type="button" class="gfarb">${gt().tabCpr}</button>`}
  if(!G.arrived&&dA<20){G.arrived=true;try{navigator.vibrate?.([200,100,200])}catch{}gSay(t.arrive);$('#garr').hidden=false;gTab('aed')}}
function gSay(x){if(!G.voice||!window.speechSynthesis)return;try{if(speechSynthesis.pending)speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(x);u.lang=GL==='pl'?'pl-PL':'en-GB';u.rate=1.05;speechSynthesis.speak(u)}catch{}}
function gTab(k){G.tab=k;for(const b of $$('#gseg button'))b.setAttribute('aria-selected',b.dataset.g===k);for(const p of $$('.gpane'))p.hidden=p.dataset.g!==k;if(k!=='cpr')gMet(false);else if(!G.met)gMet(true)}
function gFill(){const t=gt();$('#gcprl').innerHTML=T[GL].cpr.slice(3).map(x=>`<li><span>${esc(x)}</span></li>`).join('');$('#gaedl').innerHTML=T[GL].aed.map(x=>`<li>${esc(x)}</li>`).join('');for(const e of $$('.gsrc'))e.textContent=T[GL].src;
  $('#gatb').textContent=t.at;$('#ggm').textContent=t.gm;$('#gbeat').textContent=t.beat;$('#garrt').textContent=t.arriveT}
let gAC=null;function gMet(on){const b=$('#gmet');if(!on){clearInterval(G.met);G.met=null;b&&(b.textContent=gt().start,b.setAttribute('aria-pressed','false'));return}
  try{gAC=gAC||new (window.AudioContext||window.webkitAudioContext)();gAC.resume()}catch{}G.cnt=0;$('#gcnt').textContent=gCnt(0);b.textContent=gt().stop;b.setAttribute('aria-pressed','true');
  const tick=()=>{G.cnt++;$('#gcnt').textContent=gCnt(G.cnt);const el=Math.floor((Date.now()-G.t0)/1000),nx=120-el%120;$('#gtime').textContent=`${Math.floor(el/60)}:${String(el%60).padStart(2,'0')} · zmiana za ${nx} s`;
    if(Math.floor(el/120)>G.swaps){G.swaps=Math.floor(el/120);const w=$('#gswap');w.hidden=true;void w.offsetWidth;w.hidden=false;try{navigator.vibrate?.([300,100,300])}catch{}try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(GL==='pl'?'Zmiana. Niech uciska druga osoba.':'Switch. Let someone else push.');u.lang=GL==='pl'?'pl-PL':'en-GB';speechSynthesis.speak(u)}catch{}setTimeout(()=>w.hidden=true,9000)}const p=$('#gpulse');p.classList.remove('gbt');void p.offsetWidth;p.classList.add('gbt');
    if(gAC){const o=gAC.createOscillator(),g=gAC.createGain();o.frequency.value=G.cnt%30===0?1320:880;g.gain.setValueAtTime(.35,gAC.currentTime);g.gain.exponentialRampToValueAtTime(.001,gAC.currentTime+.08);o.connect(g).connect(gAC.destination);o.start();o.stop(gAC.currentTime+.09)}};
  G.t0=Date.now();G.swaps=0;$('#gswap').hidden=true;tick();G.met=setInterval(tick,60000/110)}
document.addEventListener('click',e=>{if(e.target.closest('.gfarb'))gTab('cpr');const n=e.target.closest('.gnext');if(n){gTab(n.dataset.go);$('.gpanel').scrollTo({top:0,behavior:'smooth'})}});
$('#gseg').onclick=e=>{const b=e.target.closest('button');if(b)gTab(b.dataset.g)};
$('#gatb').onclick=()=>{G.arrived=true;gTab('aed')};
$('#gmet').onclick=()=>gMet(!G.met);
$('#gvoice').onclick=e=>{G.voice=!G.voice;const b=e.currentTarget;b.setAttribute('aria-pressed',G.voice);b.querySelector('.gvl').textContent=G.voice?'Głos włączony':'Prowadź głosem';if(G.voice){G.spk=new Set();gSay((GL==='pl'?'Prowadzę do AED. ':'Guiding you to the AED. ')+$('#ginstr').textContent.replace(' · ',', ')+'. '+(GL==='pl'?'Zostało ':'')+gSayM(G.remain||0)+'.')}else try{speechSynthesis.cancel()}catch{}};
$('#grec').onclick=()=>{G.follow=true;$('#grec').setAttribute('aria-pressed','true');G.map&&G.map.flyTo([me.la,me.lo],Math.max(G.map.getZoom(),17),{duration:.5})};
function gMeHead(){const el=G.meM&&G.meM.getElement&&G.meM.getElement();if(!el)return;const s=el.querySelector('s');if(!s)return;const moving=G.course!=null&&Date.now()-(G.courseAt||0)<20000;const h=moving?G.course:G.heading;if(h==null){s.style.display='none';return}s.style.display='block';s.style.transform=`rotate(${Math.round(h)}deg)`}
function gNearDraw(){if(!G.map||typeof LF==='undefined')return;if(!G.nearL)G.nearL=LF.layerGroup().addTo(G.map);const key=G.id+'|'+Math.round(me.la*500)+'|'+Math.round(me.lo*500);if(G.nearKey===key)return;G.nearKey=key;G.nearL.clearLayers();const now=new Date();
  live(AED).filter(r=>r.id_aed!==G.id&&r.status_sprawnosci!=='niesprawny').map(r=>({r,d:dist(me,{la:r.lat,lo:r.lon})})).filter(o=>o.d<3000).sort((a,b)=>a.d-b.d).slice(0,25).forEach(({r,d})=>{const ok=r.status_rekordu==='zweryfikowany'&&state(r,now)[0]!=='off';
    LF.marker([r.lat,r.lon],{icon:LF.divIcon({className:'gaed2'+(ok?'':' unv'),html:'<span>AED</span>',iconSize:[30,30],iconAnchor:[15,15]}),title:`${r.nazwa_obiektu} – ${fmtM(d)}. Kliknij, aby prowadzić tutaj`,alt:`AED ${r.nazwa_obiektu}`,keyboard:true}).on('click',e=>{LF.DomEvent.stopPropagation(e);gGoTo(r)}).addTo(G.nearL)})}
function gGoTo(r){G.explicit=true;try{history.replaceState(null,'',location.pathname+location.search+'#prowadz'+r.id_aed)}catch{}$('#gname').innerHTML=`<b>${esc(r.nazwa_obiektu)}</b>${r.opis_dojscia?`<span>${esc(r.opis_dojscia)}</span>`:''}`;$('#ggm').href=mapsUrl(r);gAedAddr(r);gRetarget(r);G.nearKey=null;gNearDraw();const l=$('#live');if(l)l.textContent='Nowy cel: '+r.nazwa_obiektu}
const API4L=window.AED4LIFE_API||(((/^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname)||location.protocol==='file:')?'https://20-215-200-98.sslip.io':'')+'/api4life');
const API_N=20;
function a4lRec(a){const id='AED4L-'+a.id;const ul=[a.streetName,a.buildingNumber].filter(v=>v!=null&&v!=='').join(' ');
  return{id_aed:id,lat:+a.latitude,lon:+a.longitude,nazwa_obiektu:a.ownerName||(ul?`AED, ${ul}`:'AED'),miejscowosc:a.cityName||'',ulica:a.streetName||'',numer_budynku:a.buildingNumber!=null?String(a.buildingNumber):'',kod_pocztowy:a.postalCode||'',etykieta:[ul,a.cityName].filter(Boolean).join(', '),opis_dojscia:'',poziom_pietro:'',status_rekordu:'zweryfikowany',status_sprawnosci:'sprawny',kategoria_dostepu:'publiczny',calodobowo:'true',godziny_dostepu:'',sposob_otwarcia:'nieznany',zrodlo:'aed4life',src:['aed4life'],oceny:{tak:0,nie:0},paszport:null,wskaznik_jakosci:80,data_weryfikacji:''}}
async function apiNearestList(p){if(!p||p.la==null)return null;try{const ctl=new AbortController();setTimeout(()=>ctl.abort(),5000);const qs=`latitude=${(+p.la).toFixed(6)}&longitude=${(+p.lo).toFixed(6)}`;let rs=await fetch(`${API4L}/api/aed/nearest(${API_N})?${qs}`,{signal:ctl.signal,cache:'no-store'});if(!rs.ok)rs=await fetch(`${API4L}/api/aed/nearest?${qs}`,{signal:ctl.signal,cache:'no-store'});if(!rs.ok)return null;const j=await rs.json();
  const l=(Array.isArray(j)?j:[j]).filter(a=>a&&a.latitude!=null&&a.longitude!=null).map(a4lRec);if(!l.length)return null;AED=l;REAL=true;try{drawMap();drawList()}catch{}return l}catch{return null}}
async function apiNearest(p){const l=await apiNearestList(p);return l?l.slice().sort((x,y)=>dist(p,{la:x.lat,lo:x.lon})-dist(p,{la:y.lat,lo:y.lon}))[0]:null}
function gArrow(){if(G.b==null)return;const rot=G.heading==null?G.b:(G.b-G.heading+360)%360;$('#garrow').style.transform=`rotate(${rot}deg)`}
const onOri=e=>{const h=e.webkitCompassHeading!=null?e.webkitCompassHeading:(e.absolute&&e.alpha!=null?360-e.alpha:null);if(h!=null){G.heading=h;gArrow();gMeHead()}};
if(window.DeviceOrientationEvent){if(typeof DeviceOrientationEvent.requestPermission==='function'){$('#gcomp').hidden=false;$('#gcomp').onclick=async()=>{try{if(await DeviceOrientationEvent.requestPermission()==='granted'){addEventListener('deviceorientation',onOri);$('#gcomp').hidden=true}}catch{}}}else{addEventListener('deviceorientationabsolute',onOri);addEventListener('deviceorientation',onOri)}}
gFill();

function gAskShow(){if(window.pzNoAsk){window.pzNoAsk=0;return}let seen=false;try{seen=sessionStorage.getItem('pz_ask')==='1'}catch{}if(seen)return;$('#gask').hidden=false;setTimeout(()=>$('#gaskcall').focus(),50)}
function gAskDone(tab){try{sessionStorage.setItem('pz_ask','1')}catch{}$('#gask').hidden=true;gTab(tab)}
$('#gaskcall').onclick=()=>gAskDone('call');$('#gaskon').onclick=()=>gAskDone('call');$('#gaskno').onclick=()=>gAskDone('call');
$('#gask').addEventListener('keydown',e=>{if(e.key==='Escape')gAskDone('call')});
for(const a of $$('.g112big'))a.addEventListener('click',()=>gTab('call'));
G.addrAt=null;
async function gAddr(force){const at={la:me.la,lo:me.lo};$('#gcoord').textContent=G.addrTxt?'':`GPS: ${at.la.toFixed(5)}, ${at.lo.toFixed(5)}`;
  if(!force&&G.addrAt&&dist(G.addrAt,at)<40)return;G.addrAt=at;
  try{const ctl=new AbortController();setTimeout(()=>ctl.abort(),6000);
    const j=await(await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=18&addressdetails=1&accept-language=pl&lat=${at.la}&lon=${at.lo}`,{signal:ctl.signal})).json();const a=j.address||{};
    const street=a.road||a.pedestrian||a.footway||a.square||a.neighbourhood||'',num=a.house_number||'',town=a.city||a.town||a.village||a.municipality||'';
    const place=j.name&&j.name!==street?j.name:'';
    G.addrTxt=[place,[street,num].filter(Boolean).join(' '),[a.postcode,town].filter(Boolean).join(' ')].filter(Boolean).join(', ')||j.display_name||'';$('#gaddr').textContent=G.addrTxt||'Podaj współrzędne:';$('#gcoord').textContent=G.addrTxt?'':`GPS: ${at.la.toFixed(5)}, ${at.lo.toFixed(5)}`;$('#gsayaddr').textContent=G.addrTxt||`${at.la.toFixed(5)}, ${at.lo.toFixed(5)}`}
  catch{$('#gaddr').textContent=G.gps?'Brak adresu (brak internetu) – podaj współrzędne poniżej':'Ustalam adres…'}}

let REAL=false;
(async()=>{if(await apiNearestList(me)){const on=$('#v-prowadz').classList.contains('on');if(on&&!G.explicit){if(G.gps)gChoose();else{const n=gPick(null);n&&gRetarget(n)}}else route();return}})();
const HOW={swobodny:'Szafka jest otwarta – otwórz drzwiczki i weź AED. Może zawyć alarm, to normalne.',kod_od_dyspozytora:'Szafka na kod – kod poda dyspozytor 112. Powiedz mu, przy którym AED stoisz.',klucz_u_pracownika:'Klucz ma obsługa obiektu – poproś pracownika.',pomoc_pracownika:'Poproś obsługę obiektu o AED.'};
function gOpenInfo(r){const im=r.paszport&&typeof r.paszport.aed==='string'&&r.paszport.aed.startsWith('data:')?`<img class="gpimg" src="${r.paszport.aed}" alt="Zdjęcie miejsca, gdzie wisi AED">`:'';
  const fl=r.poziom_pietro!==''&&r.poziom_pietro!=null&&+r.poziom_pietro!==0?` · piętro ${esc(String(r.poziom_pietro))}`:'';
  $('#gopen').innerHTML=`${im}<b>${esc(HOW[r.sposob_otwarcia]||'Otwórz szafkę i weź AED. Może zawyć alarm, to normalne.')}</b>${r.opis_dojscia?`<span>Gdzie: ${esc(r.opis_dojscia)}${fl}</span>`:''}`;
  for(const b of $$('#grep button'))b.setAttribute('aria-pressed','false');$('#grepmsg').textContent=''}
if($('#gsend'))$('#gsend').onclick=async e=>{const r=G.r;if(!r)return;const b=e.currentTarget,ad=gAedAdrTxt(r),gm=`https://www.google.com/maps/dir/?api=1&travelmode=walking&destination=${r.lat},${r.lon}`;
  const pub=location.protocol==='https:'?`${location.origin}${location.pathname}#prowadz-${r.id_aed}`:gm;
  const txt=`PILNE! Przynieś AED: ${ad||r.nazwa_obiektu}${r.opis_dojscia?` (${r.opis_dojscia})`:''}. Trasa: ${pub} . Czekam tu: ${G.addrTxt||`${me.la.toFixed(5)}, ${me.lo.toFixed(5)}`}`;
  try{if(navigator.share){await navigator.share({title:'Przynieś AED',text:txt});return}}catch(x){if(x.name==='AbortError')return}
  try{await navigator.clipboard.writeText(txt);const o=b.textContent;b.textContent='Skopiowano – wklej w SMS';setTimeout(()=>b.textContent=o,3000)}catch{}
  if(/Android|iPhone|iPad/i.test(navigator.userAgent))location.href=`sms:?&body=${encodeURIComponent(txt)}`};
$('#grep').onclick=e=>{const b=e.target.closest('[data-rep]');if(!b||!G.r)return;const r=G.r,k=b.dataset.rep;
  for(const x of $$('#grep button'))x.setAttribute('aria-pressed',x===b);
  if(k==='ok'){r.data_weryfikacji=iso(TODAY);r.sposob_weryfikacji='zgloszenie_spolecznosci';if(r.status_rekordu==='wymaga_sprawdzenia')r.status_rekordu='zgloszony'}else{r.status_rekordu='wymaga_sprawdzenia';if(k==='zly')r.status_sprawnosci='nieznany'}
  try{const q=JSON.parse(localStorage.getItem('pz_reports')||'[]');q.push({id:r.id_aed,wynik:k,czas:new Date().toISOString()});localStorage.setItem('pz_reports',JSON.stringify(q))}catch{}
  $('#grepmsg').textContent=k==='ok'?'Dziękujemy. Potwierdzenie trafiło do rejestru AED.':'Dziękujemy. AED trafił do sprawdzenia przez instytucję.'};
if('serviceWorker' in navigator&&location.protocol!=='file:')addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}));

$('#ghandle').onclick=()=>{$('#gpanel').classList.toggle('full');setTimeout(()=>G.map&&G.map.invalidateSize(),300)};
