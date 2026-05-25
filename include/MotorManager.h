#ifndef MOTOR_MANAGER_H
#define MOTOR_MANAGER_H

#include <Arduino.h>
#include <ESP32Servo.h>

void initMotors();
void updateMotors(int emotionId);

// Xiaozhi's Otto Robot Movements (မော်တာလှုပ်ရှားမှု ၁၁ မျိုး)
void setMove_Walk();
void setMove_Turn();
void setMove_UpDown();
void setMove_Moonwalker();
void setMove_Swing();
void setMove_Crusaito();
void setMove_Flapping();
void setMove_ShakeLeg();
void setMove_TiptoeSwing();
void setMove_Jitter();
void setMove_Bend();

#endif