#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include <Arduino.h>
#include <ArduinoJson.h>

// WiFi နှင့် WebSocket ကို စတင်မည့် Function
void initNetwork();

// FreeRTOS ထဲတွင် အမြဲ Run နေပြီး Data ဝင်/ထွက် စစ်ဆေးမည့် Function
void updateNetwork();

// Server ဆီသို့ အရုပ်၏ အခြေအနေ (Arousal, Valence, Mood) ကို လှမ်းပို့မည့် Function
void sendRobotState(float valence, float arousal, const char* mood);

#endif