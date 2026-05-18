#include "DisplayManager.h"
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <FluxGarage_RoboEyes.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1

// ၁။ Display Object ကို အရင်ဆောက်ပါမည်
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// ၂။ Constructor Error ကို ရှင်းလင်းခြင်း (display ကို () ဖြင့် ထည့်ပေးရမည်)
RoboEyes<Adafruit_SSD1306> eyes(display);

void initDisplay() {
  // OLED ကို ပါဝါပေးပါမည်
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("OLED failed to start!"));
  }
  
  // ၃။ Begin Error ကို ရှင်းလင်းခြင်း (Pointer တွေ မလိုတော့ပါ၊ ဂဏန်း ၃ လုံးသာ ထည့်ပါ)
  eyes.begin(128, 64, 100); 
  eyes.setAutoblinker(true, 3, 2); 
  
  // ၄။ Function Error ကို ရှင်းလင်းခြင်း (idle အစား setMood ကို သုံးရပါမည်)
  eyes.setMood(DEFAULT); 
}

void updateDisplay() {
  eyes.update(); 
}

void setEyeHappy() {
  // ပြုံးနေစဉ် မျက်တောင်ခတ်ခြင်းကို ခဏရပ်ထားမည်
  eyes.setAutoblinker(false, 3, 2); 
  eyes.setMood(HAPPY); 
}

void setEyeAngry() {
  eyes.setAutoblinker(false, 3, 2);
  eyes.setMood(ANGRY);
}

void setEyeNeutral() {
  eyes.setMood(DEFAULT);
  // ပုံမှန်အခြေအနေရောက်မှ မျက်တောင်ပြန်ခတ်မည်
  eyes.setAutoblinker(true, 3, 2); 
}