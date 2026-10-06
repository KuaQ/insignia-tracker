/* Progressive enhancement of the existing history dashboard. No API calls or trackers. */
(function(){
 'use strict';
 const M=window.InsigniaMatch, store='insignia.preferences.v1';
 let prefs={budget:65000,preferAutomatic:true,weights:{}};
 try{const v=JSON.parse(localStorage.getItem(store));if(v&&typeof v==='object')prefs={...prefs,...v};}catch{}
 const bands={near:'Do 50 km',regional:'50–150 km',far:'150–300 km',long:'Ponad 300 km',unknown:'Brak lokalizacji'};
 const featureMeta=D.meta.portal_features||{};
 function score(x){return M.fit(x,prefs)}
 function assets(u){return /^\.\/assets\/photos\/[a-f0-9]{24}(?:-thumb)?\.webp$/.test(u||'')?u:null;}
 function previews(x){return (x.saved_previews||[]).filter(a=>a&&Array.isArray(a.photos));}
 function photos(a){return (a?.photos||[]).filter(p=>assets(p.url));}
 function picture(x){return previews(x).flatMap(photos)[0];}
 function sourceLinks(x){
  return (x.copies||[]).map(c=>`<div class="offer-source">${anchor(c.url,c.portal.toUpperCase())}<small>${esc(c.portal_id)}${c.status==='gone'||c.status==='sold'?' · nieaktywna w raporcie':''}</small></div>`).join('')||'<span class="muted">Nie zachowano linku.</span>';
 }
 function distanceBox(x){
  const loc=x.location,km=x.distance_km;
  return `<strong>${loc?.city?esc(loc.city):Number.isFinite(km)?'Punkt z archiwum':'Lokalizacja nieustalona'}</strong>${Number.isFinite(km)?`<div>~${num(Math.round(km))} km</div><span class="distance-tag">${bands[M.band(km)]}</span><small>w linii prostej · nie trasa</small>`:'<small>Nie zgadujemy na podstawie pochodzenia auta.</small>'}${M.route(loc)?`<div>${anchor(M.route(loc),'Sprawdź trasę')}</div>`:''}`;
 }
 function scoreBox(x){const s=score(x);return `<button class="fit-value ${s.candidate?'':'fit-muted'}" data-key="${esc(x.key)}" title="Zobacz skąd biorą się punkty">${s.score}<span>/100</span></button><div class="fit-track"><i style="width:${s.score}%"></i><em style="left:${s.score}%;width:${Math.max(0,s.potential-s.score)}%"></em></div><small>możliwe do ${s.potential} · dane ${s.coverage}%</small>${s.blockers.length?'<small class="fit-alert">'+esc(s.blockers.join(' · '))+'</small>':''}`;}
 function weightsPanel(){return Object.entries({...M.defaults.weights,panorama:0,bose:0,flexride:0,handsfree_tailgate:0,traffic_signs:0,park_assist:0,ventilated_seats:0,massage:0}).map(([k,v])=>`<label class="weight-field">${esc(labels[k]||k)}<input type="number" data-weight="${esc(k)}" min="0" max="25" step="1" value="${Number.isFinite(prefs.weights?.[k])?Math.max(0,Math.min(25,prefs.weights[k])):v}"></label>`).join('');}
 const panel=document.createElement('section');panel.className='panel feature-guide';
 panel.innerHTML=`<div class="panel-head"><h2>Do obejrzenia, do dojechania, do porównania</h2><span>Twoje kryteria · nie ocena stanu technicznego</span></div><p>Linki są bezpośrednio przy ofertach. <b>Zapisane zdjęcia</b> otwierają kopię bez łączenia z portalem. Odległość liczona od punktu miasta Włocławek; rzeczywisty dojazd pod przyciskiem „Sprawdź trasę”.</p><p class="muted" id="featureCoverage"></p><details id="preferences"><summary>Jak liczymy dopasowanie? Ustaw swoje preferencje</summary><p>Domyślnie: <b>wyposażenie 70 pkt, skrzynia 20 pkt, budżet 10 pkt</b>. Najwięcej ważą kamera, grzane fotele i CarPlay. Automat: 20 pkt; dopuszczony manual: 12 pkt. Każda znana cena w budżecie dostaje tyle samo — taniej nie oznacza pewniej.</p><p><b>Brak wzmianki to nie brak dodatku.</b> Pierwsza liczba to punkty z zapisanych informacji; „możliwe do” obejmuje kryteria nieznane. „Dane” oznacza procent wagi kryteriów, o których coś wiemy. Wynik nie ocenia historii szkód ani stanu auta i nie jest prawdopodobieństwem udanego zakupu. Odległość, przebieg i rocznik pozostają oddzielnymi filtrami/parametrami.</p><div class="preference-grid"><label>Budżet dopasowania (zł)<input id="fitBudget" type="number" min="1000" step="1000" value="${Number(prefs.budget)||65000}"></label><label>Skrzynia w punktacji<select id="fitGear"><option value="automatic">Preferuję automat, manual dopuszczony</option><option value="equal">Automat i manual tak samo</option></select></label><button type="button" class="soft-button" id="resetPreferences">Przywróć ustawienia</button></div><details><summary>Zmień wagi wyposażenia</summary><p class="muted">0 = bez punktów. Własne wagi są normalizowane do 100. Zapis tylko w tej przeglądarce, bez konta i bez synchronizacji urządzeń.</p><div class="weights-grid">${weightsPanel()}</div></details></details>`;
 document.querySelector('.filters').before(panel);
 $('#fitGear').value=prefs.preferAutomatic===false?'equal':'automatic';
 $('#featureCoverage').textContent=`W tej wersji: ${featureMeta.copies_with_links??D.listings.reduce((n,x)=>n+(x.copies||[]).filter(c=>c.url).length,0)} zapisanych linków · zdjęcia dla ${featureMeta.vehicles_with_photos??0} aut · odległość dla ${featureMeta.vehicles_with_distance??0} z ${D.listings.length} aut. Pozostałe lokalizacje są nieustalone.`;
 document.querySelector('.filters').insertAdjacentHTML('beforeend',`<div><label for="distanceFilter">Od Włocławka (linia prosta)</label><select id="distanceFilter"><option value="">Wszystkie odległości</option>${Object.entries(bands).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></div><div><label for="fitFilter">Dopasowanie z dostępnych danych</label><select id="fitFilter"><option value="">Wszystkie wyniki</option><option value="50">Co najmniej 50 pkt</option><option value="70">Co najmniej 70 pkt</option><option value="85">Co najmniej 85 pkt</option><option value="candidates">Aktywne, w budżecie, bez opisanych usterek</option></select></div>`);
 $('#sort').insertAdjacentHTML('afterbegin','<option value="fitDesc">Dopasowanie — najwięcej punktów</option><option value="distanceAsc">Odległość od Włocławka</option>');
 $('#sort').value='fitDesc';
 const header=$('#offerRows').closest('table').querySelector('thead tr');
 for(const name of ['Od Włocławka','Dopasowanie']){const th=document.createElement('th');th.textContent=name;header.insertBefore(th,header.lastElementChild);}
 const baseFiltered=filtered,baseTable=table,baseDetail=detail;
 filtered=function(){
  let rows=baseFiltered();const d=$('#distanceFilter').value,f=$('#fitFilter').value,s=$('#sort').value;
  rows=rows.filter(x=>(!d||M.band(x.distance_km)===d)&&(!f||(f==='candidates'?score(x).candidate:score(x).score>=Number(f))));
  if(s==='fitDesc')rows.sort((a,b)=>Number(score(b).candidate)-Number(score(a).candidate)||score(b).score-score(a).score||score(b).coverage-score(a).coverage||a.key.localeCompare(b.key));
  if(s==='distanceAsc')rows.sort((a,b)=>(a.distance_km??Infinity)-(b.distance_km??Infinity));
  return rows;
 };
 table=function(rows){
  baseTable(rows);
  if(!rows.length){$('#offerRows td').colSpan=10;return;}
  [...$('#offerRows').children].forEach((tr,i)=>{
   const x=rows[i],p=picture(x);tr.children[4].innerHTML=sourceLinks(x);
   if(p)tr.children[0].insertAdjacentHTML('afterbegin',`<button class="thumbnail-button" data-gallery="${esc(x.key)}" aria-label="Zapisane zdjęcia ${esc(x.key)}"><img alt="Zdjęcie z zapisanej oferty" src="${esc(assets(p.thumbnail)||assets(p.url))}" width="116" height="78" loading="lazy"></button>`);
   const dist=document.createElement('td');dist.className='distance-cell';dist.innerHTML=distanceBox(x);tr.insertBefore(dist,tr.lastElementChild);
   const fitCell=document.createElement('td');fitCell.className='fit-cell';fitCell.innerHTML=scoreBox(x);tr.insertBefore(fitCell,tr.lastElementChild);
   const n=previews(x).reduce((v,a)=>v+photos(a).length,0);
   tr.lastElementChild.insertAdjacentHTML('beforeend',previews(x).length?`<button class="archive-button" data-gallery="${esc(x.key)}">${n?'Zdjęcia i kopia ('+n+')':'Zapisana kopia'}</button>`:'<small class="muted">Brak zachowanej kopii</small>');
  });
 };
 function breakdown(x){const s=score(x);return `<section class="feature-detail"><div class="feature-detail-grid"><div><h3>Dopasowanie z zapisanych danych</h3>${scoreBox(x)}<p class="muted">Kliknij poniżej, aby zobaczyć każde kryterium. Wynik nie zastępuje oględzin.</p></div><div><h3>Dojazd z Włocławka</h3>${distanceBox(x)}${x.location?`<p class="muted">${esc(x.location.precision||'Lokalizacja z zapisanych danych')}. Dane lokalizacji: ${esc(x.location.observed_at||'data nieustalona')}.</p>`:''}${x.location_note?`<p class="warning">${esc(x.location_note)}</p>`:''}</div></div><details><summary>Skąd ${s.score} punktów? Pełne wyliczenie</summary><div class="table-wrap"><table><thead><tr><th>Kryterium</th><th>Dane</th><th>Punkty surowe / waga</th></tr></thead><tbody>${s.parts.map(p=>`<tr><td>${esc(p.key==='budget'?'Cena w budżecie':p.key==='gearbox'?'Skrzynia':labels[p.key]||p.key)}</td><td>${!p.known?'Nie ustalono':p.key==='budget'?money(p.value):p.key==='gearbox'?gears[p.value]:p.value?'Zapisano obecność':'Zapisano brak'}</td><td>${p.known?p.earned:'0–'+p.max} / ${p.max}</td></tr>`).join('')}</tbody></table></div><p class="muted">${s.earned} z ${s.total} wagowych punktów → ${s.score}/100. Niewiadome: ${s.unknown} punktów wagi. Deklaracje nie są niezależną weryfikacją.</p></details></section>`;}
 detail=function(x){
  baseDetail(x);if(!x)return;
  $('#detail').insertAdjacentHTML('afterbegin',`<div class="quick-source-links">${sourceLinks(x)}${previews(x).length?`<button class="archive-button" data-gallery="${esc(x.key)}">Otwórz zapisaną kopię i zdjęcia</button>`:''}</div>`);
  $('#detail').insertAdjacentHTML('beforeend',breakdown(x));
 };
 const dialog=document.createElement('dialog');dialog.id='archiveDialog';dialog.innerHTML='<button class="close" id="closeArchive" aria-label="Zamknij archiwum">×</button><div id="archiveContent"></div>';document.body.append(dialog);
 let archiveCar=null,archiveIndex=0,imageIndex=0;
 function renderArchive(){
  const x=archiveCar,list=previews(x),a=list[archiveIndex],gallery=photos(a);if(!a)return;
  imageIndex=Math.max(0,Math.min(imageIndex,gallery.length-1));
  const image=gallery[imageIndex];
  $('#archiveContent').innerHTML=`<div class="eyebrow">ZAPISANA KOPIA · ${esc(x.key)}</div><h2>${esc(x.title)}</h2><p class="warning">${esc(a.note||'Kopia częściowa. To nie jest bieżący odczyt.')}</p><div class="archive-toolbar"><label>Wersja archiwum <select id="archiveVersion">${list.map((v,i)=>`<option value="${i}" ${i===archiveIndex?'selected':''}>${esc(v.at)} · ${esc(v.portal)} · ${photos(v).length} zdjęć</option>`).join('')}</select></label>${anchor(a.source_url,'Oryginał')}${anchor(a.files_url,'Pliki źródłowe na GitHub')}</div>${image?`<figure class="archive-figure"><img id="archivePhoto" src="${esc(image.url)}" alt="Zapisane zdjęcie ${imageIndex+1} z ${gallery.length}" width="1440" height="1080"><figcaption><button id="previousPhoto" ${imageIndex===0?'disabled':''}>← Poprzednie</button><span>${imageIndex+1} / ${gallery.length}</span><button id="nextPhoto" ${imageIndex>=gallery.length-1?'disabled':''}>Następne →</button></figcaption></figure><div class="photo-thumbnails">${gallery.map((p,i)=>`<button data-photo="${i}" class="${i===imageIndex?'selected':''}" aria-label="Zdjęcie ${i+1}"><img src="${esc(assets(p.thumbnail)||assets(p.url))}" loading="lazy" alt="Miniatura ${i+1}" width="92" height="62"></button>`).join('')}</div>`:'<p class="empty">Nie ma bezpiecznie rozpoznanych zdjęć tej oferty w zapisanych plikach.</p>'}<h3>${a.description?'Opis odzyskany z zapisanej strony':'Streszczenie z raportów — nie pełny tekst ogłoszenia'}</h3><p class="archive-description">${esc(a.description||x.description||'Brak zachowanej treści.')}</p><p class="muted">Nie ładujemy zdjęć z serwera ogłoszeniowego. Nie wykonujemy skryptów pobranych z portalu. Parametry i historia auta pozostają w „Opis i historia”.</p>`;
  $('#archiveVersion').onchange=e=>{archiveIndex=Number(e.target.value);imageIndex=0;renderArchive();};
  const prev=$('#previousPhoto'),next=$('#nextPhoto');if(prev)prev.onclick=()=>{imageIndex--;renderArchive()};if(next)next.onclick=()=>{imageIndex++;renderArchive()};
 }
 document.addEventListener('click',e=>{const t=e.target.closest('[data-gallery]');if(t){archiveCar=byKey.get(t.dataset.gallery);archiveIndex=previews(archiveCar).length-1;imageIndex=0;renderArchive();if(!dialog.open)dialog.showModal();}const p=e.target.closest('[data-photo]');if(p){imageIndex=Number(p.dataset.photo);renderArchive();}});
 $('#closeArchive').onclick=()=>dialog.close();
 dialog.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'&&$('#previousPhoto')&&!$('#previousPhoto').disabled){e.preventDefault();$('#previousPhoto').click();}if(e.key==='ArrowRight'&&$('#nextPhoto')&&!$('#nextPhoto').disabled){e.preventDefault();$('#nextPhoto').click();}});
 function save(){try{localStorage.setItem(store,JSON.stringify(prefs));}catch{}refresh();}
 $('#fitBudget').addEventListener('change',e=>{const n=Number(e.target.value);if(n>0){prefs.budget=n;save();}});
 $('#fitGear').addEventListener('change',e=>{prefs.preferAutomatic=e.target.value==='automatic';save();});
 panel.addEventListener('change',e=>{if(e.target.dataset.weight){prefs.weights={...prefs.weights,[e.target.dataset.weight]:Math.max(0,Math.min(25,Number(e.target.value)||0))};save();}});
 $('#resetPreferences').onclick=()=>{prefs={budget:65000,preferAutomatic:true,weights:{}};$('#fitBudget').value=65000;$('#fitGear').value='automatic';panel.querySelectorAll('[data-weight]').forEach(i=>i.value=M.defaults.weights[i.dataset.weight]||0);save();};
 ['distanceFilter','fitFilter'].forEach(id=>$('#'+id).addEventListener('input',refresh));
 refresh();
})();
