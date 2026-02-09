#!/usr/bin/env python3
"""
Suno Studio Pro - Main Python Entry Point

This module orchestrates the audio processing pipeline:
1. Loads audio file
2. Removes AI artifacts
3. Applies mastering
4. Optionally separates and processes stems
5. Saves processed audio

Usage:
    python main.py --input input.wav --output output.wav [options]
"""

import argparse
import json
import sys
import os
import time
from pathlib import Path
import traceback

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processors.artifact_remover import ArtifactRemover
from processors.mastering_engine import MasteringEngine
from processors.stem_separator import StemProcessor
from processors.ai_learner import UserPreferenceLearner
from utils.audio_analysis import analyze_audio_metadata
from utils.file_manager import ensure_directory, get_audio_info


class SunoStudioPro:
    """Main processing orchestrator"""
    
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.artifact_remover = ArtifactRemover(sample_rate)
        self.mastering_engine = MasteringEngine(sample_rate)
        self.stem_processor = StemProcessor()
        self.ai_learner = UserPreferenceLearner()
        
    def process_audio(self, input_path, output_path, settings=None, progress_callback=None):
        """
        Main processing pipeline
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save processed audio
            settings: Dictionary of processing settings
            progress_callback: Function to call with progress updates (0-100)
            
        Returns:
            Dictionary with results and metadata
        """
        if settings is None:
            settings = {}
            
        results = {
            "input_path": input_path,
            "output_path": output_path,
            "settings": settings,
            "start_time": time.time(),
            "success": False,
            "errors": []
        }
        
        try:
            # 1. Analyze audio metadata for AI learning
            if progress_callback:
                progress_callback(5, "Analyzing audio...")
            
            metadata = analyze_audio_metadata(input_path)
            results["metadata"] = metadata
            
            # 2. Get AI suggestions if enabled
            if settings.get("ai_learning", True):
                ai_settings = self.ai_learner.predict_optimal_settings(metadata)
                if ai_settings:
                    # Blend AI suggestions with user settings
                    for key, value in ai_settings.items():
                        if key not in settings:
                            settings[key] = value
                    results["ai_suggestions"] = ai_settings
            
            # 3. Load audio
            if progress_callback:
                progress_callback(10, "Loading audio...")
            
            import librosa
            import soundfile as sf
            
            audio, sr = librosa.load(input_path, sr=self.sample_rate, mono=False)
            results["original_channels"] = 2 if audio.ndim == 2 else 1
            results["original_duration"] = len(audio[0] if audio.ndim == 2 else audio) / sr
            
            # 4. Remove AI artifacts
            if settings.get("remove_artifacts", True):
                if progress_callback:
                    progress_callback(20, "Removing AI artifacts...")
                
                intensity = settings.get("artifact_intensity", 0.5)
                audio = self.artifact_remover.process_full(
                    audio, intensity=intensity,
                    progress_callback=lambda msg: progress_callback(
                        20, msg) if progress_callback else None
                )
                results["artifacts_removed"] = True
            
            # 5. Stem separation and individual processing
            if settings.get("separate_stems", False):
                if progress_callback:
                    progress_callback(40, "Separating stems...")
                
                # Create temporary directory for stems
                temp_dir = Path(output_path).parent / "stems_temp"
                temp_dir.mkdir(exist_ok=True)
                
                # Separate stems
                stems = self.stem_processor.separate_stems(
                    input_path, str(temp_dir)
                )
                
                if stems.get("success", False):
                    if progress_callback:
                        progress_callback(50, "Processing individual stems...")
                    
                    # Process each stem individually
                    stem_settings = settings.get("stem_settings", {})
                    processed_stems = self.stem_processor.process_stem_individually(
                        stems, stem_settings
                    )
                    
                    if progress_callback:
                        progress_callback(60, "Remixing stems...")
                    
                    # Remix stems
                    mix_balance = settings.get("mix_balance", {
                        "vocals": 1.0,
                        "drums": 1.0,
                        "bass": 1.0,
                        "other": 1.0
                    })
                    
                    audio = self.stem_processor.remix_stems(
                        processed_stems, mix_balance
                    )
                    
                    # Clean up temp directory
                    import shutil
                    shutil.rmtree(temp_dir)
                    
                    results["stems_separated"] = True
                    results["stem_settings"] = stem_settings
            
            # 6. Apply mastering
            if settings.get("mastering", True):
                if progress_callback:
                    progress_callback(70, "Applying mastering...")
                
                preset = settings.get("preset", "spotify_ready")
                intensity = settings.get("mastering_intensity", 1.0)
                
                audio = self.mastering_engine.master_track(
                    audio, preset_name=preset, intensity=intensity
                )
                
                results["mastering_applied"] = True
                results["mastering_preset"] = preset
            
            # 7. Loudness normalization
            if settings.get("normalize_loudness", True):
                if progress_callback:
                    progress_callback(80, "Normalizing loudness...")
                
                import pyloudnorm as pyln
                
                target_lufs = settings.get("target_lufs", -14)
                meter = pyln.Meter(self.sample_rate)
                
                if audio.ndim == 2:
                    loudness = meter.integrated_loudness(audio.T)
                    audio = pyln.normalize.loudness(audio.T, loudness, target_lufs).T
                else:
                    loudness = meter.integrated_loudness(audio)
                    audio = pyln.normalize.loudness(audio, loudness, target_lufs)
                
                results["loudness_normalized"] = True
                results["target_lufs"] = target_lufs
                results["final_lufs"] = loudness
            
            # 8. Save output
            if progress_callback:
                progress_callback(90, "Saving processed audio...")
            
            # Ensure output directory exists
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine format from extension
            format_ext = Path(output_path).suffix.lower()[1:]  # Remove dot
            if format_ext not in ['wav', 'flac', 'mp3', 'ogg', 'aiff']:
                format_ext = 'wav'  # Default to WAV
            
            if audio.ndim == 2:
                sf.write(output_path, audio.T, self.sample_rate, format=format_ext)
            else:
                sf.write(output_path, audio, self.sample_rate, format=format_ext)
            
            # 9. Update AI learner with results
            if settings.get("ai_learning", True):
                self.ai_learner.learn_from_session(metadata, settings)
            
            # 10. Calculate processing time
            processing_time = time.time() - results["start_time"]
            results["processing_time_seconds"] = processing_time
            results["success"] = True
            
            if progress_callback:
                progress_callback(100, "Processing complete!")
            
            return results
            
        except Exception as e:
            error_msg = f"Error processing audio: {str(e)}"
            print(error_msg, file=sys.stderr)
            traceback.print_exc()
            
            results["success"] = False
            results["errors"].append(error_msg)
            results["processing_time_seconds"] = time.time() - results["start_time"]
            
            return results
    
    def batch_process(self, input_dir, output_dir, settings=None, progress_callback=None):
        """
        Process all audio files in a directory
        
        Args:
            input_dir: Directory containing audio files
            output_dir: Directory to save processed files
            settings: Processing settings
            progress_callback: Function to call with progress updates
            
        Returns:
            List of results for each file
        """
        if settings is None:
            settings = {}
            
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find audio files
        audio_extensions = ['.mp3', '.wav', '.flac', '.aiff', '.m4a', '.ogg']
        audio_files = []
        for ext in audio_extensions:
            audio_files.extend(list(input_dir.glob(f'*{ext}')))
            audio_files.extend(list(input_dir.glob(f'*{ext.upper()}')))
        
        if not audio_files:
            return {"success": False, "error": "No audio files found", "files": []}
        
        results = []
        total_files = len(audio_files)
        
        for i, audio_file in enumerate(audio_files):
            if progress_callback:
                progress_callback(
                    int((i / total_files) * 100),
                    f"Processing {audio_file.name} ({i+1}/{total_files})"
                )
            
            output_file = output_dir / f"processed_{audio_file.name}"
            
            file_result = self.process_audio(
                str(audio_file),
                str(output_file),
                settings,
                lambda progress, msg: progress_callback(
                    int((i / total_files) * 100 + (progress / total_files)),
                    f"{audio_file.name}: {msg}"
                ) if progress_callback else None
            )
            
            results.append(file_result)
        
        return {
            "success": True,
            "total_files": total_files,
            "processed_files": len([r for r in results if r.get("success", False)]),
            "results": results
        }


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description='Suno Studio Pro - Professional audio post-production for Suno AI music'
    )
    parser.add_argument('--input', '-i', required=True,
                       help='Input audio file or directory')
    parser.add_argument('--output', '-o', required=True,
                       help='Output audio file or directory')
    parser.add_argument('--preset', '-p', default='spotify_ready',
                       choices=['spotify_ready', 'youtube_ready', 'club_master',
                                'electronic', 'synthwave', 'vaporwave', 'house',
                                'radio_ready', 'acoustic', 'hiphop'],
                       help='Mastering preset')
    parser.add_argument('--remove-artifacts', action='store_true',
                       help='Remove AI artifacts')
    parser.add_argument('--no-artifacts', dest='remove_artifacts',
                       action='store_false', help='Skip artifact removal')
    parser.add_argument('--separate-stems', action='store_true',
                       help='Separate and process individual stems')
    parser.add_argument('--intensity', type=float, default=0.5,
                       help='Processing intensity (0.0 to 1.0)')
    parser.add_argument('--target-lufs', type=float, default=-14.0,
                       help='Target loudness in LUFS')
    parser.add_argument('--format', default='wav',
                       choices=['wav', 'flac', 'mp3', 'ogg', 'aiff'],
                       help='Output format')
    parser.add_argument('--batch', '-b', action='store_true',
                       help='Batch process directory')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    parser.set_defaults(remove_artifacts=True)
    
    args = parser.parse_args()
    
    # Create processor
    processor = SunoStudioPro()
    
    # Prepare settings
    settings = {
        "preset": args.preset,
        "remove_artifacts": args.remove_artifacts,
        "separate_stems": args.separate_stems,
        "artifact_intensity": args.intensity,
        "mastering_intensity": args.intensity,
        "target_lufs": args.target_lufs,
        "normalize_loudness": True,
        "mastering": True,
        "ai_learning": True
    }
    
    def progress_callback(percent, message):
        if args.verbose:
            print(f"[{percent}%] {message}")
        else:
            # Simple progress bar
            bar_length = 40
            filled_length = int(bar_length * percent / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            print(f'\rProgress: |{bar}| {percent}% {message}', end='', flush=True)
            if percent == 100:
                print()  # New line when complete
    
    try:
        if args.batch:
            # Batch processing
            print(f"Batch processing: {args.input} -> {args.output}")
            results = processor.batch_process(
                args.input, args.output, settings, progress_callback
            )
            
            if results["success"]:
                print(f"\n✅ Processed {results['processed_files']}/{results['total_files']} files successfully")
                if args.verbose:
                    for i, result in enumerate(results["results"]):
                        if result.get("success", False):
                            print(f"  {i+1}. {Path(result['input_path']).name} -> {Path(result['output_path']).name}")
                            print(f"     Duration: {result.get('original_duration', 0):.1f}s")
                            print(f"     Processing time: {result.get('processing_time_seconds', 0):.1f}s")
            else:
                print(f"\n❌ Batch processing failed: {results.get('error', 'Unknown error')}")
                sys.exit(1)
                
        else:
            # Single file processing
            print(f"Processing: {args.input} -> {args.output}")
            result = processor.process_audio(
                args.input, args.output, settings, progress_callback
            )
            
            if result["success"]:
                print(f"\n✅ Processing complete!")
                print(f"   Input: {Path(result['input_path']).name}")
                print(f"   Output: {Path(result['output_path']).name}")
                print(f"   Duration: {result.get('original_duration', 0):.1f}s")
                print(f"   Processing time: {result.get('processing_time_seconds', 0):.1f}s")
                
                if args.verbose:
                    print(f"   Settings: {json.dumps(result['settings'], indent=2)}")
                    if 'ai_suggestions' in result:
                        print(f"   AI Suggestions: {json.dumps(result['ai_suggestions'], indent=2)}")
            else:
                print(f"\n❌ Processing failed")
                for error in result.get("errors", []):
                    print(f"   Error: {error}")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()