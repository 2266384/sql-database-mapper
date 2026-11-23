from flask import Blueprint, render_template, request, redirect, url_for, flash
#from app.services import MapperService

from sqlalchemy.exc import SQLAlchemyError

"""
    Create a dedicated mapper Blueprint
    This allows us to define all the mapper functions together
"""
mapper_bp = Blueprint(
    "mapper"
    ,__name__
    ,url_prefix="/mapper"
)


"""
    Handles HTTP requests and responses
"""

# Main mapper route
@mapper_bp.route("/")
def index():
    return render_template("mapper/index.html")

