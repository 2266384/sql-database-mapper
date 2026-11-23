import json
import logging
import fnmatch
import re

from pathlib import Path

from flask import current_app

logger = logging.getLogger(__name__)

"""
    Handles Documentation business logic and validation
"""

class DocumentationService:

    @staticmethod
    def load_database_structure(connection_id):
        """ Load the saved JSON structure for the database """

        if not isinstance(connection_id, int) or connection_id <= 0:
            raise ValueError("A valid connection ID is required")

        scans_directory = (
            Path(current_app.root_path).parent
            / "dbscans"
        )

        json_file = (
            scans_directory
            / str(connection_id)
            / "database_structure.json"
        )

        if not json_file.is_file():
            logger.warning(
                "Database documentation not found: connection_id=%s",
                connection_id
            )
            return None

        try:
            with json_file.open("r", encoding="utf-8") as file:
                structure = json.load(file)

            # Ensure the JSON belongs to the requested connection_id
            if structure.get("connection_id") != connection_id:
                logger.error(
                    "ConnectionID mismatch in documentation file: %s",
                    connection_id
                )
                return None

            logger.info(
                "Database documentation loaded: connection_id=%s",
                connection_id
            )

            return structure

        except (json.JSONDecodeError, OSError):
            logger.exception(
                "Unable to load database documentation: connection_id%s",
                connection_id
            )

            raise


    @staticmethod
    def get_database_summary(structure):
        """ Calculate database summary information """

        schemas = structure.get("schemas", [])
        tables = structure.get("tables", {})
        views = structure.get("views", {})
        relationships = structure.get("relationships", [])

        return {
            "connection_id": structure.get("connection_id"),
            "database": structure.get("database"),

            # Database objects
            "schema_count": len(schemas),
            "table_count": len(tables),
            "view_count": len(views),
            "relationship_count": len(relationships),

            # Column count
            "column_count": sum(
                len(table.get("columns", []))
                for table in tables.values()
            ),

            # Programmable objects
            "stored_procedure_count": len(
                structure.get("stored_procedures", {})
            ),
            "function_count": len(
                structure.get("functions", {})
            ),
            "trigger_count": len(
                structure.get("triggers", {})
            ),

            # Other database objects
            "sequence_count": len(
                structure.get("sequences", {})
            ),
            "synonym_count": len(
                structure.get("synonyms", {})
            )
        }


    @staticmethod
    def get_tables_by_schema(structure):
        """ Group discovered table by schema """

        grouped_tables = {}

        for table_key, table in structure.get("tables", {}).items():
            schema_name = table.get("schema", "unknown")

            grouped_tables.setdefault(
                schema_name, []
            ).append({
                "key": table_key,
                **table
            })

        # Sort tables alphabetically within each schema
        for schema_name in grouped_tables:
            grouped_tables[schema_name].sort(
                key=lambda table: table.get("name", "").lower()
            )

        return dict(sorted(grouped_tables.items()))



    """ Get a specific table structure """
    @staticmethod
    def get_table_by_name(structure, table_name):

        table = structure.get("tables", {}).get(table_name)

        if table is None:
            raise ValueError(f"Table '{table_name}' not found")

        return {
            "key": table_name,
            **table
        }



    @staticmethod
    def get_views_by_schema(structure):
        """ Group discovered views by schema """

        grouped_views = {}

        for view_key, view in structure.get("views", {}).items():

            schema_name = view.get("schema", "unknown")

            grouped_views.setdefault(
                schema_name, []
            ).append({
                "key": view_key,
                **view
            })

        for schema_name in grouped_views:
            grouped_views[schema_name].sort(
                key=lambda view: view.get("name", "").lower()
            )

        return dict(sorted(grouped_views.items()))




    @staticmethod
    def search(connection_id, search_value):
        """Search a saved database scan for matching objects."""

        if not isinstance(connection_id, int) or connection_id <= 0:
            raise ValueError("A valid connection ID is required")

        structure = DocumentationService.load_database_structure(
            connection_id
        )

        if not structure:
            return []

        return DocumentationService.search_database_structure(
            structure,
            search_value
        )


    @staticmethod
    def search_database_structure(structure, search_value):
        """
        Search database metadata using wildcard matching.

        Supports:
            *  Any number of characters
            ?  A single character
            %  SQL-style any number of characters
            _  SQL-style single character

        Searches:
            Schemas
            Tables and columns
            Indexes and constraints
            Views and view columns
            Stored procedures and parameters
            Functions and parameters
            Triggers
            Sequences
            Synonyms
        """

        if not isinstance(structure, dict):
            return []

        if not isinstance(search_value, str) or not search_value.strip():
            return []

        # Prepare search pattern
        pattern = search_value.strip()
        pattern = pattern.replace("%", "*")
        pattern = pattern.replace("_", "?")

        # Default to a contains search
        if not any(char in pattern for char in ("*", "?")):
            pattern = f"*{pattern}*"

        pattern = pattern.casefold()

        results = []
        seen = set()

        # -----------------------------------------
        # Matching helpers
        # -----------------------------------------

        def matches(value):

            if value is None:
                return False

            return fnmatch.fnmatchcase(
                str(value).casefold(),
                pattern
            )


        def get_objects(collection):
            """Support both dictionary and list collections."""

            if isinstance(collection, dict):
                return collection.items()

            if isinstance(collection, list):
                return [
                    (None, item) for item in collection
                ]

            return []


        def get_name(obj):

            if isinstance(obj, dict):
                return obj.get("name")

            if isinstance(obj, str):
                return obj

            return None


        def add_result(
            object_type,
            name,
            schema=None,
            parent=None,
            table_id=None,
            qualified_name=None
        ):

            if not name:
                return

            qualified_name = qualified_name or (
                f"{schema}.{name}" if schema else name
            )

            if not (
                matches(name)
                or matches(qualified_name)
            ):
                return

            result_key = (object_type, qualified_name)

            if result_key in seen:
                return

            seen.add(result_key)

            results.append({
                "type": object_type,
                "name": name,
                "schema": schema,
                "qualified_name": qualified_name,
                "parent": parent,
                "table_id": table_id
            })


        # -----------------------------------------
        # Schemas
        # -----------------------------------------

        for schema in structure.get("schemas", []):

            schema_name = get_name(schema)

            add_result(
                "Schema",
                schema_name
            )


        # -----------------------------------------
        # Tables, columns and related objects
        # -----------------------------------------

        for table_key, table in get_objects(
            structure.get("tables", {})
        ):

            if not isinstance(table, dict):
                continue

            schema = table.get("schema")
            table_name = table.get("name")

            if not table_name:
                continue

            table_id = (
                table_key
                if table_key is not None
                else f"{schema}.{table_name}" if schema
                else table_name
            )

            table_qualified_name = (
                f"{schema}.{table_name}" if schema
                else table_name
            )

            add_result(
                "Table",
                table_name,
                schema=schema,
                table_id=table_id,
                qualified_name=table_qualified_name
            )

            # Columns
            for column in get_objects(table.get("columns", [])):

                column_data = column[1]

                if not isinstance(column_data, dict):
                    continue

                column_name = column_data.get("name")

                add_result(
                    "Column",
                    column_name,
                    schema=schema,
                    table_id=table_id,
                    parent=table_name,
                    qualified_name=(
                        f"{table_qualified_name}.{column_name}"
                    )
                )

            # Indexes
            for _, index in get_objects(table.get("indexes", [])):

                index_name = get_name(index)

                add_result(
                    "Index",
                    index_name,
                    schema=schema,
                    parent=table_name,
                    table_id=table_id,
                    qualified_name=(
                        f"{table_qualified_name}.{index_name}"
                        if index_name else None
                    )
                )

            # Primary key
            primary_key = table.get("primary_key")

            if isinstance(primary_key, dict):

                primary_key_name = primary_key.get("name")

                add_result(
                    "Primary Key",
                    primary_key_name,
                    schema=schema,
                    parent=table_name,
                    table_id=table_id,
                    qualified_name=(
                        f"{table_qualified_name}.{primary_key_name}"
                        if primary_key_name else None
                    )
                )

            # Foreign keys
            for _, foreign_key in get_objects(
                table.get("foreign_keys", [])
            ):

                foreign_key_name = get_name(foreign_key)

                add_result(
                    "Foreign Key",
                    foreign_key_name,
                    schema=schema,
                    parent=table_name,
                    table_id=table_id,
                    qualified_name=(
                        f"{table_qualified_name}.{foreign_key_name}"
                        if foreign_key_name else None
                    )
                )

            # Unique constraints
            for _, constraint in get_objects(
                table.get("unique_constraints", [])
            ):

                constraint_name = get_name(constraint)

                add_result(
                    "Unique Constraint",
                    constraint_name,
                    schema=schema,
                    parent=table_name,
                    table_id=table_id,
                    qualified_name=(
                        f"{table_qualified_name}.{constraint_name}"
                        if constraint_name else None
                    )
                )

            # Check constraints
            for _, constraint in get_objects(
                table.get("check_constraints", [])
            ):

                constraint_name = get_name(constraint)

                add_result(
                    "Check Constraint",
                    constraint_name,
                    schema=schema,
                    parent=table_name,
                    table_id=table_id,
                    qualified_name=(
                        f"{table_qualified_name}.{constraint_name}"
                        if constraint_name else None
                    )
                )


        # -----------------------------------------
        # Views and view columns
        # -----------------------------------------

        for view_key, view in get_objects(
            structure.get("views", {})
        ):

            if not isinstance(view, dict):
                continue

            schema = view.get("schema")
            view_name = view.get("name")

            if not view_name:
                continue

            view_id = (
                f"{schema}.{view_name}" if schema
                else view_name
            )

            add_result(
                "View",
                view_name,
                schema=schema,
                qualified_name=view_id
            )

            # View columns
            for _, column in get_objects(view.get("columns", [])):

                if not isinstance(column, dict):
                    continue

                column_name = column.get("name")

                add_result(
                    "View Column",
                    column_name,
                    schema=schema,
                    parent=view_name,
                    qualified_name=(
                        f"{view_id}.{column_name}"
                        if column_name else None
                    )
                )


        # -----------------------------------------
        # Stored procedures, functions and triggers
        # -----------------------------------------

        object_groups = {
            "Stored Procedure": "stored_procedures",
            "Function": "functions",
            "Trigger": "triggers"
        }

        for object_type, collection_name in object_groups.items():

            collection = structure.get(collection_name, {})

            for object_key, obj in get_objects(collection):

                if not isinstance(obj, dict):
                    continue

                schema = obj.get("schema")
                name = obj.get("name")

                if not name:
                    continue

                object_qualified_name = (
                    f"{schema}.{name}" if schema
                    else name
                )

                add_result(
                    object_type,
                    name,
                    schema=schema,
                    qualified_name=object_qualified_name
                )

                # Parameters
                for _, parameter in get_objects(
                    obj.get("parameters", [])
                ):

                    if not isinstance(parameter, dict):
                        continue

                    parameter_name = parameter.get("name")

                    add_result(
                        "Parameter",
                        parameter_name,
                        schema=schema,
                        parent=name,
                        qualified_name=(
                            f"{object_qualified_name}.{parameter_name}"
                            if parameter_name else None
                        )
                    )


        # -----------------------------------------
        # Sequences and synonyms
        # -----------------------------------------

        object_groups = {
            "Sequence": "sequences",
            "Synonym": "synonyms"
        }

        for object_type, collection_name in object_groups.items():

            for object_key, obj in get_objects(
                structure.get(collection_name, {})
            ):

                if isinstance(obj, dict):
                    name = obj.get("name")
                    schema = obj.get("schema")
                else:
                    name = obj
                    schema = None

                add_result(
                    object_type,
                    name,
                    schema=schema
                )


        # -----------------------------------------
        # Sort results
        # -----------------------------------------

        return sorted(
            results,
            key=lambda result: (
                result["type"],
                result["schema"] or "",
                result["qualified_name"] or ""
            )
        )
