"use strict";
// An interactive perspective projection of actual 3D vectors. No continuous animation.
window.SolarView = class {
  constructor(canvas) {
    this.canvas=canvas;this.context=canvas.getContext("2d");this.data=null;this.focus="sun";this.selected="earth";this.scale="compressed";this.moons=true;this.small=true;this.yaw=.35;this.pitch=.88;this.zoom=1;this.points=[];this.pending=false;
    canvas.addEventListener("pointerdown",event=>{this.drag={x:event.clientX,y:event.clientY,moved:false};canvas.setPointerCapture(event.pointerId);});
    canvas.addEventListener("pointermove",event=>{if(!this.drag)return;const dx=event.clientX-this.drag.x,dy=event.clientY-this.drag.y;this.drag.x=event.clientX;this.drag.y=event.clientY;this.drag.moved=this.drag.moved||Math.abs(dx)+Math.abs(dy)>2;this.yaw+=dx*.008;this.pitch=Math.max(-1.45,Math.min(1.45,this.pitch+dy*.008));this.drawSoon();});
    canvas.addEventListener("pointerup",event=>{if(this.drag&&!this.drag.moved){const rect=canvas.getBoundingClientRect(),x=event.clientX-rect.left,y=event.clientY-rect.top;const point=this.points.slice().reverse().find(p=>Math.hypot(p.x-x,p.y-y)<Math.max(15,p.radius+5));if(point)this.select(point.body.id);}this.drag=null;});
    canvas.addEventListener("pointercancel",()=>{this.drag=null;});
    canvas.addEventListener("wheel",event=>{event.preventDefault();this.zoom=Math.max(.25,Math.min(8,this.zoom*(event.deltaY>0?.9:1.1)));this.drawSoon();},{passive:false});
    canvas.addEventListener("keydown",event=>{if(["ArrowLeft","ArrowRight","ArrowUp","ArrowDown","+","-","Home"].includes(event.key)){event.preventDefault();if(event.key==="Home")this.reset();else if(event.key==="+")this.zoom=Math.min(8,this.zoom*1.1);else if(event.key==="-")this.zoom=Math.max(.25,this.zoom/1.1);else{this.yaw+=event.key==="ArrowLeft"?-.12:event.key==="ArrowRight"?.12:0;this.pitch=Math.max(-1.45,Math.min(1.45,this.pitch+(event.key==="ArrowUp"?.12:event.key==="ArrowDown"?-.12:0)));}this.drawSoon();}});
    new ResizeObserver(()=>this.drawSoon()).observe(canvas);
  }
  reset(){this.yaw=.35;this.pitch=.88;this.zoom=1;this.drawSoon();}
  update(data){const changed=this.data?.epoch!==data?.epoch||this.data?.bodies.length!==data?.bodies.length;this.data=data;if(changed){this.catalog();this.details();this.drawSoon();}}
  select(id){this.selected=id;const body=this.data?.bodies.find(b=>b.id===id);if(body?.kind==="moon"){this.focus=body.parent||"sun";document.getElementById("solar-focus").value=this.focus;this.zoom=1;}this.catalog();this.details();this.drawSoon();}
  catalog(){
    const container=document.getElementById("solar-catalog");container.replaceChildren();
    for(const body of this.data?.bodies||[]){const button=document.createElement("button");button.textContent=body.name;button.className=body.id===this.selected?"active":"";button.addEventListener("click",()=>this.select(body.id));container.append(button);}
    const select=document.getElementById("solar-focus"),old=this.focus;select.replaceChildren();
    for(const body of (this.data?.bodies||[]).filter(b=>["sun","planet","dwarf"].includes(b.kind))){const option=document.createElement("option");option.value=body.id;option.textContent=body.id==="sun"?"Whole solar system":body.name+" system";select.append(option);}select.value=old;
  }
  details(){
    const element=document.getElementById("solar-selected");element.replaceChildren();
    const body=this.data?.bodies.find(b=>b.id===this.selected);if(!body)return;
    const h=document.createElement("h3");h.textContent=body.name;element.append(h);
    const parent=this.data.bodies.find(b=>b.id===body.parent),distance=Math.hypot(...body.xyz_au),paragraph=document.createElement("p");
    paragraph.textContent=body.kind.replaceAll("_"," ")+" · "+body.source;element.append(paragraph);
    const details=document.createElement("div");details.className="body-data";details.textContent=`From Sun: ${distance.toFixed(4)} AU`;
    if(parent&&body.kind==="moon")details.textContent+=`\nFrom ${parent.name}: ${(Math.hypot(...body.xyz_au.map((v,i)=>v-parent.xyz_au[i]))*149597870.7).toLocaleString(undefined,{maximumFractionDigits:0})} km`;
    details.textContent+=`\nX ${body.xyz_au[0].toFixed(5)} AU\nY ${body.xyz_au[1].toFixed(5)} AU\nZ ${body.xyz_au[2].toFixed(5)} AU\n${body.center||"body center"}`;element.append(details);
  }
  drawSoon(){if(this.pending)return;this.pending=true;requestAnimationFrame(()=>{this.pending=false;this.draw();});}
  draw(){
    const rect=this.canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;
    const ratio=Math.min(window.devicePixelRatio||1,1.5);this.canvas.width=Math.round(rect.width*ratio);this.canvas.height=Math.round(rect.height*ratio);
    const ctx=this.context,w=rect.width,h=rect.height;ctx.setTransform(ratio,0,0,ratio,0,0);ctx.fillStyle="#060f19";ctx.fillRect(0,0,w,h);
    for(let i=0;i<90;i++){ctx.fillStyle=i%4?"#263849":"#486277";ctx.fillRect((i*173+13)%Math.floor(w),(i*97+29)%Math.floor(h),i%7?1:2,1);}
    if(!this.data?.bodies.length){ctx.fillStyle="#94acb5";ctx.font="13px system-ui";ctx.textAlign="center";ctx.fillText("Load the ephemeris to see calculated positions",w/2,h/2);return;}
    const origin=this.data.bodies.find(b=>b.id===this.focus)||this.data.bodies[0],local=this.focus!=="sun";
    const bodies=this.data.bodies.filter(b=>(!local||b.id===origin.id||b.parent===origin.id)&&(this.moons||b.kind!=="moon")&&(this.small||["sun","planet","moon"].includes(b.kind)||b.id===origin.id));
    const raw=b=>b.xyz_au.map((v,i)=>v-origin.xyz_au[i]);
    const factor=local?149597870.7/100000:1;
    const map=vector=>{const r=Math.hypot(...vector);if(!r)return[0,0,0];const length=this.scale==="compressed"?Math.log1p(r*factor*(local?1:10)):r*factor;return vector.map(v=>v/r*length);};
    const vectors=bodies.map(b=>({body:b,vector:map(raw(b))})),extent=Math.max(.001,...vectors.map(p=>Math.hypot(...p.vector))),scale=Math.min(w,h)*.37/extent*this.zoom;
    const project=vector=>{const[x,y,z]=vector,cy=Math.cos(this.yaw),sy=Math.sin(this.yaw),cp=Math.cos(this.pitch),sp=Math.sin(this.pitch);const xx=x*cy-y*sy,yy=(x*sy+y*cy)*cp-z*sp,zz=(x*sy+y*cy)*sp+z*cp;const perspective=5*extent/(5*extent+zz);return{x:w/2+xx*scale*perspective,y:h/2-yy*scale*perspective,depth:zz,perspective};};
    ctx.strokeStyle="#1a3348";ctx.lineWidth=1;
    for(const p of vectors.filter(p=>p.body.id!==origin.id&&p.body.kind!=="moon").slice(0,12)){const r=Math.hypot(...p.vector);ctx.beginPath();for(let i=0;i<=80;i++){const angle=i/80*Math.PI*2,point=project([r*Math.cos(angle),r*Math.sin(angle),0]);if(i===0)ctx.moveTo(point.x,point.y);else ctx.lineTo(point.x,point.y);}ctx.stroke();}
    if(local){const max=extent;for(let axis=0;axis<2;axis++){ctx.beginPath();const a=project(axis?[0,-max,0]:[-max,0,0]),b=project(axis?[0,max,0]:[max,0,0]);ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();}}
    this.points=vectors.map(p=>({...project(p.vector),body:p.body})).sort((a,b)=>b.depth-a.depth);
    ctx.textAlign="left";ctx.font="11px system-ui";const labels=[];
    for(const point of this.points){const b=point.body,radius=b.kind==="sun"?14:b.id===origin.id?12:b.kind==="planet"?6:b.kind==="moon"?3:4;point.radius=radius;
      ctx.fillStyle=b.color||"#b4a0ec";ctx.beginPath();ctx.arc(point.x,point.y,radius,0,Math.PI*2);ctx.fill();
      if(b.id==="saturn"){ctx.strokeStyle="#d0bf9b";ctx.beginPath();ctx.ellipse(point.x,point.y,radius*1.9,radius*.5,-.25,0,Math.PI*2);ctx.stroke();}
      if(b.id===this.selected){ctx.strokeStyle="#eef7ff";ctx.beginPath();ctx.arc(point.x,point.y,radius+5,0,Math.PI*2);ctx.stroke();}
      if(local||b.kind!=="moon"||b.id===this.selected){
        const width=ctx.measureText(b.name).width;let x=Math.min(w-width-8,Math.max(8,point.x+radius+8)),y=point.y+4;
        for(const offset of [0,-16,16,-32,32,-48,48,-64,64]){const candidate=point.y+4+offset;if(candidate<35||candidate>h-12)continue;if(!labels.some(r=>x<r.x+r.w&&x+width>r.x&&candidate-10<r.y+3&&candidate+3>r.y-10)){y=candidate;break;}}
        labels.push({x,y,w:width});if(Math.abs(y-point.y)>10){ctx.strokeStyle="#3b5367";ctx.beginPath();ctx.moveTo(point.x+radius,point.y);ctx.lineTo(x-3,y-4);ctx.stroke();}
        ctx.fillStyle=b.id===this.selected?"#fff":"#a7becf";ctx.fillText(b.name,x,y);
      }
    }
    ctx.font="9px monospace";ctx.fillStyle="#7393aa";ctx.textAlign="left";ctx.fillText(local?`${origin.name.toUpperCase()} FRAME / SIZES EXAGGERATED`:"HELIOCENTRIC / J2000 ECLIPTIC / SIZES EXAGGERATED",15,24);
  }
};
