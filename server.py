"""
IoT Weather Station — Self-hosted backend
Receives sensor data from NodeMCU via HTTP POST, stores in SQLite,
serves a live dashboard and REST API.

Run:  uvicorn server:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3, time, os, json
from datetime import datetime, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────
DB_PATH   = "weather.db"
API_KEY   = os.getenv("IOT_API_KEY", "vu-iot-2026")   # set env var in production
MAX_ROWS  = 50_000                                      # auto-trim oldest rows beyond this

app = FastAPI(title="IoT Weather Station", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Database ──────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         INTEGER NOT NULL,          -- unix timestamp (seconds)
                temp       REAL,                      -- °C
                humidity   REAL,                      -- %
                pressure   REAL,                      -- hPa
                dew_point  REAL,                      -- °C
                abs_hum    REAL,                      -- g/m³
                risk       INTEGER                    -- 0–5 moisture risk
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_ts ON readings(ts)")
        db.commit()

init_db()

# ── Incoming data model ───────────────────────────────────────
class SensorReading(BaseModel):
    api_key:   str
    temp:      Optional[float] = None
    humidity:  Optional[float] = None
    pressure:  Optional[float] = None
    dew_point: Optional[float] = None
    abs_hum:   Optional[float] = None
    risk:      Optional[int]   = None

# ── POST /data — receive from NodeMCU ────────────────────────
@app.post("/data")
async def receive_data(reading: SensorReading):
    if reading.api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    ts = int(time.time())
    with get_db() as db:
        db.execute("""
            INSERT INTO readings (ts, temp, humidity, pressure, dew_point, abs_hum, risk)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ts, reading.temp, reading.humidity, reading.pressure,
              reading.dew_point, reading.abs_hum, reading.risk))
        db.commit()
        # Auto-trim if over limit
        count = db.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        if count > MAX_ROWS:
            db.execute("""
                DELETE FROM readings WHERE id IN (
                    SELECT id FROM readings ORDER BY ts ASC LIMIT ?
                )
            """, (count - MAX_ROWS,))
            db.commit()

    return {"ok": True, "ts": ts}

# ── GET /api/latest — most recent reading ────────────────────
@app.get("/api/latest")
def api_latest():
    row = get_db().execute(
        "SELECT * FROM readings ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    if not row:
        return {}
    return dict(row)

# ── GET /api/history — last N hours of readings ───────────────
@app.get("/api/history")
def api_history(hours: int = 24, limit: int = 500):
    since = int(time.time()) - hours * 3600
    rows = get_db().execute("""
        SELECT ts, temp, humidity, pressure, dew_point, abs_hum, risk
        FROM readings
        WHERE ts >= ?
        ORDER BY ts ASC
        LIMIT ?
    """, (since, limit)).fetchall()
    return [dict(r) for r in rows]

# ── GET /api/stats — daily stats ─────────────────────────────
@app.get("/api/stats")
def api_stats():
    today_start = int(datetime.now().replace(hour=0,minute=0,second=0).timestamp())
    week_start  = int((datetime.now() - timedelta(days=7)).timestamp())
    db = get_db()

    def stats_query(since):
        return db.execute("""
            SELECT
                ROUND(MIN(temp),1)      AS temp_min,
                ROUND(MAX(temp),1)      AS temp_max,
                ROUND(AVG(temp),1)      AS temp_avg,
                ROUND(MIN(humidity),1)  AS hum_min,
                ROUND(MAX(humidity),1)  AS hum_max,
                ROUND(AVG(humidity),1)  AS hum_avg,
                ROUND(MIN(pressure),0)  AS press_min,
                ROUND(MAX(pressure),0)  AS press_max,
                ROUND(AVG(pressure),0)  AS press_avg,
                ROUND(MAX(risk),0)      AS risk_max,
                COUNT(*)                AS count
            FROM readings WHERE ts >= ?
        """, (since,)).fetchone()

    today = stats_query(today_start)
    week  = stats_query(week_start)
    return {
        "today": dict(today) if today else {},
        "week":  dict(week)  if week  else {},
    }

# ── GET /api/risk_history — moisture risk events ──────────────
@app.get("/api/risk_history")
def api_risk_history(hours: int = 24):
    since = int(time.time()) - hours * 3600
    rows = get_db().execute("""
        SELECT ts, risk, dew_point, abs_hum, humidity
        FROM readings
        WHERE ts >= ? AND risk >= 2
        ORDER BY ts DESC
        LIMIT 200
    """, (since,)).fetchall()
    return [dict(r) for r in rows]

# ── GET / — serve the dashboard HTML ─────────────────────────
@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)

# ── Dashboard HTML (self-contained, no CDN required) ─────────
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IoT Weather Station</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0f1117; --card: #1a1d27; --border: #2a2d3a;
    --text: #e2e8f0; --muted: #64748b; --accent: #38bdf8;
    --green: #4ade80; --yellow: #facc15; --orange: #fb923c; --red: #f87171;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; min-height: 100vh; }
  header { background: var(--card); border-bottom: 1px solid var(--border); padding: 1rem 1.5rem; display: flex; align-items: center; justify-content: space-between; }
  header h1 { font-size: 1.1rem; font-weight: 600; display: flex; align-items: center; gap: 8px; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
  .last-update { font-size: .8rem; color: var(--muted); }
  main { max-width: 1200px; margin: 0 auto; padding: 1.5rem; }
  .grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.2rem 1.4rem; }
  .card-label { font-size: .75rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-bottom: .4rem; }
  .card-value { font-size: 2.2rem; font-weight: 700; line-height: 1; }
  .card-sub { font-size: .8rem; color: var(--muted); margin-top: .4rem; }
  .chart-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.2rem 1.4rem; margin-bottom: 1.5rem; }
  .chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
  .chart-title { font-size: .9rem; font-weight: 600; }
  .range-btns { display: flex; gap: .4rem; }
  .range-btn { background: var(--border); border: none; color: var(--muted); padding: .3rem .7rem; border-radius: 6px; font-size: .78rem; cursor: pointer; transition: .15s; }
  .range-btn.active, .range-btn:hover { background: var(--accent); color: #0f1117; }
  .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
  .stat-row { display: flex; justify-content: space-between; align-items: center; padding: .5rem 0; border-bottom: 1px solid var(--border); font-size: .85rem; }
  .stat-row:last-child { border-bottom: none; }
  .stat-key { color: var(--muted); }
  .stat-val { font-weight: 500; }
  .risk-bar-wrap { margin-top: .8rem; }
  .risk-bar-bg { height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }
  .risk-bar-fill { height: 100%; border-radius: 4px; transition: width .6s; }
  .risk-label { font-size: .8rem; margin-top: .4rem; font-weight: 600; }
  footer { text-align: center; font-size: .75rem; color: var(--muted); padding: 2rem 0 1rem; }
  canvas { max-height: 240px !important; }
</style>
</head>
<body>
<header>
  <h1><span class="dot" id="dot"></span> IoT Weather Station — Hà Nội</h1>
  <span class="last-update" id="lastUpdate">Loading...</span>
</header>
<main>
  <!-- Live readings -->
  <div class="grid-4" id="liveCards">
    <div class="card"><div class="card-label">Temperature</div><div class="card-value" id="cv-temp">--</div><div class="card-sub">°C</div></div>
    <div class="card"><div class="card-label">Humidity</div><div class="card-value" id="cv-hum">--</div><div class="card-sub">% relative</div></div>
    <div class="card"><div class="card-label">Pressure</div><div class="card-value" id="cv-press">--</div><div class="card-sub">hPa</div></div>
    <div class="card"><div class="card-label">Dew Point</div><div class="card-value" id="cv-dew">--</div><div class="card-sub">°C · <span id="cv-abshum">--</span> g/m³</div></div>
  </div>

  <!-- Moisture risk card -->
  <div class="card" style="margin-bottom:1.5rem" id="riskCard">
    <div class="card-label">Moisture Risk</div>
    <div class="risk-bar-wrap">
      <div class="risk-bar-bg"><div class="risk-bar-fill" id="riskFill" style="width:0%"></div></div>
    </div>
    <div class="risk-label" id="riskLabel">—</div>
  </div>

  <!-- Temperature + Humidity chart -->
  <div class="chart-card">
    <div class="chart-header">
      <span class="chart-title">Temperature & Humidity</span>
      <div class="range-btns">
        <button class="range-btn active" onclick="setRange(1,this)">1h</button>
        <button class="range-btn" onclick="setRange(6,this)">6h</button>
        <button class="range-btn" onclick="setRange(24,this)">24h</button>
        <button class="range-btn" onclick="setRange(168,this)">7d</button>
      </div>
    </div>
    <canvas id="chartTH"></canvas>
  </div>

  <!-- Pressure chart -->
  <div class="chart-card">
    <div class="chart-header">
      <span class="chart-title">Atmospheric Pressure</span>
    </div>
    <canvas id="chartP"></canvas>
  </div>

  <!-- Moisture risk chart -->
  <div class="chart-card">
    <div class="chart-header">
      <span class="chart-title">Moisture Risk Level (0 = Good, 5 = Condensation)</span>
    </div>
    <canvas id="chartRisk"></canvas>
  </div>

  <!-- Stats -->
  <div class="grid-2">
    <div class="card">
      <div class="card-label" style="margin-bottom:.8rem">Today's Stats</div>
      <div id="statsToday"></div>
    </div>
    <div class="card">
      <div class="card-label" style="margin-bottom:.8rem">Last 7 Days</div>
      <div id="statsWeek"></div>
    </div>
  </div>
</main>
<footer>IoT Weather Station · Self-hosted · Data stored locally</footer>

<script>
const RISK_LABELS = ['DRY/GOOD','NORMAL','MODERATE','HIGH','VERY HIGH','CONDENSATION'];
const RISK_COLORS = ['#4ade80','#4ade80','#facc15','#fb923c','#f87171','#ef4444'];
let currentHours = 1;
let chartTH, chartP, chartRisk;

// ── Chart defaults ──
Chart.defaults.color = '#64748b';
Chart.defaults.borderColor = '#2a2d3a';

function makeChart(id, datasets, yLabel, yOpts={}) {
  const ctx = document.getElementById(id).getContext('2d');
  return new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets },
    options: {
      responsive: true, maintainAspectRatio: true,
      animation: { duration: 300 },
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { boxWidth: 12, font: { size: 11 } } } },
      scales: {
        x: { ticks: { maxTicksLimit: 8, font: { size: 10 } } },
        y: { title: { display: true, text: yLabel }, ...yOpts }
      }
    }
  });
}

chartTH = makeChart('chartTH', [
  { label: 'Temp (°C)', data: [], borderColor: '#f87171', backgroundColor: '#f8717120', fill: true, tension: .3, pointRadius: 0 },
  { label: 'Humidity (%)', data: [], borderColor: '#38bdf8', backgroundColor: '#38bdf820', fill: true, tension: .3, pointRadius: 0, yAxisID: 'y2' }
], '°C', {});
chartTH.options.scales.y2 = { position: 'right', title: { display: true, text: '%' }, grid: { drawOnChartArea: false } };
chartTH.update();

chartP = makeChart('chartP', [
  { label: 'Pressure (hPa)', data: [], borderColor: '#a78bfa', backgroundColor: '#a78bfa20', fill: true, tension: .3, pointRadius: 0 }
], 'hPa');

chartRisk = makeChart('chartRisk', [
  { label: 'Risk Level', data: [], borderColor: '#fb923c', backgroundColor: '#fb923c30', fill: true, tension: .2, pointRadius: 0, stepped: true }
], 'Level (0–5)', { min: 0, max: 5 });

// ── Fetch & update latest ──
async function fetchLatest() {
  try {
    const d = await fetch('/api/latest').then(r=>r.json());
    if (!d.ts) return;
    document.getElementById('cv-temp').textContent  = d.temp?.toFixed(1) ?? '--';
    document.getElementById('cv-hum').textContent   = d.humidity?.toFixed(1) ?? '--';
    document.getElementById('cv-press').textContent = d.pressure?.toFixed(0) ?? '--';
    document.getElementById('cv-dew').textContent   = d.dew_point?.toFixed(1) ?? '--';
    document.getElementById('cv-abshum').textContent= d.abs_hum?.toFixed(1) ?? '--';
    // risk
    const r = d.risk ?? 0;
    const pct = (r / 5 * 100).toFixed(0);
    document.getElementById('riskFill').style.width = pct + '%';
    document.getElementById('riskFill').style.background = RISK_COLORS[r] || '#4ade80';
    document.getElementById('riskLabel').textContent = RISK_LABELS[r] || '—';
    document.getElementById('riskLabel').style.color = RISK_COLORS[r] || '#4ade80';
    // timestamp
    const ago = Math.round((Date.now()/1000 - d.ts));
    document.getElementById('lastUpdate').textContent = `Last update: ${ago}s ago`;
    document.getElementById('dot').style.background = ago < 30 ? 'var(--green)' : 'var(--orange)';
  } catch(e) {
    document.getElementById('dot').style.background = 'var(--red)';
  }
}

// ── Fetch & update history charts ──
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

// ── Fetch stats ──
async function fetchStats() {
  const s = await fetch('/api/stats').then(r=>r.json());
  const render = (el, st) => {
    if (!st || !st.count) { document.getElementById(el).innerHTML='<div style="color:var(--muted)">No data yet</div>'; return; }
    document.getElementById(el).innerHTML = `
      <div class="stat-row"><span class="stat-key">Temp min/max/avg</span><span class="stat-val">${st.temp_min} / ${st.temp_max} / ${st.temp_avg} °C</span></div>
      <div class="stat-row"><span class="stat-key">Humidity min/max/avg</span><span class="stat-val">${st.hum_min} / ${st.hum_max} / ${st.hum_avg} %</span></div>
      <div class="stat-row"><span class="stat-key">Pressure min/max/avg</span><span class="stat-val">${st.press_min} / ${st.press_max} / ${st.press_avg} hPa</span></div>
      <div class="stat-row"><span class="stat-key">Peak moisture risk</span><span class="stat-val" style="color:${RISK_COLORS[st.risk_max||0]}">${RISK_LABELS[st.risk_max||0]}</span></div>
      <div class="stat-row"><span class="stat-key">Readings stored</span><span class="stat-val">${st.count}</span></div>
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

// ── Poll ──
fetchLatest(); fetchHistory(); fetchStats();
setInterval(fetchLatest, 5000);
setInterval(fetchHistory, 15000);
setInterval(fetchStats, 60000);
</script>
</body>
</html>
"""

