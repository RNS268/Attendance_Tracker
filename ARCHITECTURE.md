# ESP32-CAM Face Recognition Attendance System — Architecture

## 1. High-Level System Architecture

### ASCII Diagram — Full System

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           ATTENDANCE SYSTEM — HIGH-LEVEL VIEW                           │
└─────────────────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────┐         Wi‑Fi          ┌──────────────────────────────────────────┐
  │   ESP32-CAM      │◄──────────────────────►│         FLASK BACKEND (Server)           │
  │                  │      HTTPS/HTTP        │                                          │
  │ • OV2640 camera  │   POST /recognize_face │  • SQLite DB (users, embeddings, logs)   │
  │ • PIR/Button     │   GET  /health         │  • face_recognition (embeddings)         │
  │ • LED + Buzzer   │                        │  • bcrypt, sessions, tokens              │
  │                  │                        │  • REST APIs                             │
  └────────┬─────────┘                        └──────────────────┬───────────────────────┘
           │                                                      │
           │  Online recognition: capture → send frame            │
           │  Feedback: JSON response → LED/Buzzer                │
           │                                                      │
           │                                                      │  HTTP (browser)
           │                                                      │
           ▼                                                      ▼
  ┌──────────────────┐                                ┌───────────────────────────────────┐
  │  NO SD CARD      │                                │     WEB DASHBOARD (Browser)       │
  │  (Online Only)   │                                │  • login.html                     │
  │                  │                                │  • register_face.html (camera)    │
  │                  │                                │  • dashboard.html (attendance)    │
  └──────────────────┘                                └───────────────────────────────────┘
                                                                   ▲
                                                                   │
  ┌──────────────────┐         Wi‑Fi          ┌────────────────────┴──────────────────────┐
  │  MOBILE / TABLET │◄──────────────────────►│  Same Flask server (register_face.html)   │
  │  • Camera       │   getUserMedia →        │  Mobile registers new faces via browser   │
  │  • Browser      │   POST /register_face   │  → stored in DB → ESP32 recognizes later  │
  └──────────────────┘                        └───────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|----------|-----------------|
| **ESP32-CAM** | Capture image on PIR/button (or continuous) → POST to `/recognize_face` → parse JSON response → LED/buzzer feedback. |
| **Flask Server** | Auth (login, sessions, API tokens), face registration (store embeddings), face recognition (match embedding), attendance logging, dashboard API. |
| **SQLite DB** | Users (credentials), face_embeddings (name + 128-D vector), attendance_logs (timestamp, name, source). |
| **Web Dashboard** | Login, register new faces (camera capture + upload), view attendance table, logout. |
| **Mobile** | Same web UI. User opens `register_face.html` on phone → camera → capture → upload. |

### Data Flow (ASCII)

```
REGISTRATION (Mobile → Server):
  [Mobile Browser] → getUserMedia(camera) → capture frame → POST /register_face (image + name)
       → Server: extract embedding → store in DB → 200 OK

RECOGNITION + ATTENDANCE (ESP32 → Server):
  [ESP32] → capture JPEG → POST /recognize_face (image + API token)
       → Server: extract embedding → match vs DB → log to DB → return { "name": "..." | "unknown" }
  [ESP32] → LED green (match) / red (unknown)
```

### Control Flow

2. **Trigger**: PIR or button → capture image → POST `/recognize_face`.
3. **Response**: Parse JSON → name or "unknown" → log to SD → LED green/red, buzzer.
4. **Periodic sync**: Scan SD for `synced=0` → POST `/upload_attendance` → set `synced=1`.
5. **Registration**: Admin logs in on phone → `register_face.html` → capture → POST `/register_face`.
6. **Dashboard**: Admin logs in → `dashboard.html` → GET protected data → table of attendance.

---

## 2. Detailed Flowcharts (ASCII + Explanation)

### 2.1 ESP32-CAM Boot & Initialization

```
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌─────────────────┐     fail    ┌──────────────┐
│ Init Serial     │────────────►│ Log error    │
│ (debug)         │             │ restart?     │
└────┬────────────┘             └──────────────┘
     │ success
     ▼
┌─────────────────┐     fail    ┌──────────────────┐
│ Init Camera     │────────────►│ Blink LED red    │
│ (OV2640, JPEG)  │             │ Retry N times    │
└────┬────────────┘             └────────┬─────────┘
     │ success                           │
     ▼                                   │
┌─────────────────┐     fail             │
│ Init microSD    │──────────────────────┘
│ (CSV file)      │
└────┬────────────┘
     │ success
     ▼
┌─────────────────┐
│ Connect Wi‑Fi   │ ───► See flowchart 2.2
└────┬────────────┘
     │
     ▼
┌─────────────────┐     fail    ┌─────────────┐
│ NTP time sync   │────────────►│ Use RTC or  │
│                │              │ boot time   │
└────┬────────────┘             └──────┬──────┘
     │ success                         │
     ▼                                 ▼
┌─────────────────┐             ┌─────────────┐
│ GET /health     │             │ Continue    │
│ (server alive?) │             │ offline     │
└────┬────────────┘             └──────┬──────┘
     │ OK                              │
     ▼                                 ▼
┌─────────────────┐             ┌─────────────────┐
│ Main loop:      │             │ Main loop:      │
│ wait PIR/btn    │             │ wait PIR/btn    │
└─────────────────┘             │ log to SD only  │
                                └─────────────────┘
```

**Steps:**
1. Serial init for debug.
2. Camera init: `esp_camera_init()` with OV2640, JPEG quality (e.g. 10–12).
3. microSD init: mount, create/open `attendance.csv` if missing.
4. Wi‑Fi connect (see 2.2).
5. NTP sync for timestamps; if fail, use RTC or simple counter.
6. GET `/health` to verify server; if fail, continue in offline mode.
7. Enter main loop: wait for PIR or button, then capture → recognize → log.

---

### 2.2 Wi‑Fi Connection & Reconnection with Retries

```
┌─────────────────┐
│ connectWiFi()   │
└────┬────────────┘
     │
     ▼
┌─────────────────────────┐
│ attempt = 0, max = 20   │
└────┬────────────────────┘
     │
     ▼
┌─────────────────────────┐     success
│ WiFi.begin(ssid, pass)  │──────────────────► ┌─────────────┐
└────┬────────────────────┘                    │ return true │
     │                                         └─────────────┘
     │ timeout/fail
     ▼
┌─────────────────────────┐
│ attempt++               │
│ delay(500)              │
│ LED blink               │
└────┬────────────────────┘
     │
     ▼
┌─────────────────────────┐     yes    ┌──────────────────┐
│ attempt < max?          │───────────►│ loop again       │
└────┬────────────────────┘            └─────────┬────────┘
     │ no                                        │
     ▼                                           │
┌─────────────────────────┐                      │
│ return false            │                      │
│ (run offline)           │◄─────────────────────┘
└─────────────────────────┘

RECONNECT (in main loop):
  if (WiFi.status() != WL_CONNECTED) → connectWiFi() → then retry HTTP
```

**Steps:**
1. Set SSID/password, attempt = 0, max attempts (e.g. 20).
2. Call `WiFi.begin`, poll `WiFi.status() == WL_CONNECTED` with timeout (e.g. 10s).
3. On success: return true.
4. On fail: attempt++, delay, blink LED, retry.
5. After max attempts: return false; device runs offline.
6. In loop: if `WiFi.status() != WL_CONNECTED`, call `connectWiFi()` again before HTTP.

---

### 2.3 Face Registration (Mobile Browser → Server)

```
[Mobile]                    [Server]

  │
  │  GET /register_face (or login first → redirect)
  │ ─────────────────────────────────────────────►
  │                           │
  │                           │  Return register_face.html
  │ ◄─────────────────────────────────────────────
  │
  │  User allows camera
  │  navigator.mediaDevices.getUserMedia({ video })
  │
  │  User clicks "Capture"
  │  canvas.drawImage(video) → canvas.toDataURL("image/jpeg")
  │
  │  POST /register_face
  │  Content-Type: multipart/form-data
  │  { image: file, name: "John", token: "..." }
  │ ─────────────────────────────────────────────►
  │                           │
  │                           │  Validate token/session
  │                           │  Load image → face_recognition.face_encodings()
  │                           │  Store (user_id, name, embedding) in DB
  │                           │  200 { "status": "ok" }
  │ ◄─────────────────────────────────────────────
  │
  │  Show "Registered successfully"
  │
```

**Steps:**
1. User opens `register_face.html` (after login).
2. Page requests camera via `getUserMedia`.
3. User clicks Capture; frame drawn to canvas, exported as JPEG.
4. Form sends image + name (and auth token/session) to `POST /register_face`.
5. Server validates auth, extracts face encoding, stores in DB, returns 200.
6. UI shows success; user can register another or go to dashboard.

---

### 2.4 Face Recognition & Attendance Marking (ESP32 → Server → SD)

```
[ESP32]                         [Server]

  │
  │  PIR/Button triggered
  │
  │  Capture JPEG (fb)
  │
  │  POST /recognize_face
  │  Authorization: Bearer <API_TOKEN>
  │  Content-Type: multipart/form-data
  │  image: <binary>
  │ ─────────────────────────────────────────────►
  │                              │
  │                              │  Validate token
  │                              │  face_encodings() → query DB
  │                              │  min distance < threshold → name else "unknown"
  │                              │  200 { "name": "..." }
  │ ◄─────────────────────────────────────────────
  │
  │  Parse JSON → name
  │
  │  Append to SD CSV:
  │  timestamp,name,status,synced
  │  e.g. 2025-01-25T10:30:00,John,recognized,0
  │
  │  LED green (known) / red (unknown)
  │  Buzzer beep
  │
  │  [Optional] POST /upload_attendance with unsynced rows
  │ ─────────────────────────────────────────────►
  │                              │
  │                              │  Insert into attendance_logs
  │                              │  Dedupe by (timestamp, name, device_id)
  │                              │  200 { "synced": N }
  │ ◄─────────────────────────────────────────────
  │
  │  Mark rows synced=1 in CSV (or remove)
  │
```

**Steps:**
1. ESP32 captures image, POSTs to `/recognize_face` with API token.
2. Server returns `{ "name": "..." }` or `"unknown"`.
3. ESP32 writes one CSV row: `timestamp,name,status,synced`.
4. LED/buzzer feedback.
5. Optionally, ESP32 sends unsynced rows to `POST /upload_attendance`; server dedupes and stores; ESP32 marks synced.

---

### 2.5 Offline Attendance Logging + Sync When Internet Returns

```
┌─────────────────┐
│ Log attendance  │
│ (from recognize │
│  or manual)     │
└────┬────────────┘
     │
     ▼
┌─────────────────────────┐     yes
│ Wi‑Fi connected?        │─────────────► ┌──────────────────────────┐
└────┬────────────────────┘               │ POST /recognize_face     │
     │ no                                 │ Log to SD: synced=0      │
     ▼                                    │ Maybe POST /upload_attend│
┌─────────────────────────┐               └──────────────────────────┘
│ Log to SD only          │
│ timestamp,name,unknown,0│
│ (no server call)        │
└─────────────────────────┘

SYNC LOOP (periodic or after each log):
┌─────────────────────────┐
│ Read SD CSV             │
│ Find rows synced=0      │
└────┬────────────────────┘
     │
     ▼
┌─────────────────────────┐     no
│ Wi‑Fi connected?        │────────────► ┌─────────────┐
└────┬────────────────────┘              │ Skip sync   │
     │ yes                               │ Try later   │
     ▼                                   └─────────────┘
┌─────────────────────────┐
│ POST /upload_attendance │
│ Body: JSON array of     │
│   {ts, name, status}    │
└────┬────────────────────┘
     │
     ├─ 200 ──► Mark rows synced=1 (or delete)
     │
     └─ 4xx/5xx ──► Keep synced=0, retry later
```

**Steps:**
1. When no Wi‑Fi: always log to SD with `synced=0`.
2. When Wi‑Fi available: optionally call `/recognize_face`; always log to SD; then sync if possible.
3. Sync: read CSV, collect `synced=0` rows, POST to `/upload_attendance`.
4. On 200: mark those rows `synced=1` (or remove).
5. On error: leave `synced=0`, retry on next cycle.

---

### 2.6 Error Handling Flows

```
┌──────────────────────────────────────────────────────────────────┐
│ NO WI‑FI                                                         │
│ → Log to SD only, synced=0. LED blink. Retry connect periodically│
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ NO FACE DETECTED (server)                                        │
│ → Return 200 { "name": "unknown" }. ESP32 logs "no_face", sync.  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ UNKNOWN FACE (distance > threshold)                              │
│ → Return 200 { "name": "unknown" }. ESP32 logs "unknown", red LED│
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ SERVER ERROR (5xx) / NETWORK ERROR                               │
│ → ESP32: log to SD, synced=0. Retry with backoff. LED red.       │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ 401 (invalid token)                                              │
│ → ESP32: stop sending, alert. Check token in config.             │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ CAMERA INIT FAIL                                                 │
│ → Blink LED, retry N times, then restart.                        │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ SD FAIL                                                          │
│ → Skip SD log. Still try HTTP. Alert via LED.                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Browser Camera (getUserMedia)

`register_face.html` uses the **MediaDevices** API:

1. **`navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } })`**  
   Asks the browser for camera access. Works only in **secure contexts** (HTTPS or `localhost`). The user must allow access.

2. **`<video>` + `srcObject`**  
   The stream is attached to a `<video>` element so the user sees a live preview.

3. **Capture**  
   On "Capture", we draw the current video frame to a `<canvas>`, then call **`canvas.toBlob("image/jpeg", 0.92)`** to get a JPEG.

4. **Upload**  
   The blob is sent via **`FormData`** as `image` and **`POST /register_face`** with `name`. The server runs face detection, stores the embedding, and returns success.

---

## Face Recognition (Backend)

- **Library**: `face_recognition` (dlib). `face_encodings(rgb)` returns 128-D float vectors per face.
- **Storage**: Each encoding is stored as BLOB in `face_embeddings` (user_id, name, embedding).
- **Matching**: On `/recognize_face`, we compute one encoding from the image. We compare it to all stored embeddings using **Euclidean distance** (L2 norm). The **threshold** (default `0.55`, env `FACE_MATCH_THRESHOLD`) is the maximum distance for a match; lower = stricter. The closest stored face within threshold wins; otherwise we return `"unknown"`. Cosine similarity is equivalent for normalized vectors; we use L2 for simplicity.

---

## 3–8. Implementation Details

See the rest of the project:

- **Backend**: `backend/app.py`, `backend/requirements.txt`
- **Frontend**: `static/`, `templates/`
- **ESP32**: `firmware/esp32cam_attendance/`
- **Data & security**: `ARCHITECTURE.md` (this file), `DEPLOYMENT.md`
- **Deployment**: `DEPLOYMENT.md`
