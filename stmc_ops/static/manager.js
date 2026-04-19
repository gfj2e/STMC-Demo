// STMC Ops – Manager role JavaScript
// window.LOGIN_URL must be set by the HTML template before this script runs.

const SEED = '/stmc_ops/app/seed-data/';
const LOGIN_URL = window.LOGIN_URL;
let PROJECTS = [];

// Redirect immediately if no session
if(!localStorage.getItem('stmc_user')){window.location.href=LOGIN_URL;}

function fmt(n){return'$'+Number(n).toLocaleString('en-US',{minimumFractionDigits:0,maximumFractionDigits:0})}

function _initials(n){return(n||'').split(/\s+/).map(w=>w[0]||'').join('').toUpperCase().slice(0,2)||'?'}

function initAuth(data){
  const userId=localStorage.getItem('stmc_user');
  const regionId=localStorage.getItem('stmc_region');
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

function fmtPct(v,t){return t>0?Math.round(v/t*100)+'%':'0%'}

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

function drawPill(s){
  if(s==='p')return'<span class="pill pill-success">Paid</span>';
  if(s==='c')return'<span class="pill pill-brand">Current</span>';
  return'<span class="pill pill-muted">Pending</span>';
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

function showToast(msg){
  const t=document.getElementById('toast');
  t.textContent=msg;
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),3200);
}

function getCookie(name){
  const v=document.cookie.match('(^|;)\\s*'+name+'\\s*=\\s*([^;]+)');
  return v?v.pop():'';
}

async function markComplete(pid, dn){
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

    d.s='p';
    d.t=result.paid_date||new Date().toLocaleDateString('en-US',{month:'short',day:'numeric'});
    const next=p.dr.find(x=>x.s==='x');
    if(next)next.s='c';

    const seedRes=await fetch(SEED);
    const data=await seedRes.json();
    const mgr=data.manager||{};
    PROJECTS=mgr.projects||[];
    const kpis=mgr.kpis||[];
    renderKpis(kpis);
    renderBuilds(PROJECTS);
    renderBudgets(PROJECTS);
    renderDraws(PROJECTS);
    showToast('\u2713 '+d.l+' complete');
  }catch(e){
    showToast('Error saving — try again');
    console.error(e);
  }
}

function renderBuilds(projects){
  const el=document.getElementById('builds-list');
  if(!projects.length){el.innerHTML='<div class="banner banner-empty">No active builds.</div>';return}
  const active=projects.filter(p=>p.ph!=='closed');
  const closed=projects.filter(p=>p.ph==='closed');
  const sectionHdr=(label,count)=>`<div style="font-size:11px;font-weight:600;color:var(--g400);text-transform:uppercase;letter-spacing:.05em;margin:16px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--g200)">${label} <span style="font-weight:400">(${count})</span></div>`;
  const buildCard=p=>{
    const collected=p.dr?p.dr.filter(d=>d.s==='p').reduce((a,d)=>a+d.a,0):0;
    const pct=p.ct>0?Math.min(100,Math.round(collected/p.ct*100)):0;
    const rem=p.ct-collected;
    const draws=(p.dr||[]).map(d=>phR(d)).join('');
    return`
    <div class="proj-card" style="${p.ph==='closed'?'opacity:.75':''}">
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
      <div class="proj-body">${draws}</div>
    </div>`;
  };
  const activeSect=active.length?active.map(buildCard).join(''):'<div class="banner banner-empty">No active builds.</div>';
  const closedSect=closed.length?sectionHdr('Closed Builds',closed.length)+closed.map(buildCard).join(''):'';
  el.innerHTML=(active.length?sectionHdr('Active Builds',active.length):'')+activeSect+closedSect;
}

function renderBudgets(projects){
  const el=document.getElementById('budgets-list');
  if(!projects.length){el.innerHTML='<div class="banner banner-empty">No budget data.</div>';return}
  const active=projects.filter(p=>p.ph!=='closed');
  const closed=projects.filter(p=>p.ph==='closed');
  const sectionHdr=(label,count)=>`<div style="font-size:11px;font-weight:600;color:var(--g400);text-transform:uppercase;letter-spacing:.05em;margin:16px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--g200)">${label} <span style="font-weight:400">(${count})</span></div>`;
  const budgetCard=p=>{
    const trades=Object.keys(p.bg||{});
    const totalBg=trades.reduce((a,t)=>a+(p.bg[t]||0),0);
    const totalAc=trades.reduce((a,t)=>a+(p.ac[t]||0),0);
    const rem=totalBg-totalAc;
    const collected=p.dr?p.dr.filter(d=>d.s==='p').reduce((a,d)=>a+d.a,0):0;
    const colRem=p.ct-collected;
    const pct=p.ct>0?Math.min(100,Math.round(collected/p.ct*100)):0;
    const tagCls=pct>=100?'pill-brand':pct>=50?'pill-success':'pill-warning';
    const rows=trades.map(t=>{
      const bg=p.bg[t]||0,ac=p.ac[t]||0,vr=bg-ac,ov=ac>bg;
      return`<div class="rw">
        <span class="rl">${t}</span>
        <span class="rd" style="color:${ov?'#DC2626':'var(--g400)'}">${fmt(ac)} / ${fmt(bg)}</span>
        <span class="rv" style="color:${ov?'#DC2626':'var(--green)'}">${fmt(vr)}</span>
      </div>`;
    }).join('');
    return`
    <div class="card" style="margin-bottom:12px">
      <div style="padding:14px 16px 12px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
          <div>
            <div style="font-size:14px;font-weight:600">${p.nm}</div>
            <div style="font-size:11px;color:var(--g500)">${p.md} &middot; ${p.cu}</div>
          </div>
          <span class="pill ${tagCls}">${pct}% collected</span>
        </div>
        <div class="budget-bar-track" style="margin-bottom:4px"><div class="budget-bar-fill" style="width:${Math.min(pct,100)}%;background:var(--green)"></div></div>
        <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--g400);margin-bottom:10px">
          <span>${fmt(collected)} collected</span><span>${fmt(colRem)} remaining</span>
        </div>
        ${rows}
        <div class="rw rt">
          <span class="rl">Total</span>
          <span class="rd">${fmt(totalAc)} / ${fmt(totalBg)}</span>
          <span class="rv" style="color:${rem<0?'#DC2626':'var(--green)'}">${fmt(rem)}</span>
        </div>
      </div>
    </div>`;
  };
  const activeSect=active.length?active.map(budgetCard).join(''):'<div class="banner banner-empty">No active budgets.</div>';
  const closedSect=closed.length?sectionHdr('Closed',closed.length)+closed.map(budgetCard).join(''):'';
  el.innerHTML=(active.length?sectionHdr('Active',active.length):'')+activeSect+closedSect;
}

function renderDraws(projects){
  const el=document.getElementById('draws-list');
  if(!projects.length){el.innerHTML='<div class="banner banner-empty">No draw data.</div>';return}
  const active=projects.filter(p=>p.ph!=='closed');
  const closed=projects.filter(p=>p.ph==='closed');
  const sectionHdr=(label,count)=>`<div style="font-size:11px;font-weight:600;color:var(--g400);text-transform:uppercase;letter-spacing:.05em;margin:16px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--g200)">${label} <span style="font-weight:400">(${count})</span></div>`;
  const drawCard=p=>{
    const rows=(p.dr||[]).map(d=>phR(d)).join('');
    const cur=p.dr&&p.dr.find(d=>d.s==='c');
    const completeBox=cur?`
      <div style="margin-top:10px;padding:10px 14px;background:#EFF6FF;border-radius:var(--radius-sm);display:flex;justify-content:space-between;align-items:center">
        <div>
          <div style="font-size:12px;font-weight:500;color:#1D4ED8">${cur.l} ready?</div>
          <div style="font-size:10px;color:#3B82F6;opacity:.8">Creates QB invoice</div>
        </div>
        <button class="btn-complete" onclick="markComplete('${p.id}','${cur.n}')">Mark complete</button>
      </div>`:'';
    return`
    <div class="card" style="margin-bottom:16px">
      <div style="padding:14px 16px 12px">
        <div style="font-size:14px;font-weight:600;margin-bottom:2px">${p.nm}</div>
        <div style="font-size:11px;color:var(--g500);margin-bottom:10px">${p.md} &middot; ${fmt(p.ct)}</div>
        ${rows}
        ${completeBox}
      </div>
    </div>`;
  };
  const activeSect=active.length?active.map(drawCard).join(''):'<div class="banner banner-empty">No active draws.</div>';
  const closedSect=closed.length?sectionHdr('Closed',closed.length)+closed.map(drawCard).join(''):'';
  el.innerHTML=(active.length?sectionHdr('Active',active.length):'')+activeSect+closedSect;
}

function renderKpis(kpis){
  document.getElementById('pm-kpis').innerHTML=kpis.map(k=>`
    <div class="kpi-tile">
      <div class="kpi-val ${k.tone?'tone-'+k.tone:''} ${k.sm?'kpi-val-sm':''}">${k.value}</div>
      <div class="kpi-lbl">${k.label}</div>
    </div>`).join('');
}

function toggleProj(hdr){
  const body=hdr.nextElementSibling;
  const chev=hdr.querySelector('.chevron');
  body.classList.toggle('open');
  chev.classList.toggle('open');
}

async function init(){
  try{
    const res=await fetch(SEED);
    const data=await res.json();
    initAuth(data);
    const mgr=data.manager||{};
    PROJECTS=mgr.projects||[];
    const kpis=mgr.kpis||[];
    renderKpis(kpis);
    renderBuilds(PROJECTS);
    renderBudgets(PROJECTS);
    renderDraws(PROJECTS);
  }catch(e){
    document.getElementById('builds-list').innerHTML=`<div class="banner banner-empty">Failed to load data.</div>`;
    console.error(e);
  }
}
init();
