import logging

from flask import current_app
from sqlalchemy import text
from app.extensions import db

logger = logging.getLogger(__name__)


"""
    Tests connection to the SQL Database used for storing data
"""

def check_database_connection():

    # Get the current db server
    db_host = current_app.config.get("DB_HOST", "Unknown")
    db_name = current_app.config.get("DB_NAME", "Unknown")

    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "connected": True,
            "host": db_host,
            "database": db_name,
            "error": None
        }

    except Exception as exc:
        logger.exception("Database connection failed")

        return {
            "connected": False,
            "host": db_host,
            "database": db_name,
            "error": str(exc)
        }