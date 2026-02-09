"""
File management utilities for Suno Studio Pro

Handles file operations, directory management, and audio file utilities.
"""

import os
import shutil
import hashlib
import json
from pathlib import Path
from datetime import datetime
import soundfile as sf
import librosa


def ensure_directory(directory_path):
    """
    Ensure a directory exists, creating it if necessary
    
    Args:
        directory_path: Path to directory
        
    Returns:
        Path object for the directory
    """
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_audio_info(file_path):
    """
    Get information about an audio file
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Dictionary with audio file information
    """
    try:
        info = sf.info(file_path)
        
        # Get file stats
        file_stat = Path(file_path).stat()
        
        return {
            "path": str(file_path),
            "name": Path(file_path).name,
            "size_bytes": file_stat.st_size,
            "modified_time": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "created_time": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            "channels": info.channels,
            "sample_rate": info.samplerate,
            "frames": info.frames,
            "duration_seconds": info.frames / info.samplerate if info.samplerate > 0 else 0,
            "format": info.format,
            "subtype": info.subtype,
            "bit_depth": _get_bit_depth(info.subtype),
            "format_info": info.format_info,
            "subtype_info": info.subtype_info,
            "md5_hash": calculate_md5(file_path)
        }
    except Exception as e:
        return {
            "path": str(file_path),
            "name": Path(file_path).name,
            "error": str(e),
            "channels": 0,
            "sample_rate": 0,
            "duration_seconds": 0
        }


def _get_bit_depth(subtype):
    """Get bit depth from subtype string"""
    subtype_lower = subtype.lower()
    
    if 'pcm_16' in subtype_lower:
        return 16
    elif 'pcm_24' in subtype_lower:
        return 24
    elif 'pcm_32' in subtype_lower:
        return 32
    elif 'float' in subtype_lower:
        return 32  # Typically 32-bit float
    elif 'double' in subtype_lower:
        return 64  # 64-bit float
    elif '8' in subtype_lower:
        return 8
    else:
        return None


def calculate_md5(file_path, block_size=65536):
    """
    Calculate MD5 hash of a file
    
    Args:
        file_path: Path to file
        block_size: Block size for reading
        
    Returns:
        MD5 hash string
    """
    md5_hash = hashlib.md5()
    
    try:
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                md5_hash.update(block)
        return md5_hash.hexdigest()
    except Exception:
        return None


def get_supported_formats():
    """
    Get list of supported audio formats
    
    Returns:
        List of format extensions
    """
    return ['.mp3', '.wav', '.flac', '.aiff', '.aif', '.m4a', '.ogg', '.opus']


def is_audio_file(file_path):
    """
    Check if a file is a supported audio format
    
    Args:
        file_path: Path to file
        
    Returns:
        True if supported audio format, False otherwise
    """
    file_path = Path(file_path)
    return file_path.suffix.lower() in get_supported_formats()


def find_audio_files(directory_path, recursive=True):
    """
    Find all audio files in a directory
    
    Args:
        directory_path: Path to directory
        recursive: Whether to search recursively
        
    Returns:
        List of Path objects for audio files
    """
    directory = Path(directory_path)
    audio_files = []
    
    if recursive:
        for ext in get_supported_formats():
            audio_files.extend(directory.rglob(f'*{ext}'))
            audio_files.extend(directory.rglob(f'*{ext.upper()}'))
    else:
        for ext in get_supported_formats():
            audio_files.extend(directory.glob(f'*{ext}'))
            audio_files.extend(directory.glob(f'*{ext.upper()}'))
    
    # Remove duplicates and sort
    audio_files = list(set(audio_files))
    audio_files.sort()
    
    return audio_files


def create_backup(file_path, backup_dir=None):
    """
    Create a backup copy of a file
    
    Args:
        file_path: Path to file to backup
        backup_dir: Directory for backups (default: same directory with _backup suffix)
        
    Returns:
        Path to backup file, or None if failed
    """
    try:
        source_path = Path(file_path)
        
        if backup_dir is None:
            backup_dir = source_path.parent / f"{source_path.stem}_backup"
        
        backup_dir = ensure_directory(backup_dir)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
        backup_path = backup_dir / backup_name
        
        # Copy file
        shutil.copy2(source_path, backup_path)
        
        return backup_path
    except Exception as e:
        print(f"Failed to create backup: {e}")
        return None


def cleanup_old_backups(backup_dir, keep_last_n=5):
    """
    Clean up old backup files, keeping only the most recent N
    
    Args:
        backup_dir: Directory containing backup files
        keep_last_n: Number of most recent backups to keep
        
    Returns:
        Number of files deleted
    """
    try:
        backup_dir = Path(backup_dir)
        
        if not backup_dir.exists():
            return 0
        
        # Get all backup files sorted by modification time (newest first)
        backup_files = sorted(
            backup_dir.glob("*"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        # Keep only the most recent N files
        files_to_delete = backup_files[keep_last_n:]
        
        deleted_count = 0
        for file_path in files_to_delete:
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception:
                pass
        
        return deleted_count
    except Exception as e:
        print(f"Failed to cleanup backups: {e}")
        return 0


def get_output_filename(input_path, suffix="_processed", format_ext=None):
    """
    Generate an output filename based on input path
    
    Args:
        input_path: Input file path
        suffix: Suffix to add before extension
        format_ext: Output format extension (with dot, e.g., '.wav')
        
    Returns:
        Output file path
    """
    input_path = Path(input_path)
    
    if format_ext is None:
        format_ext = input_path.suffix
    
    # Remove leading dot if present
    if format_ext.startswith('.'):
        format_ext = format_ext[1:]
    
    # Create output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"{input_path.stem}{suffix}_{timestamp}.{format_ext}"
    
    return input_path.parent / output_name


def validate_audio_file(file_path):
    """
    Validate that an audio file can be loaded and processed
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Check file exists
        if not Path(file_path).exists():
            return False, "File does not exist"
        
        # Check file size
        file_size = Path(file_path).stat().st_size
        if file_size == 0:
            return False, "File is empty"
        
        # Check file extension
        if not is_audio_file(file_path):
            return False, f"Unsupported audio format. Supported: {', '.join(get_supported_formats())}"
        
        # Try to read file info
        info = sf.info(file_path)
        
        # Check sample rate
        if info.samplerate <= 0:
            return False, "Invalid sample rate"
        
        # Check duration
        duration = info.frames / info.samplerate
        if duration <= 0:
            return False, "Audio has no duration"
        
        # Check if too long (e.g., > 30 minutes)
        if duration > 1800:  # 30 minutes
            return False, "Audio too long (max 30 minutes)"
        
        # Check file size reasonable for duration
        expected_min_size = duration * info.samplerate * info.channels * 2  # Rough estimate
        if file_size < expected_min_size * 0.1:  # At least 10% of expected
            return False, "File size suspiciously small for duration"
        
        # Try to load a small portion to validate
        try:
            audio, sr = librosa.load(file_path, sr=None, mono=False, duration=1.0)
            if audio.size == 0:
                return False, "Could not load audio data"
        except Exception as load_error:
            return False, f"Failed to load audio: {load_error}"
        
        return True, "File is valid"
        
    except Exception as e:
        return False, f"Validation error: {e}"


def save_processing_metadata(output_path, metadata):
    """
    Save processing metadata as JSON file alongside audio
    
    Args:
        output_path: Path to processed audio file
        metadata: Dictionary of processing metadata
        
    Returns:
        Path to metadata file
    """
    try:
        output_path = Path(output_path)
        metadata_path = output_path.with_suffix('.json')
        
        # Add timestamp if not present
        if 'processing_timestamp' not in metadata:
            metadata['processing_timestamp'] = datetime.now().isoformat()
        
        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        return metadata_path
    except Exception as e:
        print(f"Failed to save metadata: {e}")
        return None


def load_processing_metadata(metadata_path):
    """
    Load processing metadata from JSON file
    
    Args:
        metadata_path: Path to metadata file
        
    Returns:
        Dictionary of metadata, or None if failed
    """
    try:
        metadata_path = Path(metadata_path)
        
        if not metadata_path.exists():
            return None
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        return metadata
    except Exception:
        return None


def get_file_hash_tree(directory_path):
    """
    Create a hash tree of all audio files in directory
    
    Useful for detecting changes and managing watch folders
    
    Args:
        directory_path: Path to directory
        
    Returns:
        Dictionary mapping file paths to their MD5 hashes
    """
    directory = Path(directory_path)
    hash_tree = {}
    
    for audio_file in find_audio_files(directory):
        md5_hash = calculate_md5(audio_file)
        if md5_hash:
            hash_tree[str(audio_file)] = {
                "hash": md5_hash,
                "size": audio_file.stat().st_size,
                "modified": audio_file.stat().st_mtime
            }
    
    return hash_tree


def compare_hash_trees(old_tree, new_tree):
    """
    Compare two hash trees to find changes
    
    Args:
        old_tree: Previous hash tree
        new_tree: Current hash tree
        
    Returns:
        Dictionary with added, modified, and removed files
    """
    old_files = set(old_tree.keys())
    new_files = set(new_tree.keys())
    
    added = new_files - old_files
    removed = old_files - new_files
    
    # Check for modified files
    modified = set()
    common_files = old_files.intersection(new_files)
    
    for file_path in common_files:
        if (old_tree[file_path]["hash"] != new_tree[file_path]["hash"] or
            old_tree[file_path]["size"] != new_tree[file_path]["size"]):
            modified.add(file_path)
    
    return {
        "added": list(added),
        "modified": list(modified),
        "removed": list(removed),
        "unchanged": list(common_files - modified)
    }


def test_file_utils():
    """Test file utilities"""
    print("Testing file utilities...")
    
    # Create test directory
    test_dir = Path("/tmp/suno_test")
    ensure_directory(test_dir)
    
    # Create a test audio file
    import numpy as np
    sr = 44100
    duration = 0.1  # Short test file
    t = np.linspace(0, duration, int(sr * duration))
    test_audio = np.sin(2 * np.pi * 440 * t)
    
    test_file = test_dir / "test.wav"
    sf.write(test_file, test_audio, sr)
    
    try:
        # Test ensure_directory
        subdir = test_dir / "subdir" / "nested"
        ensure_directory(subdir)
        assert subdir.exists(), "ensure_directory failed"
        print("✓ ensure_directory")
        
        # Test get_audio_info
        info = get_audio_info(test_file)
        assert info["sample_rate"] == sr, "get_audio_info failed"
        print("✓ get_audio_info")
        
        # Test calculate_md5
        md5 = calculate_md5(test_file)
        assert md5 is not None, "calculate_md5 failed"
        print("✓ calculate_md5")
        
        # Test is_audio_file
        assert is_audio_file(test_file), "is_audio_file failed"
        print("✓ is_audio_file")
        
        # Test find_audio_files
        audio_files = find_audio_files(test_dir)
        assert test_file in audio_files, "find_audio_files failed"
        print("✓ find_audio_files")
        
        # Test validate_audio_file
        is_valid, message = validate_audio_file(test_file)
        assert is_valid, f"validate_audio_file failed: {message}"
        print("✓ validate_audio_file")
        
        # Test create_backup
        backup = create_backup(test_file)
        assert backup is not None, "create_backup failed"
        assert backup.exists(), "backup file not created"
        print("✓ create_backup")
        
        # Test get_output_filename
        output_name = get_output_filename(test_file, "_test", "flac")
        assert "_test_" in str(output_name), "get_output_filename failed"
        assert output_name.suffix == ".flac", "get_output_filename format failed"
        print("✓ get_output_filename")
        
        # Test save/load metadata
        metadata = {"test": "data", "number": 123}
        metadata_path = save_processing_metadata(test_file, metadata)
        assert metadata_path is not None, "save_processing_metadata failed"
        assert metadata_path.exists(), "metadata file not created"
        
        loaded_metadata = load_processing_metadata(metadata_path)
        assert loaded_metadata["test"] == "data", "load_processing_metadata failed"
        print("✓ save/load_processing_metadata")
        
        # Test get_file_hash_tree
        hash_tree = get_file_hash_tree(test_dir)
        assert len(hash_tree) >= 1, "get_file_hash_tree failed"
        print("✓ get_file_hash_tree")
        
        # Test compare_hash_trees
        # Create a modified file
        test_file2 = test_dir / "test2.wav"
        sf.write(test_file2, test_audio * 0.5, sr)
        
        tree1 = get_file_hash_tree(test_dir)
        # Simulate change by deleting a file
        test_file2.unlink()
        tree2 = get_file_hash_tree(test_dir)
        
        comparison = compare_hash_trees(tree1, tree2)
        assert "test2.wav" in comparison["removed"], "compare_hash_trees failed"
        print("✓ compare_hash_trees")
        
        # Cleanup
        shutil.rmtree(test_dir)
        
        print("\n✅ All file utility tests passed!")
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        # Cleanup on failure
        if test_dir.exists():
            shutil.rmtree(test_dir)
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if test_dir.exists():
            shutil.rmtree(test_dir)
        raise


if __name__ == "__main__":
    test_file_utils()