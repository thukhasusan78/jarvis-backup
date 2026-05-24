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
    // ၁။ မျက်လုံး အခြေခံ အရွယ်အစား (Base Size)
    // ----------------------------------------------------
    int w = 36;         
    int h = 36;         
    int lx = 20;        
    int rx = 72;        
    int y = 14;         

    // ----------------------------------------------------
    // ၂။ ညင်သာသော Transition နှင့် Blinker (Variables)
    // ----------------------------------------------------
    static int lastRenderedEmotion = 0;
    static unsigned long transitionTimer = 0;
    static bool isTransitioning = false;
    
    // Error တက်သော မျက်တောင်ခတ်သည့် Variable များကို ဤနေရာသို့ ရွှေ့လိုက်ပါသည်
    static unsigned long lastBlink = 0;
    static bool isBlinking = false;

    if (currentEmotion != lastRenderedEmotion && !isTransitioning) {
        isTransitioning = true;
        transitionTimer = millis();
    }

    // ----------------------------------------------------
    // ၃။ အသက်ဝင်သော မျက်လုံးကစားခြင်း (Living Eye Animations)
    // ----------------------------------------------------
    static float tg_x = 0, tg_y = 0;
    static float tg_wl = 0, tg_hl = 0;
    static float tg_wr = 0, tg_hr = 0;

    static float cur_x = 0, cur_y = 0;
    static float cur_wl = 0, cur_hl = 0;
    static float cur_wr = 0, cur_hr = 0;
    static unsigned long lastLookTime = 0;
    static bool isBooting = true;        // Power စဖွင့်ချိန်
    static float bootEyeHeight = -36.0;  // မျက်လုံးအမြင့်ကို အနှုတ် (ပိတ်ထားသည်) မှ စမည်
    static bool isIdleAction = false;    // Action နှင့် Neutral ကို တစ်လှည့်စီပြရန်

    // (၁) Power ပေးပေးချင်း ညင်သာစွာ မျက်လုံးဖွင့်ခြင်း (Boot Animation)
    if (isBooting) {
        bootEyeHeight += 0.8; // ဖြည်းဖြည်းချင်း ပွင့်လာစေရန် (0.8 သည် အသင့်တော်ဆုံးဖြစ်သည်)
        cur_hl = bootEyeHeight;
        cur_hr = bootEyeHeight;
        if (bootEyeHeight >= 0) {
            cur_hl = 0; cur_hr = 0;
            isBooting = false;
            lastLookTime = millis(); // မျက်လုံးအပြည့် ပွင့်ပြီးသည်နှင့် ၃ စက္ကန့် စောင့်ရန် အချိန်မှတ်မည်
        }
    } 
    // (၂) ပုံမှန် Neutral အခြေအနေတွင် အသက်ဝင်အောင် မျက်လုံးကစားခြင်း
    else if (currentEmotion == 0 && !isTransitioning && !isBlinking) {
        if (isIdleAction) {
            // အမူအရာ တစ်ခုခု လုပ်နေပါက၊ ၁.၅ စက္ကန့် မှ ၂.၅ စက္ကန့်အကြာတွင် Neutral သို့ အလိုအလျောက် ပြန်သွားမည်
            if (millis() - lastLookTime > random(1500, 2500)) {
                tg_x = 0; tg_y = 0; tg_wl = 0; tg_hl = 0; tg_wr = 0; tg_hr = 0;
                isIdleAction = false; // Neutral သို့ ပြန်ရောက်ပြီ
                lastLookTime = millis(); // Neutral တွင် အနည်းဆုံး ၃ စက္ကန့် စောင့်ရန် အချိန်မှတ်မည်
            }
        } else {
            // Neutral သို့ ရောက်နေပါက၊ ၃ စက္ကန့် (3000ms) ပြည့်မှသာ အမူအရာအသစ် ထပ်ပြမည်
            if (millis() - lastLookTime > 3000) {
                int action = random(1, 14); 
                
                tg_x = 0; tg_y = 0; tg_wl = 0; tg_hl = 0; tg_wr = 0; tg_hr = 0;

                switch(action) {
                    case 1: tg_x = -10; tg_y = -6; break; 
                    case 2: tg_x = 10; tg_y = -6; break;  
                    case 3: tg_x = -10; tg_y = 6; break;  
                    case 4: tg_x = 10; tg_y = 6; break;   
                    case 5: tg_x = -12; tg_wl = -4; tg_hl = 0; tg_wr = 2; tg_hr = 0; break; // ဘေးကြည့်လျှင် မျက်လုံး မရှည်ထွက်တော့ပါ
                    case 6: tg_x = 12; tg_wr = -4; tg_hr = 0; tg_wl = 2; tg_hl = 0; break;
                    case 7: tg_hl = 2; tg_hr = 2; tg_wl = 2; tg_wr = 2; tg_y = -4; break; // မျက်လုံး အလွန်အမင်း ပြူးကျယ်ခြင်းကို လျှော့ချလိုက်သည် 
                    case 8: tg_hl = -12; tg_hr = -12; tg_y = 6; break; 
                    // --- ဇဝေဇဝါဖြစ်သော အမူအရာကို မျက်စိမနောက်စေရန် အလွန်သိမ်မွေ့အောင် ထပ်လျှော့ထားသည် ---
                    case 9: tg_hl = 2; tg_wl = 0; tg_hr = -6; tg_wr = -2; tg_y = -1; break; 
                    case 10: tg_hl = -6; tg_wl = -2; tg_hr = 2; tg_wr = 0; tg_y = -1; break;
                    // ----------------------------------------------------------------------
                    case 11: tg_y = -12; tg_hl = -4; tg_hr = -4; break;
                    case 12: tg_y = 10; tg_hl = -4; tg_hr = -4; break;
                    case 13: tg_hl = -8; tg_hr = -8; tg_y = -4; break;
                }
                isIdleAction = true; // အမူအရာ စတင်နေပြီ
                lastLookTime = millis();
            }
        }
    } else {
        // Routine ပြနေချိန်တွင် Offset များကို 0 သို့ Reset လုပ်မည်
        tg_x = 0; tg_y = 0; tg_wl = 0; tg_hl = 0; tg_wr = 0; tg_hr = 0;
    }

    // --- LERP (Smooth Interpolation) Algorithm ---
    float ease = 0.4; 
    cur_x += (tg_x - cur_x) * ease;
    cur_y += (tg_y - cur_y) * ease;
    cur_wl += (tg_wl - cur_wl) * ease;
    cur_wr += (tg_wr - cur_wr) * ease;
    
    // Boot တက်နေချိန်တွင် LERP က ဝင်မနှောင့်ယှက်နိုင်အောင် ပိတ်ထားမည်
    if (!isBooting) {
        cur_hl += (tg_hl - cur_hl) * ease;
        cur_hr += (tg_hr - cur_hr) * ease;
    }

    // ----------------------------------------------------
    // ၄။ Emotion အလိုက် မျက်လုံး အရွယ်အစား ပြောင်းလဲခြင်း
    // ----------------------------------------------------
    int renderEmotion = isTransitioning ? lastRenderedEmotion : currentEmotion;

    if (renderEmotion == 8) { lx += 8; rx -= 8; w += 2; } 
    else if (renderEmotion == 9) { y = 18; h = 24; lx -= 4; rx += 4; } 
    else if (renderEmotion == 10) { h = 38; y = 10; } 
    else if (renderEmotion == 14) { w = 24; h = 24; y = 24; lx += 6; rx += 6; } 
    else if (renderEmotion == 16) { lx += 10; rx += 10; y = 6; }
    else if (renderEmotion == 20) { h = 6; y = 6; lx += 4; rx -= 4; } // Alarm
    else if (renderEmotion == 21) { 
        h = 24; y = 18; 
        lx += sin(millis() / 100.0) * 4; rx += sin(millis() / 100.0) * 4;
    }
    else if (renderEmotion == 22) { y = 20; h = 26; lx -= 2; rx += 2; }
    else if (renderEmotion == 23) { 
        h = 20; y = 16; 
        int readMove = sin(millis() / 200.0) * 6; 
        lx += readMove; rx += readMove;
    }
    else if (renderEmotion == 24) { y = 18; h = 24; lx += 4; rx -= 4; }
    else if (renderEmotion == 25) { w = 40; h = 40; y = 10; lx -= 2; rx -= 2; }

    // --- Final Position တွက်ချက်ခြင်း နှင့် Glitch ကာကွယ်ခြင်း ---
    int raw_wl = w + round(cur_wl);
    int raw_hl = h + round(cur_hl);
    int wl = raw_wl < 2 ? 2 : raw_wl; // အရွယ်အစား ၂ အောက် ငယ်သွားပါက ၂ အဖြစ်သာ ထားမည်
    int hl = raw_hl < 2 ? 2 : raw_hl;
    int l_x = lx + round(cur_x) - round(cur_wl / 2);
    int l_y = y + round(cur_y) - round(cur_hl / 2);

    int raw_wr = w + round(cur_wr);
    int raw_hr = h + round(cur_hr);
    int wr = raw_wr < 2 ? 2 : raw_wr;
    int hr = raw_hr < 2 ? 2 : raw_hr;
    int r_x = rx + round(cur_x) - round(cur_wr / 2);
    int r_y = y + round(cur_y) - round(cur_hr / 2);

    // ----------------------------------------------------
    // ၅။ အလိုအလျောက် မျက်တောင်ခတ်ခြင်း (Auto-Blinker) ၏ အချိန်မှတ်စနစ်
    // ----------------------------------------------------
    if (millis() - lastBlink > 3000 && !isTransitioning) { 
        isBlinking = true;
        lastBlink = millis();
    }
    if (isBlinking && millis() - lastBlink > 150) { 
        isBlinking = false;
    }

    // ----------------------------------------------------
    // ၆။ မျက်လုံး ပုံဖော်ခြင်း (Drawing)
    // ----------------------------------------------------
    if (isBlinking || isTransitioning) {
        u8g2.drawBox(l_x, l_y + hl/2, wl, 6);
        u8g2.drawBox(r_x, r_y + hr/2, wr, 6);
        
        if (isTransitioning && millis() - transitionTimer > 120) {
            isTransitioning = false;
            lastRenderedEmotion = currentEmotion;
        }
    } else {
        u8g2.drawRBox(l_x, l_y, wl, hl, 8);
        u8g2.drawRBox(r_x, r_y, wr, hr, 8);

        u8g2.setDrawColor(0); 
        switch(renderEmotion) {
            case 1:  case 12: case 22: 
                u8g2.drawDisc(l_x + wl/2, l_y + hl + (renderEmotion==12 ? 0 : 8), 20);
                u8g2.drawDisc(r_x + wr/2, r_y + hr + (renderEmotion==12 ? 0 : 8), 20);
                break;
            case 2:  case 13: case 17: 
                u8g2.drawTriangle(l_x-5, l_y-5, l_x+wl, l_y-5, l_x, l_y+15);
                u8g2.drawTriangle(r_x, r_y-5, r_x+wr+5, r_y-5, r_x+wr, r_y+15);
                break;
            case 3:  case 6:  case 11: case 24: 
                u8g2.drawTriangle(l_x, l_y-5, l_x+wl+5, l_y-5, l_x+wl+5, l_y+20);
                u8g2.drawTriangle(r_x-5, r_y-5, r_x+wr, r_y-5, r_x-5, r_y+20);
                if (renderEmotion == 11) u8g2.drawBox(0, l_y+hl-12, 128, 20);
                break;
            case 4:  
                u8g2.drawBox(0, 0, 128, l_y+10); 
                u8g2.drawDisc(l_x + wl/2, l_y + hl + 8, 20);
                u8g2.drawDisc(r_x + wr/2, r_y + hr + 8, 20);
                break;
            case 5:  
                u8g2.drawBox(0, 0, 128, l_y+18); break;
            case 7:  
                u8g2.drawBox(r_x-5, 0, wr+10, r_y+20); break;
            case 9:  
                u8g2.drawDisc(l_x, l_y-5, 15); u8g2.drawDisc(r_x+wr, r_y+hr+5, 15); break;
            case 15: 
                u8g2.drawBox(0, 0, 128, l_y+25); break;
        }
        u8g2.setDrawColor(1); 

        if (renderEmotion >= 20) {
            unsigned long ms = millis();
            if (renderEmotion == 20) { 
                int shake = sin(ms / 30.0) * 3; 
                u8g2.drawDisc(64 + shake, 52, 8, U8G2_DRAW_UPPER_RIGHT | U8G2_DRAW_UPPER_LEFT); 
                u8g2.drawBox(55 + shake, 52, 18, 2); 
                u8g2.drawDisc(64 + shake, 55, 2);    
            }
            else if (renderEmotion == 21) { 
                int moveX = sin(ms / 100.0) * 8;
                u8g2.drawBox(100 + moveX, 30, 20, 4); 
                u8g2.drawBox(100 + moveX, 26, 6, 8);  
            }
            else if (renderEmotion == 22) { 
                u8g2.drawCircle(64, 58, 8); 
                u8g2.drawBox(64 - 8 + (int)(sin(ms/150.0)*3), 48, 2, 8); 
                u8g2.drawBox(64 + 6 + (int)(sin(ms/150.0)*3), 48, 2, 8); 
            }
            else if (renderEmotion == 23) { 
                u8g2.drawBox(32, 58, 64, 4); 
                int leftHandY = 48 + (sin(ms / 80.0) * 4); 
                int rightHandY = 48 + (cos(ms / 80.0) * 4); 
                u8g2.drawRBox(40, leftHandY, 14, 10, 4); 
                u8g2.drawRBox(74, rightHandY, 14, 10, 4); 
            }
            else if (renderEmotion == 24) { 
                int liftY = sin(ms / 150.0) * 4;
                u8g2.drawBox(34, 56 + liftY, 60, 2); 
                u8g2.drawDisc(30, 57 + liftY, 4); u8g2.drawDisc(98, 57 + liftY, 4); 
            }
            else if (renderEmotion == 25) { 
                u8g2.drawFrame(0, 0, 128, 64); 
                if (ms % 500 < 250) {          
                    u8g2.drawHLine(random(10, 110), random(10, 54), 10);
                }
            }
        }
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

// --- နေ့စဉ်ဘဝ လုပ်ဆောင်ချက်များကို ပြောင်းလဲပေးမည့် Function အသစ် ---
void setActivityRoutine(int routineId) { currentEmotion = routineId; }