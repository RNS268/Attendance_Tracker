"""
Installation Script for Attendance Tracking System Version 0.1
Installs requirements, verifies, sets up folders, and guides user
"""
import os
import sys
import subprocess
import platform
from pathlib import Path

class SystemInstaller:
    """Handles installation and verification of system requirements"""

    REQUIRED_LIBRARIES = [
        # Use loose pinning for better compatibility
        ("numpy", "numpy>=1.21.0", "Numerical computing"),
        ("pandas", "pandas>=2.0.0", "Data analysis"),
        ("openpyxl", "openpyxl>=3.0.0", "Excel handling"),
        ("opencv-python", "opencv-python>=4.8.0", "Computer vision"),
        ("face_recognition", "face_recognition>=1.3.0", "Face recognition"),
        ("face-recognition-models", "face-recognition-models>=0.3.0", "Models"),
        ("pyttsx3", "pyttsx3>=2.90", "Text-to-speech"),
        ("python-dotenv", "python_dotenv>=1.0.0", "Env management"),
        ("colorama", "colorama>=0.4.0", "Colored output"),
    ]

    def __init__(self):
        self.system = platform.system()
        self.python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        self.is_windows = self.system == "Windows"

    def print_header(self, text):
        print("\n" + "="*70)
        print(f" {text.center(68)} ")
        print("="*70)

    def print_success(self, text):
        print(f"✅ {text}")

    def print_warning(self, text):
        print(f"⚠️  {text}")

    def print_error(self, text):
        print(f"❌ {text}")

    def print_info(self, text):
        print(f"ℹ️ {text}")

    def check_python_version(self):
        self.print_header("CHECKING PYTHON VERSION")
        major, minor = sys.version_info.major, sys.version_info.minor
        if major < 3 or (major == 3 and minor < 8):
            self.print_error(f"Python 3.8+ required. Current: {major}.{minor}")
            return False
        self.print_success(f"Python {major}.{minor} detected")
        return True

    def check_pip_availability(self):
        self.print_header("CHECKING PIP")
        try:
            subprocess.run([sys.executable, "-m", "pip", "--version"],
                          check=True, capture_output=True)
            self.print_success("pip is available")
            return True
        except Exception:
            self.print_error("pip not found")
            try:
                subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"],
                              check=True)
                self.print_success("pip installed via ensurepip")
                return True
            except:
                self.print_error("Failed to install pip")
                self.print_info("Download get-pip.py from https://bootstrap.pypa.io")
                return False

    def install_library(self, lib_name, package_name, description):
        print(f"\n📦 Installing {lib_name}")
        print(f"   Purpose: {description}")
        print(f"   Command: pip install {package_name}")

        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", package_name]
        if not os.getenv("VIRTUAL_ENV"):  # Only --user if not in venv
            cmd.append("--user")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.print_success(f"{lib_name} installed")
                return True
            else:
                self.print_error(f"Failed to install {lib_name}")
                print(result.stderr.strip())
                if "dlib" in result.stderr or "cmake" in result.stderr.lower():
                    self.print_info("face_recognition requires CMake and build tools")
                    if self.is_windows:
                        self.print_info("Install: Visual Studio Build Tools (with C++)")
                    self.print_info("Then: pip install cmake")
                return False
        except Exception as e:
            self.print_error(f"Error during install: {str(e)}")
            return False

    def install_all_libraries(self):
        self.print_header("INSTALLING LIBRARIES")
        success = 0
        failed = 0
        for lib_name, package, desc in self.REQUIRED_LIBRARIES:
            if self.install_library(lib_name, package, desc):
                success += 1
            else:
                failed += 1
        print(f"\n📊 Summary: {success} succeeded, {failed} failed")
        return success, failed

    def verify_installation(self):
        self.print_header("VERIFYING INSTALLATION")
        verified = []
        import_map = {
            "face_recognition": "face_recognition",
            "opencv-python": "cv2",
            "python-dotenv": "dotenv",
            "face-recognition-models": "face_recognition",  # Same as main
        }
        for lib_name, _, _ in self.REQUIRED_LIBRARIES:
            module = import_map.get(lib_name, lib_name.replace("-", "_"))
            try:
                __import__(module)
                self.print_success(f"{lib_name} ✓")
                verified.append(True)
            except ImportError:
                self.print_error(f"{lib_name} ✗ (import failed)")
                verified.append(False)
        return all(verified)

    def create_requirements_file(self):
        self.print_header("CREATING requirements.txt")
        content = "# Attendance Tracking System v0.1 - Auto-generated\n\n"
        for _, package, _ in self.REQUIRED_LIBRARIES:
            content += package + "\n"
        try:
            with open("requirements.txt", "w") as f:
                f.write(content)
            self.print_success("requirements.txt created")
            return True
        except Exception as e:
            self.print_error(f"Failed: {e}")
            return False

    def setup_project_structure(self):
        self.print_header("CREATING PROJECT FOLDERS")
        folders = ["student_data", "attendance_files", "exports", "backups"]
        for folder in folders:
            Path(folder).mkdir(exist_ok=True)
            self.print_success(f"{folder}/")
        return True

    def show_system_info(self):
        self.print_header("SYSTEM INFORMATION")
        print(f" OS: {platform.system()} {platform.release()}")
        print(f" Python: {self.python_version} ({sys.executable})")
        print(f" Directory: {os.getcwd()}")
        venv = os.getenv("VIRTUAL_ENV") or ("Yes" if hasattr(sys, 'real_prefix') else "No")
        print(f" Virtual Env: {venv}")

    def run_test_imports(self):
        self.print_header("TESTING PROJECT MODULE IMPORTS")
        modules = ["config", "database", "excel_handler", "attendance", "main"]
        for mod in modules:
            try:
                __import__(mod)
                self.print_success(f"{mod}.py ✓")
            except Exception as e:
                self.print_error(f"{mod}.py ✗ → {e}")

    def show_post_installation_instructions(self):
        self.print_header("INSTALLATION COMPLETE!")
        print("\n🎉 Your Attendance System is ready!")
        print("\n📂 Project structure:")
        print("   student_data/        ← Database")
        print("   attendance_files/    ← Weekly Excel sheets")
        print("   exports/             ← CSV exports")
        print("   backups/             ← Safety backups")
        print("   requirements.txt     ← For future installs")
        print("\n🚀 To run:")
        print("   python main.py")
        print("\n🔄 To reinstall later:")
        print("   pip install -r requirements.txt")
        print("\nℹ️  Troubleshooting:")
        print("   • If face_recognition fails: pip install cmake first")
        print("   • On Windows: Install Visual Studio Build Tools if needed")

    def run(self):
        self.print_header("ATTENDANCE SYSTEM INSTALLER v0.1")
        self.show_system_info()

        if not self.check_python_version():
            return False
        if not self.check_pip_availability():
            return False

        self.install_all_libraries()
        verified = self.verify_installation()
        self.create_requirements_file()
        self.setup_project_structure()
        self.run_test_imports()
        self.show_post_installation_instructions()

        return verified

def main():
    try:
        installer = SystemInstaller()
        success = installer.run()
        if platform.system() == "Windows":
            input("\nPress Enter to exit...")
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    main()