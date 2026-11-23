import logging

from flask import Flask

from .config import Config
from .extensions import db, migrate
from .services.database_service import check_database_connection
from app.utils.celery_utils import celery_init_app



### Creates the Flask application
def create_app(config_class=Config):
    app = Flask(__name__)
    
    app.config.from_object(config_class)

    # Configure application logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True
    )

    app.logger.setLevel(logging.DEBUG)

    # Initialise extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Inject application config into template context
    @app.context_processor
    def inject_app_config():
        return {
            "app_name": app.config["APP_NAME"],
            "database_status": check_database_connection()
        }

    # Initialise Celery
    celery_init_app(app)
    from app.tasks.scans import execute_scan



    # Import models so they are registered with db.metadata
    from . import models

    # Registers blueprints
    from .routes.main import main_bp
    app.register_blueprint(main_bp)

    from .routes.mapper.mapper import mapper_bp
    app.register_blueprint(mapper_bp)

    from .routes.mapper.connections import connections_bp
    app.register_blueprint(connections_bp)

    from .routes.mapper.scans import scans_bp
    app.register_blueprint(scans_bp)

    from .routes.mapper.documentation import documentation_bp
    app.register_blueprint(documentation_bp)

    return app