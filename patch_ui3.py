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
  
  html[data-theme="light"] {
    --bg-color: #f1f5f9;
    --glass-bg: rgba(255, 255, 255, 0.85);
    --glass-border: rgba(0, 0, 0, 0.1);
    --text-main: #0f172a;
    --text-muted: #475569;
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
    transition: background-color 0.3s, color 0.3s;
  }
  header {
    background: var(--glass-bg);
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
  .last-update { font-size: 0.85rem; color: var(--text-muted); background: rgba(128,128,128,0.1); padding: 4px 12px; border-radius: 20px; border: 1px solid var(--glass-border); }
  
  .settings-bar { display: flex; gap: 10px; align-items: center; }
  .select-styled { background: transparent; color: var(--text-main); border: 1px solid var(--glass-border); padding: 4px 8px; border-radius: 8px; font-family: 'Outfit', sans-serif; font-size: 0.85rem; cursor: pointer; }
  .select-styled option { background: var(--bg-color); color: var(--text-main); }
  
  main { max-width: 1400px; margin: 0 auto; padding: 2rem; }
  .grid-5 { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
  .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
  
  .glass-card {
    background: var(--glass-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    padding: 1.5rem;
    transition: transform 0.3s ease, box-shadow 0.3s ease, background 0.3s;
    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    position: relative;
  }
  .glass-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.15), 0 0 0 1px rgba(128,128,128,0.1) inset;
  }
  
  .card-label { font-size: 0.85rem; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 0.8rem; display: flex; align-items: center; gap: 8px; }
  .card-value { font-size: 2.8rem; font-weight: 700; line-height: 1; }
  .card-sub { font-size: 0.9rem; font-weight: 400; color: var(--text-muted); margin-top: 0.5rem; }
  
  .tooltip { position: relative; cursor: help; border-bottom: 1px dotted var(--text-muted); }
  .tooltip .tooltiptext { visibility: hidden; width: 220px; background-color: var(--glass-bg); color: var(--text-main); text-align: center; border-radius: 8px; padding: 8px; position: absolute; z-index: 1; bottom: 125%; left: 50%; margin-left: -110px; opacity: 0; transition: opacity 0.3s; font-size: 0.8rem; font-weight: 400; border: 1px solid var(--glass-border); box-shadow: 0 4px 12px rgba(0,0,0,0.2); text-transform: none; letter-spacing: normal;}
  .tooltip:hover .tooltiptext { visibility: visible; opacity: 1; }
  
  .chart-card { padding: 1.5rem; margin-bottom: 2rem; display: flex; flex-direction: column; }
  .chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
  .chart-title { font-size: 1.1rem; font-weight: 600; letter-spacing: -0.2px; }
  .range-btns { display: flex; gap: 0.5rem; background: rgba(128,128,128,0.1); padding: 4px; border-radius: 10px; border: 1px solid var(--glass-border); }
  .range-btn { background: transparent; border: none; color: var(--text-muted); padding: 6px 12px; border-radius: 6px; font-size: 0.85rem; font-family: inherit; font-weight: 500; cursor: pointer; transition: all 0.2s; }
  .range-btn.active, .range-btn:hover { background: rgba(128,128,128,0.2); color: var(--text-main); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  
  .stat-row { display: flex; justify-content: space-between; align-items: center; padding: 0.8rem 0; border-bottom: 1px solid rgba(128,128,128,0.1); font-size: 0.95rem; }
  .stat-row:last-child { border-bottom: none; padding-bottom: 0; }
  .stat-key { color: var(--text-muted); }
  .stat-val { font-weight: 600; }
  
  .risk-bar-wrap { margin: 1rem 0 0.5rem; background: rgba(128,128,128,0.2); border-radius: 8px; height: 12px; overflow: hidden; border: 1px solid var(--glass-border); }
  .risk-bar-fill { height: 100%; border-radius: 8px; transition: width 1s cubic-bezier(0.4, 0, 0.2, 1), background-color 1s; box-shadow: 0 0 10px currentColor; }
  .risk-label { font-size: 1rem; font-weight: 600; text-align: right; margin-top: 0.5rem; }
  
  footer { text-align: center; font-size: 0.85rem; color: var(--text-muted); padding: 1rem 0 3rem; opacity: 0.7; }
  canvas { max-height: 280px !important; width: 100% !important; flex-grow: 1; }
  
  .icon-temp::before { content:'\2103'; color: #f43f5e; font-weight: 700; font-size: 1.1rem; }
  .icon-hum::before { content:'\1F4A7'; filter: grayscale(0.2) hue-rotate(180deg); }
  .icon-press::before { content:'\2601'; color: #a78bfa; font-size: 1.2rem; }
  .icon-dew::before { content:'\1F32B'; filter: grayscale(0.5); }
  .icon-alt::before { content:'\26F0'; color: #10b981; font-size: 1.1rem; }
  
  @media (max-width: 768px) {
    main { padding: 1rem; }
    .grid-5, .grid-2 { grid-template-columns: 1fr; }
    .card-value { font-size: 2.5rem; }
    header { flex-direction: column; gap: 10px; align-items: flex-start; }
    .settings-bar { width: 100%; justify-content: space-between; }
  }
</style>
</head>
<body>
<header>
  <h1><span class="dot" id="dot"></span> <span data-lang="title">Smart Environment Dashboard</span></h1>
  <div class="settings-bar">
    <span class="last-update" id="lastUpdate">Syncing...</span>
    <select id="langSelect" class="select-styled" onchange="changeLang()">
      <option value="en">🇺🇸 EN</option>
      <option value="vi">🇻🇳 VI</option>
    </select>
    <select id="themeSelect" class="select-styled" onchange="changeTheme()">
      <option value="system" data-lang="theme_sys">System</option>
      <option value="dark" data-lang="theme_dark">Dark</option>
      <option value="light" data-lang="theme_light">Light</option>
    </select>
  </div>
</header>
<main>
  <div class="grid-5" id="liveCards">
    <div class="glass-card"><div class="card-label icon-temp" data-lang="temp">Temperature</div><div class="card-value" id="cv-temp">--</div><div class="card-sub">°C</div></div>
    <div class="glass-card"><div class="card-label icon-hum" data-lang="hum">Humidity</div><div class="card-value" id="cv-hum">--</div><div class="card-sub" data-lang="hum_sub">% Relative</div></div>
    <div class="glass-card"><div class="card-label icon-press" data-lang="press">Pressure</div><div class="card-value" id="cv-press">--</div><div class="card-sub">hPa</div></div>
    <div class="glass-card">
      <div class="card-label icon-alt tooltip" data-lang="alt">Altitude
        <span class="tooltiptext" data-lang="alt_tt">Derived using Barometric formula based on sea-level pressure (1013.25 hPa).</span>
      </div>
      <div class="card-value" id="cv-alt">--</div><div class="card-sub">m</div>
    </div>
    <div class="glass-card"><div class="card-label icon-dew" data-lang="dew">Dew Point</div><div class="card-value" id="cv-dew">--</div><div class="card-sub">°C <span style="margin:0 6px;color:var(--glass-border)">|</span> <span id="cv-abshum" style="color:var(--accent)">--</span> g/m³</div></div>
  </div>

  <div class="grid-2">
    <div class="glass-card" id="riskCard">
      <div class="card-label" data-lang="risk">Moisture Risk Index</div>
      <div class="risk-bar-wrap"><div class="risk-bar-fill" id="riskFill" style="width:0%"></div></div>
      <div class="risk-label" id="riskLabel">—</div>
    </div>
    <div class="glass-card" style="display: flex; align-items: center; justify-content: center; flex-direction: column;">
      <div class="card-label tooltip" style="margin-bottom:12px; justify-content:center; text-align:center" data-lang="forecast_title">Weather Forecast (Zambretti)
         <span class="tooltiptext" data-lang="forecast_tt">Forecast algorithm calculated locally on backend by observing atmospheric pressure trend over the past 3 hours.</span>
      </div>
      <div style="text-align:center;">
        <div style="font-size:2rem; font-weight:700; color:var(--accent); text-shadow: 0 0 15px rgba(56,189,248,0.4);" id="forecastText">Collecting data...</div>
        <div style="font-size:1rem; color:var(--text-muted); margin-top:8px;">Trend: <span id="trendVal">--</span> hPa/3h</div>
      </div>
    </div>
  </div>

  <div class="chart-card glass-card">
    <div class="chart-header">
      <span class="chart-title" data-lang="chart_th">Temperature & Humidity Trends</span>
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
      <div class="chart-header"><span class="chart-title" data-lang="chart_p">Atmospheric Pressure</span></div>
      <div style="position: relative; height: 240px; width: 100%;"><canvas id="chartP"></canvas></div>
    </div>
    <div class="chart-card glass-card">
      <div class="chart-header"><span class="chart-title" data-lang="chart_r">Moisture Risk Level</span></div>
      <div style="position: relative; height: 240px; width: 100%;"><canvas id="chartRisk"></canvas></div>
    </div>
  </div>

  <div class="grid-2">
    <div class="glass-card">
      <div class="card-label" style="margin-bottom:1.2rem; font-size:1rem; color:var(--text-main);" data-lang="stat_today">Today's Analytics</div>
      <div id="statsToday"></div>
    </div>
    <div class="glass-card">
      <div class="card-label" style="margin-bottom:1.2rem; font-size:1rem; color:var(--text-main);" data-lang="stat_week">Weekly Overview</div>
      <div id="statsWeek"></div>
    </div>
  </div>
</main>
<footer data-lang="footer">Powered by Advanced IoT Architecture</footer>

<script>
// Lang Dictionaries
const LANG = {
  en: {
    title: "Smart Environment Dashboard", theme_sys: "System", theme_dark: "Dark", theme_light: "Light",
    temp: "Temperature", hum: "Humidity", hum_sub: "% Relative", press: "Pressure",
    alt: "Altitude", alt_tt: "Derived using Barometric formula based on sea-level pressure (1013.25 hPa).",
    dew: "Dew Point", risk: "Moisture Risk Index",
    forecast_title: "Weather Forecast (Zambretti)", forecast_tt: "Forecast algorithm calculated by observing atmospheric pressure trend over the past 3 hours.",
    chart_th: "Temperature & Humidity Trends", chart_p: "Atmospheric Pressure", chart_r: "Moisture Risk Level",
    stat_today: "Today's Analytics", stat_week: "Weekly Overview", footer: "Powered by Advanced IoT Architecture",
    stat_t: "Temperature (Min/Max/Avg)", stat_h: "Humidity (Min/Max/Avg)", stat_p: "Pressure (Min/Max/Avg)", stat_r: "Peak Moisture Risk", stat_c: "Data Points Recorded",
    risk0:"DRY / OPTIMAL", risk1:"NORMAL", risk2:"MODERATE RISK", risk3:"HIGH RISK", risk4:"VERY HIGH", risk5:"CONDENSATION WARNING", no_data:"No data yet"
  },
  vi: {
    title: "Bảng Điều Khiển Môi Trường IoT", theme_sys: "Hệ thống", theme_dark: "Tối", theme_light: "Sáng",
    temp: "Nhiệt độ", hum: "Độ ẩm", hum_sub: "% Tương đối", press: "Áp suất",
    alt: "Độ cao", alt_tt: "Tính toán bằng công thức khí quyển dựa trên áp suất chuẩn mặt nước biển (1013.25 hPa).",
    dew: "Điểm sương", risk: "Chỉ số Rủi ro Nấm mốc",
    forecast_title: "Dự báo Thời tiết (Zambretti)", forecast_tt: "Thuật toán dự báo được tính toán cục bộ dựa trên xu hướng áp suất trong 3 giờ qua.",
    chart_th: "Biểu đồ Nhiệt độ & Độ ẩm", chart_p: "Biểu đồ Áp suất", chart_r: "Mức độ Rủi ro Nấm mốc",
    stat_today: "Thống kê Hôm nay", stat_week: "Thống kê 7 Ngày", footer: "Phát triển bởi Kiến trúc IoT Hiện đại",
    stat_t: "Nhiệt độ (Min/Max/TB)", stat_h: "Độ ẩm (Min/Max/TB)", stat_p: "Áp suất (Min/Max/TB)", stat_r: "Rủi ro Cao nhất", stat_c: "Số bản ghi",
    risk0:"KHÔ / TỐT", risk1:"BÌNH THƯỜNG", risk2:"NGUY CƠ VỪA", risk3:"NGUY CƠ CAO", risk4:"RẤT CAO", risk5:"CẢNH BÁO NGƯNG TỤ", no_data:"Chưa có dữ liệu"
  }
};

let currentLang = 'en';
let currentHours = 1;
let chartTH, chartP, chartRisk;
let statsData = null; // Cache to re-render when lang changes

const RISK_COLORS = ['#10b981','#10b981','#f59e0b','#f97316','#ef4444','#b91c1c'];

function updateTexts() {
  document.querySelectorAll('[data-lang]').forEach(el => {
    let key = el.getAttribute('data-lang');
    if (LANG[currentLang][key]) {
      if(el.tagName==='OPTION') el.text = LANG[currentLang][key];
      else {
        // preserve nested tags like tooltips if we only want to change text node
        if(el.classList.contains('tooltip')) {
            let tt = el.querySelector('.tooltiptext');
            el.childNodes[0].nodeValue = LANG[currentLang][key] + " ";
            if(tt) tt.innerText = LANG[currentLang][key + "_tt"];
        } else {
            el.innerHTML = LANG[currentLang][key];
        }
      }
    }
  });
  if(statsData) renderStatsUI(statsData);
}

function changeLang() {
  currentLang = document.getElementById('langSelect').value;
  updateTexts();
  fetchLatest(); // refresh forecast text
}

function initTheme() {
  const saved = localStorage.getItem('theme') || 'system';
  document.getElementById('themeSelect').value = saved;
  applyTheme(saved);
}

function changeTheme() {
  const val = document.getElementById('themeSelect').value;
  localStorage.setItem('theme', val);
  applyTheme(val);
}

function applyTheme(theme) {
  if (theme === 'system') {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      document.documentElement.setAttribute('data-theme', 'light');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  } else if (theme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
  // Optional: re-render charts for color updates
}

window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', e => {
  if (document.getElementById('themeSelect').value === 'system') applyTheme('system');
});

Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(128, 128, 128, 0.1)';
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
        y: { grid: { color: 'rgba(128, 128, 128, 0.1)' }, border: { dash: [4, 4] }, title: { display: true, text: yLabel, color: '#64748b', font: {size: 11} }, ...yOpts }
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
    document.getElementById('cv-alt').textContent   = d.altitude?.toFixed(1) ?? '--';
    document.getElementById('cv-dew').textContent   = d.dew_point?.toFixed(1) ?? '--';
    document.getElementById('cv-abshum').textContent= d.abs_hum?.toFixed(1) ?? '--';
    
    const r = d.risk ?? 0;
    const pct = (r / 5 * 100).toFixed(0);
    const riskFill = document.getElementById('riskFill');
    riskFill.style.width = pct + '%';
    riskFill.style.backgroundColor = RISK_COLORS[r] || '#10b981';
    
    const riskLabel = document.getElementById('riskLabel');
    riskLabel.textContent = LANG[currentLang]['risk'+r] || '—';
    riskLabel.style.color = RISK_COLORS[r] || '#10b981';
    
    if (d.forecastText) {
        document.getElementById('forecastText').textContent = currentLang === 'vi' ? d.forecastTextVi : d.forecastText;
        let tr = d.pressureTrendHpa;
        document.getElementById('trendVal').textContent = (tr > 0 ? "+" : "") + tr.toFixed(2);
    }
    
    const ago = Math.round((Date.now()/1000 - d.ts));
    document.getElementById('lastUpdate').textContent = \`Updated: \${ago}s ago\`;
    const dot = document.getElementById('dot');
    if (ago < 30) { dot.style.background = 'var(--green)'; dot.style.boxShadow = '0 0 10px var(--green)'; } 
    else { dot.style.background = 'var(--orange)'; dot.style.boxShadow = '0 0 10px var(--orange)'; }
  } catch(e) {
    document.getElementById('dot').style.background = 'var(--red)';
    document.getElementById('dot').style.boxShadow = '0 0 10px var(--red)';
  }
}

async function fetchHistory() {
  const limit = currentHours <= 6 ? 500 : 1000;
  const data = await fetch(\`/api/history?hours=\${currentHours}&limit=\${limit}\`).then(r=>r.json());
  if (!data.length) return;
  const fmt = ts => {
    const d = new Date(ts*1000);
    return currentHours <= 6
      ? d.toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'})
      : d.toLocaleDateString('vi-VN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'});
  };
  const labels = data.map(d=>fmt(d.ts));
  chartTH.data.labels = labels; chartTH.data.datasets[0].data = data.map(d=>d.temp); chartTH.data.datasets[1].data = data.map(d=>d.humidity);
  chartTH.update('none');
  chartP.data.labels = labels; chartP.data.datasets[0].data = data.map(d=>d.pressure);
  chartP.update('none');
  chartRisk.data.labels = labels; chartRisk.data.datasets[0].data = data.map(d=>d.risk);
  chartRisk.update('none');
}

function renderStatsUI(s) {
  const l = LANG[currentLang];
  const render = (el, st) => {
    if (!st || !st.count) { document.getElementById(el).innerHTML=\`<div style="color:var(--text-muted); padding:1rem 0;">\${l.no_data}</div>\`; return; }
    document.getElementById(el).innerHTML = \`
      <div class="stat-row"><span class="stat-key">\${l.stat_t}</span><span class="stat-val">\${st.temp_min} / \${st.temp_max} / <span style="color:var(--accent)">\${st.temp_avg} °C</span></span></div>
      <div class="stat-row"><span class="stat-key">\${l.stat_h}</span><span class="stat-val">\${st.hum_min} / \${st.hum_max} / <span style="color:var(--accent)">\${st.hum_avg} %</span></span></div>
      <div class="stat-row"><span class="stat-key">\${l.stat_p}</span><span class="stat-val">\${st.press_min} / \${st.press_max} / <span style="color:var(--accent)">\${st.press_avg} hPa</span></span></div>
      <div class="stat-row"><span class="stat-key">\${l.stat_r}</span><span class="stat-val" style="color:\${RISK_COLORS[st.risk_max||0]}">\${l['risk'+(st.risk_max||0)]}</span></div>
      <div class="stat-row"><span class="stat-key">\${l.stat_c}</span><span class="stat-val">\${st.count.toLocaleString()}</span></div>
    \`;
  };
  render('statsToday', s.today);
  render('statsWeek',  s.week);
}

async function fetchStats() {
  statsData = await fetch('/api/stats').then(r=>r.json());
  renderStatsUI(statsData);
}

function setRange(h, btn) {
  currentHours = h;
  document.querySelectorAll('.range-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  fetchHistory();
}

initTheme();
fetchLatest(); fetchHistory(); fetchStats();
setInterval(fetchLatest, 5000);
setInterval(fetchHistory, 15000);
setInterval(fetchStats, 60000);
</script>
</body>
</html>
'''

with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_api_latest = False
for line in lines:
    if line.startswith('@app.get("/api/latest")'):
        in_api_latest = True
        new_lines.append(line)
        new_lines.append("def api_latest():\n")
        new_lines.append("    db = get_db()\n")
        new_lines.append("    row = db.execute('SELECT * FROM readings ORDER BY ts DESC LIMIT 1').fetchone()\n")
        new_lines.append("    if not row:\n")
        new_lines.append("        return {}\n")
        new_lines.append("    res = dict(row)\n")
        new_lines.append("    three_hours_ago = res['ts'] - 3 * 3600\n")
        new_lines.append("    old_row = db.execute('SELECT pressure FROM readings WHERE ts >= ? ORDER BY ts ASC LIMIT 1', (three_hours_ago,)).fetchone()\n")
        new_lines.append("    if old_row and old_row['pressure'] and res.get('pressure'):\n")
        new_lines.append("        trend = res['pressure'] - old_row['pressure']\n")
        new_lines.append("        res['pressureTrendHpa'] = trend\n")
        new_lines.append("        if trend <= -1.6:\n")
        new_lines.append("            res['forecastText'] = 'Rain likely soon'\n")
        new_lines.append("            res['forecastTextVi'] = 'Sắp có mưa rào'\n")
        new_lines.append("        elif trend <= -0.5:\n")
        new_lines.append("            res['forecastText'] = 'Clouding over'\n")
        new_lines.append("            res['forecastTextVi'] = 'Nhiều mây hơn'\n")
        new_lines.append("        elif trend < 0.5:\n")
        new_lines.append("            res['forecastText'] = 'No change'\n")
        new_lines.append("            res['forecastTextVi'] = 'Trời ổn định'\n")
        new_lines.append("        elif trend < 1.6:\n")
        new_lines.append("            res['forecastText'] = 'Improving'\n")
        new_lines.append("            res['forecastTextVi'] = 'Quang đãng hơn'\n")
        new_lines.append("        else:\n")
        new_lines.append("            res['forecastText'] = 'Clear skies ahead'\n")
        new_lines.append("            res['forecastTextVi'] = 'Trời quang mây tạnh'\n")
        new_lines.append("    else:\n")
        new_lines.append("        res['pressureTrendHpa'] = 0\n")
        new_lines.append("        res['forecastText'] = 'Collecting data...'\n")
        new_lines.append("        res['forecastTextVi'] = 'Đang thu thập...'\n")
        new_lines.append("    return res\n")
        continue
    
    if in_api_latest:
        if line.startswith('@app.get("/api/history")'):
            in_api_latest = False
            new_lines.append(line)
        else:
            continue
    elif line.startswith('DASHBOARD_HTML = '):
        new_lines.append('DASHBOARD_HTML = r"""' + new_html + '"""\n')
        break
    else:
        new_lines.append(line)

with open('server.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
