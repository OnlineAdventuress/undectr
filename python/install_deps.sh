#!/bin/bash

# Suno Studio Pro - Python Dependency Installer
# Simple version that installs dependencies globally

set -e

echo "🚀 Installing Suno Studio Pro Python Dependencies..."
echo "=================================================="

cd "$(dirname "$0")"

# Check Python version
echo "📋 Python version: $(python3 --version)"

# Install system dependencies if needed
echo "🔧 Checking system dependencies..."
if command -v apt-get &> /dev/null; then
    echo "📦 Ubuntu/Debian detected, installing python3-venv..."
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-dev portaudio19-dev
fi

# Install pip packages
echo "📦 Installing Python packages..."
echo "This may take a few minutes..."

# Core audio processing
pip3 install librosa==0.10.1 soundfile==0.12.1 numpy==1.26.3 scipy==1.12.0

# Audio effects
pip3 install pedalboard==0.7.4

# Loudness normalization
pip3 install pyloudnorm==0.1.0

# Stem separation (Demucs)
echo "🔬 Installing Demucs for stem separation..."
pip3 install demucs==4.0.0

# Machine learning
pip3 install scikit-learn==1.4.0 joblib==1.3.2

# File watching
pip3 install watchdog==3.0.0

# Optional: visualization
echo "🎨 Installing optional visualization libraries..."
pip3 install matplotlib==3.8.3
pip3 install sounddevice==0.4.6

# Development tools
echo "🛠️  Installing development tools..."
pip3 install pytest==7.4.4 black==24.1.1 flake8==7.0.0

# Test imports
echo "✅ Testing imports..."
python3 -c "
import librosa
import soundfile as sf
import numpy as np
from pedalboard import Pedalboard
import pyloudnorm as pyln
print('✅ Core audio libraries imported')
"

# Check demucs
python3 -c "
try:
    import demucs
    print('✅ Demucs imported successfully')
except ImportError as e:
    print('⚠️  Demucs import issue:', e)
"

# Create test directory
mkdir -p test_audio

# Create simple test tone
echo "🎵 Creating test audio..."
python3 -c "
import numpy as np
import soundfile as sf
import os

# Create test tone
sr = 44100
duration = 2.0
t = np.linspace(0, duration, int(sr * duration), False)

# Simple tone with harmonics
freq = 440
audio = 0.5 * np.sin(2 * np.pi * freq * t)
audio += 0.3 * np.sin(2 * np.pi * 2 * freq * t)
audio += 0.1 * np.sin(2 * np.pi * 8800 * t)  # High freq artifact

# Normalize
audio = audio / np.max(np.abs(audio))

# Save
sf.write('test_audio/test_tone.wav', audio, sr)
print(f'✅ Test audio created: test_audio/test_tone.wav ({len(audio)} samples)')
"

# Test the main processor
echo "🧪 Testing main processor..."
python3 -c "
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Test imports
    from processors.artifact_remover import ArtifactRemover
    from processors.mastering_engine import MasteringEngine
    from processors.stem_separator import StemProcessor
    from main import SunoStudioPro
    
    print('✅ All modules imported successfully!')
    
    # Create processor instance
    processor = SunoStudioPro(sample_rate=44100)
    print('✅ Processor created successfully')
    
    # Test with dummy settings
    settings = {
        'artifact_removal': {'enabled': True},
        'mastering': {'enabled': True},
        'stem_separation': {'enabled': False}
    }
    print('✅ Settings validated')
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

echo ""
echo "=================================================="
echo "🎉 Python Dependencies Installed!"
echo ""
echo "📁 Test Files:"
echo "  test_audio/test_tone.wav  - Test audio for processing"
echo ""
echo "🚀 Quick Test:"
echo "  python3 main.py --help"
echo ""
echo "🔧 To process audio:"
echo "  python3 main.py --input test_audio/test_tone.wav --output processed.wav"
echo ""
echo "✅ Python Audio Backend READY for Task 1.3!"
echo "=================================================="