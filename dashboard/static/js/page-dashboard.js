/* Command Center — time-aware. Tomorrow = plan · Today = live streaming · past = actual vs predicted.
   Everything derives from PLAN (plan.js), which already carries predicted + actual per hour. */
(function(){
  const E = MOCK.exec;
  const TPCOL = { 'Entry Gates':C.blue, 'Check-In':C.blue2, 'Security (PESC)':C.violet, 'Emigration':C.teal,
    'Immigration':C.green, 'Customs':C.amber, 'Transfers':C.rose };
  const showActual = PLAN.isLive || PLAN.hasActual;
  let shown = PLAN.completedHours;                 // revealed hours (plan=0, history=24, live=liveHour)
  let lpChart, pulseChart, lpView = 'day', timer = null;

  const slice = (arr) => arr.map((v,i)=> i<shown ? v : null);
  const RING_R = 41, RING_C = 2*Math.PI*RING_R;
  function statsOver(s){ let ps=0,as=0,me=0,n=0;
    PLAN.names.forEach(nm=>PLAN.tps[nm].hours.forEach(x=>{ if(x.h<s && x.pax>0){ ps+=x.pax; as+=x.actFull; me+=Math.abs(x.pax-x.actFull)/x.pax; n++; }}));
    return {predSum:ps, actSum:as, acc:n?Math.max(60,Math.min(99.9,100-(me/n)*100)):null}; }
  function accTp(tp,s){ const kn=tp.hours.filter(x=>x.h<s && x.pax>0); if(!kn.length) return null;
    const m=kn.reduce((a,x)=>a+Math.abs(x.pax-x.actFull)/x.pax,0)/kn.length; return Math.max(60,Math.min(99.9,100-m*100)); }
  const accColor = a => a>=95?C.green : a>=90?C.teal : a>=85?C.amber : C.red;

  /* ── HERO ── */
  function heroStat(l,v,s,id,big){ return `<div class="hstat"><div class="l">${l}</div><div class="v ${big?'gtxt':''}" ${id?`id="${id}"`:''}>${v}</div><div class="s" ${id?`id="${id}-s"`:''}>${s}</div></div>`; }
  function ringStat(pct,label,color,sub){ const off=RING_C*(1-Math.max(0,Math.min(100,pct))/100);
    return `<div class="hstat" style="display:flex;align-items:center;justify-content:center;min-width:112px">
      <div class="ring" style="width:92px;height:92px"><svg width="92" height="92">
        <circle cx="46" cy="46" r="${RING_R}" fill="none" stroke="var(--line2)" stroke-width="7"/>
        <circle class="ring-fg" id="hero-ring" cx="46" cy="46" r="${RING_R}" fill="none" stroke="${color}" stroke-width="7" stroke-linecap="round" stroke-dasharray="${RING_C}" stroke-dashoffset="${RING_C}" style="--ring-off:${off}" transform="rotate(-90 46 46)"/></svg>
      <div class="ring-c"><b id="hero-ring-v">${label}</b><span>${sub||'ready'}</span></div></div></div>`; }

  function renderHero(){
    const s = statsOver(shown);
    document.getElementById('h-kicker').textContent = PLAN.isPlan ? 'Plan of the Day · Next operating day'
      : PLAN.isLive ? 'Plan of the Day · Live — today' : 'Plan of the Day · Actual vs predicted';
    document.getElementById('h-title').innerHTML = (PLAN.isPlan?'Tomorrow — ':PLAN.isLive?'Today — ':'')+`<span class="gtxt">${PLAN.dateLong}</span>`;
    document.getElementById('h-sub').textContent = PLAN.isPlan
      ? 'Predictions, resources and risk windows for the full operating day — ready to distribute to the ground team.'
      : PLAN.isLive ? 'Live actuals streaming in against the plan POD published yesterday — watch prediction meet reality, hour by hour.'
      : 'How POD predicted this day versus what actually happened — verify the forecast touchpoint by touchpoint.';

    const box = document.getElementById('hero-stats');
    if (PLAN.isPlan){
      box.innerHTML = ringStat(PLAN.readiness,'', accColor(PLAN.readiness), 'plan ready')
        + heroStat('Terminal Passengers', fmt(PLAN.dayPaxTotal), 'across all flights','hs-pax',true)
        + heroStat('Flights', fmt(MOCK.flightDay.total), MOCK.flightDay.dep+' dep · '+MOCK.flightDay.arr+' arr')
        + heroStat('Peak Hour', PLAN.hh(PLAN.peakHour), 'busiest across touchpoints')
        + heroStat('Risk Windows', PLAN.actions.length, 'need ground-team action')
        + heroStat('Staff to Roster', fmt(PLAN.staffTotal), 'peak units × 3 shifts');
      document.getElementById('hero-ring-v').textContent = PLAN.readiness+'%';
      if(document.getElementById('hs-pax')) countUp(document.getElementById('hs-pax'), PLAN.dayPaxTotal);
    } else {
      const acc = s.acc!=null ? s.acc : 0;
      const actNow = s.predSum ? Math.round(PLAN.dayPaxTotal*(s.actSum/s.predSum)) : 0;
      box.innerHTML = ringStat(Math.round(acc),'',accColor(acc), PLAN.isLive?'live accuracy':'accuracy')
        + heroStat('Predicted PAX', fmt(PLAN.dayPaxTotal), PLAN.isLive?'forecast for today':'forecast','hs-pred',true)
        + heroStat('Actual PAX', actNow?fmt(actNow):'—', PLAN.isLive?('through '+PLAN.hh(shown)):'realized','hs-act')
        + heroStat('Peak Hour', PLAN.hh(PLAN.peakHour), 'busiest')
        + (PLAN.isLive ? heroStat('Hours Complete', shown+' / 24', 'live','hs-hrs')
                       : heroStat('Flights', fmt(MOCK.flightDay.total), 'that day'));
      document.getElementById('hero-ring-v').textContent = (acc?acc.toFixed(1):'—')+'%';
    }
    requestAnimationFrame(()=>requestAnimationFrame(()=>{ const rf=document.getElementById('hero-ring'); if(rf) rf.style.strokeDashoffset = rf.style.getPropertyValue('--ring-off'); }));
  }
  function updateHeroLive(){
    const s = statsOver(shown), acc = s.acc||0;
    const rf=document.getElementById('hero-ring'); if(rf) rf.style.strokeDashoffset = RING_C*(1-acc/100);
    const rv=document.getElementById('hero-ring-v'); if(rv) rv.textContent = acc.toFixed(1)+'%';
    const act=document.getElementById('hs-act'); if(act){ const a=s.predSum?Math.round(PLAN.dayPaxTotal*(s.actSum/s.predSum)):0; act.textContent=a?fmt(a):'—'; }
    const as=document.getElementById('hs-act-s'); if(as) as.textContent='through '+PLAN.hh(shown);
    const hr=document.getElementById('hs-hrs'); if(hr) hr.textContent=shown+' / 24';
  }

  /* ── DAY PANEL (mode-specific) ── */
  const icoWarn = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
  function renderDayPanel(){
    const p = document.getElementById('daypanel');
    if (PLAN.isPlan) return renderActionQueue(p);
    if (PLAN.isPast) return renderReview(p);
    return renderLive(p);
  }

  function renderActionQueue(p){
    p.innerHTML = `<div class="panel"><div class="panel-h"><h2>⚡ Tomorrow's Action Queue <span class="sub">auto-generated from the plan — where the day needs intervention, worst first</span></h2>
      <button class="btn btn-ghost" id="aq-report" style="padding:6px 13px;font-size:11px">Open in report →</button></div>
      <div class="panel-b"><div class="acts" id="actions"></div></div></div>`;
    document.getElementById('actions').innerHTML = PLAN.actions.length ? PLAN.actions.map(a=>`
      <div class="act sev-${a.sev}"><div class="ic">${icoWarn}</div><div class="bd">
        <div class="t">${a.tp}<span class="tag ${a.sev==='high'?'t-red':'t-amber'}">${a.kind}</span><span class="win">${a.window}</span></div>
        <div class="m">${a.msg}</div><div class="a">→ ${a.act}</div></div></div>`).join('')
      : '<div class="fill-note" style="margin:0;padding:14px;border:1px dashed var(--line2);border-radius:10px">✅ No risk windows — tomorrow\'s demand is servable within SLA at planned deployment across all touchpoints.</div>';
    document.getElementById('aq-report').onclick = ()=>window.open('/report','_blank');
  }

  function renderReview(p){
    const s = statsOver(24);
    const rows = PLAN.names.map(n=>{ const t=PLAN.tps[n];
      return {n, acc:t.accDay, pred:t.dayPax, act:t.dayAct}; });
    const best = rows.reduce((a,b)=>b.acc>a.acc?b:a), tight = rows.reduce((a,b)=>b.acc<a.acc?b:a);
    p.innerHTML = `<div class="panel"><div class="panel-h"><h2>Prediction vs Actual — Review <span class="sub">how POD's forecast held up on ${PLAN.dateLong}</span></h2>
      <button class="btn btn-primary" id="rev-report" style="padding:6px 14px;font-size:11px">Full report →</button></div>
      <div class="panel-b">
        <div class="grid g4" style="margin-bottom:14px">
          <div class="mini accent"><div class="mini-lab">Day Accuracy</div><div class="mini-val" style="color:${accColor(s.acc)}">${s.acc.toFixed(1)}%</div><div class="mini-sub">hourly, all touchpoints</div></div>
          <div class="mini"><div class="mini-lab">Predicted PAX</div><div class="mini-val">${fmt(PLAN.dayPaxTotal)}</div><div class="mini-sub">forecast</div></div>
          <div class="mini"><div class="mini-lab">Actual PAX</div><div class="mini-val">${fmt(PLAN.dayActTotal)}</div><div class="mini-sub">${((PLAN.dayActTotal-PLAN.dayPaxTotal)/PLAN.dayPaxTotal*100>=0?'+':'')}${((PLAN.dayActTotal-PLAN.dayPaxTotal)/PLAN.dayPaxTotal*100).toFixed(1)}% vs forecast</div></div>
          <div class="mini"><div class="mini-lab">Best / Tightest</div><div class="mini-val" style="font-size:13px">${best.n.split(' ')[0]} · ${tight.n.split(' ')[0]}</div><div class="mini-sub">${best.acc.toFixed(1)}% / ${tight.acc.toFixed(1)}%</div></div>
        </div>
        <div style="overflow-x:auto"><table class="tbl">
          <thead><tr><th>Touchpoint</th><th class="num">Predicted</th><th class="num">Actual</th><th class="num">Δ</th><th class="num">Accuracy</th><th class="ctr">Grade</th></tr></thead>
          <tbody>${rows.map(r=>{ const d=((r.act-r.pred)/r.pred*100); const g=r.acc>=95?'On Plan':r.acc>=90?'Close':'Off'; const gc=r.acc>=95?'b-low':r.acc>=90?'b-med':'b-high';
            return `<tr><td><b>${r.n}</b></td><td class="num">${fmt(r.pred)}</td><td class="num">${fmt(r.act)}</td>
              <td class="num" style="color:${Math.abs(d)<=5?'var(--green)':Math.abs(d)<=12?'var(--amber)':'var(--red)'}">${d>=0?'+':''}${d.toFixed(1)}%</td>
              <td class="num" style="font-weight:800;color:${accColor(r.acc)}">${r.acc.toFixed(1)}%</td>
              <td class="ctr"><span class="bdg ${gc}">${g}</span></td></tr>`; }).join('')}</tbody>
        </table></div>
      </div></div>`;
    document.getElementById('rev-report').onclick = ()=>window.open('/report','_blank');
  }

  function feedRow(h){ const pr=PLAN.hourlyTotal[h], ac=PLAN.hourlyActual[h]; const acc=pr?100-Math.abs(pr-ac)/pr*100:0;
    return `<div class="feed-row"><span class="feed-h">${PLAN.hh(h)}</span><span class="feed-m">actual <b>${fmt(ac)}</b> vs pred ${fmt(pr)}</span><span class="feed-a" style="color:${accColor(acc)}">${acc.toFixed(1)}%</span></div>`; }

  function renderLive(p){
    p.innerHTML = `<div class="panel"><div class="panel-h"><h2><span class="live-dot" style="display:inline-block;margin-right:6px"></span>Live Console <span class="sub">today · streaming actuals against yesterday's plan</span></h2>
      <div style="display:flex;gap:8px;align-items:center">
        <button class="btn btn-primary" id="live-play" style="padding:6px 14px;font-size:11px">▶ Play day</button>
        <button class="btn btn-ghost" id="live-reset" style="padding:6px 12px;font-size:11px">Reset to now</button></div></div>
      <div class="panel-b">
        <div class="grid g4" id="live-kpis" style="margin-bottom:12px"></div>
        <div class="liveprog"><div class="liveprog-bar" id="live-bar"></div></div>
        <div class="liveprog-lab" id="live-lab"></div>
        <div class="grid g2" style="gap:16px;margin-top:14px;align-items:start">
          <div><div class="mini-lab" style="margin-bottom:8px">LIVE FEED · hour completions</div><div class="feed" id="live-feed"></div></div>
          <div><div class="mini-lab" style="margin-bottom:8px">NEXT RISK WINDOW</div><div id="live-next"></div></div>
        </div>
      </div></div>`;
    document.getElementById('live-play').onclick = toggleLive;
    document.getElementById('live-reset').onclick = ()=>{ stopLive(); shown = Math.max(1, new Date().getHours()); PLAN.persistLive(shown); refreshCharts(); refreshBoard(); updateHeroLive(); refreshLive(); };
    refreshLive();
  }
  function refreshLive(){
    if(!PLAN.isLive) return;
    const s = statsOver(shown);
    const kp = document.getElementById('live-kpis');
    if(kp) kp.innerHTML = [
      ['Hours Complete', shown+' / 24', PLAN.hh(shown)+' now', 'accent'],
      ['Predicted (so far)', fmt(s.predSum), 'across touchpoints',''],
      ['Actual (so far)', fmt(s.actSum), ((s.actSum-s.predSum)/(s.predSum||1)*100>=0?'+':'')+((s.actSum-s.predSum)/(s.predSum||1)*100).toFixed(1)+'% vs pred',''],
      ['Running Accuracy', (s.acc!=null?s.acc.toFixed(1):'—')+'%', 'hourly, live', ''],
    ].map(([l,v,su,a])=>`<div class="mini ${a}"><div class="mini-lab">${l}</div><div class="mini-val" style="font-size:18px">${v}</div><div class="mini-sub">${su}</div></div>`).join('');
    const bar=document.getElementById('live-bar'); if(bar) bar.style.width=(shown/24*100)+'%';
    const lab=document.getElementById('live-lab'); if(lab) lab.textContent = shown>=24 ? '✓ Operating day complete — full actual vs predicted above and below.' : `Streaming… ${shown} of 24 hours posted. Press Play to fast-forward the day.`;
    const feed=document.getElementById('live-feed'); if(feed) feed.innerHTML = shown ? Array.from({length:shown},(_,i)=>shown-1-i).map(feedRow).join('') : '<div class="fill-note" style="margin:0">Waiting for the first hour to post…</div>';
    const nx=document.getElementById('live-next'); if(nx){ const up=PLAN.actions.find(a=>a.to>=shown);
      nx.innerHTML = up ? `<div class="act sev-${up.sev}" style="margin:0"><div class="ic">${icoWarn}</div><div class="bd"><div class="t">${up.tp}<span class="tag ${up.sev==='high'?'t-red':'t-amber'}">${up.kind}</span><span class="win">${up.window}</span></div><div class="m">${up.msg}</div><div class="a">→ ${up.act}</div></div></div>`
        : '<div class="fill-note" style="margin:0;padding:14px;border:1px dashed var(--line2);border-radius:10px">No further risk windows today — the rest of the day is within SLA at planned deployment.</div>'; }
    const pb=document.getElementById('live-play'); if(pb && shown>=24 && !timer) pb.textContent='▶ Replay day';
  }
  function tickLive(){ if(shown>=24){ stopLive(); refreshLive(); return; }
    shown++; PLAN.persistLive(shown); refreshCharts(); refreshBoard(); updateHeroLive(); refreshLive();
    if(shown<=24) toast(PLAN.hh(shown-1)+' posted · '+fmt(PLAN.hourlyActual[shown-1])+' pax actual'); }
  function toggleLive(){ const b=document.getElementById('live-play');
    if(timer){ stopLive(); } else { if(shown>=24){ shown=0; refreshCharts(); refreshBoard(); updateHeroLive(); } b.textContent='⏸ Pause'; timer=setInterval(tickLive,1100); } }
  function stopLive(){ if(timer){ clearInterval(timer); timer=null; } const b=document.getElementById('live-play'); if(b) b.textContent = shown>=24?'▶ Replay day':'▶ Play day'; }

  /* ── Touchpoint board ── */
  function boardCard(n,i){
    const t=PLAN.tps[n];
    const chipS = t.windows.length ? (t.windows.some(w=>w.worst==='breach')?ST.breach:ST.watch) : ST.ok;
    const shortMax = Math.max(0, ...t.windows.map(w=>w.maxShort));
    let foot2;
    if (showActual){ const a=accTp(t,shown);
      foot2 = `<span>Acc <b id="bacc-${i}" style="color:${a?accColor(a):'inherit'}">${a?a.toFixed(1)+'%':'—'}</b></span><span>Day <b>${fmt(t.dayPax)}</b> pred</span>`;
    } else {
      foot2 = `<span>Day <b>${fmt(t.dayPax)}</b> pax</span><span>Peak wait <b style="color:${t.peak.wait<=t.band.acc?'var(--green)':t.peak.wait<=t.band.high?'var(--amber)':'var(--red)'}">${t.peak.wait}m</b> / ${t.band.acc}m</span>`;
    }
    return `<a class="tp-card" href="/touchpoints?tp=${encodeURIComponent(n)}">
      ${(!showActual && shortMax>0)?`<span class="short tag t-red">−${shortMax} ${PLAN.unitLow(t.unit)}</span>`:''}
      <div class="hd"><span class="nm">${n}</span><span class="bdg ${chipS.cls}">${chipS.lab}</span></div>
      <div class="sp"><canvas id="sp-${i}"></canvas></div>
      <div class="ft"><span>Peak <b>${PLAN.hh(t.peakH)}</b> · <b>${fmt(t.peak.pax)}</b> pax</span><span>Open <b>${t.peak.open}/${t.cap}</b> ${PLAN.unitLow(t.unit)}</span></div>
      <div class="ft" style="margin-top:5px">${foot2}</div></a>`;
  }
  function renderBoard(){
    document.getElementById('board').innerHTML = PLAN.names.map((n,i)=>boardCard(n,i)).join('');
    PLAN.names.forEach((n,i)=>spark(document.getElementById('sp-'+i), PLAN.tps[n].hours.map(x=>x.pax), TPCOL[n]||C.blue));
    const risky = PLAN.names.filter(n=>PLAN.tps[n].windows.length).length;
    document.getElementById('board-sum').textContent = showActual ? PLAN.names.length+' touchpoints · actual vs predicted' : (PLAN.names.length-risky)+' on plan · '+risky+' with risk windows';
  }
  function refreshBoard(){ PLAN.names.forEach((n,i)=>{ const el=document.getElementById('bacc-'+i); if(el){ const a=accTp(PLAN.tps[n],shown); el.textContent=a?a.toFixed(1)+'%':'—'; el.style.color=a?accColor(a):'inherit'; } }); }

  /* ── Load prediction chart ── */
  function lpDatasets(){
    const e30 = a => a.flatMap(v=> v==null?[null,null]:[Math.round(v*0.52),Math.round(v*0.48)]);
    const entry=PLAN.tps['Entry Gates'].hours.map(x=>x.pax), trans=PLAN.tps['Transfers'].hours.map(x=>x.pax);
    const entryA=slice(PLAN.tps['Entry Gates'].hours.map(x=>x.actFull)), transA=slice(PLAN.tps['Transfers'].hours.map(x=>x.actFull));
    const conv = a => lpView==='hour' ? e30(a) : a;
    const ds = [ {label:'Entry — predicted', data:conv(entry), color:C.blue}, {label:'Transfers — predicted', data:conv(trans), color:C.violet} ];
    if (showActual){ ds.push({label:'Entry — actual', data:conv(entryA), color:C.blue2, fill:false, dash:[5,4]});
      ds.push({label:'Transfers — actual', data:conv(transA), color:C.rose, fill:false, dash:[5,4]}); }
    return ds;
  }
  function drawLP(){
    const cv=document.getElementById('lp-chart'); if(lpChart) lpChart.destroy();
    const labels = lpView==='hour' ? Array.from({length:48},(_,s)=> s%4===0?`${String(Math.floor(s/2)).padStart(2,'0')}:${s%2?'30':'00'}`:'') : HRS;
    lpChart = areaChart(cv, labels, lpDatasets());
    lpChart.data.datasets.forEach(d=>{ d.spanGaps=false; }); lpChart.update('none');
  }

  /* ── Airport pulse ── */
  function drawPulse(){
    const cv=document.getElementById('pulse'); if(pulseChart) pulseChart.destroy();
    const datasets = [{label:'Predicted — all touchpoints', data:PLAN.hourlyTotal, borderColor:C.blue2, borderWidth:2.6,
      backgroundColor:grad(cv.getContext('2d'),C.blue,250), fill:true, tension:.42, pointRadius:0, pointHoverRadius:5, spanGaps:false}];
    if (showActual){ datasets.push({label:'Actual', data:slice(PLAN.hourlyActual), borderColor:C.green, borderWidth:2.8, fill:false, tension:.42, pointRadius:0, pointHoverRadius:5, borderDash:[6,3], spanGaps:false}); }
    else { PLAN.names.forEach(n=>datasets.push({label:n, data:PLAN.tps[n].hours.map(x=>x.pax), borderColor:(TPCOL[n]||C.teal)+'aa', borderWidth:1.4, fill:false, tension:.42, pointRadius:0, pointHoverRadius:4})); }
    pulseChart = new Chart(cv, { type:'line', data:{labels:HRS, datasets},
      options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false},
        plugins:{ legend:{position:'top',labels:{boxWidth:9,boxHeight:9,borderRadius:4,useBorderRadius:true,padding:12,font:{size:10,weight:600}}}, tooltip:tt() },
        scales:{ x:{grid:{display:false},ticks:{maxRotation:0,autoSkip:true,maxTicksLimit:12,font:{size:9.5}}},
          y:{beginAtZero:true,grid:{color:GRID},ticks:{font:{size:9.5},callback:v=>v>=1000?(v/1000).toFixed(1)+'k':v}} } } });
  }
  function refreshCharts(){
    if(lpChart){ const ds=lpDatasets(); lpChart.data.datasets.forEach((d,i)=>{ if(ds[i]) d.data=ds[i].data; }); lpChart.update('none'); }
    if(pulseChart){ const a=pulseChart.data.datasets.find(d=>d.label==='Actual'); if(a){ a.data=slice(PLAN.hourlyActual); pulseChart.update('none'); } }
  }

  /* ── heatmap ── */
  const PROC_KEY = {'Security (PESC)':'Security'};
  function buildHM(view){
    let h='<table class="hm"><thead><tr><th></th>'+HRS.map((_,i)=>`<th>${String(i).padStart(2,'0')}</th>`).join('')+'</tr></thead><tbody>';
    PLAN.names.forEach(n=>{ const t=PLAN.tps[n]; let cells;
      if(view==='proc'){ const arr=MOCK.hmProc[PROC_KEY[n]||n]||[]; const sla=(MOCK.sla[PROC_KEY[n]||n]||{proc:30}).proc;
        cells=arr.map((v,i)=>{ const col=v<=sla?'#22c55e':v<=sla*1.5?'#f59e0b':'#ef4444'; return `<td class="c" style="background:${col}" title="${n} ${PLAN.hh(i)} · ${v}s (SLA ${sla}s)">${v}</td>`; }).join('');
      } else { cells=t.hours.map(x=>{ const col=x.status==='idle'?'var(--panel3)':x.wait<=t.band.acc?'#22c55e':x.wait<=t.band.high?'#f59e0b':'#ef4444';
          return `<td class="c" style="background:${col};${x.status==='idle'?'color:var(--dim)':''}" title="${n} ${PLAN.hh(x.h)} · ${x.wait}m at ${x.open} ${PLAN.unitLow(t.unit)} (target ${t.band.acc}m)">${x.status==='idle'?'·':x.wait}</td>`; }).join(''); }
      h+=`<tr><td class="lbl">${n}</td>${cells}</tr>`; });
    document.getElementById('hm').innerHTML=h+'</tbody></table>';
    document.getElementById('hm-note').textContent = view==='proc'?'seconds per passenger · SLA per touchpoint':'minutes at planned deployment · targets: Entry 3m · Check-In 8m · others 5m';
  }

  /* ── staff + segments ── */
  function renderStaff(){
    const rows = PLAN.names.map(n=>{ const t=PLAN.tps[n]; return {tp:n,unit:t.unit,dayPax:t.dayPax,units:t.peak.open,cap:t.cap,staffU:t.staffU,people:t.staff}; });
    const totUnits=rows.reduce((a,x)=>a+x.units,0), totPeople=rows.reduce((a,x)=>a+x.people,0);
    document.getElementById('peak-staff').textContent = fmt(totPeople)+' / day';
    document.getElementById('res-model').innerHTML =
      '<thead><tr><th>Touchpoint</th><th>Unit</th><th class="num">PAX / Day</th><th class="num">Units @ Peak</th><th class="num">Staff / Unit</th><th class="num">People (3 shifts)</th></tr></thead><tbody>'+
      rows.map(x=>`<tr><td><b>${x.tp}</b></td><td><span class="tag t-blue">${x.unit}</span></td><td class="num">${fmt(x.dayPax)}</td><td class="num"><b>${x.units}</b> <span class="dim">/ ${x.cap}</span></td><td class="num">${x.staffU}</td><td class="num" style="color:var(--blue2);font-weight:800">${fmt(x.people)}</td></tr>`).join('')+
      `<tr style="border-top:2px solid var(--line2);background:rgba(120,150,255,.04)"><td><b>Total</b></td><td></td><td></td><td class="num"><b>${totUnits}</b></td><td></td><td class="num" style="color:var(--blue2);font-weight:800;font-size:14px">${fmt(totPeople)}</td></tr></tbody>`;
    document.getElementById('staff-csv').onclick = ()=>downloadCSV('POD_StaffPlan_'+PLAN.dateISO+'.csv',
      [['Touchpoint','Unit','PAX/Day','Units @ Peak','Capacity','Staff/Unit','People (3 shifts)'], ...rows.map(x=>[x.tp,x.unit,x.dayPax,x.units,x.cap,x.staffU,x.people]),['TOTAL','','',totUnits,'','',totPeople]]);
  }
  function renderSegments(){
    document.getElementById('seg-cards').innerHTML = Object.entries(E.segments).map(([nm,sg])=>`
      <div class="mini" style="flex:1;border-left:3px solid ${sg.color}"><div style="display:flex;justify-content:space-between;align-items:center"><span class="mini-lab" style="color:${sg.color}">${nm}</span><b class="mono" style="font-size:13px">${sg.pct}%</b></div>
        <div class="mini-val" style="font-size:20px">${fmt(sg.pax)}</div><div class="mini-sub">${sg.flights} flights · avg wait ${sg.wait}m</div></div>`).join('');
    new Chart(document.getElementById('seg-chart'), { type:'bar',
      data:{ labels:HRS, datasets:[{label:'International', data:E.segHourly.intl, backgroundColor:C.amber+'cc', borderRadius:3, stack:'s'},{label:'Domestic', data:E.segHourly.dom, backgroundColor:C.teal+'cc', borderRadius:3, stack:'s'}]},
      options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false},
        plugins:{legend:{position:'top',labels:{boxWidth:9,boxHeight:9,borderRadius:4,useBorderRadius:true,padding:12,font:{size:10,weight:600}}},tooltip:tt()},
        scales:{x:{stacked:true,grid:{display:false},ticks:{maxRotation:0,autoSkip:true,maxTicksLimit:12,font:{size:9}}},y:{stacked:true,beginAtZero:true,grid:{color:GRID},ticks:{font:{size:9},callback:v=>v>=1000?(v/1000).toFixed(1)+'k':v}}} } });
    const ad=E.arrDep, tr=E.transfers, trTotal=Object.values(tr).reduce((a,b)=>a+b,0);
    document.getElementById('flow-split').innerHTML = `
      <div class="mini"><div class="mini-lab">Departures</div><div class="mini-val" style="font-size:18px;color:var(--blue2)">${fmt(ad.departures)}</div></div>
      <div class="mini"><div class="mini-lab">Arrivals</div><div class="mini-val" style="font-size:18px;color:var(--teal)">${fmt(ad.arrivals)}</div></div>
      <div class="mini" style="grid-column:1/-1"><div class="mini-lab">Transfers · ${fmt(trTotal)} total</div>
        ${Object.entries(tr).map(([k,v])=>`<div style="margin-top:8px"><div style="display:flex;justify-content:space-between;font-size:10.5px;margin-bottom:4px"><span class="muted">${k}</span><b class="mono">${fmt(v)}</b></div><div style="height:6px;background:var(--panel3);border-radius:4px;overflow:hidden"><div style="height:100%;width:${(v/trTotal*100).toFixed(1)}%;background:linear-gradient(90deg,var(--violet),var(--blue));border-radius:4px"></div></div></div>`).join('')}</div>`;
  }

  /* ── page copy + init ── */
  document.getElementById('lp-title').textContent = showActual ? 'Load — Predicted vs Actual' : 'Load Prediction';
  document.getElementById('lp-sub').textContent = 'Entry Gates & Transfers'+(PLAN.isLive?' · live':'');
  document.getElementById('pulse-title').textContent = showActual ? 'Airport Pulse — Predicted vs Actual' : 'Airport Pulse';
  document.getElementById('pulse-sub').textContent = showActual ? 'total demand · forecast vs realized' : 'total processing demand across all touchpoints · legend toggles';

  renderHero();
  renderDayPanel();
  renderBoard();
  drawLP();
  document.getElementById('lp-seg').onclick = ev => { const b=ev.target.closest('button'); if(!b)return; document.querySelectorAll('#lp-seg button').forEach(x=>x.classList.toggle('on',x===b)); lpView=b.dataset.v; drawLP(); };
  buildHM('wait');
  document.getElementById('hm-seg').onclick = ev => { const b=ev.target.closest('button'); if(!b)return; document.querySelectorAll('#hm-seg button').forEach(x=>x.classList.toggle('on',x===b)); buildHM(b.dataset.v); };
  drawPulse();
  renderStaff();
  renderSegments();
})();
