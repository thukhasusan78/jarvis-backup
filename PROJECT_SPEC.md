# PROJECT SPEC: Jarvis v2.1.0 — Secretary Vision, VIP Sales, Jammer Orders, Hardening

> **Status: see "Production Hardening Round (2026-08-13)" directly below for the current state of the codebase.** Older "QA result" / test-count lines in dated sections are historical records of those rounds, not the current state. This file (formerly `spec.md`) is the single source of truth for future agents. The sections under "Historical record" reflect the committed codebase.
>
> ⚠️ **INCIDENT (2026-08-13):** `watchdog.py`'s hard-recovery (`git fetch` + `git reset --hard origin/new-updates` + `git clean -fd`) fired and **wiped all uncommitted round-2 work** (jammer antenna model, proactive-message history persistence, prompt updates, test updates, this file's rename). Those changes are re-listed below as requirements and have been **re-applied** (see ✅ markers). Round-1 hardening (committed) survived.

## 🛡️ Production Hardening Round (2026-08-13) — ✅ DONE

Full architecture audit → 5-phase hardening. **62/62 smoke tests passing, compileall clean, 26 tools load with zero import errors.**

### H1. Security boundaries — ✅
- `Config.validate_required()` fails startup closed when `ALLOWED_USER_ID`/`TELEGRAM_TOKEN`/`GEMINI_API_KEYS` are missing (`config.py`, called from `main.py` lifespan). Telegram `/start`, `/help`, and message handlers all fail closed when the owner ID is unset.
- **Runtime role enforcement:** `tool_registry.execute_tool(tool_name, caller_role=...)` now blocks disallowed roles at execution time, not just at declaration. Both agent loops (`core/agent.py`, `interfaces/userbot/secretary_brain.py`, `core/brain.py` streaming) pass their role.
- `shell_exec` runs **argv-only** (`shell=False`, `shlex.split`); shell metacharacters (pipes/redirects/substitution) rejected; destructive binaries (`rm`, `dd`, `shutdown`, …) blocked; protected paths only readable via a read-only command allowlist.
- `backup_code` uses argv git commands; never interpolates commit messages into shell; unstages `.env`/sessions/keys before committing.
- `manage_file` blocks read/write/list of `.env`, `*.session`, `*.pem`, `*.key`, `.ssh/` etc. via `core/security.py::is_secret_path`.
- `manage_migration` zip **excludes secrets**; SFTP uses `RejectPolicy` + `~/.ssh/known_hosts` (no AutoAdd). `ssh_remote_exec` same policy; passwords never logged.
- `/health` endpoint added to `main.py`. Voice pipeline auth explicitly out of scope this cycle.

### H2. Sales workflow correctness — ✅
- **Single source of truth:** `core/business_catalog.py` holds VIP price (35,000), jammer models/prices (2-Ant 140,000 / 3-Ant 190,000), Mandalay deposit (10,000), and `PRODUCT_CAPTIONS`. `Config.VIP_SUBSCRIPTION_PRICE_MMK` imports from the catalog.
- **VIP vs jammer separation:** new event `VERIFY_AND_FULFILL_JAMMER` (verify → `record_jammer_order`); VIP path unchanged (`VERIFY_AND_FULFILL_SUBSCRIPTION` → verify → invite → reply). Prompts forbid cross-product tool use.
- **Structured event payloads:** `publish_event` accepts `product`, `chat_id`, `image_path`, `customer_name`, `jammer_model`, `phone`, `city`, `address`, `payment_type`, `min_amount`, `end_goal` (legacy free-text `data` still supported). Target agents restricted to an allowlist. Business events are validated for required fields before publishing.
- **Idempotent payment lifecycle:** ledger `PENDING → VERIFIED → FULFILLED|FAILED` (`memory/business_storage.py`). `verify_payment` records VERIFIED only after all checks; `generate_vip_invite_link(payment_txn_id=...)` marks FULFILLED on success; a VERIFIED-but-unfulfilled txn can be re-fulfilled without re-accepting the receipt. Duplicate inserts return False (race-safe).
- **Jammer orders persisted:** new `jammer_orders` table; `record_jammer_order` is `owner_role="business_manager"` only (Secretary can no longer call it directly); receipts include `Order #`.
- **Customer-messaging adapter:** `interfaces/customer_messaging.py` — business tools no longer touch `sys.modules` directly.

### H3. VIP customer-name & invite fixes (live incident 2026-08-13) — ✅
- **Incident:** Secretary asked the customer for a name mid-VIP-flow (first event omitted `customer_name`); separately `generate_vip_invite_link` failed with `Peer id invalid: -1003824267490`.
- **Fixes:** `SecretaryBrain.reply` injects `chat_id` + Telegram display name into business `publish_event` calls; `publish_event` derives `Telegram Customer {chat_id}` fallback; `verify_payment`/`generate_vip_invite_link` no longer hard-require `customer_name`; prompts state a separate name is never needed for VIP.
- **Peer resolution:** `customer_messaging.resolve_chat()` warms the Pyrogram dialog cache before `create_chat_invite_link`; `secretary_main` preflights `VIP_CHANNEL_ID` at startup and logs the resolved channel title. Note: "Peer id invalid" means the userbot session has never seen that channel — the userbot account must be a member/admin of the VIP channel. Restricted-content settings do NOT block invite creation.
- Smoke tests cover: omitted-name VIP event, deterministic fallback label, dialog-cache invite resolution.

### H4. Event & concurrency reliability — ✅
- **Broker claim model:** `core/message_broker.py` — `PENDING → IN_PROGRESS → COMPLETED|FAILED|DEAD` with `attempts`, `max_attempts` (default 3), `lease_until`, `last_error`, timestamps. `claim_next_event()` uses `BEGIN IMMEDIATE` for atomic claims; expired leases are reclaimed; exhausted/poison events go DEAD instead of looping.
- **Orchestrator:** completes events only after the agent finishes; bounded concurrency (semaphore=3); nested prompt resolution (`core/prompts/business/secretary.md` etc.); API/system errors retry via the broker.
- **SQLite WAL + busy_timeout** via `core/db.py::connect_db` — used by broker, business ledger, chat storage, and movie repository.
- **Secretary state persisted:** VIP mute, per-chat last-image path, and human-activity timestamps now survive restarts (`secretary_state` table; in-memory dicts are only a cache).
- `workspace/square.md` is appended + trimmed (32KB) instead of deleted on every owner message.

### H5. Quality gates & maintainability — ✅
- `tests/smoke_tests.py`: 62 offline checks (guards, captions, role enforcement, broker claim/retry/poison, ledger lifecycle, structured events, config fail-closed, manual-movie schema).
- CI: `.github/workflows/ci.yml` (compile + ruff + smoke). `ruff.toml` added. `.gitignore` fixed to allow `.github/*.yml`.
- `requirements.txt` fully pinned; `lancedb`/`sentence-transformers` removed (Chroma + Gemini embeddings are the live path).
- `.env.example`, `deploy/jarvis.service`, `deploy/RUNBOOK.md`, `migrations/` (canonical schema docs 001/002).
- Shared Gemini client/retry in `core/gemini_client.py` (used by both brains). Movie DB extracted to `core/movie_repository.py`. `manual_movie_trigger` uses proper `get_parameters()` (Pydantic `args_schema` bug class eliminated). Hologram tool moved to `tools/ui/` (now registered). Empty `core/evolution.py` deleted.

### Known remaining risks (accepted / future work)
- Voice WebSocket (`/ws/voice`) remains **unauthenticated at the app layer** on purpose. Production exposure is via **Cloudflare Access** on `jarvis.thukha.online` + Tunnel to `127.0.0.1:8000` + optional `VOICE_ALLOWED_ORIGINS` Origin check. Do not publish the HUD without Access.
- Streaming brain does not yet feed tool results back into Gemini for a spoken follow-up; hologram tool JSON is only partially wired to the HUD.
- Browser STT only (Chrome/Edge Web Speech API, `my-MM`); no server-side Whisper / Safari support yet.
- `custom_skills/` tools default to `owner_role="ceo"` (was "all").
- Receipt freshness window (2h) is enforced by Gemini-extracted time — a genuinely old receipt is correctly rejected (observed 2026-08-13: 13:49 receipt submitted ~16:42).
- Vision quota is consumed before the Gemini call completes (failed analyses still count).

---

## 🎙️ Voice HUD deployment (2026-08-15) — ✅ CODE DONE / ops checklist in RUNBOOK

Ship the existing JARVIS HUD (`interfaces/web/`) and `/ws/voice` pipeline to **https://jarvis.thukha.online**.

### Code
- WS keepalive: server JSON `ping` every 20s; client replies `pong`; exponential reconnect in `interfaces/web/static/js/app.js`.
- Origin allowlist: `Config.VOICE_ALLOWED_ORIGINS` / `is_voice_origin_allowed()` in `interfaces/voice/stream_engine.py`.
- Bind default: `HOST=127.0.0.1` (tunnel-only ingress). Documented in `.env.example` + `deploy/RUNBOOK.md`.
- Chrome/Edge-only STT notice on the init screen when Web Speech API is missing.
- Deploy templates: `deploy/cloudflared.yml`, `deploy/cloudflared.service`.

### Ops (manual — Cloudflare dashboard + VPS)
1. Set `.env`: `HOST=127.0.0.1`, `VOICE_ALLOWED_ORIGINS=https://jarvis.thukha.online`; restart `jarvis`.
2. Install/configure `cloudflared` tunnel → `http://127.0.0.1:8000`; DNS `jarvis.thukha.online` proxied.
3. Cloudflare Access app on `jarvis.thukha.online` path `*`, allow-list owner email(s).
4. Voice test: Chrome → Access login → initialize HUD → mic → Burmese STT → Gemini TTS (`Enceladus`).

Full step-by-step: [`deploy/RUNBOOK.md`](deploy/RUNBOOK.md) § Voice HUD.

### Out of scope this round
- Server Whisper / Gemini Live API native audio / app-level login.

---

## 🦾 Voice HUD 2.0 (2026-08-15, Round 2) — Gemini TTS, popup widgets, mobile fixes

### R10. TTS: edge-tts → Gemini TTS — ⏪ REVERTED (2026-08-15, user decision)
- Gemini TTS (`gemini-2.5-flash-preview-tts`, Enceladus) was implemented but proved unreliable in production: invalid-key 400s, "model tried to generate text" 400s, and empty-content responses. Fixes were applied (R16) but the user chose to **switch back to edge-tts** (`my-MM-ThihaNeural`) — free, no API key, stable Burmese voice.
- Current engine: `interfaces/voice/stream_engine.py::fetch_tts` uses `edge_tts.Communicate(chunk, "my-MM-ThihaNeural")` (MP3 bytes, browser `decodeAudioData`). `Config.VOICE_MODEL` / `Config.VOICE_NAME` are unused leftovers.

### R11. Hologram popup widgets — ✅ DONE
- `tools/ui/hologram_tool.py` now **returns the `hologram_trigger` JSON verbatim** (previously built it but returned a text note that was never rendered).
- `core/brain.py::stream_think` forwards any tool result containing `"hologram_trigger"` verbatim to the browser; other tools still get the generic `render_tool` activity flash.
- New popup layer in the HUD (`interfaces/web/static/js/app.js` `createPopup`): draggable, closable, cascading windows; tool activity stays in the small hologram box.
- Widgets: **map** (Google Maps embed iframe, no API key), **weather** (`/api/hud/weather` → wttr.in), **orders** (`/api/hud/orders` → `jammer_orders` + `transactions` from `workspace/business_ledger.db`), **report**, **image**.
- `interfaces/web/hud_api.py` — new read-only JSON router included in `main.py`; inherits the Cloudflare Access gate.

### R12. Mobile/Android hardening — ✅ DONE
- Visible `NET:` connection status (CONNECTING / SECURE / RECONNECTING) so a stuck socket no longer looks like "READY forever".
- STT error taxonomy: `not-allowed`/`audio-capture`/`aborted` stop auto-restart; `network`/`service-not-allowed`/`language-not-supported` counted — after 3 consecutive failures, auto-listen stops and a fallback note appears **with the actual error name shown** for debugging.
- **Text input fallback** added under the transcript box (works on any browser, sends the same WS payload as STT).
- `visibilitychange` handler resumes AudioContext, re-acquires wake lock, reconnects WS when returning to the tab.
- Screen **wake lock** requested on boot; mobile CSS for popups/transcript.

---

## 🛠️ Voice HUD 2.1 (2026-08-15, Round 3) — Orbit removal, more widgets, server-side STT

### R13. Orbit provider fully removed — ✅ DONE
- Deleted from `config.py` (`ORBIT_API_KEY`, `QA_MODEL_NAME`, `ORBIT_BASE_URL`), `core/gemini_client.py` (`build_client(use_orbit=...)` → plain `build_client()`), `core/brain.py` (`use_orbit` flag, `[PROVIDER: ORBIT]` prompt routing, streaming fallback), `interfaces/userbot/secretary_brain.py` call site, `.env.example`.
- No prompt file contained `[PROVIDER: ORBIT]`. Verified: zero `orbit`/`QA_MODEL` references remain in `*.py`.
- User action (optional): delete the stale `ORBIT_API_KEY=` line from the live `.env`.

### R14. Live-data hologram widgets — ✅ DONE
- `show_hologram` enum extended: `schedule`, `tasks`, `sysinfo` (data payload unused for these — HUD fetches live).
- New endpoints in `interfaces/web/hud_api.py`: `/api/hud/schedule` (APScheduler jobs: id, prompt preview, next run), `/api/hud/tasks` (Sir's ongoing tasks via `memory_controller`), `/api/hud/sysinfo` (psutil CPU/RAM/disk).
- Client renderers: schedule table, task list, vitals badges.
- Say e.g. "show my schedules" / "what tasks are ongoing" / "system vitals" and the popup appears while Jarvis speaks.

### R15. Server-side STT fallback — ⏪ REVERTED (2026-08-15, user decision)
- **Root cause of Redmi Note 13 Pro failure (researched):** Chrome's Web Speech API on some Xiaomi/MIUI/HyperOS builds fails with `network`/`service-not-allowed` because the Google speech service is missing or blocked; this is a device environment issue, not a code bug. HTTPS, mic permission, and disabling display-over-other-apps overlays are prerequisites on the phone.
- A Gemini-transcription push-to-talk fallback was implemented (`{"type":"audio"}` WS message, `_gemini_stt_sync()`, MediaRecorder PTT client) but the **user does not want the STT fallback** — all of it was removed. On unsupported devices the HUD now shows the actual error name plus the typing input (R12 behavior).

### R16. Gemini TTS production fixes — ⏪ MOOT (engine reverted to edge-tts, see R10)
- Live logs exposed three Gemini TTS failure modes: `API_KEY_INVALID` killing a sentence (rotation only retried quota errors), "model tried to generate text" 400 (bare text input), and empty `candidates[0].content` (`'NoneType' object has no attribute 'parts'`). Fixes were written (`_is_invalid_key_error` rotation, read-aloud `TTS_INSTRUCTION`, `_extract_tts_pcm` guards + retry) but the engine was reverted to edge-tts before they mattered. If Gemini TTS is ever revisited, this note lists the required hardening.

### R17. Voice answers directly — tool feedback loop, no Telegram detour — ✅ DONE
- **Incident (2026-08-15 live log):** a voice news query took ~8s and the answer arrived via **Telegram**, not voice: the voice brain (role `ceo`) had no `search_web` access (`tools.web` → `researcher`), so it called `delegate_task` → researcher → `WORKFLOW_COMPLETED` → CEO agent → `report_to_sir`. Holograms never appeared because nothing told the model to call `show_hologram`, and tool results were never fed back for a spoken reply.
- **Fixes:**
  - `core/brain.py::stream_think` now runs a **tool feedback loop** (max 3 rounds): function-call parts are echoed back as `model` content, results go back as `function_response` parts, and the follow-up answer keeps streaming (truncated to 4000 chars/result).
  - `VOICE_HUD_DIRECTIVE` injected into every voice prompt: short spoken Burmese, **never delegate_task / report_to_sir**, call `search_web` directly for news, call `show_hologram` when Sir asks to *see* something + one-line spoken summary.
  - `core/registry.py`: `tools.web` tools are now visible to **ceo** as well (same special-case as `deep_researcher`). Telegram-side impact: CEO *can* now search directly instead of delegating light lookups — accepted.
- **Expected latency:** simple turns ~2-4s (LLM + first-chunk TTS at first comma); search turns ~5-7s (one search + summary), instead of the ~25s delegate→orchestrator→Telegram chain.

### R18. Voice session hardening — deterministic tool filter, memory, popup close fix — ✅ DONE
- **Delegation persisted** after R17 because `core/prompts/ceo.md` contains hard "CEO PROTOCOL" system-instruction rules (news MUST go to researcher) that overruled the user-prompt directive. Fix is now deterministic: `JarvisBrain(role="ceo", voice_mode=True)` strips `delegate_task`, `report_to_sir`, `publish_event` from the tool declarations (`VOICE_BLOCKED_TOOLS`) — the model *cannot* delegate on voice; Telegram path (`voice_mode=False`, default) is unchanged.
- **Conversation memory:** the voice WS endpoint kept calling `stream_think(user_text)` with the default empty history. Now each connection keeps the last 12 turns (`Sir: … / Jarvis: …` pairs) and passes them via `chat_history`.
- **Popup close button** was dead on touch: the header drag handler's `setPointerCapture` swallowed the ✕ click. Drag now ignores taps on the close button (`e.target.closest('.hud-popup-close')`), the click handler stops propagation, and the button grew to 28px for touch.

### R19. Mobile connection hygiene — fast reconnect, dead-socket watchdog — ✅ DONE
- **Incident:** "10s latency" reports persisted even though the server pipeline measured **1.9s end-to-end** (Gemini stream 0.9s + edge-tts 0.6s, verified via live WS probe). Log analysis showed the slow turns always followed a silent reconnect — the phone spoke into a half-open socket, waited, reconnected, replayed.
- **Fixes in `interfaces/web/static/js/app.js` (v23):**
  - Reconnect backoff capped at **3s** (was 15s), starting at 500ms.
  - **Dead-socket watchdog:** server pings every 20s; if the client hears nothing for 45s on an "open" socket (mobile network switch / tab suspend), it force-closes and reconnects.
  - **Utterance queue:** text spoken while the socket is down is held in `pendingText` and flushed on `onopen` instead of being dropped.
  - `visibilitychange` now treats a socket idle >30s as dead (it can *look* OPEN after suspend) and reconnects immediately on tab return.
- No server restart needed for these (static files served live); users must hard-refresh once to get v23.

---
- Voice: "မန္တလေး မြေပုံ ပြပါ" (map), "ရာသီဥတု ပြပါ" (weather), "schedule စာရင်း ပြပါ", "orders ပြပါ", "system vitals ပြပါ".
- Browser console (HUD open): `renderHologram({action:"render_weather", data:"Mandalay"})` — popup should appear instantly; same for `render_schedule`, `render_orders`, `render_tasks`, `render_sysinfo`.
- APIs directly: `curl -s http://127.0.0.1:8000/api/hud/weather?city=Mandalay` (also `/schedule`, `/tasks`, `/orders`, `/sysinfo`).

---

## 🎬 Iron Man JARVIS — roadmap to near-parity (proposed, not yet approved)

Ordered by impact/effort. Items 1–3 are the biggest "feels like the movie" wins.

1. **Barge-in / full duplex** — Gemini Live API native audio (`Config.VOICE_MODEL` family) so Sir can interrupt Jarvis mid-sentence, like the films. Replaces the chunked STT→LLM→TTS pipeline on the WS with one bidirectional audio stream.
2. **Wake word** — "Jarvis" hotword (Picovoice Porcupine or openWakeWord server-side) so no touch-to-init is needed on a dedicated device; falls back to tap on browsers.
3. **Proactive briefing on boot** — on HUD connect, server pushes a greeting card: time, weather, unread business orders/payments count, scheduler jobs due today (data already exists in `core/scheduler.py` + `business_storage`).
4. **Tool activity feed** — persistent side rail listing every tool call as it happens (extends the `render_tool` flash into a scrolling log; zero backend change needed, the events already stream).
5. **Audio-reactive reactor** — Web Audio `AnalyserNode` drives reactor ring scale/glow with TTS amplitude; mic level drives it while listening.
6. **Server-side STT (Whisper or Gemini transcription)** — unlocks Safari/Firefox and non-Google Android ROMs (e.g. Redmi/HyperOS where Web Speech is broken). Note: a Gemini-PTT version was built (R15) then removed per user decision; revisit only if requested.
7. **Face/vision check-in** — optional webcam snapshot on boot sent through `perception/vision_analyzer.py` for "Welcome back, Sir" style contextual greetings (reuse existing face engine).
8. **PWA packaging** — manifest + service worker + add-to-homescreen icon; offline shell shows "SYSTEM OFFLINE" screen when tunnel is down.
9. ~~HUD system telemetry~~ — ✅ DONE (R14 `/api/hud/sysinfo`). Remaining upgrade: always-on corner panel with live psutil bars.
10. **Voice biometrics** — speaker-recognition gate before sensitive tools (on top of Cloudflare Access).
11. **Conversation memory panel** — scrollable transcript history from `memory/sql_storage.py` chat history.
12. **Notification channel** — business events (new VIP payment, jammer order) push a hologram alert to any connected HUD via a broadcast WS hub.

### Intentionally diverging from the movie
- No always-listening on the open internet: Access gate + origin allowlist stay mandatory.
- No destructive automation without Telegram confirmation (existing `shell_exec`/firewall guards remain).

---

## 🚨 Required Changes (2026-08-13)

### R0. Re-apply round-2 changes lost to watchdog hard recovery — ✅ DONE
1. **Proactive Bot-API messages must persist to chat history** — after every successful proactive Bot-API send to `Config.ALLOWED_USER_ID`, save via `memory_controller.add_chat_message(user_id, "model", text)` (the `report_to_sir.py` pattern). Applied to: `tools/system/business_tools/jammer_order.py` (order receipt) and `tasks/executor.py` (scheduled-task reports). **Convention for future agents:** ANY tool that proactively messages the Boss via Bot API must also save the message to chat history immediately after a successful send.
2. **Jammer antenna model in order reports** — `record_jammer_order` has a 7th required param `jammer_model` ("2 Antenna" / "3 Antenna"); receipt includes a `📡 Model:` line; `secretary.md` order collection asks for the model and includes `Model: [...]` in the `RECORD_JAMMER_ORDER` event data; `business_manager.md` jammer workflow parses/passes `jammer_model`; `tests/smoke_tests.py` schema test covers 7 params.
3. **`spec.md` renamed → `PROJECT_SPEC.md`** ✅

### R1. Watchdog fix — stop hard recovery — ✅ DONE
- **Requirement:** Remove/disable the hard-recovery block in `watchdog.py` (was: `git fetch origin new-updates`, `git reset --hard`, `git clean -fd`). It overwrote local uncommitted work-in-progress on any watchdog error and caused real data loss.
- **New behavior:** health checks, soft restart (`pkill`/`fuser` + relaunch) and Telegram alerts kept. If soft restart fails → send Sir a **FATAL alert asking for manual intervention** — the git working tree is never touched automatically.

### R2. Image handling optimization — send ALL matching product images — ✅ DONE
- When a customer requests product photos (e.g. the "3 Antennas" jammer), the system sends **all available matching images** in `workspace/products/` instead of a single default. `send_product_image` gained prefix matching (`jammer_3ant` → sends `jammer_3ant.jpg`, `jammer_3ant_2.jpg`, …); `secretary.md` updated to prefer prefix requests.

### R3. Cleanup & de-bloating — remove Creator Team and Playwright Browser — ✅ DONE
- Removed **Creator Team**: `tools/creator_team/` (`parallel_research.py`, `persona_manager.py`, `post_to_channel.py`, `save_research.py`), `creator_manager`/`content_writer` roles + prompts, and all registry/`delegate_task` enum references.
- Removed **Playwright Browser**: `tools/browser/` (`navigator.py`, `session.py`, `visual.py`), `playwright` references, and related role references.
- Verified with codebase search before deletion; compile + registry-load + smoke tests clean after.

### R4. Communication workflow refinement — ✅ DONE
- **Direct chat output:** agents must NOT auto-save intermediate files or task outputs to `workspace/` unless explicitly instructed; outputs go directly through chat.
- **Dynamic Telegram response strategy:** content within Telegram limits → sent as text; exceeding limits → automatically formatted and sent as a file attachment.

### R5. Production-grade QA protocol (mandatory for all future code)
Before finalizing ANY code change, enforce three-stage validation:
1. **Test** — validate the code functions as intended against the business logic (run `tests/smoke_tests.py` + targeted checks).
2. **Verify** — check edge cases and robustness (empty inputs, API failures, quota limits, missing files).
3. **Audit** — security and best-practice audit: vulnerabilities, anti-patterns, secrets handling, injection/traversal risks — production readiness.

**QA result for R0–R4 (2026-08-13):** Test ✅ (`compileall` clean, registry loads 25 tools with zero import errors, **21/21 smoke tests passing** incl. new prefix-matching cases) · Verify ✅ (no lingering `creator_*`/`web_surfer`/`playwright` references in code, prompts, or requirements; watchdog contains no git commands) · Audit ✅ (traversal guard precedes prefix resolution; no circular imports; over-limit responses use in-memory `BytesIO`, no temp files; no secrets touched).

## 🚨 Required Changes (2026-08-13, Round 2 — Jammer price/model mix-up)

**Incident:** A customer received all 3 jammer photos mixed together (Secretary passed the bare prefix `jammer`, which prefix-matched both models), then asked "ဒါကစျေးဘယ်လောက်လဲ" ("how much is THIS?") as a **reply-quote to the 3-Antenna photo**. The bot answered 140,000 Ks — the **2-Antenna price** — because (a) photos carried no identifying captions and (b) reply-quote context was never fed to the brain. The same customer later placed an order **without stating a model**, and the Secretary guessed "2 Antenna" in `record_jammer_order`.

### R6. Reply-quote context capture — ✅ DONE
- `interfaces/userbot/plugins/p_secretary.py`: when an incoming message has `message.reply_to_message`, append a SYSTEM note to `user_text` before it reaches the brain:
  - Quoted message has text/caption → `[SYSTEM: Customer is replying to (quoting) a previous message. Quoted message text/caption: "..."]` with an instruction to use it to resolve references like "ဒါ" / "this one".
  - Quoted message is caption-less media → note that the exact photo is unknown and the Secretary should ask for clarification rather than guess.
- No extra API calls — caption matching only (relies on R7 captions).

### R7. Self-describing product photos — ✅ DONE
- `tools/system/business_tools/send_product_image_tool.py`: new `PRODUCT_CAPTIONS` prefix→caption mapping (`jammer_2ant*` → `📡 2 Antenna Jammer — 140,000 Ks`, `jammer_3ant*` → `📡 3 Antenna Jammer — 190,000 Ks`). Every photo sent gets a per-file caption (explicit `caption` arg overrides; unknown files fall back to the filename).
- ⚠️ **Maintenance note:** these captions embed the DEFAULT prices. If prices change (live business knowledge / admin reply extraction), update `PRODUCT_CAPTIONS` too — it is intentionally static and offline.

### R8. Secretary prompt hardening (`core/prompts/business/secretary.md`) — ✅ DONE
1. **Model-specific photo prefixes:** always use `jammer_2ant` or `jammer_3ant`; the bare `jammer` prefix is allowed ONLY when the customer explicitly asks to see both models.
2. **Ambiguous price questions:** if no quoted-photo SYSTEM context identifies the model, quote BOTH prices (2 Antenna 140,000 / 3 Antenna 190,000) — never guess. If a quoted-caption SYSTEM note is present, answer for that model.
3. **🛑 No model, no order:** never `publish_event` a `RECORD_JAMMER_ORDER` until the customer has explicitly stated the model (2 Antenna or 3 Antenna) in text. If missing, ask first — do not infer from photo history.

### R9. Verification — ✅ DONE
- `tests/smoke_tests.py`: new offline checks — caption mapping resolves per file (`_default_caption`), prefix `jammer` resolves to all 3 files with correct per-model captions (mocked userbot `send_photo`), and unknown files fall back to filename captions.
- `python -m compileall` clean; full smoke suite passing.

---

## Historical record (implemented & verified)

## Project explanation (context for implementer)

`jarvis-backup` is "Jarvis" v2.1.0, a personal AI agent for Sir (Thu Kha Su San), written in Python/FastAPI with Gemini as the LLM. Burmese language throughout prompts and customer-facing text.

- **Entry:** `main.py` FastAPI lifespan starts APScheduler, admin bot (`interfaces/telegram_bot.py`), orchestrator (`core/orchestrator.py`), and the userbot Secretary (`interfaces/userbot/secretary_main.py`).
- **Config:** `config.py` — model names, round-robin `GEMINI_API_KEYS` via `Config.get_next_api_key()`, Pyrogram creds, ChromaDB/SQLite paths.
- **Secretary flow:** `plugins/p_secretary.py` handles incoming DMs. Photos are downloaded to `workspace/temp_media/` and passed to `perception/media_receiver.py::process_incoming_image()`, which runs **both** the local face engine (`perception/face_engine.py`) **and** Gemini deep vision, then hands the brain (`interfaces/userbot/secretary_brain.py`) a context string containing `Local Face Analysis:` and `Gemini Vision Analysis:` — so the Secretary can answer questions about what is actually in the image.
- **Deep vision** lives in `perception/vision_analyzer.py::analyze_image_with_gemini()` and is wired to both `media_receiver.py` (every inbound Secretary photo) and `tools/system/business_tools/payment_verifier.py` (owner_role `business_manager`, invoked via `publish_event` delegation).
- **Business:** Secretary sells **Telegram VIP channel subscriptions (35,000 MMK)** — payment is verified, then `vip_invite_tool.py` (`generate_vip_invite_link`, role `business_manager`) issues a one-time invite link via the userbot API — and Bluetooth jammers (`jammer_order.py`). It can also send product photos via `send_product_image_tool.py` (`send_product_image`). VPN/Marzban sales were removed (see Task 3). Payment anti-fraud: `payment_verifier.py` extracts transaction_id/amount/recipient via Gemini vision, enforces amount ≥ `Config.VIP_SUBSCRIPTION_PRICE_MMK` (35000), 2-hour freshness, checks duplicate ledger in `memory/business_storage.py` (`workspace/business_ledger.db`).
- **Roles:** Remaining roles: `ceo`, `sysadmin`, `researcher`, `deep_researcher`, `business_manager`, `secretary`. `delegate_task` enum: `["sysadmin", "researcher"]`. Creator Team / browser / SE Team / VPN worker have been removed.
- **Event delegation:** `core/message_broker.py` (SQLite `workspace/message_broker.db` with claim/lease/retry) + `core/orchestrator.py` pick up PENDING events, claim them to IN_PROGRESS, and spawn `JarvisAgent(role=target_agent)` with prompt from `core/prompts/<role>.md` (nested prompts supported). Events are COMPLETED only after successful agent execution.
- **Tools:** auto-discovered by `core/registry.py` walking `tools/`; role-gating via `owner_role` attribute and module path rules.

## Goals (user-approved)

1. **Option A — inline vision in Secretary pipeline** so the Secretary can read customer-sent images and reply with a relevant solution.
2. **Remove the SE Team** (never used) and other unnecessary features.
3. **Remove VPN sales**; replace with **Telegram VIP subscription channel sales: 35,000 MMK entry fee**. Keep payment-verify workflow; on success generate a **one-time invite link** via the **userbot API** (`create_chat_invite_link` with `member_limit=1`), channel ID from `.env` (`VIP_CHANNEL_ID`).
4. **Send product images** to customers on request: images live in `workspace/products/`; Secretary sends them through the **userbot session** via a new tool.

---

## Task 1 — Option A: Inline vision for Secretary inbound images

**Files:** `perception/media_receiver.py` (primary), no change needed to `p_secretary.py` photo branch signature.

### Changes
- ✅ **DONE** — `perception/media_receiver.py` now calls `analyze_image_with_gemini` with the business prompt, rebuilds the context as `[SYSTEM: ... Local Face Analysis: ... Gemini Vision Analysis: ...]`, degrades to `unavailable` on any vision error (string starting with `❌`/`⚠️` or exception), keeps the 24h `_delete_file_later` unchanged, and stays non-blocking.
- ✅ **DONE** — `tools/perception/vision_tool.py` CRITICAL RULE 1 updated: `[Local AI Vision Analysis]` → `[Local Face Analysis]` so the instruction still matches the new context format.
- ✅ **DONE** — `core/prompts/business/secretary.md` extended (see *Vision-context prompt fix* below).

### Vision-context prompt fix (added after live test)
Live test exposed a prompt-level bug: even with a correct `Gemini Vision Analysis` in context, the Secretary ignored it and parroted Jammer marketing copy (because `secretary.md` had no "trust the vision result" rule and the Jammer FAQ contained the exact sentence the model echoed). Fix applied to `core/prompts/business/secretary.md`:
- Added `🖼️ [VISION CONTEXT INTERPRETATION - အရေးကြီးဆုံး]` section: tells the model that when a `[SYSTEM: User uploaded an image...]` block is present it must answer based on `Gemini Vision Analysis:` literally, never assume the photo is our product, handle `unavailable` gracefully, and reply in 1-2 short natural Burmese sentences (e.g. "ဒါက EMO AI robot လေးပါခင်ဗျာ။").
- Time-awareness bullet no longer mentions VPN ("Continue assisting customers ... even at night").
- Removed the entire VPN sales-workflow subsection (price 5000 MMK, `VERIFY_AND_FULFILL_VPN`, `vless://` delivery) ahead of Task 3; the workflow preamble now reads: **"You handle Bluetooth Jammer Sales autonomously..."** and includes a guard: *"If the customer sends a photo that is NOT a payment receipt — FIRST answer what is actually in the image ... only proceed to sales flow if the customer explicitly asks to buy."*
- Jammer section unchanged.

### Notes / risks
- Each inbound photo now costs one extra Gemini call (in addition to payment_verifier's later call for receipts). Acceptable per user's Option A choice.
- Quota errors are handled downstream by `Config.get_next_api_key()` rotation in `vision_analyzer` (single key per call — acceptable).
- ~~Code-side Task 3 items (`marzban_tool.py`, `vpn_worker` role-gating, `VERIFY_AND_FULFILL_VPN` event path) still exist~~ — **obsolete**: Task 3 has since been fully implemented; all VPN/Marzban code and event paths are removed (verified: no `marzban`/`vpn_worker`/`VERIFY_AND_FULFILL_VPN`/`vless` references remain in live code).

## Task 2 — Remove SE Team and unused features

> ✅ **DONE** — verified: all six SE prompt files are gone from `core/prompts/` (current: `ceo.md`, `sysadmin.md`, `creator_manager.md`, `researcher.md`, `deep_researcher.md`, `content_writer.md`, `web_surfer.md`, `system.md`, `business_manager.md`, `business/secretary.md`); `ceo.md` has no `se_manager` references; `delegate_task.py` enum = `["creator_manager", "sysadmin", "web_surfer"]`; `interfaces/userbot/business_context.py` deleted; no live-code references to removed roles.

### Delete prompt files
- `core/prompts/se_manager.md`
- `core/prompts/planner.md`
- `core/prompts/coder.md`
- `core/prompts/frontend_coder.md`
- `core/prompts/qa_tester.md`
- `core/prompts/deployer.md`

(Keep: `ceo.md`, `sysadmin.md`, `creator_manager.md`, `researcher.md`, `deep_researcher.md`, `content_writer.md`, `web_surfer.md`, `system.md`, `business/secretary.md`; delete `vpn_worker`-related material per Task 3.)

### Update `core/prompts/ceo.md`
- Remove the `se_manager` routing bullet and any references to software-engineering org chart entries. The org chart should list only: `creator_manager` (news/content/channel), `sysadmin` (terminal/server/git), `web_surfer` (browser).

### Update `tools/system/delegate_task.py`
- `agent_role` enum: remove `"se_manager"` → `["creator_manager", "sysadmin", "web_surfer"]`.
- Update description text accordingly.

### Remove unused features (confirmed unused in codebase)
- `interfaces/userbot/business_context.py` — **empty file**, delete.
- Verify no imports reference deleted prompts (grep for `se_manager`, `planner`, `qa_tester`, `frontend_coder`, `deployer` after deletion; `orchestrator.py` reads prompt file dynamically and falls back safely if missing, but there must be no publisher of events targeting deleted roles — see Task 3 for the remaining `business_manager` target).

**Out of scope:** `tools/creator_team/`, browser tools, movie radar plugin — keep (still used by Telegram channels/movie features).

## Task 3 — Replace VPN sales with Telegram VIP subscription (35,000 MMK)

> ✅ **DONE** — verified: `marzban_tool.py` deleted; no `marzban`/`MARZBAN`/`vpn_worker`/`VERIFY_AND_FULFILL_VPN`/`vless` references in live code; `core/registry.py` business_tools role list = `["business_manager", "secretary"]`; `tools/perception/vision_tool.py` `owner_role = ["ceo"]`; `config.py` has `VIP_CHANNEL_ID` and `VIP_SUBSCRIPTION_PRICE_MMK = 35000`; `tools/system/business_tools/vip_invite_tool.py` exists (one-time link via `create_chat_invite_link(member_limit=1)`, `VIP_CHANNEL_ID == 0` guard); `core/prompts/business_manager.md` created; `core/prompts/business/secretary.md` publishes `VERIFY_AND_FULFILL_SUBSCRIPTION` with the specified payload.

### 3a. Delete VPN tooling
- Delete `tools/system/business_tools/marzban_tool.py` (role `vpn_worker`, Marzban API).
- Remove `MARZBAN_URL`, `MARZBAN_USERNAME`, `MARZBAN_PASSWORD` from `.env` (document removal; leave actual env edits to user or implementer with permission).
- Remove `vpn_worker` from any role lists:
  - `core/registry.py` line 75: `assigned_role = ["business_manager", "vpn_worker", "secretary"]` → change to `["business_manager", "secretary"]`.
  - `tools/perception/vision_tool.py` `owner_role = ["ceo", "vpn_worker"]` → `["ceo"]`.
- Update `core/prompts/business/secretary.md`: remove the entire VPN sales workflow section (pricing 5000 MMK, `VERIFY_AND_FULFILL_VPN` event, `vless://` key delivery instructions).

### 3b. Config additions
- `.env`: add `VIP_CHANNEL_ID=<private channel numeric id, e.g. -100xxxxxxxxxx>`.
- `config.py`: add `VIP_CHANNEL_ID = int(os.getenv("VIP_CHANNEL_ID", 0))` and `VIP_SUBSCRIPTION_PRICE_MMK = 35000` (price also stays in RAG-overridable prompt text; constant is for verification of the paid amount).

### 3c. New tool: `tools/system/business_tools/vip_invite_tool.py`
- `BaseTool`, `name = "generate_vip_invite_link"`, `owner_role = "business_manager"`.
- Description: generate a one-time invite link to the VIP channel after payment is verified.
- `execute(customer_name: str)`:
  1. Import the running userbot app from `interfaces.userbot.secretary_main` (`sys.modules.get(...)` same pattern as `reply_customer.py`).
  2. `link = await app.create_chat_invite_link(Config.VIP_CHANNEL_ID, member_limit=1, name=f"vip_{customer_name}")`.
  3. Return `✅ SUCCESS: invite link = <link.invite_link>` or a `❌` error string on failure (not running, no admin rights, etc.).
- Guard: if `VIP_CHANNEL_ID == 0`, return config error immediately.

### 3d. Payment verifier updates (`tools/system/business_tools/payment_verifier.py`)
Keep the anti-fraud pipeline; adjust for subscription:
- Verify `amount` ≥ 35,000 MMK: after JSON parse, compare numeric amount against `Config.VIP_SUBSCRIPTION_PRICE_MMK`; return `❌ Verification Failed: ငွေပမာဏ မလုံလောက်...` if short. (Handle comma-formatted amounts like "35,000" by stripping non-digits.)
- Keep: transaction ID length ≥6, 2-hour freshness, recipient name contains "thu kha su san"/"သုခစုစံ", duplicate-ID check via `is_transaction_exists`, `record_transaction(..., "VERIFIED")`.
- Success message: `✅ SUCCESS: ... VIP channel invite link ထုတ်ပေးနိုင်ပါသည်။` (remove "VPN Key" wording).
- Also fix latent bug: `re.search(r'\{.*\}', ...)` greedy regex can over-capture if AI adds trailing braces; acceptable to keep, but implementer may switch to non-greedy `{.*?}` with DOTALL or a JSON-extraction helper. Low priority.

### 3e. New event type: `VERIFY_AND_FULFILL_SUBSCRIPTION`
- Secretary publishes (replacing `VERIFY_AND_FULFILL_VPN`):
  - `target_agent`: `"business_manager"`
  - `event_type`: `"VERIFY_AND_FULFILL_SUBSCRIPTION"`
  - `data`: `"Image Path: [...]. Chat ID: [...]. Customer username: [...]. Price: 35000 MMK. END-GOAL: Verify payment with verify_payment, then call generate_vip_invite_link, then reply_to_customer with the one-time invite link."`
- ✅ **DONE** — `core/prompts/business_manager.md` created (previously absent; orchestrator fell back to default instruction). It describes: verify receipt via `verify_payment`, on success call `generate_vip_invite_link`, deliver link to customer via `reply_to_customer` (wrap link in `<code></code>`), on failure `reply_to_customer` with the rejection reason. Keep it short.

### 3f. Secretary prompt business section rewrite (`core/prompts/business/secretary.md`)
Replace the VPN section with:

- **PRODUCT: Telegram VIP Channel Subscription — 35,000 MMK** (check `[LIVE BUSINESS KNOWLEDGE]` for price override; default 35000 MMK).
- Payment via KPay/WavePay 09784679389 (Thu Kha Su San); ask for screenshot after transfer.
- On receipt screenshot: immediately `publish_event` → `VERIFY_AND_FULFILL_SUBSCRIPTION` (payload as in 3e).
- On background event containing an invite link (`https://t.me/+...`): `reply_to_customer`, wrap the link in `<code></code>`, mention it's **one-time use only**.
- Keep the Bluetooth Jammer section unchanged.

### 3g. RAG / memory
- No structural change. Existing `business_facts` RAG continues to override price/delivery info. Existing ledger DB schema keeps working (transaction_id/amount/customer_name).

## Task 4 — Send product images when customers ask

> ✅ **DONE** — verified: `tools/system/business_tools/send_product_image_tool.py` exists with the path-traversal guard, file-listing error response, and userbot `send_photo` delivery; `workspace/products/` exists and is populated; `secretary.md` contains the `📸 [PRODUCT PHOTOS]` section.

### 4a. Product storage convention
- Directory: `workspace/products/` (create with `.gitkeep` or at runtime `os.makedirs(..., exist_ok=True)`).
- Naming: `jammer_2ant.jpg`, `jammer_3ant.jpg`, `vip_preview.jpg`, etc. Lowercase, `[a-z0-9_]` names. User populates files manually.
- ✅ **Reality check (resolved 2026-08-12):** the previously non-conforming files `Three Antena 1st.jpg` / `Three Antena 2nd.jpg` have been renamed to `jammer_3ant.jpg` / `jammer_3ant_2.jpg`. Current contents: `jammer_2ant.jpg`, `jammer_3ant.jpg`, `jammer_3ant_2.jpg` — all convention-compliant and synced with the secretary prompt's known-files list.

### 4b. New tool: `tools/system/business_tools/send_product_image_tool.py`
- `BaseTool`, `name = "send_product_image"`, `owner_role` handled by module rule (business_tools → `["business_manager", "secretary"]`).
- Parameters:
  - `chat_id` (INTEGER) — target customer chat (from SYSTEM NOTE).
  - `image_filename` (STRING) — filename inside `workspace/products/` only.
  - `caption` (STRING, optional).
- `execute`:
  1. Sanitize: `os.path.basename(image_filename)`; reject anything containing `..` or path separators (path-traversal guard).
  2. `path = os.path.join("workspace", "products", safe_name)`; return clear error listing available files if missing.
  3. Get userbot app from `sys.modules.get('interfaces.userbot.secretary_main').app` (same pattern as `reply_customer.py`); `await app.send_photo(chat_id, path, caption=caption)`.
  4. Return success string.

### 4c. Secretary prompt addition
Add a section to `secretary.md`:
```
📸 [PRODUCT PHOTOS]:
- If a customer asks to see product photos (e.g. jammer real photos, VIP channel preview), use the `send_product_image` tool.
- Available images will be listed by the tool on error; known files: jammer_2ant.jpg, jammer_3ant.jpg (keep this list in sync when adding products, or rely on tool's error response).
- After sending the photo, continue the conversation naturally (e.g. answer price questions from [LIVE BUSINESS KNOWLEDGE]).
```

## Affected boundaries & data flow summary

Inbound image: `p_secretary.py (photo branch)` → download → `media_receiver.process_incoming_image` (face engine + **new Gemini vision**) → context string → `SecretaryBrain.reply` (+RAG) → reply text. If receipt: brain calls `publish_event` → broker → orchestrator spawns `business_manager` agent → `verify_payment(image_path,...)` (re-reads file within 24h window) → `generate_vip_invite_link` (userbot API) → `reply_to_customer` (userbot sends link).

Outbound product image: brain calls `send_product_image` → userbot `send_photo` from `workspace/products/`.

## Task 1 live-test result & follow-up bugfix

- ✅ Inbound photo → `process_incoming_image` → Gemini vision call succeeded (`🧠 Sending image to Gemini API for deep analysis` log line), 24h delete task intact, reply delivered.
- 🐛 **Bug found:** Secretary replied with Jammer copy-paste for an EMO toy robot photo because `secretary.md` prompted the model to behave as a VPN/Jammer salesperson with no "trust the vision result" rule.
- 🔧 **Fix:** `secretary.md` updated (see Task 1 → *Vision-context prompt fix*). The Secretary now treats `Gemini Vision Analysis:` as ground truth for image questions.
- 📌 No code changes were needed in `secretary_brain.py`; the brain was correctly forwarding the context. The issue was purely a prompt-engineering gap.

## Validation plan (run after implementation — items 1–3 verified passing on 2026-08-12; items 4–7 require live/API access)

1. `python -c "from core.registry import tool_registry; print(sorted(t.name for t in tool_registry._tools.values()))"` — no import errors; `generate_vip_invite_link` and `send_product_image` present; `generate_vpn_key` gone.
2. Grep sweep: `se_manager|vpn_worker|marzban|VERIFY_AND_FULFILL_VPN|vless` returns only intended leftovers (none in live code paths).
3. Compile check: `python -m compileall core interfaces tools perception` passes.
4. Manual dry-run of secretary brain with a fake `[SYSTEM: User uploaded an image... Gemini Vision Analysis: <sample receipt text>]` context to confirm the model replies relevantly and publishes `VERIFY_AND_FULFILL_SUBSCRIPTION`.
5. Unit-smoke `vip_invite_tool` error path with `VIP_CHANNEL_ID=0` → clean config error (no exception).
6. Unit-smoke `send_product_image` traversal guard with `../../etc/passwd` → rejected.
7. Live test (user): send the userbot a receipt image → expect verify → one-time invite link delivered to customer DM; ask "jammer ပုံလေးပြိုင်ပြပေးပါ" → photo received.

## Open questions / user action items

- User must add `VIP_CHANNEL_ID` to `.env` with the private VIP channel's numeric ID, and ensure the **userbot account is an admin** of that channel with invite-link permission.
- User must drop product images into `workspace/products/` using the naming convention above.
- Optional cleanup (user's call): remove `MARZBAN_*` and unused entries from `.env`.

## Post-implementation hardening (2026-08-12)

### Live-test bugfixes (verified in production logs)
1. **`reply_to_customer` role fix** — `tools/system/business_tools/reply_customer.py` had explicit `owner_role = "secretary"`, which bypassed the registry's `business_tools → ["business_manager", "secretary"]` folder rule. The business_manager agent therefore had no way to message customers and improvised with `publish_event` → CEO → `report_to_sir`, delivering VIP verification results to the Boss's Bot chat instead of the customer. Fixed: `owner_role = ["business_manager", "secretary"]`, plus a hard rule in `business_manager.md` never to use `publish_event`/report tools for customer results.
2. **Image path persistence** — Secretary builds chat history from live Telegram history where photos show as `[Media]`, so text-only follow-up turns lost the receipt's File Path ("Image Path: Not available from chat history"). Fixed: `last_image_uploads` tracker in `p_secretary.py` injects the last uploaded image path (24h validity) as a SYSTEM NOTE on subsequent turns.
3. **Tool-result follow-up reply** — after any tool call with no model text, the brain sent a hardcoded "please wait" even for completed actions. Fixed (then superseded by #9 below).
4. **Product filename sync** — `workspace/products/` files renamed to convention: `jammer_2ant.jpg`, `jammer_3ant.jpg`, `jammer_3ant_2.jpg`; `secretary.md` known-files list synced + self-recovery rule (trust tool error listing).
5. **`record_jammer_order` schema fix** — the tool used a LangChain-style Pydantic `args_schema` that `BaseTool.get_declaration()` ignores, so Gemini saw zero parameters and order receipts arrived with all fields `Unknown`. Fixed: proper `get_parameters()`/`get_required()` (6 required fields) + `📦 [JAMMER ORDER WORKFLOW]` section in `business_manager.md`.

### New features
6. **Vision quota (3 images / 24h per customer, receipts exempt)** — `media_receiver.process_incoming_image(chat_id=...)` enforces a sliding 24h window stored in `secretary_state` (`vision_ts_{chat_id}` via `sql_storage.get/set_vision_timestamps`). Over limit → `Gemini Vision Analysis: unavailable (daily image analysis limit reached...)`; face engine and 24h file cleanup still run. `payment_verifier.py` is exempt (revenue-critical). `/clear` resets the counter. `secretary.md` has a `🛡️ [IMAGE ANALYSIS LIMIT]` section with the receipt-exemption rule.
7. **Clickable customer link in order receipts** — `jammer_order.py` receipt renders `💬 Customer: <a href="tg://user?id={chat_id}">{chat_id}</a>`; tapping opens the customer's profile/DM (subject to their Telegram privacy settings).
8. **Customer self-service `/clear`** (also `/new`, `/restart`) — deletes last 100 Telegram messages both sides, wipes SQL `chat_history`, image tracker, and vision quota; confirms in Burmese.
9. **Multi-step tool loop in `SecretaryBrain.reply`** — bounded loop (max 3 iterations): tool results are fed back so the model can chain tools (e.g. send two product photos) or compose the final natural reply; fail-safe message after the cap.

### Clean-code sweep
- `config.py`: removed duplicated ChromaDB block (dead `CHROMA_BUSINESS_PATH`, `CHROMA_COLLECTION`; duplicate `EMBEDDING_MODEL`/`CHROMA_TOP_K`/`CHROMA_DISTANCE_THRESHOLD`).
- Deleted `tools/system/analyzer_tool.py` — permanently broken (imported non-existent `memory.vector_storage`), silently failing at registry load.
- Removed 22 unused imports across 16 files (AST-verified), incl. the dead `pyrogram.raw.types` import block in `p_secretary.py` and redundant inner imports in its photo branch.
- Kept (verified in use): `watchdog.py` (standalone supervisor/health-check script — not imported but operationally useful), `movies_memory.db` (used by `core/movie_engine.py`), `tasks/` package (used by `core/scheduler.py`).

### Tests
- `tests/smoke_tests.py` (offline, no API keys needed): path-traversal guard, VIP config guard, role-gating visibility, vision-quota storage roundtrip/window pruning, jammer-order schema. **19/19 passing** (`venv/bin/python tests/smoke_tests.py`). Registry loads 31 tools with zero import errors; `compileall` clean.

### Future roadmap (discussed, not yet approved)
- Order persistence table (queryable jammer orders, status tracking).
- VIP 30-day membership expiry (scheduled kick job) — business decision needed.
- General per-chat message throttling (extend VIP ghosting logic to all customers).

## Out of scope

- Multimodal brain (Option B) — not chosen.
- Changes to movie radar, voice engine, creator team, browser agent — unchanged.
- Refactoring orchestrator/broker architecture — unchanged.
