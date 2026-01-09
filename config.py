"""
Configuration file for Attendance System Version 0
"""
import os
import re  # Added for STUDENT_ID_PATTERN validation later

class Config:
    # Application settings
    APP_NAME = "Attendance Tracking System"
    VERSION = "0.2"
    
    # File and folder paths - More robust project root detection
    _PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
    DATABASE_FOLDER = os.path.join(_PROJECT_ROOT, "student_data")
    ATTENDANCE_FOLDER = os.path.join(_PROJECT_ROOT, "attendance_files")
    DATABASE_FILE = "students.json"
    DATABASE_PATH = os.path.join(DATABASE_FOLDER, DATABASE_FILE)  # Added convenience
    
    # System modes
    MODE_ATTENDANCE = "attendance"
    MODE_REGISTRATION = "registration"
    DEFAULT_MODE = MODE_ATTENDANCE

    # Excel file settings
    EXCEL_FILENAME_FORMAT = "Attendance_Week_{week}_{year}.xlsx"
    DATE_FORMAT = "%d-%m-%Y"   # e.g., 01-01-2026
    TIME_FORMAT = "%H:%M:%S"   # e.g., 14:30:45
    
    # Student ID validation
    STUDENT_ID_PATTERN = r'^\d{5}-[A-Z]{2}-\d{3}$'  # 24054-EC-001
    STUDENT_ID_EXAMPLE = "24054-EC-001"
    
    # Face recognition settings
    FRAME_SCALE = 0.25                    # Resize frame for speed (25% size)
    RECOGNITION_THRESHOLD = 0.6          # face_recognition default; lower = stricter
    REQUIRED_CONFIDENCE_PERCENT = 60     # We'll use this for display logic
    SHOW_MATCH_QUALITY = True
    RECOGNITION_COOLDOWN = 3             # seconds
    FACE_LEFT_TIMEOUT = 5                # seconds to clear from cooldown after leaving
    
    # Camera settings
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    CAMERA_ID = 0
    CAMERA_DEVICE_ID = 0  # Added for consistency with V0.3 pseudonym

    # ============================================
    # VERSION 0.3 - CAMERA ATTENDANCE SETTINGS
    # ============================================

    # Camera attendance mode
    USE_CAMERA_ATTENDANCE = True     # True = live camera, False = simulation

    # Processing optimization
    PROCESS_EVERY_N_FRAMES = 4       # Process every 4th frame (faster)
                                     # 1 = every frame (accurate but slow)
                                     # 2 = every other frame (balanced)
                                     # 4 = every fourth frame (efficient for low-end CPUs)

    # Display settings for live feed
    SHOW_FPS = True                  # Show frames per second
    SHOW_STUDENT_COUNT = True        # Show recognized students count
    SHOW_INSTRUCTIONS = True         # Show on-screen instructions

    # Recognition behavior
    MIN_FACE_SIZE = 50              # Minimum face width in pixels
    
    # Registration settings
    REGISTRATION_PHOTOS = 10
    SAMPLE_ENCODINGS_COUNT = 5            # How many to store separately for future ML
    PHOTO_CAPTURE_DELAY = 0.8            # Slightly increased for natural posing
    
    # Audio settings
    ENABLE_AUDIO = True
    SPEECH_RATE = 150
    # AUDIO_QUEUE_DELAY = 1.0            # Optional - can implement later if voices overlap
    
    # Version 0.2 – Camera mode
    USE_CAMERA = True          # Switch between v0.1 simulation and v0.2 camera
    SHOW_CAMERA_FEED = True   # Display camera window


class Colors:
    """Color definitions for OpenCV drawings (BGR format)"""
    BLUE = (255, 0, 0)
    GREEN = (0, 255, 0)
    RED = (0, 0, 255)
    YELLOW = (0, 255, 255)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    CYAN = (255, 255, 0)
    MAGENTA = (255, 0, 255)
    ORANGE = (0, 165, 255)


class Messages:
    """Centralized user-facing messages for consistency"""
    # Registration
    REG_START = "=== STUDENT REGISTRATION ==="
    REG_ENTER_ID = "Enter Student ID (e.g., {}): "
    REG_INVALID_ID = "Invalid ID format! Must be like: {}"
    REG_ENTER_NAME = "Enter Student Name: "
    REG_POSITION_FACE = "Position your face in the center of the frame"
    REG_CAPTURING = "Capturing {} photos for better accuracy..."
    REG_NO_FACE = "No face detected — please center your face"
    REG_PHOTO_CAPTURED = "Captured {}/{} ✓"
    REG_TURN_LEFT = "Good! Now turn slightly LEFT"
    REG_TURN_RIGHT = "Great! Now turn slightly RIGHT"
    REG_TILT_UP = "Almost done! Tilt head UP slightly"
    REG_TILT_DOWN = "Last one! Tilt head DOWN slightly"
    REG_SUCCESS = "✓ Registration successful for {}!"
    REG_FAILED = "✗ Registration failed. Please try again."
    REG_ANOTHER = "\nRegister another student? (Y/N): "

    # Attendance
    ATT_START = "=== ATTENDANCE SYSTEM ACTIVE ==="
    ATT_LOADING = "Loading student database..."
    ATT_LOADED = "✓ Loaded {} students"
    ATT_NO_STUDENTS = "No students registered yet! Register first."
    ATT_POSITION_FACE = "Position your face in front of the camera"
    ATT_PRESS_Q = "Press 'Q' to quit"
    ATT_WAITING = "Waiting for face..."
    ATT_MARKED = "✓ Attendance marked!"
    ATT_ALREADY_TODAY = "Already marked today"
    ATT_COOLDOWN = "(Cooldown active)"
    ATT_NOT_RECOGNIZED = "Not recognized"

    # Audio
    AUDIO_REG_SUCCESS = "Registration successful for {}"
    AUDIO_MARKED = "Hello {}, your attendance has been marked"
    AUDIO_ALREADY_MARKED = "{}, you are already marked today"
    AUDIO_NOT_RECOGNIZED = "Face not recognized. Please try again."

    # Camera attendance messages
    CAM_ATT_START = "🎥  LIVE CAMERA ATTENDANCE"
    CAM_ATT_LOADING = "Loading student database..."
    CAM_ATT_READY = "Camera ready! Position students in frame"
    CAM_ATT_INSTRUCTIONS = "Press 'Q' to quit  |  Press 'S' for statistics"
    CAM_ATT_NO_STUDENTS = "No students registered. Register students first."
    CAM_ATT_PROCESSING = "Processing..."
    CAM_ATT_WAITING = "Waiting for faces..."

    # Recognition feedback messages
    RECOG_SUCCESS = "✓ {name} - Attendance marked!"
    RECOG_ALREADY_MARKED = "{name} already marked today"
    RECOG_COOLDOWN = "{name} - Please wait"
    RECOG_UNKNOWN = "Unknown face detected"
    RECOG_PROCESSING = "Processing face..."


def get_match_percentage(distance: float) -> int:
    """
    Convert face_recognition distance (0.0 best — 1.0+ worst) to percentage match
    Max match at distance 0.0 → 100%, distance >=1.0 → 0%
    """
    if distance >= 1.0:
        return 0
    return int(100 * (1 - distance))


def get_match_quality(distance: float) -> str:
    """Human-readable quality label"""
    if distance < 0.40:
        return "Excellent"
    elif distance < 0.50:
        return "Good"
    elif distance < 0.60:
        return "Fair"
    else:
        return "Poor"


# Create required folders automatically when imported
def _create_folders():
    folders = [Config.DATABASE_FOLDER, Config.ATTENDANCE_FOLDER]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)  # Safer than checking exists

_create_folders()