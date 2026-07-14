/* ═══ PLAN — temporal plan engine ═══
   Builds the operating plan for a SELECTED day and, for past/live days, the ACTUAL
   (realized) load beside the prediction so operators can verify POD.

   Modes (by day offset from today):
     offset > 0  →  'plan'    (Tomorrow / D+1)  — prediction only
     offset = 0  →  'live'    (Today)           — actuals stream in hour-by-hour (liveHour)
     offset < 0  →  'history' (last 10 days)    — full actual vs predicted

   Prescription (SRC-C):  units L = ⌈(PAX/12)·AvgPT ÷ acceptableWait⌉ ; wait = ⌈(PAX/12)·AvgPT ÷ open⌉
   Selection persists in localStorage('pod-offset'); live cursor in localStorage('pod-livehour'). */
const PLAN = (() => {
  const DAYMS = 864e5, now = Date.now(), todayEpoch = Math.floor(now / DAYMS);

  let offset; try { offset = parseInt(localStorage.getItem('pod-offset')); } catch(e){}
  if (isNaN(offset)) offset = 1;                       // default = Tomorrow (plan)
  offset = Math.max(-10, Math.min(1, offset));
  const mode = offset > 0 ? 'plan' : offset === 0 ? 'live' : 'history';

  const realHour = new Date(now).getHours();
  let liveHour;  try { liveHour = parseInt(localStorage.getItem('pod-livehour')); } catch(e){}
  if (mode !== 'live' || isNaN(liveHour)) liveHour = mode==='live' ? Math.max(1, realHour) : (mode==='history' ? 24 : 0);
  liveHour = Math.max(0, Math.min(24, liveHour));

  const dateOf  = off => new Date(now + off*DAYMS);
  const fmtLong = d => d.toLocaleDateString('en-GB',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
  const fmtShort= d => d.toLocaleDateString('en-GB',{weekday:'short',day:'2-digit',month:'short'});
  const day = dateOf(offset), dayKey = todayEpoch + offset;

  const frac = x => x - Math.floor(x);
  const noise = (k,ti,h) => (frac(Math.sin(k*928.7 + ti*113.3 + h*57.1)*43758.5453) - 0.5) * 2;   // −1..1 deterministic

  const BANDS = {'Entry Gates':{acc:3,high:5},'Check-In':{acc:8,high:15},'Security (PESC)':{acc:5,high:10},
    'Emigration':{acc:5,high:10},'Immigration':{acc:5,high:10},'Customs':{acc:5,high:10},'Transfers':{acc:5,high:10}};
  const POS_SHARE = {'Check-In':0.4};

  const names = Object.keys(MOCK.resource);
  const dow = day.getDay();
  const dayFactor = [1.05,0.96,0.95,0.97,1.0,1.06,1.10][dow] * (1 + noise(dayKey,99,7)*0.03);

  const tps = {};
  names.forEach((name, ti) => {
    const r = MOCK.resource[name];
    const band = BANDS[name] || {acc:r.thr, high:Math.round(r.thr*1.5)};
    const share = POS_SHARE[name] != null ? POS_SHARE[name] : 1;
    const spread = Math.max(.04, Math.min(.14, (100 - r.acc)/100 * 2.2));   // actual scatter ~ model error

    const hours = r.pax.map((base, h) => {
      const pax  = Math.max(0, Math.round(base * dayFactor));                 // predicted (forecast)
      const eff  = Math.round(pax * share);
      const req  = eff>0 ? Math.max(1, Math.ceil((eff/12)*r.pt/band.acc)) : 0;
      const open = Math.min(req, r.cap);
      const wait = open>0 ? Math.ceil((eff/12)*r.pt/open) : 0;
      const short= Math.max(0, req - r.cap);
      const status = open===0 ? 'idle' : wait<=band.acc ? 'ok' : wait<=band.high ? 'watch' : 'breach';
      const actFull = offset<=0 ? Math.max(0, Math.round(pax * (1 + noise(dayKey,ti,h)*spread))) : null;   // realized
      const known   = offset<0 ? true : offset===0 ? (h < liveHour) : false;
      const act     = known ? actFull : null;
      let actWait = null;
      if (act != null && open>0){ const ae = Math.round(act*share); actWait = Math.ceil((ae/12)*r.pt/open); }
      return {h, pax, eff, req, open, wait, short, status, actFull, act, actWait, known};
    });

    const dayPax = hours.reduce((a,x)=>a+x.pax,0);
    const peakH  = hours.reduce((b,x,i)=> x.pax>hours[b].pax?i:b, 0);
    const peak   = hours[peakH];
    const staff  = peak.open * r.staffU * 3;

    const windows = []; let w=null;
    hours.forEach(x=>{ const risky=x.status==='watch'||x.status==='breach';
      if(risky){ if(!w) w={from:x.h,to:x.h,maxWait:x.wait,maxShort:x.short,worst:x.status};
        else { w.to=x.h; w.maxWait=Math.max(w.maxWait,x.wait); w.maxShort=Math.max(w.maxShort,x.short); if(x.status==='breach') w.worst='breach'; } }
      else if(w){ windows.push(w); w=null; } });
    if(w) windows.push(w);

    tps[name] = {name, unit:r.unit, area:r.area, cap:r.cap, staffU:r.staffU, pt:r.pt, acc:r.acc,
      band, share, hours, dayPax, peakH, peak, staff, windows, zones:r.zones};
  });

  // per-day accuracy (pred vs actFull over KNOWN hours)
  function accuracyOf(hrs){
    const kn = hrs.filter(x=>x.known && x.pax>0);
    if(!kn.length) return null;
    const mape = kn.reduce((a,x)=>a+Math.abs(x.pax-x.actFull)/x.pax,0)/kn.length;
    return Math.max(60, Math.min(99.9, 100 - mape*100));
  }
  names.forEach(n=>{ const t=tps[n];
    t.dayAct = t.hours.filter(x=>x.known).reduce((a,x)=>a+x.actFull,0);
    t.accDay = accuracyOf(t.hours); });

  const hh = h => String(h).padStart(2,'0') + ':00';
  const unitLow = u => u==='DFMDs' ? 'DFMDs' : u.toLowerCase();
  const unitOne = u => u==='DFMDs' ? 'DFMD' : u.toLowerCase().replace(/s$/,'');

  const completedHours = mode==='history' ? 24 : mode==='live' ? liveHour : 0;
  const hasActual = completedHours > 0;
  const hourlyTotal  = Array.from({length:24},(_,h)=>names.reduce((a,n)=>a+tps[n].hours[h].pax,0));
  const hourlyActual = Array.from({length:24},(_,h)=>names.reduce((a,n)=>a+(tps[n].hours[h].actFull||0),0));
  const peakHour = hourlyTotal.indexOf(Math.max(...hourlyTotal));
  const staffTotal = names.reduce((a,n)=>a+tps[n].staff,0);
  const unitsPeak  = names.reduce((a,n)=>a+tps[n].peak.open,0);
  const dayPaxTotal = Math.round(MOCK.flightDay.pax * dayFactor);

  // overall accuracy + realized total over known hours
  let predSum=0, actSum=0, mAcc=0, mN=0;
  names.forEach(n=>tps[n].hours.forEach(x=>{ if(x.known && x.pax>0){ predSum+=x.pax; actSum+=x.actFull; mAcc+=Math.abs(x.pax-x.actFull)/x.pax; mN++; }}));
  const accDay = mN ? Math.max(60, Math.min(99.9, 100-(mAcc/mN)*100)) : null;
  const dayActTotal = mN ? Math.round(dayPaxTotal*(actSum/predSum)) : null;

  // readiness (plan quality) — share of active touchpoint-hours inside SLA
  let active=0, okH=0;
  names.forEach(n=>tps[n].hours.forEach(x=>{ if(x.status!=='idle'){active++; if(x.status==='ok') okH++;} }));
  const readiness = Math.round(100*okH/Math.max(active,1));

  // action queue (predicted risk windows, worst first)
  const actions = [];
  names.forEach(n=>{ const t=tps[n]; t.windows.forEach(w=>{ const atC=w.maxShort>0;
    actions.push({tp:n, from:w.from, to:w.to, sev:w.worst==='breach'?'high':'med', window:hh(w.from)+'–'+hh(w.to+1),
      kind:atC?'AT CEILING':'TIGHT',
      msg:atC?`Demand needs ${t.cap+w.maxShort} ${unitLow(t.unit)} — ${w.maxShort} above the ${t.cap}-${unitOne(t.unit)} ceiling. Predicted wait up to ${w.maxWait}m (target ${t.band.acc}m).`
             :`Predicted wait up to ${w.maxWait}m vs the ${t.band.acc}m target through this window.`,
      act:atC?`Open all ${t.cap} ${unitLow(t.unit)} before ${hh(w.from)}; pre-process / stagger the queue upstream — adding positions is not possible.`
             :`Hold full deployment through ${hh(w.to+1)} and monitor the live feed.`}); }); });
  actions.sort((a,b)=>(b.sev==='high')-(a.sev==='high') || (b.to-b.from)-(a.to-a.from));

  function days(){
    const list = [
      {off:1, label:'Tomorrow', sub:fmtShort(dateOf(1)), tag:'PLAN', mode:'plan'},
      {off:0, label:'Today',    sub:'Live',              tag:'LIVE', mode:'live'},
      {off:-1,label:'Yesterday',sub:fmtShort(dateOf(-1)),           mode:'history'},
    ];
    for(let o=-2;o>=-10;o--) list.push({off:o, label:(-o)+' days ago', sub:fmtShort(dateOf(o)), mode:'history'});
    return list;
  }
  function select(off){ try{ localStorage.setItem('pod-offset', off); if(off!==0) localStorage.removeItem('pod-livehour'); }catch(e){} location.reload(); }
  function persistLive(h){ try{ localStorage.setItem('pod-livehour', h); }catch(e){} }

  return { offset, mode, isPlan:mode==='plan', isLive:mode==='live', isPast:mode==='history',
    day, dateLong:fmtLong(day), dateShort:fmtShort(day), dateISO:day.toISOString().slice(0,10),
    tps, names, hh, unitLow, unitOne, hourlyTotal, hourlyActual, peakHour, staffTotal, unitsPeak,
    dayPaxTotal, dayActTotal, accDay, readiness, actions, hasActual, completedHours, liveHour,
    days, select, persistLive, fmtShort };
})();

/* ── CSV export (respects the selected day; includes Actual when known) ── */
function planCSV(scope){
  const withAct = PLAN.hasActual;
  const head = ['Touchpoint','Hour','Predicted PAX', ...(withAct?['Actual PAX','Var %']:[]), 'Required Units','Planned Open','Capacity','Predicted Wait (min)','Status'];
  const rows = [head];
  const add = n => { const t=PLAN.tps[n]; t.hours.forEach(x=>{
    const varp = (withAct && x.act!=null && x.pax) ? (((x.act-x.pax)/x.pax)*100).toFixed(1)+'%' : (withAct?'—':null);
    rows.push([n, PLAN.hh(x.h), x.pax, ...(withAct?[x.act==null?'—':x.act, varp]:[]), x.req, x.open, t.cap, x.wait, x.status.toUpperCase()]); }); };
  if (scope && PLAN.tps[scope]) add(scope); else PLAN.names.forEach(add);
  downloadCSV('POD_'+(PLAN.isPast?'Actual':PLAN.isLive?'Live':'Plan')+'_'+PLAN.dateISO+(scope?'_'+scope.replace(/[^\w]+/g,''):'_AllTouchpoints')+'.csv', rows);
}
