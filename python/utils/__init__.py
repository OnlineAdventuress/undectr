"""
Suno Studio Pro - Utility Modules
"""

from .audio_analysis import (
    analyze_audio_metadata,
    estimate_genre,
    get_audio_info,
    calculate_loudness_range,
    detect_silence,
    analyze_transients
)

from .file_manager import (
    ensure_directory,
    get_audio_info,
    calculate_md5,
    get_supported_formats,
    is_audio_file,
    find_audio_files,
    create_backup,
    cleanup_old_backups,
    get_output_filename,
    validate_audio_file,
    save_processing_metadata,
    load_processing_metadata,
    get_file_hash_tree,
    compare_hash_trees
)

__all__ = [
    'analyze_audio_metadata',
    'estimate_genre',
    'get_audio_info',
    'calculate_loudness_range',
    'detect_silence',
    'analyze_transients',
    'ensure_directory',
    'get_audio_info',
    'calculate_md5',
    'get_supported_formats',
    'is_audio_file',
    'find_audio_files',
    'create_backup',
    'cleanup_old_backups',
    'get_output_filename',
    'validate_audio_file',
    'save_processing_metadata',
    'load_processing_metadata',
    'get_file_hash_tree',
    'compare_hash_trees'
]