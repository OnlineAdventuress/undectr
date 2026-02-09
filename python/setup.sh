#!/bin/bash

# Suno Studio Pro - Python Environment Setup
# Run this script to set up the Python audio processing backend

set -e

echo "🚀 Setting up Suno Studio Pro Python Backend..."
echo "=================================================="

cd "$(dirname "$0")"

# Check Python version
echo "📋 Checking Python version..."
python3 --version

# Create virtual environment
echo "🔧 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing Python dependencies..."
echo "This may take a few minutes..."

# Install core audio processing libraries
pip install librosa==0.10.1 soundfile==0.12.1 numpy==1.26.3 scipy==1.12.0

# Install pedalboard (audio effects)
pip install pedalboard==0.7.4

# Install loudness normalization
pip install pyloudnorm==0.1.0

# Install demucs for stem separation
echo "🔬 Installing Demucs (stem separation)..."
pip install demucs==4.0.0

# Install machine learning dependencies
pip install scikit-learn==1.4.0 joblib==1.3.2

# Install file watching
pip install watchdog==3.0.0

# Optional: audio visualization and playback
echo "🎨 Installing optional visualization libraries..."
pip install matplotlib==3.8.3
pip install sounddevice==0.4.6

# Development dependencies
echo "🛠️  Installing development dependencies..."
pip install pytest==7.4.4 black==24.1.1 flake8==7.0.0

# Verify installations
echo "✅ Verifying installations..."
python3 -c "import librosa; import soundfile; import pedalboard; import demucs; print('✅ All core dependencies installed successfully')"

# Create test audio file
echo "🎵 Creating test audio file..."
if [ ! -d "test_audio" ]; then
    mkdir -p test_audio
fi

# Create a simple Python script to generate test audio
cat > test_audio/generate_test.py << 'EOF'
import numpy as np
import soundfile as sf
import os

# Create a simple test tone
sample_rate = 44100
duration = 3.0  # seconds
t = np.linspace(0, duration, int(sample_rate * duration), False)

# Generate a simple tone with some harmonics (simulating Suno-like audio)
frequency = 440  # A4
audio = 0.5 * np.sin(2 * np.pi * frequency * t)
audio += 0.3 * np.sin(2 * np.pi * 2 * frequency * t)  # 2nd harmonic
audio += 0.2 * np.sin(2 * np.pi * 3 * frequency * t)  # 3rd harmonic
audio += 0.1 * np.sin(2 * np.pi * 8800 * t)  # High frequency shimmer (Suno artifact)

# Normalize
audio = audio / np.max(np.abs(audio))

# Save as WAV
sf.write('test_audio/test_tone.wav', audio, sample_rate)
print(f"✅ Test audio saved: test_audio/test_tone.wav ({len(audio)} samples)")
EOF

python3 test_audio/generate_test.py

# Run basic tests
echo "🧪 Running basic tests..."
cat > test_basic.py << 'EOF'
#!/usr/bin/env python3
"""Basic functionality tests for Suno Studio Pro"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Test artifact remover
    from processors.artifact_remover import ArtifactRemover
    print("✅ ArtifactRemover imported successfully")
    
    # Test mastering engine
    from processors.mastering_engine import MasteringEngine
    print("✅ MasteringEngine imported successfully")
    
    # Test stem separator
    from processors.stem_separator import StemProcessor
    print("✅ StemProcessor imported successfully")
    
    # Test AI learner
    from processors.ai_learner import UserPreferenceLearner
    print("✅ UserPreferenceLearner imported successfully")
    
    # Test main processor
    from main import SunoStudioPro
    print("✅ SunoStudioPro imported successfully")
    
    print("\n🎉 All Python modules imported successfully!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
EOF

python3 test_basic.py

# Create a simple processing script
echo "🔧 Creating example processing script..."
cat > process_example.py << 'EOF'
#!/usr/bin/env python3
"""Example processing script for Suno Studio Pro"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import SunoStudioPro
import soundfile as sf
import numpy as np

def process_example():
    """Process the test audio file"""
    print("🎵 Starting example audio processing...")
    
    # Create processor
    processor = SunoStudioPro(sample_rate=44100)
    
    # Load test audio
    input_path = "test_audio/test_tone.wav"
    output_path = "test_audio/processed_tone.wav"
    
    if not os.path.exists(input_path):
        print(f"❌ Input file not found: {input_path}")
        return False
    
    try:
        # Load audio
        audio, sr = sf.read(input_path)
        print(f"✅ Loaded audio: {input_path} (shape: {audio.shape}, SR: {sr})")
        
        # Basic processing settings
        settings = {
            "artifact_removal": {
                "enabled": True,
                "metallic_intensity": 0.7,
                "vocal_intensity": 0.5,
                "phase_intensity": 0.6,
                "compression_intensity": 0.4
            },
            "mastering": {
                "enabled": True,
                "preset": "spotify",
                "lufs_target": -14,
                "true_peak": -1.0
            },
            "stem_separation": {
                "enabled": False  # Disabled for quick test
            }
        }
        
        # Process audio
        print("⚙️  Processing audio...")
        result = processor.process_audio(
            input_path=input_path,
            output_path=output_path,
            settings=settings,
            progress_callback=lambda p, msg: print(f"  Progress: {p}% - {msg}")
        )
        
        if result["success"]:
            print(f"✅ Audio processed successfully!")
            print(f"   Output: {output_path}")
            print(f"   Processing time: {result['processing_time']:.2f}s")
            
            # Verify output file
            if os.path.exists(output_path):
                processed_audio, processed_sr = sf.read(output_path)
                print(f"   Processed audio shape: {processed_audio.shape}")
                print(f"   Sample rate: {processed_sr}")
                print("\n🎉 Example processing completed successfully!")
                return True
            else:
                print("❌ Output file not created")
                return False
        else:
            print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = process_example()
    sys.exit(0 if success else 1)
EOF

chmod +x process_example.py

echo ""
echo "=================================================="
echo "🎉 Python Backend Setup Complete!"
echo ""
echo "📁 Project Structure:"
echo "  /python/              - Audio processing backend"
echo "    ├── main.py         - Main processor"
echo "    ├── processors/     - Processing modules"
echo "    └── test_audio/     - Test files"
echo ""
echo "🚀 Next Steps:"
echo "  1. Activate environment: source venv/bin/activate"
echo "  2. Test processing: python process_example.py"
echo "  3. Run main processor: python main.py --help"
echo ""
echo "💡 Tips:"
echo "  - The virtual environment is in 'venv/'"
echo "  - All dependencies are installed"
echo "  - Test audio generated in 'test_audio/'"
echo ""
echo "✅ Python Audio Backend is READY for Task 1.3!"
echo "=================================================="