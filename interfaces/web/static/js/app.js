const ws = new WebSocket("wss://jarvis.thukha.online/ws/voice");
const micBtn = document.getElementById('mic-btn');
const statusText = document.getElementById('status-text');
const userTextDisplay = document.getElementById('user-text');
const hologramBox = document.getElementById('hologram-box');
const hologramContent = document.getElementById('hologram-content');

let audioContext;
let isAutoListen = false;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang = 'my-MM';
recognition.interimResults = false;
recognition.continuous = false;

// 📱 Mobile Permission Hack: ခလုတ်နှိပ်သည်နှင့် Permission ကို အတင်းတောင်းမည်
micBtn.addEventListener('click', async () => {
    // ၁။ Audio Context ကို နှိုးမည် (iOS အတွက် အရေးကြီးသည်)
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioContext.state === 'suspended') {
        await audioContext.resume();
    }

    // ၂။ ဖုန်း Browser များအတွက် Mic Permission ကို Force တောင်းမည်
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        stream.getTracks().forEach(track => track.stop()); // Permission ရပြီးလျှင် ပြန်ပိတ်ထားမည်
    } catch (err) {
        console.error("Mic Permission Blocked:", err);
    }

    isAutoListen = !isAutoListen;

    if (isAutoListen) {
        micBtn.style.boxShadow = "0 0 20px #ff0000";
        micBtn.style.borderColor = "#ff0000";
        micBtn.innerText = "🛑";
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
    if (isAutoListen && !isPlaying) {
        try { recognition.start(); } catch(e) { console.log("Already started."); }
    }
}

recognition.onstart = () => {
    statusText.innerText = "Listening... (Speak now)";
    statusText.style.color = "#ff0000";
};

recognition.onerror = (event) => {
    console.error("Mic Error: ", event.error);
    statusText.innerText = `Mic Error: ${event.error}`;
    statusText.style.color = "#ff0000";
    if(event.error === 'not-allowed') {
        isAutoListen = false;
        micBtn.innerText = "🎙️";
        micBtn.style.borderColor = "#00d2ff";
        micBtn.style.boxShadow = "none";
    }
};

recognition.onend = () => {
    if (isAutoListen && !isPlaying) {
        setTimeout(startMic, 300);
    }
};

recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    userTextDisplay.innerText = transcript;
    document.getElementById('jarvis-text').innerText = ""; 
    
    ws.send(JSON.stringify({ type: "text", text: transcript }));
    statusText.innerText = "Thinking...";
    statusText.style.color = "#ffff00";
};

// 🚀 Asynchronous ID-based Waiting Room စနစ်သစ်
let receiveIndex = 0; // ဝင်လာမည့် အသံများအတွက် ခုံနံပါတ် (ID)
let playIndex = 0;    // ဖွင့်ရမည့် အလှည့် (Sequence)
const audioWaitingRoom = {}; // အသင့်ဖြစ်သော အသံများ ထိုင်စောင့်မည့်နေရာ
let isPlaying = false;

ws.onmessage = (event) => {
    if (typeof event.data === "string") {
        try {
            const data = JSON.parse(event.data);
            if (data.type === "hologram_trigger") renderHologram(data);
            else if (data.type === "text_stream") {
                document.getElementById('jarvis-text').innerText += data.text + " ";
            }
        } catch (e) {}
    } else {
        // ⚡ အသံဖိုင်ရောက်လာသည်နှင့် ID တပ်ပေးပြီး ပြိုင်တူ (Async) Decode တန်းလုပ်ခိုင်းမည်
        const currentId = receiveIndex++;
        decodeAndStore(event.data, currentId);
    }
};

async function decodeAndStore(blob, id) {
    if (!audioContext) return;
    try {
        const arrayBuffer = await blob.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        // Decode ပြီးသွားပါက မိမိ၏ ID (ခုံနံပါတ်) နေရာတွင် ဝင်ထိုင်စောင့်နေမည်
        audioWaitingRoom[id] = audioBuffer;
        attemptPlay(); // အသံအသစ်ရတိုင်း ဖွင့်ရန် ကြိုးစားမည်
    } catch (error) {
        console.error("Decode error for ID", id, error);
        audioWaitingRoom[id] = null; // Error တက်လျှင်လည်း Queue မပိတ်စေရန် null ထည့်မည်
        attemptPlay();
    }
}

function attemptPlay() {
    if (isPlaying) return; // တစ်ခုခုဖွင့်နေလျှင် ဆက်စောင့်မည်

    // 💡 မိမိဖွင့်ရမည့် အလှည့် (playIndex) သည် Waiting Room ထဲ ရောက်နေပြီလား စစ်ဆေးမည်
    if (audioWaitingRoom.hasOwnProperty(playIndex)) {
        const audioBuffer = audioWaitingRoom[playIndex];
        delete audioWaitingRoom[playIndex]; // Waiting Room ထဲမှ ဖယ်ထုတ်မည်

        if (audioBuffer) {
            isPlaying = true;
            if (isAutoListen) { try { recognition.stop(); } catch(e){} }
            statusText.innerText = "Jarvis is speaking...";
            statusText.style.color = "#00ff00";

            const source = audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioContext.destination);

            source.onended = () => {
                isPlaying = false;
                playIndex++; // နောက်တစ်လှည့်သို့ ကူးမည်
                attemptPlay(); // နောက်တစ်လှည့် အသင့်ရှိမရှိ ဆက်တိုက်စစ်မည်
            };
            source.start(0);
        } else {
            // Decode Error တက်ထားသော ဖိုင်ဖြစ်ပါက ကျော်သွားမည်
            playIndex++;
            attemptPlay();
        }
    } else {
        // ဖွင့်စရာ အသံကုန်သွားပြီး ဝင်လာမည့်အသံ (receiveIndex) လည်း မရှိတော့လျှင် မိုက်ပြန်ဖွင့်မည်
        if (!isPlaying && receiveIndex === playIndex) {
            if (isAutoListen) {
                setTimeout(startMic, 300);
            } else {
                statusText.innerText = "System Online. Click Mic to speak.";
            }
            // အကုန်ပြီးသွားပါက ID များကို 0 မှ ပြန်စမည် (Memory မပြည့်စေရန်)
            receiveIndex = 0;
            playIndex = 0;
        }
    }
}

function playNext() {
    if (isPlaying || audioQueue.length === 0) return;
    
    isPlaying = true;
    if (isAutoListen) { recognition.stop(); }
    
    statusText.innerText = "Jarvis is speaking...";
    statusText.style.color = "#00ff00";

    const audioBuffer = audioQueue.shift();
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);

    source.onended = () => {
        isPlaying = false;
        if (audioQueue.length > 0) {
            playNext();
        } else {
            if (isAutoListen) {
                setTimeout(startMic, 300);
            } else {
                statusText.innerText = "System Online. Click Mic to speak.";
            }
        }
    };

    source.start(0);
}

function renderHologram(data) {
    hologramBox.classList.remove('hidden');
    if (data.action === "render_map") {
        hologramContent.innerHTML = `<h3 style="color:#00ff00;">📍 Map: ${data.data}</h3>`;
    } else if (data.action === "render_tool") {
        hologramContent.innerHTML = `<h3 style="color:#00ff00;">⚙️ ${data.data}</h3>`;
    }
    setTimeout(() => { hologramBox.classList.add('hidden'); }, 15000);
}