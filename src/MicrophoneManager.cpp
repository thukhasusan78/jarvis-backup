#include "MicrophoneManager.h"
#include <driver/i2s.h>
#include "NetworkManager.h" 

bool isMicRecording = false;

// INMP441 Pins
#define I2S_WS 16
#define I2S_SD 17
#define I2S_SCK 15
#define I2S_PORT I2S_NUM_1 // Speaker နှင့် မငြိစေရန် I2S_NUM_1 ကိုသုံးပါသည်

void initMicrophone() {
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = 16000, // Gemini နားလည်ရန် 16kHz
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = 1024,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0
    };
    
    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SCK,
        .ws_io_num = I2S_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_SD
    };
    
    i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_PORT, &pin_config);
    i2s_zero_dma_buffer(I2S_PORT);
    Serial.println("[Mic] INMP441 Microphone Ready!");
}

void recordAndSendAudio() {
    size_t bytesIn = 0;
    const int bufferLen = 1024;
    int16_t sBuffer[bufferLen];

    esp_err_t result = i2s_read(I2S_PORT, &sBuffer, bufferLen * sizeof(int16_t), &bytesIn, portMAX_DELAY);
    
    if (result == ESP_OK && bytesIn > 0) {
        // --- 🚀 Software Gain: အသံကို (၈) ဆ ချဲ့ပေးမည် ---
        int numSamples = bytesIn / 2; // 16-bit ဆိုတော့ 2 ဖြင့်စားသည်
        for (int i = 0; i < numSamples; i++) {
            int32_t amplified = (int32_t)sBuffer[i] * 8; // ၈ ဆ မြှောက်မည်
            
            // အသံအရမ်းကျယ်သွားပါက အက်မသွားစေရန် ကန့်သတ်ခြင်း (Clipping limit)
            if (amplified > 32767) amplified = 32767;
            if (amplified < -32768) amplified = -32768;
            
            sBuffer[i] = (int16_t)amplified;
        }
        
        sendAudioChunk((uint8_t*)sBuffer, bytesIn);
    }
}