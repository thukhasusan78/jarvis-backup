#include "NetworkManager.h"
#include <WiFi.h>
#include <WebSocketsClient.h>
#include "DisplayManager.h" 
#include <time.h> // NTP အချိန်စနစ်သုံးရန်

const char* ssid = "U Myat Phone"; 
const char* password = "Gbank8028";
const char* ws_host = "103.47.227.135"; 
const int ws_port = 8081; 
const char* ws_path = "/ws/emo";

WebSocketsClient webSocket;

// Alarm Variables များကို တည်ဆောက်ခြင်း
int alarmHour = -1;
int alarmMinute = -1;
bool isAlarmSet = false;
bool isAlarmRinging = false;

// Server မှ လှမ်းสั่งသော အချိန်အတိုင်း Alarm သတ်မှတ်ခြင်း
void setLocalAlarm(int hour, int minute) {
  alarmHour = hour;
  alarmMinute = minute;
  isAlarmSet = true;
  isAlarmRinging = false;
  Serial.printf("[Alarm] Custom Alarm Set for %02d:%02d (Myanmar Time)\n", hour, minute);
}

// နှိုးစက်ပိတ်ခြင်း
void stopAlarm() {
  isAlarmRinging = false;
  isAlarmSet = false; 
  Serial.println("[Alarm] Alarm Stopped!");
}

// လက်ရှိ မြန်မာစံတော်ချိန်ကို ဖတ်ပေးမည့် Function
bool getMyanmarTime(int &hour, int &minute, int &second) {
  struct tm timeinfo;
  if(!getLocalTime(&timeinfo)){
    return false; // အချိန် Sync မရသေးပါက False ပြန်မည်
  }
  hour = timeinfo.tm_hour;
  minute = timeinfo.tm_min;
  second = timeinfo.tm_sec;
  return true;
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("[Network] Disconnected from Server!");
      break;
    case WStype_CONNECTED:
      Serial.println("[Network] Connected to Server!");
      break;
    case WStype_TEXT:
      Serial.printf("[Network] Message from Brain: %s\n", payload);
      
      StaticJsonDocument<256> doc;
      DeserializationError error = deserializeJson(doc, payload);
      
      if (!error) {
        const char* action = doc["action"];
        if (action) {
          // (က) နှိုးစက်အသစ် သတ်မှတ်ရန် Command ဝင်လာလျှင်
          if (strcmp(action, "set_alarm") == 0) {
            int h = doc["hour"];
            int m = doc["minute"];
            setLocalAlarm(h, m);
          }
          // (ခ) နှိုးစက်ပိတ်ရန် Command ဝင်လာလျှင်
          else if (strcmp(action, "stop_alarm") == 0) {
            stopAlarm();
          }
          // (ဂ) ပုံမှန် Animation ခိုင်းစေမှု
          else if (strcmp(action, "play_animation") == 0) {
            const char* anim = doc["animation"];
            if (anim) {
              if (strcmp(anim, "HAPPY") == 0) setEyeHappy();
              else if (strcmp(anim, "ANGRY") == 0) setEyeAngry();
              else setEyeNeutral();
            }
          }
        }
      }
      break;
  }
}

void initNetwork() {
  Serial.print("[Network] Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[Network] WiFi Connected!");
  Serial.print("[Network] IP Address: ");
  Serial.println(WiFi.localIP());

  // --- မြန်မာစံတော်ချိန် (UTC +6:30) သို့ NTP Sync လုပ်ခြင်း ---
  Serial.println("[Network] Syncing Myanmar Time via NTP...");
  configTime(6.5 * 3600, 0, "pool.ntp.org", "time.nist.gov"); 

  webSocket.begin(ws_host, ws_port, ws_path);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000); 
}

void updateNetwork() {
  webSocket.loop(); 

  // ၁ စက္ကန့်တိုင်း အချိန်ကို စစ်ဆေးပြီး Alarm အချိန်နှင့် ကိုက်ညီပါက နှိုးစက်အော်မည်
  if (isAlarmSet && !isAlarmRinging) {
    int h, m, s;
    if (getMyanmarTime(h, m, s)) {
      if (h == alarmHour && m == alarmMinute && s == 0) {
        isAlarmRinging = true;
        Serial.println("[Alarm] WAKE UP!! Alarm Triggered!");
      }
    }
  }
}

void sendRobotState(float valence, float arousal, const char* mood) {
  if (webSocket.isConnected()) {
    StaticJsonDocument<200> doc;
    doc["event"] = "sensor_update";
    doc["valence"] = valence;
    doc["arousal"] = arousal;
    doc["current_mood"] = mood;

    String jsonString;
    serializeJson(doc, jsonString);
    webSocket.sendTXT(jsonString);
  }
}