/* ═══ POD shared UI layer — charts, helpers, animation, downloads, theming ═══ */

/* ── theme (set on <html data-theme> by the no-flash script in base.html) ── */
const THEME = (document.documentElement.dataset.theme === 'dark') ? 'dark' : 'light';
const TICK  = THEME==='dark' ? '#8b9bbd' : '#5a6a8f';
const GRID  = THEME==='dark' ? 'rgba(148,178,255,.09)' : 'rgba(30,60,120,.10)';
const AXIS  = THEME==='dark' ? '#8b9bbd' : '#67759a';
const TIP   = THEME==='dark'
  ? {bg:'#0a0f1e', title:'#eaf0fc', body:'#c8d3ea', border:'rgba(148,178,255,.22)'}
  : {bg:'#ffffff', title:'#0e1626', body:'#33415f', border:'rgba(30,60,120,.18)'};

/* theme-appropriate chart palette (brighter on dark, deeper on white) */
const C = THEME==='dark'
  ? { blue:'#4d8dff', blue2:'#6ea0ff', violet:'#a78bfa', teal:'#2dd4bf', green:'#34d399', amber:'#fbbf24', red:'#f87171', rose:'#fb7185', cyan:'#22d3ee' }
  : { blue:'#2563eb', blue2:'#3b76e0', violet:'#7c3aed', teal:'#0d9488', green:'#059669', amber:'#d97706', red:'#dc2626', rose:'#e11d48', cyan:'#0891b2' };

/* ── Chart.js theme defaults (guarded: the report page loads without Chart.js) ── */
if (window.Chart) {
  Chart.defaults.color = TICK;
  Chart.defaults.borderColor = GRID;
  Chart.defaults.font.family = "'Inter',sans-serif";
  Chart.defaults.font.size = 10.5;
  // NOTE: do NOT set Chart.defaults.animation here — replacing/overriding it breaks the
  // tooltip opacity fade (hover tooltips go invisible). Chart.js defaults animate fine.
}

const HRS = Array.from({length:24}, (_,h)=>`${String(h).padStart(2,'0')}:00`);

function grad(ctx, hex, h=230){ const g=ctx.createLinearGradient(0,0,0,h); g.addColorStop(0,hex+(THEME==='dark'?'66':'40')); g.addColorStop(.55,hex+'18'); g.addColorStop(1,hex+'00'); return g; }

function areaChart(cv, labels, series, opts){
  opts = opts || {};
  const ctx = cv.getContext('2d');
  const xticks = opts.allX
    ? {maxRotation:0,minRotation:0,autoSkip:false,font:{size:8.5}}
    : {maxRotation:0,autoSkip:true,maxTicksLimit:12,font:{size:9.5}};
  return new Chart(cv, { type:'line',
    data:{ labels, datasets: series.map(s=>({
      label:s.label, data:s.data, borderColor:s.color,
      backgroundColor: s.fill===false ? 'transparent' : grad(ctx,s.color),
      borderWidth:2.4, fill:s.fill!==false, tension:.42, pointRadius:0, pointHoverRadius:5,
      pointHoverBackgroundColor:s.color, pointHoverBorderColor:'#fff', pointHoverBorderWidth:1.5, borderDash:s.dash||[],
    }))},
    options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false},
      plugins:{ legend:{position:'top',labels:{boxWidth:9,boxHeight:9,borderRadius:4,useBorderRadius:true,padding:14,font:{size:10.5,weight:600}}},
        tooltip:tt() },
      scales:{ x:{grid:{display:false},ticks:xticks},
        y:{beginAtZero:true,grid:{color:GRID},ticks:{font:{size:9.5},callback:v=>v>=1000?(v/1000).toFixed(1)+'k':v}} } }
  });
}

function barLineChart(cv, labels, bars, line){
  return new Chart(cv, { type:'bar',
    data:{ labels, datasets:[
      {label:bars.label,data:bars.data,backgroundColor:bars.color+'88',borderColor:bars.color,borderWidth:0,borderRadius:5,order:2},
      {label:line.label,data:line.data,type:'line',borderColor:line.color,borderWidth:2.4,borderDash:[6,3],tension:.4,pointRadius:0,pointHoverRadius:5,order:1},
    ]},
    options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false},
      plugins:{legend:{position:'top',labels:{boxWidth:9,boxHeight:9,borderRadius:4,useBorderRadius:true,padding:14,font:{size:10.5,weight:600}}},tooltip:tt()},
      scales:{x:{grid:{display:false},ticks:{maxRotation:0,autoSkip:true,maxTicksLimit:12,font:{size:9.5}}},
        y:{beginAtZero:true,grid:{color:GRID},ticks:{font:{size:9.5}}}} }
  });
}

function donut(cv, labels, data, colors){
  return new Chart(cv, { type:'doughnut',
    data:{ labels, datasets:[{ data, backgroundColor:colors, borderColor:THEME==='dark'?'#0c1120':'#ffffff', borderWidth:3, hoverOffset:7, borderRadius:4 }] },
    options:{ responsive:true, maintainAspectRatio:false, cutout:'70%',
      plugins:{ legend:{position:'right',labels:{boxWidth:9,boxHeight:9,borderRadius:4,useBorderRadius:true,padding:10,font:{size:10.5}}}, tooltip:tt() } }
  });
}

function multiLine(cv, labels, series){
  return new Chart(cv, { type:'line',
    data:{ labels, datasets: series.map(s=>({label:s.label,data:s.data,borderColor:s.color,backgroundColor:'transparent',borderWidth:2,tension:.4,pointRadius:0,pointHoverRadius:5})) },
    options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false},
      plugins:{legend:{position:'top',labels:{boxWidth:9,boxHeight:9,borderRadius:4,useBorderRadius:true,padding:12,font:{size:10.5,weight:600}}},tooltip:tt()},
      scales:{x:{grid:{display:false},ticks:{maxRotation:0,autoSkip:true,maxTicksLimit:13,font:{size:9.5}}},
        y:{beginAtZero:true,grid:{color:GRID},ticks:{font:{size:9.5}}}} }
  });
}

function spark(cv, data, color){
  return new Chart(cv, { type:'line',
    data:{ labels:data.map((_,i)=>i), datasets:[{data,borderColor:color,borderWidth:1.7,fill:true,backgroundColor:grad(cv.getContext('2d'),color,34),tension:.42,pointRadius:0,pointHoverRadius:4}] },
    options:{ responsive:true, maintainAspectRatio:false, animation:{duration:900},
      plugins:{legend:{display:false},tooltip:Object.assign(tt(),{displayColors:false,callbacks:{title:()=>'', label:c=>fmt(c.parsed.y)+' pax'}})},
      scales:{x:{display:false},y:{display:false}} }
  });
}

/* shared tooltip style — themed. (Trigger mode is set per-chart via options.interaction,
   matching the original working build — do NOT add mode/intersect here.) */
function tt(){ return { enabled:true,
  backgroundColor:TIP.bg, titleColor:TIP.title, bodyColor:TIP.body, borderColor:TIP.border, borderWidth:1,
  cornerRadius:10, padding:11, titleFont:{weight:700,size:11.5}, bodyFont:{size:11.5},
  boxWidth:8, boxHeight:8, boxPadding:4, usePointStyle:true }; }

/* wait-time banding colour (legacy 3-tier helper) */
function heatColor(m){ return m<=10?'#22c55e' : m<=30?'#f59e0b' : '#ef4444'; }
function buildHeatmap(host, data, tps){
  let h='<table class="hm"><thead><tr><th></th>'+HRS.map((_,i)=>`<th>${String(i).padStart(2,'0')}</th>`).join('')+'</tr></thead><tbody>';
  tps.forEach(tp=>{
    h+=`<tr><td class="lbl">${tp}</td>`+data[tp].map((m,i)=>`<td class="c" style="background:${heatColor(m)}" title="${tp} ${String(i).padStart(2,'0')}:00 · ${m}m">${m}</td>`).join('')+'</tr>';
  });
  host.innerHTML = h+'</tbody></table>';
}

const fmt = n => Number(n).toLocaleString();

/* ── count-up animation for KPI numerals ── */
function countUp(el, target, opts){
  opts = opts || {};
  const dur = opts.dur || 950, dec = opts.dec || 0, suffix = opts.suffix || '', t0 = performance.now();
  function step(t){
    const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    const v = target * e;
    el.textContent = (dec ? v.toFixed(dec) : fmt(Math.round(v))) + suffix;
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

/* ── SVG progress ring (returns markup; animates via CSS transition) ── */
function ringSVG(pct, size, color, label, sub){
  const r = (size - 10) / 2, circ = 2 * Math.PI * r;
  const off = circ * (1 - Math.max(0, Math.min(100, pct)) / 100);
  return `<div class="ring" style="width:${size}px;height:${size}px">
    <svg width="${size}" height="${size}">
      <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="var(--line2)" stroke-width="7"/>
      <circle class="ring-fg" cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="7"
        stroke-linecap="round" stroke-dasharray="${circ}" stroke-dashoffset="${circ}"
        style="--ring-off:${off}" transform="rotate(-90 ${size/2} ${size/2})"/>
    </svg>
    <div class="ring-c"><b>${label}</b>${sub?`<span>${sub}</span>`:''}</div>
  </div>`;
}
function armRings(scope){
  (scope||document).querySelectorAll('.ring-fg').forEach(c=>{
    requestAnimationFrame(()=>requestAnimationFrame(()=>{ c.style.strokeDashoffset = c.style.getPropertyValue('--ring-off'); }));
  });
}

/* ── toast ── */
function toast(msg){
  let t = document.querySelector('.toast');
  if(!t){ t = document.createElement('div'); t.className='toast'; document.body.appendChild(t); }
  t.textContent = msg; t.classList.add('show');
  clearTimeout(t._h); t._h = setTimeout(()=>t.classList.remove('show'), 2600);
}

/* ── CSV download ── */
function downloadCSV(filename, rows){
  const esc = v => { v = String(v == null ? '' : v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g,'""') + '"' : v; };
  const csv = rows.map(r => r.map(esc).join(',')).join('\r\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob(['﻿' + csv], {type:'text/csv;charset=utf-8'}));
  a.download = filename;
  document.body.appendChild(a); a.click();
  setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); }, 400);
  toast('Downloaded ' + filename);
}

/* status vocabulary shared by plan-driven pages */
const ST = {
  ok:     {cls:'b-low',  lab:'On Plan'},
  watch:  {cls:'b-med',  lab:'At Risk'},
  breach: {cls:'b-high', lab:'Breach'},
  idle:   {cls:'b-idle', lab:'Idle'},
};

/* ── topbar: tomorrow chip, live clock, theme toggle, download menu (app pages only) ── */
(function(){
  // ── global day selector (drives every plan view) ──
  const ds = document.getElementById('daysel');
  if (ds && typeof PLAN !== 'undefined'){
    const dot = document.getElementById('ds-dot'), lab = document.getElementById('ds-label');
    dot.className = 'ds-dot ' + PLAN.mode;
    lab.innerHTML = PLAN.isPlan ? `<i class="t1">T+1</i> Tomorrow · ${PLAN.dateShort}`
                  : PLAN.isLive ? `LIVE · Today` : `Actual · ${PLAN.dateShort}`;
    const list = document.getElementById('daysel-list');
    list.innerHTML = PLAN.days().map(o=>{
      const on = o.off===PLAN.offset;
      const tag = o.tag ? `<span class="ds-tag ${o.mode}">${o.tag}</span>` : '';
      return `<button class="daysel-item ${on?'on':''}" data-off="${o.off}">
        <span class="ds-mk ${o.mode}"></span>
        <span class="ds-tx"><b>${o.label}</b><span>${o.sub}</span></span>${tag}</button>`;
    }).join('');
    const btn = document.getElementById('daysel-btn');
    btn.onclick = e => { e.stopPropagation(); ds.classList.toggle('open'); };
    document.addEventListener('click', ()=>ds.classList.remove('open'));
    list.querySelectorAll('.daysel-item').forEach(b=> b.onclick = ()=>PLAN.select(+b.dataset.off));
  }
  const ck = document.getElementById('top-clock');
  if (ck){ const tick = ()=> ck.textContent = new Date().toLocaleTimeString('en-GB'); tick(); setInterval(tick, 1000); }

  // theme toggle
  const tb = document.getElementById('theme-toggle');
  if (tb){
    const sun  = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>';
    const moon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"/></svg>';
    tb.innerHTML = THEME==='dark' ? sun : moon;   // show the theme you'll switch TO
    tb.title = THEME==='dark' ? 'Switch to light' : 'Switch to dark';
    tb.onclick = ()=>{ try{ localStorage.setItem('pod-theme', THEME==='dark'?'light':'dark'); }catch(e){} location.reload(); };
  }

  const dl = document.getElementById('dl-menu');
  if (dl){
    const btn = dl.querySelector('.dl-btn');
    btn.onclick = e => { e.stopPropagation(); dl.classList.toggle('open'); };
    document.addEventListener('click', ()=>dl.classList.remove('open'));
    const rep = document.getElementById('dl-report');
    const csv = document.getElementById('dl-csv');
    if (rep) rep.onclick = ()=>{ window.open('/report','_blank'); dl.classList.remove('open'); };
    if (csv) csv.onclick = ()=>{ planCSV(); dl.classList.remove('open'); };
  }
})();
