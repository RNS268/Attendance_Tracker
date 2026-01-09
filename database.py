"""
Student Database Handler for Attendance System
Uses JSON for local storage (Version 0)
Handles all student data operations
"""
import json
import os
import numpy as np
from datetime import datetime, date, timedelta  # FIXED: Added timedelta import
import shutil
import csv
import re
from typing import Dict, List, Optional, Any
from config import Config


class StudentDatabase:
    """
    Handles all database operations for student records
    with attendance tracking and face encoding management
    """

    def __init__(self, test_mode: bool = False):
        """
        Initialize database handler
        
        Args:
            test_mode: If True, uses test database for development
        """
        if test_mode:
            self.db_path = os.path.join(Config.DATABASE_FOLDER, "test_students.json")
        else:
            self.db_path = Config.DATABASE_PATH
        
        # Ensure database folder exists
        os.makedirs(Config.DATABASE_FOLDER, exist_ok=True)
        
        # Create database file if doesn't exist
        if not os.path.exists(self.db_path):
            self._create_empty_database()
            print(f"📁 Created new database: {self.db_path}")

    def _create_empty_database(self):
        """Create an empty database file with proper structure"""
        empty_db = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "students": {},
            "metadata": {
                "total_students": 0,
                "total_recognitions": 0
            }
        }
        
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(empty_db, f, indent=4, ensure_ascii=False)

    def _load_database(self) -> Optional[Dict]:
        """Load database from file with validation"""
        try:
            if not os.path.exists(self.db_path):
                return None
                
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Backward compatibility
            if "version" not in data:
                data["version"] = "1.0"
            if "metadata" not in data:
                data["metadata"] = {"total_students": 0, "total_recognitions": 0}
            
            return data
            
        except json.JSONDecodeError:
            print(f"❌ Error: Database file {self.db_path} is corrupted!")
            self._backup_corrupted_database()
            self._create_empty_database()
            return self._load_database()
        except Exception as e:
            print(f"❌ Error loading database: {e}")
            return None

    def _backup_corrupted_database(self):
        """Create backup of corrupted database"""
        if os.path.exists(self.db_path):
            backup_path = self.db_path + ".corrupted_backup"
            try:
                shutil.copy2(self.db_path, backup_path)
                print(f"⚠️ Created backup of corrupted database: {backup_path}")
            except:
                pass

    def _save_database(self, data: Dict) -> bool:
        """Save database to file with backup"""
        try:
            if os.path.exists(self.db_path):
                backup_path = self.db_path + ".backup"
                shutil.copy2(self.db_path, backup_path)
            
            data["last_updated"] = datetime.now().isoformat()
            
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving database: {e}")
            return False

    def _validate_student_id(self, student_id: str) -> bool:
        """Validate student ID format"""
        pattern = Config.STUDENT_ID_PATTERN
        return bool(re.match(pattern, student_id.strip().upper()))

    def add_student(self, student_id: str, student_name: str,
                   primary_encoding: np.ndarray, sample_encodings: List[np.ndarray]) -> bool:
        """Add or update a student"""
        if not self._validate_student_id(student_id):
            print(f"❌ Invalid student ID format: {student_id}")
            print(f" Expected: {Config.STUDENT_ID_EXAMPLE}")
            return False
        
        db = self._load_database()
        if db is None:
            self._create_empty_database()
            db = self._load_database()
            if db is None:
                return False
        
        # Check if exists
        is_update = student_id in db["students"]
        if is_update:
            print(f"⚠️ Student {student_id} already exists!")
            response = input(" Update existing student? (y/n): ").lower()
            if response != 'y':
                return False
        
        # Convert encodings to list format for JSON
        try:
            # Handle primary encoding
            if isinstance(primary_encoding, np.ndarray):
                primary_encoding_list = primary_encoding.tolist()
            else:
                primary_encoding_list = list(primary_encoding)
            
            # Handle sample encodings
            sample_encodings_list = []
            for enc in sample_encodings:
                if isinstance(enc, np.ndarray):
                    sample_encodings_list.append(enc.tolist())
                else:
                    sample_encodings_list.append(list(enc))
        except Exception as e:
            print(f"❌ Error converting encodings: {e}")
            return False
        
        # Create or update record
        if is_update:
            # Preserve existing recognition count
            existing_recognition_count = db["students"][student_id].get("recognition_count", 0)
            existing_last_recognition = db["students"][student_id].get("last_recognition_date")
        else:
            existing_recognition_count = 0
            existing_last_recognition = None
        
        student_record = {
            "student_id": student_id,
            "student_name": student_name.title(),
            "primary_encoding": primary_encoding_list,
            "sample_encodings": sample_encodings_list,
            "registration_date": datetime.now().isoformat() if not is_update else db["students"][student_id].get("registration_date"),
            "recognition_count": existing_recognition_count,
            "last_recognition_date": existing_last_recognition,
            "metadata": {
                "face_samples": len(sample_encodings),
                "last_updated": datetime.now().isoformat()
            }
        }
        
        db["students"][student_id] = student_record
        db["metadata"]["total_students"] = len(db["students"])
        
        if self._save_database(db):
            action = "updated" if is_update else "added"
            print(f"✅ Student {student_name.title()} ({student_id}) {action} successfully!")
            return True
        return False

    def get_student(self, student_id: str) -> Optional[Dict]:
        """Get student with numpy encodings converted"""
        db = self._load_database()
        if db is None or student_id not in db["students"]:
            return None
        
        student = db["students"][student_id].copy()  # Avoid modifying original
        
        try:
            student["primary_encoding"] = np.array(student["primary_encoding"], dtype=np.float32)
            student["sample_encodings"] = [
                np.array(enc, dtype=np.float32) for enc in student["sample_encodings"]
            ]
        except Exception as e:
            print(f"⚠️ Warning: Could not convert encodings for {student_id}: {e}")
            # Return raw lists instead
        
        return student

    def get_all_students(self) -> Dict[str, Dict]:
        """Return raw student dict (lists, not numpy)"""
        db = self._load_database()
        return db["students"] if db else {}

    def get_known_encodings_for_recognition(self) -> tuple[list, list, list]:
        """
        Returns data ready for comparison.
        Returns: known_encodings, known_names, known_ids
        """
        known_encodings = []
        known_names = []
        known_ids = []
        
        for student_id, data in self.get_all_students().items():
            try:
                encoding = np.array(data["primary_encoding"], dtype=np.float32)
                known_encodings.append(encoding)
                known_names.append(data["student_name"])
                known_ids.append(student_id)
            except:
                continue
        
        return known_encodings, known_names, known_ids

    def student_exists(self, student_id: str) -> bool:
        """Check if student exists in database"""
        db = self._load_database()
        return db is not None and student_id in db["students"]

    def update_recognition_stats(self, student_id: str) -> bool:
        """Update recognition statistics for a student"""
        db = self._load_database()
        if db is None or student_id not in db["students"]:
            return False
        
        db["students"][student_id]["recognition_count"] += 1
        db["students"][student_id]["last_recognition_date"] = datetime.now().isoformat()
        db["metadata"]["total_recognitions"] += 1
        
        return self._save_database(db)

    def get_student_count(self) -> int:
        """Get total number of registered students"""
        db = self._load_database()
        return len(db["students"]) if db else 0

    def delete_student(self, student_id: str) -> bool:
        """Delete a student from database"""
        db = self._load_database()
        if db is None or student_id not in db["students"]:
            return False
        
        del db["students"][student_id]
        db["metadata"]["total_students"] = len(db["students"])
        return self._save_database(db)

    def search_students_by_name(self, name_query: str) -> List[Dict]:
        """Search students by name (case-insensitive partial match)"""
        db = self._load_database()
        if db is None:
            return []
        
        matches = []
        query = name_query.lower()
        for student_id, data in db["students"].items():
            if query in data["student_name"].lower():
                matches.append({
                    "student_id": student_id,
                    "student_name": data["student_name"],
                    "recognition_count": data.get("recognition_count", 0),
                    "last_recognition": data.get("last_recognition_date", "Never")
                })
        return matches

    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        db = self._load_database()
        if db is None:
            return {}
        
        total_recognitions = sum(s.get("recognition_count", 0) for s in db["students"].values())
        today = date.today().isoformat()
        today_count = sum(
    1
    for s in db["students"].values()
    if isinstance(s.get("last_recognition_date"), str)
    and s["last_recognition_date"].startswith(today)
        )

        
        stats = {
            "total_students": len(db["students"]),
            "total_recognitions": total_recognitions,
            "recognitions_today": today_count,
            "created_at": db.get("created_at", "Unknown"),
            "last_updated": db.get("last_updated", "Unknown"),
            "database_version": db.get("version", "1.0")
        }
        
        if stats["total_students"] > 0:
            stats["avg_recognitions_per_student"] = round(total_recognitions / stats["total_students"], 2)
        
        return stats

    def export_students_to_csv(self, output_path: Optional[str] = None) -> bool:
        """Export student data to CSV file"""
        if output_path is None:
            output_path = os.path.join(Config.DATABASE_FOLDER, "students_export.csv")
        
        db = self._load_database()
        if not db:
            return False
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Student ID', 'Name', 'Registration Date', 'Recognition Count', 'Last Recognition', 'Face Samples'])
                for s in db["students"].values():
                    writer.writerow([
                        s['student_id'],
                        s['student_name'],
                        s['registration_date'][:10],
                        s.get('recognition_count', 0),
                        s.get('last_recognition_date', 'Never')[:19] if s.get('last_recognition_date') else 'Never',
                        len(s.get('sample_encodings', []))
                    ])
            print(f"✅ Exported to: {output_path}")
            return True
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False

    def import_from_csv(self, csv_path: str) -> bool:
        """Import students from CSV file (for bulk registration)"""
        if not os.path.exists(csv_path):
            print(f"❌ File not found: {csv_path}")
            return False
        
        try:
            imported = 0
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sid = row.get('Student ID', '').strip()
                    name = row.get('Name', '').strip()
                    if not sid or not name:
                        continue
                    if not self._validate_student_id(sid):
                        print(f" Skipping invalid ID: {sid}")
                        continue
                    
                    # Dummy encodings (warning printed)
                    dummy_primary = [0.0] * 960 
                    dummy_samples = [[0.0] * 960 for _ in range(5)]
                    
                    if self.add_student(sid, name, dummy_primary, dummy_samples):
                        imported += 1
            
            if imported > 0:
                print(f"✅ Imported {imported} students (with dummy face data)")
                print("⚠️  These students will NOT be recognizable until re-registered with real photos!")
            return imported > 0
        except Exception as e:
            print(f"❌ Import failed: {e}")
            return False

    def cleanup_old_data(self, days_old: int = 365) -> int:
        """Remove students who haven't been recognized in X days"""
        db = self._load_database()
        if not db:
            return 0
        
        cutoff = datetime.now() - timedelta(days=days_old)
        removed = 0
        
        to_remove = []
        for sid, s in db["students"].items():
            last_str = s.get("last_recognition_date")
            if last_str:
                try:
                    last_dt = datetime.fromisoformat(last_str)
                    if last_dt < cutoff:
                        to_remove.append(sid)
                except:
                    pass
        
        for sid in to_remove:
            del db["students"][sid]
            removed += 1
        
        if removed:
            db["metadata"]["total_students"] = len(db["students"])
            self._save_database(db)
            print(f"✅ Removed {removed} inactive students (> {days_old} days)")
        
        return removed

    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """Create a backup of the database"""
        if backup_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(Config.DATABASE_FOLDER, f"students_backup_{ts}.json")
        
        try:
            shutil.copy2(self.db_path, backup_path)
            print(f"✅ Backup created: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False


def test_database():
    """Comprehensive database testing"""
    print("🧪 Testing Student Database Module...")
    print("=" * 60)
    
    # Test in test mode (won't affect real data)
    db = StudentDatabase(test_mode=True)
    
    # Create dummy encodings (OpenCV Histogram size)
    dummy_primary = [0.1] * 960
    dummy_samples = [[0.1] * 960 for _ in range(3)]
    
    # Test 1: Add student with valid ID
    print("\n1. Adding test student...")
    success = db.add_student(
        student_id="24054-EC-001",
        student_name="Rajesh Kumar",
        primary_encoding=dummy_primary,
        sample_encodings=dummy_samples
    )
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    
    # Test 2: Add student with invalid ID
    print("\n2. Adding student with invalid ID...")
    success = db.add_student(
        student_id="INVALID-ID",
        student_name="Invalid Student",
        primary_encoding=dummy_primary,
        sample_encodings=dummy_samples
    )
    print(f"   Result: {'✅ Should fail' if not success else '❌ Should have failed'}")
    
    # Test 3: Check if student exists
    print("\n3. Checking student existence...")
    exists = db.student_exists("24054-EC-001")
    print(f"   Student '24054-EC-001' exists: {'✅ Yes' if exists else '❌ No'}")
    
    # Test 4: Get student data
    print("\n4. Retrieving student data...")
    student = db.get_student("24054-EC-001")
    if student:
        print(f"   ✅ Retrieved: {student['student_name']}")
        print(f"   Encoding type: {type(student['primary_encoding'])}")
        print(f"   Shape: {student['primary_encoding'].shape}")
    else:
        print("   ❌ Failed to retrieve student")
    
    # Test 5: Update recognition stats
    print("\n5. Updating recognition stats...")
    if db.update_recognition_stats("24054-EC-001"):
        print("   ✅ Recognition stats updated")
        student = db.get_student("24054-EC-001")
        print(f"   Recognition count: {student.get('recognition_count', 0)}")
    else:
        print("   ❌ Failed to update stats")
    
    # Test 6: Get all students
    print("\n6. Getting all students...")
    all_students = db.get_all_students()
    print(f"   Total students: {len(all_students)}")
    
    # Test 7: Get database statistics
    print("\n7. Database statistics:")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Test 8: Search students
    print("\n8. Searching students by name...")
    matches = db.search_students_by_name("rajesh")
    print(f"   Found {len(matches)} matches for 'rajesh'")
    
    # Test 9: Export to CSV
    print("\n9. Testing export to CSV...")
    db.export_students_to_csv()
    
    # Test 10: Student count
    print("\n10. Student count...")
    count = db.get_student_count()
    print(f"   Total students in database: {count}")
    
    print("\n" + "=" * 60)
    print("✅ Database module test complete!")
    
    # Cleanup: Delete test database
    try:
        if os.path.exists(db.db_path):
            os.remove(db.db_path)
            print(f"   Cleanup: Removed test database")
    except:
        pass


if __name__ == "__main__":
    test_database()