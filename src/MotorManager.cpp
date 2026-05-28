#include "MotorManager.h"

// ခြေထောက် ၄ ခုအတွက် Servo ကြေညာခြင်း
Servo servoLeftHip;
Servo servoLeftKnee;
Servo servoRightHip;
Servo servoRightKnee;

const int LEFT_HIP_PIN = 4;
const int RIGHT_HIP_PIN = 5; 
const int LEFT_KNEE_PIN = 6;  
const int RIGHT_KNEE_PIN = 7; 

// --- Xiaozhi Oscillator စနစ် ---
struct Oscillator {
    float A = 0;      // Amplitude (လှုပ်ရှားမည့် အကျယ်)
    float O = 0;      // Offset (အလယ်ဗဟိုချက်)
    float T = 1000;   // Period (အချိန် ဥပမာ - ၁၀၀၀ မီလီစက္ကန့်)
    float phase = 0;  // Phase (စတင်မည့် ဒီဂရီ)
    int pos = 90;     // လက်ရှိရောက်နေသော ဒီဂရီ
    int trim = 0;     // ချိန်ညှိမှု (Calibration)
};

Oscillator osc[4]; 
unsigned long ref_time = 0;
bool isMoving = false;
int currentMovement = 0; 

void initMotors() {
    // ESP32-S3 အတွက် Timer များကို အရင်နေရာချထားရမည်
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);

    // Servo များအတွက် 50Hz သတ်မှတ်ပေးခြင်း
    servoLeftHip.setPeriodHertz(50);
    servoLeftKnee.setPeriodHertz(50);
    servoRightHip.setPeriodHertz(50);
    servoRightKnee.setPeriodHertz(50);

    // Pin များ ချိတ်ဆက်ခြင်း
    servoLeftHip.attach(LEFT_HIP_PIN);
    servoLeftKnee.attach(LEFT_KNEE_PIN);
    servoRightHip.attach(RIGHT_HIP_PIN);
    servoRightKnee.attach(RIGHT_KNEE_PIN);
    
    for (int i=0; i<4; i++) {
        osc[i].pos = 90;
        osc[i].trim = 0; 
    }
    
    servoLeftHip.write(90);
    servoLeftKnee.write(90);
    servoRightHip.write(90);
    servoRightKnee.write(90);
    
    Serial.println(F("[Motor] Servos Ready!"));
}

// လှိုင်း (Sine Wave) ကို တွက်ချက်သည့် Function
void refreshOscillators() {
    unsigned long current_time = millis();
    for(int i = 0; i < 4; i++) {
        float time_part = (current_time - ref_time) % (unsigned long)osc[i].T;
        float angle = (float)time_part / osc[i].T * 2 * PI;
        osc[i].pos = round(osc[i].A * sin(angle + osc[i].phase) + osc[i].O) + 90 + osc[i].trim;
    }
    
    servoLeftHip.write(osc[0].pos);
    servoRightHip.write(osc[1].pos);
    servoLeftKnee.write(osc[2].pos);
    servoRightKnee.write(osc[3].pos);
}

// လှုပ်ရှားမှုများကို စတင်ရန် ချိန်ညှိခြင်း
void setOscillators(float A0, float A1, float A2, float A3, 
                    float O0, float O1, float O2, float O3, 
                    float T0, float T1, float T2, float T3, 
                    float P0, float P1, float P2, float P3) {
    osc[0].A = A0; osc[1].A = A1; osc[2].A = A2; osc[3].A = A3;
    osc[0].O = O0; osc[1].O = O1; osc[2].O = O2; osc[3].O = O3;
    osc[0].T = T0; osc[1].T = T1; osc[2].T = T2; osc[3].T = T3;
    osc[0].phase = P0; osc[1].phase = P1; osc[2].phase = P2; osc[3].phase = P3;
    ref_time = millis();
    isMoving = true;
}

// --- Xiaozhi ၏ အဓိက လှုပ်ရှားမှု ၁၁ မျိုး ---

void setMove_Walk() { // ၁။ လမ်းလျှောက်ခြင်း
    setOscillators(15, 15, 20, 20,  0, 0, 0, 0,  1000, 1000, 1000, 1000,  0, PI, PI/2, -PI/2);
}

void setMove_Turn() { // ၂။ လှည့်ခြင်း
    setOscillators(20, 20, 10, 10,  0, 0, 0, 0,  1000, 1000, 1000, 1000,  0, PI, PI/2, PI/2);
}

void setMove_UpDown() { // ၃။ ထိုင်ထလုပ်ခြင်း
    setOscillators(0, 0, 25, 25,  0, 0, 0, 0,  1000, 1000, 1000, 1000,  0, 0, PI/2, PI/2);
}

void setMove_Moonwalker() { // ၄။ မွန်းဝေါ့ခ်
    setOscillators(15, 15, 15, 15,  0, 0, 0, 0,  1500, 1500, 1500, 1500,  0, PI, PI/2, -PI/2);
}

void setMove_Swing() { // ၅။ ယိမ်းထိုးခြင်း
    setOscillators(20, 20, 0, 0,  0, 0, 0, 0,  1200, 1200, 1200, 1200,  0, PI, 0, 0);
}

void setMove_Crusaito() { // ၆။ ကဏန်းလျှောက်
    setOscillators(15, 15, 25, 25,  0, 0, 0, 0,  1500, 1500, 1500, 1500,  0, PI, PI/2, PI/2);
}

void setMove_Flapping() { // ၇။ တောင်ပံခတ်ခြင်း (ဝမ်းသာသောအခါ)
    setOscillators(10, 10, 20, 20,  0, 0, 0, 0,  600, 600, 600, 600,  0, PI, 0, PI);
}

void setMove_ShakeLeg() { // ၈။ ခြေခါခြင်း
    setOscillators(0, 0, 15, 0,  0, 0, -15, 0,  500, 500, 500, 500,  0, 0, PI/2, 0);
}

void setMove_TiptoeSwing() { // ၉။ ခြေဖျားထောက်ယိမ်းခြင်း
    setOscillators(20, 20, 15, 15,  0, 0, -10, -10,  1000, 1000, 1000, 1000,  0, PI, PI/2, PI/2);
}

void setMove_Jitter() { // ၁၀။ တုန်ယင်ခြင်း (ဒေါသထွက်/ကြောက်သောအခါ)
    setOscillators(5, 5, 5, 5,  0, 0, 0, 0,  150, 150, 150, 150,  0, PI, PI/2, -PI/2);
}

void setMove_Bend() { // ၁၁။ ကိုင်းညွတ်ခြင်း (အိပ်နေစဉ်)
    setOscillators(0, 0, 30, 30,  0, 0, -20, 20,  3000, 3000, 3000, 3000,  0, 0, PI/2, PI/2);
}

// မျက်လုံး/အမူအရာပေါ်မူတည်၍ လှုပ်ရှားမှုများကို ချိတ်ဆက်ပေးခြင်း
void updateMotors(int emotionId) {
    if (currentMovement != emotionId) {
        currentMovement = emotionId;
        
        switch (emotionId) {
            case 1: setMove_Walk(); break; 
            case 2: setMove_Turn(); break; 
            case 3: setMove_Jitter(); break;   // ဒေါသထွက်လျှင် တုန်ယင်မည်
            case 5: setMove_Flapping(); break; // ဝမ်းသာလျှင် တောင်ပံခတ်မည်
            case 6: setMove_Bend(); break;     // အိပ်နေလျှင် ခါးကိုင်းထားမည်
            case 9: setMove_ShakeLeg(); break; // မူးနေလျှင် ခြေခါမည်
            case 20: setMove_Jitter(); break;  // Alarm မြည်လျှင် တုန်ယင်မည်
            case 25: setMove_Swing(); break;   // သီချင်းနားထောင်လျှင် ယိမ်းထိုးမည်
            default: isMoving = false; break;  // ပုံမှန်ဆိုလျှင် ရပ်နေမည်
        }
    }
    
    if (isMoving) {
        refreshOscillators(); // လှုပ်ရှားနေပါက လှိုင်းများကို ဆက်လက်တွက်ချက်၍ မော်တာများကို မောင်းနှင်မည်
    } else {
        // ရပ်နေပါက ၉၀ ဒီဂရီသို့ ပြန်သွားမည်
        servoLeftHip.write(90);
        servoRightHip.write(90);
        servoLeftKnee.write(90);
        servoRightKnee.write(90);
    }
}