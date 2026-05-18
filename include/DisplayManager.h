#ifndef DISPLAY_MANAGER_H
#define DISPLAY_MANAGER_H

#include <Arduino.h>

// မျက်နှာပြင်နှင့် မျက်လုံးများကို စတင်ရန်
void initDisplay();

// မျက်လုံးများ အမြဲတမ်း အသက်ဝင်နေစေရန် (Loop တွင် ခေါ်သုံးမည်)
void updateDisplay();

// ==========================================
// AI ဦးနှောက်မှ လှမ်းခိုင်းမည့် Emotion 18 မျိုး
// ==========================================
void setEyeNeutral();     // ပုံမှန်
void setEyeHappy();       // ပျော်ရွှင်သော
void setEyeSad();         // ဝမ်းနည်းသော
void setEyeAngry();       // ဒေါသထွက်သော
void setEyeAmused();      // သဘောကျနေသော
void setEyeBored();       // ပျင်းရိနေသော
void setEyeConfident();   // ယုံကြည်မှုရှိသော
void setEyeConfused();    // ဇဝေဇဝါဖြစ်နေသော
void setEyeCurious();     // စပ်စုချင်သော/သိချင်သော
void setEyeDizzy();       // မူးဝေနေသော
void setEyeExcited();     // စိတ်လှုပ်ရှားနေသော
void setEyeFrustrated();  // စိတ်ပျက်အားငယ်သော
void setEyeLaughing();    // ရယ်မောနေသော
void setEyePleading();    // တောင်းပန်တိုးလျှိုးနေသော
void setEyeScared();      // ကြောက်ရွံ့နေသော
void setEyeSleepy();      // အိပ်ချင်နေသော
void setEyeThinking();    // စဉ်းစားနေသော
void setEyeUpset();       // စိတ်ခုနေသော

#endif