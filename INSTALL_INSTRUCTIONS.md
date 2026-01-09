# Installation Instructions for Attendance Tracker

## Issue: face_recognition Module Not Found

The `face_recognition` package requires `dlib`, which is failing to build on Python 3.14.

## Solution Options:

### Option 1: Install dlib using Homebrew (Recommended for macOS)

1. Install Homebrew if you don't have it:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. Install dlib system library:
   ```bash
   brew install dlib
   ```

3. Then install face_recognition:
   ```bash
   /usr/local/bin/python3.14 -m pip install --user face_recognition
   ```

### Option 2: Use a Pre-built dlib Wheel

Try installing from a pre-built wheel:
```bash
/usr/local/bin/python3.14 -m pip install --user https://github.com/sachadee/Dlib/releases/download/v19.22/dlib-19.22.99-cp314-cp314-macosx_11_0_arm64.whl
/usr/local/bin/python3.14 -m pip install --user face_recognition
```

### Option 3: Use Python 3.11 or 3.12 (More Compatible)

Python 3.14 is very new and some packages may not have pre-built wheels yet. Consider using Python 3.11 or 3.12:

```bash
# Install Python 3.11 or 3.12
brew install python@3.11

# Then install packages
python3.11 -m pip install -r requirements.txt
```

### Option 4: Install All Packages Manually

Run these commands one by one:

```bash
/usr/local/bin/python3.14 -m pip install --user numpy pandas openpyxl opencv-python pyttsx3 python-dotenv colorama
/usr/local/bin/python3.14 -m pip install --user face-recognition-models
# Then follow Option 1 or 2 for dlib and face_recognition
```

## Verify Installation

After installation, verify with:
```bash
/usr/local/bin/python3.14 -c "import face_recognition; print('face_recognition installed successfully!')"
```

## Current Status

✅ Most packages are already installed:
- numpy
- pandas  
- openpyxl
- opencv-python
- face-recognition-models
- pyttsx3
- python-dotenv
- colorama

❌ Missing:
- face_recognition (due to dlib build failure)
