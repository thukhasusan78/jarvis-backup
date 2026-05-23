#include <Arduino.h>
#include <Wire.h>
#include "DisplayManager.h" // မျက်လုံးပိုင်း
#include "EmotionEngine.h"  // အာရုံခံနှင့် ဦးနှောက်ပိုင်း
#include "MotorManager.h"   // မော်တာပိုင်း
#include "NetworkManager.h" // Network စနစ်
#include "AudioManager.h" // <--- အသ

#define SDA_PIN 8
#define SCL_PIN 9

// Task Handles များ
TaskHandle_t TaskDisplayHandle;
TaskHandle_t TaskEmotionHandle;
TaskHandle_t TaskMotorHandle;
TaskHandle_t TaskNetworkHandle;
TaskHandle_t TaskAudioHandle;

// Task Functions များ
void TaskDisplay(void *pvParameters);
void TaskEmotion(void *pvParameters);
void TaskMotor(void *pvParameters);
void TaskNetwork(void *pvParameters);
void TaskAudio(void *pvParameters);

void setup() {
  Serial.begin(115200);
  Serial.println("Emo Core System Booting...");

  // I2C လမ်းကြောင်းကို ဖွင့်ပါမည် (OLED နှင့် MPU6050 နှစ်ခုလုံးအတွက်)
  Wire.begin(SDA_PIN, SCL_PIN); 

  // Module တစ်ခုချင်းစီကို စတင်နှိုးပါမည်
  initDisplay(); 
  initEmotionEngine(); 
  initMotors();
  initAudio();
  initNetwork(); // WiFi နှင့် WebSocket စတင်မည်

  xTaskCreate(TaskDisplay, "Display_Task", 4096, NULL, 3, &TaskDisplayHandle);
  xTaskCreate(TaskEmotion, "Emotion_Task", 4096, NULL, 2, &TaskEmotionHandle);
  xTaskCreate(TaskMotor, "Motor_Task", 4096, NULL, 2, &TaskMotorHandle);
  
  // Network နှင့် Audio သည် Memory ပိုစားသဖြင့် 8192 bytes ပေးထားပါသည်
  xTaskCreate(TaskNetwork, "Network_Task", 8192, NULL, 1, &TaskNetworkHandle);
  xTaskCreate(TaskAudio, "Audio_Task", 8192, NULL, 2, &TaskAudioHandle);

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

// =========================================================
// TASK 4: Motor Manager (FreeRTOS)
// =========================================================
// DisplayManager မှ လက်ရှိ Emotion ကို လှမ်းယူရန် ကြေညာခြင်း
extern int currentEmotion; 

void TaskMotor(void *pvParameters) {
  for (;;) {
    // မျက်လုံး၏ လက်ရှိ Emotion အတိုင်း ခြေထောက်များကို လှုပ်ရှားစေမည်
    updateMotors(currentEmotion); 

    // မော်တာကို ချောမွေ့စေရန် 20ms (50 FPS) နှုန်းဖြင့် အမြဲ Update လုပ်မည်
    vTaskDelay(pdMS_TO_TICKS(20)); 
  }
}

// =========================================================
// TASK 5: Audio Manager (FreeRTOS)
// =========================================================
void TaskAudio(void *pvParameters) {
  for (;;) {
    updateAudio(); // သီချင်းကို တစ်ပိုင်းချင်းစီ အမြဲ Stream ဆွဲနေမည်
    vTaskDelay(pdMS_TO_TICKS(5)); // Stream မပြတ်သွားစေရန် 5ms သာ နားမည်
  }
}