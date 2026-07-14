const TP_COLORS = {
    Entry:      {bg:'#1a2250', icon:'#4e6fd0', chart:'#2844b0'},
    CheckIn:    {bg:'#ece0f2', icon:'#c8b8e8', chart:'#b090d0'},
    Emigration: {bg:'#f2e0e8', icon:'#e8b8c8', chart:'#d090a0'},
    Immigration:{bg:'#f2e8e0', icon:'#e8c8b0', chart:'#d0a880'},
    PESC:       {bg:'#e0e8f2', icon:'#b8d0e8', chart:'#80b0d0'},
    Transfers:  {bg:'#e0f2e8', icon:'#b8d8c8', chart:'#80c0a0'},
};

const TP_LABELS = {
    Entry:'Entry Gates',CheckIn:'Check-In Counters',
    Emigration:'Departure Emigration',Immigration:'Arrival Immigration',
    PESC:'Security Screening',Transfers:'Transfer Desks',
};

const TP_ICONS = {
    Entry:'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>',
    CheckIn:'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
    Emigration:'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/></svg>',
    Immigration:'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    PESC:'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    Transfers:'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>',
};

let currentData = null;
let hourlyChart = null;
let lanesChart = null;
let selectedTP = null;

// ─── Init ────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async function(){
    showLoading();
    try {
        const res = await fetch('/api/test-dates');
        const info = await res.json();
        // Auto-load a single default day (the most recent available)
        const defaultDate = info.dates[info.dates.length - 1];
        await selectDate(defaultDate);
    } catch(e) { console.error(e); }
    hideLoading();
});

async function selectDate(dateStr){
    showLoading();
    try {
        const res = await fetch(`/api/predict/${dateStr}`);
        currentData = await res.json();
        currentData._date = dateStr;
        renderHero(currentData);
        renderTouchpoints(currentData);
        closeHourly();
    } catch(e) { console.error(e); }
    hideLoading();
}

// loadData alias for charts.js auto-load compatibility
function loadData(){ /* date pills handle loading */ }

// ─── Hero Card ───────────────────────────────────────────────

function renderHero(data){
    const container = document.getElementById('hero-card');
    const d = data.total;
    const dt = new Date(data._date + 'T00:00:00');
    const dayStr = dt.toLocaleDateString('en-US',{weekday:'long',year:'numeric',month:'long',day:'numeric'});
    const acc = d.accuracy;
    const accCls = acc >= 85 ? 'acc-good' : acc >= 70 ? 'acc-ok' : 'acc-poor';

    container.innerHTML = `
        <div class="hero-date">${dayStr}</div>
        <div class="hero-grid">
            <div class="hero-main">
                <div class="hero-big">${d.predicted.toLocaleString()}</div>
                <div class="hero-label">Predicted Passengers</div>
            </div>
            <div class="hero-divider"></div>
            <div class="hero-side">
                <div class="hero-side-val">${d.actual.toLocaleString()}</div>
                <div class="hero-label">Actual Passengers</div>
                <div style="margin-top:12px;">
                    <span class="tp-acc-pill ${accCls}" style="font-size:14px;padding:5px 14px;">
                        ${acc !== null ? acc + '% accuracy' : 'N/A'}
                    </span>
                </div>
            </div>
        </div>
    `;
}

// ─── Touchpoint Cards ────────────────────────────────────────

function renderTouchpoints(data){
    const grid = document.getElementById('tp-grid');
    grid.innerHTML = '';

    for(const [key, tp] of Object.entries(data.touchpoints)){
        const colors = TP_COLORS[key] || TP_COLORS.Entry;
        const acc = tp.accuracy;
        const accCls = acc >= 85 ? 'acc-good' : acc >= 70 ? 'acc-ok' : 'acc-poor';

        const card = document.createElement('div');
        card.className = 'tp-card';
        card.dataset.tp = key;
        card.onclick = () => showHourly(key);

        card.innerHTML = `
            <div class="tp-icon" style="background:${colors.bg};color:${colors.icon};">
                ${TP_ICONS[key] || ''}
            </div>
            <div class="tp-name">${TP_LABELS[key] || key}</div>
            <div class="tp-predicted">${tp.predicted.toLocaleString()}</div>
            <div class="tp-predicted-label">Predicted</div>
            <div class="tp-actual-row">
                <div>
                    <div class="tp-actual-label">Actual</div>
                    <div class="tp-actual-val">${tp.actual.toLocaleString()}</div>
                </div>
                <span class="tp-acc-pill ${accCls}">
                    ${acc !== null ? acc + '%' : 'N/A'}
                </span>
            </div>
            <div class="tp-lanes-badge">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/></svg>
                Avg ${Math.round(tp.lanes_predicted.reduce((a,b)=>a+b,0)/24)} ${tp.lanes_label} predicted
            </div>
            <div class="tp-click-hint">Click for hourly chart</div>
        `;
        grid.appendChild(card);
    }
}

// ─── Hourly Chart ────────────────────────────────────────────

function showHourly(key){
    if(!currentData || !currentData.touchpoints[key]) return;

    // Highlight selected card
    document.querySelectorAll('.tp-card').forEach(c => c.classList.remove('selected'));
    document.querySelector(`.tp-card[data-tp="${key}"]`).classList.add('selected');

    const tp = currentData.touchpoints[key];
    const colors = TP_COLORS[key] || TP_COLORS.Entry;
    const section = document.getElementById('hourly-section');
    const title = document.getElementById('hourly-title');

    title.textContent = `${TP_LABELS[key] || key} - Hourly Predicted vs Actual`;

    if(hourlyChart) hourlyChart.destroy();
    if(lanesChart) lanesChart.destroy();

    const canvas = document.getElementById('hourly-chart');
    hourlyChart = createHourlyChart(
        canvas,
        tp.hourly_predicted,
        tp.hourly_actual,
        colors.chart,
        '#e8c8b0'
    );

    // Lanes chart
    const lanesTitle = document.getElementById('lanes-chart-title');
    lanesTitle.textContent = `${tp.lanes_label} Open - Predicted vs Actual`;
    const lanesCanvas = document.getElementById('lanes-chart');
    lanesChart = createLanesChart(
        lanesCanvas,
        tp.lanes_predicted,
        tp.lanes_actual,
        colors.chart,
        '#e8c8b0',
        tp.lanes_label
    );

    section.style.display = 'block';
    section.scrollIntoView({behavior:'smooth',block:'start'});
    selectedTP = key;
}

function closeHourly(){
    document.getElementById('hourly-section').style.display = 'none';
    document.querySelectorAll('.tp-card').forEach(c => c.classList.remove('selected'));
    if(hourlyChart){ hourlyChart.destroy(); hourlyChart = null; }
    if(lanesChart){ lanesChart.destroy(); lanesChart = null; }
    selectedTP = null;
}
