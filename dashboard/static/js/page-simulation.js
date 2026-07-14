/* What-If Simulation — two views:
   ① Scenario Studio (advanced): real-world scenarios (rain, events, airside works, fog,
      festival, screening directive, staff shortage) + custom builder. Scenarios stack and
      transform the selected day's baseline plan (PLAN) → full-day before/after impact,
      per-touchpoint table and auto-recommendations.
   ② Factor Simulation (WI-01…05): the original per-hour engine — threshold, available
      units, zone closures — unchanged.
   Generic scenario effect: {tps, from, to, up %, shift min, proc %, cap %}. */
(function(){

  /* ═══════════ view switching (lazy init so hidden canvases render correctly) ═══════════ */
  const seg = document.getElementById('sim-view');
  const views = {studio:document.getElementById('view-studio'), factors:document.getElementById('view-factors')};
  const inited = {studio:false, factors:false};
  function show(v){
    Object.entries(views).forEach(([k,el])=>el.style.display = k===v?'':'none');
    seg.querySelectorAll('button').forEach(b=>b.classList.toggle('on', b.dataset.v===v));
    if(!inited[v]){ inited[v]=true; (v==='studio'?initStudio:initFactors)(); }
  }
  seg.onclick = e => { const b=e.target.closest('button'); if(b) show(b.dataset.v); };

  /* ═════════════════════════ ① SCENARIO STUDIO ═════════════════════════ */
  const DEP = ['Entry Gates','Check-In','Security (PESC)'];
  const ARR = ['Immigration','Customs','Transfers'];
  const PRESETS = [
    {id:'rain', icon:'🌧', color:'#38bdf8', name:'Heavy Rain / Monsoon',
     desc:'Traffic slows — passengers bunch into the peak; wet processing runs slower.',
     tps:DEP, from:16, to:22, up:12, shift:30, proc:10, cap:0},
    {id:'event', icon:'🏏', color:'#fbbf24', name:'Stadium Event — Cricket Match',
     desc:'Post-match exodus — fans fly out together in a tight evening wave.',
     tps:DEP, from:17, to:22, up:22, shift:0, proc:0, cap:0},
    {id:'works', icon:'🚧', color:'#f97316', name:'Airside Works — Stands Closed',
     desc:'Remote stands & bussing — arrival banks cluster and slip later.',
     tps:ARR, from:6, to:23, up:8, shift:45, proc:5, cap:0},
    {id:'fog', icon:'🌫', color:'#a78bfa', name:'Fog / ATC Flow Control',
     desc:'The morning bank slips, then recovers in a compressed surge.',
     tps:'all', from:5, to:12, up:15, shift:90, proc:0, cap:0},
    {id:'festival', icon:'🎆', color:'#fb7185', name:'Festival Peak Day',
     desc:'Holiday demand uplift across the entire operating day.',
     tps:'all', from:0, to:23, up:18, shift:0, proc:0, cap:0},
    {id:'screen', icon:'🛂', color:'#2dd4bf', name:'Enhanced Screening Directive',
     desc:'Regulator-mandated secondary checks slow every security lane.',
     tps:['Security (PESC)','Transfers'], from:0, to:23, up:0, shift:0, proc:30, cap:0},
    {id:'shortage', icon:'🤒', color:'#f87171', name:'Staff Shortage',
     desc:'Sick calls — a share of positions cannot be manned today.',
     tps:'all', from:0, to:23, up:0, shift:0, proc:0, cap:20},
  ];
  const active = new Map();          // id -> {int, from, to} (presets) | full fx (custom/saved)
  let stChart = null, stTp = 'ALL';

  function loadSaved(){ try{ return JSON.parse(localStorage.getItem('pod-scenarios')||'[]'); }catch(e){ return []; } }
  function storeSaved(list){ try{ localStorage.setItem('pod-scenarios', JSON.stringify(list)); }catch(e){} }

  function effectiveFx(){
    const out = [];
    active.forEach((p, id)=>{
      if (id==='custom' || id.startsWith('saved-')){ out.push(p); return; }
      const b = PRESETS.find(x=>x.id===id); if(!b) return;
      const k = (p.int||100)/100;
      out.push({tps:b.tps, from:p.from, to:p.to, up:b.up*k, shift:b.shift*k, proc:b.proc*k, cap:Math.min(60,b.cap*k), name:b.name});
    });
    return out;
  }
  const applies = (fx,n) => fx.tps==='all' || fx.tps.includes(n);

  /* transform one touchpoint's baseline through the active scenario stack */
  function scenarioTp(n){
    const t = PLAN.tps[n];
    let pax = t.hours.map(x=>x.pax);
    let ptM = 1, capCut = 0, shiftMin = 0, touched = false;
    effectiveFx().forEach(fx=>{
      if(!applies(fx,n)) return; touched = true;
      pax = pax.map((v,h)=> (h>=fx.from && h<=fx.to) ? v*(1+fx.up/100) : v);
      shiftMin += fx.shift||0; ptM *= 1+(fx.proc||0)/100; capCut = Math.min(.9, capCut+(fx.cap||0)/100);
    });
    const s = Math.max(-3, Math.min(3, shiftMin/60));
    if (s){ const f=Math.abs(s)%1, w=Math.trunc(Math.abs(s)), dir=s>0?1:-1, src=pax.slice(), out=new Array(24).fill(0);
      for(let h=0;h<24;h++){ const a=h+dir*w, b=h+dir*(w+1);
        if(a>=0&&a<24) out[a]+=src[h]*(1-f); if(b>=0&&b<24) out[b]+=src[h]*f; }
      pax = out; }
    pax = pax.map(v=>Math.round(v));
    const cap2 = Math.max(1, Math.round(t.cap*(1-capCut)));
    const pt2 = t.pt*ptM;
    const hours = pax.map((P,h)=>{
      const eff = Math.round(P*t.share);
      const req = eff>0 ? Math.max(1, Math.ceil((eff/12)*pt2/t.band.acc)) : 0;
      const open = Math.min(req, cap2);
      const wait = open>0 ? Math.ceil((eff/12)*pt2/open) : 0;
      const short = Math.max(0, req-cap2);
      const status = open===0 ? 'idle' : wait<=t.band.acc ? 'ok' : wait<=t.band.high ? 'watch' : 'breach';
      return {h, pax:P, req, open, wait, short, status};
    });
    return {t, hours, cap2, touched};
  }
  const breachHrs = hrs => hrs.filter(x=>x.status==='watch'||x.status==='breach').length;
  const peakOf = hrs => hrs.reduce((b,x,i)=>x.pax>hrs[b].pax?i:b,0);

  function fxTags(b,k){
    const parts=[];
    if(b.up) parts.push('demand +'+Math.round(b.up*k)+'%');
    if(b.shift) parts.push('shift '+(b.shift*k>0?'+':'')+Math.round(b.shift*k)+'m');
    if(b.proc) parts.push('processing +'+Math.round(b.proc*k)+'%');
    if(b.cap) parts.push('capacity −'+Math.round(Math.min(60,b.cap*k))+'%');
    parts.push(b.tps==='all'?'all touchpoints':b.tps.length+' touchpoints');
    return parts.map(x=>`<span class="tag t-blue" style="font-size:9px">${x}</span>`).join(' ');
  }
  function fxSummary(sv){
    const parts=[];
    if(sv.up) parts.push((sv.up>0?'+':'')+sv.up+'% demand');
    if(sv.shift) parts.push((sv.shift>0?'+':'')+sv.shift+'m shift');
    if(sv.proc) parts.push('+'+sv.proc+'% proc');
    if(sv.cap) parts.push('−'+sv.cap+'% cap');
    return (sv.tps==='all'?'all':''+sv.tps.length)+' tp · '+PLAN.hh(sv.from)+'–'+PLAN.hh(sv.to)+' · '+parts.join(' · ');
  }

  function renderLibrary(){
    const host = document.getElementById('scn-list');
    host.innerHTML = PRESETS.map(p=>{
      const on = active.has(p.id); const st = on ? active.get(p.id) : null;
      return `<div class="scn ${on?'on':''}" data-id="${p.id}">
        <div class="scn-h" data-act="toggle">
          <span class="scn-ic" style="background:${p.color}22;color:${p.color}">${p.icon}</span>
          <div class="scn-t"><b>${p.name}</b><span>${p.desc}</span></div>
          <span class="sw ${on?'on':''}"></span>
        </div>
        ${on?`<div class="scn-body">
          <div class="sl-row" style="margin-bottom:10px"><label>Intensity <b>${st.int}%</b></label>
            <input type="range" data-p="int" min="50" max="200" step="10" value="${st.int}"></div>
          <div class="grid g2" style="gap:8px">
            <div class="sl-row" style="margin-bottom:4px"><label>From <b>${PLAN.hh(st.from)}</b></label><input type="range" data-p="from" min="0" max="23" value="${st.from}"></div>
            <div class="sl-row" style="margin-bottom:4px"><label>To <b>${PLAN.hh(st.to)}</b></label><input type="range" data-p="to" min="0" max="23" value="${st.to}"></div>
          </div>
          <div class="scn-fx">${fxTags(p, st.int/100)}</div>
        </div>`:''}
      </div>`;
    }).join('');
    const saved = loadSaved();
    document.getElementById('scn-saved').innerHTML = saved.map(sv=>{
      const id='saved-'+sv.ts, on=active.has(id);
      return `<div class="scn ${on?'on':''}" data-id="${id}">
        <div class="scn-h" data-act="toggle">
          <span class="scn-ic" style="background:rgba(167,139,250,.16);color:var(--violet)">★</span>
          <div class="scn-t"><b>${sv.name}</b><span>${fxSummary(sv)}</span></div>
          <button class="scn-del" data-act="del" title="Delete">✕</button>
          <span class="sw ${on?'on':''}"></span>
        </div></div>`;
    }).join('');
    wireLibrary();
  }

  function wireLibrary(){
    document.querySelectorAll('#scn-list .scn, #scn-saved .scn').forEach(card=>{
      const id = card.dataset.id;
      const head = card.querySelector('[data-act="toggle"]');
      if (head) head.onclick = e => {
        if (e.target.closest('[data-act="del"]')){
          storeSaved(loadSaved().filter(sv=>'saved-'+sv.ts!==id));
          active.delete(id); renderLibrary(); runStudio(); return;
        }
        if (active.has(id)) active.delete(id);
        else if (id.startsWith('saved-')){ const sv = loadSaved().find(s=>'saved-'+s.ts===id); if(sv) active.set(id, sv); }
        else { const b=PRESETS.find(x=>x.id===id); active.set(id, {int:100, from:b.from, to:b.to}); }
        renderLibrary(); runStudio();
      };
      card.querySelectorAll('input[type=range]').forEach(sl=>{
        sl.oninput = ()=>{ const st=active.get(id); if(!st) return;
          st[sl.dataset.p] = +sl.value;
          if(st.from>st.to){ if(sl.dataset.p==='from') st.to=st.from; else st.from=st.to; }
          const lb = sl.closest('.sl-row').querySelector('label b');
          lb.textContent = sl.dataset.p==='int' ? st[sl.dataset.p]+'%' : PLAN.hh(st[sl.dataset.p]);
          const b=PRESETS.find(x=>x.id===id);
          const fxt=card.querySelector('.scn-fx'); if(fxt&&b) fxt.innerHTML=fxTags(b, st.int/100);
          runStudio(); };
        sl.onclick = e=>e.stopPropagation();
      });
    });
  }

  /* custom builder */
  function initCustom(){
    const body=document.getElementById('scn-custom-body');
    document.getElementById('scn-custom-toggle').onclick = ()=> body.style.display = body.style.display==='none'?'':'none';
    const tpSel=document.getElementById('cs-tps');
    tpSel.innerHTML = '<option value="ALL">All touchpoints</option><option value="DEP">Departures (Entry · Check-In · Security)</option><option value="ARR">Arrivals (Immigration · Customs · Transfers)</option>'
      + PLAN.names.map(n=>`<option value="${n}">${n}</option>`).join('');
    const bind=(id,fmt)=>{ const el=document.getElementById(id); const v=document.getElementById(id+'-v');
      el.oninput=()=>v.textContent=fmt(+el.value); };
    bind('cs-from',v=>PLAN.hh(v)); bind('cs-to',v=>PLAN.hh(v));
    bind('cs-up',v=>(v>0?'+':'')+v+'%'); bind('cs-sh',v=>(v>0?'+':'')+v+' min');
    bind('cs-pr',v=>'+'+v+'%'); bind('cs-cap',v=>'−'+v+'%');
    tpSel.onchange=()=>document.getElementById('cs-tps-v').textContent = tpSel.options[tpSel.selectedIndex].text.split(' (')[0];
    function readFx(){
      const s=tpSel.value;
      const tps = s==='ALL'?'all' : s==='DEP'?DEP : s==='ARR'?ARR : [s];
      const fx = { name:(document.getElementById('cs-name').value.trim()||'Custom scenario'), tps,
        from:+document.getElementById('cs-from').value, to:+document.getElementById('cs-to').value,
        up:+document.getElementById('cs-up').value, shift:+document.getElementById('cs-sh').value,
        proc:+document.getElementById('cs-pr').value, cap:+document.getElementById('cs-cap').value };
      if (fx.from>fx.to){ const t=fx.from; fx.from=fx.to; fx.to=t; }
      return fx;
    }
    document.getElementById('cs-apply').onclick=()=>{ const fx=readFx(); active.set('custom', fx);
      renderStack(); runStudio(); toast('Applied: '+fx.name); };
    document.getElementById('cs-save').onclick=()=>{ const fx=readFx(); fx.ts=Date.now();
      const saved=loadSaved(); saved.push(fx); storeSaved(saved); renderLibrary(); toast('Saved to library: '+fx.name); };
  }

  function renderStack(){
    const n = active.size;
    document.getElementById('scn-count').textContent = n ? n+' scenario'+(n>1?'s':'')+' active — effects stack' : 'No scenarios active';
  }

  /* run + render impact */
  function runStudio(){
    renderStack();
    const res = {}; PLAN.names.forEach(n=>res[n]=scenarioTp(n));
    const any = active.size>0;

    const baseTotal = PLAN.hourlyTotal;
    const scnTotal = Array.from({length:24},(_,h)=>PLAN.names.reduce((a,n)=>a+res[n].hours[h].pax,0));
    const bPeak=Math.max(...baseTotal), sPeak=Math.max(...scnTotal);
    const bWait=Math.max(...PLAN.names.map(n=>PLAN.tps[n].peak.wait));
    const sWait=Math.max(...PLAN.names.map(n=>Math.max(...res[n].hours.map(x=>x.wait))));
    const bBr=PLAN.names.reduce((a,n)=>a+breachHrs(PLAN.tps[n].hours),0);
    const sBr=PLAN.names.reduce((a,n)=>a+breachHrs(res[n].hours),0);
    const dUnits=PLAN.names.reduce((a,n)=>a + (res[n].hours[peakOf(res[n].hours)].open - PLAN.tps[n].peak.open),0);
    const dStaff=PLAN.names.reduce((a,n)=>a + (res[n].hours[peakOf(res[n].hours)].open - PLAN.tps[n].peak.open)*PLAN.tps[n].staffU*3,0);
    const arrow=(b,a)=> a===b ? '<span class="dim">→</span>' : `<span style="color:${a>b?'var(--red)':'var(--green)'}">→</span>`;
    document.getElementById('st-kpis').innerHTML = [
      ['Peak Demand', fmt(bPeak)+' '+arrow(bPeak,sPeak)+' <b>'+fmt(sPeak)+'</b>', 'pax/hr across airport', sPeak>bPeak*1.02?'accent':''],
      ['Worst Peak Wait', bWait+'m '+arrow(bWait,sWait)+' <b>'+sWait+'m</b>', 'any touchpoint', ''],
      ['Risk Hours', bBr+' '+arrow(bBr,sBr)+' <b>'+sBr+'</b>', 'touchpoint-hours above target', ''],
      ['Extra @ Peak', (dUnits>=0?'+':'')+dUnits+' units · '+(dStaff>=0?'+':'')+dStaff+' staff', 'vs baseline plan', ''],
    ].map(([l,v,s,a])=>`<div class="mini ${a}"><div class="mini-lab">${l}</div><div class="mini-val" style="font-size:16.5px">${v}</div><div class="mini-sub">${s}</div></div>`).join('');

    const base = stTp==='ALL' ? baseTotal : PLAN.tps[stTp].hours.map(x=>x.pax);
    const scn  = stTp==='ALL' ? scnTotal  : res[stTp].hours.map(x=>x.pax);
    document.getElementById('st-chart-sub').textContent = (stTp==='ALL'?'whole airport':stTp)+' · '+PLAN.dateShort+(any?' · scenario applied':' · no scenario active');
    if(stChart) stChart.destroy();
    stChart = areaChart(document.getElementById('st-chart'), HRS, [
      {label:'Baseline plan', data:base, color:C.blue},
      {label:'Scenario', data:scn, color:any?C.amber:C.blue2, fill:false, dash:any?[]:[4,4]},
    ]);

    document.getElementById('st-tbl').innerHTML =
      '<thead><tr><th>Touchpoint</th><th class="num">Peak PAX</th><th class="num">Peak Wait</th><th class="num">Risk Hours</th><th class="num">Units @ Peak</th><th class="ctr">Result</th></tr></thead><tbody>'+
      PLAN.names.map(n=>{ const t=PLAN.tps[n], r=res[n];
        const pB=t.peak.pax, pA=Math.max(...r.hours.map(x=>x.pax));
        const wB=t.peak.wait, wA=Math.max(...r.hours.map(x=>x.wait));
        const brB=breachHrs(t.hours), brA=breachHrs(r.hours);
        const uB=t.peak.open, uA=r.hours[peakOf(r.hours)].open;
        const worst = r.hours.some(x=>x.status==='breach')?'breach':r.hours.some(x=>x.status==='watch')?'watch':'ok';
        const lab = worst==='breach'?'Breach':worst==='watch'?'At Risk':'On Plan';
        const cls = worst==='breach'?'b-high':worst==='watch'?'b-med':'b-low';
        const cell=(b,a,suf)=> b===a ? `<span class="dim">${b}${suf||''}</span>` : `${b}${suf||''} <b style="color:${a>b?'var(--red)':'var(--green)'}">→ ${a}${suf||''}</b>`;
        return `<tr style="${r.touched?'':'opacity:.55'}"><td><b>${n}</b>${r.touched?'':' <span class="dim" style="font-size:9px">unaffected</span>'}</td>
          <td class="num">${cell(fmt(pB),fmt(pA))}</td><td class="num">${cell(wB,wA,'m')}</td>
          <td class="num">${cell(brB,brA)}</td><td class="num">${cell(uB,uA)}</td>
          <td class="ctr"><span class="bdg ${cls}">${lab}</span></td></tr>`; }).join('')+'</tbody>';

    const recs=[];
    PLAN.names.forEach(n=>{ const t=PLAN.tps[n], r=res[n]; if(!r.touched) return;
      let w=null; const wins=[];
      r.hours.forEach(x=>{ const risky=x.status==='watch'||x.status==='breach';
        if(risky){ if(!w) w={from:x.h,to:x.h,maxW:x.wait,maxS:x.short}; else{ w.to=x.h; w.maxW=Math.max(w.maxW,x.wait); w.maxS=Math.max(w.maxS,x.short);} }
        else if(w){ wins.push(w); w=null; } });
      if(w) wins.push(w);
      wins.forEach(win=>{ const sev = win.maxW>t.band.high?'high':'med';
        recs.push({sev, tp:n, window:PLAN.hh(win.from)+'–'+PLAN.hh(win.to+1),
          msg:`Scenario pushes wait to ${win.maxW}m (target ${t.band.acc}m)${win.maxS?` and demand ${win.maxS} ${PLAN.unitLow(t.unit)} above the usable ceiling`:''}.`,
          act: win.maxS>0 ? `Open every usable ${PLAN.unitOne(t.unit)}, pre-process upstream and stagger entry through ${PLAN.hh(win.to+1)} — capacity cannot absorb this alone.`
                          : `Deploy up to ${Math.max(...r.hours.map(x=>x.open))} ${PLAN.unitLow(t.unit)} (baseline peak ${t.peak.open}) before ${PLAN.hh(win.from)}.`}); });
    });
    recs.sort((a,b)=>(b.sev==='high')-(a.sev==='high'));
    const icoWarn='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
    document.getElementById('st-recs').innerHTML = !any
      ? '<div class="fill-note" style="margin:0;padding:14px;border:1px dashed var(--line2);border-radius:10px">Toggle a scenario (or build a custom one) to see its impact and the recommended response.</div>'
      : recs.length ? recs.slice(0,6).map(r=>`<div class="act sev-${r.sev}"><div class="ic">${icoWarn}</div><div class="bd">
          <div class="t">${r.tp}<span class="tag ${r.sev==='high'?'t-red':'t-amber'}">${r.sev==='high'?'BREACH':'AT RISK'}</span><span class="win">${r.window}</span></div>
          <div class="m">${r.msg}</div><div class="a">→ ${r.act}</div></div></div>`).join('')
      : '<div class="fill-note" style="margin:0;padding:14px;border:1px dashed var(--line2);border-radius:10px">✅ The plan absorbs this scenario — every touchpoint stays within SLA at planned deployment.</div>';

    document.getElementById('st-csv').onclick = ()=>{
      const rows=[['Touchpoint','Hour','Baseline PAX','Scenario PAX','Baseline Open','Scenario Open','Baseline Wait','Scenario Wait','Scenario Status']];
      PLAN.names.forEach(n=>{ const t=PLAN.tps[n], r=res[n];
        t.hours.forEach((x,h)=>rows.push([n,PLAN.hh(h),x.pax,r.hours[h].pax,x.open,r.hours[h].open,x.wait,r.hours[h].wait,r.hours[h].status.toUpperCase()])); });
      downloadCSV('POD_Scenario_'+PLAN.dateISO+'.csv', rows);
    };
  }

  function initStudio(){
    const sel=document.getElementById('st-tp');
    sel.innerHTML = '<option value="ALL">All touchpoints</option>'+PLAN.names.map(n=>`<option>${n}</option>`).join('');
    sel.onchange = ()=>{ stTp=sel.value; runStudio(); };
    document.getElementById('scn-clear').onclick = ()=>{ active.clear(); renderLibrary(); runStudio(); };
    initCustom(); renderLibrary(); runStudio();
  }

  /* ═════════════════════════ ② FACTOR SIMULATION (original WI-01…05) ═════════════════════════ */
  function initFactors(){
    const sel = document.getElementById('s-tp');
    const TPS_SIM = Object.keys(MOCK.resource);
    sel.innerHTML = TPS_SIM.map(t=>`<option>${t}</option>`).join('');

    const thrEl = document.getElementById('s-thr'), resEl = document.getElementById('s-res'), hourEl = document.getElementById('s-hour');
    const closed = new Set();
    let chart, cur = TPS_SIM[0], mapView = 'wait';

    const peakHourOf = r => r.pax.indexOf(Math.max(...r.pax));
    const hhmm = h => String(h).padStart(2,'0')+':00';

    function openShares(r, closedSet){
      const zones = r.zones.map(z=>({name:z[0], share:z[1]}));
      const open = zones.filter(z=>!closedSet.has(z.name));
      const closedShare = zones.filter(z=>closedSet.has(z.name)).reduce((a,z)=>a+z.share,0);
      const add = open.length ? closedShare/open.length : 0;
      return open.map(z=>({name:z.name, baseShare:z.share, share:z.share+add, redistributed:add>0}));
    }

    function compute(tp, thr, availTotal, closedSet, hour){
      const r = MOCK.resource[tp];
      const P = r.pax[hour];
      const open = openShares(r, closedSet);
      const perZoneAvail = open.length ? Math.max(1, Math.floor(availTotal/open.length)) : 0;
      const rows = open.map(z=>{
        const zPAX  = Math.round(P*z.share);
        const reqL  = Math.max(1, Math.ceil((zPAX/12)*r.pt/thr));
        const openL = perZoneAvail;
        const wait  = Math.ceil((zPAX/12)*r.pt/openL);
        return {zone:z.name, baseShare:z.baseShare, share:z.share, zPAX, reqL, openL, wait, breach:wait>thr, redistributed:z.redistributed};
      });
      return { r, P, hour, rows,
        totalReq: rows.reduce((a,x)=>a+x.reqL,0),
        totalOpen: rows.reduce((a,x)=>a+x.openL,0),
        maxWait: rows.length?Math.max(...rows.map(x=>x.wait)):0,
        anyBreach: rows.some(x=>x.breach) || open.length===0,
        closed: r.zones.filter(z=>closedSet.has(z[0])).map(z=>z[0]) };
    }
    const baseline = (tp, hour) => { const r=MOCK.resource[tp]; return compute(tp, r.thr, r.cap, new Set(), hour); };

    function defaults(tp){
      const r = MOCK.resource[tp];
      thrEl.value = r.thr;
      resEl.max = r.cap; resEl.value = r.cap;
      hourEl.value = peakHourOf(r);
      document.getElementById('s-res-unit').textContent = r.unit;
      closed.clear();
    }

    function renderZones(tp){
      const r = MOCK.resource[tp];
      document.getElementById('s-zones').innerHTML = r.zones.map(([z])=>`
        <label class="ck"><input type="checkbox" data-z="${z}" ${closed.has(z)?'checked':''}> ${z}
          ${closed.has(z)?'<span style="color:var(--red);font-size:9px">● Closed</span>':'<span style="color:var(--green);font-size:9px">● Open</span>'}</label>`).join('');
      document.querySelectorAll('#s-zones input').forEach(c=>c.onchange=()=>{ c.checked?closed.add(c.dataset.z):closed.delete(c.dataset.z); renderZones(tp); run(); });
    }

    function run(){
      const tp = cur, thr = +thrEl.value, avail = +resEl.value, hour = +hourEl.value;
      document.getElementById('s-thr-v').textContent = thr+' min';
      document.getElementById('s-res-v').textContent = avail;
      document.getElementById('s-hour-v').textContent = hhmm(hour);
      const sim = compute(tp, thr, avail, closed, hour);
      const base = baseline(tp, hour);
      const r = sim.r;

      document.getElementById('s-tp-label').textContent = tp+' · '+hhmm(hour)+' · '+fmt(sim.P)+' pax/hr';
      document.getElementById('s-area-label').textContent = '④ '+r.area+' Closures';
      document.getElementById('s-chart-sub').textContent = 'by '+r.area.toLowerCase()+' · at '+hhmm(hour);
      document.getElementById('s-hourmap-sub').textContent = (mapView==='proc'?'predicted processing time (s) per ':'predicted wait (min) per ')+r.area.toLowerCase()+', every hour · '+hhmm(hour)+' outlined';
      const st = document.getElementById('s-status');
      st.textContent = sim.anyBreach ? '⚠ SLA BREACH' : '✓ WITHIN SLA';
      st.className = 'bdg '+(sim.anyBreach?'b-high':'b-low'); st.style.padding='3px 12px';

      document.getElementById('s-results').innerHTML = [
        ['Required '+r.unit, sim.totalReq, ''],
        [r.unit+' Open', sim.totalOpen+' / '+r.cap, sim.totalOpen<sim.totalReq?'var(--amber)':'var(--green)'],
        ['Predicted Max Wait', sim.maxWait+' min', sim.anyBreach?'var(--red)':'var(--green)'],
        ['Open '+r.area+'s', (r.zones.length-sim.closed.length)+' / '+r.zones.length, sim.closed.length?'var(--amber)':''],
      ].map(([l,v,c])=>`<div class="mini"><div class="mini-lab">${l}</div><div class="mini-val" style="${c?'color:'+c:''}">${v}</div></div>`).join('');

      const allZones = r.zones.map(z=>z[0]);
      const beforeMap = {}; base.rows.forEach(x=>beforeMap[x.zone]=x.wait);
      const afterMap  = {}; sim.rows.forEach(x=>afterMap[x.zone]=x.wait);
      const before = allZones.map(z=>beforeMap[z]||0);
      const after  = allZones.map(z=> z in afterMap ? afterMap[z] : 0);
      const afterCols = allZones.map(z=> (afterMap[z]||0)>thr ? C.red : C.green);
      if(chart) chart.destroy();
      chart = new Chart(document.getElementById('s-chart'), { type:'bar',
        data:{ labels:allZones, datasets:[
          {label:'Before', data:before, backgroundColor:C.blue2+'88', borderRadius:3},
          {label:'After',  data:after,  backgroundColor:afterCols, borderRadius:3},
          {label:'Threshold', type:'line', data:allZones.map(()=>thr), borderColor:C.amber, borderWidth:1.5, borderDash:[5,3], pointRadius:0},
        ]},
        options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false},
          plugins:{ legend:{position:'top',labels:{boxWidth:9,boxHeight:9,borderRadius:4,useBorderRadius:true,padding:12,font:{size:10,weight:600}}}, tooltip:tt() },
          scales:{ x:{grid:{display:false},ticks:{font:{size:9.5}}},
            y:{beginAtZero:true,grid:{color:GRID},ticks:{font:{size:9.5},callback:v=>v+'m'},
               title:{display:true,text:'avg wait (min)',font:{size:9.5},color:'#8b9bbd'}} } }
      });

      renderHourMap(r, thr, avail, hour, mapView);
    }

    function renderHourMap(r, thr, avail, selHour, view){
      const open = openShares(r, closed);
      const perZoneAvail = open.length ? Math.max(1, Math.floor(avail/open.length)) : 0;
      const peak = Math.max(...r.pax);
      const procSLA = Math.round(r.pt*60);
      const proc = view==='proc';
      const sla = proc ? procSLA : thr;
      const col = v => v<=sla ? '#22c55e' : v<=sla*1.5 ? '#f59e0b' : '#ef4444';
      let h = '<table class="hm"><thead><tr><th></th>'+
        Array.from({length:24},(_,i)=>`<th style="${i===selHour?'color:var(--blue2);font-weight:800':''}">${String(i).padStart(2,'0')}</th>`).join('')+'</tr></thead><tbody>';
      open.forEach((z,zi)=>{
        h += `<tr><td class="lbl">${z.name}</td>`+
          Array.from({length:24},(_,i)=>{
            const hh = String(i).padStart(2,'0');
            const zPAX = Math.round(r.pax[i]*z.share);
            let v, tip;
            if(proc){
              const lr = peak>0 ? r.pax[i]/peak : 0;
              v = Math.round(procSLA*(0.9 + 0.5*lr)*(1 + ((zi%3)-1)*0.06));
              tip = `${z.name} ${hh}:00 · ${v}s processing (SLA ${procSLA}s)`;
            } else {
              v = Math.ceil((zPAX/12)*r.pt/perZoneAvail);
              const reqL = Math.max(1, Math.ceil((zPAX/12)*r.pt/thr));
              tip = `${z.name} ${hh}:00 · ${zPAX} pax · req ${reqL} ${r.unit.toLowerCase()} / open ${perZoneAvail} · ${v}m wait (SLA ${thr}m)`;
            }
            const selStyle = i===selHour ? 'outline:2px solid #5b8def;outline-offset:-2px;' : '';
            return `<td class="c" style="background:${col(v)};${selStyle}" title="${tip}">${v}</td>`;
          }).join('')+'</tr>';
      });
      r.zones.filter(z=>closed.has(z[0])).forEach(z=>{
        h += `<tr style="opacity:.4"><td class="lbl">${z[0]}</td>`+
          Array.from({length:24},()=>'<td class="c" style="background:var(--panel3)">·</td>').join('')+'</tr>';
      });
      document.getElementById('s-hourmap').innerHTML = h + '</tbody></table>';
    }

    function selectTP(tp){ cur=tp; defaults(tp); renderZones(tp); run(); }
    sel.onchange = ()=>selectTP(sel.value);
    thrEl.addEventListener('input', run);
    resEl.addEventListener('input', run);
    hourEl.addEventListener('input', run);
    document.getElementById('s-map-view').onclick = ev => { const b=ev.target.closest('button'); if(!b)return;
      mapView=b.dataset.v; document.querySelectorAll('#s-map-view button').forEach(x=>x.classList.toggle('on',x===b)); run(); };
    document.getElementById('s-reset').onclick = ()=>selectTP(cur);
    selectTP(cur);
  }

  /* boot */
  show('studio');
})();
