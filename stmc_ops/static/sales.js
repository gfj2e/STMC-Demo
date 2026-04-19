// STMC Ops - Sales role JavaScript
// window.LOGIN_URL must be set by the HTML template before this script runs.

const SEED='/stmc_ops/app/seed-data/';
const LOGIN_URL=window.LOGIN_URL;

// Redirect immediately if no session
if(!localStorage.getItem('stmc_user')){window.location.href=LOGIN_URL;}

function fmt(n){return'$'+Number(n).toLocaleString('en-US',{minimumFractionDigits:0,maximumFractionDigits:0})}

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
function fmtDec(n){return'$'+Number(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}
function fmtSf(n){return Number(n).toLocaleString('en-US',{minimumFractionDigits:0,maximumFractionDigits:0})+' SF'}

let activeNavLink=null;

function switchTab(link,tab){
  document.querySelectorAll('.tab-panel').forEach(p=>{p.style.display='none'});
  document.querySelectorAll('.app-nav-link').forEach(l=>{l.classList.remove('active')});
  document.getElementById('tab-'+tab).style.display='';
  if(link){link.classList.add('active');}
  const titles={'projects':'My Projects','models':'Models','rates':'Rate Card'};
  document.querySelector('.header-title').textContent=titles[tab]||'Sales';
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

function toggleProj(hdr){
  const body=hdr.nextElementSibling;
  const chev=hdr.querySelector('.chevron');
  body.classList.toggle('open');
  chev.classList.toggle('open');
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

function renderProjects(projects){
  const el=document.getElementById('projects-list');
  if(!projects||!projects.length){el.innerHTML='<div class="banner banner-empty">No projects yet.</div>';return}
  const active=projects.filter(p=>p.ph!=='closed');
  const closed=projects.filter(p=>p.ph==='closed');
  const sectionHdr=(label,count)=>`<div style="font-size:11px;font-weight:600;color:var(--g400);text-transform:uppercase;letter-spacing:.05em;margin:16px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--g200)">${label} <span style="font-weight:400">(${count})</span></div>`;
  const totalContract=active.reduce((a,p)=>a+p.ct,0);
  document.getElementById('sales-total').textContent=fmt(totalContract);

  document.getElementById('sales-kpis').innerHTML=[
    {label:'Active builds',value:String(active.length)},
  ].map(k=>`<div class="kpi-tile"><div class="kpi-val">${k.value}</div><div class="kpi-lbl">${k.label}</div></div>`).join('');

  const projCard=p=>{
    const collected=p.dr?p.dr.filter(d=>d.s==='p').reduce((a,d)=>a+d.a,0):0;
    const totalBg=Object.values(p.bg||{}).reduce((a,b)=>a+b,0);
    const totalAc=Object.values(p.ac||{}).reduce((a,b)=>a+b,0);
    const pct=p.ct>0?Math.min(100,Math.round(collected/p.ct*100)):0;
    const rem=p.ct-collected;
    const draws=(p.dr||[]).map(d=>phR(d)).join('');
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
      <div class="proj-body">${draws}</div>
    </div>`;
  };
  const activeSect=active.length?active.map(projCard).join(''):'<div class="banner banner-empty">No active projects.</div>';
  const closedSect=closed.length?sectionHdr('Closed',closed.length)+closed.map(projCard).join(''):'';
  el.innerHTML=(active.length?sectionHdr('Active',active.length):'')+activeSect+closedSect;
}

function renderModels(models){
  const el=document.getElementById('models-list');
  if(!models||!models.length){el.innerHTML='<div class="banner banner-empty">No models available.</div>';return}
  const sorted=[...models].sort((a,b)=>a.livingSf-b.livingSf);
  const hdr=`<div class="stl">Models <span class="stl-badge">${sorted.length}</span></div><div style="font-size:11px;color:var(--g500);margin-bottom:10px">Summertown / Hayden</div>`;
  const rows=sorted.map(m=>{
    const total=(m.materialTotal||0)+(m.laborBudget||0)+(m.concreteBudget||0);
    const perSf=m.livingSf>0?Math.round(total/m.livingSf):0;
    return`<div class="card" style="padding:10px 14px;margin-bottom:6px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <div style="font-size:13px;font-weight:500;color:var(--g900)">${m.name}</div>
          ${m.livingSf?`<div style="font-size:10px;color:var(--g500)">${Number(m.livingSf).toLocaleString()} SF</div>`:''}
        </div>
        <div style="text-align:right">
          <div style="font-family:var(--font-mono);font-size:13px;font-weight:500;color:var(--g900)">${fmt(total)}</div>
          <div style="font-size:9px;color:var(--g500)">$${perSf}/SF</div>
        </div>
      </div>
    </div>`;
  }).join('');
  el.innerHTML=hdr+rows;
}

function renderRates(rc){
  const extEl=document.getElementById('ext-rates');
  const intEl=document.getElementById('int-rates');

  function buildTable(el,rows){
    if(!rows||!rows.length){el.innerHTML='<tr><td class="banner banner-empty" colspan="3">No rate data.</td></tr>';return}
    let lastGroup='';
    el.innerHTML='<thead><tr><th>Description</th><th class="r">Rate</th><th class="r">Unit</th></tr></thead><tbody>'
      +rows.map(r=>{
        let hdr='';
        if(r.g&&r.g!==lastGroup){lastGroup=r.g;hdr=`<tr class="rate-group-hdr"><td colspan="3">${r.g}</td></tr>`}
        const rateStr=r.r?'$'+Number(r.r).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}):'--';
        return`${hdr}<tr><td>${r.l}</td><td class="r">${rateStr}</td><td class="u">${r.u||'--'}</td></tr>`;
      }).join('')+'</tbody>';
  }

  buildTable(extEl,(rc&&rc.exterior)||[]);
  buildTable(intEl,(rc&&rc.interior)||[]);
}

async function init(){
  try{
    const res=await fetch(SEED);
    const data=await res.json();
    initAuth(data);
    const sales=data.sales||{};
    renderProjects(sales.projects||[]);
    renderModels(sales.models||[]);
    renderRates(sales.rateCard||{});
    const tab=new URLSearchParams(window.location.search).get('tab');
    if(tab){
      const link=document.querySelector(`.app-nav-link[data-mv-tab="${tab}"]`);
      switchTab(link,tab);
    }
  }catch(e){
    document.getElementById('projects-list').innerHTML='<div class="banner banner-empty">Failed to load data.</div>';
    console.error(e);
  }
}
init();
