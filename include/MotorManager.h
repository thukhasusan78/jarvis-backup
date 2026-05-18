#ifndef MOTOR_MANAGER_H
#define MOTOR_MANAGER_H
#include <Arduino.h>

// Servo မော်တာ ၄ လုံးကို စတင်ရန်
void initMotors();

// မျက်လုံး၏ လက်ရှိ Emotion ပေါ်မူတည်၍ ခြေထောက်များကို လှုပ်ရှားရန်
void updateMotors(int emotionId);

#endif