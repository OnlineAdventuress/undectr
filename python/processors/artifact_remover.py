"""
ArtifactRemover - Fallback Version
Simple artifact removal without pedalboard dependency
"""

import numpy as np
import librosa
import soundfile as sf
from scipy import signal

try:
    from pedalboard import Pedalboard, HighShelfFilter, LowShelfFilter
    PEDALBOARD_AVAILABLE = True
except ImportError:
    PEDALBOARD_AVAILABLE = False
    print("⚠️ Pedalboard not available, using numpy-based processing")

class ArtifactRemover:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        
    def remove_metallic_shimmer(self, audio, intensity=0.5):
        """
        Remove 8-16kHz metallic ringing characteristic of Suno
        
        Args:
            audio: numpy array of audio data (mono or stereo)
            intensity: 0.0 to 1.0, how aggressive to be
            
        Returns:
            Processed audio
        """
        # Dynamic high-shelf reduction
        shimmer_freq = 11000  # Hz (Suno's signature frequency)
        reduction_db = -8 * intensity
        
        if PEDALBOARD_AVAILABLE:
            # Apply only if audio is 2D (stereo) or 1D (mono)
            if audio.ndim == 2:
                # Process each channel
                processed = np.zeros_like(audio)
                for i in range(audio.shape[0]):
                    board = Pedalboard([
                        HighShelfFilter(
                            cutoff_frequency_hz=shimmer_freq,
                            gain_db=reduction_db
                        )
                    ])
                    processed[i] = board(audio[i], self.sample_rate)
                return processed
            else:
                # Mono
                board = Pedalboard([
                    HighShelfFilter(
                        cutoff_frequency_hz=shimmer_freq,
                        gain_db=reduction_db
                    )
                ])
                return board(audio, self.sample_rate)
        else:
            # Fallback: simple high-frequency filter
            nyquist = self.sample_rate / 2
            cutoff = shimmer_freq / nyquist
            
            # Create a simple Butterworth low-pass filter
            b, a = signal.butter(4, cutoff, btype='low')
            
            if audio.ndim == 2:
                processed = np.zeros_like(audio)
                for i in range(audio.shape[0]):
                    processed[i] = signal.filtfilt(b, a, audio[i])
                return processed
            else:
                return signal.filtfilt(b, a, audio)
    
    def smooth_vocal_artifacts(self, audio, intensity=0.5):
        """
        Smooth out robotic/choppy vocal artifacts
        
        Args:
            audio: numpy array (mono or stereo)
            intensity: 0.0 to 1.0
            
        Returns:
            Smoothed audio
        """
        # Use median filtering to smooth choppy artifacts
        window_size = int(0.02 * self.sample_rate)  # 20ms window
        window_size = max(3, window_size)  # Minimum window size
        
        if audio.ndim == 2:
            processed = np.zeros_like(audio)
            for i in range(audio.shape[0]):
                processed[i] = signal.medfilt(audio[i], kernel_size=window_size)
            return processed
        else:
            return signal.medfilt(audio, kernel_size=window_size)
    
    def reduce_sibilance(self, audio, threshold_db=-15):
        """
        Reduce harsh sibilance (de-esser)
        
        Args:
            audio: numpy array
            threshold_db: threshold for sibilance reduction
            
        Returns:
            De-essed audio
        """
        # Simple de-essing using multiband compression
        if audio.ndim == 2:
            # Process each channel
            processed = np.zeros_like(audio)
            for i in range(audio.shape[0]):
                processed[i] = self._de_ess_mono(audio[i], threshold_db)
            return processed
        else:
            return self._de_ess_mono(audio, threshold_db)
    
    def _de_ess_mono(self, audio_mono, threshold_db):
        """Simple mono de-esser"""
        # Split into bands
        nyquist = self.sample_rate / 2
        
        # High band for sibilance (3-8kHz)
        b_high, a_high = signal.butter(4, [3000/nyquist, 8000/nyquist], btype='band')
        high_band = signal.filtfilt(b_high, a_high, audio_mono)
        
        # Low band for everything else
        b_low, a_low = signal.butter(4, 3000/nyquist, btype='low')
        low_band = signal.filtfilt(b_low, a_low, audio_mono)
        
        # Detect sibilance (RMS of high band)
        window = int(0.01 * self.sample_rate)  # 10ms
        rms_high = np.sqrt(np.convolve(high_band**2, np.ones(window)/window, mode='same'))
        
        # Create gain reduction envelope
        threshold = 10**(threshold_db/20)
        gain_reduction = np.ones_like(audio_mono)
        mask = rms_high > threshold
        if np.any(mask):
            # Reduce gain where sibilance is detected
            gain_reduction[mask] = 0.7
        
        # Apply gain reduction to high band
        high_band_processed = high_band * gain_reduction
        
        # Recombine bands
        return low_band + high_band_processed
    
    def remove_clicks(self, audio, threshold=0.1):
        """
        Remove sudden clicks/pops
        
        Args:
            audio: numpy array
            threshold: click detection threshold (0.0-1.0)
            
        Returns:
            Cleaned audio
        """
        if audio.ndim == 2:
            processed = np.zeros_like(audio)
            for i in range(audio.shape[0]):
                processed[i] = self._remove_clicks_mono(audio[i], threshold)
            return processed
        else:
            return self._remove_clicks_mono(audio, threshold)
    
    def _remove_clicks_mono(self, audio_mono, threshold):
        """Remove clicks from mono audio"""
        # Detect abrupt changes
        diff = np.abs(np.diff(audio_mono))
        diff_normalized = diff / np.max(diff) if np.max(diff) > 0 else diff
        
        # Find click locations
        click_mask = diff_normalized > threshold
        
        # Interpolate click locations
        result = audio_mono.copy()
        if np.any(click_mask):
            # Get indices of clicks
            click_indices = np.where(click_mask)[0]
            
            # Interpolate around clicks
            for idx in click_indices:
                if idx > 2 and idx < len(audio_mono) - 2:
                    # Replace with average of neighbors
                    result[idx] = np.mean([audio_mono[idx-2], audio_mono[idx+2]])
        
        return result
    
    def analyze_artifacts(self, audio_path):
        """
        Analyze audio for Suno AI artifacts
        
        Returns:
            Dictionary with artifact analysis
        """
        audio, sr = sf.read(audio_path)
        
        # Basic analysis
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
        
        # FFT analysis
        D = librosa.stft(audio_mono)
        magnitude = np.abs(D)
        freq_bins = librosa.fft_frequencies(sr=sr)
        
        # Check for Suno's metallic shimmer (8-16kHz)
        shimmer_mask = (freq_bins >= 8000) & (freq_bins <= 16000)
        shimmer_strength = np.mean(magnitude[shimmer_mask]) / np.mean(magnitude) if np.mean(magnitude) > 0 else 0
        
        # Check for robotic vocals (unnatural periodicity)
        autocorr = np.correlate(audio_mono, audio_mono, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # Find peaks in autocorrelation (periodicity)
        peaks, _ = signal.find_peaks(autocorr[:int(0.1*sr)])  # First 100ms
        periodicity_score = len(peaks) / 10  # Normalized
        
        # Check for sibilance
        b_high, a_high = signal.butter(4, [3000/(sr/2), 8000/(sr/2)], btype='band')
        high_band = signal.filtfilt(b_high, a_high, audio_mono)
        sibilance_score = np.std(high_band) / np.std(audio_mono) if np.std(audio_mono) > 0 else 0
        
        return {
            'shimmer_strength': float(shimmer_strength),
            'periodicity_score': float(periodicity_score),
            'sibilance_score': float(sibilance_score),
            'recommended_intensity': min(1.0, shimmer_strength * 2),
            'has_metallic_shimmer': shimmer_strength > 0.1,
            'has_robotic_vocals': periodicity_score > 0.3,
            'has_harsh_sibilance': sibilance_score > 0.2
        }