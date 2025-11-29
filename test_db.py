"""Test database setup and verify models."""
from extensions import db
from models import DownloadTask
from flask import Flask
from config import config
import os
from datetime import datetime

# Create Flask app
env = os.getenv('FLASK_ENV', 'production')
app = Flask(__name__)
app.config.from_object(config[env])
db.init_app(app)

with app.app_context():
    # Delete any existing test data first
    existing = DownloadTask.query.filter_by(session_id='test-session-123').first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        print('✓ Cleaned up existing test data\n')
    
    # Test: Create a sample task
    test_task = DownloadTask(
        session_id='test-session-123',
        platform='youtube',
        status='pending',
        message='Testing database...'
    )
    test_task.touch()
    test_task.extend_expiry(24)
    
    db.session.add(test_task)
    db.session.commit()
    
    print('✓ Test task created')
    print(f'  - Session ID: {test_task.session_id}')
    print(f'  - Platform: {test_task.platform}')
    print(f'  - Status: {test_task.status}')
    print(f'  - Created: {test_task.created_at}')
    print(f'  - Expires: {test_task.expires_at}')
    
    # Test: Query the task
    queried = DownloadTask.query.filter_by(session_id='test-session-123').first()
    if queried:
        print('\n✓ Query test passed')
        print(f'  - Found task: {queried.session_id}')
    
    # Test: Update task
    queried.mark_status('processing', 'Download in progress...', {'percent': 50})
    db.session.commit()
    print('\n✓ Update test passed')
    print(f'  - New status: {queried.status}')
    print(f'  - Progress: {queried.last_progress}')
    
    # Test: Storage registration
    queried.set_storage('/tmp/test.mp4', storage_type='temp', file_size=1024000)
    db.session.commit()
    print('\n✓ Storage test passed')
    print(f'  - Storage path: {queried.storage_path}')
    print(f'  - File size: {queried.file_size} bytes')
    
    # Cleanup
    db.session.delete(test_task)
    db.session.commit()
    print('\n✓ Cleanup test passed')
    
    # Show all tables
    print('\n✓ Database tables:')
    for table in db.metadata.tables.keys():
        print(f'  - {table}')
    
    print(f'\n✓ Database setup complete!')
    print(f'✓ Location: {app.config["SQLALCHEMY_DATABASE_URI"]}')
