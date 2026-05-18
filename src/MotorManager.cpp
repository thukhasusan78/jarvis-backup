#include "MotorManager.h"
#include <ESP32Servo.h>

Servo leftLeg;   // ဘယ် ခြေထောက် (Pin 4)
Servo rightLeg;  // ညာ ခြေထောက် (Pin 5)
Servo leftFoot;  // ဘယ် ခြေဖဝါး (Pin 6)
Servo rightFoot; // ညာ ခြေဖဝါး (Pin 7)

void initMotors() {
  // FreeRTOS နှင့် ESP32Servo အလုပ်တွဲလုပ်နိုင်ရန်
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  // မော်တာများအတွက် Standard Frequency (50Hz) ကို မဖြစ်မနေ သတ်မှတ်ပေးရပါမည်
  leftLeg.setPeriodHertz(50);
  rightLeg.setPeriodHertz(50);
  leftFoot.setPeriodHertz(50);
  rightFoot.setPeriodHertz(50);

  // မော်တာ ၄ လုံးကို သတ်မှတ်ထားသော Pin များတွင် တပ်ဆင်ခြင်း
  leftLeg.attach(4, 500, 2400);
  rightLeg.attach(5, 500, 2400);
  leftFoot.attach(6, 500, 2400);
  rightFoot.attach(7, 500, 2400);

  // စတင်စတင်ချင်း မတ်တပ်ရပ်အနေအထား (၉၀ ဒီဂရီ) တွင် ထားမည်
  leftLeg.write(90);
  rightLeg.write(90);
  leftFoot.write(90);
  rightFoot.write(90);
}

void updateMotors(int emotionId) {
  unsigned long t = millis();
  
  // Base Angle များ (၉၀ သည် ပုံမှန် မတ်တပ်ရပ်လျက်)
  int ll = 90, rl = 90, lf = 90, rf = 90; 

  switch(emotionId) {
    case 0:  // Neutral (ပုံမှန် - အသက်ရှူသကဲ့သို့ ညင်သာစွာ လှုပ်မည်)
    case 16: // Thinking
      ll = 90 + sin(t / 500.0) * 5;
      rl = 90 - sin(t / 500.0) * 5;
      break;

    case 1:  // Happy (ပျော်ရွှင် - ခုန်ပေါက်နေမည်)
    case 10: // Excited
    case 12: // Laughing
      lf = 90 + sin(t / 150.0) * 15; // ခြေဖဝါးများ မြန်မြန်လှုပ်မည်
      rf = 90 - sin(t / 150.0) * 15;
      ll = 90 + sin(t / 150.0) * 10;
      rl = 90 - sin(t / 150.0) * 10;
      break;

    case 9:  // Dizzy (မူးဝေသော - ကမောက်ကမ ယိုင်ထိုးနေမည်)
      ll = 90 + sin(t / 300.0) * 20;
      rl = 90 + cos(t / 250.0) * 20;
      lf = 90 + sin(t / 400.0) * 15;
      rf = 90 - cos(t / 350.0) * 15;
      break;

    case 5:  // Bored (ပျင်းရိသော - ဘယ်ညာ နှေးကွေးစွာ ယိမ်းနွဲ့မည်)
      lf = 90 + sin(t / 800.0) * 15;
      rf = 90 + sin(t / 800.0) * 15; 
      break;

    case 14: // Scared (ကြောက်ရွံ့သော - တုန်ယင်နေမည်)
      ll = 90 + sin(t / 20.0) * 3;
      rl = 90 - sin(t / 20.0) * 3;
      lf = 90 + cos(t / 20.0) * 3;
      rf = 90 - cos(t / 20.0) * 3;
      break;

    case 15: // Sleepy (အိပ်ချင်သော - အောက်သို့ ကျုံ့ကျသွားမည်)
      ll = 110 + sin(t / 1000.0) * 2;
      rl = 70 - sin(t / 1000.0) * 2;
      break;

    case 3:  // Angry (ဒေါသထွက် - မာထန်ထန် ရပ်နေမည်)
    case 6:  // Confident
    case 11: // Frustrated
      ll = 70; rl = 110; // ရင်ကော့ထားသော အနေအထား
      lf = 90 + sin(t / 100.0) * 5; // ဒေါသဖြင့် ခြေဆောင့်သလို တုန်မည်
      rf = 90 - sin(t / 100.0) * 5;
      break;

    case 7:  // Confused (ဇဝေဇဝါ - ခြေတစ်ဖက် မြှောက်ထားမည်)
    case 8:  // Curious
      ll = 80; rl = 80; 
      lf = 110; rf = 90; // ခေါင်းစောင်းကြည့်သလို ခြေဖဝါးတစ်ဖက် စောင်းမည်
      break;

    default: // အခြားအရာများအတွက် ပုံမှန်
      ll = 90 + sin(t / 400.0) * 3;
      rl = 90 - sin(t / 400.0) * 3;
      break;
  }

  // တွက်ချက်ရရှိသော ဒီဂရီများကို မော်တာများဆီသို့ တကယ် ပို့လွှတ်ခြင်း
  leftLeg.write(ll);
  rightLeg.write(rl);
  leftFoot.write(lf);
  rightFoot.write(rf);
}