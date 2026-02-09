
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
