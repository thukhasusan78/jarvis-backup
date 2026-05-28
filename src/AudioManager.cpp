#include "AudioManager.h"
#include "AudioGeneratorWAV.h" 
#include "AudioOutputI2S.h"
#include "AudioFileSourceHTTPStream.h"
#include "AudioFileSourceBuffer.h" // 👈 ဤ Library အသစ်ကို ထပ်ထည့်ပါ

AudioGeneratorWAV *wav; 
AudioFileSourceHTTPStream *file;
AudioFileSourceBuffer *buff; // 👈 Buffer Pointer ကြေညာရန်
AudioOutputI2S *out;

void initAudio() {
    out = new AudioOutputI2S();
    out->SetPinout(2, 1, 41);
    out->SetGain(0.5); 
    wav = new AudioGeneratorWAV(); 
    file = nullptr;
    buff = nullptr; // 👈
    Serial.println("[Audio] I2S Audio System Ready (Buffered WAV Mode)!");
}

void playAudioStream(const char* url) {
    if (wav->isRunning()) {
        wav->stop();
    }
    
    // Memory မပိတ်ဆို့စေရန် အဟောင်းများကို အရင်ရှင်းလင်းမည်
    if (buff != nullptr) { delete buff; buff = nullptr; }
    if (file != nullptr) { delete file; file = nullptr; }
    
    file = new AudioFileSourceHTTPStream(url);
    
    // 🚀 STUTTERING FIX: Network မှ အသံကို တိုက်ရိုက်မဖွင့်ဘဲ 4KB Buffer ခံမည်
    buff = new AudioFileSourceBuffer(file, 4096); 
    
    wav->begin(buff, out); // file အစား buff ဖြင့် ချိတ်ဆက်ဖွင့်မည်
    Serial.printf("[Audio] Streaming AI Voice from: %s\n", url);
}

void updateAudio() {
    if (wav->isRunning()) {
        if (!wav->loop()) {
            wav->stop();
            Serial.println("[Audio] AI Playback Finished!");
        }
    }
}