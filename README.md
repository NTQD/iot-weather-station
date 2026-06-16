# IoT Weather Station — Self-hosted Platform

Completely replaces Blynk. Your data stays on your own machine.

---

## Files

| File | Purpose |
|---|---|
| `server.py` | FastAPI backend + embedded dashboard |
| `iot_weather_station_v6.ino` | NodeMCU sketch (replaces Blynk) |
| `requirements.txt` | Python dependencies |
| `weather.db` | SQLite database (auto-created on first run) |

---

## Server setup (run once)

### Option A — Your laptop (same WiFi as NodeMCU)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run server
uvicorn server:app --host 0.0.0.0 --port 8000
```

Then open browser: http://localhost:8000

Find your laptop IP address:
- Windows: ipconfig → IPv4 Address
- Mac/Linux: ifconfig or ip addr

### Option B — VPS (always-on, recommended)

```bash
# On your VPS (Ubuntu/Debian)
pip install -r requirements.txt

# Run in background
nohup uvicorn server:app --host 0.0.0.0 --port 8000 &

# Or use screen
screen -S iot
uvicorn server:app --host 0.0.0.0 --port 8000
# Ctrl+A then D to detach
```

Open firewall port 8000:
```bash
ufw allow 8000
```

---

## NodeMCU setup

Open `iot_weather_station_v6.ino` and change TWO lines:

```cpp
const char* SERVER_URL = "http://YOUR_SERVER_IP:8000/data";
const char* API_KEY    = "vu-iot-2026";
```

If server is your laptop at 192.168.1.50:
```cpp
const char* SERVER_URL = "http://192.168.1.50:8000/data";
```

Upload sketch → done.

---

## Dashboard features

- Live readings (auto-refresh every 5 seconds)
- Temperature + Humidity chart (1h / 6h / 24h / 7d)
- Atmospheric pressure chart
- Moisture risk chart
- Today's stats (min/max/avg)
- Last 7 days stats
- Server connection status

---

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Dashboard (browser) |
| `GET /api/latest` | Most recent reading (JSON) |
| `GET /api/history?hours=24&limit=500` | History (JSON array) |
| `GET /api/stats` | Today + 7-day stats (JSON) |
| `POST /data` | Receive from NodeMCU (JSON body) |

---

## Change the API key (recommended)

In `server.py`, line 17:
```python
API_KEY = os.getenv("IOT_API_KEY", "vu-iot-2026")
```

Run with a custom key:
```bash
IOT_API_KEY=my-secret-key uvicorn server:app --host 0.0.0.0 --port 8000
```

Then update `iot_weather_station_v6.ino` to match:
```cpp
const char* API_KEY = "my-secret-key";
```
