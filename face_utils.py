import cv2
import numpy as np
import os
import json
from config import Config

"""
Face Utilities (OpenCV Backend)
Using Haar Cascades for detection and Color Histograms for recognition.
This version replaces 'dlib' for compatibility with all macOS systems.
"""

# Flag to indicate system status (Always True for OpenCV)
FACE_RECOGNITION_AVAILABLE = True

# Load Haar Cascade for Face Detection
CASCADE_PATH = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

def detect_faces(image):
    """
    Detect faces in an image using Haar Cascades.
    Returns: List of tuples [(top, right, bottom, left), ...]
    """
    if image is None:
        return []

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(Config.MIN_FACE_SIZE, Config.MIN_FACE_SIZE)
    )

    # Convert (x, y, w, h) -> (top, right, bottom, left)
    face_locations = []
    for (x, y, w, h) in faces:
        face_locations.append((y, x + w, y + h, x))

    return face_locations

def extract_encoding(image, face_location):
    """
    Generate a 'face encoding' using Color Histograms.
    Returns: Normalized histogram array
    """
    if image is None or face_location is None:
        return None

    try:
        top, right, bottom, left = face_location
        face_roi = image[max(0, top):bottom, max(0, left):right]
        
        if face_roi.size == 0:
            return None

        # Resize and convert to HSV for color matching
        face_roi = cv2.resize(face_roi, (128, 128))
        hsv = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
        
        # Calculate Hue/Saturation histogram
        hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        
        return hist.flatten().tolist() # Return as list for JSON serialization

    except Exception as e:
        print(f"Error extracting encoding: {e}")
        return None

def compare_with_database(encoding, students_dict, threshold=0.6):
    """
    Compare probe histogram with database entries.
    Returns: {'match_found': bool, 'student_id': str, 'distance': float}
    """
    result = {'match_found': False, 'student_id': None, 'distance': 1.0}
    
    if encoding is None or not students_dict:
        return result

    probe_hist = np.array(encoding, dtype=np.float32)
    best_score = -1.0

    for sid, data in students_dict.items():
        # Handle different storage versions (primary_encoding vs encodings list)
        stored_raw = data.get("primary_encoding")
        if not stored_raw:
            continue
            
        stored_hist = np.array(stored_raw, dtype=np.float32)
        
        # Use Correlation comparison (1.0 = perfect match)
        score = cv2.compareHist(probe_hist, stored_hist, cv2.HISTCMP_CORREL)
        
        if score > best_score:
            best_score = score
            if score > threshold:
                result['match_found'] = True
                result['student_id'] = sid
                result['distance'] = 1.0 - score # Invert score to look like "distance"
                
    return result

def draw_face_box(frame, location, label, color):
    """Draw bounding box and label on frame"""
    top, right, bottom, left = location
    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
    
    # Label background
    cv2.rectangle(frame, (left, bottom), (right, bottom + 25), color, cv2.FILLED)
    cv2.putText(frame, label, (left + 5, bottom + 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

def load_known_encodings():
    """Compatibility: Load primary encodings from database"""
    if not os.path.exists(Config.DATABASE_PATH):
        return [], [], []

    try:
        with open(Config.DATABASE_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
        students = db.get("students", {})
        
        encs, names, ids = [], [], []
        for sid, sdata in students.items():
            if sdata.get("primary_encoding"):
                encs.append(sdata["primary_encoding"])
                names.append(sdata.get("student_name", "Unknown"))
                ids.append(sid)
        return encs, names, ids
    except:
        return [], [], []