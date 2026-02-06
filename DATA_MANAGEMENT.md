# Data Management

## CSV Format (microSD)

File: `/attendance.csv` on SD card (1‑bit MMC).

```
timestamp,name,status,synced
2025-01-25T10:30:00,John,recognized,1
2025-01-25T10:31:02,unknown,unknown,0
```

| Column   | Description |
|----------|-------------|
| timestamp | ISO-like `YYYY-MM-DDTHH:MM:SS` from NTP, or `millis()` if NTP failed |
| name     | From `/recognize_face` (`"unknown"` if no match or no face) |
| status   | `recognized` or `unknown` |
| synced   | `0` = not yet sent to server, `1` = sent via `POST /upload_attendance` |

- No commas in `name` or `status` (else CSV breaks).
- New rows appended. Sync process updates `synced` from `0` → `1` after successful upload.

## Database Tables (SQLite)

### `users`

| Column        | Type    | Description |
|---------------|---------|-------------|
| id            | INTEGER | PK |
| username      | TEXT    | UNIQUE, login |
| password_hash | TEXT    | bcrypt hash |
| created_at    | TIMESTAMP | |

### `face_embeddings`

| Column     | Type    | Description |
|------------|---------|-------------|
| id         | INTEGER | PK |
| user_id    | INTEGER | FK → users.id |
| name       | TEXT    | Display name for recognition |
| embedding  | BLOB   | 128‑D float32 vector from `face_recognition` |
| created_at | TIMESTAMP | |

### `attendance_logs`

| Column     | Type    | Description |
|------------|---------|-------------|
| id         | INTEGER | PK |
| name       | TEXT    | Recognized name or `unknown` |
| status     | TEXT    | e.g. `recognized`, `unknown` |
| device_id  | TEXT    | From ESP32 (e.g. `esp32-1`) |
| logged_at  | TIMESTAMP | When attendance was logged |
| created_at | TIMESTAMP | Insert time |

`UNIQUE(device_id, logged_at, name)` prevents duplicate rows when syncing.

## Sync Strategy

1. **When online**: ESP32 POSTs to `/recognize_face`, logs to SD with `synced=0`. Optionally runs sync immediately.
2. **When offline**: Logs to SD only with `synced=0`. No server call.
3. **Periodic sync** (e.g. every 60s): ESP32 reads CSV, collects rows with `synced=0`, POSTs to `POST /upload_attendance` with `{"entries": [...], "device_id": "esp32-1"}`.
4. **On 200 OK**: ESP32 rewrites CSV, setting those rows to `synced=1`.
5. **On error**: Rows stay `synced=0`; retry on next cycle.

## Duplicate Prevention

- **Server**: `INSERT OR IGNORE` on `(device_id, logged_at, name)`. Re-sending the same triple is a no-op.
- **ESP32**: Only sends `synced=0` rows; after success, marks them `synced=1` so they are not sent again.
