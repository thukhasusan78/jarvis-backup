#include "EmotionEngine.h"
#include "DisplayManager.h"
#include "NetworkManager.h" // အချိန်နှင့် Alarm variables များ ယူရန်
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

#define TOUCH_PIN 10 

Adafruit_MPU6050 mpu;
unsigned long lastActionTime = 0;
bool isIdle = true; 

void initEmotionEngine() {
  pinMode(TOUCH_PIN, INPUT_PULLUP); 
  if (!mpu.begin(0x68, &Wire)) {
    Serial.println(F("[Local AI] MPU6050 failed to start!"));
  } else {
    Serial.println(F("[Local AI] MPU6050 Ready!"));
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  }
}

void updateEmotionEngine() {
  static int lastSensorState = 0;
  if (isAlarmRinging) {
    setActivityRoutine(20); 
    isIdle = false;
    lastSensorState = 0;       // Alarm ကြောင့် isIdle false ဖြစ်သွားကြောင်း သတ်မှတ်ရန်
    lastActionTime = millis(); // နှိုးစက်ပိတ်သွားချိန်တွင် အချိန်ဆက်တွက်နိုင်ရန် အမြဲ Update လုပ်ထားမည်
    return;
  }

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  float totalAccel = abs(a.acceleration.x) + abs(a.acceleration.y) + abs(a.acceleration.z) - 9.8;
  bool isTouched = (digitalRead(TOUCH_PIN) == LOW);
  unsigned long currentTime = millis();

  if (totalAccel > 5.0) { 
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
    // အရုပ် လှုပ်ရှားမှုပြီး၍ ငြိမ်သွားပါက
    if (!isIdle) {
      // (၁) လှုပ်ရမ်းခံရပြီး (Dizzy ပြီး) ပါက ချက်ချင်း စိတ်တိုသော မျက်လုံး (ANGRY) သို့ ပြောင်းမည်
      if (lastSensorState == 2 && (currentTime - lastActionTime > 3000)) {
        Serial.println(F("[Local AI] Stop Shaking -> ANGRY"));
        setEyeAngry(); 
        lastSensorState = 3; // Angry State သို့ ပြောင်းမည်
        lastActionTime = currentTime;
      }
      // (၂) ဒေါသထွက်တာ၊ ထိတွေ့ခံရတာ အချိန်ပြည့်သွားလျှင် (သို့) နှိုးစက်ပိတ်သွားပြီးနောက် ပုံမှန်ပြန်ဖြစ်မည်
      else if ((lastSensorState == 3 && currentTime - lastActionTime > 5000) || 
               (lastSensorState == 1 && currentTime - lastActionTime > 3000) ||
               (lastSensorState == 0 && currentTime - lastActionTime > 500)) {
        Serial.println(F("[Local AI] Idle -> Returning to Daily Schedule"));
        isIdle = true;
        lastSensorState = 0;
        lastActionTime = currentTime; 
      }
    } 
    
    // --- 🕰️ နေ့စဉ်ဘဝ အချိန်ဇယားစနစ် (Daily Routine Schedule Logic) ---
    else if (isIdle) {
      int hour, minute, second;
      if (getMyanmarTime(hour, minute, second)) {
        
        // ည ၁၀ နာရီကျော်လျှင်မူ တစ်ညလုံး အိပ်နေမည် (အချိန်မရွေး)
        if (hour >= 22 || hour < 6) {
            setEyeSleepy();        
        } 
        // နေ့လည်ပိုင်း Routine များကို မိနစ် ၀ ကနေ ၉ မိနစ်အတွင်း (ပထမ ၁၀ မိနစ်စာ) သာ ပြသမည်
        else if (minute < 10) {
            if (hour == 7) {
              setActivityRoutine(21); // မနက် ၇ နာရီ (7:00 - 7:09): သွားတိုက်မယ်
            } else if (hour == 8) {
              setActivityRoutine(22); // မနက် ၈ နာရီ (8:00 - 8:09): မနက်စာ
            } else if (hour >= 9 && hour < 12) {
              setActivityRoutine(23); // (9:00-9:09, 10:00-10:09...): ကွန်ပျူတာသုံးမည်
            } else if (hour == 12 || hour == 13) {
              setActivityRoutine(22); // နေ့လည်စာ
            } else if (hour >= 17 && hour < 18) {
              setActivityRoutine(24); // Gym ဆော့မည်
            } else if (hour >= 19 && hour < 21) {
              setActivityRoutine(25); // TV ကြည့်မည်
            } else {
              setEyeNeutral();       
            }
        } 
        // ⏰ ၁၀ မိနစ်ကျော်သွားပါက ပုံမှန် မျက်လုံး (Neutral) သို့ အလိုအလျောက် ပြန်ရောက်မည်
        else {
            setEyeNeutral();
        }
        
      } else {
        // WiFi မချိတ်ရသေးပါက ပုံမှန်မျက်လုံးပြမည်
        setEyeNeutral();
      }
    }
  }
}