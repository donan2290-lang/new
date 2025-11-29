"""
Logging Configuration
Setup centralized logging for the application
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logging(app):
    """Setup application logging"""
    
    # Create logs directory
    log_folder = app.config.get('LOG_FOLDER', 'logs')
    os.makedirs(log_folder, exist_ok=True)
    
    # Get log level from config
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper())
    
    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (for production)
    log_file = app.config.get('LOG_FILE', 'logs/app.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Error log file (errors only)
    error_log_file = os.path.join(log_folder, 'error.log')
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    # Flask app logger
    app.logger.setLevel(log_level)
    app.logger.handlers = logger.handlers
    
    app.logger.info(f"Logging initialized - Level: {logging.getLevelName(log_level)}")
    app.logger.info(f"Log file: {log_file}")
    
    return logger

def log_request(request, response_status=None):
    """Log HTTP request details"""
    logger = logging.getLogger('app.request')
    
    log_data = {
        'method': request.method,
        'path': request.path,
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown')[:100],
    }
    
    if response_status:
        log_data['status'] = response_status
    
    logger.info(f"{log_data['method']} {log_data['path']} - IP: {log_data['ip']} - Status: {log_data.get('status', 'N/A')}")
