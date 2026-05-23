#include "AudioManager.h"
#include "AudioGeneratorMP3.h"
#include "AudioOutputI2S.h"
#include "AudioFileSourceHTTPStream.h"

AudioGeneratorMP3 *mp3;
AudioFileSourceHTTPStream *file;
AudioOutputI2S *out;

void initAudio() {
    out = new AudioOutputI2S();
    out->SetPinout(2, 1, 41); // မင်းချိတ်ထားသော I2S Pin များ
    out->SetGain(0.5);
    mp3 = new AudioGeneratorMP3();
    file = nullptr;
    Serial.println("[Audio] I2S Audio System Ready!");
}

void playAudioStream(const char* url) {
    if (mp3->isRunning()) {
        mp3->stop();
    }
    if (file != nullptr) {
        delete file; // Memory Leak မဖြစ်အောင် အဟောင်းကို ဖျက်မည်
        file = nullptr;
    }
    
    file = new AudioFileSourceHTTPStream(url);
    mp3->begin(file, out);
    Serial.printf("[Audio] Streaming from: %s\n", url);
}

void updateAudio() {
    if (mp3->isRunning()) {
        if (!mp3->loop()) {
            mp3->stop();
            Serial.println("[Audio] Playback Finished!");
        }
    }
}