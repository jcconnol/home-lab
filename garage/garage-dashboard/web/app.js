"use strict";
const $=id=>document.getElementById(id),esc=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let state=null,polling=false,locations=[],bodyResults=[],setupClosed=false,landPaths=[];
const solar=new SolarView($("solar-canvas"));
const numeric=value=>typeof value==="number"&&Number.isFinite(value);
const number=(value,digits=0)=>numeric(value)?value.toLocaleString(undefined,{maximumFractionDigits:digits}):"—";
const imperial=()=>state?.settings.units!=="metric";
const temp=value=>numeric(value)?Math.round(imperial()?value*9/5+32:value):"—";
const wind=value=>numeric(value)?`${Math.round(value*(imperial()?.621371:1))} ${imperial()?"mph":"km/h"}`:"—";
const distance=value=>numeric(value)?`${number(value*(imperial()?.621371:1),1)} ${imperial()?"mi":"km"}`:"—";
const direction=value=>numeric(value)?["N","NE","E","SE","S","SW","W","NW"][Math.round(value/45)%8]:"—";
const instant=value=>numeric(value)?new Date(value*1000):new Date(value);
const zone=()=>state?.feeds.weather?.data?.timezone||state?.settings.location?.timezone||Intl.DateTimeFormat().resolvedOptions().timeZone;
function format(value,options){try{return new Intl.DateTimeFormat(undefined,{timeZone:zone(),...options}).format(instant(value));}catch{return "—";}}
const time=value=>value===null||value===undefined?"—":format(value,{hour:"numeric",minute:"2-digit"});
function dateKey(value){try{const parts=new Intl.DateTimeFormat("en",{timeZone:zone(),year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(instant(value));return ["year","month","day"].map(type=>parts.find(p=>p.type===type).value).join("-");}catch{return "";}}
function notice(message){$("notice").textContent=message;$("notice").hidden=!message;}
async function api(path,data){const response=await fetch(path,data===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});const payload=await response.json();if(response.status===401){$("login").hidden=false;throw new Error(payload.error);}if(!response.ok)throw new Error(payload.error||"Request failed");return payload;}
function weatherName(code){if(code===0)return "Clear sky";if(code===1)return "Mostly clear";if(code===2)return "Partly cloudy";if(code===3)return "Overcast";if([45,48].includes(code))return "Fog";if(code>=51&&code<=57)return "Drizzle";if(code>=61&&code<=67)return "Rain";if(code>=71&&code<=77)return "Snow";if(code>=80&&code<=82)return "Rain showers";if(code>=85&&code<=86)return "Snow showers";if(code>=95)return "Thunderstorms";return "Conditions unavailable";}
function icon(code,isDay=true){const cloud=code!==0&&code!==1,rain=(code>=51&&code<=67)||(code>=80&&code<=82),snow=code>=71&&code<=77||code>=85&&code<=86;return `<svg class="weather-symbol" viewBox="0 0 60 60" aria-hidden="true">${(!cloud||code===2)&&isDay?'<circle cx="24" cy="24" r="11" fill="none" stroke="currentColor" stroke-width="2.5"/><path d="M24 4v5m0 30v5M4 24h5m30 0h5M10 10l4 4m20 20l4 4M10 38l4-4m20-20l4-4" stroke="currentColor" stroke-width="2"/>':""}${(!cloud||code===2)&&!isDay?'<path d="M35 8a19 19 0 1 0 11 32A20 20 0 0 1 35 8Z" fill="none" stroke="#c0c7ef" stroke-width="2.5"/>':""}${cloud?'<path d="M15 39a9 9 0 0 1 0-18 13 13 0 0 1 25-2 10 10 0 0 1 1 20Z" fill="#294552" stroke="#a7ccd4" stroke-width="2"/>':""}${rain?'<path d="M20 44l-3 8m14-8l-3 8m14-8l-3 8" stroke="#79d6df" stroke-width="2.5"/>':""}${snow?'<text x="17" y="55" fill="#b8e2ec" font-size="16">* * *</text>':""}${code>=95?'<path d="M32 33l-8 12h6l-3 10 13-15h-7l4-7" fill="#f4c58a"/>':""}</svg>`;}
function source(key,id){const feed=state.feeds[key],element=$(id);element.classList.remove("stale");if(!feed){element.textContent=state.configured?"Starting source…":"Set your location";return;}if(feed.status==="loading"){element.textContent="Loading…";return;}const age=(Date.now()-new Date(feed.fetched_at))/1000;const stale=feed.status==="error"||age>(key==="iss"?120:key==="aircraft"?300:7200);element.classList.toggle("stale",stale);element.textContent=feed.status==="error"?(feed.data?"Unavailable / last good data":"Source unavailable"):stale?"Data is stale":`Updated ${time(feed.fetched_at)}`;element.title=feed.error||"";}
function renderWeather(){
  const feed=state.feeds.weather,data=feed?.data;source("weather","weather-status");source("air","air-status");
  if(!data){$("weather").innerHTML=`<p class="empty">${esc(feed?.error|| (state.configured?"Fetching current conditions and your forecast…":"Set your city to see current conditions and the forecast."))}</p>`;$("hourly").replaceChildren();$("outlook").innerHTML='<p class="empty">Your forecast will appear here.</p>';return;}
  const c=data.current;
  $("weather").innerHTML=`<div class="weather-now"><div><div class="condition-icon">${icon(c.weather_code,c.is_day!==0)}<div class="temperature">${temp(c.temperature_2m)}<span>°${imperial()?"F":"C"}</span></div></div><div class="condition">${esc(weatherName(c.weather_code))}</div><div class="feels-like">Feels like ${temp(c.apparent_temperature)}° · ${numeric(c.relative_humidity_2m)?c.relative_humidity_2m:"—"}% humidity</div></div><div class="weather-metrics"><div><div class="metric-label">WIND</div><div class="metric-value">${wind(c.wind_speed_10m)}</div><div class="feels-like">From ${direction(c.wind_direction_10m)}</div></div><div><div class="metric-label">GUSTS</div><div class="metric-value">${wind(c.wind_gusts_10m)}</div></div><div><div class="metric-label">PRESSURE</div><div class="metric-value">${number(c.pressure_msl)} <small>hPa</small></div></div><div><div class="metric-label">PRECIPITATION</div><div class="metric-value">${numeric(c.precipitation)?number(c.precipitation*(imperial()?1/25.4:1),imperial()?2:1):"—"} <small>${imperial()?"in":"mm"}</small></div></div></div></div>`;
  const hours=data.hourly.time.map((value,index)=>({value,index})).filter(row=>instant(row.value)>=Date.now()-1800000).slice(0,6);
  $("hourly").innerHTML=hours.map(({value,index})=>`<div class="hour"><time>${time(value)}</time>${icon(data.hourly.weather_code?.[index],data.hourly.is_day?.[index]!==0)}<strong>${temp(data.hourly.temperature_2m[index])}°</strong><span class="rain">${number(data.hourly.precipitation_probability?.[index])}% rain</span></div>`).join("");
  $("weather-source").textContent="Open-Meteo · modeled conditions, not an indoor sensor · "+time(c.timestamp);
  const daily=data.daily||{},today=dateKey(Date.now()/1000);
  const days=(daily.time||[]).map((value,index)=>({value,index})).filter(row=>(daily.dates?.[row.index]||dateKey(row.value))>=today).slice(0,5);
  $("outlook").innerHTML=days.map(({value,index},i)=>`<div class="forecast-row"><span>${i===0?"Today":(daily.dates?.[index]?new Intl.DateTimeFormat(undefined,{timeZone:"UTC",weekday:"short"}).format(new Date(daily.dates[index]+"T12:00:00Z")):format(value,{weekday:"short"}))}</span>${icon(daily.weather_code?.[index])}<span><strong>${temp(daily.temperature_2m_max?.[index])}°</strong><span class="low">${temp(daily.temperature_2m_min?.[index])}°</span></span><span class="rain">${number(daily.precipitation_probability_max?.[index])}%</span></div>`).join("")+(days.length?`<div class="sun-times"><span>${time(daily.sunrise?.[days[0].index])}<small>SUNRISE</small></span><span>${time(daily.sunset?.[days[0].index])}<small>SUNSET</small></span></div>`:"");
  const air=state.feeds.air?.data?.current;
  $("air-quality").innerHTML=air?`<div><strong>${number(air.us_aqi)}</strong><small>REGIONAL US AQI</small></div><div><strong>${number(air.pm2_5,1)} <small>µg/m³</small></strong><small>PM2.5 · CAMS / Open-Meteo</small></div>`:'<span class="source-note">Regional air-quality data is not available yet.</span>';
}
function renderAircraft(){
  const feed=state.feeds.aircraft,data=feed?.data;source("aircraft","aircraft-status");
  if(!data){$("aircraft-count").textContent="—";$("aircraft").innerHTML=`<p class="empty">${esc(feed?.error||(state.configured?"Fetching nearby aircraft…":"Choose your city to see nearby aircraft."))}</p>`;return;}
  const planes=data.aircraft;$("aircraft-count").textContent=String(planes.length);const radius=data.radius_nm*1.852;
  let radar='<circle cx="150" cy="150" r="115" fill="#0b1b26" stroke="#365e6b"/><circle cx="150" cy="150" r="76" fill="none" stroke="#254550"/><circle cx="150" cy="150" r="38" fill="none" stroke="#254550"/><path d="M150 27V273M27 150H273" stroke="#254550"/><text x="150" y="19" text-anchor="middle">N</text><text x="283" y="154">E</text><text x="150" y="289" text-anchor="middle">S</text><text x="11" y="154">W</text><circle cx="150" cy="150" r="4" fill="#f4c58a"/>';
  for(const plane of planes){const angle=plane.bearing*Math.PI/180,x=150+Math.sin(angle)*plane.distance_km/radius*115,y=150-Math.cos(angle)*plane.distance_km/radius*115;radar+=`<g transform="translate(${x.toFixed(2)},${y.toFixed(2)}) rotate(${numeric(plane.track)?plane.track:0})"><title>${esc(plane.callsign)} / ${distance(plane.distance_km)}</title><path class="plane" d="M0-7L2-1 7 2 7 4 2 2 2 6 4 8-4 8-2 6-2 2-7 4-7 2-2-1Z"/></g>`;}
  $("aircraft").innerHTML=`<svg class="radar" viewBox="0 0 300 300" role="img" aria-label="Aircraft positions relative to your selected city, north up">${radar}</svg><div class="flight-list">${planes.slice(0,5).map(p=>`<div class="flight-row"><div><strong>${esc(p.callsign)}</strong><small>${number(p.altitude_ft)} ft · ${number(p.speed_knots)} kt${p.type?" · "+esc(p.type):""}</small></div><div class="distance">${distance(p.distance_km)}<small>${direction(p.bearing)} of city</small></div></div>`).join("")||'<p class="empty">No fresh airborne positions reported in this radius. Coverage may be limited.</p>'}</div>`;
}
function countdown(value){const seconds=Math.max(0,(instant(value)-Date.now())/1000);const days=Math.floor(seconds/86400),hours=Math.floor(seconds%86400/3600),minutes=Math.floor(seconds%3600/60);return days?`${days}d ${hours}h`:hours?`${hours}h ${minutes}m`:`${minutes} min`;}
function renderISS(){
  source("iss","iss-status");const position=state.feeds.iss?.data,passes=state.feeds.satellites?.data?.passes||[];
  const future=passes.filter(p=>instant(p.end||p.start)>Date.now()),visible=future.filter(p=>p.visibility==="potentially_visible"),next=visible[0];
  let map='<svg class="iss-map" viewBox="0 0 480 220" role="img" aria-label="ISS position on a longitude-latitude grid">';
  map+=landPaths.map(path=>`<path d="${path}" fill="#203b46" fill-rule="evenodd"/>`).join("");
  for(let x=0;x<=480;x+=60)map+=`<path d="M${x} 10V210" stroke="#1d3646"/>`;for(let y=10;y<=210;y+=40)map+=`<path d="M0 ${y}H480" stroke="#1d3646"/>`;
  map+='<path d="M0 110H480" stroke="#35576a"/><text x="6" y="103">EQUATOR</text><text x="5" y="218">180°W</text><text x="227" y="218">0°</text><text x="443" y="218">180°E</text>';
  if(state.settings.location){const l=state.settings.location,x=(l.longitude+180)/360*480,y=110-l.latitude/180*200;map+=`<circle cx="${x}" cy="${y}" r="3" fill="#f4c58a"/>`;}
  if(position){const x=(position.longitude+180)/360*480,y=110-position.latitude/180*200;map+=`<circle cx="${x}" cy="${y}" r="7" fill="none" stroke="#c0b1ef"/><circle cx="${x}" cy="${y}" r="3" fill="#c0b1ef"/><text x="${Math.min(435,Math.max(4,x+12))}" y="${Math.max(14,y-9)}">ISS</text>`;}
  map+='</svg>';
  const sourceError=state.feeds.satellites?.error||state.feeds.iss?.error;
  $("iss").innerHTML=`<div class="iss-main"><div><div class="metric-label">NEXT POTENTIALLY VISIBLE PASS</div>${next?`<div class="pass-countdown" data-countdown="${esc(next.start)}">${countdown(next.start)}</div><div class="pass-description">${format(next.start,{weekday:"short"})} at ${time(next.start)} · look ${direction(next.azimuth_degrees)}</div><div class="pass-details"><span><strong>${number(next.max_elevation_degrees)}°</strong><small>MAX ELEVATION</small></span><span><strong>${Math.round((instant(next.end)-instant(next.start))/60000)} min</strong><small>ABOVE 10°</small></span></div>`:`<p class="pass-description">${esc(sourceError||(state.feeds.satellites?.status==="live"?"No potentially visible pass in the next 48 hours.":state.configured?"Calculating passes for your city…":"Set your city to calculate passes."))}</p>`}</div><div>${map}<div class="iss-coordinates">${position?`${number(position.latitude,1)}° lat / ${number(position.longitude,1)}° lon · ${number(position.altitude_km)} km altitude<br>${position.observer_elevation>0?`Above your horizon: ${number(position.observer_elevation)}° ${direction(position.observer_azimuth)}`:"Currently below your horizon"}`:"Position not available yet."}</div></div></div>${visible.length>1?`<div class="pass-list">${visible.slice(1,3).map(p=>`<div class="pass-row"><span>${format(p.start,{weekday:"short"})} ${time(p.start)}</span><span>${direction(p.azimuth_degrees)} · ${number(p.max_elevation_degrees)}° max</span></div>`).join("")}</div>`:""}`;
}
function renderSolar(){const feed=state.feeds.solar_system;if(feed?.data){solar.update(feed.data);$("solar-status").textContent=`${feed.data.bodies.length}/${feed.data.catalog_count} bodies · ${format(feed.data.epoch,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}${feed.status==="loading"?" / loading more bodies":feed.refreshing?" / refreshing":""}${feed.status==="error"?" / stale":""}`;$("solar-note").textContent=`${feed.data.frame}. Body sizes exaggerated; compressed distances are not to scale. Rings are distance guides, not trajectories. Updates hourly. ${feed.data.unavailable.length?feed.data.unavailable.length+" catalog entries unavailable. ":""}${feed.data.coverage}`;}
  else $("solar-status").textContent=feed?.status==="error"?feed.error:feed?.status==="loading"?`${state.solar_progress.message} (${state.solar_progress.loaded}/${state.solar_progress.total})`:"Load calculated positions";
  $("solar-enable").hidden=!!feed?.data||feed?.status==="loading";
}
function render(){
  updateClock();
  const location=state.settings.location;$("location-button").textContent=state.configured?`${location.name}${location.region?", "+location.region:""} ▾`:"Set your location ▾";
  $("units-button").textContent=imperial()?"°F / mph":"°C / km/h";$("aircraft-radius").value=String(state.settings.aircraft_radius_nm);
  if(!state.configured&&!setupClosed)$("setup").hidden=false;
  renderWeather();renderAircraft();renderISS();renderSolar();
  $("updated").textContent="WEATHER ~15 MIN · AIRCRAFT ~2 MIN · ISS ~30 SEC · SOLAR SYSTEM ~1 HOUR";
}
function navigate(){const isSolar=location.hash==="#solar";$("solar").hidden=!isSolar;$("board").hidden=isSolar;document.querySelectorAll("nav a").forEach(a=>a.classList.toggle("active",a.hash===(isSolar?"#solar":"#board")));if(isSolar)solar.drawSoon();window.scrollTo(0,0);}
async function refresh(){if(polling)return;polling=true;try{state=await api("/api/status");$("login").hidden=true;$("connection").textContent="CONNECTED";notice("");render();}catch(error){$("connection").textContent="DISCONNECTED";notice(`Display host unavailable: ${error.message}. Last received information may be stale.`);}finally{polling=false;}}
async function act(work){try{await work();notice("");await refresh();}catch(error){notice(error.message);}}
$("login").addEventListener("submit",event=>{event.preventDefault();act(async()=>{await api("/api/login",{password:$("password").value});$("password").value="";});});
$("location-button").addEventListener("click",()=>{$("setup").hidden=!$("setup").hidden;setupClosed=false;$("location-query").focus();});
$("close-setup").addEventListener("click",()=>{setupClosed=true;$("setup").hidden=true;});
$("location-form").addEventListener("submit",event=>{event.preventDefault();act(async()=>{const result=await api("/api/location/search?q="+encodeURIComponent($("location-query").value));locations=result.results;$("location-results").innerHTML=locations.map((row,i)=>`<button data-location="${i}">${esc(row.name)}<small>${esc(row.region)} · ${row.latitude.toFixed(3)}, ${row.longitude.toFixed(3)}</small></button>`).join("")||'<p>No matching locations. Try a nearby city and country.</p>';});});
$("location-results").addEventListener("click",event=>{const button=event.target.closest("[data-location]");if(button)act(async()=>{await api("/api/settings",{location:locations[Number(button.dataset.location)]});setupClosed=true;$("setup").hidden=true;});});
$("units-button").addEventListener("click",()=>act(()=>api("/api/settings",{units:imperial()?"metric":"imperial"})));
$("aircraft-radius").addEventListener("change",()=>act(()=>api("/api/settings",{aircraft_radius_nm:Number($("aircraft-radius").value)})));
$("fullscreen").addEventListener("click",()=>act(async()=>{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}));
$("solar-enable").addEventListener("click",()=>act(()=>api("/api/settings",{solar_system:true})));
$("solar-focus").addEventListener("change",()=>{solar.focus=$("solar-focus").value;solar.zoom=1;solar.drawSoon();});
$("solar-scale").addEventListener("change",()=>{solar.scale=$("solar-scale").value;solar.drawSoon();});
$("solar-moons").addEventListener("change",()=>{solar.moons=$("solar-moons").checked;solar.drawSoon();});
$("solar-small").addEventListener("change",()=>{solar.small=$("solar-small").checked;solar.drawSoon();});
$("solar-reset").addEventListener("click",()=>solar.reset());
$("body-search-form").addEventListener("submit",event=>{event.preventDefault();act(async()=>{const result=await api("/api/bodies/search?q="+encodeURIComponent($("body-query").value));bodyResults=result.results;$("body-results").innerHTML=bodyResults.map((body,i)=>`<button data-body="${i}" ${body.tracked?"disabled":""}>${esc(body.name)}<small>JPL ${esc(body.id)} · ${body.tracked?"already in the catalog":"add to hourly positions"}</small></button>`).join("")||'<p>No matching JPL bodies found.</p>';});});
$("body-results").addEventListener("click",event=>{const button=event.target.closest("[data-body]");if(button)act(async()=>{await api("/api/settings",{add_body:bodyResults[Number(button.dataset.body)]});$("body-results").replaceChildren();});});
window.addEventListener("hashchange",navigate);
setInterval(()=>{location.hash=location.hash==="#solar"?"#board":"#solar";},60000);
function updateClock(){const current=Date.now()/1000;$("clock").textContent=format(current,{hour:"2-digit",minute:"2-digit",second:undefined});$("date").textContent=format(current,{weekday:"long",month:"long",day:"numeric"});document.querySelectorAll("[data-countdown]").forEach(el=>el.textContent=countdown(el.dataset.countdown));}
setInterval(updateClock,1000);
fetch("/land.json").then(response=>response.json()).then(paths=>{landPaths=paths;if(state)renderISS();}).catch(()=>{});
setInterval(refresh,15000);navigate();refresh();
