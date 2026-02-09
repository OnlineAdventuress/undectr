"""
Suno Studio Pro - Audio Processors
"""

from .artifact_remover import ArtifactRemover
from .mastering_engine import MasteringEngine
from .ai_learner import UserPreferenceLearner, SimpleRuleBasedLearner
from .watch_folder import WatchFolderProcessor, WatchFolderHandler, ProcessingQueue

# Try to import StemProcessor, but provide fallback if torch/demucs not available
try:
    from .stem_separator import StemProcessor
except ImportError as e:
    print(f"⚠️ Warning: Could not import StemProcessor: {e}")
    print("⚠️ Creating a stub StemProcessor class")
    
    # Create a stub class that warns users
    class StemProcessor:
        def __init__(self, device='cpu'):
            self.device = device
            self.model = None
            print("⚠️ StemProcessor is unavailable (torch/demucs missing)")
            print("⚠️ Install torch and demucs for stem separation")
        
        def separate_stems(self, audio_path, output_dir=None):
            raise ImportError("Stem separation requires torch and demucs. Please install: pip install torch torchaudio demucs")
        
        def process_stem_individually(self, stems, settings):
            raise ImportError("Stem processing requires torch and demucs")
        
        def export_stems(self, stems, output_dir):
            raise ImportError("Stem export requires torch and demucs")

__all__ = [
    'ArtifactRemover',
    'MasteringEngine',
    'StemProcessor',
    'UserPreferenceLearner',
    'SimpleRuleBasedLearner',
    'WatchFolderProcessor',
    'WatchFolderHandler',
    'ProcessingQueue'
]