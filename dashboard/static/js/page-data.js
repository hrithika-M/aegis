(function(){
  // ─────────────────────────────────────────────────────────────
  // Page-local mock data (self-contained — GMR Hyderabad scale ops)
  // ─────────────────────────────────────────────────────────────

  // A) Integrated Data Sources — DR-01..08
  // st: 'live' | 'connected' | 'degraded' | 'awaiting'
  const SOURCES = [
    { dr:'DR-01', name:'AODB',              feed:'Live flight schedules',          st:'awaiting',  sync:'—',           recs:null,   acc:null },
    { dr:'DR-02', name:'Data Lake',         feed:'6-month seasonal schedules',     st:'awaiting',  sync:'—',           recs:null,   acc:null },
    { dr:'DR-03', name:'LDM + PTM',         feed:'Actual bookloads (per flight)',  st:'awaiting',  sync:'—',           recs:null,   acc:null },
    { dr:'DR-04', name:'CUPPS',             feed:'Check-In & gate scans',          st:'degraded',  sync:'2 min ago',   recs:78420,  acc:73 },
    { dr:'DR-05', name:'E-Boarding',        feed:'Entry / PESC / Transfers scans', st:'degraded',  sync:'1 min ago',   recs:96310,  acc:81 },
    { dr:'DR-06', name:'Queue Stats / EWS', feed:'Processing time per channel',    st:'live',      sync:'Live',        recs:204880, acc:98 },
    { dr:'DR-07', name:'IOT Stats Daily',   feed:'Hourly PAX per zone',            st:'connected', sync:'14 min ago',  recs:168,    acc:null },
    { dr:'DR-08', name:'Holiday Mapping',   feed:'India holiday calendar 2025-26', st:'connected', sync:'1 day ago',   recs:142,    acc:null },
  ];

  // B-DQ-01/02) Scan accuracy gauges vs 90% target
  const TARGET = 90;
  const GAUGES = [
    { lab:'CUPPS vs LDM',      sub:'Check-In & gate scans · DQ-01', val:73 },
    { lab:'E-Boarding vs LDM', sub:'Entry / PESC / Transfers · DQ-02', val:81 },
  ];

  // DQ-03) PTM vs camera variance (I-I transfers)
  const VARIANCE = { val:18, lab:'PTM vs Camera Variance', sub:'Intl-to-Intl transfers · DQ-03', threshold:5 };

  // DQ-06) Check-In actuals logic freeze
  const FREEZE = { frozen:true, note:'derive_checkin_actuals v3 · locked 2026-05-28' };

  // DQ-04) Outage log — windows excluded from accuracy
  const OUTAGES = [
    { range:'01 Mar – 15 Mar', src:'E-Boarding', tp:'Entry Gates', excl:true },
    { range:'01 Apr – 07 Apr', src:'ATRS',       tp:'Security (PESC)', excl:true },
    { range:'22 Apr (06–11h)', src:'CUPPS',      tp:'Check-In',    excl:true },
  ];

  // DQ-05) Ingestion quarantine rules
  const QUAR = {
    total: 1247,
    rules: [
      { name:'Zero-scan with load',      desc:'scan_count = 0 while LDM load is non-zero', hits:512 },
      { name:'Scans exceed actual load', desc:'scan_count > actual boarded PAX',           hits:386 },
      { name:'Scan variance > 10%',      desc:'|scan − actual| / actual > 10%',            hits:349 },
    ],
  };

  // ─────────────────────────────────────────────────────────────
  // Helpers
  // ─────────────────────────────────────────────────────────────
  const STATUS = {
    live:      { bdg:'b-low',  txt:'Live' },
    connected: { bdg:'b-low',  txt:'Connected' },
    degraded:  { bdg:'b-med',  txt:'Degraded' },
    awaiting:  { bdg:'b-high', txt:'Awaiting' },
  };

  // ── Top KPIs ──
  const connected = SOURCES.filter(s=>s.st==='live'||s.st==='connected').length;
  const degraded  = SOURCES.filter(s=>s.st==='degraded').length;
  const awaiting  = SOURCES.filter(s=>s.st==='awaiting').length;
  const totalRecs = SOURCES.reduce((a,s)=>a+(s.recs||0),0);
  document.getElementById('d-kpis').innerHTML = [
    ['Sources Online', connected+' / '+SOURCES.length, 'feeds connected', 'accent', 'up'],
    ['Degraded Feeds', degraded, 'below 90% accuracy', '', 'down'],
    ['Awaiting Connection', awaiting, 'schedule feeds', '', 'flat'],
    ['Records Ingested', fmt(totalRecs), 'today', '', 'flat'],
    ['Quarantined', fmt(QUAR.total), 'records today', '', 'down'],
  ].map(([l,v,s,a,c])=>`<div class="kpi ${a}">
      <div class="kpi-lab">${l}</div><div class="kpi-val" style="font-size:22px">${v}</div>
      <div class="kpi-chg ${c}">${s}</div></div>`).join('');

  // ── A) Integrated Data Sources table ──
  document.getElementById('d-sources').innerHTML =
    '<thead><tr><th>Source</th><th>Feed</th><th class="ctr">Status</th><th>Last Sync</th><th class="num">Records</th><th class="num">Acc vs Actual</th></tr></thead><tbody>'+
    SOURCES.map(s=>{
      const st = STATUS[s.st];
      const live = s.st==='live';
      const accCell = s.acc==null
        ? '<td class="num dim">—</td>'
        : `<td class="num" style="color:${s.acc>=90?'var(--green)':s.acc>=80?'var(--amber)':'var(--red)'};font-weight:700">${s.acc}%${live?' <span class="dim" style="font-size:9px;font-weight:400">live</span>':''}</td>`;
      const recCell = s.recs==null ? '<td class="num dim">—</td>' : `<td class="num">${fmt(s.recs)}</td>`;
      const syncCls = s.sync==='Live' ? 'mono' : (s.sync==='—' ? 'dim' : 'mono dim');
      return `<tr>
        <td><span class="ds-ic">${s.dr.replace('DR-','')}</span><b>${s.name}</b></td>
        <td class="muted">${s.feed}</td>
        <td class="ctr"><span class="bdg ${st.bdg}" style="padding:2px 9px">${st.txt}</span></td>
        <td class="${syncCls}" style="font-size:11px">${s.sync}</td>
        ${recCell}
        ${accCell}
      </tr>`;
    }).join('')+
    '</tbody>';
  document.getElementById('d-src-summary').textContent = connected+' / '+SOURCES.length+' connected';

  // ── B) DQ-01 / DQ-02 : scan-accuracy gauges (horizontal bar vs 90% target) ──
  document.getElementById('d-gauges').innerHTML = GAUGES.map(g=>{
    const below = g.val < TARGET;
    const col = below ? 'var(--red)' : 'var(--green)';
    return `<div style="margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:7px">
        <div><div class="mini-lab">${g.lab}</div><div class="mini-sub">${g.sub}</div></div>
        <div style="font-size:22px;font-weight:800;font-family:'JetBrains Mono';color:${col}">${g.val}%</div>
      </div>
      <div style="position:relative;height:14px;background:var(--panel3);border-radius:8px;overflow:hidden">
        <div style="position:absolute;inset:0;width:${g.val}%;background:linear-gradient(90deg,${below?'var(--red)':'var(--green)'},${below?'var(--rose)':'var(--teal)'});border-radius:8px"></div>
      </div>
      <div style="position:relative;height:14px;margin-top:-14px;pointer-events:none">
        <div style="position:absolute;left:${TARGET}%;top:-3px;bottom:-3px;width:2px;background:var(--amber)"></div>
      </div>
      <div style="position:relative;height:14px">
        <div style="position:absolute;left:${TARGET}%;transform:translateX(-50%);font-size:9px;color:var(--amber);font-weight:700;margin-top:2px">▲ 90% target</div>
        <div style="position:absolute;right:0;font-size:9px;color:${col};font-weight:700;margin-top:2px">${below?(TARGET-g.val)+'% below':'on target'}</div>
      </div>
    </div>`;
  }).join('');

  // ── DQ-03 : PTM vs camera variance metric card ──
  document.getElementById('d-variance').innerHTML =
    `<div class="mini" style="border-color:rgba(239,68,68,.3)">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div><div class="mini-lab">${VARIANCE.lab}</div><div class="mini-sub">${VARIANCE.sub}</div></div>
        <div style="font-size:26px;font-weight:800;font-family:'JetBrains Mono';color:var(--red)">${VARIANCE.val}%</div>
      </div>
      <div style="margin-top:10px"><span class="bdg b-high" style="padding:3px 10px">Flagged for reconciliation</span>
        <span class="dim" style="font-size:10px;margin-left:8px">threshold ${VARIANCE.threshold}% · ${(VARIANCE.val/VARIANCE.threshold).toFixed(1)}× over</span></div>
    </div>`;

  // ── DQ-06 : Check-In actuals freeze status row ──
  document.getElementById('d-freeze').innerHTML =
    `<div style="display:flex;align-items:center;justify-content:space-between;padding:11px 14px;background:var(--panel2);border:1px solid var(--line);border-radius:9px">
      <div style="font-size:12px;font-weight:600">Check-In actuals logic</div>
      <span class="tag ${FREEZE.frozen?'t-green':'t-amber'}">${FREEZE.frozen?'Frozen ✓':'Pending'}</span>
    </div>
    <div class="dim" style="font-size:10px;margin-top:6px">${FREEZE.note}</div>`;

  // ── DQ-04 : Outage log table ──
  document.getElementById('d-outages').innerHTML =
    '<thead><tr><th>Date Range</th><th>Source</th><th>Touchpoint</th><th class="ctr">Excl. from Acc</th></tr></thead><tbody>'+
    OUTAGES.map(o=>`<tr>
      <td class="mono" style="font-size:11px">${o.range}</td>
      <td><b>${o.src}</b></td>
      <td class="muted">${o.tp}</td>
      <td class="ctr"><span class="bdg ${o.excl?'b-low':'b-med'}" style="padding:2px 8px">${o.excl?'Yes':'No'}</span></td>
    </tr>`).join('')+
    '</tbody>';
  document.getElementById('d-outage-cnt').textContent = OUTAGES.length+' windows';

  // ── DQ-05 : Ingestion quarantine rules ──
  document.getElementById('d-quar-rules').innerHTML = QUAR.rules.map((r,i)=>`
    <div class="imp" style="${i===QUAR.rules.length-1?'border-bottom:none':''}">
      <span style="width:22px;height:22px;border-radius:6px;background:rgba(239,68,68,.15);color:var(--red);display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:800">${i+1}</span>
      <div class="imp-nm"><b>${r.name}</b><div class="dim mono" style="font-size:10px;font-weight:400">${r.desc}</div></div>
      <div class="imp-v" style="color:var(--red)">${fmt(r.hits)}</div>
    </div>`).join('');
  document.getElementById('d-quar-cnt').textContent = fmt(QUAR.total)+' quarantined today';
})();
