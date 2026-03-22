const hologramBox = document.getElementById('hologram-box');
const hologramContent = document.getElementById('hologram-content');
const voiceIndicator = document.getElementById('voice-indicator');

// ၁။ WebSocket ချိတ်ဆက်ခြင်း
// (Production တွင် 'wss://jarvis.thukha.online/ws/voice' သို့ ပြောင်းပါ)
const ws = new WebSocket(`ws://${window.location.host}/ws/voice`);

ws.onopen = () => {
    voiceIndicator.innerText = "J.A.R.V.I.S Online";
};

// ၂။ အချက်အလက်များ လက်ခံခြင်း (Audio Bytes နှင့် JSON Text ကို ခွဲခြားခြင်း)
ws.onmessage = async (event) => {
    if (typeof event.data === "string") {
        // 👈 String ဖြစ်လျှင် Hologram Tool မှ ပို့သော JSON Data ဖြစ်သည်
        try {
            const data = JSON.parse(event.data);
            if (data.type === "hologram_trigger") {
                renderHologram(data);
            }
        } catch (e) { console.error("JSON Parse Error", e); }
    } else {
        // 👈 Binary ဖြစ်လျှင် Gemini မှ ပို့သော Audio Data ဖြစ်သည်
        // Audio Data ကို ချက်ချင်း Play မည့် Logic (Web Audio API ကို သုံးရပါမည်)
        playAudioStream(event.data);
    }
};

// ၃။ Hologram Rendering (Widget ပြသခြင်း)
function renderHologram(data) {
    hologramBox.classList.remove('hidden');
    hologramBox.classList.add('glow-effect'); // အလန်းစား Animation ထည့်ရန်
    
    if (data.action === "render_map") {
        hologramContent.innerHTML = `<h3>📍 Map: ${data.data}</h3><p>(Google Maps iframe ဤနေရာတွင် ဝင်မည်)</p>`;
    } else if (data.action === "render_weather") {
        hologramContent.innerHTML = `<h3>⛅ Weather: ${data.data}</h3>`;
    }
    
    // စက္ကန့် ၃၀ အကြာတွင် အလိုအလျောက် ပိတ်သွားရန်
    setTimeout(() => { hologramBox.classList.add('hidden'); }, 30000);
}

// ၄။ Local Wake-Vision (MediaPipe) 
// Browser တွင် လူမျက်နှာတွေ့မှသာ Video Frame ကို Server သို့ ပို့မည် (Server Load လျှော့ချရန်)
const videoElement = document.getElementById('webcam');
const camera = new Camera(videoElement, {
    onFrame: async () => {
        await faceDetection.send({image: videoElement});
    },
    width: 640, height: 480
});

const faceDetection = new FaceDetection({locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_detection/${file}`});
faceDetection.setOptions({ minDetectionConfidence: 0.5 });

faceDetection.onResults((results) => {
    if (results.detections.length > 0) {
        // လူမျက်နှာ တွေ့ပါပြီ! (Trigger)
        // ဤနေရာတွင် Video Frame ကို Base64 ပြောင်း၍ WebSocket မှတစ်ဆင့် ပို့နိုင်ပါသည်
        console.log("Sir is detected. Ready to stream visual context.");
    }
});
// ကင်မရာ စတင်ရန် `camera.start();` ကို UI တွင် ခလုတ်နှိပ်၍ ဖွင့်ပေးရပါမည်။