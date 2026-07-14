/* Global Hour-Scrubber + day-shape histogram + Next-Breach pointer.
   One control = time selector + day shape + jump-to-first-red.          */
const Scrubber = (() => {
  let hour = 8, hist = [], breaches = [], onChange = null, nextBreach = null;

  function mount(hostId, brief, cb) {
    onChange = cb;
    hist = brief.hero.map(h => h.pax);
    breaches = brief.hero.map(h => h.band === 'high');
    nextBreach = brief.next_breach;
    const host = document.getElementById(hostId);
    host.innerHTML = `
      <div class="scrub">
        <canvas class="scrub-canvas" id="scrub-canvas"></canvas>
        <div class="scrub-head" id="scrub-head"></div>
        <div class="scrub-row">
          <button class="scrub-btn" id="scrub-prev">‹</button>
          <input type="range" min="0" max="23" value="${hour}" id="scrub-range" class="scrub-range">
          <button class="scrub-btn" id="scrub-next">›</button>
          ${nextBreach ? `<button class="scrub-jump" id="scrub-jump">⚡ Next breach ${String(nextBreach.hour).padStart(2,'0')}:00 · ${nextBreach.label}</button>` : '<span class="scrub-clear">No breaches today ✓</span>'}
        </div>
      </div>`;
    const range = document.getElementById('scrub-range');
    range.oninput = e => set(+e.target.value);
    document.getElementById('scrub-prev').onclick = () => set(Math.max(0, hour - 1));
    document.getElementById('scrub-next').onclick = () => set(Math.min(23, hour + 1));
    const jump = document.getElementById('scrub-jump');
    if (jump) jump.onclick = () => set(nextBreach.hour);
    drawHist();
    set(nextBreach ? nextBreach.hour : peakHour());
  }

  function peakHour() { return hist.indexOf(Math.max(...hist)); }

  function set(h) {
    hour = h;
    document.getElementById('scrub-range').value = h;
    document.getElementById('scrub-head').innerHTML =
      `<b>${String(h).padStart(2,'0')}:00</b> <span>scrubbed hour · ${hist[h].toLocaleString()} pax</span>`;
    drawHist();
    if (onChange) onChange(h);
  }

  function drawHist() {
    const c = document.getElementById('scrub-canvas');
    if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    const W = c.clientWidth, H = 46;
    c.width = W * dpr; c.height = H * dpr;
    const ctx = c.getContext('2d'); ctx.scale(dpr, dpr); ctx.clearRect(0, 0, W, H);
    const max = Math.max(...hist, 1), n = 24, gap = 3, bw = (W - gap * (n - 1)) / n;
    hist.forEach((v, i) => {
      const bh = (v / max) * (H - 6), x = i * (bw + gap), y = H - bh;
      ctx.fillStyle = i === hour ? '#5b79e8' : breaches[i] ? 'rgba(248,113,113,.55)' : 'rgba(124,141,176,.3)';
      ctx.beginPath(); ctx.roundRect(x, y, bw, bh, 2); ctx.fill();
    });
  }

  return { mount, set, get: () => hour };
})();
