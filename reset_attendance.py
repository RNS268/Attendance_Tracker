"""
Reset Today's Attendance
Standalone script to delete the current attendance Excel file
Useful for testing - resets all attendance counts to zero
"""

import os
from datetime import datetime
from config import Config

def get_current_attendance_file_path():
    """Returns the path to the current week's attendance Excel file"""
    week_num = datetime.now().isocalendar()[1]
    year = datetime.now().year
    filename = Config.EXCEL_FILENAME_FORMAT.format(week=week_num, year=year)
    return os.path.join(Config.ATTENDANCE_FOLDER, filename)


def reset_attendance():
    print("\n" + "="*60)
    print("    RESET TODAY'S ATTENDANCE")
    print("="*60)

    filepath = get_current_attendance_file_path()

    print(f"\nCurrent attendance file:")
    print(f"   {filepath}")

    if not os.path.exists(filepath):
        print("\nNo attendance file found for this week.")
        print("   Already reset / no attendance marked yet.")
    else:
        print(f"\nFile found! Size: {os.path.getsize(filepath):,} bytes")
        confirm = input("\nDelete this file and reset attendance? (y/N): ").strip().lower()

        if confirm == 'y':
            try:
                os.remove(filepath)
                print(f"\nFile deleted successfully!")
                print("   All attendance for this week has been reset to zero.")
            except Exception as e:
                print(f"\nFailed to delete file: {e}")
                print("   Try closing Excel or running as administrator.")
        else:
            print("\nReset cancelled. Attendance file preserved.")

    print("\n" + "="*60)
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    reset_attendance()