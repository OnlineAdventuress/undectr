#!/bin/bash

# Suno Studio Pro - Quick Install
# Installs just the essential dependencies

echo "🚀 Installing essential Python dependencies..."

cd /home/ubuntu/clawd/suno-studio-pro/python

# Create virtual environment with system packages
echo "🔧 Creating virtual environment..."
python3 -m venv venv --system-site-packages

# Activate and install
source venv/bin/activate

echo "📦 Installing core packages..."
pip install --upgrade pip

# Install absolutely essential packages first
pip install numpy scipy librosa soundfile

echo "✅ Core packages installed"

# Test basic imports
echo "🧪 Testing basic imports..."
python3 -c "
import numpy as np
import librosa
import soundfile as sf
print('✅ NumPy version:', np.__version__)
print('✅ Librosa version:', librosa.__version__)
print('✅ SoundFile available')
"

# Create test directory
mkdir -p test_audio

# Create simple test
echo "🎵 Creating test audio..."
python3 -c "
import numpy as np
import soundfile as sf

sr = 44100
t = np.linspace(0, 1.0, sr)
freq = 440
audio = 0.5 * np.sin(2 * np.pi * freq * t)
audio = audio / np.max(np.abs(audio))

sf.write('test_audio/simple_test.wav', audio, sr)
print('✅ Test audio created: test_audio/simple_test.wav')
"

echo ""
echo "=================================================="
echo "🎉 Essential Python Setup Complete!"
echo ""
echo "📁 Test file: test_audio/simple_test.wav"
echo "🚀 Next: Install pedalboard and demucs"
echo "💡 Use: source venv/bin/activate"
echo "=================================================="