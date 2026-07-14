/* Command Board orchestration — SPA depths driven by one scrubbed hour. */
let BRIEF = null, VIEW = 'rails', FOCUS = null;   // FOCUS: null | 'Domestic' | 'International' | 'transfers'

const SEG_RAILS = {
  Domestic:      { dep: ['PESC_Domestic', 'Boarding'], arr: [] },
  International:  { dep: ['Emigration', 'PESC_Intl', 'Boarding'], arr: ['Immigration', 'Customs'] },
};
const BOARDING = { key: 'Boarding', label: 'Gates', terminal: true };

async function onDateChange() {
  document.getElementById('board-hero').innerHTML = '<div class="skel" style="height:120px"></div>';
  BRIEF = await api(`/api/brief/${POD_DATE}`);
  Scrubber.mount('scrubber-host', BRIEF, render);
  // Scrubber.mount calls set() which calls render(hour)
}

function tpNode(key, hour) {
  const tp = BRIEF.touchpoints[key];
  if (!tp) return { key, label: key, status: 'awaiting_data' };
  if (tp.status === 'awaiting_data')
    return { key, label: tp.label, status: 'awaiting_data', segment: tp.segment };
  return {
    key, label: tp.label, segment: tp.segment,
    derived: tp.derived, d: tp.hourly[hour],
    flowIn: tp.hourly[hour].pax,
  };
}

function render(hour) {
  if (!BRIEF) return;
  renderHero(hour);
  renderAlerts(hour);
  renderCrumbs();
  if (FOCUS === 'transfers') return renderTransfers(hour);
  if (FOCUS === 'Domestic' || FOCUS === 'International') return renderSegmentFocus(FOCUS, hour);
  if (VIEW === 'map') return renderMap(hour);
  renderRails(hour);
}

/* ── Hero + Narrator ── */
function renderHero(hour) {
  const host = document.getElementById('board-hero');
  const h = BRIEF.hero[hour];
  const head = BRIEF.headline;
  const tone = head.tone === 'at_capacity' ? 'rd' : head.tone === 'fixable' ? 'am' : 'gn';
  host.innerHTML = `
    <div class="hero-stack" id="hero-stack"></div>
    <div class="hero-body">
      <div class="hero-narr tone-${tone}">
        <span class="narr-dot"></span>${head.text}
      </div>
      <div class="hero-metrics">
        <div><b class="mono">${h.pax.toLocaleString()}</b><span>passengers · ${String(hour).padStart(2,'0')}:00</span></div>
        <div><b class="mono">${h.lanes_needed}/${h.capacity}</b><span>lanes needed vs capacity</span></div>
        <div><b class="mono" style="color:${h.deficit?'var(--rd)':'var(--gn)'}">${h.deficit ? '+'+h.deficit+' short' : 'within capacity'}</b><span>airport-wide</span></div>
        ${BRIEF.is_holiday ? '<div class="hol-chip">★ Holiday</div>' : ''}
      </div>
    </div>`;
  drawStack(document.getElementById('hero-stack'), h, { w: 80, h: 130 });
}

/* ── Alert rail ── */
function renderAlerts(hour) {
  const host = document.getElementById('alert-rail');
  if (!BRIEF.alerts.length) {
    host.innerHTML = '<div class="alert-empty">✓ All clear<br><span>No breaches predicted today</span></div>';
    return;
  }
  host.innerHTML = '<div class="alert-title">ALERTS · WORST FIRST</div>' + BRIEF.alerts.map(a => `
    <div class="alert-card v-${a.verdict}" data-key="${a.key}">
      <div class="alert-head">${a.label}<span class="alert-badge">${a.verdict === 'at_capacity' ? 'AT CEILING' : 'FIXABLE'}</span></div>
      <div class="alert-sent">${a.sentence}</div>
      <div class="alert-act">▸ ${a.action}</div>
    </div>`).join('');
  host.querySelectorAll('.alert-card').forEach(c => c.onclick = () => openInspector(c.dataset.key));
}

function renderCrumbs() {
  const c = document.getElementById('crumbs');
  if (!FOCUS) { c.innerHTML = ''; return; }
  const name = FOCUS === 'transfers' ? 'Transfers' : FOCUS;
  c.innerHTML = `<button class="crumb" onclick="clearFocus()">← Command Board</button> <span class="crumb-sep">/</span> <b>${name}</b>`;
}
function clearFocus() { FOCUS = null; render(Scrubber.get()); }

/* ── Depth 0: Flow Rails (shared spine → two segments) ── */
function renderRails(hour) {
  const stage = document.getElementById('board-stage');
  stage.innerHTML = `
    <div class="shared-spine">
      <div class="spine-tag">SHARED · ALL PASSENGERS <span class="prov" title="Domestic/International share derived from PESC ratio">≈ split derived</span></div>
      <div id="spine-rail"></div>
    </div>
    <div class="split-arrow">┌─ diverges by segment ─┐</div>
    <div class="seg-cols">
      <div class="seg-col seg-dom">
        <button class="seg-head" data-seg="Domestic"><span class="seg-dot" style="background:var(--cy)"></span>DOMESTIC<div class="seg-roll" id="roll-Domestic"></div></button>
        <div id="rail-Domestic"></div>
      </div>
      <div class="seg-col seg-intl">
        <button class="seg-head" data-seg="International"><span class="seg-dot" style="background:var(--am)"></span>INTERNATIONAL<div class="seg-roll" id="roll-International"></div></button>
        <div id="rail-International"></div>
      </div>
    </div>
    <div class="interchange" id="interchange"></div>`;

  drawFlowRail(document.getElementById('spine-rail'),
    [tpNode('Entry', hour), tpNode('CheckIn', hour)],
    { horizontal: true, maxFlow: heroMaxPax(), onClick: n => openInspector(n.key) });

  for (const seg of ['Domestic', 'International']) {
    const keys = [...SEG_RAILS[seg].dep.filter(k => k !== 'Boarding'), ...SEG_RAILS[seg].arr];
    const nodes = SEG_RAILS[seg].dep.map(k => k === 'Boarding' ? { ...BOARDING } : tpNode(k, hour));
    drawFlowRail(document.getElementById('rail-' + seg), nodes,
      { horizontal: true, maxFlow: heroMaxPax(), onClick: n => n.terminal || openInspector(n.key) });
    drawRoll(seg, hour);
  }

  // arrivals sub-rail for International
  const intlRail = document.getElementById('rail-International');
  if (SEG_RAILS.International.arr.length) {
    const arrWrap = document.createElement('div');
    arrWrap.className = 'arr-rail';
    arrWrap.innerHTML = '<div class="arr-tag">ARRIVALS</div><div id="arr-International"></div>';
    intlRail.appendChild(arrWrap);
    drawFlowRail(document.getElementById('arr-International'),
      SEG_RAILS.International.arr.map(k => tpNode(k, hour)),
      { horizontal: true, onClick: n => openInspector(n.key) });
  }

  stage.querySelectorAll('.seg-head').forEach(b => b.onclick = () => { FOCUS = b.dataset.seg; render(Scrubber.get()); });
  renderInterchange(hour);
}

function heroMaxPax() { return Math.max(...BRIEF.hero.map(h => h.pax), 1); }

function drawRoll(seg, hour) {
  // roll-up stack: sum lanes_needed vs capacity for the segment's prescribed TPs
  const keys = [...SEG_RAILS[seg].dep, ...SEG_RAILS[seg].arr].filter(k => BRIEF.touchpoints[k] && BRIEF.touchpoints[k].hourly);
  let ln = 0, cap = 0, raw = 0, staffed = 0, pax = 0;
  keys.forEach(k => { const c = BRIEF.touchpoints[k].hourly[hour]; ln += c.lanes_needed; cap += c.capacity; raw += c.raw_needed; staffed += c.staffed || 0; pax += c.pax; });
  const band = raw > cap ? 'high' : raw > cap * 0.8 ? 'medium' : 'acceptable';
  const host = document.getElementById('roll-' + seg);
  if (host) drawStack(host, { pax, lanes_needed: ln, raw_needed: raw, deficit: Math.max(0, raw - cap), capacity: cap, band, staffed, at_capacity: raw >= cap }, { w: 50, h: 70, label: false });
}

/* ── Interchange (transfers hint) ── */
function renderInterchange(hour) {
  const host = document.getElementById('interchange');
  const t = BRIEF.transfers;
  host.innerHTML = `<button class="inter-btn" onclick="FOCUS='transfers';render(Scrubber.get())">
    <span class="inter-tag">⇄ TRANSFERS</span>` +
    Object.entries(t).map(([k, v]) => `<span class="inter-flow"><b>${k}</b> ${v.hourly[hour].toLocaleString()}<i>→ ${BRIEF.touchpoints[v.feeds]?.label || v.feeds}</i></span>`).join('') +
    `<span class="inter-more">open ›</span></button>`;
}

/* ── Depth 1: Segment Focus ── */
function renderSegmentFocus(seg, hour) {
  const stage = document.getElementById('board-stage');
  const keys = ['Entry', 'CheckIn', ...SEG_RAILS[seg].dep.filter(k => k !== 'Boarding')];
  const arrKeys = SEG_RAILS[seg].arr;
  const col = seg === 'Domestic' ? 'var(--cy)' : 'var(--am)';
  stage.innerHTML = `
    <div class="segfocus">
      <div class="segfocus-head" style="border-color:${col}">
        <h3 style="color:${col}">${seg} ${seg === 'International' ? 'Departures' : ''}</h3>
        <span class="sf-sub">overall-day peak vs scrubbed hour · click a node to inspect</span>
      </div>
      <div class="sf-rail" id="sf-dep"></div>
      ${arrKeys.length ? `<div class="segfocus-head" style="border-color:${col};margin-top:18px"><h3 style="color:${col}">${seg} Arrivals</h3></div><div class="sf-rail" id="sf-arr"></div>` : ''}
      <div class="sec-title" style="margin-top:20px">24-HOUR DEMAND-VS-CAPACITY · CASCADE</div>
      <div class="sf-ribbons" id="sf-ribbons"></div>
    </div>`;
  renderSegRail('sf-dep', keys, hour);
  if (arrKeys.length) renderSegRail('sf-arr', arrKeys, hour);
  renderRibbons('sf-ribbons', [...keys, ...arrKeys], hour);
}

function renderSegRail(hostId, keys, hour) {
  const host = document.getElementById(hostId);
  host.innerHTML = '';
  keys.forEach((k, i) => {
    const tp = BRIEF.touchpoints[k];
    if (i > 0) { const a = document.createElement('div'); a.className = 'sf-conn'; host.appendChild(a); }
    const node = document.createElement('div'); node.className = 'sf-node'; node.onclick = () => openInspector(k);
    if (!tp || tp.status === 'awaiting_data') {
      node.classList.add('node-stub');
      node.innerHTML = `<div class="sf-dual stub"></div><div class="node-lab">${tp ? tp.label : k}</div><div class="node-stub-tag">awaiting data</div>`;
      host.appendChild(node); return;
    }
    // dual: overall-day peak vs scrubbed hour
    const peak = tp.hourly.reduce((a, b) => b.lanes_needed > a.lanes_needed ? b : a);
    node.innerHTML = `<div class="sf-dual"><div class="sf-g" data-kind="peak"></div><div class="sf-g" data-kind="now"></div></div>
      <div class="node-lab">${tp.label}${tp.derived ? ' <span class="prov">≈</span>' : ''}</div>
      <div class="sf-glab"><span>day peak</span><span>${String(hour).padStart(2,'0')}:00</span></div>`;
    host.appendChild(node);
    drawStack(node.querySelector('[data-kind=peak]'), peak, { w: 44, h: 92, label: false });
    drawStack(node.querySelector('[data-kind=now]'), tp.hourly[hour], { w: 44, h: 92, label: false });
  });
}

function renderRibbons(hostId, keys, nowHour) {
  const host = document.getElementById(hostId);
  host.innerHTML = '';
  keys.forEach(k => {
    const tp = BRIEF.touchpoints[k];
    if (!tp || !tp.hourly) return;
    const row = document.createElement('div'); row.className = 'ribbon-row';
    row.innerHTML = `<div class="ribbon-lab">${tp.label}</div><div class="ribbon-host"></div>`;
    host.appendChild(row);
    drawBandRibbon(row.querySelector('.ribbon-host'), tp.hourly, { nowHour });
  });
}

/* ── Depth 1: Transfers Focus ── */
function renderTransfers(hour) {
  const stage = document.getElementById('board-stage');
  stage.innerHTML = `<div class="segfocus">
    <div class="segfocus-head" style="border-color:var(--vi)"><h3 style="color:var(--vi)">Transfer Interchange</h3>
      <span class="sf-sub">where connecting passengers land & what to pre-stage</span></div>
    <div id="sankey-host" class="sankey-host"></div>
    <div class="sec-title" style="margin-top:8px">FLOW TIMING & ACTION</div>
    <div id="tr-cards" class="tr-cards"></div>
  </div>`;
  const flows = Object.entries(BRIEF.transfers).map(([k, v]) => ({
    short: k, label: v.label, total: v.total, feeds: v.feeds,
    feedsLabel: BRIEF.touchpoints[v.feeds]?.label || v.feeds,
  }));
  drawSankey(document.getElementById('sankey-host'), flows, { h: 280 });

  document.getElementById('tr-cards').innerHTML = Object.entries(BRIEF.transfers).map(([k, v]) => {
    const feedTp = BRIEF.touchpoints[v.feeds];
    const feedCell = feedTp && feedTp.hourly ? feedTp.hourly[v.peak_hour] : null;
    const loadPct = feedCell ? Math.round(feedCell.lanes_needed / feedCell.capacity * 100) : null;
    return `<div class="tr-card">
      <div class="tr-h"><b>${k}</b> ${v.label}</div>
      <div class="tr-metric mono">${v.total.toLocaleString()} <span>pax/day · peak ${String(v.peak_hour).padStart(2,'0')}:00</span></div>
      <div class="tr-act">▸ Pre-stage for ${k} wave at ${String(v.peak_hour).padStart(2,'0')}:00${loadPct!=null?` — feeds ${feedTp.label} (${loadPct}% capacity)`:''}</div>
    </div>`;
  }).join('');
}

/* ── Terminal Map (blend) ── */
function renderMap(hour) {
  const stage = document.getElementById('board-stage');
  stage.innerHTML = '<div class="map-wrap" id="map-wrap"></div><div class="map-legend">' +
    '<span class="st st-ok">within capacity</span><span class="st st-wait">near capacity</span><span class="st" style="background:rgba(239,68,68,.12);color:var(--rd)">breach</span>' +
    '<span style="margin-left:auto;color:var(--dim);font-size:11px">node size = lanes needed · click a zone to inspect</span></div>';
  drawTerminalMap(document.getElementById('map-wrap'), BRIEF.touchpoints, { hour, onZone: openInspector });
}

/* ── Depth 2: Inspector ── */
let SIM_OPEN = false;
function openInspector(key) {
  const tp = BRIEF.touchpoints[key];
  if (!tp) return;
  const insp = document.getElementById('inspector');
  const hour = Scrubber.get();
  if (tp.status === 'awaiting_data') {
    insp.innerHTML = `<button class="insp-close" onclick="closeInspector()">✕</button>
      <h3>${tp.label}</h3><div class="await" style="margin-top:14px"><h3>Awaiting data</h3><p>${tp.detail}</p></div>`;
    return showInspector();
  }
  const b = tp.brief || {};
  const cell = tp.hourly[hour];
  const verdictCls = b.verdict === 'at_capacity' ? 'rd' : b.verdict === 'fixable' ? 'am' : 'gn';
  insp.innerHTML = `
    <button class="insp-close" onclick="closeInspector()">✕</button>
    <div class="insp-head">
      <h3>${tp.label}</h3>
      <span class="seg-chip seg-${(tp.segment||'shared').toLowerCase()}">${tp.segment || 'shared'}</span>
      ${tp.derived ? '<span class="prov-tag">≈ derived split</span>' : ''}
    </div>
    <div class="insp-narr tone-${verdictCls}">${b.sentence || ''} <b>▸ ${b.action || ''}</b></div>
    <div class="insp-now">
      <div class="insp-stack" id="insp-stack"></div>
      <div class="insp-now-meta">
        <div><b class="mono">${cell.pax.toLocaleString()}</b><span>pax at ${String(hour).padStart(2,'0')}:00</span></div>
        <div><b class="mono">${cell.lanes_needed}/${cell.capacity}</b><span>lanes vs capacity</span></div>
        <div><b class="mono">${cell.wait_minutes}m</b><span>expected wait</span></div>
        <div><b class="mono">${cell.staffed ?? '—'}</b><span>staffed now</span></div>
      </div>
    </div>
    <div class="sec-title">24-HOUR DEMAND vs CAPACITY</div>
    <div class="insp-ribbon" id="insp-ribbon"></div>
    <div id="insp-lanewall"></div>
    <div class="sec-title">WHAT-IF SIMULATE</div>
    <div class="insp-sim" id="insp-sim"></div>`;
  drawStack(document.getElementById('insp-stack'), cell, { w: 70, h: 120 });
  drawBandRibbon(document.getElementById('insp-ribbon'), tp.hourly, { nowHour: hour, h: 30 });

  if (key.startsWith('PESC')) renderLaneWall(hour);
  renderSimDrawer(key);
  showInspector();
}

function renderLaneWall(hour) {
  const host = document.getElementById('insp-lanewall');
  const dom = BRIEF.touchpoints['PESC_Domestic'].hourly[hour];
  const intl = BRIEF.touchpoints['PESC_Intl'].hourly[hour];
  host.innerHTML = '<div class="sec-title">SECURITY LANE WALL · DOMESTIC vs INTERNATIONAL</div><div class="lanewall" id="lanewall"></div>';
  drawLaneWall(document.getElementById('lanewall'), dom.lanes_needed, intl.lanes_needed, dom.capacity, intl.capacity);
}

const SIM_TP_MAP = { PESC_Domestic: 'PESC', PESC_Intl: 'PESC' };
function renderSimDrawer(key) {
  const host = document.getElementById('insp-sim');
  const simTp = SIM_TP_MAP[key] || key;
  host.innerHTML = `
    <div class="sim-ctl"><label>Wait threshold <b id="s-thr-v">—</b></label><input type="range" id="s-thr" min="1" max="20" value="5"></div>
    <div class="sim-ctl"><label>Available resources <b id="s-res-v">—</b></label><input type="range" id="s-res" min="1" max="60" value="40"></div>
    <button class="run-sim" id="run-sim">Run simulation</button>
    <div id="sim-out" class="sim-out"></div>`;
  document.getElementById('s-thr').oninput = e => document.getElementById('s-thr-v').textContent = e.target.value + ' min';
  document.getElementById('s-res').oninput = e => document.getElementById('s-res-v').textContent = e.target.value;
  document.getElementById('s-thr-v').textContent = '5 min';
  document.getElementById('s-res-v').textContent = '40';
  let deb;
  const run = async () => {
    const body = { tp: simTp, date: POD_DATE, thr_wait_minutes: +document.getElementById('s-thr').value, available_resources: +document.getElementById('s-res').value, closed_zones: [] };
    const r = await api('/api/simulate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (r.error) { toast(r.error); return; }
    const b = r.baseline_summary, s = r.simulated_summary;
    document.getElementById('sim-out').innerHTML = `
      <div class="sim-cmp"><span>Breach hours</span><b>${b.breach_hours} → <i style="color:${s.breach_hours>b.breach_hours?'var(--rd)':'var(--gn)'}">${s.breach_hours}</i></b></div>
      <div class="sim-cmp"><span>Peak wait</span><b>${b.peak_wait_minutes}m → <i style="color:${s.peak_wait_minutes>b.peak_wait_minutes?'var(--rd)':'var(--gn)'}">${s.peak_wait_minutes}m</i></b></div>
      <div class="sim-cmp"><span>Peak lanes</span><b>${b.peak_total_lanes} → ${s.peak_total_lanes}</b></div>`;
  };
  document.getElementById('run-sim').onclick = run;
  ['s-thr', 's-res'].forEach(id => document.getElementById(id).addEventListener('input', () => { clearTimeout(deb); deb = setTimeout(run, 450); }));
  run();
}

function showInspector() { document.getElementById('inspector').classList.add('open'); document.getElementById('insp-scrim').classList.add('on'); }
function closeInspector() { document.getElementById('inspector').classList.remove('open'); document.getElementById('insp-scrim').classList.remove('on'); }

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('insp-scrim').onclick = closeInspector;
  document.getElementById('view-toggle').onclick = e => {
    const b = e.target.closest('button'); if (!b) return;
    VIEW = b.dataset.v;
    document.querySelectorAll('#view-toggle button').forEach(x => x.classList.toggle('on', x === b));
    FOCUS = null; render(Scrubber.get());
  };
});
