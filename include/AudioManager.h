#ifndef AUDIO_MANAGER_H
#define AUDIO_MANAGER_H
#include <Arduino.h>

void initAudio();
void playAudioStream(const char* url);
void updateAudio();

#endif