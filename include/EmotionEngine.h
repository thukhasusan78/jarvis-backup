#ifndef EMOTION_ENGINE_H
#define EMOTION_ENGINE_H

#include <Arduino.h>

// Jarvis ရဲ့ လက်ရှိ စိတ်ခံစားချက် အခြေအနေတွေကို သတ်မှတ်ခြင်း
enum MoodState {
  MOOD_NEUTRAL, // ပုံမှန်
  MOOD_HAPPY,   // ပျော်နေသည်
  MOOD_ANGRY    // ဒေါသထွက်/လန့်သွားသည်
};

// Sensor များကို စတင်မည့် Function
void initEmotionEngine();

// Russell's Model ဖြင့် စိတ်ခံစားချက်ကို အမြဲတွက်ချက်နေမည့် Function
void updateEmotionEngine();

// တွက်ချက်ပြီးသား စိတ်ခံစားချက်ကို ပြန်တောင်းယူမည့် Function
MoodState getCurrentMood();

#endif