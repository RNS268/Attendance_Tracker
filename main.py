"""
Main Program Entry Point
Attendance Tracking System v0.3
"""

import os
import sys
from datetime import datetime
from database import StudentDatabase
from live_registration import register_student  # Fixed: Always use live_registration for OpenCV version
from attendance import (

    run_simulated_attendance_mode,
    quick_attendance_for_multiple,
    run_camera_attendance
)
from excel_handler import get_today_attendance_count, clear_today_attendance, get_today_attendance_list
from config import Config, Messages

# NEW: Import for clean audio shutdown
from audio_handler import AudioHandler

# Global audio handler reference
audio_handler: AudioHandler = None


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title):
    print("\n" + "="*70)
    print(" "*15 + title)
    print("="*70)


def wait_for_enter():
    input("\n  Press Enter to continue...")


def create_required_folders():
    folders = [Config.DATABASE_FOLDER, Config.ATTENDANCE_FOLDER]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"✓ Created folder: {folder}")


def show_system_statistics():
    print_header("📊 SYSTEM STATISTICS")

    try:
        db = StudentDatabase()
        stats = db.get_database_stats()

        print(f"\n  Total Students Registered: {stats.get('total_students', 0)}")
        print(f"  Database Created: {stats.get('created_at', 'N/A')}")
        print(f"  Last Updated: {stats.get('last_updated', 'N/A')}")

        today_count = get_today_attendance_count()
        print(f"\n  Today's Attendance: {today_count}")

        if stats.get('total_students', 0) > 0:
            percentage = (today_count / stats['total_students']) * 100
            print(f"  Attendance Percentage: {percentage:.1f}%")

        today_list = get_today_attendance_list()
        if today_list:
            print(f"\n  📅 Today's Attendance List:")
            print("  " + "-"*50)
            for i, entry in enumerate(today_list, 1):
                print(f"  {i}. {entry['name']} ({entry['id']}) at {entry['time']}")
        else:
            print("  No attendance recorded today yet.")

    except Exception as e:
        print(f"  Error displaying statistics: {e}")

    print("\n" + "="*70)


def registration_menu():
    # This calls your updated register_student() which has the menu (batch + live camera)
    register_student()


def attendance_menu():
    while True:
        print_header("✅ MARK ATTENDANCE")

        print("\n  Choose attendance method:\n")
        print("  " + "-"*50)
        print("  1. 📝  Manual Entry (One by One)")
        print("  2. ⚡  Quick Batch Mode")
        print("  3. 🎥  Live Camera Recognition")
        print("  4. ⬅️  Back to Main Menu")
        print("  " + "-"*50)

        choice = input("\n  ▶  Enter choice (1-4): ").strip()

        if choice == "1":
            run_simulated_attendance_mode()
        elif choice == "2":
            quick_attendance_for_multiple()
            wait_for_enter()
        elif choice == "3":
            if Config.USE_CAMERA_ATTENDANCE:
                global audio_handler
                audio_handler = AudioHandler()  # Create instance if not exists
                audio_handler.start_session()
                try:
                    run_camera_attendance()
                finally:
                    if audio_handler:
                        audio_handler.end_session()
                        audio_handler.shutdown()
            else:
                print("\n  ⚠️ Camera mode disabled in config")
                wait_for_enter()
        elif choice == "4":
            break
        else:
            print("\n  ❌ Invalid choice.")
            wait_for_enter()


def admin_menu():
    """Restored full ADMINISTRATION menu with all original features"""
    while True:
        print_header("⚙️  ADMINISTRATION")

        print("\n  Administrative options:\n")
        print("  " + "-"*50)
        print("  1. 📊  View System Statistics")
        print("  2. 📁  Export Data")
        print("  3. 🧹  Clear Today's Attendance")
        print("  4. 🚨  System Health Check")
        print("  5. ⬅️  Back to Main Menu")
        print("  " + "-"*50)

        choice = input("\n  ▶  Enter choice (1-5): ").strip()

        if choice == "1":
            show_system_statistics()
            wait_for_enter()

        elif choice == "2":
            print("\n  Exporting data...")
            db = StudentDatabase()
            success = db.export_to_csv()  # Assuming this method exists in your database.py
            if success:
                print("  ✓ Data exported successfully to CSV.")
            else:
                print("  ✗ Failed to export data.")
            wait_for_enter()

        elif choice == "3":
            confirm = input("\n  Clear today's attendance records? (Y/N): ").upper()
            if confirm == 'Y':
                success, message = clear_today_attendance()
                if success:
                    print(f"\n  ✓ {message}")
                else:
                    print(f"\n  ✗ {message}")
            wait_for_enter()

        elif choice == "4":
            print("\n  Performing system health check...")

            # Database check
            try:
                db = StudentDatabase()
                count = db.get_student_count()
                print(f"  ✓ Database: {count} students")
            except:
                print("  ✗ Database check failed")

            # Camera check
            try:
                import cv2
                camera = cv2.VideoCapture(Config.CAMERA_DEVICE_ID)
                if camera.isOpened():
                    print("  ✓ Camera: Accessible")
                    camera.release()
                else:
                    print("  ✗ Camera: Not accessible")
            except:
                print("  ✗ Camera check failed")

            # Face recognition library check
            try:
                import face_recognition
                print("  ✓ Face Recognition: Library loaded")
            except:
                print("  ✗ Face Recognition: Library not found")

            # Pandas/Excel check
            try:
                import pandas as pd
                print("  ✓ Excel Handler: Library loaded")
            except:
                print("  ✗ Excel Handler: Library not found")

            print("\n  Health check complete.")
            wait_for_enter()

        elif choice == "5":
            break

        else:
            print("\n  ❌ Invalid choice. Please enter 1-5.")
            wait_for_enter()


def main():
    global audio_handler

    clear_screen()
    print_header(f"WELCOME TO {Config.APP_NAME}")
    print(f"\n  Version: {Config.VERSION}")
    print("  System initialized successfully!")
    print("\n" + "="*70)

    create_required_folders()

    try:
        while True:
            print_header("MAIN MENU")

            print("\n  Choose an option:\n")
            print("  " + "-"*50)
            print("  1. 👤  Student Registration")
            print("  2. ✅  Mark Attendance")
            print("  3. ⚙️   Administration")
            print("  4. 🆘  Help & Instructions")
            print("  5. 🚪  Exit System")
            print("  " + "-"*50)

            choice = input("\n  ▶  Enter your choice (1-5): ").strip()

            if choice == "1":
                registration_menu()

            elif choice == "2":
                attendance_menu()

            elif choice == "3":
                admin_menu()

            elif choice == "4":
                print_header("🆘 HELP & INSTRUCTIONS")
                print("\n  • Advanced audio with welcome/greeting/already-marked messages")
                print("  • Live camera registration with photo preview")
                print("  • Batch image registration from folders")
                print("  • Admin tools: statistics, clear today, health check")
                wait_for_enter()

            elif choice == "5":
                print_header("THANK YOU FOR USING THE SYSTEM")
                print("\n  Shutting down gracefully...")
                print("\n" + "="*70)
                break

            else:
                print("\n  ❌ Invalid choice.")
                wait_for_enter()

    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
    finally:
        # Clean shutdown of audio threads
        if audio_handler is not None:
            print("Shutting down audio system...")
            audio_handler.shutdown()
        print("Goodbye! 👋")


if __name__ == "__main__":
    main()