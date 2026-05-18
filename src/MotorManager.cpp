#include "MotorManager.h"

// ---------------------------------------------------------
// ESP32 Native LEDC (Hardware PWM) Setting များ
// ---------------------------------------------------------
const int freq = 50;           // Servo Standard Frequency (50Hz)
const int resolution = 12;     // 12-bit Resolution (0 မှ 4095 အထိ)

// PWM Channel သတ်မှတ်ခြင်း (မော်တာ ၄ လုံးအတွက် 0, 1, 2, 3)
const int CH_LL = 0; 
const int CH_RL = 1;
const int CH_LF = 2;
const int CH_RF = 3;

// 0 မှ 180 ဒီဂရီကို ESP32 နားလည်သော လျှပ်စစ်လှိုင်း (Duty Cycle) သို့ ပြောင်းပေးမည့် Function
void setMotorAngle(int channel, int angle) {
    // 500us မှ 2400us ကို 12-bit သို့ တွက်ချက်ထားခြင်း (102 မှ 491)
    int duty = map(angle, 0, 180, 102, 491); 
    ledcWrite(channel, duty);
}

void initMotors() {
  // Library မလိုတော့ဘဲ ESP32 ၏ Hardware ပိုင်းကို တိုက်ရိုက် အသက်သွင်းခြင်း
  ledcSetup(CH_LL, freq, resolution);
  ledcAttachPin(4, CH_LL);

  ledcSetup(CH_RL, freq, resolution);
  ledcAttachPin(5, CH_RL);

  ledcSetup(CH_LF, freq, resolution);
  ledcAttachPin(6, CH_LF);

  ledcSetup(CH_RF, freq, resolution);
  ledcAttachPin(7, CH_RF);

  // စတင်စတင်ချင်း မတ်တပ်ရပ်အနေအထား (၉၀ ဒီဂရီ) တွင် ထားမည်
  setMotorAngle(CH_LL, 90);
  setMotorAngle(CH_RL, 90);
  setMotorAngle(CH_LF, 90);
  setMotorAngle(CH_RF, 90);
  
  Serial.println("[Motor] Native Hardware PWM Ready! (No External Library Needed)");
}

void updateMotors(int emotionId) {
  unsigned long t = millis();
  
  int ll = 90, rl = 90, lf = 90, rf = 90; 

  // Emotion အလိုက် တွက်ချက်ခြင်း (ယခင်အတိုင်း)
  switch(emotionId) {
    case 0:  
    case 16: 
      ll = 90 + sin(t / 200.0) * 30;
      rl = 90 - sin(t / 200.0) * 30;
      break;

    case 1:  
    case 10: 
    case 12: 
      lf = 90 + sin(t / 150.0) * 45; 
      rf = 90 - sin(t / 150.0) * 45;
      ll = 90 + sin(t / 150.0) * 30;
      rl = 90 - sin(t / 150.0) * 30;
      break;

    case 9:  
      ll = 90 + sin(t / 300.0) * 40;
      rl = 90 + cos(t / 250.0) * 40;
      lf = 90 + sin(t / 400.0) * 30;
      rf = 90 - cos(t / 350.0) * 30;
      break;

    case 5:  
      lf = 90 + sin(t / 800.0) * 30;
      rf = 90 + sin(t / 800.0) * 30; 
      break;

    case 14: 
      ll = 90 + sin(t / 20.0) * 10;
      rl = 90 - sin(t / 20.0) * 10;
      lf = 90 + cos(t / 20.0) * 10;
      rf = 90 - cos(t / 20.0) * 10;
      break;

    case 15: 
      ll = 130 + sin(t / 1000.0) * 5;
      rl = 50 - sin(t / 1000.0) * 5;
      break;

    case 3:  
    case 6:  
    case 11: 
      ll = 50; rl = 130; 
      lf = 90 + sin(t / 100.0) * 15; 
      rf = 90 - sin(t / 100.0) * 15;
      break;

    case 7:  
    case 8:  
      ll = 70; rl = 70; 
      lf = 130; rf = 90; 
      break;

    default: 
      ll = 90 + sin(t / 400.0) * 10;
      rl = 90 - sin(t / 400.0) * 10;
      break;
  }

  // Simulator ကို မလိုအပ်ဘဲ အလုပ်မရှုပ်စေရန်၊ ပြောင်းလဲသွားမှသာ အမိန့်ပေးမည်
  static int last_ll = -1, last_rl = -1, last_lf = -1, last_rf = -1;

  if (ll != last_ll) { setMotorAngle(CH_LL, ll); last_ll = ll; }
  if (rl != last_rl) { setMotorAngle(CH_RL, rl); last_rl = rl; }
  if (lf != last_lf) { setMotorAngle(CH_LF, lf); last_lf = lf; }
  if (rf != last_rf) { setMotorAngle(CH_RF, rf); last_rf = rf; }
  
  // Debugging
  static unsigned long lastPrint = 0;
  if (t - lastPrint > 1000) { 
      Serial.printf("[Motor] Emotion ID: %d | Left Leg Angle: %d\n", emotionId, ll);
      lastPrint = t;
  }
}