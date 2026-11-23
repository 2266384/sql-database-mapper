from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import DatabaseConnection

"""
    Performs read and write functions on saved connection configurations
"""

class ConnectionsRepository:

    """ Return all saved connections from the Database Connection table """
    @staticmethod
    def get_connections():

        return (
            DatabaseConnection.query
            .order_by(DatabaseConnection.connection_name)
            .all()
        )


    """ Return a specific connection using its ID """
    @staticmethod
    def get_connection_by_id(connection_id):

        return db.session.get(
            DatabaseConnection,
            connection_id
        )

    """ Return a specific connection using its name """
    @staticmethod
    def get_connection_by_name(connection_name):

        return (
            DatabaseConnection.query
            .filter_by(connection_name=connection_name)
            .first()
        )

    """ Create a new database connection and store it in the DatabaseConnection table """
    @staticmethod
    def create_connection(
        connection_name,
        server,
        database,
        authentication_type,
        port=1433
    ):

        # Create a new connection
        connection = DatabaseConnection(
            connection_name=connection_name,
            server=server,
            database=database,
            authentication_type=authentication_type,
            port=port
        )

        # Try the new connection and store it in the database table
        try:
            db.session.add(connection)
            db.session.commit()

            return connection

        # Rollback in the event of failure
        except SQLAlchemyError:
            db.session.rollback()
            raise


    """ Update the configuration details for an existing connection """
    @staticmethod
    def update_connection(
        connection,
        connection_name,
        server,
        database,
        authentication_type,
        port=1433
    ):

        # Update the database connection and store it in the database
        try:
            connection.connection_name=connection_name
            connection.server=server
            connection.database=database
            connection.authentication_type=authentication_type
            connection.port = port

            db.session.commit()

            return connection

        # Rollback the update if there's an error
        except SQLAlchemyError:
            db.session.rollback()
            raise


    """ Delete a connection """
    @staticmethod
    def delete_connection(connection):

        try:
            db.session.delete(connection)
            db.session.commit()
            return True
        
        except SQLAlchemyError:
            db.session.rollback()
            raise
