new_html = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IoT Weather Station Pro</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg-color: #0b0c10;
    --glass-bg: rgba(25, 28, 36, 0.65);
    --glass-border: rgba(255, 255, 255, 0.08);
    --text-main: #f8f9fa;
    --text-muted: #94a3b8;
    --accent: #38bdf8;
    --accent-glow: rgba(56, 189, 248, 0.4);
    --green: #10b981; --yellow: #f59e0b; --orange: #f97316; --red: #ef4444;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { 
    background: var(--bg-color); 
    background-image: radial-gradient(circle at 15% 50%, rgba(56,189,248,0.08), transparent 25%), radial-gradient(circle at 85% 30%, rgba(139,92,246,0.08), transparent 25%);
    background-attachment: fixed;
    color: var(--text-main); 
    font-family: 'Outfit', sans-serif; 
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }
  header {
    background: rgba(11, 12, 16, 0.8);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--glass-border);
    padding: 1.2rem 2rem;
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 100;
  }
  header h1 { font-size: 1.4rem; font-weight: 600; display: flex; align-items: center; gap: 12px; letter-spacing: -0.5px; }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--green); box-shadow: 0 0 10px var(--green); animation: pulse 2s infinite ease-in-out; }
  @keyframes pulse { 0%,100%{transform: scale(0.95); box-shadow: 0 0 8px rgba(16,185,129,0.5);} 50%{transform: scale(1.05); box-shadow: 0 0 16px rgba(16,185,129,0.8);} }
  .last-update { font-size: 0.85rem; color: var(--text-muted); background: rgba(255,255,255,0.05); padding: 4px 12px; border-radius: 20px; border: 1px solid var(--glass-border); }
  
  main { max-width: 1400px; margin: 0 auto; padding: 2rem; }
  .grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
  .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
  
  .glass-card {
    background: var(--glass-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    padding: 1.5rem;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
  }
  .glass-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.1) inset;
  }
  
  .card-label { font-size: 0.85rem; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 0.8rem; display: flex; align-items: center; gap: 8px; }
  .card-value { font-size: 3rem; font-weight: 700; line-height: 1; background: linear-gradient(135deg, #fff, #cbd5e1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .card-sub { font-size: 0.9rem; font-weight: 400; color: var(--text-muted); margin-top: 0.5rem; }
  
  .chart-card { padding: 1.5rem; margin-bottom: 2rem; display: flex; flex-direction: column; }
  .chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
  .chart-title { font-size: 1.1rem; font-weight: 600; letter-spacing: -0.2px; }
  .range-btns { display: flex; gap: 0.5rem; background: rgba(0,0,0,0.2); padding: 4px; border-radius: 10px; border: 1px solid var(--glass-border); }
  .range-btn { background: transparent; border: none; color: var(--text-muted); padding: 6px 12px; border-radius: 6px; font-size: 0.85rem; font-family: inherit; font-weight: 500; cursor: pointer; transition: all 0.2s; }
  .range-btn.active, .range-btn:hover { background: rgba(255,255,255,0.1); color: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
  
  .stat-row { display: flex; justify-content: space-between; align-items: center; padding: 0.8rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.95rem; }
  .stat-row:last-child { border-bottom: none; padding-bottom: 0; }
  .stat-key { color: var(--text-muted); }
  .stat-val { font-weight: 600; }
  
  .risk-bar-wrap { margin: 1rem 0 0.5rem; background: rgba(0,0,0,0.3); border-radius: 8px; height: 12px; overflow: hidden; border: 1px solid var(--glass-border); box-shadow: inset 0 2px 4px rgba(0,0,0,0.5); }
  .risk-bar-fill { height: 100%; border-radius: 8px; transition: width 1s cubic-bezier(0.4, 0, 0.2, 1), background-color 1s; box-shadow: 0 0 10px currentColor; }
  .risk-label { font-size: 1rem; font-weight: 600; text-align: right; margin-top: 0.5rem; }
  
  footer { text-align: center; font-size: 0.85rem; color: var(--text-muted); padding: 1rem 0 3rem; opacity: 0.7; }
  canvas { max-height: 280px !important; width: 100% !important; flex-grow: 1; }
  
  .icon-temp::before { content:'\2103'; color: #f43f5e; font-weight: 700; font-size: 1.1rem; }
  .icon-hum::before { content:'\1F4A7'; filter: grayscale(0.2) hue-rotate(180deg); }
  .icon-press::before { content:'\2601'; color: #a78bfa; font-size: 1.2rem; }
  .icon-dew::before { content:'\1F32B'; filter: grayscale(0.5); }
  
  @media (max-width: 768px) {
    main { padding: 1rem; }
    .grid-4, .grid-2 { grid-template-columns: 1fr; }
    .card-value { font-size: 2.5rem; }
  }
</style>
</head>
<body>
<header>
  <h1><span class="dot" id="dot"></span> Smart Environment Dashboard</h1>
  <span class="last-update" id="lastUpdate">Syncing...</span>
</header>
<main>
  <div class="grid-4" id="liveCards">
    <div class="glass-card"><div class="card-label icon-temp">Temperature</div><div class="card-value" id="cv-temp">--</div><div class="card-sub">°C</div></div>
    <div class="glass-card"><div class="card-label icon-hum">Humidity</div><div class="card-value" id="cv-hum">--</div><div class="card-sub">% Relative</div></div>
    <div class="glass-card"><div class="card-label icon-press">Pressure</div><div class="card-value" id="cv-press">--</div><div class="card-sub">hPa</div></div>
    <div class="glass-card"><div class="card-label icon-dew">Dew Point</div><div class="card-value" id="cv-dew">--</div><div class="card-sub">°C <span style="margin:0 6px;color:var(--glass-border)">|</span> <span id="cv-abshum" style="color:var(--accent)">--</span> g/m³</div></div>
  </div>

  <div class="grid-2">
    <div class="glass-card" id="riskCard">
      <div class="card-label">Moisture Risk Index</div>
      <div class="risk-bar-wrap">
        <div class="risk-bar-fill" id="riskFill" style="width:0%"></div>
      </div>
      <div class="risk-label" id="riskLabel">—</div>
    </div>
    <div class="glass-card" style="display: flex; align-items: center; justify-content: center;">
      <div style="text-align:center;">
        <div style="font-size:0.9rem; color:var(--text-muted); margin-bottom:8px; text-transform:uppercase; letter-spacing:1px;">System Status</div>
        <div style="font-size:1.5rem; font-weight:600; color:var(--green); text-shadow: 0 0 15px rgba(16,185,129,0.4);">Online & Optimal</div>
      </div>
    </div>
  </div>

  <div class="chart-card glass-card">
    <div class="chart-header">
      <span class="chart-title">Temperature & Humidity Trends</span>
      <div class="range-btns">
        <button class="range-btn active" onclick="setRange(1,this)">1h</button>
        <button class="range-btn" onclick="setRange(6,this)">6h</button>
        <button class="range-btn" onclick="setRange(24,this)">24h</button>
        <button class="range-btn" onclick="setRange(168,this)">7d</button>
      </div>
    </div>
    <div style="position: relative; height: 280px; width: 100%;"><canvas id="chartTH"></canvas></div>
  </div>

  <div class="grid-2">
    <div class="chart-card glass-card">
      <div class="chart-header"><span class="chart-title">Atmospheric Pressure</span></div>
      <div style="position: relative; height: 240px; width: 100%;"><canvas id="chartP"></canvas></div>
    </div>
    <div class="chart-card glass-card">
      <div class="chart-header"><span class="chart-title">Moisture Risk Level</span></div>
      <div style="position: relative; height: 240px; width: 100%;"><canvas id="chartRisk"></canvas></div>
    </div>
  </div>

  <div class="grid-2">
    <div class="glass-card">
      <div class="card-label" style="margin-bottom:1.2rem; font-size:1rem; color:#fff;">Today's Analytics</div>
      <div id="statsToday"></div>
    </div>
    <div class="glass-card">
      <div class="card-label" style="margin-bottom:1.2rem; font-size:1rem; color:#fff;">Weekly Overview</div>
      <div id="statsWeek"></div>
    </div>
  </div>
</main>
<footer>Powered by Advanced IoT Architecture</footer>

<script>
const RISK_LABELS = ['DRY / OPTIMAL','NORMAL','MODERATE RISK','HIGH RISK','VERY HIGH','CONDENSATION WARNING'];
const RISK_COLORS = ['#10b981','#10b981','#f59e0b','#f97316','#ef4444','#b91c1c'];
let currentHours = 1;
let chartTH, chartP, chartRisk;

Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.05)';
Chart.defaults.font.family = "'Outfit', sans-serif";

function createGradient(ctx, color1, color2) {
  const gradient = ctx.createLinearGradient(0, 0, 0, 300);
  gradient.addColorStop(0, color1);
  gradient.addColorStop(1, color2);
  return gradient;
}

function makeChart(id, datasets, yLabel, yOpts={}) {
  const ctx = document.getElementById(id).getContext('2d');
  return new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 800, easing: 'easeOutQuart' },
      interaction: { mode: 'index', intersect: false },
      plugins: { 
        legend: { labels: { boxWidth: 12, usePointStyle: true, font: { size: 12, weight: 500 } } },
        tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.9)', titleFont: { size: 13, family: "'Outfit', sans-serif" }, bodyFont: { size: 13, family: "'Outfit', sans-serif" }, padding: 12, cornerRadius: 8, borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1 }
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 8, font: { size: 11 } } },
        y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, border: { dash: [4, 4] }, title: { display: true, text: yLabel, color: '#64748b', font: {size: 11} }, ...yOpts }
      }
    }
  });
}

const ctxTH = document.getElementById('chartTH').getContext('2d');
chartTH = makeChart('chartTH', [
  { label: 'Temp (°C)', data: [], borderColor: '#f43f5e', backgroundColor: createGradient(ctxTH, 'rgba(244, 63, 94, 0.4)', 'rgba(244, 63, 94, 0.0)'), fill: true, tension: 0.4, borderWidth: 2, pointRadius: 0, pointHoverRadius: 6 },
  { label: 'Humidity (%)', data: [], borderColor: '#38bdf8', backgroundColor: createGradient(ctxTH, 'rgba(56, 189, 248, 0.4)', 'rgba(56, 189, 248, 0.0)'), fill: true, tension: 0.4, borderWidth: 2, pointRadius: 0, pointHoverRadius: 6, yAxisID: 'y2' }
], '°C', {});
chartTH.options.scales.y2 = { position: 'right', grid: { drawOnChartArea: false }, border: { dash: [4, 4] }, title: { display: true, text: '%', color: '#64748b', font: {size: 11} } };
chartTH.update();

const ctxP = document.getElementById('chartP').getContext('2d');
chartP = makeChart('chartP', [
  { label: 'Pressure (hPa)', data: [], borderColor: '#a78bfa', backgroundColor: createGradient(ctxP, 'rgba(167, 139, 250, 0.4)', 'rgba(167, 139, 250, 0.0)'), fill: true, tension: 0.4, borderWidth: 2, pointRadius: 0, pointHoverRadius: 6 }
], 'hPa');

const ctxRisk = document.getElementById('chartRisk').getContext('2d');
chartRisk = makeChart('chartRisk', [
  { label: 'Risk Level', data: [], borderColor: '#fb923c', backgroundColor: createGradient(ctxRisk, 'rgba(251, 146, 60, 0.3)', 'rgba(251, 146, 60, 0.0)'), fill: true, tension: 0.1, borderWidth: 2, pointRadius: 0, pointHoverRadius: 6, stepped: 'middle' }
], 'Level (0–5)', { min: 0, max: 5, ticks: { stepSize: 1 } });

async function fetchLatest() {
  try {
    const d = await fetch('/api/latest').then(r=>r.json());
    if (!d.ts) return;
    document.getElementById('cv-temp').textContent  = d.temp?.toFixed(1) ?? '--';
    document.getElementById('cv-hum').textContent   = d.humidity?.toFixed(1) ?? '--';
    document.getElementById('cv-press').textContent = d.pressure?.toFixed(0) ?? '--';
    document.getElementById('cv-dew').textContent   = d.dew_point?.toFixed(1) ?? '--';
    document.getElementById('cv-abshum').textContent= d.abs_hum?.toFixed(1) ?? '--';
    
    const r = d.risk ?? 0;
    const pct = (r / 5 * 100).toFixed(0);
    const riskFill = document.getElementById('riskFill');
    riskFill.style.width = pct + '%';
    riskFill.style.backgroundColor = RISK_COLORS[r] || '#10b981';
    riskFill.style.color = RISK_COLORS[r] || '#10b981';
    
    const riskLabel = document.getElementById('riskLabel');
    riskLabel.textContent = RISK_LABELS[r] || '—';
    riskLabel.style.color = RISK_COLORS[r] || '#10b981';
    riskLabel.style.textShadow = `0 0 10px ${RISK_COLORS[r]}66`;
    
    const ago = Math.round((Date.now()/1000 - d.ts));
    document.getElementById('lastUpdate').textContent = `Updated: ${ago}s ago`;
    const dot = document.getElementById('dot');
    if (ago < 30) {
      dot.style.background = 'var(--green)';
      dot.style.boxShadow = '0 0 10px var(--green)';
    } else {
      dot.style.background = 'var(--orange)';
      dot.style.boxShadow = '0 0 10px var(--orange)';
    }
  } catch(e) {
    document.getElementById('dot').style.background = 'var(--red)';
    document.getElementById('dot').style.boxShadow = '0 0 10px var(--red)';
    document.getElementById('lastUpdate').textContent = 'Connection Lost';
  }
}

async function fetchHistory() {
  const limit = currentHours <= 6 ? 500 : 1000;
  const data = await fetch(`/api/history?hours=${currentHours}&limit=${limit}`).then(r=>r.json());
  if (!data.length) return;
  const fmt = ts => {
    const d = new Date(ts*1000);
    return currentHours <= 6
      ? d.toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'})
      : d.toLocaleDateString('vi-VN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'});
  };
  const labels = data.map(d=>fmt(d.ts));
  chartTH.data.labels = labels;
  chartTH.data.datasets[0].data = data.map(d=>d.temp);
  chartTH.data.datasets[1].data = data.map(d=>d.humidity);
  chartTH.update('none');
  
  chartP.data.labels = labels;
  chartP.data.datasets[0].data = data.map(d=>d.pressure);
  chartP.update('none');
  
  chartRisk.data.labels = labels;
  chartRisk.data.datasets[0].data = data.map(d=>d.risk);
  chartRisk.update('none');
}

async function fetchStats() {
  const s = await fetch('/api/stats').then(r=>r.json());
  const render = (el, st) => {
    if (!st || !st.count) { document.getElementById(el).innerHTML='<div style="color:var(--text-muted); padding:1rem 0;">No data accumulated yet</div>'; return; }
    document.getElementById(el).innerHTML = `
      <div class="stat-row"><span class="stat-key">Temperature (Min/Max/Avg)</span><span class="stat-val">${st.temp_min} / ${st.temp_max} / <span style="color:var(--accent)">${st.temp_avg} °C</span></span></div>
      <div class="stat-row"><span class="stat-key">Humidity (Min/Max/Avg)</span><span class="stat-val">${st.hum_min} / ${st.hum_max} / <span style="color:var(--accent)">${st.hum_avg} %</span></span></div>
      <div class="stat-row"><span class="stat-key">Pressure (Min/Max/Avg)</span><span class="stat-val">${st.press_min} / ${st.press_max} / <span style="color:var(--accent)">${st.press_avg} hPa</span></span></div>
      <div class="stat-row"><span class="stat-key">Peak Moisture Risk</span><span class="stat-val" style="color:${RISK_COLORS[st.risk_max||0]}; text-shadow:0 0 10px ${RISK_COLORS[st.risk_max||0]}40;">${RISK_LABELS[st.risk_max||0]}</span></div>
      <div class="stat-row"><span class="stat-key">Data Points Recorded</span><span class="stat-val">${st.count.toLocaleString()}</span></div>
    `;
  };
  render('statsToday', s.today);
  render('statsWeek',  s.week);
}

function setRange(h, btn) {
  currentHours = h;
  document.querySelectorAll('.range-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  fetchHistory();
}

fetchLatest(); fetchHistory(); fetchStats();
setInterval(fetchLatest, 5000);
setInterval(fetchHistory, 15000);
setInterval(fetchStats, 60000);
</script>
</body>
</html>
'''

with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

parts = content.split('DASHBOARD_HTML = r"""<!DOCTYPE html>')
head = parts[0]

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(head + 'DASHBOARD_HTML = r"""' + new_html + '"""\n')
