# Jarvis single-VPS runbook

## Start
```bash
cd /root/jarvis-backup
source venv/bin/activate
cp -n .env.example .env   # then fill secrets
python main.py
```

## Systemd (Jarvis)
```bash
sudo cp deploy/jarvis.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jarvis
```

## Health
- HTTP: `GET /health` (local: `curl -s http://127.0.0.1:8000/health`)
- Watchdog: `python watchdog.py` (TCP port check + soft restart; never touches git)

## Tests
```bash
python tests/smoke_tests.py
# or
pytest tests/smoke_tests.py -q
```

## Active roles
ceo, sysadmin, researcher, deep_researcher, business_manager, secretary

---

## Voice HUD on jarvis.thukha.online

Public path: **Chrome/Edge → Cloudflare Access → Cloudflare Tunnel → Jarvis on 127.0.0.1:8000**.

App-layer `/ws/voice` stays unauthenticated on purpose; lock down with Cloudflare Access + Origin allowlist + localhost bind.

### 1. Origin / bind (.env)
```bash
HOST=127.0.0.1
PORT=8000
VOICE_ALLOWED_ORIGINS=https://jarvis.thukha.online
```
Restart Jarvis after changing `.env`:
```bash
sudo systemctl restart jarvis
curl -s http://127.0.0.1:8000/health
```

### 2. Install cloudflared
```bash
# Example (Debian/Ubuntu amd64) — check Cloudflare docs for current package URL
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
cloudflared --version
```

### 3. Create tunnel + DNS
```bash
cloudflared tunnel login
cloudflared tunnel create jarvis-web
# Note the Tunnel UUID printed by create

sudo mkdir -p /etc/cloudflared
sudo cp deploy/cloudflared.yml /etc/cloudflared/config.yml
# Edit /etc/cloudflared/config.yml: replace TUNNEL_UUID and credentials-file path

cloudflared tunnel route dns jarvis-web jarvis.thukha.online
```

DNS for `jarvis.thukha.online` must be **proxied** (orange cloud) on Cloudflare.

### 4. Systemd (cloudflared)
```bash
# If binary is not at /usr/local/bin/cloudflared, edit ExecStart in the unit
sudo cp deploy/cloudflared.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared --no-pager
```

Do **not** open VPS ports 80/443 for this setup — the tunnel is the only ingress.

### 5. Cloudflare Access (Zero Trust)
1. Zero Trust → Access → Applications → Add self-hosted app.
2. Application domain: `jarvis.thukha.online`, path `*` (covers `/` and `/ws/voice`).
3. Policy: Allow your email(s) only (Google / One-time PIN).
4. Session duration: 24h is fine. Same-origin WebSocket sends the `CF_Authorization` cookie automatically.

### 6. Voice smoke test
1. Open `https://jarvis.thukha.online` in **Chrome or Edge** → complete Access login.
2. Tap **TOUCH TO INITIALIZE SYSTEM** → grant microphone.
3. Speak Burmese → expect transcript, streamed Jarvis text, then `my-MM-ThihaNeural` TTS audio.
4. Leave idle ~2 minutes → socket should stay up (server JSON ping every 20s).
5. Kill/restart tunnel briefly → HUD shows RECONNECTING and recovers.

Firefox/Safari: init screen shows Chrome/Edge requirement (browser STT only).

### Outbound requirements (VPS)
- Gemini: `generativelanguage.googleapis.com`
- Edge TTS: `speech.platform.bing.com` (no extra API key)
