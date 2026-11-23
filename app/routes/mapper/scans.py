import logging

from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services import ScansService, ConnectionsService

from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


"""
    Create a dedicated connections Blueprint
    This allows us to define all the scans functions together
"""
scans_bp = Blueprint(
    "scans"
    ,__name__
    ,url_prefix="/mapper/scans"
)


"""
    Handles HTTP requests and responses
"""


# List saved database scans
@scans_bp.route("/")
def index():

    connections = ScansService.get_connections_with_latest_scan()

    return render_template(
        "mapper/scans.html", 
        connections=connections
    )


# Create a scan of the database
@scans_bp.route("/<int:connection_id>/create",methods=["POST"])
def create(connection_id):


    try:
        connection = ConnectionsService.get_connection(connection_id)

        # Retrieve credentials submitted through the modal
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")


        # Start database scan
        result = ScansService.start_scan(
            connection=connection,
            username=username or None,
            password=password or None
        )

        if result["success"]:
            flash(result["message"], "success")

        else:
            flash(result["message"], "danger")


    except ValueError as error:
        flash(str(error), "warning")

    except Exception:

        logger.exception(
            "Unexpected error while starting scan for connection ID %s", connection_id
        )

        # Log the detailed exception server-side
        flash(
            "An unexpected error occurred while starting the database scan",
            "danger"
        )

    return redirect(url_for("scans.index"))

