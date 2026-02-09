#!/usr/bin/env python3
"""
Suno Studio Pro - Quick Python Setup
Installs dependencies in virtual environment
"""

import os
import sys
import subprocess
import shutil

def run_command(cmd, cwd=None):
    """Run a command and print output"""
    print(f"⚡ Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"❌ Command failed: {result.stderr}")
        return False
    print(f"✅ {result.stdout}")
    return True

def main():
    print("🚀 Setting up Suno Studio Pro Python Backend...")
    print("==================================================")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Check Python
    print(f"📋 Python version: {sys.version}")
    
    # Create virtual environment
    venv_path = os.path.join(script_dir, "venv")
    if not os.path.exists(venv_path):
        print("🔧 Creating virtual environment...")
        if not run_command("python3 -m venv venv"):
            print("⚠️ Trying with --system-site-packages...")
            if not run_command("python3 -m venv venv --system-site-packages"):
                print("❌ Failed to create virtual environment")
                return False
    else:
        print("✅ Virtual environment already exists")
    
    # Get pip path
    pip_path = os.path.join(venv_path, "bin", "pip")
    python_path = os.path.join(venv_path, "bin", "python")
    
    # Upgrade pip
    print("⬆️ Upgrading pip...")
    run_command(f"{pip_path} install --upgrade pip")
    
    # Install dependencies
    print("📦 Installing dependencies...")
    
    # Core packages
    core_packages = [
        "librosa==0.10.1",
        "soundfile==0.12.1", 
        "numpy==1.26.3",
        "scipy==1.12.0",
        "pedalboard==0.7.4",
        "pyloudnorm==0.1.0",
    ]
    
    for package in core_packages:
        print(f"  Installing {package}...")
        run_command(f"{pip_path} install {package}")
    
    # Demucs for stem separation
    print("🔬 Installing Demucs...")
    run_command(f"{pip_path} install demucs==4.0.0")
    
    # ML packages
    print("🤖 Installing ML packages...")
    ml_packages = ["scikit-learn==1.4.0", "joblib==1.3.2"]
    for package in ml_packages:
        run_command(f"{pip_path} install {package}")
    
    # Utility packages
    print("🛠️ Installing utilities...")
    util_packages = ["watchdog==3.0.0", "matplotlib==3.8.3", "sounddevice==0.4.6"]
    for package in util_packages:
        run_command(f"{pip_path} install {package}")
    
    # Dev packages
    print("💻 Installing dev packages...")
    dev_packages = ["pytest==7.4.4", "black==24.1.1", "flake8==7.0.0"]
    for package in dev_packages:
        run_command(f"{pip_path} install {package}")
    
    # Test imports
    print("🧪 Testing imports...")
    test_code = """
import librosa
import soundfile as sf
import numpy as np
from pedalboard import Pedalboard
import pyloudnorm as pyln
try:
    import demucs
    print("✅ Demucs imported")
except ImportError:
    print("⚠️ Demucs not installed")

print("✅ All core packages imported successfully!")
"""
    
    with open("test_import.py", "w") as f:
        f.write(test_code)
    
    run_command(f"{python_path} test_import.py")
    os.remove("test_import.py")
    
    # Create test audio
    print("🎵 Creating test audio...")
    test_audio_dir = "test_audio"
    os.makedirs(test_audio_dir, exist_ok=True)
    
    create_test_code = """
import numpy as np
import soundfile as sf

sr = 44100
duration = 2.0
t = np.linspace(0, duration, int(sr * duration), False)

# Test tone with harmonics (simulating Suno audio)
freq = 440
audio = 0.5 * np.sin(2 * np.pi * freq * t)
audio += 0.3 * np.sin(2 * np.pi * 2 * freq * t)  # 2nd harmonic
audio += 0.1 * np.sin(2 * np.pi * 8800 * t)      # High freq artifact

# Normalize
audio = audio / np.max(np.abs(audio))

# Save
sf.write('test_audio/test_tone.wav', audio, sr)
print(f"✅ Test audio created: test_audio/test_tone.wav")
"""
    
    with open("create_test.py", "w") as f:
        f.write(create_test_code)
    
    run_command(f"{python_path} create_test.py")
    os.remove("create_test.py")
    
    # Test the main processor
    print("🔧 Testing main processor...")
    test_processor_code = """
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from processors.artifact_remover import ArtifactRemover
    from processors.mastering_engine import MasteringEngine
    from processors.stem_separator import StemProcessor
    from main import SunoStudioPro
    
    print("✅ All modules imported!")
    
    processor = SunoStudioPro(sample_rate=44100)
    print("✅ Processor created!")
    
    print("🎉 Python backend is READY!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    
    with open("test_processor.py", "w") as f:
        f.write(test_processor_code)
    
    if run_command(f"{python_path} test_processor.py"):
        os.remove("test_processor.py")
        print("")
        print("==================================================")
        print("🎉 Python Audio Backend Setup Complete!")
        print("")
        print("📁 Virtual Environment:")
        print(f"  Source: source {venv_path}/bin/activate")
        print(f"  Python: {python_path}")
        print(f"  Pip: {pip_path}")
        print("")
        print("🚀 Quick Test:")
        print(f"  {python_path} main.py --help")
        print("")
        print("✅ Task 1.3 (Python Audio Backend) - COMPLETE!")
        print("==================================================")
        return True
    else:
        print("❌ Processor test failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)