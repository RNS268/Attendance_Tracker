# ESP32-CAM Firmware

## State Machine

```
BOOT → INIT (camera, SD, Wi‑Fi, NTP) → IDLE
         │
         └── Wi‑Fi fail → OFFLINE (periodic reconnect)

IDLE ──[trigger]──→ CAPTURE ──→ (optional RECOGNIZE) ──→ LOG_SD ──→ IDLE
         │                           │
         │                           └── offline: skip RECOGNIZE, log "unknown"
         │
         └── [every SYNC_RETRY_MS] → runSync() (upload unsynced CSV rows) → IDLE
```

- **Trigger**: GPIO 0 (button) LOW or GPIO 13 (PIR) HIGH; debounce 2s.
- **CAPTURE**: `esp_camera_fb_get()` → JPEG.
- **RECOGNIZE**: `POST /recognize_face` with image, parse `{"name":"..."}`.
- **LOG_SD**: Append `timestamp,name,status,synced` to CSV.
- **runSync**: Read `synced=0` rows → `POST /upload_attendance` → mark `synced=1`.

## Defines to Edit

| Define | Description |
|--------|-------------|
| `WIFI_SSID` | Wi‑Fi SSID |
| `WIFI_PASS` | Wi‑Fi password |
| `SERVER_HOST` | Flask server host (IP or domain) |
| `SERVER_PORT` | `5000` (HTTP) or `443` (HTTPS) |
| `API_TOKEN` | Must match backend `API_TOKEN` |
| `LED_PIN` | 4 (flash LED) |
| `BUZZER_PIN` | 12 |
| `BUTTON_PIN` | 0 (boot button) |
| `PIR_PIN` | 13 |
| `JPEG_QUALITY` | 10–12 |
| `NTP_GMT_OFFSET_SEC` | Your timezone offset |

## Board & Libraries

- **Board**: ESP32-CAM (AI-Thinker). Select “ESP32 Dev Module” or “AI-Thinker ESP32-CAM”.
- **Libraries**: Install via Arduino Library Manager:
  - ArduinoJson
  - (ESP32 core includes WiFi, SD_MMC, time, esp_camera)

## HTTPS

For production over HTTPS, use `WiFiClientSecure`, connect to port 443, and set `SERVER_HOST` to your domain. Use `setInsecure()` only for quick testing.
