import pyloudnorm as pyln
from pedalboard import (
    Pedalboard, Compressor, Limiter, HighpassFilter, Gain,
    LowShelfFilter, HighShelfFilter, Reverb, Delay,
    Phaser, Chorus, Distortion
)
import numpy as np


class MasteringEngine:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.presets = self._load_genre_presets()
        
    def _load_genre_presets(self):
        """Define genre-specific mastering settings"""
        return {
            "electronic": {
                "bass_boost_db": 2.5,
                "treble_adjust_db": 1.0,
                "compression_ratio": 4,
                "attack_ms": 5,
                "release_ms": 100,
                "threshold_db": -20,
                "stereo_width": 1.2,
                "target_lufs": -10,
                "reverb_amount": 0.1,
                "excitement": 0.2
            },
            "synthwave": {
                # For your Enda Echo channel
                "bass_boost_db": 2.0,
                "treble_adjust_db": 2.0,
                "compression_ratio": 5,
                "attack_ms": 10,
                "release_ms": 150,
                "threshold_db": -18,
                "stereo_width": 1.3,
                "target_lufs": -11,
                "reverb_amount": 0.3,
                "excitement": 0.4,
                "tape_saturation": 0.1
            },
            "vaporwave": {
                # For your VinylByte channel
                "bass_boost_db": 1.5,
                "treble_adjust_db": -1.0,
                "compression_ratio": 3,
                "attack_ms": 20,
                "release_ms": 200,
                "threshold_db": -15,
                "stereo_width": 1.4,
                "target_lufs": -14,
                "reverb_amount": 0.5,
                "excitement": 0.1,
                "lo_fi": 0.3
            },
            "house": {
                # For your Echo Macalla channel
                "bass_boost_db": 3.0,
                "treble_adjust_db": 1.5,
                "compression_ratio": 6,
                "attack_ms": 3,
                "release_ms": 80,
                "threshold_db": -22,
                "stereo_width": 1.1,
                "target_lufs": -9,
                "reverb_amount": 0.15,
                "excitement": 0.3
            },
            "spotify_ready": {
                "bass_boost_db": 2.0,
                "treble_adjust_db": 0.5,
                "compression_ratio": 4,
                "attack_ms": 5,
                "release_ms": 100,
                "threshold_db": -20,
                "stereo_width": 1.15,
                "target_lufs": -14,
                "reverb_amount": 0.05,
                "excitement": 0.1
            },
            "youtube_ready": {
                "bass_boost_db": 2.0,
                "treble_adjust_db": 1.0,
                "compression_ratio": 5,
                "attack_ms": 5,
                "release_ms": 90,
                "threshold_db": -19,
                "stereo_width": 1.15,
                "target_lufs": -13,
                "reverb_amount": 0.08,
                "excitement": 0.15
            },
            "club_master": {
                "bass_boost_db": 4.0,
                "treble_adjust_db": 2.0,
                "compression_ratio": 8,
                "attack_ms": 2,
                "release_ms": 50,
                "threshold_db": -25,
                "stereo_width": 1.0,
                "target_lufs": -8,
                "reverb_amount": 0.2,
                "excitement": 0.4
            },
            "radio_ready": {
                "bass_boost_db": 2.5,
                "treble_adjust_db": 1.2,
                "compression_ratio": 6,
                "attack_ms": 4,
                "release_ms": 80,
                "threshold_db": -21,
                "stereo_width": 1.1,
                "target_lufs": -10,
                "reverb_amount": 0.1,
                "excitement": 0.25
            },
            "acoustic": {
                "bass_boost_db": 1.0,
                "treble_adjust_db": 0.8,
                "compression_ratio": 3,
                "attack_ms": 15,
                "release_ms": 200,
                "threshold_db": -15,
                "stereo_width": 1.2,
                "target_lufs": -16,
                "reverb_amount": 0.2,
                "excitement": 0.05
            },
            "hiphop": {
                "bass_boost_db": 3.5,
                "treble_adjust_db": 0.3,
                "compression_ratio": 5,
                "attack_ms": 5,
                "release_ms": 100,
                "threshold_db": -20,
                "stereo_width": 1.05,
                "target_lufs": -11,
                "reverb_amount": 0.15,
                "excitement": 0.2
            }
        }
    
    def _create_mastering_chain(self, preset):
        """Build the mastering signal chain based on preset"""
        board_components = []
        
        # 1. Clean up sub-bass rumble
        board_components.append(
            HighpassFilter(cutoff_frequency_hz=30)
        )
        
        # 2. Bass boost
        if preset.get("bass_boost_db", 0) != 0:
            board_components.append(
                LowShelfFilter(
                    cutoff_frequency_hz=80,
                    gain_db=preset["bass_boost_db"]
                )
            )
        
        # 3. Treble adjustment
        if preset.get("treble_adjust_db", 0) != 0:
            board_components.append(
                HighShelfFilter(
                    cutoff_frequency_hz=8000,
                    gain_db=preset["treble_adjust_db"]
                )
            )
        
        # 4. Excitement/harmonic excitement (subtle)
        if preset.get("excitement", 0) > 0:
            board_components.append(
                Distortion(
                    drive_db=preset["excitement"] * 6  # 0-6dB based on excitement
                )
            )
        
        # 5. Main compression
        board_components.append(
            Compressor(
                threshold_db=preset.get("threshold_db", -20),
                ratio=preset.get("compression_ratio", 4),
                attack_ms=preset.get("attack_ms", 5),
                release_ms=preset.get("release_ms", 100)
            )
        )
        
        # 6. Stereo width adjustment (mid-side processing)
        # This is simplified - actual stereo width would need more complex processing
        
        # 7. Reverb (subtle)
        if preset.get("reverb_amount", 0) > 0:
            board_components.append(
                Reverb(
                    room_size=0.3 + preset["reverb_amount"] * 0.5,
                    damping=0.5,
                    wet_level=preset["reverb_amount"] * 0.3,
                    dry_level=1.0
                )
            )
        
        # 8. Tape saturation for certain genres
        if preset.get("tape_saturation", 0) > 0:
            board_components.append(
                Distortion(
                    drive_db=preset["tape_saturation"] * 3,
                    tone=0.7
                )
            )
        
        # 9. Lo-fi effect for vaporwave
        if preset.get("lo_fi", 0) > 0:
            board_components.append(
                Phaser(
                    rate_hz=0.5,
                    depth=preset["lo_fi"],
                    centre_frequency_hz=800,
                    feedback=0.2
                )
            )
        
        # 10. Final limiting
        board_components.append(
            Limiter(
                threshold_db=-1.0,
                release_ms=50
            )
        )
        
        return Pedalboard(board_components)
    
    def master_track(self, audio, preset_name="spotify_ready", intensity=1.0):
        """
        Apply professional mastering chain
        
        Args:
            audio: numpy array of audio data
            preset_name: name of preset to use
            intensity: 0.0 to 1.0, how much to apply the preset
            
        Returns:
            Mastered audio
        """
        # Get preset or default
        preset = self.presets.get(preset_name, self.presets["spotify_ready"])
        
        # Adjust preset parameters based on intensity
        adjusted_preset = preset.copy()
        if intensity != 1.0:
            # Scale most parameters by intensity
            for key in ["bass_boost_db", "treble_adjust_db", "reverb_amount",
                       "excitement", "tape_saturation", "lo_fi"]:
                if key in adjusted_preset:
                    adjusted_preset[key] *= intensity
        
        # Build mastering chain
        board = self._create_mastering_chain(adjusted_preset)
        
        # Process audio
        if audio.ndim == 2:
            # Stereo
            processed = np.zeros_like(audio)
            for i in range(audio.shape[0]):
                processed[i] = board(audio[i], self.sample_rate)
        else:
            # Mono
            processed = board(audio, self.sample_rate)
        
        # Loudness normalization
        processed = self._normalize_loudness(processed, adjusted_preset["target_lufs"])
        
        return processed
    
    def _normalize_loudness(self, audio, target_lufs):
        """Normalize audio to target LUFS"""
        try:
            meter = pyln.Meter(self.sample_rate)
            
            if audio.ndim == 2:
                # Stereo
                loudness = meter.integrated_loudness(audio.T)
                normalized = pyln.normalize.loudness(
                    audio.T, loudness, target_lufs
                ).T
            else:
                # Mono
                loudness = meter.integrated_loudness(audio)
                normalized = pyln.normalize.loudness(
                    audio, loudness, target_lufs
                )
            
            return normalized
        except Exception as e:
            print(f"Loudness normalization failed: {e}")
            return audio
    
    def analyze_audio(self, audio):
        """Analyze audio characteristics for smart mastering suggestions"""
        if audio.ndim == 2:
            # Convert to mono for analysis
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
        
        analysis = {
            "loudness": None,
            "dynamic_range": None,
            "frequency_balance": None,
            "transient_energy": None
        }
        
        try:
            # Calculate loudness
            meter = pyln.Meter(self.sample_rate)
            if audio.ndim == 2:
                analysis["loudness"] = meter.integrated_loudness(audio.T)
            else:
                analysis["loudness"] = meter.integrated_loudness(audio)
            
            # Calculate dynamic range (simplified)
            rms = np.sqrt(np.mean(audio_mono**2))
            peak = np.max(np.abs(audio_mono))
            analysis["dynamic_range"] = 20 * np.log10(peak / (rms + 1e-10))
            
            # Frequency balance (low vs high energy)
            fft = np.fft.rfft(audio_mono)
            freqs = np.fft.rfftfreq(len(audio_mono), 1/self.sample_rate)
            
            low_freq_mask = freqs < 200
            mid_freq_mask = (freqs >= 200) & (freqs < 2000)
            high_freq_mask = freqs >= 2000
            
            low_energy = np.sum(np.abs(fft[low_freq_mask])**2)
            mid_energy = np.sum(np.abs(fft[mid_freq_mask])**2)
            high_energy = np.sum(np.abs(fft[high_freq_mask])**2)
            
            total_energy = low_energy + mid_energy + high_energy + 1e-10
            analysis["frequency_balance"] = {
                "low_percent": low_energy / total_energy,
                "mid_percent": mid_energy / total_energy,
                "high_percent": high_energy / total_energy
            }
            
            # Transient energy (simplified)
            envelope = np.abs(signal.hilbert(audio_mono))
            transient_energy = np.mean(np.diff(envelope)**2)
            analysis["transient_energy"] = transient_energy
            
        except Exception as e:
            print(f"Audio analysis failed: {e}")
        
        return analysis
    
    def suggest_preset(self, audio_analysis):
        """Suggest best preset based on audio analysis"""
        if not audio_analysis.get("frequency_balance"):
            return "spotify_ready"
        
        balance = audio_analysis["frequency_balance"]
        
        # Logic for preset suggestion
        if balance["low_percent"] > 0.4:
            # Bass-heavy track
            if balance["high_percent"] > 0.3:
                return "electronic"
            else:
                return "hiphop"
        elif balance["high_percent"] > 0.4:
            # Bright track
            if audio_analysis.get("dynamic_range", 0) > 15:
                return "acoustic"
            else:
                return "synthwave"
        elif audio_analysis.get("loudness", -20) > -12:
            # Already loud track
            return "spotify_ready"
        elif audio_analysis.get("dynamic_range", 0) < 8:
            # Compressed track
            return "radio_ready"
        else:
            return "spotify_ready"


def test_mastering():
    """Test function for development"""
    engine = MasteringEngine()
    
    # Create a simple test signal
    sample_rate = 44100
    duration = 5.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create stereo test signal
    left_channel = 0.5 * np.sin(2 * np.pi * 440 * t)  # A4 sine wave
    right_channel = 0.5 * np.sin(2 * np.pi * 440 * t + 0.5)  # Phase shifted
    test_audio = np.array([left_channel, right_channel])
    
    print("Testing mastering engine...")
    
    # Test all presets
    for preset_name in ["spotify_ready", "electronic", "synthwave", "club_master"]:
        print(f"Testing {preset_name} preset...")
        mastered = engine.master_track(test_audio, preset_name)
        print(f"✓ {preset_name} complete")
    
    # Test audio analysis
    print("\nTesting audio analysis...")
    analysis = engine.analyze_audio(test_audio)
    print(f"Loudness: {analysis.get('loudness'):.1f} LUFS")
    print(f"Dynamic range: {analysis.get('dynamic_range'):.1f} dB")
    
    # Test preset suggestion
    suggested = engine.suggest_preset(analysis)
    print(f"Suggested preset: {suggested}")
    
    print("\nAll mastering tests passed!")


if __name__ == "__main__":
    test_mastering()