import logging

from sqlalchemy.exc import SQLAlchemyError

from app.services.mapper.connections_service import ConnectionsService
from app.repositories import ConnectionTestRepository


logger = logging.getLogger(__name__)

class ConnectionTestService:

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

        # Validate connection configuration
        errors = ConnectionsService.validate_connection(
            connection_name,
            server,
            database,
            authentication_type,
            port
        )

        # Validate authentication credentials
        if authentication_type == "SQL":

            if not username:
                errors.append("Username is required")

            if not password:
                errors.append("Password is required")

            if errors:
                return {
                    "success": False,
                    "errors": errors,
                    "message": "Connection details are invalid"
                }

            try:

                logger.info(
                    "Starting connection test for: %s",
                    connection_name
                )

                logger.info(
                    "Authentication type received: %r",
                    authentication_type
                )

                # Attempt actual SQL Server connection
                ConnectionTestRepository.test_connection(
                    connection_name=connection_name,
                    server=server,
                    database=database,
                    authentication_type=authentication_type,
                    port=int(port),
                    username=username,
                    password=password
                )

                logger.info(
                    "Connection test successful: %s",
                    connection_name
                )

                return {
                    "success": True,
                    "errors": [],
                    "message": "Connection successful"
                }

            except SQLAlchemyError as error:

                logger.exception(
                    "SQLAlchemy connection test failed for %s",
                    connection_name
                )

                return {
                    "success": False,
                    "errors": [str(error)],
                    "message": "Unable to connect to the database"
                }

            except ValueError as error:

                logger.exception(
                    "Invalid connection configuration for %s: %s",
                    connection_name,
                    error
                )

            except Exception:
                logger.exception(
                    "Unexpected connection test failure: %s",
                    connection_name
                )

                return {
                    "success": False,
                    "errors": [str(error)],
                    "message": "Connection details are invalid"
                }