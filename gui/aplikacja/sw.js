const V='pz-v2',CORE=['./start','index.html','manifest.webmanifest','AED4life_logo.png','icon-192.png','icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==V&&x!=='pz-tiles').map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
async function trimTiles(c){const k=await c.keys();for(let i=0;i<k.length-600;i++)await c.delete(k[i])}
self.addEventListener('fetch',e=>{const r=e.request;if(r.method!=='GET')return;const u=new URL(r.url);
  if(u.hostname==='tile.openstreetmap.org'){e.respondWith(caches.open('pz-tiles').then(async c=>{const hit=await c.match(r);if(hit)return hit;try{const res=await fetch(r);if(res.ok||res.type==='opaque'){c.put(r,res.clone());trimTiles(c)}return res}catch{return new Response('',{status:504})}}));return}
  if(u.origin!==location.origin||u.pathname.startsWith('/api/'))return;
  e.respondWith(fetch(r,{cache:'no-store'}).then(res=>{if(res.ok){const cl=res.clone();caches.open(V).then(c=>c.put(r,cl))}return res}).catch(()=>caches.match(r,{ignoreSearch:true}).then(h=>h||caches.match('index.html'))))});
