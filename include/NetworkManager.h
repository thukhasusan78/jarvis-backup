#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include <Arduino.h>
#include <ArduinoJson.h>

void initNetwork();
void updateNetwork();
void sendRobotState(float valence, float arousal, const char* mood);

// --- နှိုးစက်နှင့် အချိန်စနစ်အတွက် အသစ်ထပ်တိုးခြင်း ---
extern int alarmHour;
extern int alarmMinute;
extern bool isAlarmSet;
extern bool isAlarmRinging;

void setLocalAlarm(int hour, int minute);
void stopAlarm();
bool getMyanmarTime(int &hour, int &minute, int &second);

#endif