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
    // ၁။ မျက်လုံး အခြေခံ အရွယ်အစား
    // ----------------------------------------------------
    int w = 36;         
    int h = 36;         
    int lx = 20;        
    int rx = 72;        
    int y = 14;         

    // ----------------------------------------------------
    // ၂။ ညင်သာသော Transition (Blink-to-Transition) စနစ်
    // ----------------------------------------------------
    static int lastRenderedEmotion = 0;
    static unsigned long transitionTimer = 0;
    static bool isTransitioning = false;

    // Emotion အသစ်ပြောင်းသွားတိုင်း မျက်တောင်တစ်ချက် ခတ်မည်
    if (currentEmotion != lastRenderedEmotion && !isTransitioning) {
        isTransitioning = true;
        transitionTimer = millis();
    }

    // ----------------------------------------------------
    // ၃။ အလိုအလျောက် မျက်လုံးကစားခြင်း (Idle Look Around)
    // ----------------------------------------------------
    // (အခုမှ နေရာမှန်ရောက်သွားသဖြင့် Error လုံးဝ မတက်တော့ပါ)
    static int offsetX = 0;
    static int offsetY = 0;
    static unsigned long lastLookTime = 0;

    // ပုံမှန်အခြေအနေ (Neutral) တွင်သာ မျက်လုံးကစားပါမည်
    if (currentEmotion == 0 && !isTransitioning) {
        if (millis() - lastLookTime > 1000) { 
            offsetX = random(-4, 5); // -4 မှ 4 အတွင်း ဘယ်/ညာ
            offsetY = random(-3, 4); // -3 မှ 3 အတွင်း အထက်/အောက်
            lastLookTime = millis();
        }
    } else {
        offsetX = 0;
        offsetY = 0;
    }

    lx += offsetX;
    rx += offsetX;
    y += offsetY;

    // ----------------------------------------------------
    // ၄။ Emotion အလိုက် မျက်လုံး အရွယ်အစား ပြောင်းလဲခြင်း
    // ----------------------------------------------------
    int renderEmotion = isTransitioning ? lastRenderedEmotion : currentEmotion;

    if (renderEmotion == 8) { 
        lx += 8; rx -= 8; w += 2;
    } 
    else if (renderEmotion == 9) { 
        y = 18; h = 24; lx -= 4; rx += 4; 
    } 
    else if (renderEmotion == 10) { 
        h = 44; y = 10;
    } 
    else if (renderEmotion == 14) { 
        w = 24; h = 24; y = 24; lx += 6; rx += 6;
    } 
    else if (renderEmotion == 16) { 
        lx += 10; rx += 10; y = 6;
    }

    // ----------------------------------------------------
    // ၅။ အလိုအလျောက် မျက်တောင်ခတ်ခြင်း (Auto-Blinker)
    // ----------------------------------------------------
    static unsigned long lastBlink = 0;
    static bool isBlinking = false;
    
    // Wokwi Simulator နှေးနေမှုကို ကာဗာလုပ်ရန် 1000ms ဖြင့် ယာယီထားပါသည်
    if (millis() - lastBlink > 2000 && !isTransitioning) { 
        isBlinking = true;
        lastBlink = millis();
    }
    // မျက်တောင် ပြန်ဖွင့်မည့် အချိန်ကို 150ms ထားသည်
    if (isBlinking && millis() - lastBlink > 150) { 
        isBlinking = false;
    }

    // ----------------------------------------------------
    // ၆။ မျက်လုံး ပုံဖော်ခြင်း (Drawing)
    // ----------------------------------------------------
    if (isBlinking || isTransitioning) {
        u8g2.drawBox(lx, y + h/2, w, 6);
        u8g2.drawBox(rx, y + h/2, w, 6);
        
        if (isTransitioning && millis() - transitionTimer > 120) {
            isTransitioning = false;
            lastRenderedEmotion = currentEmotion;
        }
    } else {
        u8g2.drawRBox(lx, y, w, h, 8);
        u8g2.drawRBox(rx, y, w, h, 8);

        u8g2.setDrawColor(0); 
        
        switch(renderEmotion) {
            case 1:  
            case 12: 
                u8g2.drawDisc(lx + w/2, y + h + (renderEmotion==12 ? 0 : 8), 20);
                u8g2.drawDisc(rx + w/2, y + h + (renderEmotion==12 ? 0 : 8), 20);
                break;
                
            case 2:  
            case 13: 
            case 17: 
                u8g2.drawTriangle(lx-5, y-5, lx+w, y-5, lx, y+15);
                u8g2.drawTriangle(rx, y-5, rx+w+5, y-5, rx+w, y+15);
                break;
                
            case 3:  
            case 6:  
            case 11: 
                u8g2.drawTriangle(lx, y-5, lx+w+5, y-5, lx+w+5, y+20);
                u8g2.drawTriangle(rx-5, y-5, rx+w, y-5, rx-5, y+20);
                if (renderEmotion == 6) { 
                    u8g2.drawDisc(lx + w/2, y + h + 10, 18);
                    u8g2.drawDisc(rx + w/2, y + h + 10, 18);
                }
                if (renderEmotion == 11) u8g2.drawBox(0, y+h-12, 128, 20);
                break;
                
            case 4:  
                u8g2.drawBox(0, 0, 128, y+10); 
                u8g2.drawDisc(lx + w/2, y + h + 8, 20);
                u8g2.drawDisc(rx + w/2, y + h + 8, 20);
                break;
                
            case 5:  
                u8g2.drawBox(0, 0, 128, y+18); 
                break;
                
            case 7:  
                u8g2.drawBox(rx-5, 0, w+10, y+20); 
                break;

            case 9:  
                u8g2.drawDisc(lx, y-5, 15);     
                u8g2.drawDisc(rx+w, y+h+5, 15); 
                break;
                
            case 15: 
                u8g2.drawBox(0, 0, 128, y+25); 
                break;
        }
        u8g2.setDrawColor(1); 
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