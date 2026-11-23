import logging
import re

logger = logging.getLogger(__name__)

"""
    Handles Diagram business logic and validation
"""

class DiagramService:

    @staticmethod
    def generate_mermaid_diagram(structure, schema_name=None):
        """
            Generates a Mermaid ER Diagram

            Args:
                structure: Database scan JSON structure
                schema_name: Optional schema to filter by

            Returns:
                Mermaid ER diagram definition
        """

        lines = ["erDiagram"]

        tables = structure.get("tables", {})
        relationships = structure.get("relationships", [])

        # Keep track of tables for relationship validation
        table_names = set()

        # Filter tables by schema if requested
        selected_tables = {
            key: table
            for key, table in tables.items()
            if schema_name is None
            or table.get("schema") == schema_name
        }

        # First pass: generate entities
        for table_key, table in selected_tables.items():

            schema = table.get("schema", "dbo")
            table_name = table.get("name", table_key)

            # Schema-qualified table identifier
            identifier = DiagramService._identifier(
                schema,
                table_name
            )

            table_names.add(identifier)

            lines.append(f"    {identifier} {{")

            primary_keys = DiagramService._get_primary_key_columns(table)

            foreign_keys = DiagramService._get_foreign_key_columns(table)

            unique_columns = DiagramService._get_unique_columns(table)

            # Generate column attributes
            for column in table.get("columns", []):

                original_name = column.get("name", [])

                column_name = DiagramService._safe_name(original_name)
                column_type = (
                    column.get("data_type")
                    or column.get("type")
                    or "UNKNOWN"
                )

                column_type = DiagramService._safe_type(column_type)

                attributes = []

                if original_name in primary_keys:
                    attributes.append("PK")

                if original_name in foreign_keys:
                    attributes.append("FK")

                if original_name in unique_columns:
                    attributes.append("UK")

                attributes_text = (
                    f" {','.join(attributes)}"
                    if attributes else ""
                )

                # Add column metadata as Mermaid attribute comments
                comment = DiagramService._get_column_comment(column)

                comment_text = (
                    f' "{comment}"'
                    if comment else ""
                )

                lines.append(
                    f"        {column_type} {column_name}"
                    f"{attributes_text}{comment_text}"
                )

            lines.append("    }")

            # Add table-level metadata
            DiagramService._append_table_metadata(
                lines,
                table,
                identifier
            )

            lines.append("")

        # Second pass: generate relationships
        for relationship in relationships:
                
            source = DiagramService._table_identifier(
                relationship.get("source", "")
            )
    
            target = DiagramService._table_identifier(
                relationship.get("target", "")
            )
    
            # Only include the relationships where both tables
            # are included in the selected diagram
            if source not in table_names:
                continue
                        
            if target not in table_names:
                continue
                        
            lines.append(
                f"    {target} ||--o{{ {source} : references"
            )
    
        return "\n".join(lines)


    @staticmethod
    def _get_primary_key_columns(table):
        """
            Extract primary key column names.
        """

        primary_key = table.get("primary_key")

        if not primary_key:
            return set()

        if isinstance(primary_key, dict):
            return set(primary_key.get("columns", []))

        if isinstance(primary_key, list):
            return set(primary_key)
        
        return set()



    @staticmethod
    def _get_foreign_key_columns(table):

        columns = set()

        for fk in table.get("foreign_keys", []):

            if isinstance(fk, dict):
                columns.update(fk.get("columns", []))

        return columns


    @staticmethod
    def _get_unique_columns(table):
        """
            Extract columns that are part of unique constraints
            or unique indexes
        """

        unique_columns =  set()

        # Unique constraints
        for constraint in table.get("unique_constraints", []):

            columns = constraint.get("columns", [])

            if len(columns) == 1:
                unique_columns.add(columns[0])


        # Unique indexes
        for index in table.get("indexes", []):

            if index.get("unique", False):

                columns = index.get("columns", [])

                if len(columns) == 1:
                    unique_columns.add(columns[0])

        return unique_columns


    @staticmethod
    def _get_column_comment(column):
        """
            Build optional Mermaid column description
            using column metadata
        """

        comments = []

        if column.get("autoincrement"):
            comments.append("IDENTITY")

        # Nullability
        if column.get("nullable") is False:
            comments.append("NOT NULL")

        elif column.get("nullable") is True:
            comments.append("NULL")

        # Default value
        default = column.get("default")

        if default is not None:
            comments.append(f"DEFAULT: {default}")

        return DiagramService._safe_comment(
            "; ".join(comments)
        )

    
    @staticmethod
    def _append_table_metadata(lines, table, identifier):
        """
            Preserve table-level metadata as Mermaid comments

            Mermaid does not natively render check constraints
            or indexes as ER diagram attributes
        """

        # Index metadata
        for index in table.get("indexes", []):

            index_name = index.get("name", "unnamed")

            columns = ", ".join(
                index.get("columns", [])
            )

            index_type = (
                "UNIQUE INDEX"
                if index.get("unique", False)
                else "INDEX"
            )

            lines.append(
                f"    %% {index_type}: {identifier}."
                f"{index_name} ({columns})"
            )

        # Unique constraints
        for constraint in table.get("unique_constraints", []):

            constraint_name = constraint.get("name", "unnamed")

            columns = ", ".join(
                constraint.get("columns", [])
            )

            lines.append(
                f"    %% UNIQUE CONSTRAINT: "
                f"{identifier}.{constraint_name} ({columns})"
            )

        # Check for constraints
        for constraint in table.get("check_constraints", []):

            constraint_name = constraint.get(
                "name",
                constraint.get("constraint_name", "unnamed")
            )

            definition = constraint.get(
                "definition",
                ""
            )

            disabled = constraint.get("is_disabled", False)
            not_trusted = constraint.get("is_not_trusted", False)

            status = []

            if disabled:
                status.append("DISABLED")

            if not_trusted:
                status.append("NOT TRUSTED")

            status_text = (
                f" [{', '.join(status)}]"
                if status else ""
            )

            definition = DiagramService._safe_comment(
                definition
            )

            lines.append(
                f"    %% CHECK: {identifier}.{constraint_name}"
                f"{status_text}: {definition}"
            )


    @staticmethod
    def _table_identifier(table_name):
        """ Convert schema.table into a Mermaid identifier """

        schema, _, table = table_name.partition(".")

        return DiagramService._identifier(schema, table)


    @staticmethod
    def _identifier(schema, table):
        """Create a valid Mermaid entity identifier."""

        value = f"{schema}_{table}"

        # Mermaid identifiers should be simple identifiers
        return re.sub(r"[^a-zA-Z0-9_]", "_", value)


    @staticmethod
    def _safe_name(name):
        return re.sub(r"[^a-zA-Z0-9_]", "_", str(name))


    @staticmethod
    def _safe_type(column_type):
        # Remove SQL Server collation information and
        # simplify types for Mermaid

        if not column_type:
            return "UNKNOWN"

    
        column_type = str(column_type)

        # Remove SQL Server collation information
        column_type = column_type.split(" COLLATE ")[0]

        column_type = re.sub(r"[^a-zA-Z0-9_]", "_", column_type)

        column_type = re.sub(r"_+", "_", column_type)

        return re.sub(r"_+", "_", column_type).strip("_") or "UNKNOWN"


    @staticmethod
    def _safe_comment(value):
        """
            Sanitise comments for mermaid attribute descriptions
            and Mermaid source comments
        """

        if value is None:
            return ""

        value = str(value)

        # Keep comments on a single line
        value = re.sub(r"[\r\n]+", " ", value)

        # Prevent quotes breaking Mermaid attribute syntax
        value = value.replace('"', "'")

        return value.strip()