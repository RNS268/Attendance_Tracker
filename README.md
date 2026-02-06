# ESP32-CAM Face Recognition Attendance System — Setup Guide

This guide will walk you through the step-by-step process of activating the ESP32-CAM Face Recognition Attendance System.

## Step 1: Preparation

Ensure you have Python 3.10 or higher installed on your system.

## Step 2: Virtual Environment Setup

It is highly recommended to use a virtual environment to avoid dependency conflicts.

```bash
# Navigate to the project directory
cd /Users/Shashank/Documents/Attendance

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows
```

## Step 3: Installing Dependencies

Install the required Python packages. Note that `face_recognition` requires `face_recognition_models` and `setuptools` (for `pkg_resources` in Python 3.10+).

```bash
# Upgrade pip first
pip install --upgrade pip

# Install basic requirements
pip install -r backend/requirements.txt

# Install required models and compatibility layers
pip install git+https://github.com/ageitgey/face_recognition_models
pip install setuptools
```

## Step 4: Activating the Backend

1.  Navigate to the `backend` directory.
2.  Start the Flask application.

```bash
cd backend
python app.py
```

The server should start and listen on port `5000`. You should see output similar to this:

```
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

## Step 5: Accessing the Dashboard

1.  Open your web browser and navigate to `http://127.0.0.1:5000`.
2.  Login with the default admin credentials:
    *   **Username:** `admin`
    *   **Password:** `admin123`
3.  Go to **Register Face** to capture your face using your webcam. This will allow the system to recognize you later via the ESP32-CAM.
4.  Navigate to the **Dashboard** to see attendance logs.

## Step 6: Connecting the ESP32-CAM (Online Mode)

1.  **Install Required Libraries:**
    *   Open Arduino IDE.
    *   Go to **Sketch** > **Include Library** > **Manage Libraries...**.
    *   Search for **"ArduinoJson"** and install the latest version (v7+ recommended).
2.  Open the `firmware/esp32cam_attendance/esp32cam_attendance.ino` sketch in Arduino IDE.
3.  Set your Wi-Fi credentials (`WIFI_SSID`, `WIFI_PASS`).
4.  Set the `SERVER_URL` to your computer's local IP address or cloud URL (e.g., `http://192.168.1.100:5000/recognize_face`).
5.  Ensure the `API_TOKEN` matches the one on the server (default: `esp32-cam-api-token-change-in-production`).
6.  Upload the code to your ESP32-CAM. No SD card is required.

---

For more advanced deployment options (ngrok, cloud servers), refer to [DEPLOYMENT.md](file:///Users/Shashank/Documents/Attendance/DEPLOYMENT.md).
