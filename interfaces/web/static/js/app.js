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
const netStatus = document.getElementById('net-status');
const userTextDisplay = document.getElementById('user-text');
const jarvisTextDisplay = document.getElementById('jarvis-text');
const hologramBox = document.getElementById('hologram-box');
const hologramContent = document.getElementById('hologram-content');
const browserNotice = document.getElementById('browser-notice');
const popupLayer = document.getElementById('popup-layer');
const textInput = document.getElementById('text-input');
const sttFallbackNote = document.getElementById('stt-fallback-note');

// --- STATE ---
let socket = null;
let recognition = null;
let audioContext = null;
let isShuttingDown = false;
let isAutoListen = true; // Touch ခဲ့ပြီးဖြစ်၍ Auto ဖွင့်ပေးမည်
let isBooted = false;
let reconnectAttempt = 0;
let reconnectTimer = null;
let speechSupported = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
let consecutiveSttErrors = 0;
let wakeLock = null;
let popupCount = 0;
let pendingText = null;      // utterance waiting for an open socket
let lastHeardAt = 0;         // last time the server said anything (ping counts)

// Streaming Queue States
let receiveIndex = 0;
let playIndex = 0;
const audioWaitingRoom = {};
let isPlaying = false;

// Show Chrome/Edge requirement before boot if STT is missing
if (!speechSupported && browserNotice) {
    browserNotice.classList.remove('hidden');
}

function setNetStatus(text) {
    if (netStatus) netStatus.innerText = "NET: " + text;
}

// --- 1. BOOT SEQUENCE (The Trusted Gesture) ---
window.systemBoot = () => {
    if (!speechSupported) {
        if (browserNotice) browserNotice.classList.remove('hidden');
        // Still allow boot: the text-input fallback keeps the HUD usable
    }

    if (isBooted) return;
    isBooted = true;
    screens.init.classList.add('hidden');
    screens.hud.classList.remove('hidden');
    screens.hud.style.animation = "hudInit 1s ease forwards";

    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    if (audioContext.state === 'suspended') {
        audioContext.resume();
    }

    requestWakeLock();
    connectWebSocket();
    initVoice();
};

// Keep the screen awake while talking (mobile)
async function requestWakeLock() {
    try {
        if ('wakeLock' in navigator) {
            wakeLock = await navigator.wakeLock.request('screen');
        }
    } catch (e) { /* optional feature */ }
}

// Reconnect when the user returns to the tab (mobile browsers suspend sockets)
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && isBooted) {
        if (audioContext && audioContext.state === 'suspended') audioContext.resume();
        requestWakeLock();
        // A socket can look OPEN but be dead after suspend — check staleness
        const stale = Date.now() - lastHeardAt > 30000;
        if (!socket || socket.readyState !== WebSocket.OPEN || stale) {
            try { if (socket) socket.close(); } catch(e) {}
            connectWebSocket();
        }
    }
});

// --- 2. WEBSOCKET HANDLER ---
function connectWebSocket() {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
        return;
    }

    setNetStatus("CONNECTING");
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log("Connected to JARVIS Core");
        reconnectAttempt = 0;
        lastHeardAt = Date.now();
        setNetStatus("SECURE");
        if (micStatus && !isPlaying && isAutoListen && speechSupported) {
            micStatus.innerText = "LISTENING";
        }
        // Flush any utterance that arrived while the socket was down
        if (pendingText) {
            const t = pendingText;
            pendingText = null;
            socket.send(JSON.stringify({ type: "text", text: t }));
        }
        // STT may have been waiting for an open socket after reconnect
        if (isBooted && isAutoListen && !isPlaying) {
            setTimeout(startMic, 200);
        }
    };

    socket.onclose = () => {
        console.log("Disconnected");
        if (isShuttingDown || !isBooted) return;
        scheduleReconnect();
    };

    socket.onerror = () => {
        // onclose will fire after error; reconnect there
    };

    socket.onmessage = (event) => {
        lastHeardAt = Date.now();
        if (typeof event.data === "string") {
            try {
                const data = JSON.parse(event.data);
                if (data.type === "ping") {
                    if (socket && socket.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({ type: "pong" }));
                    }
                    return;
                }
                if (data.type === "pong") {
                    return;
                }
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

function scheduleReconnect() {
    if (reconnectTimer || isShuttingDown) return;
    // Fast recovery: cap backoff at 3s (a voice HUD must feel alive)
    const delay = Math.min(500 * Math.pow(2, reconnectAttempt), 3000);
    reconnectAttempt += 1;
    setNetStatus("RECONNECTING");
    if (micStatus) micStatus.innerText = "RECONNECTING";
    setReactorState("offline");
    reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectWebSocket();
    }, delay);
}

// Dead-socket watchdog: the server pings every 20s, so silence >45s means the
// socket is half-open (mobile network switch, tab suspend). Force a fresh one.
setInterval(() => {
    if (!isBooted || isShuttingDown) return;
    if (socket && socket.readyState === WebSocket.OPEN && Date.now() - lastHeardAt > 45000) {
        console.log("Socket stale, reconnecting");
        try { socket.close(); } catch(e) {}
        connectWebSocket();
    }
}, 10000);

// --- 3. NATIVE SPEECH RECOGNITION ---
function initVoice() {
    const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Speech) {
        if (browserNotice) browserNotice.classList.remove('hidden');
        showSttFallback("USE CHROME");
        return;
    }

    recognition = new Speech();
    recognition.lang = 'my-MM';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        consecutiveSttErrors = 0;
        if (!isShuttingDown && !isPlaying) {
            setReactorState("listening");
        }
    };

    recognition.onerror = (event) => {
        console.error("Mic Error:", event.error);
        // Permission/hardware failures: stop auto-restart entirely
        if (event.error === 'not-allowed' || event.error === 'audio-capture' || event.error === 'aborted') {
            isAutoListen = false;
            showSttFallback("MIC ERROR", event.error);
            return;
        }
        // Newer Android / MIUI-HyperOS without Google speech service:
        // 'network' or 'service-not-allowed'. Retrying forever just spins —
        // after a few failures, stop and show the typing fallback.
        if (event.error === 'network' || event.error === 'service-not-allowed' || event.error === 'language-not-supported') {
            consecutiveSttErrors += 1;
            if (consecutiveSttErrors >= 3) {
                isAutoListen = false;
                showSttFallback("VOICE N/A", event.error);
            }
        }
    };

    recognition.onresult = (event) => {
        const text = event.results[0][0].transcript;
        sendUserText(text);
    };

    recognition.onend = () => {
        // အသံမဖွင့်နေဘူး၊ Auto လည်းဖြစ်တယ်ဆိုရင် မိုက်ပြန်ဖွင့်မည်
        if (!isShuttingDown && isAutoListen && !isPlaying) {
            setTimeout(startMic, 300);
        }
    };

    // Do not start mic until the WebSocket is open (avoids lost first utterance)
    if (socket && socket.readyState === WebSocket.OPEN) {
        startMic();
    }
}

function showSttFallback(statusText, detail) {
    if (sttFallbackNote) {
        sttFallbackNote.classList.remove('hidden');
        sttFallbackNote.innerText = detail
            ? `Voice input unavailable on this device (${detail}) — please type below.`
            : "Voice input unavailable on this device/network — please type below.";
    }
    if (micStatus) micStatus.innerText = statusText;
    setReactorState("offline");
}

function sendUserText(text) {
    if (!text) return;
    userTextDisplay.innerText = text;
    jarvisTextDisplay.innerText = ""; // Clear old response

    setReactorState("processing");
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "text", text: text }));
    } else {
        // Don't drop the utterance — deliver it as soon as the socket is back
        pendingText = text;
        setNetStatus("RECONNECTING");
        connectWebSocket();
    }
}

// Text input fallback (mobile-friendly)
window.sendTextInput = () => {
    const text = (textInput.value || "").trim();
    if (!text) return;
    textInput.value = "";
    sendUserText(text);
};
if (textInput) {
    textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendTextInput();
    });
}

function startMic() {
    if (!recognition) return;
    if (isAutoListen && !isPlaying && !isShuttingDown && socket && socket.readyState === WebSocket.OPEN) {
        try { recognition.start(); } catch(e) {}
    }
}

// Manual Toggle for Mic
window.toggleMic = () => {
    if (!speechSupported) return;
    isAutoListen = !isAutoListen;
    if (isAutoListen) {
        consecutiveSttErrors = 0;
        if (sttFallbackNote) sttFallbackNote.classList.add('hidden');
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
            try { if (recognition) recognition.stop(); } catch(e) {} // စကားပြောနေစဉ် မိုက်ပိတ်မည်
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

// --- 5. HOLOGRAM POPUP WINDOWS ---
function createPopup(title, bodyHtml) {
    popupCount += 1;
    const popup = document.createElement('div');
    popup.className = 'hud-popup';
    // Cascade new popups; keep them on-screen on mobile
    const offset = Math.min(popupCount * 28, 140);
    popup.style.top = (60 + offset) + "px";
    popup.style.right = "12px";

    popup.innerHTML = `
        <div class="hud-popup-header">
            <span class="hud-popup-title">${title}</span>
            <button class="hud-popup-close" aria-label="Close">✕</button>
        </div>
        <div class="hud-popup-body">${bodyHtml}</div>
    `;

    popup.querySelector('.hud-popup-close').addEventListener('click', (e) => {
        e.stopPropagation();
        popup.remove();
        popupCount = Math.max(0, popupCount - 1);
    });

    makeDraggable(popup, popup.querySelector('.hud-popup-header'));
    popupLayer.appendChild(popup);
    return popup.querySelector('.hud-popup-body');
}

// Drag popups with mouse or touch (but never when tapping the close button)
function makeDraggable(popup, handle) {
    let startX = 0, startY = 0, baseX = 0, baseY = 0, dragging = false;

    handle.addEventListener('pointerdown', (e) => {
        if (e.target.closest('.hud-popup-close')) return; // let the click through
        dragging = true;
        handle.setPointerCapture(e.pointerId);
        const rect = popup.getBoundingClientRect();
        baseX = rect.left;
        baseY = rect.top;
        startX = e.clientX;
        startY = e.clientY;
        popup.style.right = "auto";
    });
    handle.addEventListener('pointermove', (e) => {
        if (!dragging) return;
        popup.style.left = Math.max(0, baseX + e.clientX - startX) + "px";
        popup.style.top = Math.max(0, baseY + e.clientY - startY) + "px";
    });
    handle.addEventListener('pointerup', () => { dragging = false; });
}

function renderHologram(data) {
    // Tool activity feed stays in the small hologram box
    if (data.action === "render_tool") {
        hologramBox.classList.remove('hidden');
        hologramContent.innerHTML = `<h3 class="text-green-400 font-bold tracking-widest">⚙️ EXECUTING: ${data.data}</h3>`;
        setTimeout(() => { hologramBox.classList.add('hidden'); }, 8000);
        return;
    }

    if (data.action === "render_map") {
        const q = encodeURIComponent(data.data || "Mandalay");
        createPopup("MAP DATA", `<iframe loading="lazy" src="https://maps.google.com/maps?q=${q}&output=embed"></iframe>`);
        return;
    }

    if (data.action === "render_weather") {
        const city = data.data || "Mandalay";
        const body = createPopup("WEATHER", `<p class="text-cyan-200 animate-pulse">Fetching ${escapeHtml(city)} weather…</p>`);
        fetch(`/api/hud/weather?city=${encodeURIComponent(city)}`)
            .then(r => r.json())
            .then(w => {
                if (!w.ok) {
                    body.innerHTML = `<p class="text-red-400">Weather unavailable: ${escapeHtml(w.error || "error")}</p>`;
                    return;
                }
                body.innerHTML = `
                    <div class="hud-weather-temp">${w.temp_c}°C</div>
                    <p class="text-cyan-100 mt-1">${escapeHtml(w.desc)} — ${escapeHtml(w.city)}</p>
                    <div class="mt-2">
                        <span class="hud-badge">Feels ${w.feels_c}°C</span>
                        <span class="hud-badge">Humidity ${w.humidity}%</span>
                        <span class="hud-badge">Wind ${w.wind_kmph} km/h</span>
                    </div>`;
            })
            .catch(() => { body.innerHTML = `<p class="text-red-400">Weather fetch failed.</p>`; });
        return;
    }

    if (data.action === "render_orders") {
        const body = createPopup("ORDER DATA", `<p class="text-cyan-200 animate-pulse">Loading Telegram order data…</p>`);
        fetch('/api/hud/orders?limit=10')
            .then(r => r.json())
            .then(d => {
                if (!d.ok) {
                    body.innerHTML = `<p class="text-red-400">Order data unavailable: ${escapeHtml(d.error || "error")}</p>`;
                    return;
                }
                let html = "";
                if (d.orders && d.orders.length) {
                    html += `<p class="text-cyan-300 font-bold mb-1">📦 JAMMER ORDERS</p><table>
                        <tr><th>#</th><th>Model</th><th>Customer</th><th>City</th><th>Status</th></tr>` +
                        d.orders.map(o => `<tr>
                            <td>${o.id}</td>
                            <td>${escapeHtml(o.jammer_model || "")}</td>
                            <td>${escapeHtml(o.customer_name || "")}</td>
                            <td>${escapeHtml(o.city || "")}</td>
                            <td>${escapeHtml(o.status || "")}</td>
                        </tr>`).join("") + `</table>`;
                }
                if (d.transactions && d.transactions.length) {
                    html += `<p class="text-cyan-300 font-bold mt-3 mb-1">💳 PAYMENTS</p><table>
                        <tr><th>Txn</th><th>Amount</th><th>Product</th><th>Status</th></tr>` +
                        d.transactions.map(t => `<tr>
                            <td>${escapeHtml(t.transaction_id || "")}</td>
                            <td>${escapeHtml(t.amount || "")}</td>
                            <td>${escapeHtml(t.product || "")}</td>
                            <td>${escapeHtml(t.status || "")}</td>
                        </tr>`).join("") + `</table>`;
                }
                body.innerHTML = html || `<p class="text-gray-400">No orders recorded yet.</p>`;
            })
            .catch(() => { body.innerHTML = `<p class="text-red-400">Order data fetch failed.</p>`; });
        return;
    }

    if (data.action === "render_schedule") {
        const body = createPopup("SCHEDULE", `<p class="text-cyan-200 animate-pulse">Loading scheduled tasks…</p>`);
        fetch('/api/hud/schedule')
            .then(r => r.json())
            .then(d => {
                if (!d.ok) {
                    body.innerHTML = `<p class="text-red-400">Schedule unavailable: ${escapeHtml(d.error || "error")}</p>`;
                    return;
                }
                if (!d.jobs || !d.jobs.length) {
                    body.innerHTML = `<p class="text-gray-400">No active schedules.</p>`;
                    return;
                }
                body.innerHTML = `<table>
                    <tr><th>ID</th><th>Task</th><th>Next Run</th></tr>` +
                    d.jobs.map(j => `<tr>
                        <td>${escapeHtml(j.id)}</td>
                        <td>${escapeHtml(j.prompt)}</td>
                        <td>${escapeHtml(j.next_run ? j.next_run.replace("T", " ").slice(0, 19) : "—")}</td>
                    </tr>`).join("") + `</table>`;
            })
            .catch(() => { body.innerHTML = `<p class="text-red-400">Schedule fetch failed.</p>`; });
        return;
    }

    if (data.action === "render_tasks") {
        const body = createPopup("ONGOING TASKS", `<p class="text-cyan-200 animate-pulse">Loading tasks…</p>`);
        fetch('/api/hud/tasks')
            .then(r => r.json())
            .then(d => {
                if (!d.ok) {
                    body.innerHTML = `<p class="text-red-400">Tasks unavailable: ${escapeHtml(d.error || "error")}</p>`;
                    return;
                }
                const lines = (d.tasks_text || "")
                    .split("\n")
                    .map(l => l.trim())
                    .filter(l => l && !l.startsWith("CURRENT ONGOING TASKS"));
                body.innerHTML = lines.length
                    ? lines.map(l => `<p class="py-1 border-b border-cyan-900">${escapeHtml(l)}</p>`).join("")
                    : `<p class="text-gray-400">No ongoing tasks at the moment.</p>`;
            })
            .catch(() => { body.innerHTML = `<p class="text-red-400">Tasks fetch failed.</p>`; });
        return;
    }

    if (data.action === "render_sysinfo") {
        const body = createPopup("SYSTEM VITALS", `<p class="text-cyan-200 animate-pulse">Scanning server…</p>`);
        fetch('/api/hud/sysinfo')
            .then(r => r.json())
            .then(d => {
                if (!d.ok) {
                    body.innerHTML = `<p class="text-red-400">Sysinfo unavailable: ${escapeHtml(d.error || "error")}</p>`;
                    return;
                }
                body.innerHTML = `
                    <div class="mt-1">
                        <span class="hud-badge">CPU ${d.cpu_percent}%</span>
                        <span class="hud-badge">RAM ${d.ram_percent}% (${d.ram_used_mb}/${d.ram_total_mb} MB)</span>
                        <span class="hud-badge">DISK ${d.disk_percent}%</span>
                    </div>`;
            })
            .catch(() => { body.innerHTML = `<p class="text-red-400">Sysinfo fetch failed.</p>`; });
        return;
    }

    if (data.action === "render_image") {
        createPopup("IMAGE", `<img src="${escapeHtml(data.data)}" alt="hologram image">`);
        return;
    }

    if (data.action === "render_report") {
        createPopup("REPORT", `<p class="whitespace-pre-wrap">${escapeHtml(data.data)}</p>`);
        return;
    }

    // Unknown widget: fall back to the small hologram box
    hologramBox.classList.remove('hidden');
    hologramContent.innerHTML = `<h3 class="text-green-400 font-bold tracking-widest">${escapeHtml(data.action)}: ${escapeHtml(data.data)}</h3>`;
    setTimeout(() => { hologramBox.classList.add('hidden'); }, 15000);
}

function escapeHtml(value) {
    return String(value == null ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

// --- 6. UI EFFECTS ---
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

// Clock
setInterval(() => {
    document.getElementById('clock').innerText = new Date().toLocaleTimeString();
}, 1000);
