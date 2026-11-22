import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import re
L=open(os.path.join(ROOT,'build','base_app.js')).read().split('\n')
def block(tok):
    i=next(k for k,l in enumerate(L) if l.startswith(tok))
    j=i+1
    while j<len(L) and (L[j].startswith(' ') or L[j]=='' and False):
        j+=1
    return i,j
def replace(tok,new):
    i,j=block(tok); L[i:j]=[new]
def textrep(a,b):
    global L
    s='\n'.join(L); assert a in s, a[:80]; L=s.replace(a,b).split('\n')

ICONS=r'''const ICO={sos:'<path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1z" fill="currentColor" stroke="none"/>',home:'<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>',map:'<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>',heart:'<path d="M12 20s-7-4.4-9-9a5 5 0 0 1 9-3 5 5 0 0 1 9 3c-2 4.6-9 9-9 9z"/><path d="M12.5 8 10 12h4l-2.5 4"/>',plus:'<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',list:'<path d="M8 6h13M8 12h13M8 18h13"/><path d="M4 6h.01M4 12h.01M4 18h.01"/>',user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',check:'<path d="M9 12l2 2 4-4"/><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',upload:'<path d="M12 15V3M7 8l5-5 5 5"/><path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/>',chart:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',data:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',route:'<circle cx="6" cy="19" r="2"/><circle cx="18" cy="5" r="2"/><path d="M8 19h7a3.5 3.5 0 0 0 0-7H9a3.5 3.5 0 0 1 0-7h7"/>',mega:'<path d="M3 11v2a1 1 0 0 0 1 1h2l5 4V6L6 10H4a1 1 0 0 0-1 1z"/><path d="M15 9a4 4 0 0 1 0 6M18 6a8 8 0 0 1 0 12"/>',lock:'<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',bldg:'<path d="M3 21h18M5 21V8l7-5 7 5v13M9 21v-5h6v5"/>',nav:'<path d="M3 11l18-8-8 18-2-8z"/>',aed:'<rect x="4" y="3" width="16" height="18" rx="3"/><path d="M12 16s-4-2.4-4-5a2.2 2.2 0 0 1 4-1.2A2.2 2.2 0 0 1 16 11c0 2.6-4 5-4 5z"/>'};
const ic=n=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICO[n]}</svg>`;
const pill=s=>`<span class="pill b-${s}">${s==='zweryfikowany'?'✓ ':''}${LBL[s]}</span>`;'''
i,_=block("const badge=")
L.insert(i,ICONS)

replace("function drawList(",r'''function drawList(){const f=filtered();$('#cnt').textContent=`${f.length} AED w pobliżu`;
  $('#list').innerHTML=f.length?f.slice(0,60).map(({r,s,d})=>`<div role="listitem"><button class="item" data-id="${r.id_aed}" aria-pressed="${sel===r.id_aed}"><b>${esc(r.nazwa_obiektu)}</b><span class="km">${fmtD(d)}</span><span class="meta">${pill(r.status_rekordu)} <span class="st ${s[0]}">${s[0]==='off'?'zamknięte':(({kod_od_dyspozytora:'kod poda 112',klucz_u_pracownika:'klucz u obsługi',pomoc_pracownika:'poproś obsługę'})[r.sposob_otwarcia]||(r.kategoria_dostepu==='dla_klientow'?'dla klientów':'otwarte'))}</span></span></button></div>`).join(''):'<p class="empty">Żaden AED nie spełnia filtrów. Odznacz któryś z nich.</p>'}''')

replace("function detail(",r'''function detail(id){sel=id;const r=AED.find(a=>a.id_aed===id);if(!r){$('#detail').innerHTML='';return}const s=state(r,at()),age=r.data_weryfikacji?months(new Date(r.data_weryfikacji),TODAY):null,canRec=ALLOW[role].includes('trasa');
  $('#detail').innerHTML=`<article class="card" aria-labelledby="dt"><div class="row" style="justify-content:space-between"><h2 id="dt" style="margin:0">${esc(r.nazwa_obiektu)}</h2>${pill(r.status_rekordu)}</div><p class="st ${s[0]}" style="margin:4px 0 0">${s[1]}</p>
  <div class="row" style="margin-top:14px"><a class="btn okb" href="${mapsUrl(r)}" rel="noopener">${ic('nav')} Prowadź</a><button id="qrBtn">${ic('check')} Jest na miejscu</button>${canRec?`<a class="btn" href="#trasa">${ic('route')} ${r.paszport?'Nagraj trasę od nowa':'Nagraj trasę, +50 pkt'}</a>`:''}</div>
  <div class="split" style="margin-top:16px"><div><dl class="kv" style="margin:0"><dt>Gdzie</dt><dd><b>${esc(r.opis_dojscia)||'brak opisu'}${r.poziom_pietro!==''?`, piętro ${r.poziom_pietro}`:''}</b></dd><dt>Jak zdobyć</dt><dd>${LBL[r.sposob_otwarcia]}</dd><dt>Godziny</dt><dd>${r.calodobowo==='true'?'całą dobę':esc(r.godziny_dostepu)||'brak danych'}</dd><dt>Sprawdzono</dt><dd>${r.data_weryfikacji?pl(r.data_weryfikacji):'nigdy'}</dd></dl>
  <details class="det"><summary>Więcej informacji</summary><dl class="kv" style="margin:4px 0 0"><dt>Adres</dt><dd>ul. ${esc(r.ulica)} ${esc(r.numer_budynku)}, ${esc(r.miejscowosc)}</dd><dt>Kto może użyć</dt><dd>${LBL[r.kategoria_dostepu]}</dd><dt>Potwierdzenia</dt><dd>${r.oceny.tak} „jest”, ${r.oceny.nie} „nie ma”</dd><dt>Jakość danych</dt><dd>${r.wskaznik_jakosci}/100</dd><dt>Źródła</dt><dd>${r.src.join(', ')}</dd></dl></details></div>
  <div>${r.paszport?passport(r,'d'):`<div class="empty" style="background:var(--sf2);border-radius:14px">${ic('route')}<br>Brak trasy od wejścia do AED</div>`}</div></div></article>`;
  $('#qrBtn').onclick=()=>{$('#dlgB').textContent=`${r.nazwa_obiektu}, ${r.miejscowosc}.`;$('#dlg').showModal()};drawMap();drawList()}''')

replace("function drawQueue(",r'''function drawQueue(){const q=AED.filter(r=>['zgloszony','wymaga_sprawdzenia'].includes(r.status_rekordu)).sort((a,b)=>(b.status_rekordu==='wymaga_sprawdzenia')-(a.status_rekordu==='wymaga_sprawdzenia')||(b.zrodlo==='zgloszenie_mieszkanca')-(a.zrodlo==='zgloszenie_mieszkanca')).slice(0,20);drawMinKpi();
  $('#queue').innerHTML=q.length?q.map(r=>`<div class="card qitem"><div class="ph">${r.zdjecie?`<img src="${r.zdjecie}" alt="Zdjęcie ze zgłoszenia">`:ic('aed')}</div><div><div class="row" style="justify-content:space-between"><b style="font-size:18px">${esc(r.nazwa_obiektu)}</b>${pill(r.status_rekordu)}</div><div class="note">${esc(r.miejscowosc)} · ${esc(r.opis_dojscia)} · źródło: ${r.src.join(', ')} · sprawdzony: ${r.data_weryfikacji?pl(r.data_weryfikacji):'nigdy'}</div>
   <div class="row"><button class="okb" data-q="ok" data-id="${r.id_aed}">Zatwierdź</button><button data-q="check" data-id="${r.id_aed}">Do sprawdzenia</button><button class="danger" data-q="del" data-id="${r.id_aed}">Usuń</button></div></div></div>`).join(''):'<p class="empty">Wszystko sprawdzone. Brak zgłoszeń do decyzji.</p>'}
function drawMinKpi(){const lv=live(AED),z=lv.filter(r=>r.status_rekordu==='zgloszony').length,w=lv.filter(r=>r.status_rekordu==='wymaga_sprawdzenia').length;
  $('#minKpi').innerHTML=[[z,'czeka na decyzję'],[w,'do sprawdzenia'],[Math.round(100*lv.filter(r=>r.status_rekordu==='zweryfikowany').length/lv.length)+'%','zweryfikowanych'],[lv.length,'AED w zbiorze']].map(([v,l])=>`<div class="kpi"><b>${v}</b><span>${l}</span></div>`).join('')}''')

# CSV output
i,j=block("$('#runCsv').onclick")
src='\n'.join(L[i:j])
src=src.replace('''<table class="stack"><thead><tr><th>Wiersz</th><th>Obiekt</th><th>Wynik</th><th>Uwagi</th></tr></thead><tbody>${res.map(x=>{const [t,col]=out(x);return `<tr><td>${x.i}</td><td>${esc(x.r.nazwa_obiektu)||'—'}<br><span class="note">${esc(x.r.opis_dojscia)}</span></td><td style="color:${col};font-weight:700">${t}</td><td>${issHTML(x.is)}</td></tr>`}).join('')}</tbody></table>''',
'''<div class="stackc">${res.map(x=>{const [t,col]=out(x);return `<div class="card"><div class="row" style="justify-content:space-between"><b>Wiersz ${x.i}: ${esc(x.r.nazwa_obiektu)||'—'}</b><span class="pill" style="color:${col};background:var(--sf2)">${t}</span></div>${x.r.opis_dojscia?`<div class="note">${esc(x.r.opis_dojscia)}</div>`:''}${issHTML(x.is)}</div>`}).join('')}</div>''')
src=src.replace('''${ok.length?`<h3 style="margin-top:16px">Plik gotowy do dane.gov.pl</h3>''','''${ok.length?`<h3 style="margin-top:20px">Plik gotowy do dane.gov.pl</h3>''')
assert 'class="stackc"' in src
L[i:j]=[src]

textrep("$('#t-'+x).classList.toggle('pri',on)}","$('#t-'+x).classList.toggle('on',on)}")
textrep("function drawData(){","function drawData(){drawFlow();$('#provs').innerHTML=provCards(false);")
textrep("$('#cpCsv').onclick=e=>{$('#export').textContent=toCSV(live(AED).slice(0,5))+'\\r\\n…';copy(toCSV(live(AED)),e.target)};","$('#cpCsv').onclick=e=>{const t=aggCSV();$('#export').textContent=t.split('\\r\\n').slice(0,6).join('\\r\\n')+'\\r\\n…';copy(t,e.target)};$('#cpDcat').onclick=()=>{$('#export').textContent=JSON.stringify({'@type':'dcat:Dataset','dct:title':'Krajowa lista defibrylatorów AED','dct:publisher':'Ministerstwo Cyfryzacji (koordynator)','dct:accrualPeriodicity':'WEEKLY','dct:license':'ODbL-1.0 (zawiera dane OpenStreetMap)','dct:modified':iso(TODAY),'dct:source':providers().map(p=>({dostawca:p.name,licencja:p.lic,rekordy:p.n})),'dcat:distribution':[{format:'CSV',conformsTo:'RFC 4180'},{format:'GeoJSON'}],uwaga:'Szkic. Pola zweryfikować z Przewodnikiem dla dostawców danych dane.gov.pl.'},null,2)};")
textrep("const TABS=['queue','form','csv','cov'];","const TABS=['queue','cov','prov','csv','form'];let curTab='queue';const showTab=t=>{curTab=t;$('#t-'+t).click()};")
textrep("if(t==='queue')drawQueue();if(t==='cov')drawCov()}","curTab=t;if(t==='queue')drawQueue();if(t==='cov')drawCov();if(t==='prov')$('#provsAdmin').innerHTML=provCards(true)}")
textrep("""$('#lic').innerHTML=Object.entries(bySrc).map(([s,c])=>`<tr><td>${s}</td><td>${LIC[s]}</td><td class="n">${c}</td></tr>`).join('');""",
"""$('#lic').innerHTML=Object.entries(bySrc).map(([s,c])=>`<div class="row" style="justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--line)"><span><b>${s}</b><br><span class="note">licencja ${LIC[s]}</span></span><b>${c}</b></div>`).join('')+'<p class="note">Zbiór zawiera dane OpenStreetMap, więc jako całość jest na ODbL 1.0.</p>';""")
textrep("""$('#meta').innerHTML=meta.map(([a,b])=>`<tr><td>${a}</td><td>${esc(b)}</td></tr>`).join('')""","""$('#meta').innerHTML=meta.map(([a,b])=>`<dt>${a}</dt><dd>${esc(b)}</dd>`).join('')""")
textrep("""<button class="pri" type="submit">${T[L].find} AED</button>""","""<button class="go2" type="submit">${T[L].find} AED</button>""")
textrep('back:"← Wróć"','back:"‹ Wróć",f_start:"Start"')
textrep('back:"← Back"','back:"‹ Back",f_start:"Home"')

replace("const ROLES={",r'''const ROLES={
  publiczny:{name:'Gość',hello:'Dzień dobry',lead:'Znajdź najbliższy defibrylator albo dowiedz się, jak pomóc.',start:'start',nav:[['start','Start','home'],['mapa','Mapa','map'],['rko','RKO','heart']],
    tiles:[['ratunek','Ratunek 112','Najbliższy AED i połączenie z 112','sos','sos'],['mapa','Mapa AED','Wszystkie defibrylatory w okolicy','map'],['rko','Jak robić RKO','Instrukcja Polskiej Rady Resuscytacji','heart'],['zglos','Zgłoś AED','Wymaga zalogowania','plus','lock']],
    desc:'Bez konta. Szybka pomoc i podgląd danych.',icon:'user',can:['Ratunek 112 i nawigacja do AED','Mapa i instrukcja RKO','Potwierdzenie „jest / nie ma”','Dane otwarte']},
  zglaszajacy:{name:'Zgłaszający',hello:'Cześć, Ania',lead:'Dziękujemy, że pomagasz utrzymać mapę AED w aktualności.',start:'start',nav:[['start','Start','home'],['mapa','Mapa','map'],['zglos','Zgłoś','plus'],['moje','Moje','list']],
    tiles:[['ratunek','Ratunek 112','Najbliższy AED i połączenie z 112','sos','sos'],['zglos','Zgłoś AED','Lokalizacja, opis i zdjęcie','plus'],['moje','Moje zgłoszenia','Status i punkty','list','',()=>mine().filter(r=>r.status_rekordu!=='zweryfikowany').length],['moje','Nagraj trasę','AED w okolicy bez trasy, +50 pkt','route'],['mapa','Mapa AED','Defibrylatory w okolicy','map'],['akcja','Akcja','Naklejki QR i punkty','mega']],
    desc:'Mieszkaniec, wolontariusz, zarządca budynku.',icon:'plus',can:['Zgłaszanie AED ze zdjęciem','Nagrywanie trasy od wejścia (+50 pkt)','Śledzenie statusu zgłoszeń']},
  ministerstwo:{name:'Ministerstwo Cyfryzacji',hello:'Panel koordynatora',lead:'Krajowy zbiór AED: weryfikacja, jakość danych i publikacja w dane.gov.pl.',start:'start',nav:[['start','Start','home'],['dysponent','Panel','check'],['mapa','Mapa','map']],
    tiles:[['ratunek','Ratunek 112','Podgląd trybu dla obywatela','sos','sos'],['weryfikacja','Do weryfikacji','Zgłoszenia czekające na decyzję','check','',()=>live(AED).filter(r=>['zgloszony','wymaga_sprawdzenia'].includes(r.status_rekordu)).length],['pokrycie','Pokrycie kraju','Miasta wymagające działania','chart'],['dostawcy','Dostawcy danych','Zbiory w dane.gov.pl i ich aktualność','upload'],['import','Import pliku','Sprawdzenie CSV od dysponenta','list'],['mapa','Mapa AED','Podgląd zbioru','map']],
    desc:'Koordynator zbioru krajowego i publikacji.',icon:'bldg',can:['Weryfikacja zgłoszeń','Import danych z walidacją','Pokrycie kraju i jakość','Eksport do dane.gov.pl']}};''')
replace("const ALLOW=",r'''const ALLOW={publiczny:['start','ratunek','rko','mapa','konto','akcja'],zglaszajacy:['start','ratunek','rko','mapa','konto','akcja','zglos','trasa','moje'],ministerstwo:['start','ratunek','rko','mapa','konto','akcja','zglos','trasa','moje','dysponent']};''')
replace("function drawNav(",r'''function drawNav(){$('#tabs').innerHTML=ROLES[role].nav.map(([h,t,i])=>`<a href="#${h}">${ic(i)}<span>${t}</span></a>`).join('');$('#who').innerHTML=`<span class="av">${ic(ROLES[role].icon)}</span><span class="nm">${role==='publiczny'?'Zaloguj się':ROLES[role].name}</span>`;$('#who').setAttribute('aria-label',role==='publiczny'?'Zaloguj się':'Konto: '+ROLES[role].name)}
function drawStart(){const R=ROLES[role];$('#hello').textContent=R.hello;$('#startLead').textContent=R.lead;
  $('#tiles').innerHTML=R.tiles.map(([h,t,d,i,cls,cnt])=>{const c=cnt?cnt():0;return `<a class="tile ${cls||''}" href="#${h}"><span class="ic">${ic(cls==='lock'?'lock':i)}</span><span><b>${t}</b><br><span class="d">${d}</span></span>${c?`<span class="cnt" aria-label="${c} do zrobienia">${c}</span>`:''}</a>`}).join('');
  let info='';if(role==='publiczny')info=`<div class="card row" style="justify-content:space-between"><span><b>W Twoim budynku jest AED?</b><br><span class="note">Zaloguj się, zrób mu zdjęcie i dodaj go do mapy.</span></span><a class="btn pri" href="#konto">Zaloguj się</a></div>`;
  if(role==='zglaszajacy'){const r=mine().sort((a,b)=>(b.data_dodania_w_zrodle||'').localeCompare(a.data_dodania_w_zrodle||''))[0];if(r)info=`<div class="card"><span class="note">Ostatnie zgłoszenie</span><div class="row" style="justify-content:space-between;margin-top:4px"><b style="font-size:19px">${esc(r.nazwa_obiektu)}</b>${pill(r.status_rekordu)}</div><div class="note">${r.status_rekordu==='zweryfikowany'?'Zatwierdzone. AED jest widoczny w trybie ratunkowym.':'Czeka na decyzję instytucji. Zwykle trwa to do 3 dni.'}</div></div>`}
  if(role==='ministerstwo'){const lv=live(AED);info=`<div class="card"><b>Stan zbioru</b><div class="bar" style="margin:10px 0 6px;height:12px"><i style="width:${Math.round(100*lv.filter(r=>r.status_rekordu==='zweryfikowany').length/lv.length)}%;background:var(--ok)"></i></div><span class="note">${lv.filter(r=>r.status_rekordu==='zweryfikowany').length} z ${lv.length} AED zweryfikowanych w ostatnim roku. Ostatnia publikacja w dane.gov.pl: ${pl(iso(TODAY))}.</span></div>`}
  $('#startInfo').innerHTML=info}''')
replace("function drawRoles(",r'''function drawRoles(){$('#roles').innerHTML=Object.entries(ROLES).map(([k,v])=>`<button class="role" data-role="${k}" aria-pressed="${k===role}"><span class="ic">${ic(v.icon)}</span><b>${v.name}</b><span>${v.desc}</span><ul>${v.can.map(c=>`<li>${c}</li>`).join('')}</ul><span class="btn ${k===role?'':'pri'}">${k===role?'Aktywny widok':(k==='publiczny'?'Kontynuuj jako gość':'Zaloguj się')}</span></button>`).join('')}''')
replace("function drawMoje(",r'''function drawMoje(){const m=mine(),pts=points+m.length*20;$('#mojeLead').textContent='Zgłoszenie pojawi się w trybie ratunkowym po zatwierdzeniu przez instytucję.';
  $('#mojeKpi').innerHTML=[[m.length,'zgłoszonych AED'],[m.filter(r=>r.status_rekordu==='zweryfikowany').length,'zatwierdzonych'],[AED.filter(r=>r.paszport&&r.paszport.autor==='wolontariusz (Ty)').length,'nagranych tras'],[pts,'punktów']].map(([v,l])=>`<div class="kpi"><b>${v}</b><span>${l}</span></div>`).join('');
  const tl=r=>r.status_rekordu==='wymaga_sprawdzenia'||r.status_rekordu==='usuniety'?`<span class="tl"><i class="done">zgłoszony</i>›<i class="now">${LBL[r.status_rekordu]}</i></span>`:`<span class="tl"><i class="done">zgłoszony</i>›<i class="${r.status_rekordu==='zweryfikowany'?'done':'now'}">${r.status_rekordu==='zweryfikowany'?'zweryfikowany':'czeka na weryfikację'}</i></span>`;
  $('#mojeList').innerHTML=m.length?m.map(r=>`<div class="card"><div class="row" style="justify-content:space-between"><b style="font-size:19px">${esc(r.nazwa_obiektu)}</b><span class="note">${pl(r.data_dodania_w_zrodle)}</span></div><div class="note">${esc(r.miejscowosc)} · ${esc(r.opis_dojscia)}</div>${tl(r)}<div class="row" style="margin-top:10px">${r.paszport?`<span class="pill b-zweryfikowany">✓ trasa nagrana</span>`:`<a class="btn" href="#trasa" data-sel="${r.id_aed}">${ic('route')} Nagraj trasę, +50 pkt</a>`}</div></div>`).join(''):'<p class="empty">Nie masz jeszcze zgłoszeń.</p>';
  const todo=live(AED).filter(r=>!r.paszport&&r.umiejscowienie==='w_budynku'&&r.autor!=='ja').map(r=>({r,d:dist(me,{la:r.lat,lo:r.lon})})).sort((a,b)=>a.d-b.d).slice(0,4);
  $('#mojeTodo').innerHTML=todo.map(({r,d})=>`<a class="card row" href="#trasa" data-sel="${r.id_aed}" style="justify-content:space-between;text-decoration:none;color:inherit"><span><b>${esc(r.nazwa_obiektu)}</b><br><span class="note">${fmtD(d)} · ${esc(r.opis_dojscia)}</span></span><span class="btn">${ic('route')} +50 pkt</span></a>`).join('')}''')
replace("function drawCov(",r'''function drawCov(){const by={};for(const r of AED){if(r.status_rekordu==='usuniety')continue;const c=by[r.miejscowosc]||(by[r.miejscowosc]={n:0,v:0,q:0,p:0,chk:0,z:0});c.n++;c.q+=r.wskaznik_jakosci;if(r.status_rekordu==='zweryfikowany')c.v++;if(r.paszport)c.p++;if(r.status_rekordu==='wymaga_sprawdzenia')c.chk++;if(r.status_rekordu==='zgloszony')c.z++}
  const rows=Object.entries(by).map(([k,c])=>({k,...c,pv:Math.round(100*c.v/c.n),aq:Math.round(c.q/c.n),pp:Math.round(100*c.p/c.n)})).sort((a,b)=>a.pv-b.pv);
  $('#cov').innerHTML=rows.map(r=>`<div class="card"><div class="row" style="justify-content:space-between"><b style="font-size:19px">${r.k}</b><span class="note">${r.n} AED</span></div><div class="row" style="justify-content:space-between;margin-top:8px"><span>Zweryfikowane</span><b style="color:${r.pv<50?'var(--red)':'var(--ok)'}">${r.pv}%</b></div><div class="bar"><i style="width:${r.pv}%;background:${r.pv<50?'var(--red)':'var(--ok)'}"></i></div><div class="row" style="margin-top:10px;gap:6px">${r.z?`<span class="pill b-zgloszony">${r.z} czeka na decyzję</span>`:''}${r.chk?`<span class="pill b-wymaga_sprawdzenia">${r.chk} do sprawdzenia</span>`:''}<span class="pill b-usuniety">trasy: ${r.pp}%</span><span class="pill b-usuniety">jakość: ${r.aq}</span></div></div>`).join('')}''')
replace("const VIEWS=",r'''const VIEWS=['start','ratunek','rko','konto','moje','locked','mapa','zglos','trasa','dysponent','dane','akcja'],NAVMAP={trasa:'mapa',ratunek:'start',akcja:'start',konto:'start',locked:'start'},TABHASH={weryfikacja:'queue',pokrycie:'cov',dostawcy:'prov',import:'csv',dodaj:'form'};''')
replace("function route(",r'''let lastView='';function route(){let h=location.hash.slice(1);if(h.startsWith('potwierdz-')){const id=h.slice(10);location.hash='mapa';if(AED.some(a=>a.id_aed===id)){detail(id);$('#qrBtn').click()}return}
  let tab=null;if(TABHASH[h]){tab=TABHASH[h];h='dysponent'}if(!VIEWS.includes(h))h=ROLES[role].start;
  if(!ALLOW[role].includes(h)&&h!=='locked'){$('#lockTxt').textContent=h==='dysponent'?'Panel jest dostępny dla pracowników Ministerstwa Cyfryzacji.':'Zgłaszanie AED i nagrywanie tras wymaga konta. Dzięki temu rejestr jest chroniony przed fałszywymi wpisami.';h='locked'}
  for(const v of VIEWS)$('#v-'+v).classList.toggle('on',v===h);const navH=NAVMAP[h]||h;for(const a of $$('#tabs a'))a.getAttribute('href')==='#'+navH?a.setAttribute('aria-current','page'):a.removeAttribute('aria-current');
  if(h!==lastView&&h!=='mapa')window.scrollTo(0,0);lastView=h;
  if(h!=='mapa'&&pickFor&&h!=='zglos'&&h!=='ratunek')pickFor=null;if(h==='mapa'){if(pickFor){$('#pickbar').textContent=pickFor==='zglos'?'Dotknij miejsca, gdzie wisi AED':'Dotknij miejsca, gdzie jesteś'}drawMap();drawList();if(sel)detail(sel)}
  document.body.classList.toggle('sosmode',h==='ratunek');if(h==='ratunek')renderSos();if(h==='start')drawStart();if(h==='trasa')wizStart();if(h==='dysponent'){showTab(tab||curTab)}if(h==='dane')drawData();if(h==='konto')drawRoles();if(h==='moje')drawMoje()}''')
textrep("location.hash=ROLES[role].start};","location.hash='start'};")

NEW_PROV=r"""const PROVT={jst:c=>`Gmina ${c}`,sluzby_ratownicze:c=>`Straż pożarna – ${c}`,oswiata:c=>`Szkoły i uczelnie – ${c}`,ochrona_zdrowia:c=>`Placówki medyczne – ${c}`,transport:()=>'Zarządca dworców (przykład)',handel_i_uslugi:()=>'Zarządcy obiektów handlowych (przykład)'};
function dostOf(r){const d=[];if(r.src.includes('osm'))d.push('OpenStreetMap');if(r.src.includes('dysponent'))d.push((PROVT[r.dysponent_typ]||(()=>r.dysponent_nazwa||'Dysponent'))(r.miejscowosc));if(r.src.includes('zgloszenie_mieszkanca')||r.src.includes('potwierdzenie_qr'))d.push('Zgłoszenia mieszkańców');return [...new Set(d)]}
let fetchShift={};
function providers(){const m={};for(const r of live(AED))for(const p of dostOf(r)){const x=m[p]||(m[p]={name:p,n:0,chk:0,ver:0});x.n++;if(r.status_rekordu==='wymaga_sprawdzenia')x.chk++;if(r.status_rekordu==='zweryfikowany')x.ver++}
  return Object.values(m).map(x=>{const kind=x.name==='OpenStreetMap'?'osm':x.name==='Zgłoszenia mieszkańców'?'mies':'inst';let h=0;for(const c of x.name)h=(h*31+c.charCodeAt(0))%997;const days=fetchShift[x.name]?0:h%7;
    return {...x,kind,lic:kind==='osm'?'ODbL-1.0':'CC0-1.0',mode:kind==='osm'?'pobieranie z API OpenStreetMap codziennie':kind==='mies'?'formularz i kody QR w aplikacji':'automatyczna aktualizacja ze stałego adresu URL, co tydzień',last:new Date(TODAY-days*864e5),fmt:kind==='osm'?'GeoJSON':'CSV (wzorcowy schemat)'}}).sort((a,b)=>b.n-a.n)}
const AGG=["id_aed","etykieta","lat","lon","miejscowosc","adres","umiejscowienie","poziom_pietro","opis_dojscia","kategoria_dostepu","calodobowo","godziny_dostepu","sposob_otwarcia","status_sprawnosci","status_rekordu","data_weryfikacji","wskaznik_jakosci","liczba_dostawcow","dostawcy","identyfikatory_zrodlowe","licencje_zrodel","data_aktualizacji"];
function aggRows(){return live(AED).map(r=>{const d=dostOf(r);return {...r,adres:[r.ulica&&'ul. '+r.ulica,r.numer_budynku].filter(Boolean).join(' '),liczba_dostawcow:d.length,dostawcy:d.join(';'),identyfikatory_zrodlowe:d.map(p=>`${p==='OpenStreetMap'?'osm':p}:${p==='OpenStreetMap'?r.id_zrodla:r.id_aed}`).join(';'),licencje_zrodel:[...new Set(d.map(p=>p==='OpenStreetMap'?'ODbL-1.0':'CC0-1.0'))].join(';'),data_aktualizacji:iso(TODAY)}})}
const aggCSV=()=>[AGG.join(','),...aggRows().map(r=>AGG.map(k=>csvCell(r[k])).join(','))].join('\r\n');
let provAll=false;
function provCards(admin){const ps=providers(),show=provAll?ps:ps.slice(0,8);return `<div class="card" style="padding:6px 18px">${show.map(p=>`<div class="prow"><span><b>${esc(p.name)}</b><br><span class="note">${p.fmt} · ${p.mode} · pobrano ${pl(iso(p.last))} · ${p.lic}</span></span><span class="pr"><b>${p.n}</b><span class="note">AED</span>${p.chk?`<span class="pill b-zgloszony">${p.chk} do poprawy</span>`:`<span class="pill b-zweryfikowany">✓ zgodny</span>`}${admin?`<button data-fetch="${esc(p.name)}" style="min-height:40px;font-size:14px;padding:6px 12px">Pobierz</button>`:''}</span></div>`).join('')}</div>${ps.length>8?`<button data-provall style="margin-top:10px">${provAll?'Pokaż mniej':`Pokaż wszystkich dostawców (${ps.length})`}</button>`:''}`}
document.addEventListener('click',e=>{if(!e.target.closest('[data-provall]'))return;provAll=!provAll;if($('#provs'))$('#provs').innerHTML=provCards(false);if($('#provsAdmin'))$('#provsAdmin').innerHTML=provCards(true)});
document.addEventListener('click',e=>{const b=e.target.closest('[data-fetch]');if(!b)return;fetchShift[b.dataset.fetch]=1;$('#provsAdmin').innerHTML=provCards(true);$('#live').textContent=`Pobrano zbiór: ${b.dataset.fetch}. Walidacja zakończona.`});
function drawFlow(){const pv=providers(),ag=aggRows(),inRec=ag.reduce((a,r)=>a+r.liczba_dostawcow,0),multi=ag.filter(r=>r.liczba_dostawcow>1).length;
  $('#flow').innerHTML=`<div class="card"><span class="ic">${ic('upload')}</span><span class="num">${pv.length}</span><b>dostawców publikuje zbiory</b><p class="note" style="margin:4px 0 0">Gminy, straż pożarna, szkoły, zarządcy obiektów, OpenStreetMap, mieszkańcy. Każdy we wzorcowym schemacie.</p></div>
  <div class="card"><span class="ic">${ic('check')}</span><span class="num">${inRec} → ${ag.length}</span><b>walidacja i scalanie</b><p class="note" style="margin:4px 0 0">Te same AED od kilku dostawców (do 25 m, podobna nazwa) łączymy w jeden rekord: ${multi} potwierdzonych podwójnie.</p></div>
  <div class="card"><span class="ic">${ic('data')}</span><span class="num">1</span><b>krajowa lista w dane.gov.pl</b><p class="note" style="margin:4px 0 0">Wybrane pola, pochodzenie i licencja każdego rekordu. Aktualizacja co tydzień.</p></div>`}
"""
i,_=block('function drawData(')
L.insert(i,NEW_PROV)

i=next(k for k,l in enumerate(L) if l.startswith("  if(sos.st==='ask'){box.innerHTML="))
L[i]=r"""  if(sos.st==='ask'){box.innerHTML=`<div class="askbig"><a class="big green" style="min-height:150px;font-size:clamp(30px,8vw,44px)" href="${gmSearch('')}" rel="noopener">${T[L].openMap}<span class="sub">${T[L].openMap_s}</span></a><form id="locForm" role="search" style="display:grid;gap:8px"><label for="addr" style="font-size:18px;font-weight:700">${T[L].orAddr}</label><div class="row" style="flex-wrap:nowrap"><input type="text" id="addr" autocomplete="street-address" enterkeyhint="go" placeholder="${T[L].ph}"><button type="submit" class="go2" style="min-height:56px;font-size:18px;flex:none" aria-label="${T[L].find}">${ic('nav')}</button></div></form>${framed?`<button type="button" data-sos="demo" style="font-size:15px;min-height:44px">${T[L].demo}</button>`:''}</div>`;return}"""
textrep("if(!g){$('#askErr').textContent=T[L].notfound;return}","if(!g){location.href=gmSearch($('#addr').value);return}")
textrep("const mapsUrl=r=>","const gmSearch=q=>`https://www.google.com/maps/dir/?api=1&travelmode=walking&destination=${encodeURIComponent('defibrylator AED')}${q&&q.trim()?`&origin=${encodeURIComponent(q.trim())}`:''}`;const mapsUrl=r=>")
textrep('ask:"Gdzie jesteś?"','ask:"Gdzie jesteś?",openMap:"Prowadź do AED",openMap_s:"Google Maps wyznaczy trasę od Ciebie",orAddr:"albo wpisz, gdzie jesteś, a wskażemy sprawdzony AED:"')
textrep('ask:"Where are you?"','ask:"Where are you?",openMap:"Go to AED",openMap_s:"Google Maps will route you from where you are",orAddr:"or type where you are and we’ll pick a verified AED:"')


i=next(k for k,l in enumerate(L) if l.startswith("  if(!best||best.d>AED_MAX){box.innerHTML="))
L[i]="""  if(!best||best.d>AED_MAX){uczFar=best||null;box.innerHTML=`<a class="big red" href="#uciskaj" style="background:light-dark(#1a1d2e,#2c2f38);font-size:clamp(34px,9vw,52px)">${T[L].press}<span class="sub">${T[L].press_s}</span></a>`;return}"""
textrep('noaed:"Brak AED w pobliżu",noaed_s:"Zadzwoń 112 i uciskaj klatkę piersiową",','noaed:"Brak AED w pobliżu",noaed_s:"Zadzwoń 112 i uciskaj klatkę piersiową",press:"UCISKAJ KLATKĘ",press_s:"AED jest za daleko. Pokażę Ci, jak.",ucz_h:"AED jest za daleko. Uciskaj klatkę piersiową.",ucz_rate:"w rytm tego koła",ucz_how:"Środek klatki. Mocno, 5–6 cm. Nie przerywaj do przyjazdu karetki.",ucz_sound:"Włącz dźwięk rytmu",ucz_sound_off:"Wyłącz dźwięk",ucz_time:"Uciskasz od",say_h:"Powiedz dyspozytorowi 112:",coords:"współrzędne",runner:"Ktoś jest obok? Niech pobiegnie po AED ({d}). Wyślij mu trasę:",send:"Wyślij trasę",')
textrep('noaed:"No AED nearby",noaed_s:"Call 112 and push on the chest",','noaed:"No AED nearby",noaed_s:"Call 112 and push on the chest",press:"PUSH ON THE CHEST",press_s:"The AED is too far. I’ll show you how.",ucz_h:"The AED is too far. Push on the chest.",ucz_rate:"to the beat of this circle",ucz_how:"Centre of the chest. Hard, 5–6 cm. Don’t stop until the ambulance arrives.",ucz_sound:"Turn on the beat sound",ucz_sound_off:"Turn off sound",ucz_time:"Pushing for",say_h:"Tell the 112 dispatcher:",coords:"coordinates",runner:"Someone with you? They can run for the AED ({d}). Send them the route:",send:"Send route",')
textrep("w_serwisie:\"w serwisie\",zgloszony:\"zgłoszony\",zweryfikowany:\"zweryfikowany\",wymaga_sprawdzenia:\"wymaga sprawdzenia\"","w_serwisie:\"w serwisie\",zgloszony:\"czeka na sprawdzenie\",zweryfikowany:\"sprawdzony\",wymaga_sprawdzenia:\"do sprawdzenia\"")
UCZ=r"""let uczFar=null,uczStart=0,uczT=null,uczSnd=false,uczCtx=null;
function uczOpen(){uczStart=Date.now();clearInterval(uczT);let on=false;
  uczT=setInterval(()=>{on=!on;const p=$('#press');if(!p||!$('#v-uciskaj').classList.contains('on')){clearInterval(uczT);return}p.classList.toggle('on',on);
    if(on&&uczSnd&&uczCtx){const o=uczCtx.createOscillator(),g=uczCtx.createGain();o.frequency.value=880;g.gain.value=.2;o.connect(g).connect(uczCtx.destination);o.start();o.stop(uczCtx.currentTime+.05)}
    const s=Math.floor((Date.now()-uczStart)/1000);$('#uczT').textContent=`${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`},60000/110/2);
  const addr=me.src&&me.src.startsWith('adres:')?me.src.replace(/^adres: /,'').replace(/ \(.*\)$/,''):'';
  $('#sayWhere').textContent=addr||`${me.la.toFixed(5)}, ${me.lo.toFixed(5)}`;$('#sayExtra').textContent=addr?'':T[L].coords+' (GPS)';
  const far=uczFar||live(AED).filter(r=>r.status_rekordu==='zweryfikowany').map(r=>({r,d:dist(me,{la:r.lat,lo:r.lon})})).sort((a,b)=>a.d-b.d)[0];
  $('#uczAed').innerHTML=far&&far.d<2000?`<div class="say"><span class="note">${T[L].runner.replace('{d}',fmtD(far.d))}</span><div class="row" style="margin-top:10px"><button class="okb" id="uczSend">${ic('nav')} ${T[L].send}</button></div></div>`:'';
  $('#uczSend')&&($('#uczSend').onclick=e=>copy(`Pilne: potrzebny AED. Biegnij tutaj: ${mapsUrl(far.r)} i przynieś go do: ${addr||me.la.toFixed(5)+', '+me.lo.toFixed(5)}`,e.target,T[L].copied))}
document.addEventListener('click',e=>{if(e.target.closest('#uczSound')){uczSnd=!uczSnd;try{uczCtx=uczCtx||new (window.AudioContext||window.webkitAudioContext)()}catch{}e.target.closest('#uczSound').textContent=uczSnd?T[L].ucz_sound_off:T[L].ucz_sound}});"""
j=next(k for k,l in enumerate(L) if l.startswith("let metro=null"))
L.insert(j,UCZ)
textrep("const VIEWS=['start','ratunek','rko',","const VIEWS=['start','ratunek','uciskaj','dostepnosc','rko',")
textrep("document.body.classList.toggle('sosmode',h==='ratunek');","document.body.classList.toggle('sosmode',h==='ratunek'||h==='uciskaj');if(h==='uciskaj')uczOpen();")
for r in ["publiczny","zglaszajacy","ministerstwo"]:
    pass
textrep("const ALLOW={publiczny:['start',","const ALLOW={publiczny:['uciskaj','dostepnosc','start',")
textrep("zglaszajacy:['start',","zglaszajacy:['uciskaj','dostepnosc','start',")
textrep("ministerstwo:['start',","ministerstwo:['uciskaj','dostepnosc','start',")
textrep("['rko','RKO','heart']","['rko','Jak pomóc','heart']")
textrep("['rko','Jak robić RKO','Instrukcja Polskiej Rady Resuscytacji','heart']","['rko','Jak uciskać klatkę','Krok po kroku, według Polskiej Rady Resuscytacji','heart']")


ICO2="""ICO.chev='<path d="M9 6l6 6-6 6"/>';"""
k=next(i for i,l in enumerate(L) if l.startswith("const ic=n=>"))
L.insert(k+1,ICO2)
i,j=block("function drawStart(")
L[i:j]=[r"""function drawStart(){const R=ROLES[role];const H=R.hero;
  $('#hero').innerHTML=`<a class="hero ${H.cls||''}" href="#${H.h}"><span class="hic">${ic(H.i)}</span><span><b>${H.t}</b><span class="s">${H.d}</span></span><span class="chev">${ic('chev')}</span></a>`;
  $('#rows').innerHTML=R.rows.map(([h,t,i,cls,cnt])=>{const c=cnt?cnt():0;return `<a class="rowi ${cls||''}" href="#${h}"><span class="ic">${ic(cls==='lock'?'lock':i)}</span><b>${t}</b>${c?`<span class="cnt">${c}</span>`:'<span></span>'}<span class="chev">${ic('chev')}</span></a>`}).join('');
  let info='';if(role==='zglaszajacy'){const r=mine().sort((a,b)=>(b.data_dodania_w_zrodle||'').localeCompare(a.data_dodania_w_zrodle||''))[0];if(r)info=`<div class="card row" style="justify-content:space-between"><span><span class="note">Twoje ostatnie zgłoszenie</span><br><b style="font-size:18px">${esc(r.nazwa_obiektu)}</b></span>${pill(r.status_rekordu)}</div>`}
  $('#startInfo').innerHTML=info}"""]
textrep("['ratunek','Ratunek 112','Najbliższy AED i połączenie z 112','sos','sos'],['mapa','Mapa AED','Wszystkie defibrylatory w okolicy','map'],","['ratunek','Ratunek 112','Najbliższy AED i połączenie z 112','sos','sos'],['mapa','Mapa AED','Wszystkie defibrylatory w okolicy','map'],")

k=next(i for i,l in enumerate(L) if l.startswith("const ALLOW="))
L.insert(k,r"""ROLES.publiczny.hero={h:'ratunek',t:'Ktoś potrzebuje pomocy?',d:'Najbliższy AED i telefon 112',i:'sos'};
ROLES.publiczny.rows=[['mapa','Mapa AED','map'],['rko','Jak uciskać klatkę','heart'],['zglos','Zgłoś AED','plus','lock']];
ROLES.zglaszajacy.hero={h:'ratunek',t:'Ktoś potrzebuje pomocy?',d:'Najbliższy AED i telefon 112',i:'sos'};
ROLES.zglaszajacy.rows=[['zglos','Zgłoś AED','plus'],['moje','Moje zgłoszenia','list','',()=>mine().filter(r=>r.status_rekordu!=='zweryfikowany').length],['mapa','Mapa AED','map'],['rko','Jak uciskać klatkę','heart']];
ROLES.ministerstwo.hero={h:'weryfikacja',t:'',d:'Zgłoszenia czekają na Twoją decyzję',i:'check',cls:'blue'};
ROLES.ministerstwo.rows=[['ratunek','Ratunek 112','sos','red'],['pokrycie','Pokrycie kraju','chart'],['dostawcy','Dostawcy danych','upload'],['import','Import pliku','list'],['mapa','Mapa AED','map']];""")
textrep("function drawStart(){const R=ROLES[role];const H=R.hero;","function drawStart(){const R=ROLES[role];const H={...R.hero};if(role==='ministerstwo'){const n=live(AED).filter(r=>['zgloszony','wymaga_sprawdzenia'].includes(r.status_rekordu)).length;H.t=n?`${n} zgłoszeń do sprawdzenia`:'Wszystko sprawdzone';}")

textrep('goBig:"IDŹ DO AED"','goBig:"Idź do AED"')
textrep('goBig:"GO TO AED"','goBig:"Go to AED"')
textrep('press:"UCISKAJ KLATKĘ"','press:"Uciskaj klatkę"')
textrep('press:"PUSH ON THE CHEST"','press:"Push on the chest"')
textrep("function drawStart(){","let entered=false;function drawStart(){")
textrep("  $('#startInfo').innerHTML=info}","  $('#startInfo').innerHTML=info;if(!entered){entered=true;$('#hero').firstElementChild?.classList.add('enter');$('#rows').classList.add('enter2')}}")

textrep("function drawStart(){const R=ROLES[role];","function drawStart(){const R=ROLES[role];$('#hello').textContent={publiczny:'Pomoc przy zatrzymaniu krążenia',zglaszajacy:'Cześć, Ania',ministerstwo:'Panel koordynatora'}[role];")

textrep("$('#hello').textContent={publiczny:","{const lv=live(AED);$('#fact').textContent=`W rejestrze ${lv.length} defibrylatorów, ${lv.filter(r=>r.status_rekordu==='zweryfikowany').length} sprawdzonych w ostatnim roku. Dane przykładowe.`}$('#hello').textContent={publiczny:")

textrep("function drawMap(){","function drawSvg(){")
LMCODE=r"""const LF=window.L;const LM={map:null,ok:false,layer:null,hl:null,bld:{}};const PLB=[[48.99,14.11],[54.84,24.16]];
function drawMap(){if(LM.ok)drawLeaflet();else drawSvg()}
function lmInit(){if(LM.map||!window.L)return;if(location.protocol==='file:'){$('#maphint').hidden=false;return}
  LM.map=LF.map('lmap',{zoomControl:false,attributionControl:true}).setView([me.la,me.lo],14);LM.map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
  LM.osm=LF.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,referrerPolicy:'strict-origin-when-cross-origin',attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'});
  LM.osm.on('tileerror',()=>{if(location.protocol==='file:')$('#pickbar').textContent='Mapa z budynkami działa po opublikowaniu strony pod adresem https (np. GitHub Pages).'});
  LM.osm.addTo(LM.map);LM.osm.once('tileload',()=>{LM.ok=true;$('#fig').classList.add('live');LM.map.invalidateSize();drawMap();if(sel)showBuilding(AED.find(a=>a.id_aed===sel))});
  LM.layer=LF.layerGroup().addTo(LM.map);LM.map.on('click',e=>onMapPick(e.latlng.lat,e.latlng.lng));LM.map.on('dragstart',()=>{if(LM.follow){LM.follow=false;$('#zloc').setAttribute('aria-pressed','false')}})}
function drawLeaflet(){$('#fig').classList.toggle('pick',!!pickFor);const dt=at(),vis=new Set(filtered().map(o=>o.r.id_aed));LM.layer.clearLayers();
  for(const r of live(AED)){const [c,t]=state(r,dt),unv=r.status_rekordu!=='zweryfikowany',col=c==='ok'?'#0a7a3e':c==='warn'?'#8f5300':'#7a7a7a';
    LF.circleMarker([r.lat,r.lon],{radius:sel===r.id_aed?12:9,color:unv?'#111':col,weight:unv?2.5:2,dashArray:unv?'4 3':null,fillColor:c==='warn'||unv?'#fff':col,fillOpacity:vis.has(r.id_aed)?1:.35,opacity:vis.has(r.id_aed)?1:.35}).bindTooltip(`${esc(r.nazwa_obiektu)} · ${t}`).on('click',e=>{LF.DomEvent.stopPropagation(e);if(!pickFor)location.hash='prowadz'+r.id_aed}).addTo(LM.layer)}
  meMarker()}
function onMapPick(la,lo){const pos={la:+la.toFixed(6),lo:+lo.toFixed(6)};
  if(pickFor==='zglos'){repPos=pos;pickFor=null;$('#repPos').textContent=`${pos.la}, ${pos.lo}`;location.hash='zglos';return}
  if(LM.watch!=null){navigator.geolocation.clearWatch(LM.watch);LM.watch=null;LM.gps=null;LM.follow=false;LM.acc&&(LM.acc.remove(),LM.acc=null);$('#zloc').setAttribute('aria-pressed','false')}me={...pos,src:'wskazano na mapie'};saveMe();if(pickFor==='ratunek'){pickFor=null;location.hash='ratunek';return}$('#live').textContent='Ustawiono Twoją lokalizację.';drawMap();drawList()}
const inPoly=(pt,poly)=>{let c=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const [yi,xi]=poly[i],[yj,xj]=poly[j];if(((yi>pt[0])!==(yj>pt[0]))&&(pt[1]<(xj-xi)*(pt[0]-yi)/(yj-yi)+xi))c=!c}return c};
async function showBuilding(r){if(!LM.ok||!r)return;if(LM.hl){LM.hl.remove();LM.hl=null}LM.map.flyTo([r.lat,r.lon],18,{duration:.6});
  const label=`AED: ${esc(r.opis_dojscia||r.nazwa_obiektu)}${r.poziom_pietro!==''?`, piętro ${r.poziom_pietro}`:''}`;
  let poly=LM.bld[r.id_aed];
  if(poly===undefined){poly=null;try{const ctl=new AbortController();setTimeout(()=>ctl.abort(),6000);
      const q=`[out:json][timeout:8];way["building"](around:30,${r.lat},${r.lon});out geom;`;
      const res=await fetch('https://overpass-api.de/api/interpreter',{method:'POST',body:'data='+encodeURIComponent(q),signal:ctl.signal});const j=await res.json();
      const ws=(j.elements||[]).map(w=>w.geometry.map(g=>[g.lat,g.lon]));const pt=[r.lat,r.lon];
      poly=ws.find(w=>inPoly(pt,w))||ws.map(w=>({w,d:Math.min(...w.map(([a,b])=>dist({la:a,lo:b},{la:r.lat,lo:r.lon})))})).sort((a,b)=>a.d-b.d)[0]?.w||null}catch{}LM.bld[r.id_aed]=poly}
  if(sel!==r.id_aed)return;
  LM.hl=poly?LF.polygon(poly,{color:'#c8102e',weight:3,fillColor:'#c8102e',fillOpacity:.22}):LF.circle([r.lat,r.lon],{radius:22,color:'#c8102e',weight:3,dashArray:'6 4',fillColor:'#c8102e',fillOpacity:.12});
  LM.hl.addTo(LM.map).bindTooltip(label,{permanent:true,direction:'top',className:'aedtip',offset:[0,-8]})}
$('#zin').onclick=()=>LM.ok?LM.map.zoomIn():zoom(.6);$('#zout').onclick=()=>LM.ok?LM.map.zoomOut():zoom(1/.6);
$('#zpl').onclick=()=>{if(LM.ok)LM.map.fitBounds(PLB);else{vb=[-20,-20,680,640];drawSvg()}};
const meIcon=st=>LF.divIcon({className:'medot'+(st?' stale':''),html:'<b></b><i></i>',iconSize:[18,18]});
function meMarker(){if(!LM.ok)return;const ll=[me.la,me.lo];if(!LM.me){LM.me=LF.marker(ll,{icon:meIcon(!LM.gps),keyboard:false,zIndexOffset:1000}).bindTooltip('Tu jesteś').addTo(LM.map)}else{LM.me.setLatLng(ll);LM.me.setIcon(meIcon(!LM.gps))}
  if(LM.acc){LM.acc.setLatLng(ll).setRadius(LM.gps?.acc||0)}else if(LM.gps){LM.acc=LF.circle(ll,{radius:LM.gps.acc,color:'#1a73e8',weight:1,opacity:.4,fillColor:'#1a73e8',fillOpacity:.1,interactive:false}).addTo(LM.map)}}
function mapLocate(){const b=$('#zloc');if(LM.gps&&LM.ok){LM.follow=true;b.setAttribute('aria-pressed','true');LM.map.flyTo([me.la,me.lo],Math.max(LM.map.getZoom(),17),{duration:.6});return}
  if(!navigator.geolocation){$('#live').textContent='Ta przeglądarka nie udostępnia lokalizacji. Dotknij mapy, aby ją wskazać.';return}
  b.classList.add('wait');let first=true;
  LM.watch=navigator.geolocation.watchPosition(p=>{b.classList.remove('wait');b.setAttribute('aria-pressed','true');
      LM.gps={acc:Math.round(p.coords.accuracy)};me={la:+p.coords.latitude.toFixed(6),lo:+p.coords.longitude.toFixed(6),src:'GPS'};saveMe();meMarker();
      if(LM.ok&&(first||LM.follow)){LM.follow=true;LM.map.flyTo([me.la,me.lo],first?17:LM.map.getZoom(),{duration:first?.8:.3})}
      if(first){first=false;drawList()}},
    e=>{b.classList.remove('wait');b.setAttribute('aria-pressed','false');$('#live').textContent=e.code===1?'Brak zgody na lokalizację. Zezwól w pasku adresu albo dotknij mapy, aby wskazać miejsce.':'Nie udało się ustalić lokalizacji. Dotknij mapy, aby wskazać miejsce.';$('#maphint').hidden=true},
    {enableHighAccuracy:true,maximumAge:5000,timeout:15000})}
$('#zloc').onclick=()=>LM.ok?mapLocate():$('#live').textContent='Mapa jeszcze się ładuje.';
$('#znear').onclick=async()=>{window.pzNoAsk=1;const _b=$('#znear');_b.disabled=true;let _r=null;try{if(typeof apiNearest==='function'&&me&&me.la)_r=await apiNearest(me)}finally{_b.disabled=false}if(_r){location.hash='prowadz'+_r.id_aed;return}const c=filtered().filter(o=>o.r.status_rekordu==='zweryfikowany').sort((a,b)=>(a.s[0]==='ok'?0:1)-(b.s[0]==='ok'?0:1)||a.d-b.d)[0];if(c)location.hash='prowadz'+c.r.id_aed;else{window.pzNoAsk=0;$('#live').textContent='Brak zweryfikowanego AED w pobliżu.'}};
$('#zfs').onclick=()=>{const f=$('#fig');document.fullscreenElement?document.exitFullscreen():f.requestFullscreen?.()};
document.addEventListener('fullscreenchange',()=>{$('#zfs').setAttribute('aria-pressed',!!document.fullscreenElement);setTimeout(()=>LM.map&&LM.map.invalidateSize(),60)});
{const oc=$('#fCity').onchange;$('#fCity').onchange=e=>{oc(e);if(LM.ok){const c=CITIES.find(x=>x[0]===e.target.value);c?LM.map.setView([c[1],c[2]],14):LM.map.fitBounds(PLB)}}}"""
k=next(i for i,l in enumerate(L) if l.startswith("for(const id of ['#fNow'"))
L.insert(k+1,LMCODE)
textrep("if(h==='mapa'){if(pickFor){","if(h==='mapa'){lmInit();setTimeout(()=>LM.map&&LM.map.invalidateSize(),50);if(pickFor){")
textrep("$('#dlg').showModal()};drawMap();drawList()}","$('#dlg').showModal()};drawMap();drawList();showBuilding(r)}")


textrep("""function locate(){if(!navigator.geolocation){sos.st='ask';return renderSos()}sos.st='locating';renderSos();
  navigator.geolocation.getCurrentPosition(p=>{me={la:p.coords.latitude,lo:p.coords.longitude,src:'GPS'};saveMe();sos.st='found';renderSos()},()=>{sos.st='ask';renderSos()},{enableHighAccuracy:true,timeout:8000,maximumAge:30000})}""",
"""function locate(){if(!navigator.geolocation){sos.st='ask';return renderSos()}sos.st='locating';renderSos();
  const ok=p=>{me={la:p.coords.latitude,lo:p.coords.longitude,src:'GPS'};saveMe();sos.st='found';renderSos()};
  const fail=e=>{sos.denied=e&&e.code===1;sos.st='ask';renderSos()};
  navigator.geolocation.getCurrentPosition(ok,e=>e.code===1?fail(e):navigator.geolocation.getCurrentPosition(ok,fail,{enableHighAccuracy:false,timeout:12000,maximumAge:600000}),{enableHighAccuracy:true,timeout:6000,maximumAge:60000})}""")
textrep("""<a class="big green" style="min-height:150px;font-size:clamp(30px,8vw,44px)" href="${gmSearch('')}" rel="noopener">${T[L].openMap}<span class="sub">${T[L].openMap_s}</span></a>""",
"""<button type="button" data-sos="find" class="big green" style="min-height:150px;width:100%;font-size:clamp(30px,8vw,44px)">${T[L].openMap}</button>""")
textrep("""  if(t.dataset.sos==='again'){""","""  if(t.dataset.sos==='find'){if(sos.denied)location.href=gmSearch('');else locate()}
  if(t.dataset.sos==='again'){""")
textrep('openMap:"Prowadź do AED",openMap_s:"Google Maps wyznaczy trasę od Ciebie",','openMap:"Znajdź najbliższy AED",')
textrep('openMap:"Go to AED",openMap_s:"Google Maps will route you from where you are",','openMap:"Find nearest AED",')


_s='\n'.join(L)
import re as _re
_m=_re.search(r"VIEWS=\[([^\]]*)\]",_s);print('VIEWS',_m.group(0)[:80])
_s=_s.replace(_m.group(0),_m.group(0).replace("VIEWS=[","VIEWS=['prowadz',"),1)
_a=_s.index('const ALLOW=');_e=_s.index('\n',_a);_s=_s[:_a]+_s[_a:_e].replace("['uciskaj',","['prowadz','uciskaj',")+_s[_e:]
_s=_s.replace("publiczny:{name:'Gość',","publiczny:{name:'Gość',",1)
_s=_s.replace("if(h.startsWith('prowadz')){gid=h.slice(8)||null;h='prowadz'}","if(h.startsWith('prowadz')){gid=h.slice(8)||null;h='prowadz'}if(h==='ratunek')h='prowadz';",1)
_s=_s.replace("addEventListener('hashchange',route);","if(location.hash==='#ratunek')history.replaceState(null,'',location.pathname+location.search+'#prowadz');\naddEventListener('hashchange',route);",1)
_s=_s.replace("NAVMAP={","NAVMAP={prowadz:'start',",1)
_s=_s.replace("let lastView='';function route(){let h=location.hash.slice(1);","let lastView='';function route(){let h=location.hash.slice(1);let gid=null;if(h.startsWith('prowadz')){gid=h.slice(8)||null;h='prowadz'}",1)
_s=_s.replace("if(h==='moje')drawMoje()}","if(h==='moje')drawMoje();if(h==='prowadz')gOpen(gid);else gClose()}",1)
_s=_s.replace('<a class="big green" href="${mapsUrl(r)}" rel="noopener">','<a class="big green" href="#prowadz-${r.id_aed}">',1)
_s=_s.replace('<a class="btn okb" href="${mapsUrl(r)}" rel="noopener">','<a class="btn okb" href="#prowadz-${r.id_aed}">',1)
_s=_s.replace("addEventListener('hashchange',route);",open(os.path.join(ROOT,'build','guide.js')).read()+"\naddEventListener('hashchange',route);",1)
_s=_s.replace("if(h.startsWith('prowadz')){gid=h.slice(8)||null;h='prowadz'}","if(h.startsWith('prowadz')){gid=h.slice(8)||null;h='prowadz'}if(h==='ratunek')h='prowadz';",1)
_s=_s.replace("LF.map('lmap',{zoomControl:false,","LF.map('lmap',{preferCanvas:true,zoomControl:false,",1)
_s=_s.replace("LM.layer.clearLayers();\n  for(const r of live(AED)){","LM.layer.clearLayers();const BB=LM.map.getBounds().pad(.25);\n  for(const r of live(AED).filter(r=>BB.contains([r.lat,r.lon])).slice(0,3000)){",1)
_s=_s.replace("LM.layer=LF.layerGroup().addTo(LM.map);","LM.layer=LF.layerGroup().addTo(LM.map);LM.map.on('moveend',()=>{if(AED.length>2500&&LM.ok)drawLeaflet()});",1)
_s=_s.replace("const pts=live(AED).map(r=>{","const pts=live(AED).filter(r=>{const X=px(r.lon),Y=py(r.lat);return X>=vb[0]&&X<=vb[0]+vb[2]&&Y>=vb[1]&&Y<=vb[1]+vb[3]}).slice(0,2500).map(r=>{",1)
_s=_s.replace(".sort((a,b)=>a.pv-b.pv);\n  $('#cov').innerHTML=rows.map(",".sort((a,b)=>a.pv-b.pv);\n  $('#cov').innerHTML=rows.slice(0,60).map(",1)
L=_s.split('\n')
open(os.path.join(ROOT,'build','_app.js'),'w').write('\n'.join(L))
sh=open(os.path.join(ROOT,'web','shell.html')).read()
open(os.path.join(ROOT,'..','aplikacja','index.html'),'w').write(sh.replace('/*APP*/','\n'.join(L)))
print("ok")
