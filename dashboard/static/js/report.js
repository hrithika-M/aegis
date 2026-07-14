/* POD — print-ready report. Time-aware: Plan (tomorrow) · Live (today) · Actual vs Predicted (past). */
(function(){
  const q = new URLSearchParams(location.search);
  const scopeTP = q.get('tp') && PLAN.tps[q.get('tp')] ? q.get('tp') : null;
  const names = scopeTP ? [scopeTP] : PLAN.names;
  const genAt = new Date().toLocaleString('en-GB', {day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
  const showActual = PLAN.isLive || PLAN.hasActual;
  const modeTitle = PLAN.isPast ? 'Actual vs Predicted' : PLAN.isLive ? 'Live Operations' : 'Plan of the Day';

  document.getElementById('bar-scope').textContent = (scopeTP ? scopeTP+' — ' : '') + modeTitle + (scopeTP?'':' · full day');
  document.getElementById('b-print').onclick = ()=>window.print();
  document.getElementById('b-csv').onclick = ()=>planCSV(scopeTP || undefined);

  const PILL = {ok:'<span class="pill p-ok">ON PLAN</span>', watch:'<span class="pill p-watch">AT RISK</span>',
                breach:'<span class="pill p-breach">BREACH</span>', idle:'<span class="pill p-idle">IDLE</span>'};

  /* pure-SVG 24h chart — predicted (area) + actual (dashed) for print */
  function svgLoad(t){
    const W=830,H=150,PL=34,PB=22,PT=8;
    const data=t.hours.map(x=>x.pax), act=t.hours.map(x=>x.known?x.actFull:null);
    const mx=Math.max(...data,1);
    const x=i=>PL+i*(W-PL-6)/23, y=v=>PT+(H-PT-PB)*(1-v/mx);
    const pts=data.map((v,i)=>`${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
    const area=`${PL},${H-PB} ${pts} ${x(23).toFixed(1)},${H-PB}`;
    const peakI=data.indexOf(Math.max(...data));
    const actPts=act.map((v,i)=>v==null?null:`${x(i).toFixed(1)},${y(v).toFixed(1)}`).filter(Boolean).join(' ');
    const gid='g-'+t.name.replace(/[^\w]/g,'');
    const ticks=[0,3,6,9,12,15,18,21,23].map(h=>`<text x="${x(h)}" y="${H-6}" font-size="7.5" fill="#8b9bbd" text-anchor="middle">${String(h).padStart(2,'0')}</text>`).join('');
    const gy=[0.25,0.5,0.75,1].map(f=>{ const yy=y(mx*f);
      return `<line x1="${PL}" y1="${yy}" x2="${W-6}" y2="${yy}" stroke="#e6ecf7" stroke-width="1"/><text x="${PL-4}" y="${yy+2.5}" font-size="7" fill="#8b9bbd" text-anchor="end">${mx*f>=1000?(mx*f/1000).toFixed(1)+'k':Math.round(mx*f)}</text>`; }).join('');
    return `<div class="svgwrap"><svg viewBox="0 0 ${W} ${H}" width="100%" preserveAspectRatio="xMidYMid meet">
        <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2563eb" stop-opacity=".26"/><stop offset="1" stop-color="#2563eb" stop-opacity=".02"/></linearGradient></defs>
        ${gy}<polygon points="${area}" fill="url(#${gid})"/>
        <polyline points="${pts}" fill="none" stroke="#2563eb" stroke-width="2" stroke-linejoin="round"/>
        ${actPts?`<polyline points="${actPts}" fill="none" stroke="#059669" stroke-width="2" stroke-dasharray="5 4" stroke-linejoin="round"/>`:''}
        <circle cx="${x(peakI)}" cy="${y(data[peakI])}" r="3.4" fill="#7c3aed"/>
        <text x="${Math.min(x(peakI),W-90)}" y="${Math.max(y(data[peakI])-7,10)}" font-size="8.5" font-weight="700" fill="#7c3aed">peak ${PLAN.hh(peakI)} · ${fmt(data[peakI])}</text>
        ${ticks}</svg>
      <div class="svgcap">Passengers per hour — ${t.name}, ${PLAN.dateLong}${showActual?' · <b style="color:#2563eb">predicted</b> vs <b style="color:#059669">actual</b>':''}</div></div>`;
  }

  function row(x){
    const cls=x.status==='breach'?'hl-breach':x.status==='watch'?'hl-watch':'';
    let a='';
    if(showActual){ if(x.known && x.pax){ const v=(x.actFull-x.pax)/x.pax*100;
        a=`<td class="num">${fmt(x.actFull)}</td><td class="num">${v>=0?'+':''}${v.toFixed(0)}%</td>`; }
      else a='<td class="num">—</td><td class="num">—</td>'; }
    return `<tr class="${cls}"><td class="num" style="text-align:left;font-family:'JetBrains Mono'">${PLAN.hh(x.h)}</td>
      <td class="num">${x.pax?fmt(x.pax):'—'}</td>${a}<td class="num">${x.req||'—'}</td><td class="num"><b>${x.open||'—'}</b></td>
      <td class="num">${x.wait?x.wait+'m':'—'}</td><td class="ctr">${PILL[x.status]||''}</td></tr>`;
  }
  const HEAD = `<tr><th>Hour</th><th class="num">Pred</th>${showActual?'<th class="num">Actual</th><th class="num">Var</th>':''}<th class="num">Req</th><th class="num">Open</th><th class="num">Wait</th><th class="ctr">Status</th></tr>`;

  function tpSection(n,i){
    const t=PLAN.tps[n]; const shortMax=Math.max(0,...t.windows.map(w=>w.maxShort),0);
    const zones=t.zones||[]; const perZone=Math.max(1,Math.floor(t.peak.open/Math.max(zones.length,1)));
    const windowsTxt=t.windows.length? t.windows.map(w=>`<b>${PLAN.hh(w.from)}–${PLAN.hh(w.to+1)}</b> — wait up to ${w.maxWait}m${w.maxShort?` (${w.maxShort} ${PLAN.unitLow(t.unit)} short)`:''}`).join(' · ')
      : 'No risk windows — every hour servable within the SLA target at planned deployment.';
    const acts=PLAN.actions.filter(a=>a.tp===n);
    const accStat = showActual ? `<div class="stat"><div class="l">Accuracy</div><div class="v">${t.accDay!=null?t.accDay.toFixed(1)+'%':'—'}</div><div class="s">pred vs actual</div></div>` : `<div class="stat"><div class="l">Staff (3 shifts)</div><div class="v">${t.staff}</div><div class="s">${t.staffU}/unit</div></div>`;
    const actStat = showActual ? `<div class="stat"><div class="l">Actual PAX</div><div class="v">${t.dayAct?fmt(t.dayAct):'—'}</div><div class="s">${t.dayAct?((t.dayAct-t.dayPax)/t.dayPax*100>=0?'+':'')+((t.dayAct-t.dayPax)/t.dayPax*100).toFixed(1)+'%':'realized'}</div></div>` : `<div class="stat"><div class="l">${t.unit} @ Peak</div><div class="v">${t.peak.open}/${t.cap}</div><div class="s">${shortMax?shortMax+' short':'within capacity'}</div></div>`;
    return `<div class="tpsec ${(!scopeTP && i>0)?'pb':''}">
      <div class="tphead"><h3>${n}</h3><div class="u">${t.unit} · capacity ${t.cap} · SLA ${t.band.acc}m (high ${t.band.high}m) · processing ${Math.round(t.pt*60)}s/pax</div></div>
      <div class="tpstats">
        <div class="stat"><div class="l">Predicted PAX</div><div class="v">${fmt(t.dayPax)}</div><div class="s">forecast</div></div>
        ${actStat}
        <div class="stat"><div class="l">Peak Hour</div><div class="v">${PLAN.hh(t.peakH)}</div><div class="s">${fmt(t.peak.pax)} pax</div></div>
        <div class="stat"><div class="l">Peak Wait</div><div class="v">${t.peak.wait}m</div><div class="s">target ${t.band.acc}m</div></div>
        ${accStat}
      </div>
      ${svgLoad(t)}
      <div class="cols2">
        <div><table><thead>${HEAD}</thead><tbody>${t.hours.slice(0,12).map(row).join('')}</tbody></table></div>
        <div><table><thead>${HEAD}</thead><tbody>${t.hours.slice(12).map(row).join('')}</tbody></table></div>
      </div>
      ${zones.length>1?`<div style="margin-top:12px"><table><thead><tr><th>${t.area}</th><th class="num">Share</th><th class="num">PAX @ Peak</th><th class="num">${t.unit}</th></tr></thead>
        <tbody>${zones.map(([z,s])=>`<tr><td>${z}</td><td class="num">${(s*100).toFixed(1)}%</td><td class="num">${fmt(Math.round(s*t.peak.pax*t.share))}</td><td class="num">${perZone}</td></tr>`).join('')}</tbody></table></div>`:''}
      <div class="note"><b>${showActual?'Notes.':'Ground-team notes.'}</b> ${windowsTxt}${acts.map(a=>`<br>→ <b>${a.window}</b>: ${a.act}`).join('')}</div>
    </div>`;
  }

  const scopeActs = PLAN.actions.filter(a=>!scopeTP || a.tp===scopeTP);
  const glanceTitle = PLAN.isPlan?'Tomorrow at a glance':PLAN.isLive?'Today (live) at a glance':'Day at a glance';
  const glance = showActual ? `
      <div class="stat"><div class="l">Predicted PAX</div><div class="v">${fmt(PLAN.dayPaxTotal)}</div><div class="s">${MOCK.flightDay.total} flights</div></div>
      <div class="stat"><div class="l">Actual PAX</div><div class="v">${PLAN.dayActTotal!=null?fmt(PLAN.dayActTotal):'—'}</div><div class="s">${PLAN.dayActTotal!=null?((PLAN.dayActTotal-PLAN.dayPaxTotal)/PLAN.dayPaxTotal*100>=0?'+':'')+((PLAN.dayActTotal-PLAN.dayPaxTotal)/PLAN.dayPaxTotal*100).toFixed(1)+'% vs forecast':''}</div></div>
      <div class="stat"><div class="l">Day Accuracy</div><div class="v">${PLAN.accDay!=null?PLAN.accDay.toFixed(1)+'%':'—'}</div><div class="s">hourly, all touchpoints</div></div>
      <div class="stat"><div class="l">Peak Hour</div><div class="v">${PLAN.hh(PLAN.peakHour)}</div><div class="s">across touchpoints</div></div>
      <div class="stat"><div class="l">${PLAN.isLive?'Hours Complete':'Units @ Peak'}</div><div class="v">${PLAN.isLive?PLAN.completedHours+' / 24':PLAN.unitsPeak}</div><div class="s">${PLAN.isLive?'posted':'all touchpoints'}</div></div>`
    : `
      <div class="stat"><div class="l">Terminal PAX</div><div class="v">${fmt(PLAN.dayPaxTotal)}</div><div class="s">${MOCK.flightDay.total} flights</div></div>
      <div class="stat"><div class="l">Peak Hour</div><div class="v">${PLAN.hh(PLAN.peakHour)}</div><div class="s">across touchpoints</div></div>
      <div class="stat"><div class="l">Units @ Peak</div><div class="v">${PLAN.unitsPeak}</div><div class="s">all touchpoints</div></div>
      <div class="stat"><div class="l">Staff to Roster</div><div class="v">${fmt(PLAN.staffTotal)}</div><div class="s">3 shifts</div></div>
      <div class="stat"><div class="l">Plan Readiness</div><div class="v">${PLAN.readiness}%</div><div class="s">hours within SLA</div></div>`;

  document.getElementById('paper').innerHTML = `
    <div class="mast"><div class="brand">
      <div class="lg"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg></div>
      <div><h1>${modeTitle} — ${scopeTP?scopeTP:'Operations Report'}</h1>
        <div class="sub">GMR Hyderabad International Airport · prepared by POD${showActual?' — actual vs predicted':' for the ground team'}</div>
        <div class="datebox">Operating day${PLAN.isPast?' (actual)':PLAN.isLive?' (live)':''}: ${PLAN.dateLong}</div></div>
    </div><div class="meta">Generated <b>${genAt}</b><br>Scope <b>${scopeTP?'1 touchpoint':names.length+' touchpoints + summary'}</b><br>Source <b>POD prediction engine</b> · Commercial-in-Confidence</div></div>

    <div class="sec"><h2>${glanceTitle} <span class="hint">whole airport</span></h2><div class="stats">${glance}</div></div>

    <div class="sec"><h2>${PLAN.isPast?'Where the plan flagged risk':'Actions for the ground team'} <span class="hint">${scopeActs.length?scopeActs.length+' window'+(scopeActs.length>1?'s':''):'no interventions needed'}</span></h2>
      ${scopeActs.length ? scopeActs.map(a=>`<div class="ract ${a.sev==='high'?'high':''}"><div class="w">${a.window}</div>
          <div><div class="t">${a.tp}<span class="rtag ${a.kind==='AT CEILING'?'ceil':'tight'}">${a.kind}</span></div><div class="m">${a.msg}</div><div class="a">→ ${a.act}</div></div></div>`).join('')
        : '<div class="note">✅ Predicted demand is servable within SLA at the planned deployment across '+(scopeTP?'this touchpoint':'all touchpoints')+'.</div>'}</div>

    <div class="sec"><h2>Service-level reference <span class="hint">wait-time targets &amp; capacity</span></h2>
      <table><thead><tr><th>Touchpoint</th><th class="num">Target</th><th class="num">High</th><th class="num">Capacity</th><th class="num">Processing</th>${showActual?'<th class="num">Accuracy</th>':'<th class="num">Plan @ Peak</th>'}<th class="ctr">${PLAN.isPast?'Result':'Status'}</th></tr></thead>
        <tbody>${names.map(n=>{ const t=PLAN.tps[n]; const st=t.windows.length?(t.windows.some(w=>w.worst==='breach')?'breach':'watch'):'ok';
          const lastCol = showActual ? `<td class="num">${t.accDay!=null?t.accDay.toFixed(1)+'%':'—'}</td>` : `<td class="num">${t.peak.open} ${PLAN.unitLow(t.unit)}</td>`;
          return `<tr><td><b>${n}</b></td><td class="num">${t.band.acc}m</td><td class="num">${t.band.high}m</td><td class="num">${t.cap} ${PLAN.unitLow(t.unit)}</td><td class="num">${Math.round(t.pt*60)}s</td>${lastCol}<td class="ctr">${PILL[st]}</td></tr>`; }).join('')}
        </tbody></table></div>

    ${names.map((n,i)=>tpSection(n,i)).join('')}

    <div class="rfoot"><span>POD · ${modeTitle} — generated ${genAt} · WAISL Data Science &amp; Engineering</span><span>Commercial-in-Confidence · distribute to rostered ground-team leads only</span></div>`;
})();
