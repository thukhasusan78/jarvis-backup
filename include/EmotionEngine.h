#ifndef EMOTION_ENGINE_H
#define EMOTION_ENGINE_H

#include <Arduino.h>

// Sensor များကို စတင်မည့် Function
void initEmotionEngine();

// Sensor Data ဖတ်ပြီး Emotion 18 မျိုးကို အလိုအလျောက် ပြောင်းလဲပေးမည့် Function
void updateEmotionEngine();

#endif