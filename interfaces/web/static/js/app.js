const ws = new WebSocket("wss://jarvis.thukha.online/ws/voice");
const micBtn = document.getElementById('mic-btn');
const statusText = document.getElementById('status-text');
const userTextDisplay = document.getElementById('user-text');
const hologramBox = document.getElementById('hologram-box');
const hologramContent = document.getElementById('hologram-content');

let audioContext;

// ၁။ မြန်မာဘာသာစကားအတွက် Browser Native STT (Zero-Latency) တပ်ဆင်ခြင်း
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang = 'my-MM'; // မြန်မာဘာသာစကား
recognition.interimResults = false; 

recognition.onstart = () => {
    micBtn.style.background = "#ff0000";
    statusText.innerText = "Listening...";
};

recognition.onspeechend = () => {
    micBtn.style.background = "transparent";
    statusText.innerText = "Processing...";
    recognition.stop();
};

// ၂။ User ပြောပြီးတာနဲ့ စာသားကို WebSocket ကနေ Server (CEO) ဆီ တိုက်ရိုက်ပို့ခြင်း
recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    userTextDisplay.innerText = transcript;
    
    // Server ဆီသို့ JSON Text အနေဖြင့် ပို့လွှတ်သည်
    ws.send(JSON.stringify({ type: "text", text: transcript }));
};

micBtn.addEventListener('click', () => {
    if (!audioContext) audioContext = new (window.AudioContext || window.webkitAudioContext)();
    recognition.start();
});

// ၃။ Server မှ ပြန်လာသော အဖြေ (Hologram JSON သို့မဟုတ် Audio Bytes) ကို လက်ခံခြင်း
ws.onmessage = async (event) => {
    if (typeof event.data === "string") {
        try {
            const data = JSON.parse(event.data);
            if (data.type === "hologram_trigger") renderHologram(data);
        } catch (e) { console.log(event.data); }
    } else {
        // Audio Bytes (Edge TTS မှ အသံ) ဖြစ်ပါက ချက်ချင်း Play မည်
        statusText.innerText = "Jarvis is speaking...";
        await playAudioStream(event.data);
        statusText.innerText = "System Online. Click Mic to speak.";
    }
};

// ၄။ Audio ဖတ်သည့် စနစ်
async function playAudioStream(blob) {
    if (!audioContext) return;
    const arrayBuffer = await blob.arrayBuffer();
    // Edge TTS မှလာသော MP3/WAV bytes များကို Decode လုပ်ခြင်း
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start(0);
}

// ၅။ Hologram ပြသသည့် စနစ်
function renderHologram(data) {
    hologramBox.classList.remove('hidden');
    if (data.action === "render_map") {
        hologramContent.innerHTML = `<h3 style="color:#00ff00;">📍 Map: ${data.data}</h3>`;
    }
    setTimeout(() => { hologramBox.classList.add('hidden'); }, 15000);
}