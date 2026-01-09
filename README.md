# 📸 Live Webcam Attendance System (V0.3)

A Python-based attendance tracking system that uses **Face Recognition** to mark attendance in real-time via webcam. It logs attendance directly into Excel sheets and supports voice feedback.

## 🚀 Features
- **Live Camera Recognition**: Real-time face detection and attendance marking.
- **Smart Cooldown**: Prevents "spamming" of attendance marks (marks once per session/day).
- **Audio Feedback**: Text-to-speech greetings (e.g., *"Attendance marked for Shashank"*).
- **Visual Feedback**: Color-coded boxes (Green = Marked, Blue = Already Marked, Red = Unknown).
- **Excel Logging**: Automatically generates weekly Excel reports (`Attendance_Week_X_202X.xlsx`).
- **Dual Modes**: 
  - **Simulation Mode**: Manual entry for testing.
  - **Live Camera Mode**: Fully automated process.

## 🛠️ Prerequisites
- Python 3.10+
- Webcam

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/RNS268/Attendance_Tracker.git
   cd Attendance_Tracker
   ```

2. **Install dependencies:**
   ```bash
   pip install opencv-python face-recognition pandas openpyxl pyttsx3 colorama
   ```
   *(Note: `face-recognition` requires `dlib`, which usually requires CMake installed on your system).*

## 🏃 Usage

1. **Run the application:**
   ```bash
   python main.py
   ```

2. **Register a Student:**
   - Select **Option 1** (Student Registration).
   - Choose **Live Camera Registration** to capture photos instantly.
   - Follow the on-screen instructions (turn head left, right, etc.).

3. **Start Attendance:**
   - Select **Option 2** (Mark Attendance).
   - Choose **Option 3** (Live Camera Recognition).
   - The camera will open. When a registered face is detected, attendance is marked!

## 📂 Project Structure
```
├── attendance_files/      # Generated Excel reports
├── registration_images/   # Raw images for training
├── student_data/          # Database (JSON)
├── main.py                # Entry point
├── config.py              # Settings (e.g., Camera ID, Cooldowns)
├── attendance.py          # Core attendance logic
├── registration.py        # Registration logic
├── face_utils.py          # Face recognition helpers
└── requirements.txt       # Dependencies
```

## 🔧 Configuration
You can tweak settings in `config.py`:
- `PROCESS_EVERY_N_FRAMES`: Increase this (e.g., 3 or 4) if video is laggy.
- `RECOGNITION_COOLDOWN`: Time to wait before marking the same person again (default: 30s).
- `ENABLE_AUDIO`: Toggle voice feedback.

## 🤝 Contributing
Feel free to open issues or submit pull requests!

## 📜 License
This project is open-source.
