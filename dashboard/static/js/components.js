/* POD signature SVG components — the visual grammar of the board.
   Every metric is demand-against-capacity, never a raw count.        */
const SVGNS = 'http://www.w3.org/2000/svg';
const BANDCOL = { acceptable: '#34d399', medium: '#fbbf24', high: '#f87171' };
const SEGCOL = { Domestic: '#22d3ee', International: '#f59e0b', shared: '#8aa0c8' };

function el(tag, attrs, parent) {
  const n = document.createElementNS(SVGNS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(n);
  return n;
}

function ensureHatch(svg, id, color) {
  let defs = svg.querySelector('defs');
  if (!defs) defs = el('defs', {}, svg);
  if (defs.querySelector('#' + id)) return;
  const p = el('pattern', { id, width: 5, height: 5, patternTransform: 'rotate(45)', patternUnits: 'userSpaceOnUse' }, defs);
  el('rect', { width: 5, height: 5, fill: 'transparent' }, p);
  el('line', { x1: 0, y1: 0, x2: 0, y2: 5, stroke: color, 'stroke-width': 2, opacity: .8 }, p);
}

/* ── THE STACK — signature capacity gauge ──────────────────────
   d: {pax, lanes_needed, raw_needed, deficit, capacity, band, staffed, at_capacity}
   opts: {w, h, label, sub, segment, showDeficit} */
function drawStack(host, d, opts = {}) {
  host.innerHTML = '';
  const w = opts.w || 64, h = opts.h || 150;
  const capH = h * 0.78;                       // capacity column height
  const deficit = d.deficit || Math.max(0, (d.raw_needed || 0) - d.capacity);
  const overflowH = deficit > 0 ? h * 0.16 : 0;
  const svg = el('svg', { viewBox: `0 0 ${w} ${h}`, width: w, height: h, preserveAspectRatio: 'xMidYMax meet', class: 'stack-svg' }, host);
  ensureHatch(svg, 'def-hatch', '#f87171');

  const colW = Math.min(w * 0.62, 30), x = (w - colW) / 2;
  const capTop = overflowH + 6;
  const col = BANDCOL[d.band] || '#34d399';
  const fillFrac = d.capacity > 0 ? Math.min(d.lanes_needed / d.capacity, 1) : 0;

  // capacity track (remaining headroom)
  el('rect', { x, y: capTop, width: colW, height: capH, rx: 5, fill: 'rgba(255,255,255,.05)', stroke: 'rgba(255,255,255,.1)', 'stroke-width': 1 }, svg);
  // filled = lanes_needed
  const fh = capH * fillFrac;
  el('rect', { x, y: capTop + capH - fh, width: colW, height: fh, rx: 5, fill: col, opacity: .92 }, svg);
  // glow on breach
  if (d.band === 'high') el('rect', { x, y: capTop + capH - fh, width: colW, height: fh, rx: 5, fill: col, opacity: .25, style: 'filter:blur(4px)' }, svg);
  // DEFICIT cap (hatched, above the ceiling) — only when uncapped demand exceeds capacity
  if (deficit > 0) {
    el('rect', { x, y: 4, width: colW, height: overflowH, rx: 3, fill: 'url(#def-hatch)', stroke: '#f87171', 'stroke-width': 1 }, svg);
    el('line', { x1: x - 3, y1: capTop, x2: x + colW + 3, y2: capTop, stroke: '#f87171', 'stroke-width': 1.4, 'stroke-dasharray': '3 2' }, svg);
  }
  // staffed tick (operator's current lanes)
  if (d.staffed != null && d.capacity > 0) {
    const sy = capTop + capH - capH * Math.min(d.staffed / d.capacity, 1);
    el('line', { x1: x - 4, y1: sy, x2: x + colW + 4, y2: sy, stroke: '#e8eef7', 'stroke-width': 1.6 }, svg);
    el('circle', { cx: x + colW + 4, cy: sy, r: 2, fill: '#e8eef7' }, svg);
  }

  // overlay text
  if (opts.label !== false) {
    const wrap = document.createElement('div');
    wrap.className = 'stack-cap';
    wrap.innerHTML = `<b style="color:${col}">${d.lanes_needed}</b><span>/${d.capacity}</span>` +
      (deficit > 0 ? `<i class="def">+${deficit}</i>` : '');
    host.appendChild(wrap);
  }
}

/* ── 24h Band Ribbon — capacity-deficit cells across the day ──── */
function drawBandRibbon(host, hours, opts = {}) {
  host.innerHTML = '';
  const n = 24, gap = 2, w = host.clientWidth || 480, cellW = (w - gap * (n - 1)) / n, hgt = opts.h || 26;
  const svg = el('svg', { viewBox: `0 0 ${w} ${hgt}`, width: '100%', height: hgt, class: 'ribbon-svg' }, host);
  ensureHatch(svg, 'rib-hatch', '#f87171');
  hours.forEach((c, i) => {
    const x = i * (cellW + gap);
    el('rect', { x, y: 0, width: cellW, height: hgt, rx: 3, fill: BANDCOL[c.band] || '#34d399', opacity: c.band === 'acceptable' ? .35 : .85,
      'data-h': i, class: 'rib-cell' }, svg);
    if (c.at_capacity) el('rect', { x, y: 0, width: cellW, height: hgt, rx: 3, fill: 'url(#rib-hatch)' }, svg);
    if (opts.nowHour === i) el('rect', { x: x - 1, y: -1, width: cellW + 2, height: hgt + 2, rx: 3, fill: 'none', stroke: '#5b79e8', 'stroke-width': 2 }, svg);
  });
  return svg;
}

/* ── Flow Rail — touchpoints in journey order, weighted connectors ── */
function drawFlowRail(host, nodes, opts = {}) {
  // nodes: [{key,label,d?,segment,status?,flow?}]  d = stack data at scrubbed hour
  host.innerHTML = '';
  const horizontal = opts.horizontal;
  const wrap = document.createElement('div');
  wrap.className = 'rail ' + (horizontal ? 'rail-h' : 'rail-v');
  nodes.forEach((node, i) => {
    if (i > 0) {
      const conn = document.createElement('div');
      conn.className = 'rail-conn';
      const flow = node.flowIn || 0, maxFlow = opts.maxFlow || 1;
      const thick = 2 + Math.min(flow / maxFlow, 1) * 10;
      conn.style.setProperty('--thick', thick + 'px');
      wrap.appendChild(conn);
    }
    const nd = document.createElement('div');
    nd.className = 'rail-node' + (node.status === 'awaiting_data' ? ' node-stub' : '') + (node.terminal ? ' node-term' : '');
    nd.dataset.key = node.key;
    nd.dataset.segment = node.segment || 'shared';
    if (node.status === 'awaiting_data') {
      nd.innerHTML = `<div class="node-stack stub"></div><div class="node-lab">${node.label}</div><div class="node-stub-tag">awaiting data</div>`;
    } else if (node.terminal) {
      nd.innerHTML = `<div class="node-term-glyph">→</div><div class="node-lab">${node.label}</div>`;
    } else {
      const sh = document.createElement('div'); sh.className = 'node-stack';
      nd.appendChild(sh);
      const lab = document.createElement('div'); lab.className = 'node-lab';
      lab.innerHTML = node.label + (node.derived ? ' <span class="prov" title="derived from PESC ratio">≈</span>' : '');
      nd.appendChild(lab);
      if (node.d) drawStack(sh, node.d, { w: 56, h: 120 });
    }
    if (opts.onClick) nd.onclick = () => opts.onClick(node);
    wrap.appendChild(nd);
  });
  host.appendChild(wrap);
}

/* ── Transfer Sankey — ribbons terminating in downstream stacks ── */
function drawSankey(host, flows, opts = {}) {
  // flows: [{short,label,total,feeds,color}]
  host.innerHTML = '';
  const w = host.clientWidth || 700, h = opts.h || 300;
  const svg = el('svg', { viewBox: `0 0 ${w} ${h}`, width: '100%', height: h }, host);
  const maxT = Math.max(...flows.map(f => f.total), 1);
  const lx = w * 0.11, rx = w * 0.52;
  const srcY = { 'Domestic': h * 0.3, 'International': h * 0.7 };
  // source labels
  el('text', { x: lx, y: srcY.Domestic - 22, fill: '#22d3ee', 'font-size': 11, 'font-weight': 700, 'text-anchor': 'middle' }, svg).textContent = 'DOMESTIC ARR';
  el('text', { x: lx, y: srcY.International - 22, fill: '#f59e0b', 'font-size': 11, 'font-weight': 700, 'text-anchor': 'middle' }, svg).textContent = 'INTL ARR';
  flows.forEach((f, i) => {
    const srcSeg = f.short[0] === 'D' ? 'Domestic' : 'International';
    const sy = srcY[srcSeg] + (i - 1) * 14;
    const ty = h * (0.22 + i * 0.28);
    const tw = 3 + (f.total / maxT) * 34;
    const col = f.short === 'D-D' ? '#22d3ee' : f.short === 'I-D' ? '#a78bfa' : '#f59e0b';
    const path = `M ${lx} ${sy} C ${w * 0.32} ${sy}, ${w * 0.38} ${ty}, ${rx} ${ty}`;
    el('path', { d: path, fill: 'none', stroke: col, 'stroke-width': tw, opacity: .5, 'stroke-linecap': 'round' }, svg);
    el('circle', { cx: lx, cy: sy, r: 4, fill: col }, svg);
    // terminus = the downstream stack it feeds
    el('rect', { x: rx, y: ty - 16, width: 11, height: 32, rx: 2, fill: col, opacity: .85 }, svg);
    el('text', { x: rx + 18, y: ty - 2, fill: '#e8eef7', 'font-size': 12, 'font-weight': 700 }, svg).textContent = `${f.short} · ${f.label}`;
    el('text', { x: rx + 18, y: ty + 14, fill: '#7c8db0', 'font-size': 10.5 }, svg).textContent = `${f.total.toLocaleString()} pax → ${f.feedsLabel}`;
  });
  return svg;
}

/* ── PESC Domestic/International Lane Wall ──────────────────────── */
function drawLaneWall(host, domLanes, intlLanes, domCap, intlCap) {
  host.innerHTML = '';
  const mk = (lanes, cap, label, color) => {
    const block = document.createElement('div'); block.className = 'lanewall-block';
    block.innerHTML = `<div class="lw-head" style="color:${color}">${label} · ${lanes}/${cap}</div>`;
    const grid = document.createElement('div'); grid.className = 'lw-grid';
    for (let i = 0; i < cap; i++) {
      const cell = document.createElement('div');
      cell.className = 'lw-cell' + (i < lanes ? ' on' : '');
      cell.style.setProperty('--c', color);
      grid.appendChild(cell);
    }
    block.appendChild(grid);
    return block;
  };
  host.appendChild(mk(domLanes, domCap, 'Domestic', '#22d3ee'));
  host.appendChild(mk(intlLanes, intlCap, 'International', '#f59e0b'));
}

/* ── Terminal Map — stylized spatial schematic (blend) ─────────── */
function drawTerminalMap(host, tps, opts = {}) {
  host.innerHTML = '';
  const w = 760, h = 300;
  const svg = el('svg', { viewBox: `0 0 ${w} ${h}`, width: '100%', class: 'tmap' }, host);
  // terminal outline
  el('rect', { x: 8, y: 8, width: w - 16, height: h - 16, rx: 16, fill: 'rgba(255,255,255,.015)', stroke: 'rgba(255,255,255,.08)', 'stroke-width': 1 }, svg);
  // landside → airside axis label
  el('text', { x: 20, y: 26, fill: '#475873', 'font-size': 10, 'font-weight': 700 }, svg).textContent = 'LANDSIDE';
  el('text', { x: w - 70, y: 26, fill: '#475873', 'font-size': 10, 'font-weight': 700 }, svg).textContent = 'AIRSIDE';

  // zone positions (stylized journey geography)
  const zones = [
    { key: 'Entry', x: 60, y: 150, label: 'Entry' },
    { key: 'CheckIn', x: 200, y: 150, label: 'Check-In' },
    { key: 'Emigration', x: 360, y: 80, label: 'Emigration', seg: 'International' },
    { key: 'PESC_Intl', x: 520, y: 80, label: 'Security Intl', seg: 'International' },
    { key: 'PESC_Domestic', x: 520, y: 220, label: 'Security Dom', seg: 'Domestic' },
    { key: 'Immigration', x: 360, y: 250, label: 'Immigration', seg: 'International' },
    { key: 'Customs', x: 200, y: 250, label: 'Customs', seg: 'International' },
    { key: 'Boarding', x: 680, y: 150, label: 'Gates', terminal: true },
  ];
  // connectors (journey paths)
  const link = (a, b, col) => {
    const za = zones.find(z => z.key === a), zb = zones.find(z => z.key === b);
    if (za && zb) el('line', { x1: za.x, y1: za.y, x2: zb.x, y2: zb.y, stroke: col, 'stroke-width': 1.5, opacity: .3, 'stroke-dasharray': '4 3' }, svg);
  };
  link('Entry', 'CheckIn', '#8aa0c8');
  link('CheckIn', 'Emigration', '#f59e0b'); link('Emigration', 'PESC_Intl', '#f59e0b'); link('PESC_Intl', 'Boarding', '#f59e0b');
  link('CheckIn', 'PESC_Domestic', '#22d3ee'); link('PESC_Domestic', 'Boarding', '#22d3ee');
  link('Immigration', 'Customs', '#f59e0b');

  zones.forEach(z => {
    const tp = tps[z.key];
    const g = el('g', { class: 'tmap-zone', 'data-key': z.key, style: 'cursor:pointer' }, svg);
    let col = '#475873', r = 16, glow = 0;
    if (tp && tp.hourly && !z.terminal) {
      const cell = tp.hourly[opts.hour || 0];
      col = BANDCOL[cell.band] || '#34d399';
      r = 14 + Math.min(cell.lanes_needed / cell.capacity, 1) * 14;
      glow = cell.band === 'high' ? 1 : 0;
    } else if (z.terminal) { col = '#5b79e8'; }
    else if (tp && tp.status === 'awaiting_data') { col = '#475873'; }
    if (glow) el('circle', { cx: z.x, cy: z.y, r: r + 6, fill: col, opacity: .25, style: 'filter:blur(5px)' }, svg);
    el('circle', { cx: z.x, cy: z.y, r, fill: col, opacity: z.terminal ? .5 : .8, stroke: 'rgba(255,255,255,.2)', 'stroke-width': 1 }, g);
    el('text', { x: z.x, y: z.y + r + 13, fill: '#b9c6dd', 'font-size': 10, 'font-weight': 600, 'text-anchor': 'middle' }, g).textContent = z.label;
    if (opts.onZone && !z.terminal) g.onclick = () => opts.onZone(z.key);
  });
  return svg;
}
