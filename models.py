"""Database models for the VideoDownloaderApp."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func

from extensions import db


class DownloadTask(db.Model):
    """Track download/conversion lifecycle for better cleanup and observability."""

    __tablename__ = "download_tasks"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    platform = db.Column(db.String(64), index=True)
    source_url = db.Column(db.Text)
    direct_url = db.Column(db.Text)
    requested_filename = db.Column(db.String(255))
    storage_path = db.Column(db.String(512))
    storage_type = db.Column(db.String(32), default="temp", index=True)
    file_size = db.Column(db.BigInteger)
    status = db.Column(db.String(32), default="pending", index=True)
    message = db.Column(db.String(255))
    last_progress = db.Column(db.JSON)
    last_accessed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())
    expires_at = db.Column(db.DateTime, index=True)

    def mark_status(self, status: str, message: str | None = None, progress: dict | None = None):
        """Convenience helper to update status/message/last progress."""
        self.status = status
        if message:
            self.message = message
        if progress is not None:
            self.last_progress = progress
        self.touch()

    def set_storage(self, path: str | None, storage_type: str = "temp", file_size: int | None = None):
        self.storage_path = path
        self.storage_type = storage_type
        if file_size is not None:
            self.file_size = file_size
        self.touch()

    def touch(self):
        self.last_accessed_at = datetime.utcnow()

    def extend_expiry(self, hours: int):
        from datetime import timedelta
        self.expires_at = datetime.utcnow()
        if hours and hours > 0:
            self.expires_at = self.expires_at + timedelta(hours=hours)
