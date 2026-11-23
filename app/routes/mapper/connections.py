from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services import ConnectionsService
from app.services import ConnectionTestService

from sqlalchemy.exc import SQLAlchemyError

"""
    Create a dedicated connections Blueprint
    This allows us to define all the connections functions together
"""
connections_bp = Blueprint(
    "connections"
    ,__name__
    ,url_prefix="/mapper/connections"
)


"""
    Handles HTTP requests and responses
"""


# List saved database connections
@connections_bp.route("/")
def connections():

    connections = ConnectionsService.get_connections()

    return render_template(
        "mapper/connections.html", 
        connections=connections
    )


# Create a new database connection
@connections_bp.route("/connection", methods=["GET", "POST"])
def create_connection():

    if request.method == "POST":

        # Retrieve form values
        connection_name = request.form.get("connection_name")
        server = request.form.get("server")
        database = request.form.get("database")
        authentication_type = request.form.get("authentication_type")
        port = request.form.get("port", 1433)

        try:

            ConnectionsService.create_connection(
                connection_name,
                server,
                database,
                authentication_type,
                port
            )

            flash(
                "Database connection saved successfully",
                "success"
            )

            return redirect(url_for("connections.connections"))

        except ValueError as error:

            flash(
                str(error),
                "danger"
            )

        except SQLAlchemyError:

            flash(
                "Unable to save the database connection",
                "danger"
            )

    return render_template(
        "mapper/connection_form.html",
        connection=None
    )


# Modify an existing database connection
@connections_bp.route("/connection/<int:connection_id>/edit",methods=["GET", "POST"])
def edit_connection(connection_id):

    try:
        connection = ConnectionsService.get_connection(connection_id)

    except ValueError:

        flash(
            "Database connection not found",
            "warning"
        )

        return redirect(url_for("connection.connections"))



    if request.method == "POST":

        # Retrieve form values
        connection_name = request.form.get("connection_name")
        server = request.form.get("server")
        database = request.form.get("database")
        authentication_type = request.form.get("authentication_type")
        port = request.form.get("port", 1433)

        try:

            ConnectionsService.update_connection(
                connection,
                connection_name,
                server,
                database,
                authentication_type,
                port
            )

            flash(
                "Database connection updated successfully",
                "success"
            )

            return redirect(url_for("connections.connections"))

        except ValueError as error:

            flash(str(error), "danger")

        except SQLAlchemyError:

            flash("Unable to update the database connection", "danger")

    return render_template(
        "mapper/connection_form.html",
        connection=connection
    )


# Delete an existing database connection
@connections_bp.route("/connection/<int:connection_id>/delete",methods=["POST"])
def delete_connection(connection_id):

    try:
        ConnectionsService.delete_connection(connection_id)

        flash("Database connection deleted successfully", "success")

    except ValueError as error:

        flash(str(error), "warning")

        return redirect(url_for("connections.connections"))

    except SQLAlchemyError:

        flash(
            "Unable to delete the database connection",
            "danger"
        )

    return redirect(url_for("connections.connections"))



@connections_bp.route("/<int:connection_id>/test", methods=["POST"])
def test(connection_id):
    """Test a saved database connection."""

    try:
        # Retrieve the saved connection configuration
        connection = ConnectionsService.get_connection(connection_id)

        # Retrieve credentials submitted through the modal
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Test the connection
        result = ConnectionTestService.test_connection(
            connection_name=connection.connection_name,
            server=connection.server,
            database=connection.database,
            authentication_type=connection.authentication_type,
            port=connection.port,
            username=username,
            password=password
        )

        if result["success"]:
            flash(
                f"Connection to {connection.connection_name} successful.",
                "success"
            )
        else:
            flash(
                f"Connection test failed: {result['message']}",
                "danger"
            )

    except ValueError as error:
        flash(str(error), "warning")

    except Exception:
        # Log the detailed exception server-side
        flash(
            "An unexpected error occurred while testing the connection.",
            "danger"
        )

    return redirect(url_for("connections.connections"))