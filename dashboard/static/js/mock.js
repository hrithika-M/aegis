/* POD mock data — realistic values matching the reference. UI-only, no backend. */
const TPS = ['Entry Gates','Check-In','Security','Emigration','Immigration','Customs','Transfers'];

// a believable bimodal hourly passenger curve (24h)
function curve(peakA, peakB, base, amp){
  return Array.from({length:24}, (_,h) => {
    const a = Math.exp(-Math.pow((h-peakA)/2.4,2));
    const b = Math.exp(-Math.pow((h-peakB)/2.8,2));
    return Math.round(base + amp*(a*0.85 + b));
  });
}
function jitter(arr, pct){ return arr.map(v => Math.round(v*(1+(Math.sin(v*9.7)%1)*pct))); }

const MOCK = {
  date: 'Wednesday, March 25, 2026',
  exec: {
    kpis: [
      {lab:'Total Predicted PAX', val:'111,749', chg:'+2.31% vs yesterday', dir:'up'},
      {lab:'Actual PAX', val:'108,637', chg:'97.2% match', dir:'flat'},
      {lab:'Prediction Accuracy', val:'97.23%', chg:'+2.31% vs yesterday', dir:'up'},
      {lab:'Total Flights', val:'872', chg:'+18 vs yesterday', dir:'up'},
      {lab:'Avg Wait Time', val:'6.4 min', chg:'-1.2 min vs yesterday', dir:'up'},
    ],
    loadEntry: curve(7,19,180,2400),
    loadTransfers: curve(9,17,90,650),
    loadEntryAct: null,  // filled below
    status: [
      {nm:'Entry Gates', st:'normal'}, {nm:'Check-In', st:'warning'}, {nm:'Security', st:'busy'},
      {nm:'Emigration', st:'normal'}, {nm:'Immigration', st:'normal'}, {nm:'Customs', st:'normal'}, {nm:'Transfers', st:'busy'},
    ],
    // Today at a glance
    glance: { health: 92, peakHour: '18:00', holiday: false, sla: 89, worst: 'Security' },
    // Domestic vs International (of 111,749)
    segments: {
      Domestic:      { pax: 86047, pct: 77, flights: 712, wait: 5.8, color:'#22d3ee' },
      International:  { pax: 25702, pct: 23, flights: 160, wait: 7.9, color:'#f59e0b' },
    },
    segHourly: { dom: curve(7,19,140,1900), intl: curve(8,20,40,560) },
    // Arrivals vs Departures
    arrDep: { departures: 64280, arrivals: 47469 },
    transfers: { 'D-D': 7551, 'I-D': 483, 'I-I': 490 },
    // Alerts — worst first (actionable)
    alerts: [
      { tp:'Security (PESC)', sev:'high', msg:'Breaches 17:00-19:00, at 46-DFMD ceiling', act:'Cannot add lanes — escalate / divert at 18:00', verdict:'AT CEILING' },
      { tp:'Check-In', sev:'med', msg:'Wait exceeds 8 min during 18:00-20:00 evening rush', act:'Open 6 more counters by 18:00', verdict:'FIXABLE' },
      { tp:'Transfers', sev:'med', msg:'I-D transfer wave 14:00 feeds Domestic Security', act:'Pre-stage 2 transfer desks at 14:00', verdict:'FIXABLE' },
    ],
    // staff plan rows: [tp, h06,h08,h10,h12,h14,h16,h18,h20,h22, peak]
    staff: [
      ['Entry Gates',45,62,58,48,40,52,68,40,32,68],
      ['Check-In',78,92,80,55,58,60,88,60,28,96],
      ['Security',82,98,80,62,66,72,98,68,30,98],
      ['Emigration',28,36,22,12,14,20,38,32,18,40],
      ['Immigration',26,30,24,14,16,18,28,28,22,34],
      ['Customs',16,20,14,8,10,12,18,16,12,24],
      ['Transfers',24,28,22,18,20,22,28,24,16,32],
    ],
  },
  // wait-time heatmap: tp -> 24 values (minutes)
  heatmap: {},
  // flights defined below as MOCK.flights (richer, requirement-aligned)
  // turn-up profile: 13 buckets 360->0 min before departure (ratio %)
  turnup: [2,4,7,11,15,18,16,12,8,4,2,1,0.5],
  zones: {
    'Security': [
      {z:'Zone A', pred:1200, act:1150, proc:22, wait:3.1, util:68, st:'normal'},
      {z:'Zone B', pred:1500, act:1420, proc:31, wait:5.3, util:82, st:'busy'},
      {z:'Zone C', pred:900,  act:860,  proc:18, wait:1.2, util:45, st:'normal'},
      {z:'Zone D', pred:700,  act:670,  proc:26, wait:4.7, util:78, st:'warning'},
    ],
  },
  liveEvents: [
    {id:'AI 217', route:'HYD → DXB', st:'Delayed 30 min', stc:'down', time:'14:30 → 15:00'},
    {id:'EK 530', route:'HYD → DXB', st:'Gate Changed', stc:'flat', time:'A5 → A12'},
    {id:'6E 102', route:'HYD → BOM', st:'Early Boarding', stc:'up', time:'12:10'},
    {id:'SG 812', route:'HYD → CCU', st:'Delayed 15 min', stc:'down', time:'09:45 → 10:00'},
    {id:'AI 650', route:'HYD → DEL', st:'On Time', stc:'up', time:'10:30'},
  ],
  impact: [
    {nm:'Check-In Load', v:'+12%', lvl:'med'},
    {nm:'Security Load', v:'+15%', lvl:'high'},
    {nm:'Emigration Load', v:'+8%', lvl:'low'},
    {nm:'Transfer Load', v:'+22%', lvl:'high'},
    {nm:'Immigration Load', v:'+10%', lvl:'med'},
    {nm:'Customs Load', v:'+5%', lvl:'low'},
  ],
  sources: [
    {nm:'AODB (Flights)', sync:'10:04 AM', rec:'872'},
    {nm:'Data Lake (Schedules)', sync:'09:58 AM', rec:'12,430'},
    {nm:'LDM + PTM (Bookloads)', sync:'10:02 AM', rec:'872'},
    {nm:'CUPPS (Check-in & Gate)', sync:'10:01 AM', rec:'236,541'},
    {nm:'E-Boarding (PESC/Transfers)', sync:'10:03 AM', rec:'198,764'},
    {nm:'Queue Stats (Processing Time)', sync:'10:02 AM', rec:'45,219'},
    {nm:'IOT Stats (Hourly Pax)', sync:'10:01 AM', rec:'68,442'},
    {nm:'Holiday Mapping File', sync:'09:55 AM', rec:'245'},
  ],
};

// ── Resource model: each touchpoint has its OWN unit + throughput + staffing ──
// units needed = ceil(hourly PAX / pax-per-unit), capped at capacity
// staff needed = units × staff-per-unit
// Each entry also carries: open (units currently deployed), wait (peak avg wait, min),
// acc (model accuracy %), thr (wait threshold, min), and zones (its OWN sub-area breakdown).
MOCK.resource = {
  'Entry Gates':    {unit:'Lanes',    paxU:250, staffU:1, cap:40, open:10, wait:2.8, acc:97.8, thr:4,
    pax:curve(7,19,200,1500),
    zones:[['Gate 03',0.197],['Gate 05',0.162],['Gate 08',0.131],['Gate 04',0.127],['Gate 06',0.105],['Gate 09',0.090],['Gate 10',0.067],['Gate 11',0.052],['Gate 01',0.049],['Gate 02',0.020]]},
  'Check-In':       {unit:'Counters', paxU:90,  staffU:1, cap:30, open:14, wait:9.5, acc:96.5, thr:10,
    pax:curve(7,19,120,900),
    zones:[['Checkin G Zone',0.324],['Checkin K Zone',0.130],['Checkin D Zone',0.111],['Checkin H Zone',0.097],['Checkin J Zone',0.081],['Checkin M Zone',0.071],['Checkin L Zone',0.069],['Checkin P Zone',0.044],['Checkin N Zone',0.043],['Checkin B Zone',0.029]]},
  'Security (PESC)':{unit:'DFMDs',    paxU:150, staffU:2, cap:46, open:19, wait:8.7, acc:97.1, thr:10,
    pax:curve(8,19,300,2800),
    zones:[['ATRS 11-12',0.197],['ATRS 13-14',0.169],['ATRS 15-16',0.167],['ATRS 25-26',0.159],['ATRS 9-10',0.073],['ATRS 23-24',0.061],['ATRS 7-8',0.059],['ATRS 17-18',0.055],['ATRS 1',0.031],['ATRS 5-6',0.011],['ATRS 21-22',0.011],['ATRS 19-20',0.003]]},
  'Emigration':     {unit:'Desks',    paxU:120, staffU:1, cap:44, open:8,  wait:6.4, acc:96.9, thr:10,
    pax:curve(8,20,80,620),
    zones:[['Departure Emigration',1.0]]},
  'Immigration':    {unit:'Desks',    paxU:110, staffU:1, cap:40, open:7,  wait:5.9, acc:95.8, thr:10,
    pax:curve(3,9,80,560),
    zones:[['Arrival Immigration',1.0]]},
  'Customs':        {unit:'Lanes',    paxU:100, staffU:1, cap:4,  open:3,  wait:2.1, acc:98.2, thr:10,
    pax:curve(3,9,30,150),
    zones:[['Green Channel',0.88],['Red Channel',0.12]]},
  'Transfers':      {unit:'Desks',    paxU:110, staffU:1, cap:11, open:5,  wait:4.5, acc:96.0, thr:10,
    pax:curve(9,17,60,350),
    zones:[['D-D Transfers',0.873],['I-D Transfers',0.048],['I-I Transfers',0.078]]},
};
// avg processing time per touchpoint (minutes / passenger) — real airport SLA (seconds ÷ 60)
// Entry 20s · Check-In 150s · Security 30s · Emigration 60s · Immigration 60s · Transfers 30s · Customs 30s (assumed)
Object.entries({'Entry Gates':20/60,'Check-In':150/60,'Security (PESC)':30/60,'Emigration':60/60,'Immigration':60/60,'Customs':30/60,'Transfers':30/60})
  .forEach(([k,v])=>{ if(MOCK.resource[k]) MOCK.resource[k].pt = v; });
// sub-area category noun per touchpoint (matches how each touchpoint is differentiated)
const SIM_AREA = {'Entry Gates':'Gate','Customs':'Channel','Transfers':'Transfer flow'};
Object.keys(MOCK.resource).forEach(k=>{ MOCK.resource[k].area = SIM_AREA[k] || 'Zone'; });

// Calibrate each touchpoint's daily PAX to realistic volumes tied to the ~111,749 day
// (departures 64,280 · arrivals 47,469 · ~23% international). Touchpoints OVERLAP — a passenger
// crosses several — so these do NOT sum to 111,749; each is a realistic slice of it.
//   Entry/Check-In/Security ≈ departing pax · Emigration/Immigration/Customs ≈ international only · Transfers ≈ connecting
const DAY_PAX = {
  'Entry Gates':55000, 'Check-In':26000, 'Security (PESC)':62000,
  'Emigration':14000, 'Immigration':11000, 'Customs':2500, 'Transfers':8500,
};
Object.entries(DAY_PAX).forEach(([k,target])=>{
  const r = MOCK.resource[k]; if(!r) return;
  const sum = r.pax.reduce((a,b)=>a+b,0);
  if(sum>0){ const f = target/sum; r.pax = r.pax.map(v=>Math.max(0, Math.round(v*f))); }
});

// Real operational PEAK units (max positions the airport opens at the busiest hour).
// Re-derive throughput-per-unit (paxU) from these so the prescription yields exactly these
// peak units — consistently on the dashboard, Touchpoints, and Simulation.
const PEAK_UNITS = {
  'Entry Gates':7, 'Check-In':12, 'Security (PESC)':21,
  'Emigration':6, 'Immigration':6, 'Customs':2, 'Transfers':4,
};
Object.entries(PEAK_UNITS).forEach(([k,u])=>{
  const r = MOCK.resource[k]; if(r) r.paxU = Math.ceil(Math.max(...r.pax)/u);
});

// ── Flight prediction (PR-03/04/05/08) ──
// Day-level schedule summary (realistic for a GMR Hyderabad peak day).
MOCK.flightDay = { total:872, dep:442, arr:430, dom:712, intl:160, pax:111749, lf:88.4 };
// Turn-up profiles (PR-04): 13 buckets, 360→0 min before departure (ratio %).
MOCK.tuMin  = [360,330,300,270,240,210,180,150,120,90,60,30,0];
MOCK.tuDom  = [1,2,3,5,8,12,16,18,15,10,6,3,1];   // domestic — arrive later
MOCK.tuIntl = [3,6,10,15,17,15,11,8,5,4,3,2,1];   // international — arrive earlier
// Representative sample of the 872 flights. dir: dep|arr · dom: domestic.
// total = predicted boarded PAX (Bookloads); split into local (start here) + transfer (connecting).
MOCK.flights = [
  // ── Departures · Domestic ──
  {id:'6E 102', al:'IndiGo',     ac:'A320neo', route:'HYD → BOM', dir:'dep', dom:true,  time:'12:10', cap:186, total:171, local:157, transfer:14, status:'On Time'},
  {id:'AI 560', al:'Air India',  ac:'A321',    route:'HYD → DEL', dir:'dep', dom:true,  time:'06:15', cap:222, total:198, local:182, transfer:16, status:'Boarding'},
  {id:'UK 846', al:'Vistara',    ac:'A320',    route:'HYD → DEL', dir:'dep', dom:true,  time:'19:40', cap:180, total:169, local:155, transfer:14, status:'On Time'},
  {id:'QP 1402',al:'Akasa Air',  ac:'737 MAX', route:'HYD → BLR', dir:'dep', dom:true,  time:'08:20', cap:189, total:163, local:150, transfer:13, status:'Delayed 20 min'},
  {id:'SG 234', al:'SpiceJet',   ac:'737-800', route:'HYD → MAA', dir:'dep', dom:true,  time:'15:30', cap:189, total:157, local:144, transfer:13, status:'On Time'},
  {id:'6E 776', al:'IndiGo',     ac:'A320',    route:'HYD → CCU', dir:'dep', dom:true,  time:'21:05', cap:186, total:167, local:154, transfer:13, status:'On Time'},
  {id:'IX 1184',al:'AI Express', ac:'737-800', route:'HYD → GOI', dir:'dep', dom:true,  time:'11:00', cap:186, total:164, local:151, transfer:13, status:'Gate Changed'},
  // ── Departures · International ──
  {id:'EK 526', al:'Emirates',   ac:'B777-300',route:'HYD → DXB', dir:'dep', dom:false, time:'04:30', cap:354, total:322, local:251, transfer:71, status:'On Time'},
  {id:'QR 504', al:'Qatar Airways',ac:'A350-900',route:'HYD → DOH',dir:'dep', dom:false, time:'03:05', cap:283, total:249, local:194, transfer:55, status:'On Time'},
  {id:'AI 936', al:'Air India',  ac:'A321',    route:'HYD → DXB', dir:'dep', dom:false, time:'19:00', cap:222, total:200, local:156, transfer:44, status:'On Time'},
  {id:'SQ 529', al:'Singapore',  ac:'B787-10', route:'HYD → SIN', dir:'dep', dom:false, time:'23:55', cap:337, total:286, local:223, transfer:63, status:'On Time'},
  {id:'LH 753', al:'Lufthansa',  ac:'A340-300',route:'HYD → FRA', dir:'dep', dom:false, time:'02:40', cap:298, total:259, local:202, transfer:57, status:'Delayed 35 min'},
  // ── Arrivals · International (feed Immigration / Customs) ──
  {id:'EK 525', al:'Emirates',   ac:'B777-300',route:'DXB → HYD', dir:'arr', dom:false, time:'02:15', cap:354, total:315, local:246, transfer:69, status:'Landed'},
  {id:'QR 503', al:'Qatar Airways',ac:'A350-900',route:'DOH → HYD',dir:'arr', dom:false, time:'01:40', cap:283, total:243, local:190, transfer:53, status:'Landed'},
  {id:'AI 935', al:'Air India',  ac:'A321',    route:'DXB → HYD', dir:'arr', dom:false, time:'13:30', cap:222, total:195, local:152, transfer:43, status:'On Time'},
  {id:'SV 752', al:'Saudia',     ac:'A330-300',route:'JED → HYD', dir:'arr', dom:false, time:'04:50', cap:290, total:244, local:190, transfer:54, status:'On Time'},
  // ── Arrivals · Domestic ──
  {id:'6E 5311',al:'IndiGo',     ac:'A320',    route:'BOM → HYD', dir:'arr', dom:true,  time:'09:25', cap:186, total:167, local:154, transfer:13, status:'On Time'},
];

// derive actual entry load (slightly under predicted)
MOCK.exec.loadEntryAct = MOCK.exec.loadEntry.map(v => Math.round(v*0.95));
// per-touchpoint SLA (seconds) — real airport thresholds (keyed by TPS names)
MOCK.sla = {
  'Entry Gates':{wait:240,proc:20}, 'Check-In':{wait:600,proc:150}, 'Security':{wait:600,proc:30},
  'Emigration':{wait:600,proc:60}, 'Immigration':{wait:600,proc:60}, 'Customs':{wait:600,proc:30}, 'Transfers':{wait:600,proc:30},
};
// hourly heatmaps (bimodal busy shape): wait in MINUTES, processing time in SECONDS, per touchpoint
const HM_WAIT_PEAK = {'Entry Gates':5,'Check-In':11,'Security':13,'Emigration':8,'Immigration':7,'Customs':3,'Transfers':9}; // peak wait, min
MOCK.hmWait = {}; MOCK.hmProc = {};
TPS.forEach(tp => {
  const shape = curve(8,19,0,1); const mx = Math.max(...shape);   // bimodal 0..~1.85
  MOCK.hmWait[tp] = shape.map(v => Math.max(1, Math.round((v/mx) * (HM_WAIT_PEAK[tp]||10))));   // minutes
  const proc = (MOCK.sla[tp]||{proc:30}).proc;
  MOCK.hmProc[tp] = shape.map(v => Math.round(proc * (0.9 + 0.5*(v/mx))));                       // seconds: 0.9×SLA → ~1.4×SLA at peak
});
MOCK.heatmap = MOCK.hmWait;   // back-compat
