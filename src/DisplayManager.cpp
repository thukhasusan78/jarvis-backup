#include "DisplayManager.h"
#include <U8g2lib.h>
#include <Wire.h>

// ---------------------------------------------------------
// 1. မျက်နှာပြင် ကြေညာခြင်း (1.3 inch OLED - SH1106 အတွက်)
// ---------------------------------------------------------
// သတိပြုရန်: မိမိအသုံးပြုသော I2C Pin များသည် S3 DevKitC တွင် SDA=8, SCL=9 ဖြစ်ပါက 
// Wire.begin(8, 9); ဟု initDisplay() တွင် ပြင်ပေးရန် လိုအပ်ပါသည်။
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);

// ---------------------------------------------------------
// 2. မျက်လုံး Object ကြေညာခြင်း 
// ---------------------------------------------------------
// esp32-eyes library ၏ အဓိကလုပ်ဆောင်မည့် ကိန်းရှင် (Variable) ဖြစ်သည်။
// Library ထဲတွင် Emotion များကို 0 မှ 17 အထိ (သို့) Enum ဖြင့် ကြေညာထားလေ့ရှိသည်။
int currentEmotion = 0; // 0 = Neutral အဖြစ် ပုံသေထားပါမည်။

// မျက်နှာပြင် စတင်သည့် Function
void initDisplay() {
    // I2C လမ်းကြောင်းကို စတင်ခြင်း (ESP32-S3 Default Pin များအတွက်)
    Wire.begin(); 
    
    // U8g2 မျက်နှာပြင်ကို အသက်သွင်းခြင်း
    u8g2.begin();
    u8g2.clearBuffer();
    
    // (esp32-eyes ၏ init function လိုအပ်ပါက ဤနေရာတွင် ထည့်ပါမည်)
    
    // ပထမဆုံးအကြိမ် အနေဖြင့် ပုံမှန်မျက်နှာ (Neutral) ကို ပြသထားမည်
    setEyeNeutral();
}

// မျက်လုံးများ အမြဲတမ်း အသက်ဝင်နေစေရန် (Loop ထဲတွင် အမြဲပတ်နေမည့် Function)
void updateDisplay() {
    u8g2.clearBuffer();
    
    // ဤနေရာတွင် esp32-eyes မှ မျက်လုံးပုံဆွဲမည့် (draw) function ကို ခေါ်ပါမည်။
    // ဥပမာ - eyes.draw(u8g2, currentEmotion); 
    // လောလောဆယ် U8g2 ဖြင့် စမ်းသပ်ထားသော စာသားကို ယာယီထည့်ထားပါမည်။
    u8g2.setFont(u8g2_font_ncenB08_tr);
    u8g2.setCursor(10, 30);
    u8g2.print("Emotion ID: ");
    u8g2.print(currentEmotion);
    
    u8g2.sendBuffer();
}

// =========================================================
// 3. AI ဦးနှောက်မှ လှမ်းခိုင်းမည့် Emotion Functions (၁၈) မျိုး
// =========================================================
// မှတ်ချက် - Library ၏ Enum နာမည်များအတိုင်း သတ်မှတ်ထားခြင်း ဖြစ်သည်။

void setEyeNeutral() {
    currentEmotion = 0;
}

void setEyeHappy() {
    currentEmotion = 1;
}

void setEyeSad() {
    currentEmotion = 2;
}

void setEyeAngry() {
    currentEmotion = 3;
}

void setEyeAmused() {
    currentEmotion = 4;
}

void setEyeBored() {
    currentEmotion = 5;
}

void setEyeConfident() {
    currentEmotion = 6;
}

void setEyeConfused() {
    currentEmotion = 7;
}

void setEyeCurious() {
    currentEmotion = 8;
}

void setEyeDizzy() {
    currentEmotion = 9;
}

void setEyeExcited() {
    currentEmotion = 10;
}

void setEyeFrustrated() {
    currentEmotion = 11;
}

void setEyeLaughing() {
    currentEmotion = 12;
}

void setEyePleading() {
    currentEmotion = 13;
}

void setEyeScared() {
    currentEmotion = 14;
}

void setEyeSleepy() {
    currentEmotion = 15;
}

void setEyeThinking() {
    currentEmotion = 16;
}

void setEyeUpset() {
    currentEmotion = 17;
}