#!/usr/bin/env python3
"""
Watch Folder Processor for Suno Studio Pro

Monitors folders for new audio files, processes them automatically,
and maintains a processing queue with priority support.
"""

import time
import threading
import queue
import json
import shutil
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict, List, Optional, Callable

from .artifact_remover import ArtifactRemover
from .mastering_engine import MasteringEngine
# StemProcessor may fail to import if torch/demucs not available
try:
    from .stem_separator import StemProcessor
    STEM_PROCESSOR_AVAILABLE = True
except (ImportError, OSError) as e:
    STEM_PROCESSOR_AVAILABLE = False
    StemProcessor = None
    print(f"⚠️ StemProcessor unavailable: {e}")
from ..utils.file_manager import ensure_directory, get_audio_info, validate_audio_file
from ..utils.audio_analysis import analyze_audio_metadata


class WatchFolderHandler(FileSystemEventHandler):
    """File system event handler for watch folders"""
    
    def __init__(self, processor, config):
        super().__init__()
        self.processor = processor
        self.config = config
        self.processed_files = set()
        self.last_processed = {}
        
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if self._should_process(file_path):
            self.processor.enqueue_file(file_path, priority='high')
            
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if self._should_process(file_path):
            # Only process if not recently processed
            last_time = self.last_processed.get(str(file_path), 0)
            if time.time() - last_time > 60:  # 60 second cooldown
                self.processor.enqueue_file(file_path, priority='medium')
                
    def _should_process(self, file_path: Path) -> bool:
        """Check if file should be processed"""
        # Skip if already processed in this session
        if str(file_path) in self.processed_files:
            return False
            
        # Check file extension
        supported_exts = ['.mp3', '.wav', '.flac', '.aiff', '.m4a', '.ogg']
        if file_path.suffix.lower() not in supported_exts:
            return False
            
        # Validate file
        is_valid, error = validate_audio_file(file_path)
        if not is_valid:
            print(f"Skipping invalid file {file_path}: {error}")
            return False
            
        return True
    
    def mark_processed(self, file_path: Path):
        """Mark file as processed"""
        self.processed_files.add(str(file_path))
        self.last_processed[str(file_path)] = time.time()


class ProcessingQueue:
    """Thread-safe processing queue with priority support"""
    
    def __init__(self):
        self.queue = queue.PriorityQueue()
        self.lock = threading.Lock()
        self.task_id = 0
        
    def enqueue(self, item, priority: int = 0):
        """Add item to queue with priority (lower = higher priority)"""
        with self.lock:
            self.task_id += 1
            # Use (priority, task_id, item) tuple for stable ordering
            self.queue.put((priority, self.task_id, item))
            
    def dequeue(self):
        """Get next item from queue"""
        try:
            priority, task_id, item = self.queue.get_nowait()
            return item
        except queue.Empty:
            return None
            
    def size(self):
        """Get current queue size"""
        return self.queue.qsize()
        
    def empty(self):
        """Check if queue is empty"""
        return self.queue.empty()


class WatchFolderProcessor:
    """
    Main watch folder processor that manages queues and workers
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.queue = ProcessingQueue()
        self.workers = []
        self.observer = None
        self.handlers = {}
        self.running = False
        
        # Initialize processors
        self.artifact_remover = ArtifactRemover(self.config.get('sample_rate', 44100))
        self.mastering_engine = MasteringEngine(self.config.get('sample_rate', 44100))
        if STEM_PROCESSOR_AVAILABLE:
            self.stem_processor = StemProcessor()
        else:
            self.stem_processor = None
            print("⚠️ StemProcessor unavailable (torch/demucs missing). Stem separation disabled.")
        
        # Statistics
        self.stats = {
            'processed_files': 0,
            'failed_files': 0,
            'total_processing_time': 0,
            'start_time': None,
            'last_activity': None
        }
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'watch_folders': [],
            'output_folder': 'processed',
            'max_workers': 2,
            'sample_rate': 44100,
            'default_preset': 'spotify_ready',
            'remove_artifacts': True,
            'artifact_intensity': 0.5,
            'separate_stems': False,
            'auto_delete_original': False,
            'backup_original': True,
            'backup_folder': 'backups',
            'max_queue_size': 100,
            'log_level': 'INFO',
            'log_file': 'suno_watchdog.log',
            'notifications': {
                'enable': False,
                'webhook_url': None,
                'email': None
            }
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
                
        return default_config
        
    def add_watch_folder(self, folder_path: str, recursive: bool = True):
        """Add a folder to watch"""
        folder = Path(folder_path)
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
            print(f"Created watch folder: {folder}")
            
        # Create output subfolder
        output_folder = folder / self.config['output_folder']
        ensure_directory(output_folder)
        
        # Create backup folder if enabled
        if self.config['backup_original']:
            backup_folder = folder / self.config['backup_folder']
            ensure_directory(backup_folder)
            
        # Start watching this folder
        if self.observer is None:
            self.observer = Observer()
            
        handler = WatchFolderHandler(self, self.config)
        self.handlers[str(folder)] = handler
        self.observer.schedule(handler, str(folder), recursive=recursive)
        
        print(f"Added watch folder: {folder} (recursive: {recursive})")
        return True
        
    def enqueue_file(self, file_path: Path, priority: str = 'medium'):
        """Add file to processing queue"""
        priority_map = {
            'high': 0,
            'medium': 1,
            'low': 2
        }
        priority_value = priority_map.get(priority.lower(), 1)
        
        # Check queue size limit
        if self.queue.size() >= self.config['max_queue_size']:
            print(f"Queue full ({self.queue.size()}), skipping {file_path}")
            return False
            
        self.queue.enqueue({
            'file_path': str(file_path),
            'priority': priority,
            'enqueued_time': datetime.now().isoformat(),
            'status': 'queued'
        }, priority_value)
        
        print(f"Enqueued {file_path} with {priority} priority (queue size: {self.queue.size()})")
        return True
        
    def process_file(self, task: Dict) -> Dict:
        """Process a single file"""
        file_path = Path(task['file_path'])
        start_time = time.time()
        
        result = {
            'task': task,
            'file_path': str(file_path),
            'start_time': datetime.fromtimestamp(start_time).isoformat(),
            'success': False,
            'errors': [],
            'processing_time': 0,
            'output_path': None
        }
        
        try:
            # Validate file
            is_valid, error = validate_audio_file(file_path)
            if not is_valid:
                result['errors'].append(f"Validation failed: {error}")
                return result
                
            # Analyze audio metadata
            metadata = analyze_audio_metadata(file_path)
            result['metadata'] = metadata
            
            # Get processing settings
            settings = self._get_processing_settings(metadata)
            
            # Create output path
            output_folder = file_path.parent / self.config['output_folder']
            ensure_directory(output_folder)
            output_file = output_folder / f"processed_{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
            
            # Backup original if enabled
            if self.config['backup_original']:
                backup_folder = file_path.parent / self.config['backup_folder']
                ensure_directory(backup_folder)
                backup_file = backup_folder / f"original_{file_path.name}"
                shutil.copy2(file_path, backup_file)
                result['backup_path'] = str(backup_file)
            
            # Process the file
            print(f"Processing {file_path.name}...")
            
            # Load audio
            import librosa
            import soundfile as sf
            
            audio, sr = librosa.load(file_path, sr=self.config['sample_rate'], mono=False)
            
            # Remove artifacts
            if self.config['remove_artifacts']:
                intensity = self.config.get('artifact_intensity', 0.5)
                audio = self.artifact_remover.process_full(audio, intensity=intensity)
                result['artifacts_removed'] = True
                
            # Apply mastering
            preset = self.config.get('default_preset', 'spotify_ready')
            audio = self.mastering_engine.master_track(audio, preset_name=preset)
            result['mastering_preset'] = preset
            
            # Save processed file
            if audio.ndim == 2:
                sf.write(output_file, audio.T, sr)
            else:
                sf.write(output_file, audio, sr)
                
            # Update result
            result['success'] = True
            result['output_path'] = str(output_file)
            
            # Mark as processed in handler
            for handler in self.handlers.values():
                handler.mark_processed(file_path)
                
            # Auto-delete original if configured
            if self.config.get('auto_delete_original', False):
                file_path.unlink()
                result['original_deleted'] = True
                
        except Exception as e:
            result['errors'].append(str(e))
            print(f"Error processing {file_path}: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            end_time = time.time()
            result['processing_time'] = end_time - start_time
            result['end_time'] = datetime.fromtimestamp(end_time).isoformat()
            
        return result
        
    def _get_processing_settings(self, metadata: Dict) -> Dict:
        """Get processing settings based on audio metadata"""
        # Start with default config
        settings = {
            'remove_artifacts': self.config['remove_artifacts'],
            'artifact_intensity': self.config.get('artifact_intensity', 0.5),
            'default_preset': self.config.get('default_preset', 'spotify_ready'),
            'separate_stems': self.config.get('separate_stems', False)
        }
        
        # AI-based adjustments could go here
        # For now, return basic settings
        return settings
        
    def _worker_loop(self, worker_id: int):
        """Worker thread that processes files from queue"""
        print(f"Worker {worker_id} started")
        
        while self.running:
            task = self.queue.dequeue()
            
            if task is None:
                # Queue is empty, sleep a bit
                time.sleep(0.5)
                continue
                
            # Process the file
            result = self.process_file(task)
            
            # Update statistics
            with threading.Lock():
                self.stats['processed_files'] += 1
                self.stats['total_processing_time'] += result['processing_time']
                self.stats['last_activity'] = datetime.now().isoformat()
                
                if not result['success']:
                    self.stats['failed_files'] += 1
                    
            # Log result
            if result['success']:
                print(f"Worker {worker_id}: Successfully processed {Path(result['file_path']).name} "
                      f"in {result['processing_time']:.1f}s")
            else:
                print(f"Worker {worker_id}: Failed to process {Path(result['file_path']).name}: "
                      f"{result['errors']}")
                      
            # Save result to log
            self._log_result(result, worker_id)
            
    def _log_result(self, result: Dict, worker_id: int):
        """Log processing result to file"""
        log_file = Path(self.config.get('log_file', 'suno_watchdog.log'))
        ensure_directory(log_file.parent)
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'worker_id': worker_id,
            **result
        }
        
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\\n')
        except Exception as e:
            print(f"Failed to write log: {e}")
            
    def start_workers(self):
        """Start worker threads"""
        max_workers = self.config['max_workers']
        self.running = True
        
        for i in range(max_workers):
            worker = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)
            
        print(f"Started {max_workers} worker threads")
        
    def stop_workers(self):
        """Stop worker threads"""
        self.running = False
        
        for worker in self.workers:
            worker.join(timeout=5.0)
            
        print("All workers stopped")
        
    def start_watching(self):
        """Start watching folders"""
        if self.observer is None:
            self.observer = Observer()
            
        # Start observer
        self.observer.start()
        self.stats['start_time'] = datetime.now().isoformat()
        
        print("Watch folder observer started")
        print(f"Watching {len(self.handlers)} folder(s)")
        
    def stop_watching(self):
        """Stop watching folders"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            
        print("Watch folder observer stopped")
        
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        stats = self.stats.copy()
        stats['queue_size'] = self.queue.size()
        stats['worker_count'] = len(self.workers)
        stats['active_workers'] = sum(1 for w in self.workers if w.is_alive())
        stats['watch_folders'] = list(self.handlers.keys())
        
        if stats['processed_files'] > 0:
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['processed_files']
        else:
            stats['avg_processing_time'] = 0
            
        return stats
        
    def process_existing_files(self, folder_path: Optional[str] = None):
        """Process all existing files in watch folders"""
        folders_to_process = []
        
        if folder_path:
            folders_to_process.append(Path(folder_path))
        else:
            folders_to_process = [Path(folder) for folder in self.handlers.keys()]
            
        for folder in folders_to_process:
            if not folder.exists():
                print(f"Folder does not exist: {folder}")
                continue
                
            # Find all audio files
            from ..utils.file_manager import find_audio_files
            audio_files = find_audio_files(folder)
            
            print(f"Found {len(audio_files)} existing files in {folder}")
            
            # Enqueue all files with low priority
            for file_path in audio_files:
                self.enqueue_file(file_path, priority='low')
                
    def save_config(self, config_path: Optional[str] = None):
        """Save current configuration to file"""
        if config_path is None:
            config_path = 'suno_watchdog_config.json'
            
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"Configuration saved to {config_path}")
        except Exception as e:
            print(f"Failed to save configuration: {e}")


def main():
    """Command-line interface for watch folder processor"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Suno Studio Pro Watch Folder Processor'
    )
    parser.add_argument('--config', '-c', default='suno_watchdog_config.json',
                       help='Configuration file path')
    parser.add_argument('--watch', '-w', action='append',
                       help='Folders to watch (can be used multiple times)')
    parser.add_argument('--output', '-o', default='processed',
                       help='Output subfolder name')
    parser.add_argument('--workers', type=int, default=2,
                       help='Number of worker threads')
    parser.add_argument('--process-existing', action='store_true',
                       help='Process existing files in watch folders')
    parser.add_argument('--no-backup', action='store_true',
                       help='Disable backup of original files')
    parser.add_argument('--preset', default='spotify_ready',
                       choices=['spotify_ready', 'youtube_ready', 'club_master',
                                'electronic', 'synthwave', 'vaporwave', 'house',
                                'radio_ready', 'acoustic', 'hiphop'],
                       help='Mastering preset')
    parser.add_argument('--log-file', default='suno_watchdog.log',
                       help='Log file path')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Create processor
    processor = WatchFolderProcessor(args.config)
    
    # Update config from command line
    if args.watch:
        processor.config['watch_folders'] = args.watch
    if args.output:
        processor.config['output_folder'] = args.output
    if args.workers:
        processor.config['max_workers'] = args.workers
    if args.no_backup:
        processor.config['backup_original'] = False
    if args.preset:
        processor.config['default_preset'] = args.preset
    if args.log_file:
        processor.config['log_file'] = args.log_file
        
    # Add watch folders
    for folder in processor.config['watch_folders']:
        processor.add_watch_folder(folder)
        
    if not processor.handlers:
        print("No watch folders configured. Use --watch to add folders.")
        return
        
    # Start workers
    processor.start_workers()
    
    # Process existing files if requested
    if args.process_existing:
        print("Processing existing files...")
        processor.process_existing_files()
        
    # Start watching
    processor.start_watching()
    
    try:
        print("\\nSuno Studio Pro Watch Folder Processor running.")
        print("Press Ctrl+C to stop.\\n")
        
        # Print stats periodically
        while True:
            time.sleep(10)
            stats = processor.get_stats()
            print(f"Queue: {stats['queue_size']} files | "
                  f"Processed: {stats['processed_files']} | "
                  f"Failed: {stats['failed_files']} | "
                  f"Workers: {stats['active_workers']}/{stats['worker_count']}")
                  
    except KeyboardInterrupt:
        print("\\nShutting down...")
    finally:
        processor.stop_watching()
        processor.stop_workers()
        
        # Final stats
        stats = processor.get_stats()
        print(f"\\nFinal statistics:")
        print(f"  Total files processed: {stats['processed_files']}")
        print(f"  Failed files: {stats['failed_files']}")
        print(f"  Average processing time: {stats.get('avg_processing_time', 0):.1f}s")
        print(f"  Total processing time: {stats['total_processing_time']:.1f}s")
        

if __name__ == '__main__':
    main()