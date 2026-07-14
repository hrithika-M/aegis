/* Touchpoint Plans — per-touchpoint, time-aware. Predicted plan + (past/live) actual vs predicted. */
(function(){
  let loadChart, unitsChart, cur;
  const TPCOL = { 'Entry Gates':C.blue, 'Check-In':C.blue2, 'Security (PESC)':C.violet, 'Emigration':C.teal,
    'Immigration':C.green, 'Customs':C.amber, 'Transfers':C.rose };
  const showActual = PLAN.isLive || PLAN.hasActual;
  const accColor = a => a>=95?'var(--green)' : a>=90?'var(--teal)' : a>=85?'var(--amber)' : 'var(--red)';
  document.getElementById('tp-date').textContent = (PLAN.isPlan?'plan for ':PLAN.isLive?'live · ':'actual · ') + PLAN.dateShort;

  const chips = document.getElementById('tp-chips');
  function chipDot(n){ const t=PLAN.tps[n]; if(showActual){ const a=t.accDay; return a==null?'var(--dim)':accColor(a); }
    if(!t.windows.length) return 'var(--green)'; return t.windows.some(w=>w.worst==='breach')?'var(--red)':'var(--amber)'; }
  chips.innerHTML = PLAN.names.map(n=>`<button class="chip" data-tp="${n}"><span class="dot" style="background:${chipDot(n)}"></span>${n}</button>`).join('');
  chips.onclick = e => { const b=e.target.closest('.chip'); if(!b) return; render(b.dataset.tp); };

  function render(name){
    cur = name; const t = PLAN.tps[name];
    chips.querySelectorAll('.chip').forEach(c=>c.classList.toggle('on', c.dataset.tp===name));

    /* ── KPI band ── */
    const shortMax = Math.max(0, ...t.windows.map(w=>w.maxShort), 0);
    const wCol = t.peak.wait<=t.band.acc?'var(--green)':t.peak.wait<=t.band.high?'var(--amber)':'var(--red)';
    let kpis;
    if (showActual){
      const dlt = t.dayAct && t.dayPax ? ((t.dayAct-t.dayPax)/t.dayPax*100) : 0;
      kpis = [
        {lab:'Predicted Load', val:fmt(t.dayPax), sub:'forecast', cu:t.dayPax},
        {lab:'Actual Load', val:t.dayAct?fmt(t.dayAct):'—', sub:(dlt>=0?'+':'')+dlt.toFixed(1)+'% vs forecast', style:'color:'+(Math.abs(dlt)<=5?'var(--green)':Math.abs(dlt)<=12?'var(--amber)':'var(--red)')},
        {lab:'Peak Hour', val:PLAN.hh(t.peakH), sub:fmt(t.peak.pax)+' pax predicted'},
        {lab:'Peak Wait (plan)', val:t.peak.wait+' min', sub:'target '+t.band.acc+'m', style:'color:'+wCol},
        {lab:PLAN.isLive?'Live Accuracy':'Day Accuracy', val:(t.accDay!=null?t.accDay.toFixed(1):'—')+'%', sub:PLAN.isLive?('through '+PLAN.hh(PLAN.completedHours)):'hourly, held-out', style:'color:'+(t.accDay!=null?accColor(t.accDay):'inherit')},
      ];
    } else {
      kpis = [
        {lab:'Predicted Load', val:fmt(t.dayPax), sub:'passengers tomorrow', cu:t.dayPax},
        {lab:'Peak Hour', val:PLAN.hh(t.peakH), sub:fmt(t.peak.pax)+' pax in the hour'},
        {lab:t.unit+' @ Peak', val:t.peak.open+' / '+t.cap, sub:shortMax>0?shortMax+' short of demand':'within capacity', style:shortMax>0?'color:var(--amber)':''},
        {lab:'Peak Wait', val:t.peak.wait+' min', sub:'target '+t.band.acc+'m · high '+t.band.high+'m', style:'color:'+wCol},
        {lab:'Model Accuracy', val:t.acc+'%', sub:'held-out validation'},
      ];
    }
    document.getElementById('tp-kpis').innerHTML = kpis.map((k,i)=>`<div class="mini">
      <div class="mini-lab">${k.lab}</div><div class="mini-val" ${k.style?`style="${k.style}"`:''} ${k.cu?`id="tpk-${i}"`:''}>${k.val}</div>
      <div class="mini-sub">${k.sub}</div></div>`).join('');
    const cuEl = document.getElementById('tpk-0'); if(cuEl) countUp(cuEl, t.dayPax);

    /* ── Load chart ── */
    const pax = t.hours.map(x=>x.pax);
    if(loadChart) loadChart.destroy();
    const series = [{label:'Predicted', data:pax, color:TPCOL[name]||C.blue}];
    if (showActual){ series.push({label:'Actual', data:t.hours.map(x=>x.known?x.actFull:null), color:C.green, fill:false, dash:[5,4]}); }
    loadChart = areaChart(document.getElementById('tp-load'), HRS, series, {allX:true});
    loadChart.data.datasets.forEach(d=>d.spanGaps=false); loadChart.update('none');

    /* ── Units to open ── */
    const openArr=t.hours.map(x=>x.open), reqArr=t.hours.map(x=>x.req);
    const cols=t.hours.map(x=> x.short>0?C.red+'d0':x.status==='watch'?C.amber+'d0':(TPCOL[name]||C.blue)+'aa');
    document.getElementById('tp-units-title').textContent = t.unit;
    document.getElementById('tp-units-sub').textContent = 'planned open (bars) vs demand-required (line) · capacity '+t.cap;
    if(unitsChart) unitsChart.destroy();
    unitsChart = new Chart(document.getElementById('tp-units'), { type:'bar',
      data:{ labels:HRS, datasets:[
        {label:'Planned open', data:openArr, backgroundColor:cols, borderRadius:4, order:3},
        {label:'Required by demand', type:'line', data:reqArr, borderColor:C.teal, borderWidth:2, borderDash:[5,3], pointRadius:0, tension:.25, order:1},
        {label:'Capacity ('+t.cap+')', type:'line', data:HRS.map(()=>t.cap), borderColor:C.red, borderWidth:1.4, borderDash:[2,3], pointRadius:0, tension:0, order:2} ]},
      options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false},
        plugins:{ legend:{position:'top',labels:{boxWidth:9,boxHeight:9,borderRadius:4,useBorderRadius:true,padding:14,font:{size:10.5,weight:600}}}, tooltip:tt() },
        scales:{ x:{grid:{display:false},ticks:{maxRotation:0,minRotation:0,autoSkip:false,font:{size:8.5}}},
          y:{beginAtZero:true,grid:{color:GRID},ticks:{font:{size:9.5},precision:0,callback:v=>Number.isInteger(v)?v:''}, title:{display:true,text:t.unit+' open',font:{size:9.5},color:'#8b9bbd'}} } } });

    /* ── Hourly table (Actual + Var when known) ── */
    const riskHrs = t.hours.filter(x=>x.status==='watch'||x.status==='breach').length;
    document.getElementById('tp-tbl-sum').textContent = showActual ? (PLAN.completedHours+' hours posted') : (riskHrs?riskHrs+' risk hours':'all hours on plan');
    const aCols = showActual ? '<th class="num">Actual</th><th class="num">Var</th>' : '';
    document.getElementById('tp-tbl').innerHTML =
      '<thead><tr><th>Hour</th><th class="num">Predicted</th>'+aCols+'<th class="num">Required</th><th class="num">Open</th><th class="num">Pred. Wait</th><th class="ctr">Status</th></tr></thead><tbody>'+
      t.hours.map(x=>{ const s=ST[x.status]||ST.ok; const rc=x.status==='breach'?'r-breach':x.status==='watch'?'r-watch':'';
        let actCells='';
        if(showActual){ if(x.known && x.pax){ const v=(x.actFull-x.pax)/x.pax*100;
            actCells=`<td class="num">${fmt(x.actFull)}</td><td class="num" style="color:${Math.abs(v)<=5?'var(--green)':Math.abs(v)<=12?'var(--amber)':'var(--red)'}">${v>=0?'+':''}${v.toFixed(0)}%</td>`; }
          else actCells='<td class="num dim">—</td><td class="num dim">—</td>'; }
        return `<tr class="${rc}"><td class="mono">${PLAN.hh(x.h)}</td><td class="num">${x.pax?fmt(x.pax):'—'}</td>${actCells}
          <td class="num">${x.req||'—'}${x.short>0?` <span class="tag t-red" style="font-size:9px">+${x.short}</span>`:''}</td>
          <td class="num"><b>${x.open||'—'}</b></td><td class="num">${x.wait?x.wait+'m':'—'}</td>
          <td class="ctr"><span class="bdg ${s.cls}">${s.lab}</span></td></tr>`; }).join('')+'</tbody>';

    /* ── Zones @ peak ── */
    const zones=t.zones||[]; const zoneCount=Math.max(zones.length,1); const perZone=Math.max(1,Math.floor(t.peak.open/zoneCount));
    document.getElementById('tp-zones-sub').textContent = zoneCount+' '+t.area.toLowerCase()+'s · peak '+fmt(t.peak.pax)+' pax at '+PLAN.hh(t.peakH)+' · ~'+perZone+' '+PLAN.unitLow(t.unit)+' / '+t.area.toLowerCase();
    document.getElementById('tp-zones').innerHTML =
      '<thead><tr><th>'+t.area+'</th><th class="num">Share</th><th class="num">PAX @ Peak</th><th class="num">'+t.unit+'</th><th class="num">Pred. Wait</th><th class="ctr">Status</th></tr></thead><tbody>'+
      zones.map(([zName,share],zi)=>{ const zPax=Math.round(share*t.peak.pax*t.share); const zPt=t.pt*(1+((zi%3)-1)*0.08);
        const wait=Math.max(1,Math.ceil((zPax/12)*zPt/perZone)); const cls=wait<=t.band.acc?'b-low':wait<=t.band.high?'b-med':'b-high'; const lab=wait<=t.band.acc?'On Plan':wait<=t.band.high?'At Risk':'Breach';
        return `<tr><td>${zName}</td><td class="num">${(share*100).toFixed(1)}%</td><td class="num">${fmt(zPax)}</td><td class="num">${perZone}</td><td class="num">${wait} min</td><td class="ctr"><span class="bdg ${cls}">${lab}</span></td></tr>`; }).join('')+'</tbody>';
  }

  document.getElementById('tp-csv').onclick = ()=>planCSV(cur);
  document.getElementById('tp-report').onclick = ()=>window.open('/report?tp='+encodeURIComponent(cur),'_blank');
  const q = new URLSearchParams(location.search).get('tp');
  render(q && PLAN.tps[q] ? q : PLAN.names[0]);
})();
