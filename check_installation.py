#!/usr/bin/env python3
"""Check which packages are installed"""

packages = [
    ('numpy', 'numpy'),
    ('pandas', 'pandas'),
    ('openpyxl', 'openpyxl'),
    ('cv2', 'opencv-python'),
    ('pyttsx3', 'pyttsx3'),
    ('dotenv', 'python-dotenv'),
    ('colorama', 'colorama'),
    ('face_recognition', 'face_recognition'),
]

print("=" * 50)
print("Package Installation Status")
print("=" * 50)

installed = []
missing = []

for module_name, package_name in packages:
    try:
        __import__(module_name)
        print(f"✅ {package_name}")
        installed.append(package_name)
    except ImportError:
        print(f"❌ {package_name} - MISSING")
        missing.append(package_name)

print("\n" + "=" * 50)
print(f"Summary: {len(installed)}/{len(packages)} packages installed")
print("=" * 50)

if missing:
    print(f"\n⚠️  Missing packages: {', '.join(missing)}")
    print("\nTo install missing packages, run:")
    print("  bash install_face_recognition.sh")
else:
    print("\n✅ All packages are installed!")
