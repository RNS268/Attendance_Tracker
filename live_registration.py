"""
Registration Module (OpenCV Backend)
- Batch registration from images folder
- Advanced live camera registration with preview
- Pure OpenCV implementation (No face_recognition/dlib required)
"""

import os
import re
import json
import cv2
import numpy as np
from datetime import datetime
from config import Config
from database import StudentDatabase
import face_utils

# ====================== BULK IMAGE REGISTRATION ======================

REG_DIR = "registration_images"

def register_from_images(target_id=None):
    """Register students from folders in registration_images/"""
    print("\n" + "="*70)
    print("    BATCH REGISTRATION FROM IMAGES")
    print("="*70)

    if not os.path.exists(REG_DIR):
        os.makedirs(REG_DIR, exist_ok=True)
        print(f"Folder '{REG_DIR}' created. Add student folders with images.")
        return

    db = StudentDatabase()
    registered = skipped = 0

    folders = [target_id] if target_id else [d for d in os.listdir(REG_DIR) if os.path.isdir(os.path.join(REG_DIR, d))]

    for student_id in folders:
        if not re.match(Config.STUDENT_ID_PATTERN, student_id):
            print(f"✗ Invalid ID folder: {student_id}")
            skipped += 1
            continue

        path = os.path.join(REG_DIR, student_id)
        images = [f for f in os.listdir(path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]

        if not images:
            print(f"⚠ No images in {student_id}")
            skipped += 1
            continue

        encodings = []
        for img_file in images:
            try:
                img_path = os.path.join(path, img_file)
                img = cv2.imread(img_path)
                if img is None: continue
                
                locs = face_utils.detect_faces(img)
                if locs:
                    # Extract the largest face encoding
                    locs = sorted(locs, key=lambda l: (l[2]-l[0])*(l[1]-l[3]), reverse=True)
                    enc = face_utils.extract_encoding(img, locs[0])
                    if enc:
                        encodings.append(enc)
            except:
                pass

        if len(encodings) < 3:
            print(f"✗ {student_id}: Only {len(encodings)} valid faces found. Need at least 3.")
            skipped += 1
            continue

        # Get name from DB if exists, else ask user
        name = db.get_student_name(student_id) if db.student_exists(student_id) else input(f"Enter Name for {student_id}: ").title() or "Student"
        
        # Average the histograms
        primary = np.mean(encodings, axis=0).tolist()
        
        success = db.add_student(
            student_id=student_id,
            student_name=name,
            primary_encoding=primary,
            sample_encodings=[]
        )
        if success:
            registered += 1
            print(f"✓ {name} ({student_id}) registered successfully")
        else:
            skipped += 1

    print(f"\nSummary: {registered} registered, {skipped} skipped")

# ====================== LIVE CAMERA REGISTRATION ======================

def draw_oval_guide(frame, cx, cy):
    cv2.ellipse(frame, (cx, cy), (140, 180), 0, 0, 360, (255, 165, 0), 3)

def is_face_well_positioned(rect, cx, cy):
    if not rect: return False
    x, y, w, h = rect
    return (abs(x + w//2 - cx) < 60 and abs(y + h//2 - cy) < 80 and w > 160 and h > 160)

def show_photo_preview(frames):
    if not frames: return
    grid = np.zeros((400, 800, 3), np.uint8)
    for i, f in enumerate(frames[:10]):
        r, c = i // 5, i % 5
        small = cv2.resize(f, (140, 140))
        # Center in 160x200 cell, starting at y=30
        grid[r*200+30:r*200+170, c*160+20:c*160+160] = small
        cv2.putText(grid, str(i+1), (c*160+30, r*200+50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
    cv2.putText(grid, "CAPTURED PHOTOS - Press any key", (100, 30), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255,255,255), 2)
    cv2.imshow("Preview", grid)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def live_camera_registration():
    print("\n" + "="*70)
    print("    LIVE CAMERA REGISTRATION")
    print("="*70)

    db = StudentDatabase()
    while True:
        sid = input(f"Student ID ({Config.STUDENT_ID_EXAMPLE}): ").strip().upper()
        if re.match(Config.STUDENT_ID_PATTERN, sid): break
        print("Invalid format")

    if db.student_exists(sid):
        if input("Overwrite? (y/N): ").lower() != 'y':
            return

    name = input("Student Name: ").strip().title() or "Student"

    cap = cv2.VideoCapture(Config.CAMERA_DEVICE_ID)
    cap.set(3, Config.CAMERA_WIDTH)
    cap.set(4, Config.CAMERA_HEIGHT)
    if not cap.isOpened():
        print("Camera error")
        return

    poses = [("Straight",4), ("Left",2), ("Right",2), ("Up",1), ("Down",1)]
    encodings = []
    frames = []
    captured = 0
    total = Config.REGISTRATION_PHOTOS
    cx, cy = Config.CAMERA_WIDTH//2, Config.CAMERA_HEIGHT//2
    pose_idx = photos_this_pose = 0

    while captured < total:
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)
        disp = frame.copy()
        draw_oval_guide(disp, cx, cy)

        cv2.putText(disp, f"Pose: {poses[pose_idx][0]}", (20,50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,255,255), 2)
        cv2.putText(disp, f"{captured}/{total}", (20,90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)

        locs = face_utils.detect_faces(frame)
        ready = False
        if locs:
            # Sort by size (largest first)
            locs = sorted(locs, key=lambda l: (l[2]-l[0])*(l[1]-l[3]), reverse=True)
            top, right, bottom, left = locs[0]
            w, h = right - left, bottom - top
            cv2.rectangle(disp, (left, top), (right, bottom), (0, 255, 0), 3)

            if is_face_well_positioned((left, top, w, h), cx, cy):
                ready = True
                cv2.putText(disp, "READY - HOLD", (disp.shape[1]//2-200, disp.shape[0]-40), cv2.FONT_HERSHEY_DUPLEX, 1.1, (0,255,0), 3)

        if ready and photos_this_pose < poses[pose_idx][1]:
            enc = face_utils.extract_encoding(frame, locs[0])
            if enc:
                encodings.append(enc)
                frames.append(frame.copy())
                captured += 1
                photos_this_pose += 1
                print(f"✓ {captured}/{total}")
                
                # Flash effect
                overlay = disp.copy()
                cv2.rectangle(overlay, (0,0), (disp.shape[1],disp.shape[0]), (255,255,255), -1)
                cv2.addWeighted(overlay, 0.4, disp, 0.6, 0, disp)
                
                if photos_this_pose >= poses[pose_idx][1]:
                    pose_idx += 1
                    photos_this_pose = 0

        cv2.imshow("Live Registration (Q to cancel)", disp)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            print("Cancelled")
            break

    cap.release()
    cv2.destroyAllWindows()

    if captured < 8:
        print("Not enough photos captured.")
        return

    show_photo_preview(frames)
    if input("Save this registration? (Y/n): ").lower() in ['', 'y', 'yes']:
        # Average the histogram encodings
        avg_encoding = np.mean(encodings, axis=0).tolist()
        success = db.add_student(sid, name, avg_encoding, [])
        if success:
            print(f"✓ {name} ({sid}) registered successfully!")
        else:
            print("✗ Failed to save.")

# ====================== MAIN MENU ======================

def register_student():
    """Main registration menu"""
    while True:
        print("\n" + "="*70)
        print("    STUDENT REGISTRATION MENU")
        print("="*70)
        print("  1. 📁 Batch from Images (registration_images/)")
        print("  2. 🎥 Live Camera Registration (with preview)")
        print("  3. ⬅️ Back to Main Menu")
        print("="*70)

        choice = input("\n  Choose (1-3): ").strip()

        if choice == '1':
            register_from_images()
        elif choice == '2':
            live_camera_registration()
        elif choice == '3':
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    register_student()