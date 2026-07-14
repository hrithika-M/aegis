/* Single-page Summary dashboard — everything visible, no drilling. */
let SB = null, lpChart = null, LP_VIEW = 'day', KPI = {};

const HM_BANDS = [
  { max: 10, c: '#34d399' }, { max: 20, c: '#a3c948' },
  { max: 30, c: '#f59e0b' }, { max: 45, c: '#f87171' }, { max: 1e9, c: '#dc2626' },
];
function hmColor(m) { for (const b of HM_BANDS) if (m <= b.max) return b.c; return '#dc2626'; }

async function onDateChange() {
  document.getElementById('kpi-strip').innerHTML = '<div class="skel" style="height:96px"></div>';
  SB = await api(`/api/brief/${POD_DATE}`);
  if (!Object.keys(KPI).length) KPI = (await api('/api/config/kpi')).kpi;
  renderKPIs();
  renderLoad();
  renderHeatmap();
  renderResource();
  renderGlance();
  renderDataSources();
}

/* ── KPI strip ── */
function renderKPIs() {
  const hero = SB.hero;
  const totalPax = SB.summary.pred || hero.reduce((a, h) => a + h.pax, 0);
  const peak30 = Math.max(...SB.airport_intervals);
  const peak30slot = SB.airport_intervals.indexOf(peak30);
  // avg wait across prescribed touchpoints/hours
  let ws = 0, wn = 0, peakLanes = 0;
  for (const k in SB.touchpoints) {
    const tp = SB.touchpoints[k]; if (!tp.hourly) continue;
    tp.hourly.forEach(c => { ws += c.wait_minutes; wn++; });
  }
  hero.forEach(h => peakLanes = Math.max(peakLanes, h.lanes_needed));
  const avgWait = wn ? ws / wn : 0;
  const acc = SB.summary.accuracy;
  const slotLabel = `${String(Math.floor(peak30slot / 2)).padStart(2, '0')}:${peak30slot % 2 ? '30' : '00'}`;

  const cards = [
    { ic: '👥', col: '#5b79e8', lab: 'Total Passengers (Day)', val: totalPax.toLocaleString(), sub: SB.is_holiday ? '★ Holiday' : 'predicted' },
    { ic: '⚡', col: '#22d3ee', lab: 'Peak 30-min PAX', val: peak30.toLocaleString(), sub: 'at ' + slotLabel },
    { ic: '⏱', col: '#f59e0b', lab: 'Avg Wait Time (All)', val: avgWait.toFixed(1) + ' min', sub: 'across touchpoints' },
    { ic: '▦', col: '#a78bfa', lab: 'Peak Lanes Needed', val: peakLanes.toLocaleString(), sub: 'airport-wide / hr' },
    { ic: '◎', col: '#34d399', lab: 'POD Accuracy', val: (acc != null ? acc : '—') + '%', sub: 'held-out validation' },
  ];
  document.getElementById('kpi-strip').innerHTML = cards.map(c => `
    <div class="kpi">
      <div class="kpi-ic" style="background:${c.col}22;color:${c.col}">${c.ic}</div>
      <div class="kpi-body">
        <div class="kpi-lab">${c.lab}</div>
        <div class="kpi-val mono">${c.val}</div>
        <div class="kpi-sub">${c.sub}</div>
      </div>
    </div>`).join('') + `
    <div class="kpi kpi-ai">
      <div class="kpi-ai-glow"></div>
      <div><div class="kpi-lab" style="color:#cdd9ff">AI-Powered Predictions</div>
      <div class="kpi-ai-sub">High accuracy · holiday & seasonality aware</div></div>
    </div>`;
}

/* ── Load Prediction chart ── */
function renderLoad() {
  if (lpChart) lpChart.destroy();
  const ctx = document.getElementById('lp-chart').getContext('2d');
  const entry = SB.intervals.Entry, transf = SB.intervals.Transfers;
  let labels, eSeries, tSeries;
  if (LP_VIEW === 'day') {
    labels = [...Array(48).keys()].map(s => s % 4 === 0 ? `${String(Math.floor(s / 2)).padStart(2, '0')}:${s % 2 ? '30' : '00'}` : '');
    eSeries = entry; tSeries = transf;
  } else {
    labels = [...Array(24).keys()].map(h => `${String(h).padStart(2, '0')}:00`);
    eSeries = [...Array(24).keys()].map(h => entry[h * 2] + entry[h * 2 + 1]);
    tSeries = [...Array(24).keys()].map(h => transf[h * 2] + transf[h * 2 + 1]);
  }
  lpChart = lineChart(ctx, labels, [
    dsPred(eSeries, '#22d3ee', ctx, 'Entry Gates (Dep)'),
    dsPred(tSeries, '#a78bfa', ctx, 'Transfers (Connect)'),
  ], { maxTicks: 13 });
}

/* ── Wait Time Heatmap ── */
async function renderHeatmap() {
  const hm = await api(`/api/heatmap/${POD_DATE}`);
  const host = document.getElementById('hm-host');
  const hours = [...Array(24).keys()];
  let html = '<table class="hm-tbl"><thead><tr><th></th>' +
    hours.map(h => `<th>${String(h).padStart(2, '0')}</th>`).join('') + '</tr></thead><tbody>';
  hm.rows.forEach(row => {
    html += `<tr><td class="hm-lab">${row.label}</td>` + row.cells.map(c =>
      `<td class="hm-c" style="background:${hmColor(c.wait_minutes)}" title="${row.label} ${String(c.hour).padStart(2,'0')}:00 · ${c.wait_minutes}m · ${c.pax} pax">${Math.round(c.wait_minutes)}</td>`).join('') + '</tr>';
  });
  host.innerHTML = html + '</tbody></table>';
}

/* ── Resource table ── */
async function renderResource() {
  const rx = await api(`/api/prescription/${POD_DATE}`);
  const hours = [...Array(24).keys()];
  let html = '<thead><tr><th class="rt-tp">Touchpoint</th><th>KPI</th>' +
    hours.map(h => `<th>${String(h).padStart(2, '0')}</th>`).join('') + '<th class="rt-tot">Total</th></tr></thead><tbody>';
  for (const k in rx.touchpoints) {
    const tp = rx.touchpoints[k];
    const total = tp.hours.reduce((a, h) => a + h.lanes_needed, 0);
    html += `<tr><td class="rt-tp">${tp.label}</td><td class="rt-kpi">${tp.kpi.acceptable}m</td>` +
      tp.hours.map(h => {
        const col = h.band === 'high' ? '#f87171' : h.band === 'medium' ? '#f59e0b' : 'var(--mut)';
        return `<td class="mono" style="color:${col}">${h.lanes_needed}</td>`;
      }).join('') + `<td class="rt-tot mono">${total.toLocaleString()}</td></tr>`;
  }
  document.getElementById('res-tbl').innerHTML = html + '</tbody>';
}

/* ── Today at a Glance ── */
function renderGlance() {
  const acc = SB.summary.accuracy || 0;
  let breaches = 0, atcap = 0;
  for (const k in SB.touchpoints) { const tp = SB.touchpoints[k]; if (!tp.hourly) continue; tp.hourly.forEach(c => { if (c.band === 'high') breaches++; if (c.at_capacity) atcap++; }); }
  const health = Math.max(40, Math.round(acc - breaches * 1.5 - atcap * 2));
  const hcol = health >= 85 ? '#34d399' : health >= 70 ? '#f59e0b' : '#f87171';
  const r = 42, circ = 2 * Math.PI * r, off = circ * (1 - health / 100);
  document.getElementById('glance-gauge').innerHTML = `
    <svg width="110" height="110" viewBox="0 0 110 110">
      <circle cx="55" cy="55" r="${r}" stroke="rgba(255,255,255,.07)" stroke-width="9" fill="none"/>
      <circle cx="55" cy="55" r="${r}" stroke="${hcol}" stroke-width="9" fill="none" stroke-linecap="round"
        stroke-dasharray="${circ}" stroke-dashoffset="${off}" transform="rotate(-90 55 55)" style="transition:stroke-dashoffset 1s"/>
      <text x="55" y="52" text-anchor="middle" fill="${hcol}" font-size="22" font-weight="800" font-family="JetBrains Mono">${health}%</text>
      <text x="55" y="70" text-anchor="middle" fill="#7c8db0" font-size="9">${health >= 85 ? 'Excellent' : health >= 70 ? 'Good' : 'Watch'}</text>
    </svg>`;
  const items = [
    { ok: breaches === 0, t: breaches === 0 ? 'Operations Normal' : `${breaches} breach hours` },
    { ok: atcap === 0, t: atcap === 0 ? 'No Capacity Alerts' : `${atcap} at-capacity hours` },
    { ok: acc >= 85, t: acc >= 85 ? 'Predictions On Track' : 'Accuracy below target' },
  ];
  document.getElementById('glance-items').innerHTML = items.map(i =>
    `<div class="gl-item"><span class="gl-dot ${i.ok ? 'ok' : 'bad'}">${i.ok ? '✓' : '!'}</span>${i.t}</div>`).join('');
}

/* ── Integrated Data Sources ── */
async function renderDataSources() {
  const cfg = await api('/api/config/kpi');
  const ds = cfg.data_sources;
  const order = ['AODB', 'CUPPS', 'EBoarding', 'IOTStats', 'DataLake', 'Bookloads', 'Holidays', 'EWS'];
  const stt = { connected: { t: 'Live', c: 'var(--gn)' }, partial: { t: 'Partial', c: 'var(--cy)' }, awaiting_data: { t: 'Pending', c: 'var(--am)' } };
  document.getElementById('ds-bar').innerHTML =
    '<span class="ds-title">Integrated Data Sources</span>' +
    order.filter(k => ds[k]).map(k => { const s = stt[ds[k].status]; return `<span class="ds-item"><i class="ds-dot" style="background:${s.c}"></i>${ds[k].label.split(' (')[0]}<small style="color:${s.c}">${s.t}</small></span>`; }).join('') +
    `<span class="ds-acc">Model Accuracy <b class="mono">${SB.summary.accuracy ?? '—'}%</b></span>`;
}

/* toggle handler */
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('lp-toggle').onclick = e => {
    const b = e.target.closest('button'); if (!b) return;
    LP_VIEW = b.dataset.v;
    document.querySelectorAll('#lp-toggle button').forEach(x => x.classList.toggle('on', x === b));
    renderLoad();
  };
});
