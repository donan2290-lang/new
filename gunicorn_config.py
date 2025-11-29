"""
Gunicorn Production Server Configuration
Run with: gunicorn -c gunicorn_config.py app:app
"""
import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = 'logs/gunicorn_access.log'
errorlog = 'logs/gunicorn_error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'snapload_video_downloader'

# Server mechanics
daemon = False
pidfile = 'logs/gunicorn.pid'
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = '/path/to/key.pem'
# certfile = '/path/to/cert.pem'

def when_ready(server):
    """Called just after the server is started"""
    server.log.info("Gunicorn server is ready. Spawning workers")

def on_starting(server):
    """Called just before the master process is initialized"""
    server.log.info("Starting Gunicorn server...")

def on_exit(server):
    """Called just before the master process exits"""
    server.log.info("Shutting down Gunicorn server...")

def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal"""
    worker.log.info("Worker received INT or QUIT signal")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal"""
    worker.log.info("Worker received ABORT signal")
