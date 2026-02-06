# Security Implementation

## Login & Passwords

- **Storage**: Passwords hashed with **bcrypt** (cost factor from `bcrypt.gensalt()`).
- **Verification**: `bcrypt.checkpw(plain, hash)` on `POST /login`.
- **Session**: Flask `session` (signed cookie). `SECRET_KEY` must be set in production.

## Token-Based Auth (ESP32)

- **API token**: Shared secret in env `API_TOKEN`, same value configured on ESP32.
- **Usage**: ESP32 sends `Authorization: Bearer <API_TOKEN>` on:
  - `POST /recognize_face`
  - `POST /upload_attendance`
- **Validation**: `secrets.compare_digest(token, API_TOKEN)` to avoid timing leaks.
- **401**: Invalid or missing token → `{"error": "Invalid or missing API token"}`.

## Session Auth (Web Dashboard)

- **Protected routes**: `/dashboard`, `/register_face`, `GET/POST`, `/api/dashboard`.
- **Check**: `session.get("user_id")`. If missing, redirect to `/login` (or 401 for JSON).
- **Logout**: `POST /logout` clears session.

## Protections

- **Input validation**: Name length, image type/size, `entries` array size (max 500).
- **Rate limiting**: Simple in-memory per-IP (optional). Window 60s, max 30 requests.
- **Max body size**: 10 MB for uploads.

## Production Checklist

1. Set `SECRET_KEY` to a long random value (`openssl rand -hex 32`).
2. Set `API_TOKEN` and use the same value in ESP32 firmware.
3. Use **HTTPS** for the Flask app. For ESP32, use `WiFiClientSecure` and the production URL (see DEPLOYMENT).
4. Change default `admin` / `admin123` via `INIT_ADMIN_USER` and `INIT_ADMIN_PASSWORD` before first run, or create new users and remove default.
