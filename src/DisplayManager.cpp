#include "DisplayManager.h"
#include <U8g2lib.h>
#include <Wire.h>

// ---------------------------------------------------------
// 1. မျက်နှာပြင် ကြေညာခြင်း (1.3 inch OLED - SH1106 အတွက်)
// ---------------------------------------------------------
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);

int currentEmotion = 0; // 0 = Neutral အဖြစ် ပုံသေထားပါမည်။

void initDisplay() {
    Wire.begin(); 
    u8g2.begin();
    u8g2.clearBuffer();
    setEyeNeutral();
}

void updateDisplay() {
    u8g2.clearBuffer();
    
    // ----------------------------------------------------
    // ၁။ မျက်လုံး အခြေခံ အရွယ်အစားနှင့် နေရာ (Base Size)
    // ----------------------------------------------------
    int w = 30;         // မျက်လုံး အကျယ်
    int h = 46;         // မျက်လုံး အမြင့်
    int lx = 25;        // ဘယ်မျက်လုံး နေရာ
    int rx = 73;        // ညာမျက်လုံး နေရာ
    int y = 10;         // အပေါ်မှ အကွာအဝေး

    // ----------------------------------------------------
    // ၂။ Emotion အလိုက် မျက်လုံး အရွယ်အစား ပြောင်းလဲခြင်း
    // ----------------------------------------------------
    if (currentEmotion == 8) { // Curious (စပ်စုချင်သော - မျက်လုံးများ နီးကပ်သွားမည်)
        lx += 8; rx -= 8; w += 2;
    } 
    else if (currentEmotion == 9) { // Dizzy (မူးဝေသော - မျက်လုံး သေးသေးလေးဖြစ်သွားမည်)
        w = 16; h = 16; y = 24; lx += 7; rx += 7;
    } 
    else if (currentEmotion == 10) { // Excited (စိတ်လှုပ်ရှားသော - မျက်လုံး ပြူးကျယ်သွားမည်)
        h = 52; y = 6;
    } 
    else if (currentEmotion == 14) { // Scared (ကြောက်ရွံ့သော - မျက်လုံးသေးသွားပြီး အောက်ရောက်သွားမည်)
        w = 20; h = 24; y = 30; lx += 5; rx += 5;
    } 
    else if (currentEmotion == 16) { // Thinking (စဉ်းစားနေသော - ညာဘက်အပေါ်သို့ ဝေ့ကြည့်မည်)
        lx += 12; rx += 12; y = 4;
    }

    // ----------------------------------------------------
    // ၃။ အလိုအလျောက် မျက်တောင်ခတ်ခြင်း (Auto-Blinker)
    // ----------------------------------------------------
    static unsigned long lastBlink = 0;
    static bool isBlinking = false;
    
    // ၄ စက္ကန့်ပြည့်တိုင်း မျက်တောင်ခတ်မည်
    if (millis() - lastBlink > 4000) { 
        isBlinking = true;
        lastBlink = millis();
    }
    // ၁၅၀ မီလီစက္ကန့် ကြာလျှင် မျက်လုံးပြန်ဖွင့်မည်
    if (isBlinking && millis() - lastBlink > 150) { 
        isBlinking = false;
    }

    // ----------------------------------------------------
    // ၄။ မျက်လုံး ပုံဖော်ခြင်း (Procedural Generation)
    // ----------------------------------------------------
    if (isBlinking) {
        // မျက်တောင်ခတ်နေစဉ် (မျဉ်းပြားလေးသာ ပေါ်မည်)
        u8g2.drawBox(lx, y + h/2, w, 6);
        u8g2.drawBox(rx, y + h/2, w, 6);
    } else {
        // အခြေခံ မျက်လုံးအဝိုင်းလေးများ အရင်ဆွဲမည်
        u8g2.drawRBox(lx, y, w, h, 8);
        u8g2.drawRBox(rx, y, w, h, 8);

        // ခဲဖျက် (အမည်းရောင်) ဖြင့် Emotion အလိုက် ပုံသွင်းမည်
        u8g2.setDrawColor(0); 
        
        switch(currentEmotion) {
            case 1:  // Happy
            case 12: // Laughing (ပိုကျယ်သော အပြုံး)
                // အောက်ခြေကို တြိဂံပုံ ဖျက်၍ ပြုံးနေအောင် လုပ်မည်
                u8g2.drawTriangle(lx-5, y+h+5, lx+w+5, y+h+5, lx+w/2, y+h-(currentEmotion==12? 25:15));
                u8g2.drawTriangle(rx-5, y+h+5, rx+w+5, y+h+5, rx+w/2, y+h-(currentEmotion==12? 25:15));
                break;
                
            case 2:  // Sad
            case 13: // Pleading
            case 17: // Upset
                // အပြင်ဘက် ထောင့်များကို ဖျက်၍ ဝမ်းနည်းသော မျက်ခုံး လုပ်မည်
                u8g2.drawTriangle(lx-5, y-5, lx+w, y-5, lx, y+15);
                u8g2.drawTriangle(rx, y-5, rx+w+5, y-5, rx+w, y+15);
                break;
                
            case 3:  // Angry
            case 6:  // Confident
            case 11: // Frustrated
                // အတွင်းဘက် ထောင့်များကို ဖျက်၍ ဒေါသထွက်သော မျက်ခုံး လုပ်မည်
                u8g2.drawTriangle(lx, y-5, lx+w+5, y-5, lx+w+5, y+20);
                u8g2.drawTriangle(rx-5, y-5, rx+w, y-5, rx-5, y+20);
                if (currentEmotion == 6) { 
                    // Confident ဆိုလျှင် အောက်ခြေပါ နည်းနည်းပြုံးမည်
                    u8g2.drawTriangle(lx-5, y+h+5, lx+w+5, y+h+5, lx+w/2, y+h-10);
                    u8g2.drawTriangle(rx-5, y+h+5, rx+w+5, y+h+5, rx+w/2, y+h-10);
                }
                if (currentEmotion == 11) {
                    // Frustrated ဆိုလျှင် မျက်လုံးပြားသွားမည် (အောက်ကို ဖြတ်မည်)
                    u8g2.drawBox(0, y+h-15, 128, 20);
                }
                break;
                
            case 4:  // Amused (သဘောကျသော)
                u8g2.drawBox(0, 0, 128, y+12); // အပေါ်မှ မျက်လုံးမှေးမည်
                u8g2.drawTriangle(lx-5, y+h+5, lx+w+5, y+h+5, lx+w/2, y+h-15);
                u8g2.drawTriangle(rx-5, y+h+5, rx+w+5, y+h+5, rx+w/2, y+h-15);
                break;
                
            case 5:  // Bored (ပျင်းရိသော)
                u8g2.drawBox(0, 0, 128, y+22); // မျက်လုံး တစ်ဝက်ပိတ်မည်
                break;
                
            case 7:  // Confused (ဇဝေဇဝါ)
                u8g2.drawBox(rx-5, 0, w+10, y+25); // ညာမျက်လုံး တစ်ဖက်တည်း မှေးမည်
                break;
                
            case 15: // Sleepy (အိပ်ချင်သော)
                u8g2.drawBox(0, 0, 128, y+32); // မျက်လုံး ၃ပုံ ၂ပုံ ပိတ်မည်
                break;
        }
        
        u8g2.setDrawColor(1); // မျက်လုံးဆွဲရန် (အဖြူရောင်) ပြန်ပြောင်းမည်
    }
    
    u8g2.sendBuffer(); // OLED ပေါ်သို့ တကယ် ပုံဖော်မည်
}

// =========================================================
// AI ဦးနှောက်မှ လှမ်းခိုင်းမည့် Emotion Functions (၁၈) မျိုး
// =========================================================

void setEyeNeutral() { currentEmotion = 0; }
void setEyeHappy() { currentEmotion = 1; }
void setEyeSad() { currentEmotion = 2; }
void setEyeAngry() { currentEmotion = 3; }
void setEyeAmused() { currentEmotion = 4; }
void setEyeBored() { currentEmotion = 5; }
void setEyeConfident() { currentEmotion = 6; }
void setEyeConfused() { currentEmotion = 7; }
void setEyeCurious() { currentEmotion = 8; }
void setEyeDizzy() { currentEmotion = 9; }
void setEyeExcited() { currentEmotion = 10; }
void setEyeFrustrated() { currentEmotion = 11; }
void setEyeLaughing() { currentEmotion = 12; }
void setEyePleading() { currentEmotion = 13; }
void setEyeScared() { currentEmotion = 14; }
void setEyeSleepy() { currentEmotion = 15; }
void setEyeThinking() { currentEmotion = 16; }
void setEyeUpset() { currentEmotion = 17; }