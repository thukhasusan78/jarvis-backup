#include <Arduino.h>
#include <Wire.h>
#include "DisplayManager.h" // မျက်လုံးပိုင်း
#include "EmotionEngine.h"  // အာရုံခံနှင့် ဦးနှောက်ပိုင်း
#include "NetworkManager.h" // Network စနစ်

#define SDA_PIN 8
#define SCL_PIN 9

// Task Handles များ
TaskHandle_t TaskDisplayHandle;
TaskHandle_t TaskEmotionHandle;
TaskHandle_t TaskNetworkHandle;

// Task Functions များ
void TaskDisplay(void *pvParameters);
void TaskEmotion(void *pvParameters);
void TaskNetwork(void *pvParameters);

void setup() {
  Serial.begin(115200);
  Serial.println("Emo Core System Booting...");

  // I2C လမ်းကြောင်းကို ဖွင့်ပါမည် (OLED နှင့် MPU6050 နှစ်ခုလုံးအတွက်)
  Wire.begin(SDA_PIN, SCL_PIN); 

  // Module တစ်ခုချင်းစီကို စတင်နှိုးပါမည်
  initDisplay(); 
  initEmotionEngine(); 
  //initNetwork(); // WiFi နှင့် WebSocket စတင်မည်

  // FreeRTOS Tasks များ စတင်ပါမည်
  // မျက်လုံး Task (Priority 3 - အရေးအကြီးဆုံး)
  xTaskCreate(TaskDisplay, "Display_Task", 4096, NULL, 3, &TaskDisplayHandle);
  
  // Sensor ဖတ်သည့် Task (Priority 2)
  xTaskCreate(TaskEmotion, "Emotion_Task", 4096, NULL, 2, &TaskEmotionHandle);

    // Network Task ကို Priority 1 ဖြင့် စတင်ပါမည် (မျက်လုံးကို မထစ်စေရန် အနိမ့်ဆုံး Priority ပေးထားပါသည်)
  //xTaskCreate(TaskNetwork, "Network_Task", 8192, NULL, 1, &TaskNetworkHandle);

  Serial.println("FreeRTOS Running...");
}

void loop() {
  vTaskDelete(NULL); // FreeRTOS ကို သုံးထားသဖြင့် loop() ကို ပိတ်ထားသည်
}

// =========================================================
// TASK 1: Display Manager (FreeRTOS)
// =========================================================
void TaskDisplay(void *pvParameters) {
  for (;;) {
    updateDisplay(); // မျက်လုံး Animation ကို အမြဲ Run နေပါမည်
    vTaskDelay(pdMS_TO_TICKS(20)); // 20ms နားမည်
  }
}

// =========================================================
// TASK 2: Emotion Engine (FreeRTOS)
// =========================================================
void TaskEmotion(void *pvParameters) {
  for (;;) {
    // ၁။ Sensor များကို ဖတ်ပြီး EmotionEngine.cpp ထဲတွင် မျက်လုံးများကို တိုက်ရိုက် ပြောင်းလဲပါမည်
    updateEmotionEngine(); 

    // ၂။ ၁၀၀ မီလီစက္ကန့် (0.1 စက္ကန့်) တစ်ခါ Sensor များ ဖတ်ပါမည် (Delay မဟုတ်ပါ၊ Task Delay ပါ)
    vTaskDelay(pdMS_TO_TICKS(100)); 
  }
}

// =========================================================
// TASK 3: Network Manager (FreeRTOS)
// =========================================================
void TaskNetwork(void *pvParameters) {
  unsigned long lastSendTime = 0; // အချိန်မှတ်ရန်
  
  for (;;) {
    updateNetwork(); // WebSocket ကို လုံးဝ မအိပ်စေဘဲ အမြဲ Run ပေးနေမည်
    
    // ၂ စက္ကန့် (2000ms) ပြည့်တိုင်းသာ ဆာဗာဆီသို့ Data လှမ်းပို့မည်
    if (millis() - lastSendTime > 2000) {
      sendRobotState(0.0, 0.0, "NEUTRAL"); 
      lastSendTime = millis();
    }
    
    // Network Loop ကို ထစ်မသွားစေရန် 20ms သာ နားပေးမည်
    vTaskDelay(pdMS_TO_TICKS(20)); 
  }
}