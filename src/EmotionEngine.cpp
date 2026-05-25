#include "EmotionEngine.h"
#include "DisplayManager.h"
#include "NetworkManager.h" 
#include "MicrophoneManager.h" // 👈 မိုက်အတွက် အသစ်
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

  // 👈 currentTime error ပျောက်သွားရန် ဤနေရာတွင် ပြန်ထည့်ထားပါသည်
  unsigned long currentTime = millis();

  // --- 🎤 Auto-Record Timer (Touch မလိုဘဲ ၅ စက္ကန့် အသံဖမ်းစမ်းသပ်ရန်) ---
  static bool hasRecorded = false;     
  static bool isRecordingTest = false; 
  static unsigned long recordStartTime = 0;

  if (currentTime > 5000 && !hasRecorded) {
      if (!isRecordingTest) {
          Serial.println(F("[Mic] Auto-Recording Started... Speak now!"));
          sendCommand("start_record"); 
          setEyeCurious();             
          isRecordingTest = true;
          recordStartTime = currentTime;
          isIdle = false;
      }
      recordAndSendAudio(); 
      if (currentTime - recordStartTime > 5000) {
          Serial.println(F("[Mic] Recording Stopped."));
          sendCommand("stop_record"); 
          isRecordingTest = false;
          hasRecorded = true;         
          isIdle = true;
          lastActionTime = currentTime;
          lastSensorState = 0;
      }
      return; // အသံဖမ်းနေစဉ် အခြားဆင်ဆာများ ဝင်မရှုပ်စေရန်
  }
  // ------------------------------------------------------------------

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  float totalAccel = abs(a.acceleration.x) + abs(a.acceleration.y) + abs(a.acceleration.z) - 9.8;
  bool isTouched = (digitalRead(TOUCH_PIN) == LOW); // 👈 Touch ကုဒ်အဟောင်း ယခင်အတိုင်း ရှိနေပါသည်

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
      if (lastSensorState == 2 && (currentTime - lastActionTime > 3000)) {
        Serial.println(F("[Local AI] Stop Shaking -> ANGRY"));
        setEyeAngry(); 
        lastSensorState = 3; 
        lastActionTime = currentTime;
      }
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