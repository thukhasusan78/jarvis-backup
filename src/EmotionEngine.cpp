#include "EmotionEngine.h"
#include "DisplayManager.h"
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

#define TOUCH_PIN 10 // Diagram အရ Pin 10 တွင် ချိတ်ထားပါသည်

Adafruit_MPU6050 mpu;

// AI ဆုံးဖြတ်ချက်အတွက် အချိန်မှတ်စနစ်
unsigned long lastActionTime = 0;
bool isIdle = true; 

void initEmotionEngine() {
  pinMode(TOUCH_PIN, INPUT_PULLUP); // Touch pin ကို ဖွင့်ပါမည်

  // main.cpp တွင် Wire.begin(8, 9) ဖွင့်ထားပြီးဖြစ်၍ &Wire ကိုသာ ယူသုံးပါမည်
  if (!mpu.begin(0x68, &Wire)) {
    Serial.println(F("[Local AI] MPU6050 failed to start!"));
  } else {
    Serial.println(F("[Local AI] MPU6050 Ready!"));
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  }
}

void updateEmotionEngine() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // ၁။ MPU6050 လှုပ်ရှားမှုကို တွက်ချက်ခြင်း (Acceleration)
  float totalAccel = abs(a.acceleration.x) + abs(a.acceleration.y) + abs(a.acceleration.z) - 9.8;
  
  // ၂။ Touch Sensor ဖတ်ခြင်း
  bool isTouched = (digitalRead(TOUCH_PIN) == LOW);

  unsigned long currentTime = millis();

  // ==========================================
  // Local AI Decision Logic (0 Latency)
  // ==========================================

  if (totalAccel > 5.0) { // အကြမ်းပတမ်း လှုပ်ခံရလျှင် (တန်ဖိုး ၅ ကျော်လျှင်)
    if (isIdle || (currentTime - lastActionTime > 3000)) {
      Serial.println(F("[Local AI] Shaking! -> DIZZY"));
      setEyeDizzy(); // ခေါင်းမူးသွားပါမည်
      lastActionTime = currentTime;
      isIdle = false;
    }
  } 
  else if (isTouched) { // ခေါင်းကို ပွတ်လျှင် / ခလုတ်နှိပ်လျှင်
    if (isIdle || (currentTime - lastActionTime > 3000)) {
      Serial.println(F("[Local AI] Touched! -> HAPPY"));
      setEyeHappy(); // ပြုံးပါမည်
      lastActionTime = currentTime;
      isIdle = false;
    }
  } 
  else { // ဘာမှမလုပ်ဘဲ ၅ စက္ကန့် ကြာသွားလျှင်
    if (!isIdle && (currentTime - lastActionTime > 5000)) {
      Serial.println(F("[Local AI] Idle -> NEUTRAL"));
      setEyeNeutral(); // ပုံမှန် မျက်လုံး ပြန်ဖြစ်ပါမည်
      isIdle = true;
    }
  }
}