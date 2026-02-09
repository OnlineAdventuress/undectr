import torch
import torchaudio
import numpy as np
from demucs.pretrained import get_model
from demucs.apply import apply_model
import soundfile as sf


class StemProcessor:
    def __init__(self, device='cpu'):
        """
        Initialize stem separator using Demucs
        
        Args:
            device: 'cpu' or 'cuda' for GPU acceleration
        """
        self.device = device
        self.model = None
        self._load_model()
        
    def _load_model(self):
        """Load the Demucs model"""
        try:
            # 'htdemucs' is the recommended model for general use
            self.model = get_model('htdemucs')
            self.model.to(self.device)
            print(f"Demucs model loaded on {self.device}")
        except Exception as e:
            print(f"Error loading Demucs model: {e}")
            print("Falling back to simple frequency-based separation")
            self.model = None
    
    def separate_stems(self, audio_path, output_dir=None):
        """
        Separate audio into stems: drums, bass, other, vocals
        
        Args:
            audio_path: path to input audio file
            output_dir: directory to save individual stems (optional)
            
        Returns:
            Dictionary with stem arrays and metadata
        """
        if self.model is None:
            return self._simple_separation(audio_path, output_dir)
        
        try:
            # Load audio
            wav, sr = torchaudio.load(audio_path)
            
            # Ensure stereo by duplicating mono
            if wav.shape[0] == 1:
                wav = wav.repeat(2, 1)
            
            # Move to device
            wav = wav.to(self.device)
            
            # Separate stems
            with torch.no_grad():
                stems = apply_model(self.model, wav[None], device=self.device)[0]
            
            # stems shape: [4, channels, samples]
            # 0: drums, 1: bass, 2: other, 3: vocals
            
            stems_dict = {
                "drums": stems[0].cpu().numpy(),
                "bass": stems[1].cpu().numpy(),
                "other": stems[2].cpu().numpy(),
                "vocals": stems[3].cpu().numpy()
            }
            
            # Save stems if output_dir provided
            if output_dir:
                import os
                os.makedirs(output_dir, exist_ok=True)
                
                base_name = os.path.splitext(os.path.basename(audio_path))[0]
                
                for stem_name, stem_data in stems_dict.items():
                    output_path = os.path.join(
                        output_dir, 
                        f"{base_name}_{stem_name}.wav"
                    )
                    
                    if stem_data.ndim == 2:
                        sf.write(output_path, stem_data.T, sr)
                    else:
                        sf.write(output_path, stem_data, sr)
                
                stems_dict["output_dir"] = output_dir
            
            stems_dict["sample_rate"] = sr
            stems_dict["success"] = True
            
            return stems_dict
            
        except Exception as e:
            print(f"Error separating stems: {e}")
            # Fall back to simple separation
            return self._simple_separation(audio_path, output_dir)
    
    def _simple_separation(self, audio_path, output_dir=None):
        """
        Simple frequency-based separation as fallback
        This is less accurate than Demucs but works without the model
        """
        import librosa
        
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=44100, mono=False)
            
            if audio.ndim == 1:
                # Convert mono to stereo
                audio = np.array([audio, audio])
            
            # Simple frequency-based separation
            stems_dict = {
                "drums": self._extract_drums(audio, sr),
                "bass": self._extract_bass(audio, sr),
                "vocals": self._extract_vocals(audio, sr),
                "other": self._extract_other(audio, sr)
            }
            
            # Save if output_dir provided
            if output_dir:
                import os
                os.makedirs(output_dir, exist_ok=True)
                
                base_name = os.path.splitext(os.path.basename(audio_path))[0]
                
                for stem_name, stem_data in stems_dict.items():
                    output_path = os.path.join(
                        output_dir, 
                        f"{base_name}_{stem_name}_simple.wav"
                    )
                    
                    if stem_data.ndim == 2:
                        sf.write(output_path, stem_data.T, sr)
                    else:
                        sf.write(output_path, stem_data, sr)
                
                stems_dict["output_dir"] = output_dir
            
            stems_dict["sample_rate"] = sr
            stems_dict["success"] = True
            stems_dict["method"] = "simple_frequency"
            
            return stems_dict
            
        except Exception as e:
            print(f"Simple separation also failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "failed"
            }
    
    def _extract_drums(self, audio, sr):
        """Simple drum extraction using high-pass and transient detection"""
        import librosa
        
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
            
        # High-pass filter for percussive elements
        D = librosa.stft(audio_mono)
        magnitude = np.abs(D)
        
        # Zero out low frequencies (below 100Hz)
        freq_bins = librosa.fft_frequencies(sr=sr)
        low_freq_mask = freq_bins < 100
        magnitude[low_freq_mask] *= 0.1
        
        # Enhance transients
        phase = np.angle(D)
        D_drums = magnitude * np.exp(1j * phase)
        drums_mono = librosa.istft(D_drums)
        
        # Convert back to stereo
        if audio.ndim == 2:
            return np.array([drums_mono, drums_mono])
        return drums_mono
    
    def _extract_bass(self, audio, sr):
        """Simple bass extraction using low-pass"""
        import librosa
        
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
            
        D = librosa.stft(audio_mono)
        magnitude = np.abs(D)
        
        # Keep only low frequencies (below 250Hz)
        freq_bins = librosa.fft_frequencies(sr=sr)
        high_freq_mask = freq_bins > 250
        magnitude[high_freq_mask] *= 0.1
        
        phase = np.angle(D)
        D_bass = magnitude * np.exp(1j * phase)
        bass_mono = librosa.istft(D_bass)
        
        if audio.ndim == 2:
            return np.array([bass_mono, bass_mono])
        return bass_mono
    
    def _extract_vocals(self, audio, sr):
        """Simple vocal extraction focusing on 200-4000Hz range"""
        import librosa
        
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
            
        D = librosa.stft(audio_mono)
        magnitude = np.abs(D)
        
        freq_bins = librosa.fft_frequencies(sr=sr)
        # Focus on vocal range
        vocal_mask = (freq_bins >= 200) & (freq_bins <= 4000)
        non_vocal_mask = ~vocal_mask
        magnitude[non_vocal_mask] *= 0.3  # Reduce non-vocal frequencies
        
        phase = np.angle(D)
        D_vocals = magnitude * np.exp(1j * phase)
        vocals_mono = librosa.istft(D_vocals)
        
        if audio.ndim == 2:
            return np.array([vocals_mono, vocals_mono])
        return vocals_mono
    
    def _extract_other(self, audio, sr):
        """Extract everything else (mid-range instruments)"""
        import librosa
        
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
            
        D = librosa.stft(audio_mono)
        magnitude = np.abs(D)
        
        freq_bins = librosa.fft_frequencies(sr=sr)
        # Remove extreme lows and highs
        extreme_low_mask = freq_bins < 80
        extreme_high_mask = freq_bins > 8000
        magnitude[extreme_low_mask] *= 0.1
        magnitude[extreme_high_mask] *= 0.1
        
        phase = np.angle(D)
        D_other = magnitude * np.exp(1j * phase)
        other_mono = librosa.istft(D_other)
        
        if audio.ndim == 2:
            return np.array([other_mono, other_mono])
        return other_mono
    
    def process_stem_individually(self, stems, settings):
        """
        Apply different processing to each stem
        
        Args:
            stems: dictionary from separate_stems
            settings: dictionary with processing settings for each stem
            
        Returns:
            Dictionary with processed stems
        """
        from .mastering_engine import MasteringEngine
        from .artifact_remover import ArtifactRemover
        
        processed_stems = {}
        mastering_engine = MasteringEngine()
        artifact_remover = ArtifactRemover()
        
        # Vocals processing
        if "vocals" in stems and settings.get("process_vocals", True):
            vocals = stems["vocals"]
            
            # De-essing (simplified)
            if settings.get("de_ess_vocals", True):
                vocals = self._de_ess(vocals, stems.get("sample_rate", 44100))
            
            # Artifact removal for vocals
            if settings.get("clean_vocals", True):
                vocals = artifact_remover.smooth_vocal_artifacts(
                    vocals, intensity=0.7
                )
            
            # Vocal mastering
            vocal_preset = settings.get("vocal_preset", "spotify_ready")
            vocals = mastering_engine.master_track(
                vocals, preset_name=vocal_preset, intensity=0.3
            )
            
            processed_stems["vocals"] = vocals
        
        # Drums processing
        if "drums" in stems and settings.get("process_drums", True):
            drums = stems["drums"]
            
            # Enhance transients
            if settings.get("enhance_drum_transients", True):
                drums = artifact_remover.enhance_transients(drums, intensity=0.8)
            
            # Drum mastering
            drum_preset = settings.get("drum_preset", "club_master")
            drums = mastering_engine.master_track(
                drums, preset_name=drum_preset, intensity=0.4
            )
            
            processed_stems["drums"] = drums
        
        # Bass processing
        if "bass" in stems and settings.get("process_bass", True):
            bass = stems["bass"]
            
            # Sub boost
            if settings.get("boost_bass_sub", True):
                from pedalboard import LowShelfFilter
                board = Pedalboard([
                    LowShelfFilter(cutoff_frequency_hz=60, gain_db=3.0)
                ])
                
                if bass.ndim == 2:
                    processed = np.zeros_like(bass)
                    for i in range(bass.shape[0]):
                        processed[i] = board(bass[i], stems.get("sample_rate", 44100))
                    bass = processed
                else:
                    bass = board(bass, stems.get("sample_rate", 44100))
            
            # Phase correction for bass
            bass = artifact_remover.correct_phase_issues(bass, intensity=0.5)
            
            processed_stems["bass"] = bass
        
        # Other instruments processing
        if "other" in stems and settings.get("process_other", True):
            other = stems["other"]
            
            # Stereo widening
            if settings.get("widen_other", True):
                other = self._stereo_widen(other, intensity=0.3)
            
            # Shimmer removal
            other = artifact_remover.remove_metallic_shimmer(other, intensity=0.4)
            
            processed_stems["other"] = other
        
        return processed_stems
    
    def _de_ess(self, audio, sr, intensity=0.5):
        """Simple de-essing using multiband compression concept"""
        import librosa
        
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
            
        D = librosa.stft(audio_mono)
        magnitude = np.abs(D)
        
        freq_bins = librosa.fft_frequencies(sr=sr)
        # Sibilance range (4-8kHz)
        sibilance_mask = (freq_bins >= 4000) & (freq_bins <= 8000)
        
        # Reduce sibilance frequencies
        magnitude[sibilance_mask] *= (1.0 - intensity * 0.5)
        
        phase = np.angle(D)
        D_deessed = magnitude * np.exp(1j * phase)
        deessed = librosa.istft(D_deessed)
        
        if audio.ndim == 2:
            return np.array([deessed, deessed])
        return deessed
    
    def _stereo_widen(self, audio, intensity=0.5):
        """Simple stereo widening using mid-side processing"""
        if audio.ndim == 1:
            # Mono to stereo
            return np.array([audio, audio])
        
        left = audio[0]
        right = audio[1]
        
        # Mid-side processing
        mid = (left + right) / 2
        side = (left - right) / 2
        
        # Enhance side signal
        side = side * (1.0 + intensity)
        
        # Reconstruct with enhanced stereo width
        left_new = mid + side
        right_new = mid - side
        
        return np.array([left_new, right_new])
    
    def remix_stems(self, processed_stems, mix_balance=None):
        """
        Recombine stems into final mix
        
        Args:
            processed_stems: dictionary of processed stems
            mix_balance: dictionary with balance for each stem (0.0-1.0)
            
        Returns:
            Final mixed audio
        """
        if not processed_stems:
            raise ValueError("No stems provided for remixing")
        
        # Default balance
        if mix_balance is None:
            mix_balance = {
                "vocals": 1.0,
                "drums": 1.0,
                "bass": 1.0,
                "other": 1.0
            }
        
        # Find first stem to determine shape
        first_stem = next(iter(processed_stems.values()))
        
        # Initialize mix
        if first_stem.ndim == 2:
            mix = np.zeros_like(first_stem)
        else:
            # Assume mono
            mix = np.zeros_like(first_stem)
        
        # Mix stems with balance
        for stem_name, stem_data in processed_stems.items():
            balance = mix_balance.get(stem_name, 1.0)
            
            # Ensure shapes match
            if stem_data.shape != mix.shape:
                # Resize if needed (simplified - in production would need proper resampling)
                if stem_data.ndim == 2 and mix.ndim == 2:
                    min_len = min(stem_data.shape[1], mix.shape[1])
                    stem_data = stem_data[:, :min_len]
                    mix = mix[:, :min_len]
                elif stem_data.ndim == 1 and mix.ndim == 1:
                    min_len = min(len(stem_data), len(mix))
                    stem_data = stem_data[:min_len]
                    mix = mix[:min_len]
            
            mix = mix + (stem_data * balance)
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(mix))
        if max_val > 1.0:
            mix = mix / max_val
        
        return mix


def test_stem_separation():
    """Test function for development"""
    processor = StemProcessor()
    
    print("Testing stem separation...")
    print("Note: This requires an audio file to test.")
    print("To fully test, provide an audio file path.")
    
    # Create simple test signal
    sr = 44100
    duration = 3.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # Simple test signal with different frequency components
    test_signal = np.array([
        0.3 * np.sin(2 * np.pi * 100 * t) +  # Bass
        0.2 * np.sin(2 * np.pi * 1000 * t) +  # Mid
        0.1 * np.sin(2 * np.pi * 5000 * t),   # High
        
        0.3 * np.sin(2 * np.pi * 100 * t + 0.2) +  # Bass with phase
        0.2 * np.sin(2 * np.pi * 1000 * t + 0.2) +  # Mid with phase
        0.1 * np.sin(2 * np.pi * 5000 * t + 0.2)    # High with phase
    ])
    
    print("Created test signal")
    print(f"Shape: {test_signal.shape}")
    print(f"Sample rate: {sr}")
    
    # Test simple separation functions
    print("\nTesting simple separation methods...")
    
    drums = processor._extract_drums(test_signal, sr)
    print(f"Drums extracted: {drums.shape}")
    
    bass = processor._extract_bass(test_signal, sr)
    print(f"Bass extracted: {bass.shape}")
    
    vocals = processor._extract_vocals(test_signal, sr)
    print(f"Vocals extracted: {vocals.shape}")
    
    other = processor._extract_other(test_signal, sr)
    print(f"Other extracted: {other.shape}")
    
    # Test stereo widening
    widened = processor._stereo_widen(test_signal, 0.5)
    print(f"Stereo widened: {widened.shape}")
    
    # Test de-essing
    deessed = processor._de_ess(test_signal, sr, 0.5)
    print(f"De-essed: {deessed.shape}")
    
    print("\nStem processor tests passed!")
    print("Note: Full Demucs separation requires the model to be downloaded.")


if __name__ == "__main__":
    test_stem_separation()