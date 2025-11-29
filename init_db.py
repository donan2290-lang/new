"""Initialize database tables."""
from extensions import db
from models import DownloadTask
from flask import Flask
from config import config
import os

# Create Flask app
env = os.getenv('FLASK_ENV', 'production')
app = Flask(__name__)
app.config.from_object(config[env])

# Initialize database
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()
    print('✓ Database tables created successfully')
    print('✓ DownloadTask model ready')
    print(f'✓ Database location: {app.config["SQLALCHEMY_DATABASE_URI"]}')
