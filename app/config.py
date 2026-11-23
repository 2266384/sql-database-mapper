import os

from dotenv import load_dotenv
from app.database.connection_factory import ConnectionFactory

load_dotenv()


def _build_database_uri():

    connection_url = ConnectionFactory.build_sql_server_url(
        server=os.environ["DB_HOST"],
        port=os.getenv("DB_PORT", "1433"),
        database=os.environ["DB_NAME"],
        authentication_type="SQL",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"]
    )

    return connection_url.render_as_string(hide_password=False)


# Variables used by the app
class Config:
    APP_NAME = "DB Tools"
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = _build_database_uri()

    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Celery settings
    CELERY_BROKER_URL = os.getenv(
        "CELERY_BROKER_URL",
        "redis://localhost:6379/0"
    )

    CELERY_RESULT_BACKEND = os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/1"
    )

    CREDENTIAL_ENCRYPTION_KEY = os.environ["CREDENTIAL_ENCRYPTION_KEY"]