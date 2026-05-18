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
    // ၁။ မျက်လုံး အခြေခံ အရွယ်အစား (EMO ကဲ့သို့ စတုရန်းကျကျ ပြင်ဆင်ထားသည်)
    // ----------------------------------------------------
    int w = 36;         // မျက်လုံး အကျယ် (ပိုကျယ်လာမည်)
    int h = 36;         // မျက်လုံး အမြင့် (စတုရန်းပိုကျမည်)
    int lx = 20;        // ဘယ်မျက်လုံး နေရာ
    int rx = 72;        // ညာမျက်လုံး နေရာ
    int y = 14;         // အပေါ်မှ အကွာအဝေး

    // ----------------------------------------------------
    // ၂။ ညင်သာသော Transition (Blink-to-Transition) စနစ်
    // ----------------------------------------------------
    static int lastRenderedEmotion = 0;
    static unsigned long transitionTimer = 0;
    static bool isTransitioning = false;

    // Emotion အသစ်ပြောင်းသွားတိုင်း ချက်ချင်းကြီးမပြောင်းဘဲ မျက်တောင်တစ်ချက် ခတ်လိုက်ပါမည်
    if (currentEmotion != lastRenderedEmotion && !isTransitioning) {
        isTransitioning = true;
        transitionTimer = millis();
    }

    // ----------------------------------------------------
    // ၃။ Emotion အလိုက် မျက်လုံး အရွယ်အစား ပြောင်းလဲခြင်း
    // ----------------------------------------------------
    int renderEmotion = isTransitioning ? lastRenderedEmotion : currentEmotion;

    if (renderEmotion == 8) { // Curious 
        lx += 8; rx -= 8; w += 2;
    } 
    else if (renderEmotion == 9) { // Dizzy (မူးဝေသော - မျက်လုံးလွဲသွားမည်)
        y = 18; h = 24; lx -= 4; rx += 4; // ပြားပြီး ဘေးကားသွားမည်
    } 
    else if (renderEmotion == 10) { // Excited 
        h = 44; y = 10;
    } 
    else if (renderEmotion == 14) { // Scared
        w = 24; h = 24; y = 24; lx += 6; rx += 6;
    } 
    else if (renderEmotion == 16) { // Thinking
        lx += 10; rx += 10; y = 6;
    }

    // ----------------------------------------------------
    // ၄။ အလိုအလျောက် မျက်တောင်ခတ်ခြင်း (Auto-Blinker)
    // ----------------------------------------------------
    static unsigned long lastBlink = 0;
    static bool isBlinking = false;
    
    if (millis() - lastBlink > 4000 && !isTransitioning) { 
        isBlinking = true;
        lastBlink = millis();
    }
    if (isBlinking && millis() - lastBlink > 150) { 
        isBlinking = false;
    }

    // ----------------------------------------------------
    // ၅။ မျက်လုံး ပုံဖော်ခြင်း (Drawing)
    // ----------------------------------------------------
    
    // Transition ကြောင့်ဖြစ်စေ၊ Auto-blink ကြောင့်ဖြစ်စေ မျက်တောင်ခတ်နေလျှင်
    if (isBlinking || isTransitioning) {
        u8g2.drawBox(lx, y + h/2, w, 6);
        u8g2.drawBox(rx, y + h/2, w, 6);
        
        // Transition ပြီးဆုံးသွားလျှင် Emotion အသစ်သို့ ကူးပြောင်းမည်
        if (isTransitioning && millis() - transitionTimer > 120) {
            isTransitioning = false;
            lastRenderedEmotion = currentEmotion;
        }
    } else {
        // အခြေခံ မျက်လုံးအဝိုင်းလေးများ အရင်ဆွဲမည်
        u8g2.drawRBox(lx, y, w, h, 8);
        u8g2.drawRBox(rx, y, w, h, 8);

        u8g2.setDrawColor(0); // ခဲဖျက် (အမည်းရောင်)
        
        switch(renderEmotion) {
            case 1:  // Happy
            case 12: // Laughing
                u8g2.drawDisc(lx + w/2, y + h + (renderEmotion==12 ? 0 : 8), 20);
                u8g2.drawDisc(rx + w/2, y + h + (renderEmotion==12 ? 0 : 8), 20);
                break;
                
            case 2:  // Sad
            case 13: // Pleading
            case 17: // Upset
                u8g2.drawTriangle(lx-5, y-5, lx+w, y-5, lx, y+15);
                u8g2.drawTriangle(rx, y-5, rx+w+5, y-5, rx+w, y+15);
                break;
                
            case 3:  // Angry
            case 6:  // Confident
            case 11: // Frustrated
                u8g2.drawTriangle(lx, y-5, lx+w+5, y-5, lx+w+5, y+20);
                u8g2.drawTriangle(rx-5, y-5, rx+w, y-5, rx-5, y+20);
                if (renderEmotion == 6) { 
                    u8g2.drawDisc(lx + w/2, y + h + 10, 18);
                    u8g2.drawDisc(rx + w/2, y + h + 10, 18);
                }
                if (renderEmotion == 11) u8g2.drawBox(0, y+h-12, 128, 20);
                break;
                
            case 4:  // Amused
                u8g2.drawBox(0, 0, 128, y+10); 
                u8g2.drawDisc(lx + w/2, y + h + 8, 20);
                u8g2.drawDisc(rx + w/2, y + h + 8, 20);
                break;
                
            case 5:  // Bored
                u8g2.drawBox(0, 0, 128, y+18); 
                break;
                
            case 7:  // Confused
                u8g2.drawBox(rx-5, 0, w+10, y+20); 
                break;

            case 9:  // Dizzy (အသစ် - မျက်လုံးလွဲသွားမည်)
                // အဝိုင်းလေးတွေနဲ့ ပုံစံလွဲအောင် ဖျက်မည်
                u8g2.drawDisc(lx, y-5, 15);     // ဘယ်ဘက် အပေါ်ထောင့် ဖျက်မည်
                u8g2.drawDisc(rx+w, y+h+5, 15); // ညာဘက် အောက်ထောင့် ဖျက်မည်
                break;
                
            case 15: // Sleepy
                u8g2.drawBox(0, 0, 128, y+25); 
                break;
        }
        u8g2.setDrawColor(1); // အဖြူရောင် ပြန်ပြောင်းမည်
    }
    
    u8g2.sendBuffer();
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