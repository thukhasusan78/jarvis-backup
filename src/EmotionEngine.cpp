#include "EmotionEngine.h"
#include "DisplayManager.h"
#include "NetworkManager.h" 
#include "MicrophoneManager.h" 
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
    lastSensorState = 0;       
    lastActionTime = millis(); 
    return;
  }

  unsigned long currentTime = millis();

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  float totalAccel = abs(a.acceleration.x) + abs(a.acceleration.y) + abs(a.acceleration.z) - 9.8;
  
  // Touch Sensor ကို ဖတ်မည် (လက်နှင့်ထိလျှင် HIGH ဖြစ်မည်ဟု ယူဆပါသည်)
  bool isTouched = (digitalRead(TOUCH_PIN) == HIGH); 

  // =================================================================
  // 🎤 Push-to-Talk (Walkie-Talkie ပုံစံ အသံဖမ်းစနစ်)
  // =================================================================
  static bool isRecording = false;

  if (isTouched) {
      if (!isRecording) {
          Serial.println(F("[Mic] Touch detected. Listening..."));
          sendCommand("start_record"); 
          setEyeCurious(); // စကားနားထောင်နေကြောင်း သိသာရန် မျက်လုံးပြောင်းမည်
          isRecording = true;
          isMicRecording = true;
          isIdle = false;
      }
      lastActionTime = currentTime;
      return; // အသံဖမ်းနေစဉ် အခြားအမူအရာများ ဝင်မနှောင့်ယှက်စေရန် (ဒီကနေပဲ အလုပ်လုပ်မည်)
  } else {
      if (isRecording) {
          Serial.println(F("[Mic] Touch released. Processing audio..."));
          isMicRecording = false;
          sendCommand("stop_record"); 
          isRecording = false;
          
          setEyeThinking(); // Gemini ဆီက အဖြေကို စောင့်နေစဉ် စဉ်းစားနေသည့် မျက်လုံးပြမည်
          isIdle = false;
          lastSensorState = 4; // စဉ်းစားနေသည့် State အဖြစ် မှတ်သားမည်
          lastActionTime = currentTime;
          return; 
      }
  }
  // =================================================================

  // အောက်ပိုင်းသည် ကျန်သည့် Sensor (Shaking နှင့် Routine) များဖြစ်သည်
  if (totalAccel > 5.0) { 
    if (lastSensorState != 2 || (currentTime - lastActionTime > 2000)) {
      Serial.println(F("[Local AI] Shaking! -> DIZZY"));
      setEyeDizzy(); 
      lastActionTime = currentTime;
      isIdle = false;
      lastSensorState = 2;
    }
  } 
  else { 
    // အရုပ် ငြိမ်သွားပြီးနောက် အမူအရာ ပြောင်းလဲခြင်းများ
    if (!isIdle) {
      if (lastSensorState == 2 && (currentTime - lastActionTime > 3000)) {
        Serial.println(F("[Local AI] Stop Shaking -> ANGRY"));
        setEyeAngry(); 
        lastSensorState = 3; 
        lastActionTime = currentTime;
      }
      else if ((lastSensorState == 3 && currentTime - lastActionTime > 5000) || 
               (lastSensorState == 4 && currentTime - lastActionTime > 4000) || // AI စဉ်းစားချိန် ၄ စက္ကန့်ခန့် ပြပြီးနောက် ပုံမှန်ပြန်ဖြစ်မည်
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
        if (hour >= 22 || hour < 6) {
            setEyeSleepy();        
        } 
        else if (minute < 10) {
            if (hour == 7) setActivityRoutine(21); 
            else if (hour == 8) setActivityRoutine(22); 
            else if (hour >= 9 && hour < 12) setActivityRoutine(23); 
            else if (hour == 12 || hour == 13) setActivityRoutine(22); 
            else if (hour >= 17 && hour < 18) setActivityRoutine(24); 
            else if (hour >= 19 && hour < 21) setActivityRoutine(25); 
            else setEyeNeutral();       
        } 
        else {
            setEyeNeutral();
        }
      } else {
        setEyeNeutral();
      }
    }
  }
}