#include "NetworkManager.h"
#include <WiFi.h>
#include <WebSocketsClient.h>
#include "DisplayManager.h" // မျက်လုံးကို လှမ်းထိန်းချုပ်ရန် ထည့်သွင်းခြင်း

const char* ssid = "Wokwi-GUEST"; 
const char* password = "";

// ဤနေရာတွင် မင်းရဲ့ VPS IP ကို ပြန်ထည့်ပေးပါ
const char* ws_host = "103.47.227.135"; 
const int ws_port = 8081; 
const char* ws_path = "/ws/emo";

WebSocketsClient webSocket;

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
      
      // ဆာဗာမှ ဝင်လာသော JSON ကို ဖတ်ခြင်း
      StaticJsonDocument<200> doc;
      DeserializationError error = deserializeJson(doc, payload);
      
      if (!error) {
        const char* anim = doc["animation"];
        if (anim) {
          // Animation နာမည်ပေါ်မူတည်၍ မျက်လုံး ပြောင်းလဲပေးခြင်း
          if (strcmp(anim, "HAPPY") == 0) {
             setEyeHappy();
          } else if (strcmp(anim, "ANGRY") == 0) {
             setEyeAngry();
          } else {
             setEyeNeutral();
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

  webSocket.begin(ws_host, ws_port, ws_path);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000); 
}

void updateNetwork() {
  webSocket.loop(); 
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