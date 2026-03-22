const ws = new WebSocket("wss://jarvis.thukha.online/ws/voice");
const micBtn = document.getElementById('mic-btn');
const statusText = document.getElementById('status-text');
const userTextDisplay = document.getElementById('user-text');
const hologramBox = document.getElementById('hologram-box');
const hologramContent = document.getElementById('hologram-content');

let audioContext;
let isAutoListen = false; // 🔄 Hands-free စနစ်အတွက် State

// ၁။ Browser Native STT 
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang = 'my-MM';
recognition.interimResults = false;
recognition.continuous = false; // လက်စွဲထိန်းချုပ်မည်

// --- 🎙️ Hands-free Mic Controller ---
micBtn.addEventListener('click', () => {
    if (!audioContext) audioContext = new (window.AudioContext || window.webkitAudioContext)();
    
    isAutoListen = !isAutoListen; // အဖွင့်/အပိတ် ခလုတ်အဖြစ် ပြောင်းလဲခြင်း

    if (isAutoListen) {
        micBtn.style.boxShadow = "0 0 20px #ff0000";
        micBtn.style.borderColor = "#ff0000";
        micBtn.innerText = "🛑"; // ရပ်တန့်ရန် ခလုတ်အသွင် ပြောင်းမည်
        startMic();
    } else {
        micBtn.style.boxShadow = "none";
        micBtn.style.borderColor = "#00d2ff";
        micBtn.innerText = "🎙️";
        statusText.innerText = "System Offline. Click Mic to start.";
        recognition.stop();
    }
});

function startMic() {
    // Auto-listen ဖွင့်ထားပြီး Jarvis လည်း စကားပြောမနေဘူးဆိုရင် မိုက်ဖွင့်မည်
    if (isAutoListen && !isPlaying) {
        try { recognition.start(); } catch(e) {}
    }
}

recognition.onstart = () => {
    statusText.innerText = "Listening... (Speak now)";
    statusText.style.color = "#ff0000";
};

// 👇 ဒီအောက်က Code အသစ်ကို ပေါင်းထည့်ပါ
recognition.onerror = (event) => {
    console.error("Speech Recognition Error: ", event.error);
    // ဖုန်းတွင် မည်သည့် Error ကြောင့် မိုက်မပွင့်သည်ကို ပြသပေးမည်
    statusText.innerText = `Mic Error: ${event.error}`; 
    statusText.style.color = "#ff0000";
    micBtn.style.boxShadow = "none";
    micBtn.style.borderColor = "#00d2ff";
    micBtn.innerText = "🎙️";
    isAutoListen = false;
};

// စကားပြောပြီး၍ ရပ်သွားတိုင်း Auto ပြန်ဖွင့်ပေးမည့်စနစ် (Loop)
recognition.onend = () => {
    if (isAutoListen && !isPlaying) {
        setTimeout(startMic, 300); // Error မတက်စေရန် 300ms ခြားပြီးမှ ပြန်ဖွင့်မည်
    }
};

recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    userTextDisplay.innerText = transcript;
    document.getElementById('jarvis-text').innerText = ""; // 👈 အဟောင်းများကို ရှင်းလင်းမည်
    
    // Server ဆီသို့ စာသားပို့ခြင်း
    ws.send(JSON.stringify({ type: "text", text: transcript }));
    
    statusText.innerText = "Thinking...";
    statusText.style.color = "#ffff00";
};

ws.onmessage = async (event) => {
    if (typeof event.data === "string") {
        try {
            const data = JSON.parse(event.data);
            if (data.type === "hologram_trigger") renderHologram(data);
            // 👈 Server မှ Text Stream လာပါက UI တွင် ပြသမည်
            else if (data.type === "text_stream") {
                document.getElementById('jarvis-text').innerText += data.text + " ";
            }
        } catch (e) { console.log(event.data); }
    } else {
        // အသံ Bytes များကို Queue ထဲသို့ တန်းစီထည့်ခြင်း
        await handleAudioBlob(event.data);
    }
};

// --- 🎵 Robust Audio Queue System (အထစ်အငေါ့ကင်းစနစ်) ---
const audioQueue = [];
let isPlaying = false;

async function handleAudioBlob(blob) {
    if (!audioContext) return;
    const arrayBuffer = await blob.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    
    audioQueue.push(audioBuffer); // Queue ထဲသို့ ထည့်မည်
    playNext(); // ဖွင့်ရန် ကြိုးစားမည်
}

function playNext() {
    // တစ်ခုခု ဖွင့်နေလျှင် သို့မဟုတ် Queue ထဲတွင် အသံမရှိလျှင် ကျော်မည်
    if (isPlaying || audioQueue.length === 0) return;
    
    isPlaying = true;
    
    // 💡 Jarvis စကားပြောနေစဉ် မိမိအသံကို ပြန်မကြားစေရန် (Echo မဖြစ်ရန်) မိုက်ကို ယာယီပိတ်မည်
    if (isAutoListen) recognition.stop();
    
    statusText.innerText = "Jarvis is speaking...";
    statusText.style.color = "#00ff00";

    const audioBuffer = audioQueue.shift(); // ပထမဆုံး အသံကို ဆွဲထုတ်မည်
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);

    // အသံတစ်ပိုင်း ပြီးဆုံးသွားသည့်အခါ (Event-driven)
    source.onended = () => {
        isPlaying = false;
        
        if (audioQueue.length > 0) {
            playNext(); // Queue ထဲတွင် ကျန်နေသေးလျှင် ဆက်ဖွင့်မည်
        } else {
            // အကုန်ဖွင့်ပြီးသွားလျှင် မိုက်ကို အလိုလို ပြန်ဖွင့်ပေးမည်
            if (isAutoListen) {
                startMic();
            } else {
                statusText.innerText = "System Online. Click Mic to speak.";
            }
        }
    };

    source.start(0);
}

// --- 🧊 Hologram System ---
function renderHologram(data) {
    hologramBox.classList.remove('hidden');
    if (data.action === "render_map") {
        hologramContent.innerHTML = `<h3 style="color:#00ff00;">📍 Map: ${data.data}</h3>`;
    } else if (data.action === "render_tool") {
        hologramContent.innerHTML = `<h3 style="color:#00ff00;">⚙️ ${data.data}</h3>`;
    }
    setTimeout(() => { hologramBox.classList.add('hidden'); }, 15000);
}