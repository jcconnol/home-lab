"use strict";
const modes = {
  overview: ["Mission control", "A little window into your very unusual lab.", "⌂"],
  terrarium: ["Artificial-life terrarium", "A small ecosystem. Real rules. A little care.", "✳"],
  network: ["Digital radar", "Your explicitly configured devices and services.", "◎"],
  health: ["GRACE health", "An independent check on your assistant's availability.", "+"],
  observatory: ["Anomaly observatory", "Unusual observations, with the evidence attached.", "△"],
  twin: ["Apartment twin", "Rooms, lights, and the state they actually reported.", "▦"],
  space: ["Space command", "Observation windows and imported satellite passes.", "↗"],
  universe: ["Garage universe", "Your device fleet, interpreted as a small solar system.", "◌"],
  detective: ["Signal detective", "Events that happened close together. Causes still to investigate.", "≈"],
  timeline: ["Time machine", "Recorded changes, in the order they happened.", "↶"],
  missions: ["Science missions", "Make a prediction. Observe. Write down what happened.", "⚑"]
};
let state = null;
let mode = location.hash.slice(1) || "overview";
let selectedNode = null;
let busy = false;
const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const date = (value) => value ? new Date(value).toLocaleString() : "Not checked yet";
const tag = (status) => `<span class="tag ${["unavailable","unreachable","error","anomaly"].includes(status) ? "bad" : ["unknown","stale","degraded","not_configured","checking"].includes(status) ? "warn" : ""}">${esc(String(status || "unknown").replaceAll("_", " "))}</span>`;
const empty = (title, text) => `<div class="empty"><strong>${esc(title)}</strong>${esc(text)}</div>`;
const panel = (title, body, note="") => `<article class="panel"><h2>${esc(title)}</h2>${note ? `<p>${esc(note)}</p>` : ""}${body}</article>`;

$("navigation").innerHTML = Object.entries(modes).map(([key, value]) => `<a href="#${key}" data-mode="${key}"><span class="nav-icon">${value[2]}</span>${esc(key === "overview" ? "Overview" : value[0])}</a>`).join("");

function habitat(large=false) {
  const t = state.terrarium;
  let shapes = "";
  for(let i=0;i<32;i++) shapes+=`<circle cx="${12+(i*97)%680}" cy="${35+(i*41)%170}" r="${i%3===0?1.5:.7}" fill="#97ce6c" opacity=".4"/>`;
  for(let i=0;i<Math.ceil(t.plants/4);i++) {
    const x=18+(i*71)%650,y=235+(i*13)%40,h=17+(i*17)%40;
    shapes+=`<path d="M${x} ${y}q-8 -${h/2} 0 -${h}" fill="none" stroke="#7cbb55" stroke-width="3"/><path d="M${x-12} ${y-h+5}q12 -20 24 0Z" fill="${i%3?'#3e7950':'#a8ca56'}"/><circle cx="${x-3}" cy="${y-h}" r="1.5" fill="#c9ff86"/>`;
  }
  for(const creature of t.creatures.slice(0,100)) {
    const x=45+(creature.id*101+t.tick*9)%610,y=170+(creature.id*31)%70;
    shapes+=`<g><title>Creature ${creature.id}: age ${creature.age}, energy ${creature.energy}</title><ellipse cx="${x}" cy="${y+12}" rx="23" ry="4" fill="#07120d" opacity=".7"/><path d="M${x-12} ${y+5}q-8 -17 3 -23q15 -9 24 6q8 18 -5 21Z" fill="${creature.parent?'#e2bf72':'#bcf470'}" stroke="#7bba43"/><path d="M${x-6} ${y-15}l-4 -12m15 11l5 -12" stroke="#bcf470" stroke-width="3"/><circle cx="${x-10}" cy="${y-28}" r="5" fill="#def5b5"/><circle cx="${x+10}" cy="${y-28}" r="5" fill="#def5b5"/><circle cx="${x-9}" cy="${y-28}" r="2" fill="#13211c"/><circle cx="${x+11}" cy="${y-28}" r="2" fill="#13211c"/><path d="M${x-3} ${y-4}q5 4 9 -1m-11 12l-3 7m13 -7l3 7" stroke="#426131" stroke-width="2" fill="none"/><text x="${x}" y="${y+32}" text-anchor="middle" fill="#b1d48e" font-family="monospace" font-size="8">SPEC-${String(creature.id).padStart(3,'0')}</text></g>`;
  }
  return `<svg class="terrarium ${large?'large':''}" viewBox="0 0 700 300" role="img" aria-label="Ecosystem with ${t.creatures.length} creatures and ${t.plants} plant energy"><defs><radialGradient id="portal"><stop stop-color="#bfff694d"/><stop offset=".7" stop-color="#5ca93412"/><stop offset="1" stop-color="#08170f00"/></radialGradient></defs><path d="M0 60H700M0 110H700M0 160H700M100 0V300M200 0V300M300 0V300M400 0V300M500 0V300M600 0V300" stroke="#345737" opacity=".15"/><circle cx="530" cy="137" r="104" fill="url(#portal)"/><ellipse cx="530" cy="137" rx="66" ry="79" fill="none" stroke="#74bc39" stroke-width="2" stroke-dasharray="55 7 14 9" opacity=".8"/><ellipse cx="530" cy="137" rx="58" ry="70" fill="none" stroke="#b9f75f" stroke-width=".7" opacity=".6"/><path d="M505 138q25 -42 47 -11t-26 31q-24 -5 -7 -24t20 10" fill="none" stroke="#90cf47" opacity=".4"/><text x="530" y="235" fill="#81a85d" font-family="monospace" font-size="8" text-anchor="middle">COSMETIC PORTAL / SIMULATED HABITAT</text><path d="M0 234Q130 200 280 239T700 229V300H0Z" fill="#143224"/><path d="M0 270Q200 226 390 271T700 252V300H0Z" fill="#1b3b25"/>${shapes}<path d="M12 42V12H42M658 12H688V42M12 258V288H42M658 288H688V258" fill="none" stroke="#82b64e"/><text x="26" y="33" fill="#b7ef80" font-family="monospace" font-size="10">BIOSPHERE 01 / ${t.paused?'STASIS':'ACTIVE'}</text><text x="26" y="282" fill="#94b879" font-family="monospace" font-size="8">PERSISTENT ECOLOGY / TICK ${t.tick}</text></svg>`;
}

function careControls() {
  return `<div class="controls"><button data-care="feed">Feed +10</button><button class="secondary" data-care="pause">${state.terrarium.paused ? "Resume" : "Pause"}</button><button class="secondary" data-care="step">Advance one tick</button><button class="secondary" data-care="introduce">Introduce creature</button></div>`;
}

function terrariumPanel(large=false) {
  const t=state.terrarium;
  return `<article class="panel habitat-panel"><div class="panel-top"><div><h2>A world on your workbench</h2><p>Forage. Grow. Survive. Start a new lineage.</p></div>${tag(t.paused ? "paused" : "running")}</div>${habitat(large)}<div class="terrarium-stats"><span>POPULATION <strong>${t.creatures.length}</strong></span><span>PLANT ENERGY <strong>${t.plants}/100</strong></span><span>TICK <strong>${t.tick}</strong></span></div>${careControls()}</article>`;
}

function serviceRows() {
  const nodes=state.network.nodes;
  return nodes.length ? `<div class="rows">${nodes.map(n=>`<div class="row"><div><span class="name">${esc(n.name || n.id)}</span><small>${esc(n.host)}:${esc(n.port)}${n.check_kind?" / "+esc(n.check_kind):""}</small></div>${tag(n.status)}</div>`).join("")}</div>` : empty("No services configured", "Add your devices to runtime/config.json to start tracking reachability.");
}

function eventRows(events) {
  return events.length ? `<div class="rows">${events.slice().reverse().map(e=>`<div class="row"><div><span class="name">${esc(e.source)} / ${esc(e.event || e.type || "observation")}</span><small>${esc(date(e.timestamp))}</small></div></div>`).join("")}</div>` : empty("Quiet so far", "Service-state changes are recorded here. No events have been invented.");
}

function graph(universe=false) {
  const nodes=state.network.nodes;
  if (!nodes.length) return empty("Your fleet starts here", "Configure named TCP services to build this map. Traffic relationships are not inferred.");
  const positions={};
  nodes.forEach((n,i)=> {const angle=(i/nodes.length)*Math.PI*2-Math.PI/2;positions[n.id]={x:350+Math.cos(angle)*205,y:190+Math.sin(angle)*130};});
  let drawing="";
  if (universe) drawing+=`<ellipse cx="350" cy="190" rx="205" ry="130" fill="none" stroke="#344c32"/>`;
  for (const edge of state.network.edges) {
    const a=positions[edge.source],b=positions[edge.target];
    if(a&&b) drawing+=`<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="#6b825c" stroke-dasharray="5 5"/>`;
  }
  if(universe) drawing+=`<circle cx="350" cy="190" r="25" fill="#c9b26d"/><text x="350" y="235" text-anchor="middle">Garage lab</text>`;
  for (const n of nodes) {
    const p=positions[n.id];
    drawing+=`<g data-node="${esc(n.id)}" role="button" tabindex="0" aria-label="Inspect ${esc(n.name || n.id)}"><rect x="${p.x-85}" y="${p.y-23}" width="170" height="75" rx="8" fill="transparent"/><circle cx="${p.x}" cy="${p.y}" r="${universe?19:11}" fill="${n.status==="reachable"?"#b4e686":"#59695c"}"/><text x="${p.x}" y="${p.y+38}" text-anchor="middle">${esc(n.name || n.id)}</text></g>`;
  }
  return `<svg class="graph" viewBox="0 0 700 390" aria-label="${universe?"Cosmetic fleet solar system":"Configured service network map"}" role="img">${drawing}</svg><p>${universe?"Cosmetic orbits; colors represent reported reachability.":"Dashed edges are configured links or explicitly reported agent connections. Select a device for its measurement scope."}</p>`;
}

function inputPanel(name, title, description, render) {
  const value=state.modules[name];
  if (!value || value.status==="not_configured") return panel(title, empty("Waiting for your data", description));
  if(value.status==="error") return panel(title, empty("Input needs attention", value.error));
  const sources=value.sources ? panel("Live source status",`<div class="rows">${Object.entries(value.sources).map(([name,feed])=>`<div class="row"><div class="name">${esc(name)}<small>${esc(feed.error||feed.data?.attribution||feed.data?.note||feed.data?.source_url||"Configured source")}</small><small>${esc(date(feed.fetched_at))}${feed.stale?" / last good data retained in cache; excluded from current readings":""}</small></div>${tag(feed.status)}</div>`).join("")}</div>`) : "";
  return sources+render(value.data);
}

function missionCards() {
  return state.missions.map(m=>`<article class="panel mission"><h2>${esc(m.question)}</h2><p>Prediction: ${esc(m.prediction)}</p><span class="detail">Mission ${m.id} / ${esc(date(m.created_at))}</span>${m.observations.map(o=>`<div class="observation">${esc(o.outcome)}<small class="detail"> / ${esc(date(o.observed_at))}</small></div>`).join("")}<form data-observe="${m.id}"><input name="outcome" aria-label="Observation for mission ${m.id}" placeholder="What actually happened?" maxlength="2000" required><button class="secondary" type="submit">Record observation</button></form></article>`).join("") || empty("Your first experiment awaits", "Write a question and a prediction above.");
}

function render() {
  if(!state) return;
  if(!modes[mode]) mode="overview";
  document.body.dataset.mode=mode;
  $("title").textContent=modes[mode][0];$("subtitle").textContent=modes[mode][1];
  document.querySelectorAll("[data-mode]").forEach(a=>a.classList.toggle("active",a.dataset.mode===mode));
  const h=state.health,t=state.terrarium;
  let html="";
  if(mode==="overview") {
    const online=state.network.nodes.filter(n=>n.status==="reachable").length;
    html=`<div class="command-strip"><span>FIELD TERMINAL / GARAGE COMMAND</span><span>OBSERVATION + SIMULATION / ${state.network.nodes.length} CONFIGURED SERVICES</span></div><div class="stats"><article class="panel stat"><span class="label">GRACE / HTTP</span><strong>${esc(h.status.replaceAll("_"," "))}</strong><small>${h.latency_ms!==undefined?`${h.latency_ms} ms check`:"Configure your tower URL"}</small></article><article class="panel stat"><span class="label">FLEET / REACHABLE</span><strong>${online} <span class="muted">/ ${state.network.nodes.length}</span></strong><small>Configured TCP services</small></article><article class="panel stat"><span class="label">LIVING TERRARIUM</span><strong>${t.creatures.length} creatures</strong><small>Tick ${t.tick} / ${t.paused?"paused":"growing"}</small></article><article class="panel stat"><span class="label">DASHBOARD HOST / STORAGE</span><strong>${state.host.disk_free_gb} GB</strong><small>Free on ${esc(state.host.name)}</small></article></div><div class="grid">${terrariumPanel()}<div class="stack">${panel("Service watch",serviceRows(),"TCP checks and enrolled heartbeats; resource data requires a host agent.")}${panel("Recent changes",eventRows(state.events.slice(-4)))}</div></div><div class="panel mission"><h2>Make this lab yours</h2><p>The terrarium and experiment notebook work now. Configure your tower and services for live checks; connect your own data files for the other observatory modes. No demo measurements are presented as live data.</p><div class="pills"><a href="#missions">Start a science mission →</a><a href="#network">Explore your fleet →</a></div></div>`;
  } else if(mode==="terrarium") {
    html=`<div class="grid">${terrariumPanel(true)}${panel("Ecosystem log",t.events.length?`<div class="rows">${t.events.slice(-12).reverse().map(e=>`<div class="row"><div class="name">${esc(e.type)} / creature ${e.id}<small>Tick ${e.tick}${e.parent?` / parent ${e.parent}`:""}</small></div></div>`).join("")}</div>`:empty("A new beginning","Births and deaths will appear as the ecosystem develops."),"State is saved on the dashboard host. It pauses while the host is off.")}</div>`;
  } else if(mode==="network" || mode==="universe") {
    const node=state.network.nodes.find(n=>n.id===selectedNode);
    html=`<div class="grid">${panel(mode==="universe"?"Your small solar system":"Device and service map",graph(mode==="universe"))}<div class="stack">${panel("Configured services",serviceRows())}${panel("Selected device",node?`<h3>${esc(node.name||node.id)}</h3>${tag(node.status)}<p>${esc(node.host)}:${esc(node.port)}</p><p>${esc(node.error||"Service check succeeded. Application internals have not been verified.")}</p>${node.metadata?.cpu_percent!==undefined?`<p>CPU ${esc(node.metadata.cpu_percent)}% / RAM ${esc(node.metadata.memory_percent)}% / ${esc(node.metadata.disk_free_gb)} GB free</p>`:""}<span class="detail">${esc(date(node.checked_at))}</span>`:empty("Select a node","Choose a device on the map to inspect its last check."))}</div></div>`;
  } else if(mode==="health") {
    html=`<div class="grid">${panel("GRACE availability",`${tag(h.status)}<div class="large-number">${h.latency_ms!==undefined?`${h.latency_ms} ms`:"—"}</div><p>${esc(h.error || (h.status==="not_configured"?"Start with --grace-url http://YOUR-TOWER:8000/ or set grace_url in the config file.":"This is an HTTP availability check, not proof that every GRACE integration is healthy."))}</p><span class="detail">Last check: ${esc(date(h.checked_at))}</span>`)}${panel("Dashboard host",`<div class="rows"><div class="row">Host <strong>${esc(state.host.name)}</strong></div><div class="row">Platform <strong>${esc(state.host.system)}</strong></div><div class="row">Dashboard uptime <strong>${Math.floor(state.host.uptime_seconds/60)} min</strong></div><div class="row">Free storage <strong>${state.host.disk_free_gb} GB</strong></div></div>`,"These measurements belong to the dashboard host, which may be a different machine from GRACE.")}</div>${panel("Checks still to connect",`<ul class="pending-list"><li>Database connectivity and persistence</li><li>Model service, queue, and inference latency</li><li>Camera and voice-node heartbeats</li><li>Tower CPU, GPU, memory, and temperature agents</li></ul>`)}`;
  } else if(mode==="observatory") {
    html=inputPanel("observatory","Anomaly observatory","Set inputs.anomaly_readings to a JSON reading history in your config. Live public-feed collection is not connected yet.",data=>`<div class="cards">${data.map(r=>panel(r.metric,`${tag(r.status)}<div class="large-number">${esc(r.value)} ${esc(r.unit)}</div><p>${esc(r.explanation)}</p><span class="detail">${esc(r.source)} / ${esc(r.location)}<br>${esc(date(r.timestamp))}</span>`)).join("") || empty("No readings","Your input file contains no observations.")}</div>`);
  } else if(mode==="space") {
    html=inputPanel("space","Observation windows","Set inputs.satellite_passes to sourced pass predictions for your location. Orbital prediction and live satellite feeds remain to implement.",data=>`<div class="cards">${data.map(p=>panel(p.name,`${tag(p.visibility||"unverified")}<div class="large-number">${Math.max(0,Math.floor((new Date(p.start)-Date.now())/60000))} min</div><p>${esc(date(p.start))}</p><span class="detail">${esc(p.location)}<br>Source: ${esc(p.source)}</span>`,"Computed visibility is a prediction, not a guarantee; clouds and obstructions matter. Imported schedules may be unverified.")).join("") || empty("No future passes","Import fresh, location-specific predictions.")}</div>`);
  } else if(mode==="twin") {
    html=inputPanel("twin","Apartment map","Set inputs.apartment_layout and inputs.apartment_states. The first version reads exports; it does not subscribe to Home Assistant yet.",data=>`<div class="cards">${data.rooms.map(room=>{const w=room.width||6,h=room.height||4;return panel(room.name,`<svg class="graph" viewBox="0 0 360 240" role="img" aria-label="${esc(room.name)} device positions"><rect x="10" y="10" width="340" height="220" fill="#202d23" stroke="#52604b"/>${room.devices.map(d=>`<g><circle cx="${20+Number(d.x||0)/w*300}" cy="${20+Number(d.y||0)/h*180}" r="9" fill="${d.freshness==="fresh"&&d.state==="on"?"#e8ce81":"#6c7d6d"}"/><text x="${20+Number(d.x||0)/w*300}" y="${45+Number(d.y||0)/h*180}" text-anchor="middle">${esc(d.entity_id)}</text></g>`).join("")}</svg><div class="rows">${room.devices.map(d=>`<div class="row"><div class="name">${esc(d.entity_id)}<small>${esc(d.state)}</small></div>${tag(d.freshness)}</div>`).join("")}</div>`,state.modules.twin.note||"Read-only export. Last change time is not a live connection heartbeat.");}).join("")}</div>`);
  } else if(mode==="detective") {
    const pairs=state.modules.detective?.data||[];
    html=panel("Coincidence is a clue",pairs.length?`<div class="rows">${pairs.slice().reverse().map(p=>`<div class="row"><div><span class="name">${esc(p.events[0].source)} ↔ ${esc(p.events[1].source)}</span><small>${p.separation_seconds} seconds apart / ${esc(p.explanation)}</small></div></div>`).join("")}</div>`:empty("No cross-source coincidences yet","Events from different sources within 60 seconds appear here. That does not establish a cause."));
  } else if(mode==="timeline") {
    html=panel("Recorded history",eventRows(state.events),"Tracks configured service-state changes and optional imported events. Gaps are not reconstructed.");
  } else if(mode==="missions") {
    html=panel("Launch an experiment",`<form id="create-mission" class="mission-form"><label>Your question<input name="question" required maxlength="2000" placeholder="Does this mount reduce vibration?"></label><label>Your prediction<input name="prediction" required maxlength="2000" placeholder="At least 20% less vibration"></label><button type="submit">Create mission</button></form>`,"Keep predictions separate from observed outcomes.")+missionCards();
  }
  $("content").innerHTML=html;
  $("updated").textContent=state.checked_at?`CHECKED ${date(state.checked_at)}`:"INITIAL CHECK IN PROGRESS";
}

async function api(path,data) {
  const response=await fetch(path,data===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
  const payload=await response.json();
  if(response.status===401){$("login").hidden=false;$("content").hidden=true;throw new Error(payload.error);}
  if(!response.ok) throw new Error(payload.error||"Request failed");
  return payload;
}

function notify(message){$("notice").textContent=message;$("notice").hidden=!message;}

async function refresh() {
  if(busy) return;
  busy=true;
  try {
    const focused=document.activeElement;
    const editing=focused?.tagName==="INPUT"&&$("content").contains(focused);
    state=await api("/api/status");
    $("login").hidden=true;$("content").hidden=false;
    $("connection").textContent="CONNECTED / PRIVATE HOST";
    const stale=state.checked_at&&(Date.now()-new Date(state.checked_at))>state.refresh_seconds*2000+5000;
    notify(state.collection_error?`Collector needs attention: ${state.collection_error}`:stale?"Checks are stale. Last results remain visible; they may no longer reflect current conditions.":"");
    if(!editing) render();
  } catch(error) {$("connection").textContent="DISCONNECTED";notify(error.message);}
  finally {busy=false;}
}

async function act(path,data) {
  try {await api(path,data);state=await api("/api/status");render();notify("");} catch(error){notify(error.message);}
}

window.addEventListener("hashchange",()=>{mode=location.hash.slice(1);render();});
$("content").addEventListener("click",event=>{
  const care=event.target.closest("[data-care]");
  if(care) act("/api/terrarium",{action:care.dataset.care});
  const node=event.target.closest("[data-node]");
  if(node){selectedNode=node.dataset.node;render();}
});
$("content").addEventListener("keydown",event=>{
  if((event.key==="Enter"||event.key===" ")&&event.target.hasAttribute("data-node")){event.preventDefault();selectedNode=event.target.dataset.node;render();}
});
$("content").addEventListener("submit",event=>{
  event.preventDefault();
  const form=event.target,fields=Object.fromEntries(new FormData(form));
  if(form.id==="create-mission") act("/api/missions",{action:"create",...fields});
  else if(form.dataset.observe) act("/api/missions",{action:"observe",id:Number(form.dataset.observe),...fields});
});
$("login").addEventListener("submit",async event=>{
  event.preventDefault();
  try{await api("/api/login",{password:$("password").value});$("password").value="";await refresh();}catch(error){notify(error.message);}
});
setInterval(()=>{$("clock").textContent=new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"});},1000);
setInterval(refresh,5000);
refresh();
