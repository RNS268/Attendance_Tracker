import cv2
import numpy as np
import os
import face_utils
from database import StudentDatabase
from config import Config

def run_mock_test():
    print("🧪 Running OpenCV Engine Mock Test...")
    
    # 1. Test Detection
    print("\n1. Testing Face Detection...")
    mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw a white rectangle to simulate a "face" for Haar cascade (might not work perfectly on black, but testing for crashes)
    cv2.rectangle(mock_frame, (200, 150), (400, 350), (255, 255, 255), -1)
    
    try:
        locs = face_utils.detect_faces(mock_frame)
        print(f"✅ Detection function ran. Found {len(locs)} faces.")
    except Exception as e:
        print(f"❌ Detection crashed: {e}")

    # 2. Test Encoding
    print("\n2. Testing Encoding Extraction...")
    try:
        mock_loc = (150, 400, 350, 200) # top, right, bottom, left
        encoding = face_utils.extract_encoding(mock_frame, mock_loc)
        if encoding:
            print(f"✅ Encoding generated. Size: {len(encoding)}")
        else:
            print("❌ Encoding failed (returned None).")
    except Exception as e:
        print(f"❌ Encoding crashed: {e}")

    # 3. Test Database Compatibility
    print("\n3. Testing Database Compatibility...")
    db = StudentDatabase(test_mode=True)
    try:
        # Create a mock student with current encoding size
        dummy_enc = [0.1] * 960
        db.add_student("24054-EC-001", "Test Student", np.array(dummy_enc), [])
        
        students = db.get_all_students()
        match = face_utils.compare_with_database(dummy_enc, students)
        print(f"✅ Comparison result: {match}")
    except Exception as e:
        print(f"❌ Database test crashed: {e}")
    finally:
        if os.path.exists(db.db_path):
            os.remove(db.db_path)

    print("\n✨ Mock test complete. If no 'CRASHED' messages appeared, the system is ready for the real camera.")

if __name__ == "__main__":
    run_mock_test()
