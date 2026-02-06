"""
ESP32-CAM Face Recognition Attendance System — Flask Backend
Complete implementation: auth, face registration, recognition, attendance sync.
"""

import io
import os
import json
import sqlite3
import secrets
import logging
from functools import wraps

import bcrypt
import flask
from flask import Flask, request, jsonify, redirect, url_for, session, send_from_directory
import face_recognition
from PIL import Image
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, static_folder=os.path.join(_BASE, "static"), template_folder=os.path.join(_BASE, "templates"))
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production-use-secrets-token-hex")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB
DATABASE = os.environ.get("DATABASE_URL", "sqlite:///attendance.db").replace("postgres://", "sqlite:///").split("?")[0]
if DATABASE.startswith("sqlite"):
    DB_PATH = os.path.join(os.path.dirname(__file__), "attendance.db")
else:
    DB_PATH = None

# Face recognition settings
FACE_MATCH_THRESHOLD = float(os.environ.get("FACE_MATCH_THRESHOLD", "0.6"))
# Distance between 0.6 and 0.8 is "seen but not clear"
FACE_VISIBLE_THRESHOLD = float(os.environ.get("FACE_VISIBLE_THRESHOLD", "0.8"))

# API token for ESP32. Set via env; must match ESP32 config.
API_TOKEN = os.environ.get("API_TOKEN", "esp32-cam-api-token-change-in-production")

# Cooldown for logging the same person (seconds): 10 minutes = 600 seconds
RECOGNITION_COOLDOWN = int(os.environ.get("RECOGNITION_COOLDOWN", "600"))
LAST_LOGGED = {}  # { (device_id, name): timestamp }

# Live Frame Storage (file-based so it works with multiple workers and survives restarts)
LATEST_FRAME_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "latest_capture.jpg")

# Rate limiting: simple in-memory (per process). Optional.
RATE_LIMIT = {}
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 30


# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
def get_db():
    if DB_PATH is None:
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    if conn is None:
        return
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS face_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            embedding BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            device_id TEXT,
            logged_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(device_id, logged_at, name)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_attendance_logged_at ON attendance_logs(logged_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_attendance_name ON attendance_logs(name)")
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        admin_user = os.environ.get("INIT_ADMIN_USER", "admin")
        admin_pass = os.environ.get("INIT_ADMIN_PASSWORD", "admin123")
        insert_user(cur, admin_user, admin_pass)
    conn.commit()
    conn.close()


def insert_user(cur, username: str, password: str) -> int:
    h = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, h))
    return cur.lastrowid


def verify_user(cur, username: str, password: str) -> dict | None:
    cur.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        return None
    if not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        return None
    return {"id": row["id"], "username": row["username"]}


def embedding_to_blob(enc: np.ndarray) -> bytes:
    return enc.astype(np.float32).tobytes()


def blob_to_embedding(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)


# -----------------------------------------------------------------------------
# Auth helpers
# -----------------------------------------------------------------------------
def api_token_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        auth = request.headers.get("Authorization")
        token = None
        if auth and auth.startswith("Bearer "):
            token = auth[7:]
        if not token or not secrets.compare_digest(token, API_TOKEN):
            return jsonify({"error": "Invalid or missing API token"}), 401
        return f(*args, **kwargs)
    return wrapped


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.headers.get("Accept", "").find("application/json") != -1:
                return jsonify({"error": "Login required"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped


def simple_rate_limit(key: str) -> bool:
    import time
    now = int(time.time())
    if key not in RATE_LIMIT:
        RATE_LIMIT[key] = []
    RATE_LIMIT[key] = [t for t in RATE_LIMIT[key] if now - t < RATE_LIMIT_WINDOW]
    if len(RATE_LIMIT[key]) >= RATE_LIMIT_MAX:
        return False
    RATE_LIMIT[key].append(now)
    return True


# -----------------------------------------------------------------------------
# Face recognition
# -----------------------------------------------------------------------------
from PIL import Image, ImageOps

def extract_embedding(rgb: np.ndarray):
    # Convert back to PIL for processing if needed
    img = Image.fromarray(rgb)
    w, h = img.size
    logger.debug(f"Extracting embedding from {w}x{h} image")

    # Try with default HOG model first
    face_locations = face_recognition.face_locations(rgb)
    
    # If no face found, try contrast enhancement
    if not face_locations:
        logger.debug("No face found, trying histogram equalization...")
        eq_img = ImageOps.equalize(img)
        eq_rgb = np.array(eq_img)
        face_locations = face_recognition.face_locations(eq_rgb)
        if face_locations:
            logger.info("Face found after histogram equalization")
            rgb = eq_rgb # Use the equalized version for encoding
    
    # If still no face found, try upscaling once
    if not face_locations:
        logger.debug("No face found, trying upscaled detection...")
        face_locations = face_recognition.face_locations(rgb, number_of_times_to_upsample=1)
        
    if not face_locations:
        return None
        
    encodings = face_recognition.face_encodings(rgb, known_face_locations=face_locations)
    if len(encodings) == 0:
        return None
    return encodings[0]


def match_face(embedding: np.ndarray, conn) -> tuple[str | None, str]:
    cur = conn.cursor()
    cur.execute("SELECT id, name, embedding FROM face_embeddings")
    stored = cur.fetchall()
    if not stored:
        return None, "no_baseline" # No faces registered yet
    
    best_name = None
    best_dist = float("inf")
    
    for row in stored:
        enc = blob_to_embedding(row["embedding"])
        dist = float(np.linalg.norm(embedding - enc))
        if dist < best_dist:
            best_dist = dist
            best_name = row["name"]
    
    logger.info(f"Best match: {best_name} (dist: {best_dist:.4f})")
    
    if best_dist <= FACE_MATCH_THRESHOLD:
        return best_name, "recognized"
    elif best_dist <= FACE_VISIBLE_THRESHOLD:
        return best_name, "not_clear"
    else:
        return None, "unknown"


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "attendance-api"})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return flask.send_from_directory(app.template_folder, "login.html")
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database not configured"}), 500
    user = verify_user(conn.cursor(), username, password)
    conn.close()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return jsonify({"status": "ok", "username": user["username"]})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "ok"})


@app.route("/register_face", methods=["GET", "POST"])
@login_required
def register_face():
    if request.method == "GET":
        return flask.send_from_directory(app.template_folder, "register_face.html")
    if "image" not in request.files and "image" not in (request.form or {}):
        return jsonify({"error": "No image provided"}), 400
    name = (request.form.get("name") or "").strip()
    if not name or len(name) > 128:
        return jsonify({"error": "Valid name required (1–128 chars)"}), 400
    f = request.files.get("image")
    if not f:
        return jsonify({"error": "No image file"}), 400
    try:
        img = Image.open(f.stream).convert("RGB")
        rgb = np.array(img)
    except Exception as e:
        return jsonify({"error": f"Invalid image: {e}"}), 400
    enc = extract_embedding(rgb)
    if enc is None:
        return jsonify({"error": "No face detected in image"}), 400
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database not configured"}), 500
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO face_embeddings (user_id, name, embedding) VALUES (?, ?, ?)",
        (session["user_id"], name, embedding_to_blob(enc))
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "name": name})


@app.route("/recognize_face", methods=["POST"])
@api_token_required
def recognize_face():
    # Rate limiting per device
    device_id = request.headers.get("X-Device-ID", "esp32-cam")
    if not simple_rate_limit(f"recognize:{device_id}"):
        logger.warning(f"Rate limit exceeded for device: {device_id}")
        return jsonify({"error": "Rate limit exceeded"}), 429
    
    logger.info(f"Face recognition request from device: {device_id}")

    # Support both multipart (web/browser) and raw binary (ESP32)
    rgb = None
    try:
        if "image" in request.files:
            f = request.files["image"]
            if not f or f.filename == "":
                return jsonify({"error": "No image file provided"}), 400
            
            img_bytes = f.read()
            if not img_bytes:
                return jsonify({"error": "Empty image file"}), 400

            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            rgb = np.array(img)
        elif request.data and len(request.data) > 0:
            # Check content type for better error messages
            content_type = request.headers.get("Content-Type", "")
            if "image" not in content_type.lower() and len(request.data) < 100:
                return jsonify({"error": "Invalid image data"}), 400
            img_bytes = request.data
            img = Image.open(io.BytesIO(request.data)).convert("RGB")
            rgb = np.array(img)
        else:
            return jsonify({"error": "No image provided"}), 400

        # Store latest frame to file for live feed (works with multiple workers, survives restarts)
        if img_bytes:
            try:
                with open(LATEST_FRAME_PATH, "wb") as out:
                    out.write(img_bytes)
                logger.info(f"Live feed updated from device: {device_id} ({len(img_bytes)} bytes)")
            except Exception as e:
                logger.warning(f"Could not save latest frame to file: {e}")
        
        # Validate image size
        if rgb is None or rgb.size == 0:
            return jsonify({"error": "Invalid image data"}), 400
            
    except Exception as e:
        import traceback
        logger.error(f"Image processing error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": f"Invalid image: {str(e)}"}), 400
    
    # Extract face embedding
    enc = extract_embedding(rgb)
    
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database not configured"}), 500
    
    name = None
    status = "unknown"
    
    if enc is not None:
        name, status = match_face(enc, conn)
    else:
        logger.warning(f"No face detected in image from device: {device_id}")
        status = "no_face"
    
    # Log attendance automatically if match and not on cooldown
    import datetime
    import time
    now_dt = datetime.datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    now_ts = time.time()
    
    # Check if already marked (within cooldown)
    if name:
        key = (device_id, name)
        last_time = LAST_LOGGED.get(key, 0)
        if now_ts - last_time <= RECOGNITION_COOLDOWN:
            status = "already_marked"
    
    final_name = name if name else "unknown"
    should_log = (status == "recognized")

    if should_log:
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO attendance_logs (name, status, device_id, logged_at) VALUES (?, ?, ?, ?)",
                (final_name, status, device_id, now_str)
            )
            conn.commit()
            # Update last logged timestamp after successful commit
            LAST_LOGGED[(device_id, final_name)] = now_ts
        except sqlite3.IntegrityError:
            # Duplicate entry, ignore (cooldown prevented duplicate)
            logger.debug(f"Duplicate attendance entry prevented for {final_name} on {device_id}")
        except Exception as e:
            import traceback
            logger.error(f"Logging error: {e}\n{traceback.format_exc()}")
        
    conn.close()
    
    return jsonify({
        "name": final_name,
        "status": status
    })


@app.route("/upload_attendance", methods=["POST"])
@api_token_required
def upload_attendance():
    data = request.get_json(force=True, silent=True)
    if not data or "entries" not in data:
        return jsonify({"error": "JSON body with 'entries' array required"}), 400
    entries = data["entries"]
    if not isinstance(entries, list) or len(entries) > 500:
        return jsonify({"error": "entries must be array, max 500"}), 400
    device_id = (data.get("device_id") or "esp32-default").strip()[:64]
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database not configured"}), 500
    cur = conn.cursor()
    synced = 0
    for e in entries:
        ts = e.get("timestamp") or e.get("logged_at") or e.get("ts")
        name = (e.get("name") or "").strip() or "unknown"
        status = (e.get("status") or "unknown").strip()[:32] or "unknown"
        if not ts:
            continue
        try:
            cur.execute(
                """INSERT OR IGNORE INTO attendance_logs (name, status, device_id, logged_at)
                   VALUES (?, ?, ?, ?)""",
                (name, status, device_id, ts)
            )
            if cur.rowcount:
                synced += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "synced": synced})


@app.route("/dashboard")
@login_required
def dashboard():
    return flask.send_from_directory(app.template_folder, "dashboard.html")


@app.route("/api/registered_faces/<path:name>", methods=["DELETE"])
@login_required
def api_delete_face(name):
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database not configured"}), 500
    cur = conn.cursor()
    cur.execute("DELETE FROM face_embeddings WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": f"Deleted face for {name}"})


@app.route("/api/registered_faces")
@login_required
def api_registered_faces():
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database not configured"}), 500
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT name FROM face_embeddings ORDER BY name ASC")
    rows = cur.fetchall()
    conn.close()
    return jsonify({"people": [r["name"] for r in rows]})


@app.route("/api/attendance/today", methods=["DELETE"])
@login_required
def api_clear_today():
    import datetime
    today_start = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database not configured"}), 500
    cur = conn.cursor()
    cur.execute("DELETE FROM attendance_logs WHERE logged_at >= ?", (today_start,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "Today's logs cleared"})


@app.route("/api/attendance/history")
@login_required
def api_attendance_history():
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database not configured"}), 500
    cur = conn.cursor()
    # Group by date part of logged_at
    cur.execute(
        """SELECT name, status, device_id, logged_at, date(logged_at) as log_date 
           FROM attendance_logs 
           ORDER BY logged_at DESC LIMIT 1000"""
    )
    rows = cur.fetchall()
    conn.close()
    
    import collections
    history = collections.defaultdict(list)
    for r in rows:
        history[r["log_date"]].append({
            "name": r["name"],
            "status": r["status"],
            "device_id": r["device_id"],
            "logged_at": r["logged_at"]
        })
    
    return jsonify({"history": history})


@app.route("/api/dashboard")
@login_required
def api_dashboard():
    import datetime
    today_start = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database not configured"}), 500
    cur = conn.cursor()
    cur.execute(
        "SELECT name, status, device_id, logged_at FROM attendance_logs WHERE logged_at >= ? ORDER BY logged_at DESC",
        (today_start,)
    )
    rows = cur.fetchall()
    conn.close()
    data = [
        {"name": r["name"], "status": r["status"], "device_id": r["device_id"], "logged_at": r["logged_at"]}
        for r in rows
    ]
    return jsonify({"attendance": data})


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/api/latest_frame")
@login_required
def api_latest_frame():
    if not os.path.isfile(LATEST_FRAME_PATH):
        return jsonify({"error": "No frame received yet"}), 404
    try:
        with open(LATEST_FRAME_PATH, "rb") as f:
            data = f.read()
    except Exception as e:
        logger.warning(f"Could not read latest frame file: {e}")
        return jsonify({"error": "Could not read frame"}), 500
    if not data:
        return jsonify({"error": "No frame received yet"}), 404
    resp = flask.Response(data, mimetype="image/jpeg")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    return resp


# -----------------------------------------------------------------------------
# Init & run
# -----------------------------------------------------------------------------
with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
