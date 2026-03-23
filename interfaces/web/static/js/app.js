// --- CONFIG & DOM ---
const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
const WS_URL = wsProtocol + window.location.host + "/ws/voice";

const screens = {
    init: document.getElementById('init-screen'),
    hud: document.getElementById('hud-interface'),
    shutdown: document.getElementById('shutdown-screen')
};
const reactor = document.getElementById('reactor');
const micStatus = document.getElementById('mic-status');
const userTextDisplay = document.getElementById('user-text');
const jarvisTextDisplay = document.getElementById('jarvis-text');
const hologramBox = document.getElementById('hologram-box');
const hologramContent = document.getElementById('hologram-content');

// --- STATE ---
let socket = null;
let recognition = null;
let audioContext = null;
let isShuttingDown = false;
let isAutoListen = true; // Touch ခဲ့ပြီးဖြစ်၍ Auto ဖွင့်ပေးမည်

// Streaming Queue States
let receiveIndex = 0;
let playIndex = 0;
const audioWaitingRoom = {};
let isPlaying = false;

// --- 1. BOOT SEQUENCE (The Trusted Gesture) ---
window.systemBoot = () => { 
    screens.init.classList.add('hidden');
    screens.hud.classList.remove('hidden');
    screens.hud.style.animation = "hudInit 1s ease forwards";

    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    if (audioContext.state === 'suspended') {
        audioContext.resume(); 
    }

    // 💡 ပြဿနာဖြစ်စေသော Hardware လုသည့် Silent Ping ကို ဖယ်ရှားလိုက်ပါပြီ

    connectWebSocket();
    initVoice(); 
};

// --- 2. WEBSOCKET HANDLER ---
function connectWebSocket() {
    socket = new WebSocket(WS_URL);
    socket.onopen = () => console.log("Connected to JARVIS Core");
    socket.onclose = () => console.log("Disconnected");

    socket.onmessage = (event) => {
        if (typeof event.data === "string") {
            try {
                const data = JSON.parse(event.data);
                if (data.type === "hologram_trigger") {
                    renderHologram(data);
                } else if (data.type === "text_stream") {
                    jarvisTextDisplay.innerText += data.text + " ";
                }
            } catch (e) {}
        } else {
            // အသံ Bytes များကို ID တပ်၍ Waiting Room သို့ ပို့မည်
            const currentId = receiveIndex++;
            decodeAndStore(event.data, currentId);
        }
    };
}

// --- 3. NATIVE SPEECH RECOGNITION ---
function initVoice() {
    const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Speech) {
        alert("Your browser does not support Speech Recognition.");
        return;
    }

    recognition = new Speech();
    recognition.lang = 'my-MM';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        if (!isShuttingDown && !isPlaying) {
            setReactorState("listening");
        }
    };

    recognition.onerror = (event) => {
        console.error("Mic Error:", event.error);
        // Hardware လုခြင်း သို့မဟုတ် Permission ကြောင့် ပိတ်ကျပါက အတင်းပြန်မဖွင့်တော့ဘဲ ရပ်ထားမည်
        if (event.error === 'not-allowed' || event.error === 'audio-capture' || event.error === 'aborted') {
            micStatus.innerText = "MIC ERROR";
            setReactorState("offline");
            isAutoListen = false;
        }
    };

    recognition.onresult = (event) => {
        const text = event.results[0][0].transcript;
        userTextDisplay.innerText = text;
        jarvisTextDisplay.innerText = ""; // Clear old response
        
        setReactorState("processing");
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "text", text: text }));
        }
    };

    recognition.onend = () => {
        // အသံမဖွင့်နေဘူး၊ Auto လည်းဖြစ်တယ်ဆိုရင် မိုက်ပြန်ဖွင့်မည်
        if (!isShuttingDown && isAutoListen && !isPlaying) {
            setTimeout(startMic, 300);
        }
    };

    startMic();
}

function startMic() {
    if (isAutoListen && !isPlaying && !isShuttingDown) {
        try { recognition.start(); } catch(e) {}
    }
}

// Manual Toggle for Mic
window.toggleMic = () => {
    isAutoListen = !isAutoListen;
    if (isAutoListen) {
        startMic();
    } else {
        try { recognition.stop(); } catch(e) {}
        setReactorState("offline");
        micStatus.innerText = "OFFLINE";
    }
};

// --- 4. TRUE STREAMING & WAITING ROOM (GAPLESS AUDIO) ---
async function decodeAndStore(blob, id) {
    if (!audioContext) return;
    try {
        const arrayBuffer = await blob.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        audioWaitingRoom[id] = audioBuffer;
        attemptPlay(); 
    } catch (error) {
        console.error("Decode error for ID", id, error);
        audioWaitingRoom[id] = null; 
        attemptPlay();
    }
}

function attemptPlay() {
    if (isPlaying || isShuttingDown) return; 

    if (audioWaitingRoom.hasOwnProperty(playIndex)) {
        const audioBuffer = audioWaitingRoom[playIndex];
        delete audioWaitingRoom[playIndex]; 

        if (audioBuffer) {
            isPlaying = true;
            try { recognition.stop(); } catch(e) {} // စကားပြောနေစဉ် မိုက်ပိတ်မည်
            setReactorState("speaking");

            const source = audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioContext.destination);

            source.onended = () => {
                isPlaying = false;
                playIndex++; 
                attemptPlay(); 
            };
            source.start(0);
        } else {
            playIndex++;
            attemptPlay();
        }
    } else {
        // အသံကုန်သွားပါက မိုက်ပြန်ဖွင့်မည်
        if (!isPlaying && receiveIndex === playIndex) {
            receiveIndex = 0;
            playIndex = 0;
            if (isAutoListen) {
                setTimeout(startMic, 300);
            } else {
                setReactorState("offline");
            }
        }
    }
}

// --- 5. UI EFFECTS ---
function setReactorState(state) {
    reactor.classList.remove('state-listening', 'state-processing', 'state-speaking');
    if (state === 'listening') {
        reactor.classList.add('state-listening');
        micStatus.innerText = "LISTENING";
    } else if (state === 'processing') {
        reactor.classList.add('state-processing');
        micStatus.innerText = "THINKING";
    } else if (state === 'speaking') {
        reactor.classList.add('state-speaking');
        micStatus.innerText = "SPEAKING";
    } else {
        micStatus.innerText = "READY";
    }
}

function renderHologram(data) {
    hologramBox.classList.remove('hidden');
    if (data.action === "render_map") {
        hologramContent.innerHTML = `<h3 class="text-green-400 font-bold tracking-widest">📍 MAP DATA: ${data.data}</h3>`;
    } else if (data.action === "render_tool") {
        hologramContent.innerHTML = `<h3 class="text-green-400 font-bold tracking-widest">⚙️ EXECUTING: ${data.data}</h3>`;
    }
    setTimeout(() => { hologramBox.classList.add('hidden'); }, 15000);
}

// Clock
setInterval(() => {
    document.getElementById('clock').innerText = new Date().toLocaleTimeString();
}, 1000);