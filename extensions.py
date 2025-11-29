"""Application-wide extensions.

Centralize extension instantiation (e.g., SQLAlchemy) to avoid circular imports.
"""
from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy database instance, initialized in app factory/startup
# Other modules should import `db` from this module and call `db.init_app(app)`.
db = SQLAlchemy()
