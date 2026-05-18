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
    // အခြေအနေ (က) - အခုမှ စပြီး ငြိမ်သွားခြင်း 
    // (ဘာမှမလုပ်ဘဲ ၂ စက္ကန့် ကြာလျှင် ပုံမှန် Neutral သို့ အရင်သွားမည်)
    if (!isIdle && (currentTime - lastActionTime > 2000)) {
      Serial.println(F("[Local AI] Idle -> NEUTRAL"));
      setEyeNeutral(); 
      isIdle = true;
      lastSensorState = 0;
      lastActionTime = currentTime; // ငြိမ်သွားတဲ့ အချိန်ကို စတင်မှတ်သားမည်
    } 
    // အခြေအနေ (ခ) - ငြိမ်နေတာ ကြာသွားခြင်း (Idle Personality)
    // (၇ စက္ကန့်ပြည့်တိုင်း အခြားအမူအရာတစ်ခုခုကို ကျပန်း ပြောင်းမည်)
    else if (isIdle && (currentTime - lastActionTime > 5000)) {
      int randomIdleEmotion = random(0, 5); // 0 မှ 4 အတွင်း ကျပန်းဂဏန်း (Random) ထုတ်မည်
      
      switch(randomIdleEmotion) {
        case 0: 
          setEyeNeutral(); 
          Serial.println(F("[Local AI] Idle -> NEUTRAL")); 
          break;
        case 1: 
          setEyeBored(); // ပျင်းရိသော
          Serial.println(F("[Local AI] Idle -> BORED")); 
          break;
        case 2: 
          setEyeSleepy(); // အိပ်ချင်သော
          Serial.println(F("[Local AI] Idle -> SLEEPY")); 
          break;
        case 3: 
          setEyeCurious(); // စပ်စုချင်သော
          Serial.println(F("[Local AI] Idle -> CURIOUS")); 
          break;
        case 4: 
          setEyeAmused(); // သဘောကျနေသော
          Serial.println(F("[Local AI] Idle -> AMUSED")); 
          break;
      }
      
      lastActionTime = currentTime; // ၇ စက္ကန့်ကို အစကနေ ပြန်မှတ်မည်
    }
  }
}