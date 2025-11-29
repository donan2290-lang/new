"""
File Cleanup Utility
Automatically clean up old files from uploads and outputs folders
"""
import os
import time
import threading
import logging
from datetime import datetime, timedelta

from services.task_service import cleanup_expired_tasks

logger = logging.getLogger(__name__)

class FileCleanupScheduler:
    """Background scheduler for cleaning up old files"""
    
    def __init__(self, app=None):
        self.app = app
        self.running = False
        self.thread = None
        self.track_tasks = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        self.enabled = app.config.get('AUTO_CLEANUP_ENABLED', True)
        self.interval_hours = app.config.get('CLEANUP_INTERVAL_HOURS', 1)
        self.max_age_hours = app.config.get('CLEANUP_MAX_AGE_HOURS', 24)
        self.upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        self.output_folder = app.config.get('OUTPUT_FOLDER', 'outputs')
        
        if self.enabled:
            self.start()

    def enable_task_tracking(self, enabled=True):
        """Allow scheduler to rely on DB-backed task metadata for cleanup."""
        self.track_tasks = enabled
    
    def start(self):
        """Start the cleanup scheduler"""
        if self.running:
            logger.warning("Cleanup scheduler already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info(f"File cleanup scheduler started (interval: {self.interval_hours}h, max age: {self.max_age_hours}h)")
    
    def stop(self):
        """Stop the cleanup scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("File cleanup scheduler stopped")
    
    def _run_scheduler(self):
        """Background thread that runs cleanup periodically"""
        while self.running:
            try:
                self.cleanup_old_files()
            except Exception as e:
                logger.error(f"Error in cleanup scheduler: {e}")
            
            # Sleep for interval (check every minute if we should stop)
            sleep_seconds = self.interval_hours * 3600
            for _ in range(int(sleep_seconds / 60)):
                if not self.running:
                    break
                time.sleep(60)
    
    def cleanup_old_files(self):
        """Clean up files older than max_age_hours"""
        if not self.enabled:
            return
        
        cutoff_time = time.time() - (self.max_age_hours * 3600)
        total_deleted = 0
        total_size_freed = 0
        
        # Clean both folders
        for folder in [self.upload_folder, self.output_folder]:
            if not os.path.exists(folder):
                continue
            
            try:
                deleted, size_freed = self._cleanup_folder(folder, cutoff_time)
                total_deleted += deleted
                total_size_freed += size_freed
            except Exception as e:
                logger.error(f"Error cleaning folder {folder}: {e}")
        
        if total_deleted > 0:
            logger.info(f"Cleanup completed: {total_deleted} files deleted, {self._format_size(total_size_freed)} freed")

        # Cleanup database task records/files
        self._cleanup_task_records()

    def _cleanup_task_records(self):
        if not self.track_tasks or not self.app:
            return
        try:
            with self.app.app_context():
                removed, size_freed = cleanup_expired_tasks()
                if removed:
                    logger.info(
                        "Task cleanup removed %s records (%.2f MB)",
                        removed,
                        size_freed / (1024 * 1024) if size_freed else 0,
                    )
        except Exception as exc:
            logger.error(f"Failed to cleanup task records: {exc}")
    
    def _cleanup_folder(self, folder, cutoff_time):
        """Clean up files in a specific folder"""
        deleted_count = 0
        size_freed = 0
        
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            
            # Skip directories
            if os.path.isdir(file_path):
                continue
            
            try:
                # Check file age
                file_mtime = os.path.getmtime(file_path)
                
                if file_mtime < cutoff_time:
                    # File is old, delete it
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    deleted_count += 1
                    size_freed += file_size
                    logger.debug(f"Deleted old file: {filename} ({self._format_size(file_size)})")
            
            except Exception as e:
                logger.error(f"Error deleting file {filename}: {e}")
        
        return deleted_count, size_freed
    
    def get_folder_stats(self):
        """Get statistics about folders"""
        stats = {}
        
        for folder_name in ['uploads', 'outputs']:
            folder = getattr(self, f'{folder_name[:-1]}_folder', folder_name)
            
            if not os.path.exists(folder):
                stats[folder_name] = {'files': 0, 'size': 0}
                continue
            
            file_count = 0
            total_size = 0
            oldest_file = None
            
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                
                if os.path.isfile(file_path):
                    file_count += 1
                    total_size += os.path.getsize(file_path)
                    
                    file_mtime = os.path.getmtime(file_path)
                    if oldest_file is None or file_mtime < oldest_file:
                        oldest_file = file_mtime
            
            stats[folder_name] = {
                'files': file_count,
                'size': total_size,
                'size_formatted': self._format_size(total_size),
                'oldest_file_age': self._format_age(oldest_file) if oldest_file else 'N/A'
            }
        
        return stats
    
    @staticmethod
    def _format_size(bytes_size):
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} TB"
    
    @staticmethod
    def _format_age(timestamp):
        """Format timestamp age to human readable"""
        age_seconds = time.time() - timestamp
        
        if age_seconds < 60:
            return f"{int(age_seconds)}s"
        elif age_seconds < 3600:
            return f"{int(age_seconds / 60)}m"
        elif age_seconds < 86400:
            return f"{int(age_seconds / 3600)}h"
        else:
            return f"{int(age_seconds / 86400)}d"

# Global instance
cleanup_scheduler = FileCleanupScheduler()
