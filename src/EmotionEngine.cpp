#include "EmotionEngine.h"
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

#define TOUCH_PIN 10 // Touch Sensor ချိတ်ထားသော Pin

Adafruit_MPU6050 mpu;

// Emotion Engine Variables
float valence = 0.0;
float arousal = 0.0;
MoodState currentMood = MOOD_NEUTRAL;

void initEmotionEngine() {
  pinMode(TOUCH_PIN, INPUT_PULLUP); // Touch pin ကို ဖွင့်ပါမည်

  // MPU6050 Sensor ကို စတင်ပါမည် (I2C လမ်းကြောင်းက main.cpp မှာ ဖွင့်ထားပြီးသားကို ယူသုံးမည်)
  if (!mpu.begin(0x68, &Wire)) {
    Serial.println(F("MPU6050 failed to start!"));
  } else {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  }
}

void updateEmotionEngine() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // ၁။ လှုပ်ရှားမှုကို တွက်ချက်ခြင်း (Arousal)
  float totalAccel = abs(a.acceleration.x) + abs(a.acceleration.y) + abs(a.acceleration.z) - 9.8;
  if (totalAccel > 5.0) { 
    arousal += 2.0; 
    valence -= 1.0; 
  }

  // ၂။ ထိတွေ့မှုကို ဖတ်ခြင်း (Valence)
  if (digitalRead(TOUCH_PIN) == LOW) {
    valence += 1.5; 
    arousal -= 0.5; 
  }

  // ၃။ စိတ်ခံစားချက် တဖြည်းဖြည်း ပြန်ငြိမ်သွားစေရန် (Decay)
  valence *= 0.95; 
  arousal *= 0.95;

  // ကန့်သတ်ချက် (-10 မှ 10 အတွင်း)
  valence = constrain(valence, -10.0, 10.0);
  arousal = constrain(arousal, -10.0, 10.0);

  // ၄။ တွက်ချက်ထားသော တန်ဖိုးများပေါ်မူတည်၍ Mood သတ်မှတ်ခြင်း
  if (valence > 4.0) {
    currentMood = MOOD_HAPPY;
  } else if (arousal > 6.0 && valence < -2.0) {
    currentMood = MOOD_ANGRY;
  } else {
    currentMood = MOOD_NEUTRAL;
  }
}

MoodState getCurrentMood() {
  return currentMood; // လက်ရှိ Mood ကို လှမ်းတောင်းရင် ပြန်ပို့ပေးပါမည်
}