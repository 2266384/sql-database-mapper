import json
import logging

from pathlib import Path
from werkzeug.utils import secure_filename
from datetime import datetime, timezone

from celery import shared_task
from flask import current_app
from sqlalchemy import create_engine

from app.extensions import db
from app.database.connection_factory import ConnectionFactory
from app.repositories.scans_repository import ScansRepository
from app.services.mapper.connections_service import ConnectionsService
from app.services.mapper.scans_service import ScansService
from app.security.credentials import decrypt_credentials

logger = logging.getLogger(__name__)


def create_scan_engine(connection, username=None, password=None):

    connection_url = ConnectionFactory.build_sql_server_url(
        server=connection.server,
        database=connection.database,
        authentication_type=connection.authentication_type,
        port=connection.port or 1433,
        username=username,
        password=password
    )

    return create_engine(
        connection_url,
        pool_pre_ping=True
    )


def save_scan_output(connection_id, structure):
    """
        Save the extracted database structure using the connection ID

        Each connection has its own directory and JSON file
        Existing files are overwritten by subsequent successful scans
    """

    if not connection_id:
        raise ValueError("Connection ID is required")

    # Set the output path
    output_directory = (
        Path(current_app.root_path).parent
        / "dbscans"
        / str(connection_id)
    )

    # Make the directory if it doesn't exist
    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = output_directory / "database_structure.json"

    # Include the connection ID in the saved structure
    structure["connection_id"] = connection_id

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            structure,
            file,
            indent=4,
            ensure_ascii=False,
            default=str
        )

    logger.info(
        "Databsase scan saved: connection_id=%s, database=%s, location=%s",
        connection_id,
        structure.get("database"),
        output_file
    )

    return str(output_file) 



@shared_task(
    bind=True,
    name="app.tasks.scans.execute_scan",
    ignore_result=True
)
def execute_scan(
    self,
    scan_id,
    connection_id,
    encrypted_credentials=None
):

    """ Execute a database scan in the background """

    logger.info("Starting background scan: %s", scan_id)

    engine = None

    try:

        # --------------------------------------------------
        # 1. Retrieve scan and saved connection
        # --------------------------------------------------
        scan = ScansRepository.get_scan_by_id(scan_id)

        if scan is None:
            raise ValueError(f"Scan {scan_id} was not found")

        if scan.database_connection_id != connection_id:
            raise ValueError("Scan does not belong to the supplied connection")

        connection = ConnectionsService.get_connection(connection_id)

        if connection is None:
            raise ValueError(f"Connection {connection_id} was not found")



        # --------------------------------------------------
        # 2. Update scan status to RUNNING
        # --------------------------------------------------
        ScansRepository.update_scan(
            scan_id,
            status="RUNNING",
            started_at=datetime.now(timezone.utc),
            error_message=None
        )



        # --------------------------------------------------
        # 3. Decrypt credentials if supplied
        # --------------------------------------------------
        credentials = (
            decrypt_credentials(encrypted_credentials)
            if encrypted_credentials
            else {}
        )

        username = credentials.get("username")
        password = credentials.get("password")

        
        
        # --------------------------------------------------
        # 4. Create and test database engine
        # --------------------------------------------------
        engine = create_scan_engine(
            connection=connection,
            username=username,
            password=password
        )

        with engine.connect() as database_connection:
            database_connection.exec_driver_sql("SELECT 1")

        logger.info(
            "Database connection established for scan: %s",
            scan_id
        )

        

        # --------------------------------------------------
        # 5. Extract database structure
        # --------------------------------------------------

        # Relaod the scan after updating its status
        scan = ScansRepository.get_scan_by_id(scan_id)

        mapper_result = ScansService.extract_database_structure(
            scan=scan,
            engine=engine
        )

        """
        logger.info(
            "Mapper result type: %s",
            type(mapper_result).__name__
        )

        logger.info(
            "Mapper result: %r",
            mapper_result
        )
        """

        if not isinstance(mapper_result, dict):
            raise RuntimeError(
                "Database structure extraction returned an unexpected result"
            )

        if not mapper_result.get("success"):
            raise RuntimeError(
                "; ".join(mapper_result.get("errors", []))
                or "Database structure extraction failed"
            )

        structure = mapper_result.get("data")

        if structure is None:
            raise RuntimeError(
                "Database structure extraction returned no data"
            )



        # --------------------------------------------------
        # 6. Save extracted database structure
        # --------------------------------------------------
        output_location = save_scan_output(
            connection_id,
            structure
        )

        if not isinstance(structure, dict):
            raise RuntimeError(
                "Extracted database structure must be a dictionary"
            )

        tables = structure.get("tables", {})

        object_count = len(tables)



        # --------------------------------------------------
        # 7. Update scan status to COMPLETED
        # --------------------------------------------------
        ScansRepository.update_scan(
            scan_id,
            status="COMPLETED",
            completed_at=datetime.now(timezone.utc),
            object_count=object_count,
            output_location=output_location,
            error_message=None
        )

        logger.info(
            "Scan completed successfully: %s. Objects: %s", 
            scan_id,
            object_count
        )

    except Exception:
        logger.exception(
            "Background scan failed: %s",
            scan_id
        )

        # --------------------------------------------------
        # 8. Update scan status to FAILED
        # --------------------------------------------------

        try:
            ScansRepository.update_scan(
                scan_id,
                status="FAILED",
                completed_at=datetime.now(timezone.utc),
                error_message="Scan failed.  Check application logs"
            )

        except Exception:
            logger.exception(
                "Unable to update scan status to FAILED: %s",
                scan_id
            )

        raise

    finally:

        # --------------------------------------------------
        # 9. Clean up
        # --------------------------------------------------

        if engine is not None:
            engine.dispose()

        db.session.remove()
