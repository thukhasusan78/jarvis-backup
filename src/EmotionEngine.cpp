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

  float totalAccel = abs(a.acceleration.x) + abs(a.acceleration.y) + abs(a.acceleration.z) - 9.8;
  bool isTouched = (digitalRead(TOUCH_PIN) == LOW);
  unsigned long currentTime = millis();

  // Sensor မှတ်ဉာဏ် (ယခင်လုပ်ခဲ့သော အခြေအနေကို မှတ်ထားရန်)
  static int lastSensorState = 0; // 0=Neutral, 1=Touched, 2=Shaking

  if (totalAccel > 5.0) { 
    // အရင်က Happy ဖြစ်နေရင်တောင် အကြမ်းပတမ်းလှုပ်တာကို ဦးစားပေးပြီး ချက်ချင်း ဖြတ်ဝင်မည် (Interrupt)
    if (lastSensorState != 2 || (currentTime - lastActionTime > 2000)) {
      Serial.println(F("[Local AI] Shaking! -> DIZZY"));
      setEyeDizzy(); 
      lastActionTime = currentTime;
      isIdle = false;
      lastSensorState = 2;
    }
  } 
  else if (isTouched) { 
    if (lastSensorState != 1 || (currentTime - lastActionTime > 2000)) {
      Serial.println(F("[Local AI] Touched! -> HAPPY"));
      setEyeHappy(); 
      lastActionTime = currentTime;
      isIdle = false;
      lastSensorState = 1;
    }
  } 
  else { 
    // ဘာမှမလုပ်ဘဲ ၂ စက္ကန့် (2000ms) ကြာတာနဲ့ ချက်ချင်း Neutral ပြန်ပြောင်းမည် (အရင်လို ၅ စက္ကန့် အကြာကြီး မစောင့်တော့ပါ)
    if (!isIdle && (currentTime - lastActionTime > 2000)) {
      Serial.println(F("[Local AI] Idle -> NEUTRAL"));
      setEyeNeutral(); 
      isIdle = true;
      lastSensorState = 0;
    }
  }
}