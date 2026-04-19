// STMC Ops – Owner role JavaScript
// window.LOGIN_URL must be set by the HTML template before this script runs.

const SEED='/stmc_ops/app/seed-data/';
const LOGIN_URL=window.LOGIN_URL;
let PROJECTS=[];

// Redirect immediately if no session
if(!localStorage.getItem('stmc_user')){window.location.href=LOGIN_URL;}

function fmt(n){return'$'+Number(n).toLocaleString('en-US',{minimumFractionDigits:0,maximumFractionDigits:0})}

function getCookie(name){
  const v=document.cookie.match('(^|;)\\s*'+name+'\\s*=\\s*([^;]+)');
  return v?v.pop():'';
}

function showToast(msg){
  const t=document.getElementById('toast');
  t.textContent=msg;
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),3200);
}

async function markComplete(pid,dn){
  const p=PROJECTS.find(x=>String(x.id)===String(pid));
  if(!p)return;
  const d=p.dr.find(x=>String(x.n)===String(dn));
  if(!d)return;
  try{
    const res=await fetch('/stmc_ops/app/draw/complete/',{
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')},
      body:JSON.stringify({job_id:pid,draw_number:dn})
    });
    if(!res.ok)throw new Error('Server error');
    const result=await res.json();
    const seedRes=await fetch(SEED);
    const data=await seedRes.json();
    const own=data.owner||{};
    PROJECTS=own.projects||[];
    renderKpis(own.kpis||[]);
    renderNotifications(own.notifications||[]);
    renderDashProjects(PROJECTS);
    renderAllProjects(PROJECTS);
    renderPayments(PROJECTS);
    showToast('\u2713 '+d.l+' complete');
  }catch(e){
    showToast('Error saving \u2014 try again');
    console.error(e);
  }
}

function _initials(n){return(n||'').split(/\s+/).map(w=>w[0]||'').join('').toUpperCase().slice(0,2)||'?'}

function initAuth(data){
  const userId=localStorage.getItem('stmc_user');
  const users=(data&&data.users)||[];
  const user=users.find(u=>u.id===userId)||{name:userId,initials:_initials(userId)};
  const nameEl=document.getElementById('hN');
  const badgeEl=document.getElementById('hA');
  if(nameEl)nameEl.textContent=user.name||userId;
  if(badgeEl)badgeEl.textContent=user.initials||_initials(user.name||userId);
  document.querySelectorAll('.logout-link').forEach(btn=>{
    btn.addEventListener('click',()=>{
      localStorage.removeItem('stmc_user');
      localStorage.removeItem('stmc_region');
      window.location.href=LOGIN_URL;
    });
  });
}

function switchTab(btn,tab){
  document.querySelectorAll('.tab-panel').forEach(p=>{p.style.display='none'});
  document.querySelectorAll('.app-nav-link').forEach(b=>{b.classList.remove('active')});
  document.getElementById('tab-'+tab).style.display='';
  btn.classList.add('active');
}

function phasePill(ph){
  const map={'framing':'success','roughin':'success','roofing':'success','siding':'success','punch':'success','complete':'success','final':'success','closed':'success','interior':'warning','paint':'warning','estimate':'muted'};
  const lbl={'estimate':'Estimate','framing':'Framing','roughin':'Rough-In','interior':'Interior','punch':'Punch','final':'Final','closed':'Closed','roofing':'Roofing','siding':'Siding','paint':'Paint','complete':'Complete'};
  const t=map[(ph||'').toLowerCase()]||'muted';
  return`<span class="pill pill-${t}">${lbl[ph]||ph}</span>`;
}

function stepPill(p){
  const cur=(p.dr||[]).find(d=>d.s==='c');
  if(!cur)return phasePill(p.ph);
  const lbl=cur.l.replace(/^\d+\w*\s*[\u2014\-]\s*/,'');
  return`<span class="pill pill-success">${lbl}</span>`;
}

function drawNumClass(s){return s==='p'?'paid':s==='c'?'current':''}
function drawPill(s){
  if(s==='p')return'<span class="pill pill-success">Paid</span>';
  if(s==='c')return'<span class="pill pill-brand">Due</span>';
  return'<span class="pill pill-muted">Pending</span>';
}

function toggleProj(hdr){
  const body=hdr.nextElementSibling;
  const chev=hdr.querySelector('.chevron');
  body.classList.toggle('open');
  chev.classList.toggle('open');
}

function renderKpis(kpis){
  document.getElementById('owner-kpis').innerHTML=kpis.map(k=>`
    <div class="kpi-tile">
      <div class="kpi-val ${k.tone?'tone-'+k.tone:''}">${k.value}</div>
      <div class="kpi-lbl">${k.label}</div>
    </div>`).join('');
  const cv=kpis.find(k=>k.label==='Contract value');
  if(cv)document.getElementById('owner-total').textContent=cv.value;
}

function phR(d){
  const ic=d.s==='p'?'\u2713':d.s==='c'?'\u25BA':(d.n===0?'D':d.n);
  const dc=d.s==='p'?'pdg':d.s==='c'?'pdb':'pdx';
  const sc=d.s==='p'?'var(--green)':d.s==='c'?'#1D4ED8':'var(--g400)';
  const sl=d.s==='p'?'Paid'+(d.t?' '+d.t:''):d.s==='c'?'Current':'Pending';
  return`<div class="ph">
    <div class="pd ${dc}">${ic}</div>
    <div style="flex:1"><div style="font-weight:500">${d.l}</div>${d.t&&d.s==='p'?`<div style="font-size:10px;color:var(--g400)">${d.t}</div>`:''}</div>
    <div style="text-align:right;min-width:55px">
      <div style="font-family:var(--font-mono);font-weight:500">${fmt(d.a)}</div>
      <div style="font-size:9px;font-weight:600;text-transform:uppercase;color:${sc}">${sl}</div>
    </div>
  </div>`;
}

function renderNotifications(notifs){
  const toneClass={'brand':'','success':'tone-success','warning':'tone-warning'};
  const badge=document.getElementById('notif-count');
  if(badge)badge.textContent=notifs.length;
  document.getElementById('notif-list').innerHTML=notifs.map(n=>{
    const tc=toneClass[n.tone]||'';
    return`<div class="notif ${tc}">
      <div class="notif-dot ${tc}"></div>
      <div style="font-size:12px;line-height:1.5">
        <strong>${n.title}</strong> &mdash; ${n.message}
        ${n.time?`<div style="font-size:10px;color:var(--g400);margin-top:2px">${n.time}</div>`:''}
      </div>
    </div>`;
  }).join('');
}

function renderDashProjects(projects){
  const active=projects.filter(p=>p.ph!=='closed');
  const closed=projects.filter(p=>p.ph==='closed');
  const sectionHdr=(label,count)=>`<div style="font-size:11px;font-weight:600;color:var(--g400);text-transform:uppercase;letter-spacing:.05em;margin:16px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--g200)">${label} <span style="font-weight:400">(${count})</span></div>`;
  const heading=`<div class="stl">Active projects <span class="stl-badge">${active.length}</span></div>`;
  const buildCard=p=>{
    const collected=p.dr?p.dr.filter(d=>d.s==='p').reduce((a,d)=>a+d.a,0):0;
    const pct=p.ct>0?Math.min(100,Math.round(collected/p.ct*100)):0;
    const rem=p.ct-collected;
    const draws=(p.dr||[]).map(d=>phR(d)).join('');
    const cur=p.dr&&p.dr.find(d=>d.s==='c');
    const completeBox=cur&&p.ph!=='closed'?`
      <div style="margin-top:10px;padding:10px 14px;background:#EFF6FF;border-radius:var(--radius-sm);display:flex;justify-content:space-between;align-items:center">
        <div>
          <div style="font-size:12px;font-weight:500;color:#1D4ED8">${cur.l} ready?</div>
          <div style="font-size:10px;color:#3B82F6;opacity:.8">Tap to mark paid</div>
        </div>
        <button class="btn-complete" onclick="markComplete('${p.id}','${cur.n}')">Mark complete</button>
      </div>`:'';
    return`
    <div class="proj-card">
      <div class="proj-hdr" onclick="toggleProj(this)">
        <div class="proj-hdr-top">
          <div>
            <p class="proj-name">${p.nm}</p>
            <p class="proj-sub">${p.md} &middot; ${p.cu} &middot; PM: ${p.pm}</p>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            ${stepPill(p)}
            <span class="chevron">&#8964;</span>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-top:10px;padding-top:8px;border-top:1px solid var(--g200)">
          <div><div style="font-size:9px;color:var(--g400);text-transform:uppercase">Contract</div><div style="font-family:var(--font-mono);font-size:12px;font-weight:500;margin-top:1px">${fmt(p.ct)}</div></div>
          <div><div style="font-size:9px;color:var(--g400);text-transform:uppercase">Collected</div><div style="font-family:var(--font-mono);font-size:12px;font-weight:500;margin-top:1px;color:var(--green)">${fmt(collected)}</div></div>
          <div><div style="font-size:9px;color:var(--g400);text-transform:uppercase">Progress</div><div style="font-family:var(--font-mono);font-size:12px;font-weight:500;margin-top:1px">${pct}%</div></div>
          <div><div style="font-size:9px;color:var(--g400);text-transform:uppercase">Balance</div><div style="font-family:var(--font-mono);font-size:12px;font-weight:500;margin-top:1px;color:var(--green)">${fmt(rem)}</div></div>
        </div>
        <div style="height:4px;background:var(--g200);border-radius:2px;margin-top:8px;overflow:hidden"><div style="height:100%;background:var(--green);border-radius:2px;width:${pct}%"></div></div>
      </div>
      <div class="proj-body">${draws}${completeBox}</div>
    </div>`;
  };
  const activeSect=active.length?active.map(buildCard).join(''):'<div class="banner banner-empty">No active projects.</div>';
  const closedSect=closed.length?sectionHdr('Closed',closed.length)+closed.map(buildCard).join(''):'';
  document.getElementById('dash-projects').innerHTML=heading+activeSect+closedSect;
}

function renderAllProjects(projects){
  const el=document.getElementById('all-projects-list');
  const active=projects.filter(p=>p.ph!=='closed');
  const closed=projects.filter(p=>p.ph==='closed');
  const sectionHdr=(label,count)=>`<div style="font-size:11px;font-weight:600;color:var(--g400);text-transform:uppercase;letter-spacing:.05em;margin:16px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--g200)">${label} <span style="font-weight:400">(${count})</span></div>`;
  const buildCard=p=>{
    const trades=Object.keys(p.bg||{});
    const totalBg=trades.reduce((a,t)=>a+(p.bg[t]||0),0);
    const totalAc=trades.reduce((a,t)=>a+(p.ac[t]||0),0);
    const collected=p.dr?p.dr.filter(d=>d.s==='p').reduce((a,d)=>a+d.a,0):0;
    const margin=p.ct>0&&totalBg>0?Math.round((p.ct-totalBg)/p.ct*100):0;
    const marginColor=margin>=30?'var(--green)':margin>=15?'var(--amber)':'#DC2626';
    const collectedPct=p.ct>0?Math.min(100,Math.round(collected/p.ct*100)):0;
    const rows=trades.map(t=>{
      const bg=p.bg[t]||0,ac=p.ac[t]||0,ov=ac>bg;
      return`<div class="rw">
        <span class="rl">${t}</span>
        <span class="rd" style="color:${ov?'#DC2626':'var(--g400)'}">${fmt(ac)}/${fmt(bg)}</span>
        <span class="rv" style="color:${ov?'#DC2626':'var(--green)'}">${fmt(bg-ac)}</span>
      </div>`;
    }).join('');
    return`
    <div class="card" style="margin-bottom:16px;padding:14px 16px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
        <div>
          <div style="font-size:15px;font-weight:600;color:var(--g900)">${p.nm}</div>
          <div style="font-size:11px;color:var(--g500);margin-top:2px">${p.md} &middot; ${p.cu} &middot; PM: ${p.pm}</div>
        </div>
        ${phasePill(p.ph)}
      </div>
      <div class="proj-kpis">
        <div class="proj-kpi"><div class="proj-kl">Contract</div><div class="proj-kv">${fmt(p.ct)}</div></div>
        <div class="proj-kpi"><div class="proj-kl">Collected</div><div class="proj-kv" style="color:var(--green)">${fmt(collected)}</div></div>
        <div class="proj-kpi"><div class="proj-kl">PM Budget</div><div class="proj-kv">${fmt(totalBg)}</div></div>
        <div class="proj-kpi"><div class="proj-kl">Margin</div><div class="proj-kv" style="color:${marginColor}">${margin}%</div></div>
      </div>
      <div class="ybanner">COLLECTED &mdash; ${collectedPct}% of contract</div>
      <div style="height:6px;background:var(--g200);border-radius:3px;overflow:hidden;margin-bottom:10px">
        <div style="height:100%;border-radius:3px;background:var(--green);width:${collectedPct}%"></div>
      </div>
      ${rows}
      ${_completeBox(p)}
    </div>`;
  };
  const activeSect=active.map(buildCard).join('')||'<div class="banner banner-empty">No active projects.</div>';
  const closedSect=closed.length?sectionHdr('Closed Projects',closed.length)+closed.map(buildCard).join(''):'';
  el.innerHTML=(active.length?sectionHdr('Active Projects',active.length):'')+activeSect+closedSect;
}

function _completeBox(p){
  const cur=p.dr&&p.dr.find(d=>d.s==='c');
  return cur?`
    <div style="margin-top:10px;padding:10px 14px;background:#EFF6FF;border-radius:var(--radius-sm);display:flex;justify-content:space-between;align-items:center">
      <div>
        <div style="font-size:12px;font-weight:500;color:#1D4ED8">${cur.l} ready?</div>
        <div style="font-size:10px;color:#3B82F6;opacity:.8">Tap to mark paid</div>
      </div>
      <button class="btn-complete" onclick="markComplete('${p.id}','${cur.n}')">Mark complete</button>
    </div>`:'';
}

function renderPayments(projects){
  const el=document.getElementById('payments-list');
  const active=projects.filter(p=>p.ph!=='closed');
  const closed=projects.filter(p=>p.ph==='closed');
  const sectionHdr=(label,count)=>`<div style="font-size:11px;font-weight:600;color:var(--g400);text-transform:uppercase;letter-spacing:.05em;margin:16px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--g200)">${label} <span style="font-weight:400">(${count})</span></div>`;
  const payCard=p=>{
    const total=p.ct||0;
    const paid=p.dr?p.dr.filter(d=>d.s==='p').reduce((a,d)=>a+d.a,0):0;
    const pct=total>0?Math.min(100,Math.round(paid/total*100)):0;
    const rows=(p.dr||[]).map(d=>`
      <div class="draw-row">
        <div class="draw-num ${drawNumClass(d.s)}">${d.n===0?'D':d.n}</div>
        <div class="draw-info">
          <div class="draw-label">${d.l}</div>
          ${d.t?`<div class="draw-date">${d.t}</div>`:'<div class="draw-date" style="color:var(--g400)">—</div>'}
        </div>
        ${drawPill(d.s)}
        <div class="draw-amt">${fmt(d.a)}</div>
      </div>`).join('');
    return`
    <div class="card" style="margin-bottom:16px">
      <div class="section-hdr section-hdr-red">
        ${p.nm}
        <span class="badge">${fmt(paid)} of ${fmt(total)}</span>
      </div>
      <div style="padding:12px 16px;border-bottom:1px solid var(--g200)">
        <div class="pay-labels"><span>Collected — ${pct}%</span><span>Remaining: ${fmt(total-paid)}</span></div>
        <div class="pay-track" style="margin-top:6px"><div class="pay-fill" style="width:${pct}%"></div></div>
      </div>
      <div style="padding:8px 16px 12px">${rows}${_completeBox(p)}</div>
    </div>`;
  };
  const activeSect=active.length?active.map(payCard).join(''):'<div class="banner banner-empty">No active payments.</div>';
  const closedSect=closed.length?sectionHdr('Closed Projects',closed.length)+closed.map(payCard).join(''):'';
  el.innerHTML=(active.length?sectionHdr('Active Projects',active.length):'')+activeSect+closedSect;
}

async function init(){
  try{
    const res=await fetch(SEED);
    const data=await res.json();
    initAuth(data);
    const own=data.owner||{};
    PROJECTS=own.projects||[];
    renderKpis(own.kpis||[]);
    renderNotifications(own.notifications||[]);
    renderDashProjects(PROJECTS);
    renderAllProjects(PROJECTS);
    renderPayments(PROJECTS);
  }catch(e){
    document.getElementById('notif-list').innerHTML='<div class="banner banner-empty">Failed to load data.</div>';
    console.error(e);
  }
}
init();
