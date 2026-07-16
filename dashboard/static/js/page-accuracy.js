/* POD — Accuracy & Models page. Self-contained: page-local mock data + render.
   Covers AR-01..05, AC-01..05, PR-10, RT-03. Mock data only. */
(function(){

  // ── page-local mock data (do NOT touch mock.js) ──
  const TP = ['Entry Gates','Check-In','Security','Emigration','Immigration','Customs','Transfers'];
  const TPCOL = {
    'Entry Gates':C.blue, 'Check-In':C.blue2, 'Security':C.violet, 'Emigration':C.teal,
    'Immigration':C.green, 'Customs':C.amber, 'Transfers':C.rose
  };

  // last ~6 months (oldest → newest); today is mid-Jun 2026
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun'];

  // monthly HOURLY accuracy per touchpoint (%, 84–98), gently trending up as models retrain (AC-05)
  const TREND = {
    'Entry Gates':  [93.1, 93.8, 94.2, 95.0, 95.6, 96.1],
    'Check-In':     [88.4, 89.1, 90.3, 91.0, 91.8, 92.4],
    'Security':     [86.2, 87.0, 88.1, 88.9, 90.2, 91.1],
    'Emigration':   [89.7, 90.4, 91.2, 92.0, 92.7, 93.5],
    'Immigration':  [84.3, 85.6, 86.9, 87.8, 88.6, 89.4],
    'Customs':      [90.5, 91.3, 92.0, 92.8, 93.4, 94.0],
    'Transfers':    [85.0, 86.1, 87.2, 88.0, 89.1, 90.0],
  };

  // per-touchpoint accuracy summary — hourly is PRIMARY (AR-04); held-out last-5-days (AR-03)
  // daily % is typically a few points higher than hourly (totals match even when shape drifts)
  const ACC = TP.map(tp=>{
    const hourly = TREND[tp][TREND[tp].length-1];               // latest month
    const daily  = Math.min(98.5, hourly + 2.6 + Math.random()*1.0);
    return { tp, hourly:+hourly.toFixed(1), daily:+daily.toFixed(1) };
  });

  // KPI summary
  const fleetHourly = +(ACC.reduce((a,x)=>a+x.hourly,0)/ACC.length).toFixed(1);
  const fleetDaily  = +(ACC.reduce((a,x)=>a+x.daily ,0)/ACC.length).toFixed(1);

  // ── Model Registry (AC-01 hybrid, AC-02 own accuracy, AC-04 winner) ──
  // type: 'direct'  = trained straight on queue/scan history
  //       'chained' = flight-aware, depends on upstream flight predictions (Bookloads→Turn-up→Zone→Proc)
  const MODELS = [
    // flight-aware chained chain (AC-01)
    {name:'Bookloads',        type:'chained', target:'Expected boarding PAX per flight', algos:'RandomForest · LGBM', winner:'LGBM',         acc:94.2, status:'Production'},
    {name:'Turn-up Profile',  type:'chained', target:'Local PAX arrival curve',       algos:'RandomForest · LGBM', winner:'RandomForest', acc:90.8, status:'Production'},
    {name:'Zone-ratio',       type:'chained', target:'Load split across zones/lanes', algos:'RandomForest · LGBM', winner:'LGBM',         acc:88.5, status:'Production'},
    {name:'Processing-time',  type:'chained', target:'Service time per PAX (min)',     algos:'RandomForest · LGBM', winner:'LGBM',         acc:91.6, status:'Production'},
    // direct queue-data models (AC-01) — also the AC-03 fallback path
    {name:'Entry Gates · hourly', type:'direct', target:'Entry Gates hourly load',  algos:'RandomForest · LGBM', winner:'LGBM',         acc:96.1, status:'Production'},
    {name:'Check-In · hourly',    type:'direct', target:'Check-In hourly load',     algos:'RandomForest · LGBM', winner:'RandomForest', acc:92.4, status:'Production'},
    {name:'Security · hourly',    type:'direct', target:'Security (PESC) hourly load',algos:'RandomForest · LGBM', winner:'LGBM',         acc:91.1, status:'Production'},
    {name:'Emigration · hourly',  type:'direct', target:'Emigration hourly load',   algos:'RandomForest · LGBM', winner:'LGBM',         acc:93.5, status:'Production'},
    {name:'Immigration · hourly', type:'direct', target:'Immigration hourly load',  algos:'RandomForest · LGBM', winner:'RandomForest', acc:89.4, status:'Production'},
    {name:'Customs · hourly',     type:'direct', target:'Customs hourly load',      algos:'RandomForest · LGBM', winner:'LGBM',         acc:94.0, status:'Production'},
    {name:'Transfers · hourly',   type:'direct', target:'Transfers hourly load',    algos:'RandomForest · LGBM', winner:'RandomForest', acc:90.0, status:'Production'},
    {name:'Security · 30-min interval', type:'direct', target:'Security 30-min intervals', algos:'RandomForest · LGBM', winner:'LGBM', acc:87.3, status:'Candidate'},
  ];

  // ── Prediction API (RT-03) ──
  const API = [
    ['GET',  '/api/predict/<date>',            'Full-day per-touchpoint hourly load forecast for a date'],
    ['GET',  '/api/intervals/<date>/<tp>',     '30-minute interval predictions for one touchpoint'],
    ['GET',  '/api/prescription/<date>',       'Recommended lanes / positions per touchpoint per hour (WI)'],
    ['GET',  '/api/accuracy/<month>',          'Held-out hourly & daily accuracy per touchpoint for a month'],
    ['POST', '/api/simulate',                  'What-if: posts closures/threshold, returns recomputed waits'],
    ['GET',  '/api/data-quality',              'Scan-data quality score; drives AC-03 fallback to direct models'],
    ['GET',  '/api/models',                    'Model registry: target, algorithm, winner, stage accuracy'],
  ];

  const accColor = a => a>=93 ? 'var(--green)' : a>=88 ? 'var(--amber)' : 'var(--red)';
  const bdgClass = a => a>=93 ? 'b-low' : a>=88 ? 'b-med' : 'b-high';

  // ── KPI strip ──
  document.getElementById('a-kpis').innerHTML = [
    ['Fleet Hourly Accuracy', fleetHourly+'%', 'primary measure · AR-04', 'accent'],
    ['Fleet Daily Accuracy',  fleetDaily+'%',  'secondary check', ''],
    ['Models in Registry',    MODELS.length,   MODELS.filter(m=>m.status==='Production').length+' in production · PR-10', ''],
    ['Validation Method',     'Held-out',      'last-5-days · AR-03', ''],
  ].map(([l,v,s,a])=>`<div class="kpi ${a}">
      <div class="kpi-lab">${l}</div>
      <div class="kpi-val" style="font-size:22px">${v}</div>
      <div class="kpi-chg flat">${s}</div></div>`).join('');

  // ── A · monthly hourly-accuracy trend (multiLine, AR-01) ──
  multiLine(
    document.getElementById('a-trend'),
    MONTHS,
    TP.map(tp=>({ label:tp, data:TREND[tp], color:TPCOL[tp] }))
  );

  // ── A · accuracy-by-touchpoint table (AR-03 / AR-04) ──
  document.querySelector('#a-acc-tbl tbody').innerHTML = ACC.map(r=>`
    <tr>
      <td><b>${r.tp}</b></td>
      <td class="num dim">${r.daily.toFixed(1)}%</td>
      <td class="num" style="font-weight:800;color:${accColor(r.hourly)}">${r.hourly.toFixed(1)}%</td>
      <td class="ctr"><span class="bdg b-low" style="padding:2px 8px">Hourly</span></td>
      <td class="dim" style="font-size:11px">held-out last-5-days validation</td>
    </tr>`).join('');

  // ── B · Variance Tolerance (AR-02) — live recompute on slider ──
  // Each touchpoint's intra-day shape has a base spread; tolerance band determines how many
  // of the 24 hours fall inside ±band. Looser band → more hours pass.
  // "spread" ~ typical |predicted-actual|/actual for that touchpoint's busiest hours.
  const SPREAD = {
    'Entry Gates':0.09, 'Check-In':0.15, 'Security':0.18, 'Emigration':0.13,
    'Immigration':0.21, 'Customs':0.11, 'Transfers':0.19
  };
  // deterministic per-hour deviation pattern so results are stable across slider moves
  function hourDevs(tp){
    const s = SPREAD[tp];
    return Array.from({length:24}, (_,h)=>{
      // pseudo-random but deterministic by tp+hour
      const seed = (tp.length*7 + h*13) % 17;
      const n = (Math.sin(seed*1.7)+1)/2;          // 0..1
      return s * (0.35 + 1.3*n);                    // deviation magnitude for that hour
    });
  }
  const DEVS = {}; TP.forEach(tp=>DEVS[tp]=hourDevs(tp));

  function hoursWithin(tp, band){
    return DEVS[tp].filter(d=>d<=band).length;       // hours whose deviation is inside ±band
  }

  function renderTolerance(pct){
    const band = pct/100;
    document.getElementById('a-tol-v').textContent = '±'+pct+'%';

    // overall summary cards
    const perTp = TP.map(tp=>({tp, hrs:hoursWithin(tp, band)}));
    const totalHrs = perTp.reduce((a,x)=>a+x.hrs,0);
    const avgHrs = (totalHrs/TP.length);
    const worst = perTp.reduce((a,b)=>b.hrs<a.hrs?b:a);
    const best  = perTp.reduce((a,b)=>b.hrs>a.hrs?b:a);

    document.getElementById('a-tol-cards').innerHTML = [
      ['Avg Hours / Day in Tolerance', avgHrs.toFixed(1)+' / 24', 'across 7 touchpoints'],
      ['% of Hours Passing', Math.round(totalHrs/(TP.length*24)*100)+'%', 'all touchpoints'],
      ['Best Touchpoint', best.hrs+' / 24', best.tp],
      ['Tightest Touchpoint', worst.hrs+' / 24', worst.tp],
    ].map(([l,v,s])=>`<div class="mini"><div class="mini-lab">${l}</div>
        <div class="mini-val" style="font-size:18px">${v}</div>
        <div class="mini-sub">${s}</div></div>`).join('');

    // per-touchpoint table
    document.querySelector('#a-tol-tbl tbody').innerHTML = perTp.map(x=>{
      const ratio = x.hrs/24;
      const cls = ratio>=0.8 ? 'b-low' : ratio>=0.6 ? 'b-med' : 'b-high';
      const lab = ratio>=0.8 ? 'Strong' : ratio>=0.6 ? 'Fair' : 'Watch';
      return `<tr>
        <td><b>${x.tp}</b></td>
        <td class="num" style="font-weight:800;color:${ratio>=0.8?'var(--green)':ratio>=0.6?'var(--amber)':'var(--red)'}">${x.hrs}</td>
        <td class="num dim">24</td>
        <td class="ctr"><span class="bdg ${cls}" style="padding:2px 8px">${lab}</span></td>
      </tr>`;
    }).join('');
  }
  // expose for inline oninput in the template, and also wire directly
  window.__accTol = renderTolerance;
  const tolEl = document.getElementById('a-tol');
  tolEl.addEventListener('input', e=>renderTolerance(+e.target.value));
  renderTolerance(+tolEl.value);

  // ── C · Model Registry (AC-01/02/04/05, PR-10) with Direct/Flight-aware filter ──
  function renderRegistry(filter){
    const rows = MODELS.filter(m=>filter==='all'||m.type===filter);
    document.querySelector('#a-reg-tbl tbody').innerHTML = rows.map(m=>{
      const typeTag = m.type==='chained'
        ? '<span class="tag t-violet">Flight-aware</span>'
        : '<span class="tag t-blue">Direct</span>';
      const statusBdg = m.status==='Production'
        ? '<span class="bdg b-low" style="padding:2px 8px">Production</span>'
        : '<span class="bdg b-med" style="padding:2px 8px">Candidate</span>';
      const winTag = m.winner==='LGBM'
        ? '<span class="tag t-teal">LGBM</span>'
        : '<span class="tag t-green">RandomForest</span>';
      return `<tr>
        <td><b>${m.name}</b></td>
        <td>${typeTag}</td>
        <td class="dim" style="font-size:11px">${m.target}</td>
        <td class="mono" style="font-size:11px">${m.algos}</td>
        <td class="ctr">${winTag}</td>
        <td class="num" style="font-weight:800;color:${accColor(m.acc)}">${m.acc.toFixed(1)}%</td>
        <td class="ctr">${statusBdg}</td>
      </tr>`;
    }).join('');
  }
  renderRegistry('all');
  document.querySelectorAll('#a-reg-seg button').forEach(b=>{
    b.onclick = ()=>{
      document.querySelectorAll('#a-reg-seg button').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');
      renderRegistry(b.dataset.f);
    };
  });

  // ── C2 · Model Fallback Status (AC-03) ──
  // per scan-feed scan-data quality vs the 90% gate. ≥90% → flight-aware models run;
  // below 90% → that feed falls back to the direct queue models so predictions keep flowing.
  const FB_GATE = 90;
  const FEEDS = [
    {feed:'BHS / bag-tag scans',     q:96.4},
    {feed:'Boarding-gate scans',     q:94.1},
    {feed:'Security lane (PESC)',    q:91.2},
    {feed:'CUPPS check-in scans',    q:73.0},   // below gate → direct fallback ACTIVE
    {feed:'Emigration e-gate scans', q:88.6},   // below gate → direct fallback ACTIVE
  ];

  const fbAbove = FEEDS.filter(f=>f.q>=FB_GATE).length;
  const fbBelow = FEEDS.length - fbAbove;
  const fbMinFeed = FEEDS.reduce((a,b)=>b.q<a.q?b:a);

  // header track tag — overall posture
  const fbTrackEl = document.getElementById('a-fb-track');
  if(fbBelow>0){
    fbTrackEl.className = 'tag t-amber';
    fbTrackEl.textContent = fbBelow+' feed'+(fbBelow>1?'s':'')+' on direct fallback';
  } else {
    fbTrackEl.className = 'tag t-green';
    fbTrackEl.textContent = 'all feeds flight-aware';
  }

  // KPI tiles
  document.getElementById('a-fb-kpis').innerHTML = [
    ['Fallback Threshold', FB_GATE+'%', 'scan-data quality gate · AC-03'],
    ['Feeds ≥ Threshold',  fbAbove+' / '+FEEDS.length, 'flight-aware models active'],
    ['Feeds in Fallback',  fbBelow+' / '+FEEDS.length, 'direct queue models active'],
    ['Lowest-quality Feed', fbMinFeed.q.toFixed(1)+'%', fbMinFeed.feed],
  ].map(([l,v,s])=>`<div class="mini"><div class="mini-lab">${l}</div>
      <div class="mini-val" style="font-size:18px">${v}</div>
      <div class="mini-sub">${s}</div></div>`).join('');

  // per-feed table with a gauge bar (90% threshold marked) + active-track badge
  document.querySelector('#a-fb-tbl tbody').innerHTML = FEEDS.map(f=>{
    const ok = f.q>=FB_GATE;
    const col = ok ? 'var(--green)' : 'var(--red)';
    const trackBdg = ok
      ? '<span class="bdg b-low" style="padding:2px 8px">Flight-aware</span>'
      : '<span class="bdg b-high" style="padding:2px 8px">Direct fallback ACTIVE</span>';
    // gauge: fill = quality %, with a marker at the 90% gate
    const gauge = `<div style="position:relative;height:14px;border-radius:7px;background:var(--panel3);overflow:hidden;min-width:140px">
        <div style="position:absolute;left:0;top:0;bottom:0;width:${f.q}%;background:${col};opacity:.55;border-radius:7px"></div>
        <div title="90% gate" style="position:absolute;left:${FB_GATE}%;top:-2px;bottom:-2px;width:2px;background:var(--txt);opacity:.85"></div>
      </div>`;
    return `<tr>
      <td><b>${f.feed}</b></td>
      <td class="num" style="font-weight:800;color:${col}">${f.q.toFixed(1)}%</td>
      <td>${gauge}</td>
      <td class="ctr">${trackBdg}</td>
    </tr>`;
  }).join('');

  // ── C3 · Automated Retraining + regression gate (AC-05) ──
  // monthly cadence; a candidate is promoted only if it beats the incumbent on
  // held-out hourly accuracy (AR-03). Otherwise the incumbent stays.
  const RT_LAST = 'May 1, 2026';
  const RT_NEXT = 'Jul 1, 2026';
  const RETRAIN = [
    {target:'Entry Gates hourly load',     inc:95.6, cand:96.1},
    {target:'Check-In hourly load',        inc:91.8, cand:92.4},
    {target:'Security (PESC) hourly load', inc:90.2, cand:91.1},
    {target:'Immigration hourly load',     inc:88.6, cand:89.4},
    {target:'Security 30-min intervals',   inc:88.0, cand:87.3},  // candidate worse → gate FAILS, held
  ];

  const rtPass = RETRAIN.filter(r=>r.cand>r.inc).length;
  const rtFail = RETRAIN.length - rtPass;

  document.getElementById('a-rt-kpis').innerHTML = [
    ['Cadence',          'Monthly',       'auto-retrain · AC-05', 'accent'],
    ['Last Retrained',   RT_LAST,         'completed run', ''],
    ['Next Scheduled',   RT_NEXT,         'in '+rtFail+' held + '+rtPass+' promoted', ''],
    ['Regression Gate',  rtPass+' pass · '+rtFail+' fail', 'candidate must beat incumbent', ''],
  ].map(([l,v,s,a])=>`<div class="mini ${a}"><div class="mini-lab">${l}</div>
      <div class="mini-val" style="font-size:16px">${v}</div>
      <div class="mini-sub">${s}</div></div>`).join('');

  document.querySelector('#a-rt-tbl tbody').innerHTML = RETRAIN.map(r=>{
    const delta = +(r.cand - r.inc).toFixed(1);
    const pass = r.cand > r.inc;
    const dCol = pass ? 'var(--green)' : 'var(--red)';
    const gateBdg = pass
      ? '<span class="bdg b-low" style="padding:2px 8px">Pass · ships</span>'
      : '<span class="bdg b-high" style="padding:2px 8px">Fail · held</span>';
    return `<tr>
      <td><b>${r.target}</b></td>
      <td class="num dim">${r.inc.toFixed(1)}%</td>
      <td class="num" style="font-weight:800;color:${accColor(r.cand)}">${r.cand.toFixed(1)}%</td>
      <td class="num" style="font-weight:800;color:${dCol}">${delta>0?'+':''}${delta.toFixed(1)}</td>
      <td class="ctr">${gateBdg}</td>
    </tr>`;
  }).join('');

  // ── D · Prediction API (RT-03) ──
  // escape angle brackets so path placeholders like <date> render literally (not as DOM elements)
  const esc = s => s.replace(/</g,'&lt;').replace(/>/g,'&gt;');
  document.querySelector('#a-api-tbl tbody').innerHTML = API.map(([m,ep,ret])=>{
    const mc = m==='GET' ? 't-blue' : 't-amber';
    return `<tr>
      <td class="ctr"><span class="tag ${mc}">${m}</span></td>
      <td class="mono" style="font-size:11.5px;color:var(--txt)">${esc(ep)}</td>
      <td class="dim" style="font-size:11px">${esc(ret)}</td>
    </tr>`;
  }).join('');

})();
