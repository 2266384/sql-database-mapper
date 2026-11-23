import logging

from sqlalchemy import inspect

from app.repositories.scans_repository import ScansRepository
from app.services.mapper.connections_service import ConnectionsService
from app.security.credentials import encrypt_credentials

logger = logging.getLogger(__name__)

"""
    Handles Scans business logic and validation
"""

class ScansService:
    
    @staticmethod
    def get_connections_with_latest_scan():
        """ Retrieve all saved scans """

        return ScansRepository.get_connections_with_latest_scan()



    @staticmethod
    def start_scan(connection, username=None, password=None):
        """ Validate and queue a database scan """
        
        scan = None

        # Validate saved connection
        if connection is None:
            return {
                "success": False,
                "message": "Database connection does not exist"
            }

        authentication_type = (
            connection.authentication_type or ""
        ).strip().upper()

        # Validate saved connection configuration
        errors = ConnectionsService.validate_connection(
            connection.connection_name,
            connection.server,
            connection.database,
            authentication_type,
            connection.port
        )

        # Validate additional scan credentials
        if authentication_type == "SQL":

            username = (username or "").strip()
            password = password or ""

            if not username:
                errors.append("Username is required")

            if not password:
                errors.append("Password is required")

        if errors:
            return {
                "success": False,
                "message": " ".join(errors)
            }

        try:
            # Encrypt credentials before creating the task
            encrypted_credentials = None

            if authentication_type == "SQL":
                encrypted_credentials = encrypt_credentials(
                    username=username,
                    password=password
                )

            # Create a PENDING scan record
            scan  = ScansRepository.create_scan(
                connection_id=connection.id
            )

            # Import scans task her to avoid circular imports
            from app.tasks.scans import execute_scan

            # Queue the background scan
            execute_scan.delay(
                scan.id,
                connection.id,
                encrypted_credentials
            )

            logger.info(
                "Scan queued successfully. Scan ID %s", scan.id
            )

            return {
                "success": True,
                "message": "Database scan queued successfully",
                "scan_id": scan.id
            }

        except Exception:

            logger.exception(
                "Unable to start scan for connection ID %s", connection.id
            )

            if scan is not None:
                try:
                    ScansRepository.update_scan(
                        scan.id,
                        status="FAILED",
                        error_message="Unable to queue background scan"
                    )

                except Exception:
                    logger.exception(
                        "Unable to mark scan %s as failed", scan.id
                    )

            return {
                "success": False,
                "message": "Unable to create the database scan"
            }


    @staticmethod
    def extract_database_structure(
        scan,
        engine,
        schemas=None
    ):

        """
            Validates and orchestrates database structure extraction

            Args:
                scan: Scan model instance.
                engine: SQLAlchemy Engine connected to the target database.
                schemas: Optional list of schemas to extract.

            Returns:
                Dictionary containing extraction status and data.
        """

        errors = []

        # Validate scan
        if scan is None:
            errors.append("Scan does not exist")

        # Validate scan status
        elif scan.status != "RUNNING":
            errors.append("Scan is not running")

        # Validate database engine
        if engine is None:
            errors.append("Database connection is unavailable")

        if errors:
            return {
                "success": False,
                "errors": errors,
                "data": None
            }

        try:

            # Validate requested schemas
            if schemas is not None:

                available_schemas = ScansRepository.extract_schemas(engine)

                available_schema_names = [
                    schema["name"]
                    for schema in available_schemas
                ]

                invalid_schemas = [
                    schema
                    for schema in schemas
                    if schema not in available_schemas
                ]

                if invalid_schemas:
                    return {
                        "success": False,
                        "errors": [
                            f"Invalid schemas: {', '.join(invalid_schemas)}"
                        ],
                        "data": None
                    }


            # Delegate extraction to repository
            structure = ScansRepository.extract_database_structure(
                engine=engine,
                schemas=schemas
            )

            """
            logger.info(
                "Repository returned type: %s",
                type(structure).__name__
            )
            
            logger.info(
                "Repository returned value: %r",
                structure
            )
            """

            if structure is None:
                raise RuntimeError(
                    "Repository returned None instead of database structure"
                )

            logger.info(
                "Database structure extracted successfully for scan %s", scan.id
            )

            return {
                "success": True,
                "errors": [],
                "data": structure
            }

        except Exception:

            logger.exception(
                "Error extracting database structure for scan %s",
                scan.id
            )

            return{
                "success": False,
                "errors": ["Unable to extract database structure"],
                "data": None
            }