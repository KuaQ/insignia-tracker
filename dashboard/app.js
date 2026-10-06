const D = window.INSIGNIA_DATA || {listings:[],events:[],meta:{}};
const $ = s => document.querySelector(s);
const fmtPLN = n => Number.isFinite(n) ? new Intl.NumberFormat('pl-PL',{style:'currency',currency:'PLN',maximumFractionDigits:0}).format(n) : '—';
const fmtNum = n => Number.isFinite(n) ? new Intl.NumberFormat('pl-PL').format(n) : '—';
const parseDate = s => s ? new Date(s) : null;
const esc = s => String(s ?? '').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
const active = x => x.status === 'active' && !x.problematic;
const median = arr => { const a=arr.filter(Number.isFinite).sort((x,y)=>x-y); if(!a.length)return null; const m=Math.floor(a.length/2); return a.length%2?a[m]:(a[m-1]+a[m])/2; };

function equipmentLabels(e={}){
 const labels={agr:'AGR',heated_seats:'grzane fotele',heated_steering:'grzana kierownica',heated_windshield:'grzana szyba',rear_camera:'kamera',camera_360:'360°',blind_spot:'martwe pole',rcta:'RCTA',acc:'ACC',intellilux:'IntelliLux',hud:'HUD',dic8:'DIC 8"',carplay:'CarPlay',android_auto:'Android Auto',electric_tailgate:'el. klapa',handsfree_tailgate:'klapa nogą',keyless:'keyless',traffic_signs:'znaki',park_assist:'park assist',panorama:'panorama',bose:'BOSE',flexride:'FlexRide'};
 return Object.entries(e).filter(([,v])=>v===true).map(([k])=>labels[k]||k);
}
function statusOf(x){ if(x.problematic)return 'problematic'; return x.status||'active'; }
function renderKpis(){
 const a=D.listings.filter(active);
 const k=[
  ['Aktywne',a.length,'bez zadeklarowanej poważnej usterki'],
  ['Mediana ceny',fmtPLN(median(a.map(x=>x.price_pln))),'aktywny zbiór'],
  ['Mediana przebiegu',median(a.map(x=>x.mileage_km)) ? fmtNum(median(a.map(x=>x.mileage_km)))+' km':'—','aktywny zbiór'],
  ['Automaty',a.filter(x=>x.gearbox==='automatic').length,'aktywny zbiór'],
  ['Zniknięte / sprzedane',D.listings.filter(x=>['gone','sold'].includes(statusOf(x))).length,'historia trackera']
 ];
 $('#kpis').innerHTML=k.map(([l,v,n])=>'<div class="kpi"><div class="label">'+l+'</div><div class="value">'+v+'</div><div class="note">'+n+'</div></div>').join('');
}
function filtered(){
 const q=$('#search').value.toLowerCase().trim(), st=$('#statusFilter').value, gb=$('#gearboxFilter').value, pm=Number($('#priceMax').value)||Infinity;
 let a=D.listings.filter(x=>{
  const hay=JSON.stringify(x).toLowerCase();
  return (!q||hay.includes(q)) && (!st||statusOf(x)===st) && (!gb||x.gearbox===gb) && (!x.price_pln||x.price_pln<=pm);
 });
 const s=$('#sort').value;
 const n=v=>Number.isFinite(v)?v:9e15;
 a.sort((x,y)=> s==='priceDesc'?n(y.price_pln)-n(x.price_pln):s==='mileageAsc'?n(x.mileage_km)-n(y.mileage_km):s==='yearDesc'?n(y.year)-n(x.year):s==='lastSeenDesc'?((parseDate(y.last_seen)||0)-(parseDate(x.last_seen)||0)):n(x.price_pln)-n(y.price_pln));
 return a;
}
function renderTable(){
 const rows=filtered(); $('#resultCount').textContent=rows.length+' wyników';
 $('#offerRows').innerHTML=rows.length?rows.map((x,i)=>{
  const eq=equipmentLabels(x.equipment).slice(0,5);
  const st=statusOf(x);
  return '<tr id="row-'+esc(x.key||x.portal_id||i)+'"><td><div class="car-title">'+esc(x.title||((x.year||'')+' Opel Insignia'))+'</div><div class="sub">'+esc(x.vin||x.portal_id||'')+'</div></td><td class="money">'+fmtPLN(x.price_pln)+'</td><td>'+ (x.mileage_km?fmtNum(x.mileage_km)+' km':'—') +'</td><td>'+esc(x.year||'—')+'</td><td>'+esc(x.gearbox==='automatic'?'automat':x.gearbox==='manual'?'manual':'—')+'</td><td>'+esc(x.portal||'—')+'</td><td><span class="badge '+st+'">'+esc(st)+'</span></td><td>'+eq.map(e=>'<span class="badge">'+esc(e)+'</span>').join('')+'</td><td><button class="link" data-detail="'+i+'">Szczegóły</button></td></tr>';
 }).join(''):'<tr><td colspan="9" class="empty">Brak ofert dla wybranych filtrów.</td></tr>';
 document.querySelectorAll('[data-detail]').forEach((b,idx)=>b.onclick=()=>showDetail(rows[Number(b.dataset.detail)]));
}
function showDetail(x){
 const eq=equipmentLabels(x.equipment);
 const archive=x.archive_url?'<p><a href="'+esc(x.archive_url)+'" target="_blank">Otwórz zachowaną kopię</a></p>':'';
 const orig=x.url?'<p><a href="'+esc(x.url)+'" target="_blank">Otwórz oryginalne ogłoszenie</a></p>':'';
 $('#detail').innerHTML='<h2>'+esc(x.title||'Opel Insignia')+'</h2>'+orig+archive+'<div class="detail-grid">'+[
 ['Cena',fmtPLN(x.price_pln)],['Przebieg',x.mileage_km?fmtNum(x.mileage_km)+' km':'—'],['Rok',x.year||'—'],['Skrzynia',x.gearbox||'—'],['Portal',x.portal||'—'],['ID',x.portal_id||'—'],['VIN',x.vin||'—'],['First seen',x.first_seen||'—'],['Last seen',x.last_seen||'—']
 ].map(([a,b])=>'<div class="detail-box"><b>'+a+'</b>'+esc(b)+'</div>').join('')+'</div><div class="equip"><h3>Wyposażenie</h3>'+eq.map(e=>'<span class="badge">'+esc(e)+'</span>').join('')+'</div>'+(x.seller_claims?.length?'<div class="equip"><h3>Deklaracje sprzedawcy</h3><p>'+esc(x.seller_claims.join(' · '))+'</p></div>':'');
 $('#detailDialog').showModal();
}
function renderScatter(){
 const svg=$('#scatter'), pts=D.listings.filter(active).filter(x=>Number.isFinite(x.price_pln)&&Number.isFinite(x.mileage_km));
 if(!pts.length){svg.innerHTML='<text x="30" y="50">Brak danych</text>';return}
 const W=760,H=330,p={l:62,r:24,t:22,b:44}, xmax=Math.max(...pts.map(x=>x.mileage_km))*1.06, ymin=Math.floor(Math.min(...pts.map(x=>x.price_pln))/5000)*5000, ymax=Math.ceil(Math.max(...pts.map(x=>x.price_pln))/5000)*5000;
 const X=v=>p.l+(v/xmax)*(W-p.l-p.r), Y=v=>H-p.b-((v-ymin)/(ymax-ymin||1))*(H-p.t-p.b);
 let out='';
 for(let i=0;i<5;i++){const yv=ymin+(ymax-ymin)*i/4,y=Y(yv);out+=`<line x1="${p.l}" y1="${y}" x2="${W-p.r}" y2="${y}" stroke="#ececf0"/><text x="${p.l-8}" y="${y+4}" text-anchor="end" font-size="11" fill="#7a7f87">${Math.round(yv/1000)}k</text>`;}
 for(let i=0;i<5;i++){const xv=xmax*i/4,x=X(xv);out+=`<text x="${x}" y="${H-15}" text-anchor="middle" font-size="11" fill="#7a7f87">${Math.round(xv/1000)}k</text>`;}
 pts.forEach((x,i)=>{out+=`<circle cx="${X(x.mileage_km)}" cy="${Y(x.price_pln)}" r="5.5" fill="#5d3fd3" opacity=".75"><title>${esc((x.year||'')+' '+fmtPLN(x.price_pln)+' · '+fmtNum(x.mileage_km)+' km')}</title></circle>`;});
 svg.innerHTML=out;
}
function renderBars(){
 const a=D.listings.filter(active), years={}; a.forEach(x=>{if(x.year)years[x.year]=(years[x.year]||0)+1});
 const data=Object.entries(years).sort((a,b)=>a[0]-b[0]).concat([['Automat',a.filter(x=>x.gearbox==='automatic').length],['Manual',a.filter(x=>x.gearbox==='manual').length]]);
 const max=Math.max(1,...data.map(x=>x[1]));
 $('#bars').innerHTML=data.map(([l,v])=>'<div class="bar-row"><span>'+esc(l)+'</span><div class="bar-track"><div class="bar-fill" style="width:'+(v/max*100)+'%"></div></div><b>'+v+'</b></div>').join('');
}
function renderEvents(){
 const ev=[...(D.events||[])].slice(-30).reverse();
 $('#events').innerHTML=ev.length?ev.map(e=>'<div class="event"><strong>'+esc(e.type||'zmiana')+' · '+esc(e.portal||'')+' '+esc(e.portal_id||'')+'</strong><p>'+esc(e.at||'')+(e.price_pln?' · '+fmtPLN(e.price_pln):'')+(e.reason?' · '+esc(e.reason):'')+'</p></div>').join(''):'<div class="empty">Brak zapisanej historii zdarzeń.</div>';
 const gone=D.listings.filter(x=>['gone','sold'].includes(statusOf(x)));
 $('#goneList').innerHTML=gone.length?gone.map(x=>'<div class="compact-item"><strong>'+esc(x.title||x.portal_id||'Auto')+'</strong><p>'+esc(statusOf(x))+' · '+fmtPLN(x.price_pln)+'</p></div>').join(''):'<div class="empty">Brak znikniętych ofert w danych panelu.</div>';
}
function refresh(){renderTable();renderScatter();renderBars()}
['search','statusFilter','gearboxFilter','priceMax','sort'].forEach(id=>$('#'+id).addEventListener('input',refresh));
$('#closeDialog').onclick=()=>$('#detailDialog').close();
$('#subtitle').textContent='Stan danych: '+(D.meta?.generated_at||'brak daty')+' · '+(D.meta?.note||'');
$('#dataStatus').textContent=(D.listings?.length||0)+' ofert w pliku';
renderKpis();refresh();renderEvents();
