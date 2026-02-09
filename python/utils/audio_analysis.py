"""
Audio analysis utilities for Suno Studio Pro

Provides metadata extraction and analysis for audio files.
Used by AI learner and for audio processing decisions.
"""

import librosa
import numpy as np
from scipy import signal
import soundfile as sf
from pathlib import Path


def analyze_audio_metadata(file_path):
    """
    Analyze audio file and extract metadata
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Dictionary with audio metadata
    """
    try:
        # Load audio
        audio, sr = librosa.load(file_path, sr=None, mono=False)
        
        # Convert to mono for some analyses
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
        
        # Basic metadata
        duration = len(audio_mono) / sr
        
        # Calculate loudness (LUFS)
        import pyloudnorm as pyln
        meter = pyln.Meter(sr)
        if audio.ndim == 2:
            loudness = meter.integrated_loudness(audio.T)
        else:
            loudness = meter.integrated_loudness(audio)
        
        # Calculate BPM (tempo)
        tempo, _ = librosa.beat.beat_track(y=audio_mono, sr=sr)
        
        # Estimate key
        chroma = librosa.feature.chroma_cqt(y=audio_mono, sr=sr)
        key_strength = np.max(chroma, axis=0)
        estimated_key = np.argmax(np.sum(chroma, axis=1))
        
        # Key names
        key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key_name = key_names[estimated_key % 12]
        
        # Determine if major or minor (simplified)
        # Look at relative strengths of major vs minor third
        third_index = (estimated_key + 4) % 12  # Major third
        minor_third_index = (estimated_key + 3) % 12  # Minor third
        
        major_strength = np.sum(chroma[third_index])
        minor_strength = np.sum(chroma[minor_third_index])
        
        mode = 'major' if major_strength > minor_strength else 'minor'
        
        # Spectral centroid (brightness)
        spectral_centroid = librosa.feature.spectral_centroid(y=audio_mono, sr=sr)
        avg_spectral_centroid = np.mean(spectral_centroid)
        
        # Spectral rolloff (high frequency content)
        spectral_rolloff = librosa.feature.spectral_rolloff(y=audio_mono, sr=sr)
        avg_spectral_rolloff = np.mean(spectral_rolloff)
        
        # Zero crossing rate (noisiness)
        zcr = librosa.feature.zero_crossing_rate(audio_mono)
        avg_zcr = np.mean(zcr)
        
        # RMS energy
        rms = librosa.feature.rms(y=audio_mono)
        avg_rms = np.mean(rms)
        
        # Dynamic range (peak to RMS ratio)
        peak = np.max(np.abs(audio_mono))
        dynamic_range_db = 20 * np.log10(peak / (avg_rms + 1e-10))
        
        # Frequency balance analysis
        fft = np.fft.rfft(audio_mono)
        freqs = np.fft.rfftfreq(len(audio_mono), 1/sr)
        
        # Define frequency bands
        low_mask = freqs < 200
        mid_mask = (freqs >= 200) & (freqs < 2000)
        high_mask = freqs >= 2000
        
        low_energy = np.sum(np.abs(fft[low_mask])**2)
        mid_energy = np.sum(np.abs(fft[mid_mask])**2)
        high_energy = np.sum(np.abs(fft[high_mask])**2)
        
        total_energy = low_energy + mid_energy + high_energy + 1e-10
        
        # Harmonic-percussive separation
        harmonic, percussive = librosa.decompose.hpss(audio_mono)
        harmonic_ratio = np.sum(np.abs(harmonic)**2) / (np.sum(np.abs(audio_mono)**2) + 1e-10)
        
        # Detect vocals (simplified)
        # Look for energy in typical vocal range with harmonic content
        vocal_range_mask = (freqs >= 85) & (freqs <= 255)
        vocal_energy = np.sum(np.abs(fft[vocal_range_mask])**2)
        has_vocals = vocal_energy > (total_energy * 0.05) and harmonic_ratio > 0.3
        
        # Estimate genre (simplified)
        genre = estimate_genre(
            tempo[0] if len(tempo) > 0 else 120,
            avg_spectral_centroid,
            avg_zcr,
            harmonic_ratio,
            dynamic_range_db
        )
        
        # Stereo information
        if audio.ndim == 2:
            # Phase correlation
            correlation = np.corrcoef(audio[0], audio[1])[0, 1]
            
            # Stereo width (simplified)
            mid = (audio[0] + audio[1]) / 2
            side = (audio[0] - audio[1]) / 2
            side_energy = np.sum(side**2)
            mid_energy = np.sum(mid**2)
            stereo_width = side_energy / (mid_energy + 1e-10)
        else:
            correlation = 1.0  # Mono = perfect correlation
            stereo_width = 0.0
        
        # Build metadata dictionary
        metadata = {
            "file_path": str(file_path),
            "file_name": Path(file_path).name,
            "file_size": Path(file_path).stat().st_size,
            "sample_rate": sr,
            "channels": 2 if audio.ndim == 2 else 1,
            "duration_seconds": duration,
            "loudness_lufs": float(loudness),
            "tempo_bpm": float(tempo[0]) if len(tempo) > 0 else 120.0,
            "key": key_name,
            "mode": mode,
            "key_strength": float(np.max(key_strength)),
            "spectral_centroid": float(avg_spectral_centroid),
            "spectral_rolloff": float(avg_spectral_rolloff),
            "zero_crossing_rate": float(avg_zcr),
            "rms_energy": float(avg_rms),
            "dynamic_range_db": float(dynamic_range_db),
            "frequency_balance": {
                "low_percent": float(low_energy / total_energy),
                "mid_percent": float(mid_energy / total_energy),
                "high_percent": float(high_energy / total_energy)
            },
            "harmonic_ratio": float(harmonic_ratio),
            "has_vocals": bool(has_vocals),
            "estimated_genre": genre,
            "stereo_correlation": float(correlation),
            "stereo_width": float(stereo_width),
            "analysis_timestamp": np.datetime64('now').astype(str)
        }
        
        return metadata
        
    except Exception as e:
        print(f"Error analyzing audio {file_path}: {e}")
        # Return minimal metadata
        return {
            "file_path": str(file_path),
            "file_name": Path(file_path).name,
            "error": str(e),
            "duration_seconds": 0,
            "loudness_lufs": -20,
            "tempo_bpm": 120,
            "key": "C",
            "mode": "major",
            "has_vocals": False,
            "estimated_genre": "unknown"
        }


def estimate_genre(tempo, spectral_centroid, zcr, harmonic_ratio, dynamic_range):
    """
    Simple genre estimation based on audio features
    
    Returns:
        Genre string
    """
    # Rule-based genre estimation
    if tempo > 160 and zcr > 0.1:
        return "hardcore" if spectral_centroid > 2000 else "drum_and_bass"
    elif tempo > 128:
        if harmonic_ratio > 0.6:
            return "trance" if spectral_centroid > 1500 else "house"
        else:
            return "techno"
    elif tempo > 100:
        if harmonic_ratio > 0.7:
            return "synthwave" if spectral_centroid < 1000 else "pop"
        else:
            return "hiphop" if dynamic_range < 8 else "rock"
    elif tempo > 80:
        if harmonic_ratio > 0.8:
            return "vaporwave" if spectral_centroid < 800 else "indie"
        else:
            return "ambient" if zcr < 0.05 else "lo_fi"
    else:
        return "ambient" if harmonic_ratio > 0.5 else "drone"


from .file_manager import get_audio_info


def calculate_loudness_range(audio, sr):
    """
    Calculate loudness range (LRA) in LU
    
    Args:
        audio: Audio data
        sr: Sample rate
        
    Returns:
        Loudness range in LU
    """
    try:
        import pyloudnorm as pyln
        
        meter = pyln.Meter(sr)
        
        if audio.ndim == 2:
            lra = pyln.loudness_range(audio.T, meter)
        else:
            lra = pyln.loudness_range(audio, meter)
        
        return float(lra)
    except:
        return 0.0


def detect_silence(audio, sr, threshold_db=-60):
    """
    Detect silent portions in audio
    
    Args:
        audio: Audio data
        sr: Sample rate
        threshold_db: Silence threshold in dB
        
    Returns:
        List of (start_time, end_time) tuples for silent regions
    """
    if audio.ndim == 2:
        audio_mono = np.mean(audio, axis=0)
    else:
        audio_mono = audio
    
    # Convert threshold to linear
    threshold = 10 ** (threshold_db / 20)
    
    # Calculate RMS in short windows
    window_size = int(0.1 * sr)  # 100ms windows
    hop_size = window_size // 2
    
    silent_regions = []
    in_silence = False
    silence_start = 0
    
    for i in range(0, len(audio_mono) - window_size, hop_size):
        window = audio_mono[i:i + window_size]
        rms = np.sqrt(np.mean(window ** 2))
        
        if rms < threshold and not in_silence:
            # Start of silence
            in_silence = True
            silence_start = i / sr
        elif rms >= threshold and in_silence:
            # End of silence
            in_silence = False
            silence_end = i / sr
            if silence_end - silence_start > 0.5:  # Only report > 0.5s silences
                silent_regions.append((silence_start, silence_end))
    
    # Handle trailing silence
    if in_silence:
        silence_end = len(audio_mono) / sr
        if silence_end - silence_start > 0.5:
            silent_regions.append((silence_start, silence_end))
    
    return silent_regions


def analyze_transients(audio, sr):
    """
    Analyze transients (percussive attacks)
    
    Args:
        audio: Audio data
        sr: Sample rate
        
    Returns:
        Dictionary with transient analysis
    """
    if audio.ndim == 2:
        audio_mono = np.mean(audio, axis=0)
    else:
        audio_mono = audio
    
    # Onset detection
    onset_env = librosa.onset.onset_strength(y=audio_mono, sr=sr)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env, sr=sr, units='time'
    )
    
    # Calculate transient density (onsets per second)
    duration = len(audio_mono) / sr
    transient_density = len(onset_frames) / duration if duration > 0 else 0
    
    # Calculate average transient strength
    avg_transient_strength = np.mean(onset_env) if len(onset_env) > 0 else 0
    
    return {
        "transient_density": float(transient_density),
        "avg_transient_strength": float(avg_transient_strength),
        "onset_times": onset_frames.tolist() if hasattr(onset_frames, 'tolist') else list(onset_frames)
    }


def test_analysis():
    """Test the audio analysis functions"""
    print("Testing audio analysis...")
    
    # Create a simple test signal
    sr = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # Create stereo test signal
    test_audio = np.array([
        0.5 * np.sin(2 * np.pi * 440 * t),  # A4 sine wave
        0.5 * np.sin(2 * np.pi * 440 * t + 0.5)  # Phase shifted
    ])
    
    # Save test file
    test_file = Path("/tmp/test_audio_analysis.wav")
    sf.write(test_file, test_audio.T, sr)
    
    try:
        # Test metadata analysis
        metadata = analyze_audio_metadata(test_file)
        print(f"Metadata analysis complete:")
        print(f"  Duration: {metadata.get('duration_seconds'):.2f}s")
        print(f"  Loudness: {metadata.get('loudness_lufs'):.1f} LUFS")
        print(f"  Tempo: {metadata.get('tempo_bpm'):.1f} BPM")
        print(f"  Key: {metadata.get('key')} {metadata.get('mode')}")
        print(f"  Genre: {metadata.get('estimated_genre')}")
        print(f"  Has vocals: {metadata.get('has_vocals')}")
        
        # Test audio info
        info = get_audio_info(test_file)
        print(f"\nAudio info:")
        print(f"  Channels: {info.get('channels')}")
        print(f"  Sample rate: {info.get('samplerate')} Hz")
        print(f"  Format: {info.get('format')}")
        
        # Test transient analysis
        transients = analyze_transients(test_audio, sr)
        print(f"\nTransient analysis:")
        print(f"  Density: {transients.get('transient_density'):.2f}/s")
        print(f"  Strength: {transients.get('avg_transient_strength'):.3f}")
        
        # Test silence detection
        silences = detect_silence(test_audio, sr)
        print(f"\nSilence detection: Found {len(silences)} silent regions")
        
        # Clean up
        test_file.unlink()
        
        print("\n✅ All audio analysis tests passed!")
        
    except Exception as e:
        print(f"❌ Analysis test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_analysis()