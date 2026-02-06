# Deployment Instructions

## 1. Run Locally (Flask)

### Prerequisites

- Python 3.10+
- `face_recognition` requires `dlib`; on macOS often: `brew install cmake` and `pip install dlib` then `face_recognition`.

### Steps

```bash
cd /path/to/Attendance
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

Set env (optional; defaults exist):

```bash
export SECRET_KEY="your-secret-key-use-openssl-rand-hex-32"
export API_TOKEN="esp32-cam-api-token-change-in-production"
export INIT_ADMIN_USER="admin"
export INIT_ADMIN_PASSWORD="admin123"
```

Run:

```bash
cd backend && python app.py
```

Server: `http://127.0.0.1:5000`. Open in browser: login → dashboard, register face.

### Local Network Access (ESP32 on same LAN)

- Run Flask on `0.0.0.0` (default in `app.py`).
- Find your machine’s LAN IP (e.g. `192.168.1.100`).
- In ESP32 firmware set `SERVER_URL` to `http://<your-ip>:5000/recognize_face`.
- Ensure firewall allows port 5000.

---

## 2. ngrok for Testing (ESP32 → Internet)

Use ngrok to expose local Flask to the internet so ESP32 can reach it from another network.

```bash
ngrok http 5000
```

ngrok prints a URL like `https://abc123.ngrok.io`. Use that as the base for your `SERVER_URL`.

**ESP32**:

- Set `SERVER_URL` to `https://abc123.ngrok.io/recognize_face`.
- Note: The current firmware uses `HTTPClient`, which supports both HTTP and HTTPS.

---

## 3. Deploy Flask to Free Cloud

### Render

1. Create account at [render.com](https://render.com).
2. New **Web Service**. Connect your Git repo (or upload project).
3. **Root directory**: leave default or set to repo root.
4. **Build**:
   - Build command: `pip install -r backend/requirements.txt`
   - Or use a `render.yaml` / Dockerfile if you prefer.
5. **Start**:
   - Start command: `cd backend && gunicorn -w 1 -b 0.0.0.0:$PORT app:app`
   - Render sets `PORT`.
6. **Environment variables** (in Dashboard → Environment):
   - `SECRET_KEY` = `openssl rand -hex 32`
   - `API_TOKEN` = same token you’ll use in ESP32
   - `INIT_ADMIN_USER` = admin username
   - `INIT_ADMIN_PASSWORD` = admin password
7. Deploy. Note the service URL (e.g. `https://your-app.onrender.com`).

**Note**: Render’s free tier may spin down; first request can be slow. SQLite on ephemeral disk is lost on restart. For persistence use Render disk or a hosted DB.

### Railway

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub.
2. Add **Web Service**, select repo.
3. **Settings**:
   - Build: `pip install -r backend/requirements.txt`
   - Start: `cd backend && gunicorn -w 1 -b 0.0.0.0:$PORT app:app`
4. **Variables**: `SECRET_KEY`, `API_TOKEN`, `INIT_ADMIN_USER`, `INIT_ADMIN_PASSWORD`.
5. Deploy. Use the generated public URL.

### Fly.io

1. Install `flyctl`, login: `fly auth login`.
2. In project root: `fly launch`. Choose app name, region.
3. Set env: `fly secrets set SECRET_KEY=... API_TOKEN=... INIT_ADMIN_USER=... INIT_ADMIN_PASSWORD=...`
4. Use a `Dockerfile` or `fly.toml` to run `gunicorn` (e.g. `CMD cd backend && gunicorn -w 1 -b 0.0.0.0:8080 app:app`). Expose port 8080.
5. `fly deploy`. Use `https://<app>.fly.dev`.

---

## 4. Environment Variables Summary

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask session signing. Use a long random string. |
| `API_TOKEN` | Shared secret for ESP32 `Authorization: Bearer`; must match firmware. |
| `INIT_ADMIN_USER` | First user if DB empty. |
| `INIT_ADMIN_PASSWORD` | First user password. |
| `PORT` | Server port (Render/Railway set this). |
| `DATABASE_URL` | For SQLite leave unset or `sqlite:///attendance.db`. |
| `FACE_MATCH_THRESHOLD` | Optional; default `0.55`. |

---

## 5. Update ESP32 for Production

1. **Wi-Fi**: Set `WIFI_SSID` and `WIFI_PASS` in the sketch.
2. **Server**:
   - **Local**: `SERVER_URL` = `http://192.168.1.100:5000/recognize_face`.
   - **Cloud**: `SERVER_URL` = `https://your-app.onrender.com/recognize_face`.
3. **API token**: Set `API_TOKEN` to the same value as `API_TOKEN` on the server.

Flash the ESP32-CAM and power it. Verify `/health` returns `{"status":"ok"}` (e.g. via browser or `curl`).
