(function(){
  const sel = document.getElementById('fsel');
  const F = MOCK.flights;
  sel.innerHTML = F.map(f=>`<option value="${f.id}">${f.id} · ${f.route}${f.dir==='arr'?'  (arr)':''}</option>`).join('');

  // ── Day schedule summary ──
  const D = MOCK.flightDay;
  document.getElementById('f-daystats').innerHTML = [
    ['Total Flights', fmt(D.total), 'showing '+F.length+' sample'],
    ['Departures', fmt(D.dep), 'planned tomorrow'],
    ['Arrivals', fmt(D.arr), 'planned tomorrow'],
    ['Predicted PAX', fmt(D.pax), 'all flights'],
    ['Avg Load Factor', D.lf+'%', 'predicted'],
  ].map(([l,v,s],i)=>`<div class="kpi ${i===0?'accent':''}">
      <div class="kpi-lab">${l}</div><div class="kpi-val" style="font-size:22px">${v}</div>
      <div class="kpi-chg flat">${s}</div></div>`).join('');

  let tu, cur = F[0], rtMode = 'ontime';   // rtMode: live adjustment applied to the selected flight (RT-01/RT-02)
  const toMin = t => { const [h,m]=t.split(':').map(Number); return h*60+m; };
  const toHM  = x => { x=((Math.round(x)%1440)+1440)%1440; return String(Math.floor(x/60)).padStart(2,'0')+':'+String(x%60).padStart(2,'0'); };

  // Real-time adjustment definitions (RT-01): each shifts effective timing and/or status.
  const RT = {
    ontime: { delay:0,  gate:false, label:'On time',      status:f=>f.status },
    d30:    { delay:30,  gate:false, label:'Delay +30 min',status:f=>'Delayed 30 min' },
    d60:    { delay:60,  gate:false, label:'Delay +60 min',status:f=>'Delayed 60 min' },
    gate:   { delay:0,   gate:true,  label:'Gate change',  status:f=>'Gate Changed' },
  };

  // Build the effective flight after applying the active real-time adjustment.
  function effective(f){
    const a = RT[rtMode] || RT.ontime;
    const e = Object.assign({}, f);
    e.time = toHM(toMin(f.time) + a.delay);   // shift effective departure / landing
    e.status = a.status(f);
    return e;
  }

  function render(f){
    cur = f;
    const eff = effective(f);
    document.getElementById('f-id').textContent = f.id;
    const dir = document.getElementById('f-dir');
    dir.textContent = f.dir==='dep'?'Departure':'Arrival';
    dir.className = 'tag '+(f.dir==='dep'?'t-blue':'t-teal');
    const dom = document.getElementById('f-dom');
    dom.textContent = f.dom?'Domestic':'International';
    dom.className = 'tag '+(f.dom?'t-green':'t-violet');
    const stc = /On Time|Early|Boarding|Landed/.test(eff.status)?'t-green':/Delayed/.test(eff.status)?'t-amber':'t-blue';
    const st = document.getElementById('f-status'); st.textContent = eff.status; st.className = 'tag '+stc;

    // schedule-given details (effective time reflects any live adjustment)
    const timeCell = eff.time!==f.time
      ? `<span class="dim" style="text-decoration:line-through;font-size:13px">${f.time}</span> <span style="color:var(--amber)">→ ${eff.time}</span>`
      : f.time;
    document.getElementById('f-details').innerHTML = [
      ['Airline',f.al],['Aircraft',f.ac],['Route',f.route],
      [f.dir==='dep'?'Departure':'Arrival',timeCell],['Seat Capacity',f.cap],
    ].map(([l,v])=>`<div class="mini"><div class="mini-lab">${l}</div><div class="mini-val" style="font-size:16px">${v}</div></div>`).join('');

    // bookloads prediction
    const lf = Math.round(f.total/f.cap*100);
    document.getElementById('f-pred').innerHTML = [
      ['Total Boarded PAX',fmt(f.total),''],
      ['Local PAX',fmt(f.local),'var(--teal)'],
      ['Transfer PAX',fmt(f.transfer),'var(--violet)'],
      ['Load Factor',lf+'%','var(--blue2)'],
    ].map(([l,v,c])=>`<div class="mini"><div class="mini-lab">${l}</div><div class="mini-val" style="${c?'color:'+c:''}">${v}</div></div>`).join('');

    renderTurnup(eff);
    renderProj(eff);
    renderRT(f, eff);
  }

  // ── Real-time adjustment output (RT-01 / RT-02) — before → after ──
  function renderRT(f, eff){
    const out = document.getElementById('f-rt-out');
    const a = RT[rtMode] || RT.ontime;
    const dirWord = f.dir==='dep'?'departure':'landing';
    let card;
    if(rtMode==='ontime'){
      out.innerHTML =
        `<div class="fill-note" style="padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--panel2)">
           <span class="tag t-green" style="margin-right:8px">Scheduled</span>
           Prediction reflects the published AODB schedule — ${dirWord} <b class="mono">${f.time}</b>. No live adjustment applied.
         </div>`;
      return;
    }
    if(a.gate){
      card =
        `<span class="tag t-amber" style="margin-right:8px">Gate change</span>
         Re-gated — ${dirWord} timing unchanged at <b class="mono">${f.time}</b>.
         <span class="dim">Turn-up load and touchpoint windows are unaffected; only the assigned gate/stand moves.</span>`;
    } else {
      card =
        `<span class="tag t-amber" style="margin-right:8px">${a.label}</span>
         Effective ${dirWord} <span class="dim mono" style="text-decoration:line-through">${f.time}</span>
         <b class="mono" style="color:var(--amber)"> → ${eff.time}</b>
         <span style="color:var(--teal)">(+${a.delay} min)</span>.
         <span class="dim">Turn-up load re-projected to new timing — every touchpoint window below shifts +${a.delay} min (RT-02).</span>`;
    }
    out.innerHTML =
      `<div style="padding:10px 12px;border:1px solid var(--line2);border-radius:8px;background:var(--panel2)">
         <div style="font-size:12.5px;line-height:1.6">${card}</div>
       </div>`;
  }

  // ── Turn-up profile (departures) / arrival offsets (arrivals) ──
  function renderTurnup(f){
    const body = document.getElementById('f-turnup-body');
    const title = document.getElementById('f-tu-title');
    if(tu){ tu.destroy(); tu=null; }

    if(f.dir==='arr'){
      title.innerHTML = 'Arrival Processing <span class="sub">offset from landing · TP-05 / TP-06</span>';
      body.innerHTML = `<div style="padding:10px 4px">
        <div class="mini-sub" style="margin-bottom:12px">Arrivals have no turn-up curve — their load lands at fixed offsets after touchdown at <b>${f.time}</b>:</div>
        ${f.dom
          ? `<div class="mini"><div class="mini-lab">Domestic arrival</div><div class="mini-val" style="font-size:15px">Passengers exit directly — no Immigration / Customs.</div></div>`
          : `<div class="grid g2" style="gap:10px">
              <div class="mini"><div class="mini-lab">Immigration</div><div class="mini-val" style="font-size:18px;color:var(--amber)">${toHM(toMin(f.time)+27)}</div><div class="mini-sub">+25–30 min after landing</div></div>
              <div class="mini"><div class="mini-lab">Customs</div><div class="mini-val" style="font-size:18px;color:var(--amber)">${toHM(toMin(f.time)+42)}</div><div class="mini-sub">+40–45 min after landing</div></div>
            </div>`}
      </div>`;
      return;
    }

    title.innerHTML = 'Turn-Up Profile <span class="sub">when local PAX arrive · PR-04</span>';
    const prof = f.dom?MOCK.tuDom:MOCK.tuIntl;
    const depM = toMin(f.time);
    const labels = MOCK.tuMin.map(mb=>toHM(depM-mb));
    const data = prof.map(p=>Math.round(p/100*f.local));
    const act  = data.map(v=>Math.round(v*0.96));   // actual scan (E-Boarding) ~96% of predicted
    const peak = Math.max(...prof);
    const cols = prof.map(p=> p===peak ? C.violet : C.violet+'99');
    // summary stats (folded in from the old Turn-Up page)
    const peakI = prof.indexOf(peak);
    const fmtHM = m => { const h=Math.floor(m/60), mm=m%60; return mm?`${h}h ${mm}m`:`${h}h`; };
    let cum=0, by80=null; for(let i=0;i<prof.length;i++){ cum+=prof[i]; if(by80===null&&cum>=80) by80=MOCK.tuMin[i]; }
    body.innerHTML =
      '<div class="chart" style="height:178px"><canvas id="f-turnup"></canvas></div>'+
      '<div class="grid g3" style="gap:8px;margin-top:10px">'+
        `<div class="mini"><div class="mini-lab">Peak Arrival</div><div class="mini-val" style="font-size:15px">${fmtHM(MOCK.tuMin[peakI])}</div><div class="mini-sub">before departure</div></div>`+
        `<div class="mini"><div class="mini-lab">80% Arrived By</div><div class="mini-val" style="font-size:15px">${fmtHM(by80)}</div><div class="mini-sub">before departure</div></div>`+
        `<div class="mini"><div class="mini-lab">Peak 30-Min</div><div class="mini-val" style="font-size:15px">${Math.max(...data)}</div><div class="mini-sub">pax / 30 min</div></div>`+
      '</div>';
    tu = new Chart(document.getElementById('f-turnup'), {
      type:'bar',
      data:{ labels, datasets:[
        {label:'Predicted PAX', data, backgroundColor:cols, borderRadius:3, order:2},
        {label:'Actual (E-Boarding)', data:act, type:'line', borderColor:C.teal, borderWidth:2, borderDash:[6,4], pointRadius:0, pointHoverRadius:5, tension:.4, order:1},
      ]},
      options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false},
        plugins:{ legend:{position:'top',labels:{boxWidth:9,boxHeight:9,borderRadius:4,useBorderRadius:true,padding:12,font:{size:10,weight:600}}}, tooltip:tt() },
        scales:{
          x:{grid:{display:false}, ticks:{font:{size:8.5},maxRotation:0,autoSkip:false},
             title:{display:true,text:'arrival clock time (before '+f.time+' departure)',font:{size:9.5},color:'#8696b5'}},
          y:{beginAtZero:true,grid:{color:GRID},ticks:{font:{size:9.5},precision:0},
             title:{display:true,text:'PAX',font:{size:9.5},color:'#8696b5'}} } }
    });
  }

  // ── Touchpoint projection (PR-05) ──
  function renderProj(f){
    const tbl = document.getElementById('f-proj');
    const note = document.getElementById('f-proj-note');
    const m = toMin(f.time);
    let rows;
    if(f.dir==='dep'){
      rows = [
        ['Entry Gates',     toHM(m-210)+'–'+toHM(m-60), f.local, 'local'],
        ['Check-In',        toHM(m-200)+'–'+toHM(m-55), f.local, 'local'],
        ['Security (PESC)', toHM(m-180)+'–'+toHM(m-45), f.total, 'local + transfer'],
      ];
      if(!f.dom) rows.push(['Emigration', toHM(m-160)+'–'+toHM(m-40), f.total, 'local + transfer']);
      note.textContent = 'Local PAX enter via Entry → Check-In; transfer PAX join at Security from their inbound flight. PR-05 projects these onto the touchpoint load curves.';
    } else if(f.dom){
      rows = [
        ['Arrival Concourse', toHM(m+8),  f.total,    'deplaned'],
        ['Transfers',         toHM(m+25), f.transfer, 'connecting'],
      ];
      note.textContent = 'Domestic arrival — no Immigration / Customs. Connecting PAX feed onward departures.';
    } else {
      rows = [
        ['Immigration',       toHM(m+27), f.local,    'arriving'],
        ['Baggage + Customs', toHM(m+42), f.local,    'arriving'],
        ['Transfers',         toHM(m+30), f.transfer, 'connecting'],
      ];
      note.textContent = 'International arrival — load lands at fixed offsets after touchdown (TP-05 / TP-06). Transfer PAX route to onward flights.';
    }
    tbl.innerHTML =
      '<thead><tr><th>Touchpoint</th><th>Load window</th><th class="num">PAX</th><th>Segment</th></tr></thead><tbody>'+
      rows.map(r=>`<tr><td><b>${r[0]}</b></td><td class="mono">${r[1]}</td><td class="num">${fmt(r[2])}</td><td class="dim" style="font-size:11px">${r[3]}</td></tr>`).join('')+
      '</tbody>';
  }

  // ── Real-time adjustment control (RT-01 / RT-02) ──
  const rtSeg = document.getElementById('f-rt-seg');
  function syncSeg(){ rtSeg.querySelectorAll('button').forEach(b=>b.classList.toggle('on', b.dataset.rt===rtMode)); }
  rtSeg.querySelectorAll('button').forEach(b=> b.onclick = ()=>{ rtMode = b.dataset.rt; syncSeg(); render(cur); });

  // Selecting a different flight resets to its published (scheduled) state.
  function select(f){ rtMode='ontime'; syncSeg(); render(f); }

  select(cur);
  sel.onchange = () => select(F.find(f=>f.id===sel.value));
  document.getElementById('fsearch').oninput = e => {
    const q = e.target.value.trim().toUpperCase().replace(/\s/g,'');
    if(!q) return;
    const f = F.find(x=>x.id.replace(/\s/g,'').includes(q));
    if(f){ sel.value=f.id; select(f); }
  };
})();
