"use strict";
const $=id=>document.getElementById(id);
const esc=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let state=null,polling=false,working=false,receiving=false,lab=null,stopLab=false;
const uid=()=>globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+Math.random().toString(36).slice(2);
function notice(message){$("notice").textContent=message;$("notice").hidden=!message;}
async function api(path,data){
  let response;
  try{response=await fetch(path,data===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});}catch(error){error.offline=true;throw error;}
  const result=await response.json();
  if(response.status===401){$("login").hidden=false;$("application").hidden=true;}
  if(!response.ok){const error=new Error(result.error||result.note||`HTTP ${response.status}`);error.status=response.status;throw error;}
  return result;
}
function outbox(action,value){return new Promise((resolve,reject)=>{
  const open=indexedDB.open("garage-fleet-outbox",1);
  open.onupgradeneeded=()=>open.result.createObjectStore("requests",{keyPath:"id"});
  open.onerror=()=>reject(open.error);
  open.onsuccess=()=>{const db=open.result,transaction=db.transaction("requests",action==="list"?"readonly":"readwrite"),store=transaction.objectStore("requests");const request=action==="list"?store.getAll():action==="put"?store.put(value):store.delete(value);transaction.oncomplete=()=>{resolve(request.result);db.close();};transaction.onerror=()=>{reject(transaction.error);db.close();};};
});}
async function deliver(path,data){
  const packet={id:uid(),device:state?.you,path,data};
  try{return await api(path,data);}catch(error){if(!error.offline)throw error;await outbox("put",packet);return {queued:true};}
}
async function flush(){
  const rows=await outbox("list");$("queue-status").textContent=`OFFLINE QUEUE / ${rows.length}`;
  for(const row of rows){if(row.device!==state?.you)continue;try{await api(row.path,row.data);await outbox("delete",row.id);}catch(error){notice(`Queued request retained: ${error.message}`);break;}}
}
function navigate(){const page=location.hash.slice(1)||"devices";document.body.dataset.mode=page==="matches"?"arena":page;document.querySelectorAll("[data-page]").forEach(section=>section.hidden=section.dataset.page!==page);document.querySelectorAll("nav a").forEach(a=>a.classList.toggle("active",a.hash==="#"+page));}
window.addEventListener("hashchange",navigate);navigate();
function name(id){return state?.devices.find(d=>d.id===id)?.name||id;}
function choices(select,options){const previous=select.value;select.innerHTML=options;if([...select.options].some(o=>o.value===previous))select.value=previous;}
function board(fen){
  const pieces={p:"♟",r:"♜",n:"♞",b:"♝",q:"♛",k:"♚",P:"♙",R:"♖",N:"♘",B:"♗",Q:"♕",K:"♔"};
  let squares="",index=0;
  for(const row of fen.split(" ")[0].split("/"))for(const code of row){const count=/[1-8]/.test(code)?Number(code):1;for(let i=0;i<count;i++){const piece=pieces[code]||"";squares+=`<span class="square ${((Math.floor(index/8)+index%8)%2)?"dark":""} ${code===code.toLowerCase()&&piece?"black-piece":""}">${piece}</span>`;index++;}}
  return `<div class="chess-board" role="img" aria-label="Chess board: ${esc(fen)}">${squares}</div>`;
}
function render(){
  const me=state.devices.find(d=>d.id===state.you);$("device-name").textContent=me?.name||"PAIRED";$("connection").textContent="CONNECTED / PAIRED";
  $("devices").innerHTML=state.devices.map(d=>`<article class="panel"><h2>${esc(d.name)}</h2><span class="tag ${d.online?"":"warn"}">${d.online?"online":"offline"}</span><p>${esc(d.metadata.kind||"device")} / ${esc(d.metadata.platform||"not reported")}</p>${d.metadata.cpu_percent!==undefined?`<p class="detail">CPU ${esc(d.metadata.cpu_percent)}% / RAM ${esc(d.metadata.memory_percent)}% / ${esc(d.metadata.disk_free_gb)} GB free</p>`:""}<span class="detail">${d.last_seen?new Date(d.last_seen*1000).toLocaleString():"Waiting for first heartbeat"}</span></article>`).join("");
  document.querySelectorAll(".device-select").forEach(select=>choices(select,state.devices.filter(d=>d.id!==state.you||select.closest("#job-form")).map(d=>`<option value="${esc(d.id)}">${esc(d.name)}${d.online?"":" (offline)"}</option>`).join("")));
  choices($("photo-select"),'<option value="">No photo</option>'+state.photos.map(p=>`<option value="${p.id}">${esc(p.project)} / ${esc(p.caption||p.id.slice(0,8))}</option>`).join(""));
  $("photos").innerHTML=state.photos.map(p=>`<article class="panel"><a href="/media/photos/${p.digest}" target="_blank" rel="noopener"><img src="/media/photos/${p.digest}" alt="${esc(p.caption||p.project)}" loading="lazy"></a><h2>${esc(p.project)}</h2><p>${esc(p.caption)}</p><span class="detail">${esc(name(p.device))} / ${esc(new Date(p.captured_at).toLocaleString())}</span></article>`).join("")||'<div class="empty">Take the first photo for your lab journal.</div>';
  $("messages").innerHTML=state.messages.map(m=>{const photo=state.photos.find(p=>p.id===m.attachment);return `<article class="panel"><h2>${esc(name(m.sender))} → ${esc(name(m.recipient))}</h2><p class="message-body">${esc(m.text)}</p>${photo?`<a href="/media/photos/${photo.digest}" target="_blank" rel="noopener">Open attached original</a>`:""}<p class="detail">${esc(m.sent_at)} / ${m.acknowledged_at?"acknowledged":"queued / unacknowledged"}</p>${m.recipient===state.you&&!m.acknowledged_at?`<button data-ack="${m.id}">Acknowledge</button>`:""}</article>`;}).join("")||'<div class="empty">No dispatches yet.</div>';
  $("matches").innerHTML=state.matches.map(match=>{
    const joined=match.players.includes(state.you),ready=match.players.length===2,d=match.data;
    let body=`<p>${match.players.map(id=>esc(name(id))).join(" vs ")}${ready?"":" / waiting for a second device"}</p>`;
    if(!joined&& !ready)body+=`<button data-join="${match.id}">Join match</button>`;
    if(match.kind==="battle")body+=`<pre class="match-result">Round ${d.round} | A: ${d.players.a.hp} HP / ${d.players.a.energy} energy | B: ${d.players.b.hp} HP / ${d.players.b.energy} energy\n${d.winner?"Winner: "+esc(d.winner):d.submitted?"Move committed. Waiting for opponent.":"Choose strike, guard, charge, or repair."}</pre>${joined&&ready&&!d.winner&&!d.submitted?`<div class="controls">${d.allowed_actions.map(a=>`<button data-battle="${match.id}" data-round="${d.round}" data-action="${a}">${a}</button>`).join("")}</div>`:""}`;
    if(match.kind==="chess")body+=board(d.fen)+`<p class="detail">White ${Math.ceil(d.remaining[0])}s / Black ${Math.ceil(d.remaining[1])}s / ${d.winner===null?"to move: "+(d.turn===0?"white":"black"):"result: "+esc(d.winner)}</p>${joined&&ready&&d.winner===null&&d.you===d.turn?`<form data-chess="${match.id}"><label>Legal move<select name="move">${d.legal_moves.map(m=>`<option value="${m.uci}">${m.uci}</option>`).join("")}</select></label><button>Play move</button></form>`:""}<button class="secondary" data-pgn="${match.id}">Download PGN</button>`;
    if(match.kind==="network")body+=`<pre class="match-result">${d.finished?"Verified output: "+JSON.stringify(d.values)+"\nReference: "+JSON.stringify(d.reference):d.timed_out?"Timed out: a stage did not finish.":"Stages complete: "+d.stage+" / 2"}</pre>${d.task?`<button data-layer="${match.id}">Compute my layer on this device</button>`:""}<p class="detail">A tiny untrained network, not a distributed language model.</p>`;
    return `<article class="panel match"><h2>${esc(match.kind.toUpperCase())} / ${match.id}</h2>${body}</article>`;
  }).join("")||'<div class="empty">Create a match, then join it from another paired device.</div>';
  $("benchmarks").innerHTML=state.benchmarks.map(b=>`<article class="panel"><h2>${esc(name(b.sender))} → ${esc(name(b.recipient))}</h2><p>${b.uploaded} bytes received by hub / ${b.acknowledged} bytes verified in the time window / ${b.verified_mbps} Mbps</p><span class="tag">${esc(b.state)}</span><p class="detail">Hub-relayed path. Budget ${b.budget} bytes.</p>${b.state==="active"?`<button class="secondary" data-stop-bench="${b.id}">Stop transfer</button>`:""}</article>`).join("");
  $("jobs").innerHTML=state.jobs.map(job=>`<article class="panel"><h2>${esc(job.kind)} / ${esc(name(job.device))}</h2><span class="tag">${esc(job.state)}</span><p>${esc(job.result?.error||job.result?.summary||"Waiting for an installed agent to execute this job.")}</p>${job.result?.artifact?`<a href="/media/artifacts/${esc(job.result.artifact)}" target="_blank" rel="noopener"><img class="job-artifact" src="/media/artifacts/${esc(job.result.artifact)}" alt="Recorded browser test screenshot"></a>`:""}</article>`).join("");
}
async function poll(){
  if(polling)return;polling=true;
  try{state=await api("/api/state");$("login").hidden=true;$("application").hidden=false;render();await receive();await automatic();}
  catch(error){$("connection").textContent="DISCONNECTED";notice(error.message);}
  finally{polling=false;}
}
async function run(action){try{await action();notice("");await poll();}catch(error){notice(error.message);}}
async function compute(match){const task=match.data.task;if(!task)return;const values=task.layer.weights.map((weights,i)=>{const value=weights.reduce((sum,w,j)=>sum+w*task.input[j],task.layer.bias[i]);return task.layer.activation==="relu"?Math.max(0,value):value;});await api("/api/matches/action",{id:match.id,stage:task.stage,values});}
async function automatic(){
  if(!$("auto").checked||working)return;working=true;
  try{for(const match of state.matches){if(!match.players.includes(state.you)||match.players.length!==2)continue;const d=match.data;
    if(match.kind==="network"){if(d.task)await compute(match);continue;}
    if(d.winner!==null||(match.kind==="battle"&&d.submitted)||(match.kind==="chess"&&d.you!==d.turn))continue;
    const mode=$("agent-mode").value;if(mode==="manual")continue;let action;
    if(mode==="tower")action=(await api("/api/model/move",{id:match.id})).action;
    else if(match.kind==="chess")action=d.legal_moves.slice().sort((a,b)=>{const score=m=>m.features.reduce((sum,v,i)=>sum+v*[10,.1,1000,.05][i],0);return score(b)-score(a);})[0]?.uci;
    else {const stats=d.players[d.you];action=stats.hp<8&&stats.energy>=3?"repair":stats.energy>=2?"strike":"charge";}
    await api("/api/matches/action",match.kind==="chess"?{id:match.id,move:action}:{id:match.id,round:d.round,action});
  }}finally{working=false;}
}
const fromBase64=value=>Uint8Array.from(atob(value),c=>c.charCodeAt(0));
function toBase64(bytes){let value="";for(let i=0;i<bytes.length;i+=8192)value+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(value);}
async function receive(){
  if(!$("receive").checked||receiving)return;
  if(!globalThis.crypto?.subtle){$("benchmark-progress").textContent="Use HTTPS or localhost to verify received chunks.";return;}
  receiving=true;try{for(const b of state.benchmarks)for(const chunk of b.chunks){const received=await api("/api/chunks/"+chunk.id),bytes=fromBase64(received.data);const hash=[...new Uint8Array(await crypto.subtle.digest("SHA-256",bytes))].map(v=>v.toString(16).padStart(2,"0")).join("");if(hash!==received.sha256)throw new Error("Received chunk failed integrity check");await api("/api/benchmarks/ack",{id:chunk.id,sha256:hash});}}finally{receiving=false;}
}
$("login").addEventListener("submit",event=>{event.preventDefault();run(async()=>{await api("/api/login",{token:new FormData(event.target).get("token")});event.target.reset();await api("/api/heartbeat",{kind:"phone browser",platform:navigator.platform,user_agent:navigator.userAgent});state=await api("/api/state");await flush();});});
$("logout").addEventListener("click",()=>run(async()=>{await api("/api/logout",{});location.reload();}));
$("photo-form").addEventListener("submit",event=>{event.preventDefault();run(async()=>{const form=new FormData(event.target),file=form.get("image");if(!file.size||file.size>5*1024**2)throw new Error("Choose an original photo up to 5 MiB");const result=await deliver("/api/photos",{image:toBase64(new Uint8Array(await file.arrayBuffer())),project:form.get("project"),caption:form.get("caption"),captured_at:new Date().toISOString()});event.target.reset();if(result.queued)notice("Saved in this browser's offline queue; keep this browser data until it uploads.");});});
$("message-form").addEventListener("submit",event=>{event.preventDefault();run(async()=>{const data=Object.fromEntries(new FormData(event.target));data.id=uid();if(!data.photo)delete data.photo;await deliver("/api/messages",data);event.target.querySelector('[name="text"]').value="";});});
$("job-form").addEventListener("submit",event=>{event.preventDefault();run(async()=>{const data=Object.fromEntries(new FormData(event.target));data.spec=JSON.parse(data.spec);await api("/api/jobs",data);});});
$("plan-form").addEventListener("submit",event=>{event.preventDefault();run(async()=>{const result=await api("/api/model/plan",{prompt:new FormData(event.target).get("prompt")});$("job-spec").value=JSON.stringify(result.plan,null,2);});});
$("benchmark-form").addEventListener("submit",event=>{event.preventDefault();run(async()=>{const benchmark=await api("/api/benchmarks",{recipient:new FormData(event.target).get("recipient")});const bytes=new Uint8Array(64*1024);for(let i=0;i<bytes.length;i++)bytes[i]=i%251;for(let i=0;i<32;i++){await api("/api/benchmarks/chunk",{id:benchmark.id,data:toBase64(bytes)});$("benchmark-progress").textContent=`Sent ${(i+1)*64} KiB to the relay; recipient must verify delivery.`;await new Promise(resolve=>setTimeout(resolve,200));}});});
document.body.addEventListener("click",event=>{const button=event.target.closest("button");if(!button)return;const d=button.dataset;
  if(d.create)run(()=>api("/api/matches",{kind:d.create}));
  if(d.join)run(()=>api("/api/matches/join",{id:d.join}));
  if(d.ack)run(()=>api("/api/messages/ack",{id:d.ack}));
  if(d.battle)run(()=>api("/api/matches/action",{id:d.battle,round:Number(d.round),action:d.action}));
  if(d.layer)run(()=>compute(state.matches.find(m=>m.id===d.layer)));
  if(d.stopBench)run(()=>api("/api/benchmarks/stop",{id:d.stopBench}));
  if(d.pgn){const match=state.matches.find(m=>m.id===d.pgn),a=document.createElement("a");a.href=URL.createObjectURL(new Blob([match.data.pgn],{type:"application/x-chess-pgn"}));a.download=match.id+".pgn";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
});
$("matches").addEventListener("submit",event=>{event.preventDefault();if(event.target.dataset.chess)run(()=>api("/api/matches/action",{id:event.target.dataset.chess,move:new FormData(event.target).get("move")}));});
$("start-lab").addEventListener("click",()=>run(async()=>{if(lab)throw new Error("A fixture test is already running");stopLab=false;lab=await api("/api/lab/start",{});let passed=0,failed=0;try{for(let i=0;i<30&&!stopLab;i++){try{await api("/api/lab/request",{id:lab.id});passed++;}catch(error){if(error.status===503)failed++;else throw error;}$("lab-progress").textContent=`${passed} successful / ${failed} intentional fixture failures`;await new Promise(resolve=>setTimeout(resolve,200));}}finally{await api("/api/lab/stop",{id:lab.id});lab=null;$("lab-progress").textContent=`Fixture ${stopLab?"stopped":"complete"}: ${passed} successful / ${failed} intentional failures.`;}}));
$("stop-lab").addEventListener("click",()=>{stopLab=true;});
setInterval(poll,2000);
setInterval(async()=>{if(state)try{await api("/api/heartbeat",{kind:"phone browser",platform:navigator.platform,user_agent:navigator.userAgent});await flush();}catch(error){notice(error.message);}},10000);
window.addEventListener("online",()=>run(flush));
poll();
