// ─────────────────────────────────────────────────────────────
// IoT Weather Station v7 — Pushing the hardware to its limit
// New in v7:
//   1. Altitude reading + Zambretti-style pressure trend forecast
//   2. OTA wireless firmware updates (no USB cable needed)
//   3. Sparkline mini-graph of temperature history on Screen 1
//   4. Automatic night dimming / screen-off using NTP clock
// ─────────────────────────────────────────────────────────────

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <ESP8266mDNS.h>      // required by ArduinoOTA for network discovery
#include <ArduinoOTA.h>       // ← NEW: wireless firmware updates
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_AHTX0.h>
#include <Adafruit_BMP280.h>
#include <time.h>

// ── WiFi ──────────────────────────────────────────────────────
const char* WIFI_SSID = "Phu Chu Tich";
const char* WIFI_PASS = "quetm@QRdeketnoi";

// ── Server config ─────────────────────────────────────────────
const char* SERVER_URL = "http://192.168.1.7:8000/data";
// const char* SERVER_URL = "https://iot-weather-station-0mea.onrender.com/data";
const char* API_KEY    = "vu-iot-2026";

// ── OTA config ───────────────────────────────────────────────
const char* OTA_HOSTNAME = "iot-weather-station"; // shows up in Arduino IDE "Network Ports"
const char* OTA_PASSWORD = "24442221";          // change this to your own password

// ── NTP ───────────────────────────────────────────────────────
#define NTP_SERVER1  "pool.ntp.org"
#define NTP_SERVER2  "time.nist.gov"
#define UTC_OFFSET_S 25200   // UTC+7 Vietnam

// ── Local altitude reference ────────────────────────────────────
// Sea-level pressure used for altitude calculation. 1013.25 hPa is the
// global standard; using local QNH from a weather station near you
// gives a more accurate altitude reading if you know it.
#define SEALEVEL_HPA 1013.25

// ── OLED ──────────────────────────────────────────────────────
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT  64
#define OLED_ADDRESS  0x3C
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// ── Sensors ───────────────────────────────────────────────────
Adafruit_AHTX0 aht;
Adafruit_BMP280 bmp;

// ── State ─────────────────────────────────────────────────────
bool ahtOK = false, bmpOK = false, oledOK = false;
bool timesynced = false;
float temp_val = NAN, hum_val = NAN, press_val = NAN, alt_val = NAN;

int currentScreen = 0;
const int TOTAL_SCREENS  = 6;          // ← was 5, now 6 (added Forecast screen)
const unsigned long SCREEN_INTERVAL = 4000;
unsigned long lastScreenChange = 0;

const unsigned long NTP_REFRESH_MS  = 10UL * 60UL * 1000UL;
const unsigned long SEND_INTERVAL   = 5000UL;
unsigned long lastNtpSync  = 0;
unsigned long lastSend     = 0;

// POST result tracking for display
bool  lastPostOK    = false;
unsigned long lastPostTime = 0;
int   postCount     = 0;
int   postFail      = 0;

// ─────────────────────────────────────────────────────────────
// FEATURE 1 — Pressure history ring buffer for Zambretti forecast
// ─────────────────────────────────────────────────────────────
// We sample pressure every PRESSURE_SAMPLE_MS and keep the last
// PRESSURE_HISTORY_SIZE samples, covering a 3-hour rolling window.
// 3 hours / 15 min per sample = 12 samples.
#define PRESSURE_HISTORY_SIZE 12
const unsigned long PRESSURE_SAMPLE_MS = 15UL * 60UL * 1000UL; // 15 min
float pressureHistory[PRESSURE_HISTORY_SIZE];
int   pressureHistoryCount = 0;     // how many slots are filled so far
int   pressureHistoryIdx   = 0;     // next write position (ring buffer)
unsigned long lastPressureSample = 0;

// Forecast text + trend arrow, refreshed whenever we have enough history
String forecastText  = "Collecting data...";
String trendArrow     = "-";
float  pressureTrendHpa = 0; // hPa change over the 3h window (negative = falling)

// ─────────────────────────────────────────────────────────────
// FEATURE 3 — Sparkline temperature history (one column per pixel)
// ─────────────────────────────────────────────────────────────
// Stored as int8_t = (temp_C * 2), range -64..63 maps to -32.0..31.5°C
// which comfortably covers Vietnam's climate while saving RAM
// (128 bytes total instead of 512 for a float array).
#define SPARK_WIDTH 128
int8_t sparkBuffer[SPARK_WIDTH];
int    sparkCount = 0;     // how many columns have real data so far
int    sparkIdx   = 0;     // next write index (ring buffer)
const unsigned long SPARK_SAMPLE_MS = 60UL * 1000UL; // 1 sample per minute → ~2h view
unsigned long lastSparkSample = 0;

// ─────────────────────────────────────────────────────────────
// FEATURE 4 — Night dimming state
// ─────────────────────────────────────────────────────────────
bool screenAsleep = false;
const int NIGHT_START_HOUR = 23; // 11 PM
const int NIGHT_END_HOUR   = 6;  // 6 AM

// ── NTP ───────────────────────────────────────────────────────
void syncNTP() {
  if (WiFi.status() != WL_CONNECTED) return;
  configTime(UTC_OFFSET_S, 0, NTP_SERVER1, NTP_SERVER2);
  time_t now = 0; int retries = 0;
  while (now < 100000 && retries < 10) { delay(500); now = time(nullptr); retries++; }
  if (now > 100000) { timesynced = true; }
  lastNtpSync = millis();
}

// ── Physics ───────────────────────────────────────────────────
float dewPoint(float t, float rh) {
  float g = (17.27 * t) / (237.3 + t) + log(rh / 100.0);
  return (237.3 * g) / (17.27 - g);
}
float absHumidity(float t, float rh) {
  return (6.112 * exp(17.67 * t / (t + 243.5)) * rh * 2.1674) / (273.15 + t);
}
int moistureRisk(float t, float rh) {
  if (isnan(t) || isnan(rh)) return -1;
  float dpd = t - dewPoint(t, rh);
  float ah  = absHumidity(t, rh);
  if (dpd < 2.0)               return 5;
  if (dpd < 4.0 || ah > 22.0)  return 4;
  if (dpd < 6.0 || ah > 18.0)  return 3;
  if (dpd < 10.0 || rh > 80.0) return 2;
  if (rh > 60.0)                return 1;
  return 0;
}
const char* riskLabel(int r) {
  switch(r){case 5:return"CONDENSATION";case 4:return"VERY HIGH";case 3:return"HIGH";
            case 2:return"MODERATE";case 1:return"NORMAL";case 0:return"DRY/GOOD";}
  return "NO DATA";
}

// ── Helpers ───────────────────────────────────────────────────
String zp(int n){ return (n<10?"0":"")+String(n); }
const char* dowVN[]={"CN","T2","T3","T4","T5","T6","T7"};

// ─────────────────────────────────────────────────────────────
// FEATURE 1 — Zambretti-style pressure trend forecast
// ─────────────────────────────────────────────────────────────
// Records one pressure sample every 15 minutes into a 12-slot ring
// buffer (3-hour window), then compares oldest vs newest sample to
// classify the trend. This is the same principle barometers have
// used for over a century: pressure FALLING = storm/rain approaching,
// pressure RISING = clearing skies, STABLE = no significant change.
void samplePressureHistory() {
  if (isnan(press_val)) return;
  unsigned long now = millis();
  if (now - lastPressureSample < PRESSURE_SAMPLE_MS && pressureHistoryCount > 0) return;
  lastPressureSample = now;

  pressureHistory[pressureHistoryIdx] = press_val;
  pressureHistoryIdx = (pressureHistoryIdx + 1) % PRESSURE_HISTORY_SIZE;
  if (pressureHistoryCount < PRESSURE_HISTORY_SIZE) pressureHistoryCount++;

  updateForecast();
}

void updateForecast() {
  if (pressureHistoryCount < 2) {
    forecastText = "Collecting data...";
    trendArrow = "-";
    return;
  }

  // Oldest sample = the slot right after the current write pointer
  // (since it's a ring buffer, that's the next one to be overwritten)
  int oldestIdx = (pressureHistoryCount < PRESSURE_HISTORY_SIZE)
                    ? 0
                    : pressureHistoryIdx; // when full, write pointer = oldest
  float oldest = pressureHistory[oldestIdx];
  // Newest sample = the one just written (one step back from write pointer)
  int newestIdx = (pressureHistoryIdx - 1 + PRESSURE_HISTORY_SIZE) % PRESSURE_HISTORY_SIZE;
  float newest = pressureHistory[newestIdx];

  pressureTrendHpa = newest - oldest;

  // Classic Zambretti-style thresholds, tuned for a 3-hour window:
  //  > +1.6 hPa  → rising fast  → clearing skies
  //  > +0.5 hPa  → rising slow  → improving
  //  -0.5..+0.5  → steady       → no change
  //  < -0.5 hPa  → falling slow → clouding over, rain possible
  //  < -1.6 hPa  → falling fast → rain/storm likely soon
  if (pressureTrendHpa <= -1.6) {
    forecastText = "Rain likely soon";
    trendArrow = "FALL FAST";
  } else if (pressureTrendHpa <= -0.5) {
    forecastText = "Clouding over";
    trendArrow = "FALLING";
  } else if (pressureTrendHpa < 0.5) {
    forecastText = "No change";
    trendArrow = "STEADY";
  } else if (pressureTrendHpa < 1.6) {
    forecastText = "Improving";
    trendArrow = "RISING";
  } else {
    forecastText = "Clear skies ahead";
    trendArrow = "RISE FAST";
  }
}

// ─────────────────────────────────────────────────────────────
// FEATURE 3 — Sparkline sampling
// ─────────────────────────────────────────────────────────────
void sampleSparkline() {
  if (isnan(temp_val)) return;
  unsigned long now = millis();
  if (now - lastSparkSample < SPARK_SAMPLE_MS && sparkCount > 0) return;
  lastSparkSample = now;

  // Clamp to int8_t range before storing (±31.5°C is generous for Vietnam)
  float clamped = constrain(temp_val, -32.0, 31.5);
  sparkBuffer[sparkIdx] = (int8_t)round(clamped * 2.0);
  sparkIdx = (sparkIdx + 1) % SPARK_WIDTH;
  if (sparkCount < SPARK_WIDTH) sparkCount++;
}

// Draws the sparkline into a rectangle (x,y,w,h) on the OLED.
// Auto-scales vertically based on min/max in the buffer so small
// fluctuations are still visible.
void drawSparkline(int x, int y, int w, int h) {
  if (sparkCount < 2) return;

  // Find min/max across valid samples for auto-scaling
  float minT = 1000, maxT = -1000;
  int n = sparkCount;
  for (int i = 0; i < n; i++) {
    int idx = (sparkIdx - n + i + SPARK_WIDTH) % SPARK_WIDTH;
    float v = sparkBuffer[idx] / 2.0;
    if (v < minT) minT = v;
    if (v > maxT) maxT = v;
  }
  float range = maxT - minT;
  if (range < 1.0) range = 1.0; // avoid flat-line division by zero

  int prevPx = -1, prevPy = -1;
  for (int i = 0; i < n; i++) {
    int idx = (sparkIdx - n + i + SPARK_WIDTH) % SPARK_WIDTH;
    float v = sparkBuffer[idx] / 2.0;
    int px = x + (int)((float)i / (SPARK_WIDTH - 1) * w);
    int py = y + h - (int)((v - minT) / range * h);
    if (prevPx >= 0) display.drawLine(prevPx, prevPy, px, py, SSD1306_WHITE);
    prevPx = px; prevPy = py;
  }
}

// ─────────────────────────────────────────────────────────────
// FEATURE 4 — Night dimming based on NTP clock
// ─────────────────────────────────────────────────────────────
void updateNightMode() {
  if (!oledOK || !timesynced) return;

  time_t now = time(nullptr);
  struct tm* t = localtime(&now);
  int h = t->tm_hour;

  bool isNight = (NIGHT_START_HOUR > NIGHT_END_HOUR)
                   ? (h >= NIGHT_START_HOUR || h < NIGHT_END_HOUR)   // wraps midnight
                   : (h >= NIGHT_START_HOUR && h < NIGHT_END_HOUR);

  if (isNight && !screenAsleep) {
    display.ssd1306_command(SSD1306_DISPLAYOFF);
    screenAsleep = true;
    Serial.println("[NIGHT] Screen OFF (23:00–06:00 power saving)");
  } else if (!isNight && screenAsleep) {
    display.ssd1306_command(SSD1306_DISPLAYON);
    screenAsleep = false;
    Serial.println("[DAY] Screen ON");
  }
}

// ── HTTP POST to server ───────────────────────────────────────
void postData() {
  if (WiFi.status() != WL_CONNECTED) { postFail++; lastPostOK=false; return; }

  float dp  = (!isnan(temp_val)&&!isnan(hum_val)) ? dewPoint(temp_val,hum_val)   : NAN;
  float ah  = (!isnan(temp_val)&&!isnan(hum_val)) ? absHumidity(temp_val,hum_val): NAN;
  int   r   = moistureRisk(temp_val, hum_val);

  String body = "{";
  body += "\"api_key\":\"" + String(API_KEY) + "\"";
  if (!isnan(temp_val))  body += ",\"temp\":"     + String(temp_val, 2);
  if (!isnan(hum_val))   body += ",\"humidity\":"  + String(hum_val, 2);
  if (!isnan(press_val)) body += ",\"pressure\":"  + String(press_val, 2);
  if (!isnan(alt_val))   body += ",\"altitude\":"  + String(alt_val, 1);
  if (!isnan(dp))        body += ",\"dew_point\":" + String(dp, 2);
  if (!isnan(ah))        body += ",\"abs_hum\":"   + String(ah, 2);
  if (r >= 0)            body += ",\"risk\":"      + String(r);
  body += "}";

  WiFiClient client;
  HTTPClient http;
  http.begin(client, SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(4000);

  int code = http.POST(body);
  lastPostOK = (code == 200);
  if (lastPostOK) postCount++; else postFail++;
  lastPostTime = millis();

  Serial.printf("[POST] %d | T=%.1f H=%.1f P=%.0f Alt=%.1f Td=%.1f AH=%.1f Risk=%d\n",
    code, isnan(temp_val)?-999:temp_val, isnan(hum_val)?-999:hum_val,
    isnan(press_val)?-999:press_val, isnan(alt_val)?-999:alt_val,
    isnan(dp)?-999:dp, isnan(ah)?-999:ah, r);

  http.end();
}

// ── Read sensors ──────────────────────────────────────────────
void readSensors() {
  if (ahtOK) {
    sensors_event_t humidity, temp;
    aht.getEvent(&humidity, &temp);
    temp_val = temp.temperature;
    hum_val  = humidity.relative_humidity;
  }
  if (bmpOK) {
    float raw = bmp.readPressure();
    press_val = (raw > 1.0f) ? raw / 100.0f : NAN;
    // ── FEATURE 1: Altitude ──
    // readAltitude() takes sea-level pressure in hPa and derives height
    // from the measured pressure using the barometric formula.
    alt_val = bmp.readAltitude(SEALEVEL_HPA);
  }
  samplePressureHistory();
  sampleSparkline();
}

// ── OLED screens ─────────────────────────────────────────────
void drawScreen1() {
  display.clearDisplay();
  display.fillRect(0,0,128,10,SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK); display.setTextSize(1);
  display.setCursor(8,1); display.print("IOT WEATHER STATION");
  display.setTextColor(SSD1306_WHITE);
  display.drawLine(0,11,127,11,SSD1306_WHITE);
  display.setCursor(0,14); display.print("TEMP");
  display.setTextSize(2); display.setCursor(0,24);
  if(!isnan(temp_val)){display.print(temp_val,1);display.print("C");}
  else display.print("--.-C");
  display.setTextSize(1);

  // ── FEATURE 3: Sparkline replaces the old plain divider line ──
  // Drawn in the strip between y=44 and y=54 (10px tall, full width)
  display.setCursor(96, 36); display.print("trend");
  drawSparkline(0, 44, 128, 10);
  display.drawLine(0,54,127,54,SSD1306_WHITE);

  display.setCursor(0,57); display.print("H:");
  if(!isnan(hum_val)){display.print(hum_val,0);display.print("%");}
  else display.print("--%");
  display.setCursor(50,57); display.print("P:");
  if(!isnan(press_val)){display.print(press_val,0);}
  else display.print("----");
  display.display();
}

void drawScreen2() {
  display.clearDisplay();
  display.drawRect(0,0,128,64,SSD1306_WHITE);
  display.setTextSize(1); display.setCursor(30,4); display.print("TEMPERATURE");
  display.drawLine(1,13,126,13,SSD1306_WHITE);
  display.setTextSize(4);
  String ts=isnan(temp_val)?"--.-":String(temp_val,1);
  int tw=ts.length()*24;
  display.setCursor(max(0,(128-tw-12)/2),16); display.print(ts);
  display.setTextSize(2); display.print("C");
  display.setTextSize(1);
  display.drawLine(1,52,126,52,SSD1306_WHITE);
  display.setCursor(4,56); display.print("Hum:");
  if(!isnan(hum_val)) display.print(hum_val,1);
  display.print("%  P:");
  if(!isnan(press_val)) display.print(press_val,0);
  display.display();
}

void drawScreen3() {
  display.clearDisplay();
  display.fillRect(0,0,128,10,SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK); display.setTextSize(1);
  display.setCursor(16,1); display.print("MOISTURE RISK");
  display.setTextColor(SSD1306_WHITE);
  if(isnan(temp_val)||isnan(hum_val)){
    display.setCursor(20,28); display.print("No sensor data");
    display.display(); return;
  }
  float td=dewPoint(temp_val,hum_val);
  float dpd=temp_val-td;
  float ah=absHumidity(temp_val,hum_val);
  int r=moistureRisk(temp_val,hum_val);
  display.setCursor(0,13); display.print("Dew pt: "); display.print(td,1); display.print("C");
  display.setCursor(0,23); display.print("DPD   : "); display.print(dpd,1); display.print("C");
  display.setCursor(0,33); display.print("Abs H : "); display.print(ah,1); display.print("g/m3");
  display.drawLine(0,43,127,43,SSD1306_WHITE);
  const char* label=riskLabel(r);
  int lw=strlen(label)*6;
  display.setCursor((128-lw)/2,47); display.print(label);
  display.drawRect(0,57,128,7,SSD1306_WHITE);
  if(r>=0) display.fillRect(1,58,(int)(126.0*r/5.0),5,SSD1306_WHITE);
  for(int i=1;i<=4;i++) display.drawLine(1+126*i/5,56,1+126*i/5,64,SSD1306_WHITE);
  display.display();
}

// Draw WiFi signal bars at (x,y). bars: 0-4 filled bars out of 4.
void drawSignalBars(int x, int y, int bars) {
  int barW = 3, gap = 1;
  int heights[4] = {3, 6, 9, 12};
  for (int i = 0; i < 4; i++) {
    int bx = x + i * (barW + gap);
    int bh = heights[i];
    int by = y + (12 - bh);
    if (i < bars) display.fillRect(bx, by, barW, bh, SSD1306_WHITE);
    else display.drawRect(bx, by, barW, bh, SSD1306_WHITE);
  }
}
int rssiToBars(long rssi) {
  if (rssi >= -55) return 4;
  if (rssi >= -65) return 3;
  if (rssi >= -75) return 2;
  if (rssi >= -85) return 1;
  return 0;
}

void drawScreen4() {
  display.clearDisplay();
  display.fillRect(0,0,128,10,SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK); display.setTextSize(1);
  display.setCursor(16,1); display.print("SERVER STATUS");
  display.setTextColor(SSD1306_WHITE);

  display.setCursor(0,13);
  display.print("WiFi: ");
  display.print(WiFi.status()==WL_CONNECTED ? "OK" : "FAIL");
  if (WiFi.status()==WL_CONNECTED) {
    int bars = rssiToBars(WiFi.RSSI());
    drawSignalBars(108, 12, bars);
  }

  display.setCursor(0,23);
  display.print("Server: ");
  display.print(lastPostOK ? "OK" : "FAIL");

  display.setCursor(0,33);
  display.print("Sent:"); display.print(postCount);
  display.setCursor(64,33);
  display.print("Fail:"); display.print(postFail);

  display.drawLine(0,44,127,44,SSD1306_WHITE);

  display.setCursor(0,48);
  if(WiFi.status()==WL_CONNECTED) display.print(WiFi.localIP().toString());
  else display.print("Not connected");

  display.setCursor(0,57);
  if(lastPostTime>0){
    unsigned long ago=(millis()-lastPostTime)/1000;
    display.print("Last post: "); display.print(ago); display.print("s ago");
  } else {
    display.print("No post yet");
  }
  display.display();
}

void drawScreen5() {
  display.clearDisplay();
  display.fillRect(0,0,128,10,SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK); display.setTextSize(1);
  display.setCursor(34,1); display.print("DATE & TIME");
  display.setTextColor(SSD1306_WHITE);
  if(!timesynced){
    display.setCursor(8,18); display.print("Waiting for NTP...");
    display.setCursor(0,54);
    display.print(WiFi.status()==WL_CONNECTED?"WiFi: connected":"WiFi: offline");
    display.display(); return;
  }
  time_t now=time(nullptr);
  struct tm* t=localtime(&now);
  String timeStr=zp(t->tm_hour)+(t->tm_sec%2==0 ? ":" : " ")+zp(t->tm_min)
              +(t->tm_sec%2==0 ? ":" : " ")+zp(t->tm_sec);
  display.setTextSize(2);
  int tw=timeStr.length()*12;
  display.setCursor((128-tw)/2,14); display.print(timeStr);
  display.drawLine(0,36,127,36,SSD1306_WHITE);
  display.setTextSize(1);
  String dateStr=String(dowVN[t->tm_wday])+"  "
    +zp(t->tm_mday)+"/"+zp(t->tm_mon+1)+"/"+String(t->tm_year+1900);
  int dw=dateStr.length()*6;
  display.setCursor((128-dw)/2,40); display.print(dateStr);
  display.setCursor(0,54);
  unsigned long secs=(millis()-lastNtpSync)/1000UL;
  display.print("NTP sync "); display.print(secs/60); display.print("m ago");
  display.display();
}

// ── FEATURE 1 — Screen 6: Altitude + Forecast ─────────────────
void drawScreen6() {
  display.clearDisplay();
  display.fillRect(0,0,128,10,SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK); display.setTextSize(1);
  display.setCursor(10,1); display.print("ALTITUDE & FORECAST");
  display.setTextColor(SSD1306_WHITE);

  // Altitude
  display.setCursor(0,13);
  display.print("Altitude: ");
  if (!isnan(alt_val)) { display.print(alt_val,1); display.print("m"); }
  else display.print("--- m");

  // Pressure trend over 3h
  display.setCursor(0,23);
  display.print("3h trend: ");
  if (pressureHistoryCount >= 2) {
    if (pressureTrendHpa >= 0) display.print("+");
    display.print(pressureTrendHpa,1);
    display.print("hPa");
  } else {
    display.print("--");
  }

  display.drawLine(0,34,127,34,SSD1306_WHITE);

  // Forecast — big and centered
  display.setTextSize(1);
  display.setCursor(2,40);
  display.print("Forecast:");

  display.setTextSize(1);
  int fw = forecastText.length() * 6;
  display.setCursor(max(0,(128-fw)/2), 52);
  display.print(forecastText);

  // Trend indicator bar (visual direction of pressure change)
  display.drawRect(0,57,128,7,SSD1306_WHITE);
  // Map -3..+3 hPa trend onto a 0..126 bar with center = no change
  float clampedTrend = constrain(pressureTrendHpa, -3.0, 3.0);
  int barCenter = 64;
  int barLen = (int)(clampedTrend / 3.0 * 63);
  if (barLen >= 0) display.fillRect(barCenter, 58, barLen, 5, SSD1306_WHITE);
  else display.fillRect(barCenter + barLen, 58, -barLen, 5, SSD1306_WHITE);
  display.drawLine(barCenter,56,barCenter,64,SSD1306_WHITE); // center marker

  display.display();
}

void updateDisplay() {
  if(!oledOK || screenAsleep) return;   // ← skip drawing while sleeping (Feature 4)
  unsigned long now=millis();
  if(now-lastScreenChange>=SCREEN_INTERVAL){
    currentScreen=(currentScreen+1)%TOTAL_SCREENS;
    lastScreenChange=now;
  }
  switch(currentScreen){
    case 0: drawScreen1(); break;
    case 1: drawScreen2(); break;
    case 2: drawScreen3(); break;
    case 3: drawScreen4(); break;
    case 4: drawScreen5(); break;
    case 5: drawScreen6(); break;   // ← new altitude/forecast screen
  }
}

// ── FEATURE 2 — OTA setup ──────────────────────────────────────
void setupOTA() {
  ArduinoOTA.setHostname(OTA_HOSTNAME);
  ArduinoOTA.setPassword(OTA_PASSWORD);

  ArduinoOTA.onStart([]() {
    Serial.println("[OTA] Update starting...");
    if (oledOK) {
      display.ssd1306_command(SSD1306_DISPLAYON); // wake screen during update
      display.clearDisplay();
      display.setTextSize(1);
      display.setCursor(0,0);
      display.print("OTA UPDATE");
      display.setCursor(0,16);
      display.print("Uploading...");
      display.display();
    }
  });

  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    int pct = (progress * 100) / total;
    Serial.printf("[OTA] Progress: %u%%\n", pct);
    if (oledOK) {
      display.fillRect(0, 30, 128, 12, SSD1306_BLACK);
      display.drawRect(0, 30, 128, 10, SSD1306_WHITE);
      display.fillRect(2, 32, (int)(124.0 * pct / 100.0), 6, SSD1306_WHITE);
      display.setCursor(0, 44);
      display.fillRect(0, 44, 128, 10, SSD1306_BLACK);
      display.print(pct); display.print("%");
      display.display();
    }
  });

  ArduinoOTA.onEnd([]() {
    Serial.println("\n[OTA] Update complete — rebooting");
    if (oledOK) {
      display.clearDisplay();
      display.setCursor(20,28);
      display.print("Rebooting...");
      display.display();
    }
  });

  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("[OTA] Error[%u]\n", error);
    if (oledOK) {
      display.clearDisplay();
      display.setCursor(0,28);
      display.print("OTA FAILED");
      display.display();
    }
  });

  ArduinoOTA.begin();
  Serial.println("[OTA] Ready — hostname: " + String(OTA_HOSTNAME));
  Serial.println("[OTA] In Arduino IDE: Tools > Port > Network Ports");
}

// ── Setup ─────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n\n=== IoT Weather Station v7 — Hardware unleashed ===");

  Wire.begin(4, 5);

  oledOK = display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS);
  Serial.println(oledOK ? "[OK]   OLED ready" : "[WARN] OLED not found");

  ahtOK = aht.begin();
  Serial.println(ahtOK ? "[OK]   AHT20 ready" : "[WARN] AHT20 not found");

  bmpOK = bmp.begin(0x76);
  if(!bmpOK) bmpOK = bmp.begin(0x77);
  Serial.println(bmpOK ? "[OK]   BMP280 ready" : "[WARN] BMP280 not found");

  if(bmpOK){
    // bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
    //                 Adafruit_BMP280::SAMPLING_X2,
    //                 Adafruit_BMP280::SAMPLING_X16,
    //                 Adafruit_BMP280::FILTER_X16,
    //                 Adafruit_BMP280::STANDBY_MS_500);
  }

  // Init sparkline buffer to a neutral value to avoid garbage on first draw
  for (int i = 0; i < SPARK_WIDTH; i++) sparkBuffer[i] = 0;

  if(oledOK){
    display.clearDisplay(); display.setTextSize(1);
    display.fillRect(0,0,128,10,SSD1306_WHITE);
    display.setTextColor(SSD1306_BLACK);
    display.setCursor(8,1); display.print("IOT WEATHER STATION");
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0,14); display.print("AHT20 : "); display.println(ahtOK?"OK":"NOT FOUND");
    display.setCursor(0,24); display.print("BMP280: "); display.println(bmpOK?"OK":"NOT FOUND");
    display.drawLine(0,35,127,35,SSD1306_WHITE);
    display.setCursor(0,40); display.print("Connecting WiFi...");
    display.display();
  }

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int attempts=0;
  while(WiFi.status()!=WL_CONNECTED && attempts<30){
    delay(500); Serial.print("."); attempts++;
  }

  if(WiFi.status()==WL_CONNECTED){
    Serial.println("\n[OK]   WiFi: "+WiFi.localIP().toString());
    syncNTP();
    setupOTA();   // ← FEATURE 2: start OTA listener once WiFi is up
    if(oledOK){
      display.clearDisplay(); display.setTextSize(1);
      display.setCursor(0,0); display.print("WiFi OK");
      display.setCursor(0,12); display.print(WiFi.localIP().toString());
      display.setCursor(0,24); display.print("OTA: "); display.print(OTA_HOSTNAME);
      display.setCursor(0,36); display.print("Server:");
      display.setCursor(0,46); display.print(SERVER_URL);
      display.display();
      delay(2000);
    }
  } else {
    Serial.println("\n[WARN] WiFi failed");
  }

  lastScreenChange=millis();
  lastSend=millis();
  lastPressureSample=millis();
  lastSparkSample=millis();
  readSensors();
}

// ── Loop ──────────────────────────────────────────────────────
void loop() {
  ArduinoOTA.handle();   // ← FEATURE 2: must be called every loop, non-blocking

  unsigned long now=millis();

  if(now-lastSend>=SEND_INTERVAL){
    lastSend=now;
    readSensors();
    postData();
  }

  if(now-lastNtpSync>=NTP_REFRESH_MS) syncNTP();

  updateNightMode();   // ← FEATURE 4: check every loop, cheap (just an hour compare)
  updateDisplay();
}
