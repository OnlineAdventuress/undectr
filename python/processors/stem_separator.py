import numpy as np
import librosa
import soundfile as sf
from scipy import signal, ndimage
import os

try:
    import torch
    import torchaudio
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    DEMUCS_AVAILABLE = True
except ImportError:
    DEMUCS_AVAILABLE = False
    print("⚠️ Demucs not available, using frequency-based separation")

try:
    from pedalboard import Pedalboard, HighShelfFilter, LowShelfFilter, Compressor, Gain
    PEDALBOARD_AVAILABLE = True
except ImportError:
    PEDALBOARD_AVAILABLE = False
    print("⚠️ Pedalboard not available, using numpy-based processing")


class StemProcessor:
    def __init__(self, device='cpu'):
        """
        Initialize stem separator with fallback to frequency-based separation
        
        Args:
            device: 'cpu' or 'cuda' for GPU acceleration (only if torch available)
        """
        self.device = device
        self.model = None
        self._load_model()
        
    def _load_model(self):
        """Try to load Demucs model, fall back to frequency-based if not available"""
        if not DEMUCS_AVAILABLE:
            print("⚠️ Demucs not available, using frequency-based separation")
            self.model = None
            return
            
        try:
            # 'htdemucs' is the recommended model for general use
            self.model = get_model('htdemucs')
            self.model.to(self.device)
            print(f"✅ Demucs model loaded on {self.device}")
        except Exception as e:
            print(f"⚠️ Error loading Demucs model: {e}")
            print("⚠️ Falling back to frequency-based separation")
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
        if self.model is not None and DEMUCS_AVAILABLE:
            return self._separate_with_demucs(audio_path, output_dir)
        else:
            return self._simple_separation(audio_path, output_dir)
    
    def _separate_with_demucs(self, audio_path, output_dir):
        """Separate using Demucs (if available)"""
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
            stems_np = stems.cpu().numpy()
            
            result = {
                'drums': stems_np[0],
                'bass': stems_np[1],
                'other': stems_np[2],
                'vocals': stems_np[3],
                'sample_rate': sr,
                'original_shape': wav.shape
            }
            
            # Save stems if output_dir provided
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                for stem_name, stem_data in result.items():
                    if stem_name not in ['sample_rate', 'original_shape']:
                        output_path = os.path.join(output_dir, f"{stem_name}.wav")
                        sf.write(output_path, stem_data.T, sr)
            
            return result
            
        except Exception as e:
            print(f"⚠️ Demucs separation failed: {e}")
            print("⚠️ Falling back to frequency-based separation")
            return self._simple_separation(audio_path, output_dir)
    
    def _simple_separation(self, audio_path, output_dir=None):
        """
        Simple frequency-based stem separation
        No ML, just frequency filtering
        
        Returns:
            Dictionary with 'drums', 'bass', 'vocals', 'other'
        """
        # Load audio
        audio, sr = sf.read(audio_path)
        
        # Ensure mono for processing
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
        
        stems = {
            'drums': self._extract_drums(audio, sr),
            'bass': self._extract_bass(audio, sr),
            'vocals': self._extract_vocals(audio, sr),
            'other': self._extract_other(audio, sr),
            'sample_rate': sr,
            'original_shape': audio.shape
        }
        
        # Save stems if output_dir provided
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            for stem_name, stem_data in stems.items():
                if stem_name not in ['sample_rate', 'original_shape']:
                    output_path = os.path.join(output_dir, f"{stem_name}.wav")
                    sf.write(output_path, stem_data, sr)
        
        return stems
    
    def _extract_drums(self, audio, sr):
        """Extract drums using high-frequency and transient detection"""
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
            
        D = librosa.stft(audio_mono)
        magnitude = np.abs(D)
        
        # Drums are typically transient and high-frequency
        freq_bins = librosa.fft_frequencies(sr=sr)
        
        # Emphasize transients (sudden amplitude changes)
        envelope = np.abs(librosa.onset.onset_strength(y=audio_mono, sr=sr))
        envelope_normalized = envelope / np.max(envelope) if np.max(envelope) > 0 else envelope
        
        # Apply envelope to magnitude (simplified)
        magnitude_weighted = magnitude * (1 + 0.5 * envelope_normalized[:, np.newaxis])
        
        # Emphasize high frequencies (cymbals, hi-hats)
        high_freq_mask = freq_bins > 2000
        magnitude_weighted[high_freq_mask] *= 1.5
        
        # Emphasize attack portion
        phase = np.angle(D)
        D_drums = magnitude_weighted * np.exp(1j * phase)
        drums_mono = librosa.istft(D_drums)
        
        if audio.ndim == 2:
            return np.array([drums_mono, drums_mono])
        return drums_mono
    
    def _extract_bass(self, audio, sr):
        """Extract bass frequencies (<250Hz)"""
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
            
        D = librosa.stft(audio_mono)
        magnitude = np.abs(D)
        
        # Bass frequencies
        freq_bins = librosa.fft_frequencies(sr=sr)
        bass_mask = freq_bins <= 250
        
        # Reduce non-bass frequencies
        magnitude[~bass_mask] *= 0.3
        
        # Smooth bass frequencies
        magnitude[bass_mask] = ndimage.gaussian_filter(magnitude[bass_mask], sigma=1)
        
        phase = np.angle(D)
        D_bass = magnitude * np.exp(1j * phase)
        bass_mono = librosa.istft(D_bass)
        
        if audio.ndim == 2:
            return np.array([bass_mono, bass_mono])
        return bass_mono
    
    def _extract_vocals(self, audio, sr):
        """Extract vocals (200-4000Hz range)"""
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
            
        D = librosa.stft(audio_mono)
        magnitude = np.abs(D)
        
        freq_bins = librosa.fft_frequencies(sr=sr)
        # Vocal range
        vocal_mask = (freq_bins >= 200) & (freq_bins <= 4000)
        non_vocal_mask = ~vocal_mask
        
        # Reduce non-vocal frequencies
        magnitude[non_vocal_mask] *= 0.3
        
        # Apply harmonic-percussive source separation for vocals
        D_harmonic, D_percussive = librosa.decompose.hpss(D)
        # Vocals are more harmonic
        magnitude = np.abs(D_harmonic)
        
        phase = np.angle(D)
        D_vocals = magnitude * np.exp(1j * phase)
        vocals_mono = librosa.istft(D_vocals)
        
        if audio.ndim == 2:
            return np.array([vocals_mono, vocals_mono])
        return vocals_mono
    
    def _extract_other(self, audio, sr):
        """Extract everything else (mid-range instruments)"""
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
        
        # Also reduce vocals and bass ranges
        vocal_mask = (freq_bins >= 200) & (freq_bins <= 4000)
        bass_mask = freq_bins <= 250
        magnitude[vocal_mask] *= 0.5
        magnitude[bass_mask] *= 0.5
        
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
                vocals, stems.get("sample_rate", 44100),
                preset=vocal_preset,
                target_lufs=settings.get("vocal_lufs", -16)
            )
            processed_stems["vocals"] = vocals
        
        # Drums processing
        if "drums" in stems and settings.get("process_drums", True):
            drums = stems["drums"]
            
            # Compression and limiting for drums
            if settings.get("compress_drums", True):
                drums = mastering_engine.compress_track(
                    drums, stems.get("sample_rate", 44100),
                    ratio=4.0, threshold_db=-15,
                    attack_ms=5, release_ms=100
                )
            
            # EQ boost for punch
            if settings.get("eq_drums", True):
                drums = mastering_engine.eq_track(
                    drums, stems.get("sample_rate", 44100),
                    bass_boost_db=2.0,
                    presence_boost_db=1.5
                )
            
            processed_stems["drums"] = drums
        
        # Bass processing
        if "bass" in stems and settings.get("process_bass", True):
            bass = stems["bass"]
            
            # Compression and limiting
            if settings.get("compress_bass", True):
                bass = mastering_engine.compress_track(
                    bass, stems.get("sample_rate", 44100),
                    ratio=3.0, threshold_db=-12,
                    attack_ms=10, release_ms=150
                )
            
            # Low-end enhancement
            if settings.get("enhance_bass", True):
                bass = mastering_engine.eq_track(
                    bass, stems.get("sample_rate", 44100),
                    bass_boost_db=3.0,
                    low_mid_cut_db=-1.0
                )
            
            processed_stems["bass"] = bass
        
        # Other instruments processing
        if "other" in stems and settings.get("process_other", True):
            other = stems["other"]
            
            # General mastering
            other = mastering_engine.master_track(
                other, stems.get("sample_rate", 44100),
                preset=settings.get("other_preset", "spotify_ready"),
                target_lufs=settings.get("other_lufs", -14)
            )
            
            # Stereo width enhancement
            if settings.get("widen_other", True):
                other = mastering_engine.enhance_stereo_width(
                    other, width=1.2
                )
            
            processed_stems["other"] = other
        
        return processed_stems
    
    def _de_ess(self, audio, sr, threshold=6000, reduction_db=-6):
        """
        Simple de-esser for sibilance reduction
        
        Args:
            audio: input audio
            sr: sample rate
            threshold: frequency threshold for de-essing (Hz)
            reduction_db: how much to reduce (dB)
            
        Returns:
            De-essed audio
        """
        if audio.ndim == 2:
            # Process each channel
            processed = np.zeros_like(audio)
            for i in range(audio.shape[0]):
                processed[i] = self._de_ess_mono(audio[i], sr, threshold, reduction_db)
            return processed
        else:
            return self._de_ess_mono(audio, sr, threshold, reduction_db)
    
    def _de_ess_mono(self, audio_mono, sr, threshold, reduction_db):
        """De-ess mono audio"""
        if PEDALBOARD_AVAILABLE:
            # Simple de-esser using high-shelf filter
            board = Pedalboard([
                HighShelfFilter(
                    cutoff_frequency_hz=threshold,
                    gain_db=reduction_db,
                    q=0.7
                )
            ])
            
            return board(audio_mono, sr)
        else:
            # Fallback: simple high-frequency reduction
            from scipy import signal
            
            # Design a simple filter
            nyquist = sr / 2
            cutoff = threshold / nyquist
            
            # Create a simple IIR filter to reduce highs
            b, a = signal.butter(4, cutoff, btype='low')
            filtered = signal.filtfilt(b, a, audio_mono)
            
            # Mix original and filtered
            return 0.7 * audio_mono + 0.3 * filtered
    
    def export_stems(self, stems, output_dir):
        """
        Export separated stems to WAV files
        
        Args:
            stems: dictionary from separate_stems
            output_dir: directory to save stems
        """
        os.makedirs(output_dir, exist_ok=True)
        sr = stems['sample_rate']
        
        for stem_name, stem_data in stems.items():
            if stem_name not in ['sample_rate', 'original_shape']:
                output_path = os.path.join(output_dir, f"{stem_name}.wav")
                sf.write(output_path, stem_data, sr)
                print(f"Exported {stem_name} to {output_path}")
        
        # Also export the mix (sum of all stems)
        if 'drums' in stems:
            mix = np.zeros_like(stems['drums'])
            for stem_name, stem_data in stems.items():
                if stem_name not in ['sample_rate', 'original_shape']:
                    if stem_data.shape == mix.shape:
                        mix += stem_data
            
            mix_path = os.path.join(output_dir, "mix.wav")
            sf.write(mix_path, mix, sr)
            print(f"Exported mix to {mix_path}")