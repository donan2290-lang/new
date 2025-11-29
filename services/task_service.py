"""Helper utilities for recording download/conversion tasks in the database."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from flask import current_app

from extensions import db
from models import DownloadTask


def _retention_hours() -> int:
    try:
        return int(current_app.config.get("DOWNLOAD_RETENTION_HOURS", 24))
    except Exception:
        return 24


def upsert_task(session_id: str, defaults: Optional[dict[str, Any]] = None) -> DownloadTask:
    """Create or update a task record for the provided session id."""
    defaults = defaults or {}
    task = DownloadTask.query.filter_by(session_id=session_id).one_or_none()
    created = False
    if not task:
        task = DownloadTask(session_id=session_id)
        db.session.add(task)
        created = True

    for key, value in defaults.items():
        if hasattr(task, key) and value is not None:
            setattr(task, key, value)

    task.touch()
    task.extend_expiry(_retention_hours())
    if created and not task.status:
        task.status = "pending"
    db.session.commit()
    return task


def mark_status(session_id: str, status: str, message: str | None = None, progress: Optional[dict[str, Any]] = None):
    """Update status/message for a task while keeping expiry fresh."""
    try:
        task = upsert_task(session_id)
        task.mark_status(status, message, progress)
        task.extend_expiry(_retention_hours())
        db.session.commit()
    except Exception as exc:  # pragma: no cover
        current_app.logger.error("Failed to mark status for %s: %s", session_id, exc)


def register_storage(session_id: str, path: str, storage_type: str = "temp", file_size: int | None = None):
    """Persist location of a temporary artifact for later cleanup."""
    try:
        task = upsert_task(session_id)
        task.set_storage(path, storage_type=storage_type, file_size=file_size)
        db.session.commit()
    except Exception as exc:  # pragma: no cover
        current_app.logger.error("Failed to register storage for %s: %s", session_id, exc)


def mark_file_deleted(session_id: str):
    """Clear stored file metadata after streaming/cleanup."""
    try:
        task = DownloadTask.query.filter_by(session_id=session_id).one_or_none()
        if not task:
            return
        task.set_storage(None, storage_type=task.storage_type)
        if task.status != "completed":
            task.status = "completed"
        task.touch()
        db.session.commit()
    except Exception as exc:  # pragma: no cover
        current_app.logger.error("Failed to mark file deleted for %s: %s", session_id, exc)


def cleanup_expired_tasks():
    """Remove expired task rows and their lingering files."""
    now = datetime.utcnow()
    expired = DownloadTask.query.filter(DownloadTask.expires_at.isnot(None), DownloadTask.expires_at < now).all()
    if not expired:
        return 0, 0

    removed = 0
    size_freed = 0
    for task in expired:
        try:
            if task.storage_path and os.path.exists(task.storage_path):
                try:
                    size_freed += os.path.getsize(task.storage_path)
                except OSError:
                    pass
                try:
                    os.remove(task.storage_path)
                except OSError as exc:
                    current_app.logger.warning("Failed to remove %s: %s", task.storage_path, exc)
            db.session.delete(task)
            removed += 1
        except Exception as exc:  # pragma: no cover
            current_app.logger.error("Failed to purge task %s: %s", task.session_id, exc)
    db.session.commit()
    return removed, size_freed
