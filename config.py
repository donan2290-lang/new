"""
Application Configuration
Load from environment variables with fallback defaults
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    ENV = os.getenv('FLASK_ENV', 'production')
    
    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # File Upload
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 50))
    MAX_DOWNLOAD_SIZE_MB = int(os.getenv('MAX_DOWNLOAD_SIZE_MB', 500))
    MAX_CONTENT_LENGTH = MAX_FILE_SIZE_MB * 1024 * 1024
    
    # Folders
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', 'outputs')
    LOG_FOLDER = os.getenv('LOG_FOLDER', 'logs')
    DOWNLOAD_RETENTION_HOURS = int(os.getenv('DOWNLOAD_RETENTION_HOURS', 24))
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATE_LIMIT_DEFAULT = os.getenv('RATE_LIMIT_DEFAULT', '100 per hour')
    RATE_LIMIT_DOWNLOAD = os.getenv('RATE_LIMIT_DOWNLOAD', '10 per hour')
    RATE_LIMIT_CONVERT = os.getenv('RATE_LIMIT_CONVERT', '20 per hour')
    RATE_LIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
    
    # File Cleanup
    AUTO_CLEANUP_ENABLED = os.getenv('AUTO_CLEANUP_ENABLED', 'True').lower() == 'true'
    CLEANUP_INTERVAL_HOURS = int(os.getenv('CLEANUP_INTERVAL_HOURS', 1))
    CLEANUP_MAX_AGE_HOURS = int(os.getenv('CLEANUP_MAX_AGE_HOURS', 24))
    
    # Language/i18n
    DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'id')
    SUPPORTED_LANGUAGES = os.getenv('SUPPORTED_LANGUAGES', 'id,en').split(',')
    BABEL_DEFAULT_LOCALE = DEFAULT_LANGUAGE
    BABEL_TRANSLATION_DIRECTORIES = 'translations'
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///snapload.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        # Create required folders
        for folder in [Config.UPLOAD_FOLDER, Config.OUTPUT_FOLDER, Config.LOG_FOLDER]:
            os.makedirs(folder, exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENV = 'development'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENV = 'production'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}
