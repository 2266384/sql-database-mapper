from app.repositories.connections_repository import ConnectionsRepository

"""
    Handles Connections business logic and validation
"""

class ConnectionsService:

    VALID_AUTHENTICATION_TYPES = ("SQL", "WINDOWS")

    @staticmethod
    def validate_connection(
        connection_name,
        server,
        database,
        authentication_type,
        port=1433
    ):

        """
            Validates the connection parameters
        """

                
        # Normalise the inputs
        connection_name = (connection_name or "").strip()
        server = (server or "").strip()
        database = (database or "").strip()
        authentication_type = (authentication_type or "").strip().upper()

        errors = []

        if not connection_name:
            errors.append("Connection name is required")

        if not server:
            errors.append("Server name is required")

        if not database:
            errors.append("Database name is required")

        try:
            port = int(port)

            if not 1 <= port <= 65535:
                errors.append("Port must be between 1 and 65535")
        
        except (TypeError, ValueError):
            errors.append("A valid SQL Server port is required")

        if authentication_type not in (
            ConnectionsService.VALID_AUTHENTICATION_TYPES
        ):
            errors.append("Invalid authentication type")

        return errors

    
    @staticmethod
    def get_connections():
        """ Retrieve all saved connections """

        return ConnectionsRepository.get_connections()


    @staticmethod
    def get_connection(connection_id):
        """ Retrieve a connetion by id """

        connection = ConnectionsRepository.get_connection_by_id(
            connection_id
        )

        if connection is None:
            raise ValueError("Database connection is not found")

        return connection

    
    @staticmethod
    def create_connection(
        connection_name,
        server,
        database,
        authentication_type,
        port=1433
    ):

        """ Validate and create a new connection """

        # Normalise the inputs
        connection_name = (connection_name or "").strip()
        server = (server or "").strip()
        database = (database or "").strip()
        authentication_type = (authentication_type or "").strip().upper()

        # Validate fields
        errors = ConnectionsService.validate_connection(
            connection_name,
            server,
            database,
            authentication_type,
            port
        )

        if errors:
            raise ValueError(" ".join(errors))

        port = int(port)

        # Check for duplicate connection names
        existing = ConnectionsRepository.get_connection_by_name(
            connection_name
        )

        if existing:
            raise ValueError("A connection with that name already exists")

        # Persist connection
        return ConnectionsRepository.create_connection(
            connection_name, 
            server, 
            database, 
            authentication_type,
            port
        )


    @staticmethod
    def update_connection(
        connection_id,
        connection_name,
        server,
        database,
        authentication_type,
        port=1433
    ):
        """ Validate and update an existing connection """

        # Normalise input
        connection_name = (connection_name or "").strip()
        server = (server or "").strip()
        database = (database or "").strip()
        authentication_type = (authentication_type or "").strip().upper()

        # Retrieve existing connection
        connection = ConnectionsService.get_connection(connection_id)

        # Validate fields
        errors = ConnectionsService.validate_connection(
            connection_name,
            server,
            database,
            authentication_type,
            port
        )

        if errors:
            raise ValueError(" ".join(errors))

        port = int(port)

        # Check for duplicate names excluding current connection
        existing = ConnectionsRepository.get_connection_by_name(connection_name)

        if existing and existing.id != connection_id:
            raise ValueError("A connection with that name already exists")

        # Persist changes
        return ConnectionsRepository.update_connection(
            connection,
            connection_name,
            server,
            database,
            authentication_type,
            port
        )


    @staticmethod
    def delete_connection(connection_id):
        """ Delete an existing connection """

        connection = ConnectionsService.get_connection(connection_id)

        ConnectionsRepository.delete_connection(connection)