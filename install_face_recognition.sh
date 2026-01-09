#!/bin/bash
# Installation script for face_recognition and dlib
# Run this script in your terminal: bash install_face_recognition.sh

echo "=========================================="
echo "Installing face_recognition dependencies"
echo "=========================================="

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

echo ""
echo "Step 1: Installing dlib via Homebrew..."
brew install dlib

echo ""
echo "Step 2: Installing face_recognition..."
/usr/local/bin/python3.14 -m pip install --user face_recognition

echo ""
echo "Step 3: Verifying installation..."
/usr/local/bin/python3.14 -c "import face_recognition; print('✅ face_recognition installed successfully!')" || echo "❌ Installation failed. Please check the error messages above."

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
