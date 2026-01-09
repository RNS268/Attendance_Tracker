"""
Attendance Module (Simulated Mode)
For Version 0 - Manual student ID input without camera
Based strictly on Claude's pseudocode
"""
import re
import time
from datetime import datetime
from database import StudentDatabase
from excel_handler import add_attendance_entry, get_today_attendance_count, get_today_attendance_list
from config import Config, Messages, Colors, get_match_quality
import cv2
from face_utils import (
    detect_faces, 
    extract_encoding, 
    compare_with_database, 
    draw_face_box
)

# NEW: Import the advanced AudioHandler
from audio_handler import AudioHandler

# Global audio handler instance (will be initialized in camera mode)
audio_handler: AudioHandler = None

# =========================================================
# VERSION 0.1 - SIMULATION & MANUAL ENTRY
# =========================================================

def validate_student_id_format(student_id):
    """Validate ID using pattern from Config"""
    if not student_id:
        return False
    return bool(re.match(Config.STUDENT_ID_PATTERN, student_id))


def simulate_attendance_single_student(student_id):
    """Process a single student ID for attendance"""
    db = StudentDatabase()
    
    # 1. Validate format
    if not validate_student_id_format(student_id):
        print(f"❌ Invalid ID format. Use format like {Config.STUDENT_ID_EXAMPLE}")
        return False

    # 2. Check if student exists
    if not db.student_exists(student_id):
        print(f"❌ Student ID {student_id} not found in database.")
        return False

    # 3. Get student name
    student_name = db.get_student_name(student_id)
    
    # 4. Mark attendance
    print(f"Found: {student_name}")
    success, message = add_attendance_entry(student_id, student_name)
    
    if success:
        print(f"✅ {message}")
        
        # Audio feedback if available (simulated mode might not initialize audio_handler global)
        # We can implement a simple text-to-speech fallback here if desired
        try:
             import pyttsx3
             engine = pyttsx3.init()
             engine.say(f"Welcome {student_name}")
             engine.runAndWait()
        except:
            pass
        return True
    else:
        print(f"⚠️  {message}")
        return False


def run_simulated_attendance_mode():
    """Manual Entry Mode Loop"""
    print("\n" + "="*70)
    print("    MANUAL ATTENDANCE MARKING (SIMULATION)")
    print("="*70)
    print("Type 'Q' to return to menu\n")

    while True:
        student_id = input(f"Enter Student ID ({Config.STUDENT_ID_EXAMPLE}): ").strip().upper()
        
        if student_id == 'Q':
            break
            
        simulate_attendance_single_student(student_id)
        print("-" * 50)


def quick_attendance_for_multiple():
    """Batch entry mode"""
    print("\n" + "="*70)
    print("    BATCH ATTENDANCE ENTRY")
    print("="*70)
    print("Enter IDs separated by comma (e.g., ID1, ID2, ID3)")
    
    raw_input = input("\nEnter IDs: ").strip().upper()
    if not raw_input:
        return

    ids = [x.strip() for x in raw_input.split(',')]
    print(f"\nProcessing {len(ids)} IDs...\n")
    
    success_count = 0
    for sid in ids:
        if simulate_attendance_single_student(sid):
            success_count += 1
            
    print(f"\nCompleted: {success_count}/{len(ids)} marked successfully.")
    input("Press Enter to continue...")

# =========================================================
# VERSION 0.3 - LIVE CAMERA ATTENDANCE (UPDATED WITH NEW AUDIO HANDLER)
# =========================================================

def run_camera_attendance():
    """Run continuous camera attendance with real-time recognition using OpenCV Backend"""
    global audio_handler
    
    # 1. Initialization
    print("\n" + "="*70)
    print(Messages.CAM_ATT_START.center(70))
    print("="*70 + "\n")

    print(Messages.CAM_ATT_LOADING)


    # Load database
    db = StudentDatabase()
    students_dict = db.get_all_students()

    if len(students_dict) == 0:
        print(Messages.CAM_ATT_NO_STUDENTS)
        input("\nPress Enter to return...")
        return

    print(f"✓ Loaded {len(students_dict)} students\n")

    # Initialize camera
    camera = cv2.VideoCapture(Config.CAMERA_DEVICE_ID)
    if not camera.isOpened():
        print("✗ Cannot access camera!")
        print("Ensure no other application is using the camera.")
        input("\nPress Enter to return...")
        return

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAMERA_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAMERA_HEIGHT)
    print("✓ Camera initialized\n")

    # NEW: Initialize advanced AudioHandler
    audio_handler = AudioHandler()
    audio_handler.start_session()
    print("✓ Advanced audio feedback enabled\n")

    # Tracking variables
    cooldown_tracker = {}        # {student_id: last_marked_time}
    recognized_today = set()     # Track who was marked today
    frame_count = 0

    print(Messages.CAM_ATT_READY)
    print(Messages.CAM_ATT_INSTRUCTIONS)
    print("\n" + "="*70 + "\n")
    time.sleep(2)

    window_name = "Live Attendance - Press Q to Quit"

    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                print("Failed to capture frame")
                break

            display_frame = frame.copy()
            current_time = time.time()

            frame_count += 1
            should_process = (frame_count % Config.PROCESS_EVERY_N_FRAMES == 0)

            if should_process:
                small_frame = cv2.resize(frame, (0, 0), fx=Config.FRAME_SCALE, fy=Config.FRAME_SCALE)
                face_locations = detect_faces(small_frame)

                # Focus on largest face only
                if face_locations and len(face_locations) > 1:
                    face_locations.sort(key=lambda loc: (loc[2]-loc[0]) * (loc[1]-loc[3]), reverse=True)
                    face_locations = [face_locations[0]]

                if face_locations:
                    face_locations = [
                        (int(top/Config.FRAME_SCALE), int(right/Config.FRAME_SCALE), 
                         int(bottom/Config.FRAME_SCALE), int(left/Config.FRAME_SCALE))
                        for top, right, bottom, left in face_locations
                    ]

                for face_location in face_locations:
                    top, right, bottom, left = face_location
                    face_width = right - left
                    face_height = bottom - top

                    if face_width < Config.MIN_FACE_SIZE or face_height < Config.MIN_FACE_SIZE:
                        draw_face_box(display_frame, face_location, "Too small", Colors.YELLOW)
                        continue

                    encoding = extract_encoding(frame, face_location)
                    if encoding is None:
                        draw_face_box(display_frame, face_location, "Processing...", Colors.YELLOW)
                        continue

                    match_result = compare_with_database(encoding, students_dict)

                    if match_result['match_found']:
                        student_id = match_result['student_id']
                        distance = match_result['distance']
                        student_name = students_dict[student_id]['student_name']

                        # NEW: Feed into AudioHandler
                        was_marked_today = student_id in recognized_today
                        audio_handler.process_person(
                            person_id=student_id,
                            person_name=student_name,
                            is_recognized=True,
                            attendance_marked=was_marked_today
                        )

                        # Visual label
                        if Config.SHOW_MATCH_QUALITY:
                            quality = get_match_quality(distance)
                            label = f"{student_name} ({quality})"
                        else:
                            label = student_name

                        # Cooldown for marking
                        if student_id in cooldown_tracker:
                            if current_time - cooldown_tracker[student_id] < Config.RECOGNITION_COOLDOWN:
                                label += " (wait)"
                                draw_face_box(display_frame, face_location, label, Colors.YELLOW)
                                continue

                        # Mark attendance
                        success, message = add_attendance_entry(student_id, student_name)

                        if success:
                            cooldown_tracker[student_id] = current_time
                            if student_id not in recognized_today:
                                recognized_today.add(student_id)

                            label += " ✓"
                            draw_face_box(display_frame, face_location, label, Colors.GREEN)
                            print(Messages.RECOG_SUCCESS.format(name=student_name))
                            db.update_recognition_stats(student_id)
                        else:
                            label += " (Done)"
                            draw_face_box(display_frame, face_location, label, Colors.BLUE)
                    else:
                        draw_face_box(display_frame, face_location, "Unknown", Colors.RED)

            cv2.imshow(window_name, display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        # Cleanup
        camera.release()
        cv2.destroyAllWindows()
        
        if audio_handler:
            audio_handler.end_session()
            # Optional: audio_handler.shutdown() if you want full cleanup

    print("\nCamera attendance session ended.")