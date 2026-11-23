from flask import Blueprint, render_template, request, abort

from app.services.mapper.scans_service import ScansService
from app.services.mapper.documentation_service import DocumentationService
from app.services.mapper.connections_service import ConnectionsService
from app.services.mapper.diagram_service import DiagramService


"""
    Create a dedicated mapper Blueprint
    This allows us to define all the mapper functions together
"""
documentation_bp = Blueprint(
    "documentation"
    ,__name__
    ,url_prefix="/mapper"
)


"""
    Handles HTTP requests and responses
"""

@documentation_bp.route("/documentation")
def index():

    connections_with_scans = ScansService.get_connections_with_latest_scan()

    documentation_items = []

    for connection, latest_scan in connections_with_scans:

        structure = None
        summary = None

        if latest_scan:
            structure = (
                DocumentationService.load_database_structure(
                    connection.id
                )
            )

        if structure:
            summary = (
                DocumentationService.get_database_summary(
                    structure
                )
            )

        documentation_items.append({
            "connection": connection,
            "latest_scan": latest_scan,
            "summary": summary
        })

    return render_template(
        "mapper/documentation_index.html",
        documentation_items=documentation_items
    )


# Database documentation route
@documentation_bp.route("/documentation/<int:connection_id>")
def documentation(connection_id):

    structure = DocumentationService.load_database_structure(
        connection_id
    )

    if structure is None:
        return render_template(
            "mapper/documentation.html",
            connection_id=connection_id,
            structure=None,
            summary=None,
            tables_by_schema=None,
            views_by_schema=None
        ), 404


    summary = DocumentationService.get_database_summary(
        structure
        )

    tables_by_schema = DocumentationService.get_tables_by_schema(
        structure
    )

    views_by_schema = DocumentationService.get_views_by_schema(
        structure
    )

    return render_template(
        "mapper/documentation.html",
        connection_id=connection_id,
        structure=structure,
        summary=summary,
        tables_by_schema=tables_by_schema,
        views_by_schema=views_by_schema
    )


# Database diagram route
@documentation_bp.route("/diagram/<int:connection_id>")
def view_diagram(connection_id):

    schema_name = request.args.get("schema")

    if not schema_name:
        abort(400, description="Schema name is required")

    structure = DocumentationService.load_database_structure(connection_id)

    if structure is None:
        abort(404, description="Database documentation not found")

    diagram = DiagramService.generate_mermaid_diagram(
        structure, 
        schema_name
    )

    print("Generated Mermaid diagram:")
    print(diagram)

    return render_template(
        "mapper/schema_diagram.html", 
        connection_id=connection_id,
        database=structure.get("database"),
        schema_name=schema_name,
        diagram=diagram
    )


# Table information
@documentation_bp.route("<int:connection_id>/table/<path:table_name>")
def view_table(connection_id, table_name):

    structure = DocumentationService.load_database_structure(connection_id)

    if structure is None:
        abort(404, description="Database documentation not found")

    # Retrieve the selected table
    table = DocumentationService.get_table_by_name(
        structure,
        table_name
    )

    if table is None:
        abort(404, description="Table not found")

    relationships = structure.get("relationships", [])
    # Relationships originating from this table
    outgoing_relationships = [
        relationship
        for relationship in relationships
        if relationship.get("source") == table_name
    ]

    # Get the relationships for the table
    incoming_relationships = [
        relationship
        for relationship in relationships
        if relationship.get("target") == table_name
    ]

    return render_template(
        "mapper/table.html", 
        table=table,
        table_name=table_name,
        connection_id=connection_id,
        database=structure.get("database"),
        schema_name=table.get("schema"),
        outgoing_relationships=outgoing_relationships,
        incoming_relationships=incoming_relationships
    )


@documentation_bp.route("/search")
def search():

    connection_id = request.args.get("connection_id", type=int)
    search_value = request.args.get("q", "").strip()

    connections = ConnectionsService.get_connections()

    results = []

    if connection_id and search_value:
        results = DocumentationService.search(
            connection_id,
            search_value
        )

    return render_template(
        "mapper/documentation/search.html",
        connections=connections,
        connection_id=connection_id,
        search_value=search_value,
        results=results
    )