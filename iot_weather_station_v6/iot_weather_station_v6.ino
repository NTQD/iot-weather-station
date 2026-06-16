// ─────────────────────────────────────────────────────────────
// IoT Weather Station v6 — Self-hosted platform (no Blynk)
// Sends data via HTTP POST to your own server every 5 seconds.
// ─────────────────────────────────────────────────────────────

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
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
// If server is on your laptop on the same WiFi:  http://192.168.1.x:8000/data
// If server is on a VPS:                         http://your-domain.com:8000/data
const char* SERVER_URL = "http://192.168.1.12:8000/data";
const char* API_KEY    = "vu-iot-2026";           // must match server.py IOT_API_KEY

// ── NTP ───────────────────────────────────────────────────────
#define NTP_SERVER1  "pool.ntp.org"
#define NTP_SERVER2  "time.nist.gov"
#define UTC_OFFSET_S 25200   // UTC+7 Vietnam

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
float temp_val = NAN, hum_val = NAN, press_val = NAN;

int currentScreen = 0;
const int TOTAL_SCREENS  = 5;
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

// ── HTTP POST to server ───────────────────────────────────────
void postData() {
  if (WiFi.status() != WL_CONNECTED) { postFail++; lastPostOK=false; return; }

  float dp  = (!isnan(temp_val)&&!isnan(hum_val)) ? dewPoint(temp_val,hum_val)   : NAN;
  float ah  = (!isnan(temp_val)&&!isnan(hum_val)) ? absHumidity(temp_val,hum_val): NAN;
  int   r   = moistureRisk(temp_val, hum_val);

  // Build JSON manually — saves ~10KB vs ArduinoJson
  String body = "{";
  body += "\"api_key\":\"" + String(API_KEY) + "\"";
  if (!isnan(temp_val))  body += ",\"temp\":"     + String(temp_val, 2);
  if (!isnan(hum_val))   body += ",\"humidity\":"  + String(hum_val, 2);
  if (!isnan(press_val)) body += ",\"pressure\":"  + String(press_val, 2);
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

  Serial.printf("[POST] %d | T=%.1f H=%.1f P=%.0f Td=%.1f AH=%.1f Risk=%d\n",
    code, isnan(temp_val)?-999:temp_val, isnan(hum_val)?-999:hum_val,
    isnan(press_val)?-999:press_val, isnan(dp)?-999:dp, isnan(ah)?-999:ah, r);

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
  }
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
  display.drawLine(0,44,127,44,SSD1306_WHITE);
  display.setCursor(0,48); display.print("Hum:");
  if(!isnan(hum_val)){display.print(hum_val,1);display.print("%");}
  else display.print("--.-% ");
  display.setCursor(72,48); display.print("P:");
  if(!isnan(press_val)){display.print(press_val,0);display.print("hPa");}
  else display.print("----hPa");
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

void drawScreen4() {
  display.clearDisplay();
  display.fillRect(0,0,128,10,SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK); display.setTextSize(1);
  display.setCursor(16,1); display.print("SERVER STATUS");
  display.setTextColor(SSD1306_WHITE);

  // WiFi
  display.setCursor(0,13);
  display.print("WiFi: ");
  display.print(WiFi.status()==WL_CONNECTED ? "OK  " : "FAIL");
  if(WiFi.status()==WL_CONNECTED){
    display.print(WiFi.RSSI()); display.print("dB");
  }

  // Server
  display.setCursor(0,23);
  display.print("Server: ");
  display.print(lastPostOK ? "OK" : "FAIL");

  // Counters
  display.setCursor(0,33);
  display.print("Sent:"); display.print(postCount);
  display.setCursor(64,33);
  display.print("Fail:"); display.print(postFail);

  display.drawLine(0,44,127,44,SSD1306_WHITE);

  // IP
  display.setCursor(0,48);
  if(WiFi.status()==WL_CONNECTED) display.print(WiFi.localIP().toString());
  else display.print("Not connected");

  // Last post age
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
  String timeStr=zp(t->tm_hour)+(t->tm_sec%2==0?":":"  ")+zp(t->tm_min)
                +(t->tm_sec%2==0?":":"  ")+zp(t->tm_sec);
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

void updateDisplay() {
  if(!oledOK) return;
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
  }
}

// ── Setup ─────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n\n=== IoT Weather Station v6 — Self-hosted ===");

  Wire.begin(4, 5);

  oledOK = display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS);
  Serial.println(oledOK ? "[OK]   OLED ready" : "[WARN] OLED not found");

  ahtOK = aht.begin();
  Serial.println(ahtOK ? "[OK]   AHT20 ready" : "[WARN] AHT20 not found");

  bmpOK = bmp.begin(0x76);
  if(!bmpOK) bmpOK = bmp.begin(0x77);
  Serial.println(bmpOK ? "[OK]   BMP280 ready" : "[WARN] BMP280 not found");

  if(bmpOK){
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                    Adafruit_BMP280::SAMPLING_X2,
                    Adafruit_BMP280::SAMPLING_X16,
                    Adafruit_BMP280::FILTER_X16,
                    Adafruit_BMP280::STANDBY_MS_500);
  }

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
    if(oledOK){
      display.clearDisplay(); display.setTextSize(1);
      display.setCursor(0,0); display.print("WiFi OK");
      display.setCursor(0,12); display.print(WiFi.localIP().toString());
      display.setCursor(0,24); display.print("Server:");
      display.setCursor(0,34); display.print(SERVER_URL);
      display.display();
      delay(2000);
    }
  } else {
    Serial.println("\n[WARN] WiFi failed");
  }

  lastScreenChange=millis();
  lastSend=millis();
  readSensors();
}

// ── Loop ──────────────────────────────────────────────────────
void loop() {
  unsigned long now=millis();

  // Read + send every SEND_INTERVAL
  if(now-lastSend>=SEND_INTERVAL){
    lastSend=now;
    readSensors();
    postData();
  }

  // NTP refresh every 10 min
  if(now-lastNtpSync>=NTP_REFRESH_MS) syncNTP();

  updateDisplay();
}
