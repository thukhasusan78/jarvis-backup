#ifndef MICROPHONE_MANAGER_H
#define MICROPHONE_MANAGER_H

#include <Arduino.h>

extern bool isMicRecording;

void initMicrophone();
void recordAndSendAudio();

#endif