/* POD shared front-end helpers */
const TP_ORDER = ['Entry','CheckIn','Emigration','Immigration','PESC','Transfers'];
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

let POD_DATE = localStorage.getItem('pod_date') || null;

Chart.defaults.color = '#7c8db0';
Chart.defaults.borderColor = 'rgba(255,255,255,.05)';
Chart.defaults.font.family = "'Inter',sans-serif";
Chart.defaults.font.size = 10.5;

function toast(msg){
  const t = document.createElement('div');
  t.className = 'toast'; t.textContent = msg;
  $('#toasts').appendChild(t);
  setTimeout(() => { t.style.opacity = 0; t.style.transition = '.4s'; setTimeout(() => t.remove(), 400); }, 2600);
}

function accClass(a){ if(a == null) return 'acc-n'; return a >= 90 ? 'acc-g' : a >= 75 ? 'acc-a' : 'acc-r'; }
function fmt(n){ return n == null ? '—' : Number(n).toLocaleString(); }

function countUp(el, target, suffix=''){
  if(target == null){ el.textContent = '—'; return; }
  const dur = 800, t0 = performance.now();
  function tick(t){
    const k = Math.min((t - t0) / dur, 1);
    const ease = 1 - Math.pow(1 - k, 3);
    el.textContent = Math.round(target * ease).toLocaleString() + suffix;
    if(k < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function skeleton(el, h=120){ el.innerHTML = `<div class="skel" style="height:${h}px"></div>`; }

async function api(path, opts){
  const r = await fetch(path, opts);
  if(!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

/* date pills — shared across all pages */
async function initDatePills(){
  const wrap = $('#date-pills');
  if(!wrap) return;
  const info = await api('/api/test-dates');
  if(!POD_DATE || !info.dates.includes(POD_DATE)) POD_DATE = info.dates[info.dates.length - 1];
  localStorage.setItem('pod_date', POD_DATE);
  wrap.innerHTML = info.dates.map(d =>
    `<button class="dpill ${d === POD_DATE ? 'on' : ''}" data-d="${d}">${info.labels[d]}</button>`).join('');
  wrap.onclick = e => {
    const b = e.target.closest('.dpill'); if(!b) return;
    POD_DATE = b.dataset.d;
    localStorage.setItem('pod_date', POD_DATE);
    $$('.dpill').forEach(p => p.classList.toggle('on', p.dataset.d === POD_DATE));
    if(typeof onDateChange === 'function') onDateChange();
  };
}

function lineChart(ctx, labels, datasets, opts={}){
  return new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: opts.ratio !== false,
      interaction: { mode: 'index', intersect: false },
      animation: { duration: 700, easing: 'easeOutQuart' },
      plugins: {
        legend: { position: 'top', labels: { boxWidth: 9, boxHeight: 9, borderRadius: 4, useBorderRadius: true, padding: 14, font: { size: 10.5, weight: 600 } } },
        tooltip: { backgroundColor: 'rgba(14,22,38,.96)', borderColor: 'rgba(255,255,255,.12)', borderWidth: 1, cornerRadius: 9, padding: 11, titleFont: { weight: 700 } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: opts.maxTicks || 12 } },
        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,.04)' } },
      },
    },
  });
}

function gradFill(ctx, hex, h=260){
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, hex + '4d'); g.addColorStop(1, hex + '00');
  return g;
}

function dsPred(data, color, ctx, label='Predicted'){
  return { label, data, borderColor: color, backgroundColor: ctx ? gradFill(ctx, color) : 'transparent',
           borderWidth: 2.4, fill: !!ctx, tension: .4, pointRadius: 0, pointHoverRadius: 5 };
}
function dsAct(data, label='Actual'){
  return { label, data, borderColor: '#10b981', backgroundColor: 'transparent',
           borderWidth: 2.2, borderDash: [7, 4], fill: false, tension: .4, pointRadius: 0, pointHoverRadius: 5 };
}

document.addEventListener('DOMContentLoaded', async () => {
  await initDatePills();
  if(typeof onDateChange === 'function') onDateChange();
});
