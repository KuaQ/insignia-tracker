'use strict';
const D=window.INSIGNIA_DATA||{meta:{},listings:[],events:[]};
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=n=>Number.isFinite(n)?new Intl.NumberFormat('pl-PL').format(n):'—';
const money=n=>Number.isFinite(n)?num(n)+' zł':'—';
const median=a=>{a=a.filter(Number.isFinite).sort((x,y)=>x-y);return a.length?(a[Math.floor(a.length/2)]+a[Math.floor((a.length-1)/2)])/2:null};
const hasDefects=x=>x.problematic===true||(x.defects||[]).length>0;
const statRow=x=>x.status==='active'&&!hasDefects(x);
const gears={automatic:'Automat',manual:'Manual'};
const states={active:'Aktywne w raporcie',sold:'Sprzedane wg użytkownika',gone:'Zniknięte — nie sprzedaż',unverified:'Niezweryfikowane'};
const kinds={first_seen:'Pierwsza zapisana obserwacja',price_down:'Obniżka ceny',price_up:'Podwyżka ceny',portal_price_down:'Zmiana ceny kopii',data_correction:'Korekta danych',mileage_change:'Zmiana przebiegu',sold:'Sprzedaż potwierdzona przez użytkownika',gone:'Ogłoszenie zniknęło',portal_copy_gone:'Zniknęła kopia portalowa'};
const labels={agr:'AGR',heated_seats:'Grzane fotele',heated_rear_seats:'Grzana kanapa',heated_steering:'Grzana kierownica',heated_windshield:'Grzana szyba',rear_camera:'Kamera cofania',camera_360:'Kamera 360°',blind_spot:'Martwe pole',rcta:'RCTA',acc:'ACC',intellilux:'IntelliLux / Matrix',adaptive_led:'Adaptacyjne LED',hud:'HUD',dic8:'DIC 8″',carplay:'CarPlay',android_auto:'Android Auto',electric_tailgate:'Elektryczna klapa',handsfree_tailgate:'Klapa nogą',keyless:'Keyless',traffic_signs:'Znaki',park_assist:'Asystent parkowania',panorama:'Panorama / szyberdach',bose:'BOSE',flexride:'FlexRide',massage:'Masaż',ventilated_seats:'Wentylacja foteli',lane_assist:'Asystent pasa',collision_warning:'Ostrzeganie o kolizji',pedestrian_detection:'Wykrywanie pieszych',aeb:'Hamowanie awaryjne',towbar:'Hak'};
const eq=x=>Object.entries(x.equipment||{}).filter(([,v])=>v===true).map(([k])=>labels[k]||k);
const byKey=new Map(D.listings.map(x=>[x.key,x]));
function safeUrl(u){try{const v=new URL(u);return v.protocol==='https:'?v.href:null}catch{return null}}
function anchor(u,t){const href=safeUrl(u);return href?`<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(t)} ↗</a>`:esc(t)+' <span class="muted">· pełny link niezapisany</span>'}
function filtered(){
 const q=$('#search').value.toLocaleLowerCase('pl').trim(),st=$('#statusFilter').value,p=$('#portalFilter').value,g=$('#gearboxFilter').value,m=Number($('#priceMax').value)||Infinity;
 const a=D.listings.filter(x=>{
  const hay=JSON.stringify(x).toLocaleLowerCase('pl')+' '+eq(x).join(' ').toLocaleLowerCase('pl');
  return (!q||hay.includes(q))&&(!st||(st==='defects'?hasDefects(x):x.status===st))&&(!p||(x.copies||[]).some(c=>c.portal===p))&&(!g||(g==='unknown'?!x.gearbox:x.gearbox===g))&&(x.price_pln==null||x.price_pln<=m);
 });
 const sort=$('#sort').value;
 const cmp=(x,y,field,dir=1)=>x[field]==null?y[field]==null?0:1:y[field]==null?-1:dir*(x[field]-y[field]);
 a.sort((x,y)=>sort==='priceAsc'?cmp(x,y,'price_pln'):sort==='priceDesc'?cmp(x,y,'price_pln',-1):sort==='mileageAsc'?cmp(x,y,'mileage_km'):sort==='yearDesc'?cmp(x,y,'year',-1):String(y.first_seen||'').localeCompare(String(x.first_seen||'')));
 return a;
}
function kpis(rows){
 const sample=rows.filter(statRow),active=rows.filter(x=>x.status==='active');
 const cards=[['Samochody w widoku',rows.length,`Pełna baza: ${D.listings.length}`],['Aktywne wg raportów',active.length,'Nie oznacza potwierdzenia dostępności dziś'],['Mediana ceny',money(median(sample.map(x=>x.price_pln))),`Próba bez opisanych usterek: ${sample.length} aut`],['Mediana przebiegu',num(median(sample.map(x=>x.mileage_km)))+' km','Ta sama próba'],['Sprzedane / zniknięte',`${rows.filter(x=>x.status==='sold').length} / ${rows.filter(x=>x.status==='gone').length}`,'Dwa różne statusy']];
 $('#kpis').innerHTML=cards.map(([a,b,c])=>`<div class="kpi"><div class="label">${esc(a)}</div><div class="value">${esc(b)}</div><div class="note">${esc(c)}</div></div>`).join('');
 $('#scope').textContent=`Wykresy i mediany: ${sample.length} aut z wybranych filtrów, aktywnych według ostatnich raportów, bez opisanych uszkodzeń/usterek. Nie są to auta sprawdzone technicznie.`;
}
function table(rows){
 $('#resultCount').textContent=`${rows.length} z ${D.listings.length} samochodów`;
 $('#offerRows').innerHTML=rows.length?rows.map(x=>{
 const equipment=eq(x),portals=[...new Set((x.copies||[]).map(c=>c.portal))];
 return `<tr><td><div class="car-title">${esc(x.title)}</div><div class="sub">${esc(x.key)}</div><div class="sub">W trackerze od ${esc(x.first_seen||'daty nieustalonej')}</div></td><td class="money">${money(x.price_pln)}</td><td class="nowrap">${num(x.mileage_km)} km</td><td>${gears[x.gearbox]||'Do potwierdzenia'}</td><td>${portals.map(esc).join('<br>')}</td><td><span class="badge ${esc(x.status)}">${esc(states[x.status]||x.status)}</span>${hasDefects(x)?'<span class="badge defects">Opisane usterki</span>':''}<div class="sub">Raporty: ${esc((x.last_reported_at||'').slice(0,10))}</div></td><td>${equipment.slice(0,4).map(l=>`<span class="badge">${esc(l)}</span>`).join('')}${equipment.length>4?`<span class="badge">+${equipment.length-4}</span>`:''}${!equipment.length?'<span class="muted">Brak zapisanej listy</span>':''}</td><td><button class="link" data-key="${esc(x.key)}">Opis i historia →</button></td></tr>`;
 }).join(''):'<tr><td colspan="8" class="empty">Brak samochodów dla wybranych filtrów.</td></tr>';
}
function scatter(rows){
 const a=rows.filter(statRow).filter(x=>Number.isFinite(x.price_pln)&&Number.isFinite(x.mileage_km)),svg=$('#scatter');
 if(!a.length){svg.innerHTML='<text x="24" y="70" fill="#667085">Brak danych w tej próbie.</text>';return}
 const w=760,h=360,l=65,r=22,t=25,b=57,maxX=Math.max(10000,...a.map(x=>x.mileage_km))*1.05,minY=Math.floor(Math.min(...a.map(x=>x.price_pln))/5000)*5000,maxY=Math.max(minY+5000,Math.ceil(Math.max(...a.map(x=>x.price_pln))/5000)*5000);
 const X=v=>l+v/maxX*(w-l-r),Y=v=>h-b-(v-minY)/(maxY-minY)*(h-t-b);
 let out='';for(let i=0;i<=4;i++){const v=minY+(maxY-minY)*i/4,y=Y(v);out+=`<line x1="${l}" y1="${y}" x2="${w-r}" y2="${y}" stroke="#e7eaf2"/><text x="${l-9}" y="${y+4}" text-anchor="end" font-size="10" fill="#667085">${Math.round(v/1000)} tys.</text>`}
 for(let i=0;i<=4;i++){const v=maxX*i/4;out+=`<text x="${X(v)}" y="${h-32}" text-anchor="middle" font-size="10" fill="#667085">${Math.round(v/1000)} tys.</text>`}
 out+=`<text x="${w-r}" y="${h-4}" text-anchor="end" font-size="11" fill="#667085">Przebieg (km)</text>`;
 a.forEach(x=>{const title=`${x.title} · ${money(x.price_pln)} · ${num(x.mileage_km)} km`;out+=`<circle data-key="${esc(x.key)}" tabindex="0" role="button" aria-label="${esc(title)}" cx="${X(x.mileage_km)}" cy="${Y(x.price_pln)}" r="5.5" fill="#7056d9" opacity=".85"><title>${esc(title)}</title></circle>`});svg.innerHTML=out;
}
function bars(rows){
 const sample=rows.filter(statRow),years={};sample.forEach(x=>{if(x.year)years[x.year]=(years[x.year]||0)+1});
 const counts=Object.entries(years).sort((a,b)=>a[0]-b[0]);
 counts.push(['Automat',sample.filter(x=>x.gearbox==='automatic').length],['Manual',sample.filter(x=>x.gearbox==='manual').length],['Do potwierdzenia',sample.filter(x=>!x.gearbox).length]);
 const max=Math.max(1,...counts.map(x=>x[1]));
 $('#bars').innerHTML=counts.map(([l,n])=>`<div class="bar-row"><span>${esc(l)}</span><div class="bar-track"><div class="bar-fill" style="width:${n/max*100}%"></div></div><b>${n}</b></div>`).join('');
}
function eventText(e){
 if(Number.isFinite(e.old_price_pln))return money(e.old_price_pln)+' → '+money(e.price_pln);
 if(e.type==='mileage_change')return num(e.old_mileage_km)+' → '+num(e.mileage_km)+' km';
 return e.note||'';
}
function historyTable(events){return events.length?`<div class="table-wrap"><table class="historytable"><thead><tr><th>Data raportu</th><th>Zdarzenie</th><th>Wartość / wyjaśnienie</th></tr></thead><tbody>${events.map(e=>`<tr><td class="nowrap">${esc((e.at||'').slice(0,10))}</td><td>${esc(kinds[e.type]||e.type)}</td><td>${esc(eventText(e))}${e.note&&e.old_price_pln?'<p class="muted">'+esc(e.note)+'</p>':''}</td></tr>`).join('')}</tbody></table></div>`:'<p class="muted">Brak zapisanych zmian. To nie dowodzi stałości ceny przed rozpoczęciem obserwacji.</p>'}
function priceChart(x){
 const changes=(x.history||[]).filter(e=>['price_down','price_up','portal_price_down'].includes(e.type)&&Number.isFinite(e.old_price_pln));
 if(!changes.length)return '<p class="muted">Brak potwierdzonej sekwencji zmian ceny w zapisanych raportach.</p>';
 const values=[changes[0].old_price_pln,...changes.map(e=>e.price_pln)],dates=['Przed zmianą',...changes.map(e=>e.at.slice(5,10))],W=760,H=205,min=Math.min(...values)-600,max=Math.max(...values)+600,X=i=>75+i/(values.length-1)*610,Y=v=>H-38-(v-min)/(max-min)*(H-78);
 const poly=values.map((v,i)=>`${X(i)},${Y(v)}`).join(' ');
 return `<svg class="price-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Zapisane zmiany ceny"><polyline points="${poly}" fill="none" stroke="#6046d5" stroke-width="2.5"/>${values.map((v,i)=>`<circle cx="${X(i)}" cy="${Y(v)}" r="4.5" fill="#6046d5"/><text x="${X(i)}" y="${Y(v)-13}" text-anchor="middle" font-size="12" fill="#202433">${money(v)}</text><text x="${X(i)}" y="${H-8}" text-anchor="middle" font-size="11" fill="#667085">${esc(dates[i])}</text>`).join('')}</svg><p class="muted">Sekwencja zapisanych zmian, nie ciągły wykres dzienny. Punkt „Przed zmianą” nie ma przypisanej fikcyjnej daty. Korekty błędnych odczytów pominięto.</p>`;
}
function detail(x){
 if(!x)return;
 const boxes=[['Cena ofertowa',money(x.price_pln)],['Przebieg',num(x.mileage_km)+' km'],['Skrzynia',gears[x.gearbox]||'Do potwierdzenia'],['Pochodzenie (deklaracja)',x.origin||'Nie zapisano'],['Pierwsza obserwacja',x.first_seen||'Nieustalona'],['Okres obserwacji',Number.isFinite(x.days_observed)?x.days_observed+' dni · nie czas sprzedaży':'Nieustalony'],['VIN / zapis surowy',x.vin||x.vin_raw||'Nie zapisano'],['Status',states[x.status]||x.status],['Data raportów',x.last_reported_at||'—']];
 const sources=(x.copies||[]).map(c=>`<p>${anchor(c.url,c.portal.toUpperCase()+' · '+c.portal_id)} · <b>${money(c.price_pln)}</b> · ${esc(states[c.status]||c.status)}</p>`).join('');
 const absent=Object.entries(x.equipment||{}).filter(([,v])=>v===false).map(([k])=>labels[k]||k);
 $('#detail').innerHTML=`<div class="eyebrow">KARTA SAMOCHODU · ${esc(x.key)}</div><h2 class="detail-heading">${esc(x.title)}</h2><p class="source-label">Źródło: zapisane raporty i ustalenia. Bez nowej weryfikacji oferty.</p><div class="detail-grid">${boxes.map(([l,v])=>`<div class="detail-box"><b>${esc(l)}</b>${esc(v)}</div>`).join('')}</div>${x.status_evidence?'<p class="warning">'+esc(x.status_evidence)+'</p>':''}${x.vin_quality?'<p class="warning">VIN: '+esc(x.vin_quality)+'. Nie używamy go jako pewnego klucza duplikatu.</p>':''}<h3>Opis — streszczenie zapisanych informacji</h3><p class="description">${esc(x.description||'Brak zapisanego opisu.')}</p>${hasDefects(x)?'<div class="warning"><b>Opisane usterki / zastrzeżenia</b><p>'+esc((x.defects||[]).join(' · '))+'</p></div>':''}<h3>Wyposażenie zapisane w raportach</h3>${eq(x).length?eq(x).map(l=>`<span class="badge">${esc(l)}</span>`).join(''):'<p class="muted">Brak zapisanej szczegółowej listy.</p>'}${absent.length?'<p class="muted">Zgłoszony brak: '+esc(absent.join(', '))+'.</p>':''}<p class="muted">Pozostałe dodatki: brak informacji, a nie potwierdzony brak wyposażenia.</p>${(x.seller_claims||[]).length?'<h3>Deklaracje sprzedawcy</h3><p class="description">'+esc(x.seller_claims.join(' · '))+'</p>':''}<h3>Ogłoszenia tego samochodu</h3><div class="detailsources">${sources}</div><p class="muted">Powiązania z wcześniejszych raportów${x.dedup_confidence?' · pewność: '+esc(x.dedup_confidence):''}. Ceny poszczególnych kopii mogą się różnić. Brak pełnego URL nie jest zastępowany wymyślonym linkiem.</p><h3>Zapisane zmiany ceny</h3>${priceChart(x)}<h3>Historia obserwacji</h3>${historyTable(x.history||[])}<h3>Zachowane pliki</h3>${(x.archives||[]).length?x.archives.map(a=>'<p>'+anchor(a.url,a.label)+' <span class="muted">'+esc(a.at)+'</span></p>').join(''):'<p class="muted">Brak powiązanego archiwum. Nie odtwarzano zdjęć ani pełnej treści usuniętej oferty z pamięci.</p>'}`;
 $('#detailDialog').showModal();
}
function history(rows){
 const keys=new Set(rows.map(r=>r.key)),ev=[...D.events].filter(e=>keys.has(e.key)).sort((a,b)=>String(b.at).localeCompare(String(a.at)));
 $('#events').innerHTML=ev.length?ev.map(e=>`<div class="event"><button class="link" data-key="${esc(e.key)}">${esc(kinds[e.type]||e.type)} · ${esc(e.key)}</button><p>${esc(e.at)}${e.portal?' · '+esc(e.portal):''}${eventText(e)?' · '+esc(eventText(e)):''}</p></div>`).join(''):'<p class="empty">Brak zdarzeń dla wybranych filtrów.</p>';
 const gone=rows.filter(r=>['sold','gone'].includes(r.status));
 $('#goneList').innerHTML=gone.length?gone.map(x=>`<div class="compact-item"><button class="link" data-key="${esc(x.key)}">${esc(x.title)} · ${money(x.price_pln)}</button><p class="muted">${esc(states[x.status])} · ${esc(x.status_date||'')}<br>${esc(x.status_evidence||'')}</p></div>`).join(''):'<p class="muted">Brak w wybranych filtrach.</p>';
 $('#portalSummary').innerHTML=['otomoto','olx','autoplac'].map(p=>`<p class="muted"><b>${p.toUpperCase()}</b> · ${rows.filter(x=>(x.copies||[]).some(c=>c.portal===p)).length} samochodów z rozpoznanym wpisem</p>`).join('');
}
function refresh(){const rows=filtered();kpis(rows);table(rows);scatter(rows);bars(rows);history(rows)}
document.addEventListener('click',e=>{const t=e.target.closest('[data-key]');if(t)detail(byKey.get(t.dataset.key))});
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('circle[data-key]')){e.preventDefault();detail(byKey.get(e.target.dataset.key))}});
['search','statusFilter','portalFilter','gearboxFilter','priceMax','sort'].forEach(id=>$('#'+id).addEventListener('input',refresh));
$('#closeDialog').onclick=()=>$('#detailDialog').close();
$('#subtitle').textContent=`${D.listings.length} samochodów · dane z raportów do ${D.meta.as_of||'daty nieustalonej'} · nie tylko sześć przykładowych ofert`;
$('#provenance').textContent=D.meta.note||'Brak informacji o pochodzeniu danych.';
$('#buildStamp').textContent=' Zbudowano panel: '+(D.meta.generated_at||'nieustalono')+'. Data budowy nie jest datą odczytu ogłoszeń.';
refresh();
