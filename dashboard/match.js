/* Deterministic preference fit. Not a mechanical-condition or purchase-safety rating. */
(function(root){
 'use strict';
 const equipment={rear_camera:12,heated_seats:12,carplay:10,heated_steering:6,agr:5,intellilux:5,acc:5,hud:3,dic8:2,electric_tailgate:3,heated_windshield:2,blind_spot:2,rcta:1,camera_360:1,keyless:1};
 const defaults={budget:65000,preferAutomatic:true,weights:equipment};
 function fit(car,prefs={}){
  const budget=Number(prefs.budget)>0?Number(prefs.budget):defaults.budget;
  const prefer=prefs.preferAutomatic!==false;
  const weights={...equipment,...(prefs.weights||{})};
  const parts=[];
  function add(key,max,earned,known,value){parts.push({key,max,earned,known,value});}
  add('budget',10,Number.isFinite(car.price_pln)&&car.price_pln<=budget?10:0,Number.isFinite(car.price_pln),car.price_pln);
  const knownGear=['automatic','manual'].includes(car.gearbox);
  add('gearbox',20,knownGear?(car.gearbox==='automatic'||!prefer?20:12):0,knownGear,car.gearbox);
  Object.entries(weights).forEach(([key,w])=>{w=Math.max(0,Number(w)||0);if(!w)return;const v=(car.equipment||{})[key];add(key,w,v===true?w:0,typeof v==='boolean',v);});
  const total=parts.reduce((s,p)=>s+p.max,0),earned=parts.reduce((s,p)=>s+p.earned,0),unknown=parts.filter(p=>!p.known).reduce((s,p)=>s+p.max,0);
  const blockers=[];
  if(car.status!=='active')blockers.push('Nieaktywne lub niezweryfikowane');
  if(car.problematic===true||(car.defects||[]).length)blockers.push('Opisane usterki — osobna ocena');
  if(Number.isFinite(car.price_pln)&&car.price_pln>budget)blockers.push('Poza budżetem');
  if(car.year&&car.year<2017)blockers.push('Poza generacją B');
  return {score:Math.round(earned/total*100),potential:Math.round((earned+unknown)/total*100),coverage:Math.round((total-unknown)/total*100),earned,total,unknown,parts,blockers,candidate:blockers.length===0};
 }
 function band(km){if(!Number.isFinite(km))return 'unknown';if(km<=50)return 'near';if(km<=150)return 'regional';if(km<=300)return 'far';return 'long';}
 function distance(a,b){const rad=x=>x*Math.PI/180;const dLat=rad(b.lat-a.lat),dLon=rad(b.lon-a.lon);const h=Math.sin(dLat/2)**2+Math.cos(rad(a.lat))*Math.cos(rad(b.lat))*Math.sin(dLon/2)**2;return 6371.0088*2*Math.atan2(Math.sqrt(h),Math.sqrt(Math.max(0,1-h)));}
 function route(location){if(!location)return null;const dest=Number.isFinite(location.lat)&&Number.isFinite(location.lon)?`${location.lat},${location.lon}`:location.city?location.city+', Polska':null;if(!dest)return null;return 'https://www.google.com/maps/dir/?'+new URLSearchParams({api:'1',origin:'Włocławek, Polska',destination:dest,travelmode:'driving'});}
 const api={fit,band,distance,route,defaults};root.InsigniaMatch=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window==='undefined'?globalThis:window);
