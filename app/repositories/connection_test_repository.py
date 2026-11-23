import os
import logging

from sqlalchemy import create_engine, text
from app.database.connection_factory import ConnectionFactory

"""
    Repository for testing database connections

    This repository separates the method for testing a database
    connection from the main application logic.
"""

class ConnectionTestRepository:

    logger = logging.getLogger(__name__)

    @staticmethod
    def test_connection(
        connection_name,
        server,
        database,
        authentication_type,
        port=1433,
        username=None,
        password=None
    ):
        
        # Build SQLAlchemy connection URL
        connection_url = ConnectionFactory.build_sql_server_url(
            server=server,
            database=database,
            authentication_type=authentication_type,
            port=int(port),
            username=username,
            password=password
        )

        engine = create_engine(
            connection_url,
            connect_args={"timeout": 5}
        )

        try:
            # Attempt connection and execute test query
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                return True

        finally:

            # Release connection resources
            engine.dispose()
