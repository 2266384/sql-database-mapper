import logging
from sqlalchemy import select, inspect, text

from app.extensions import db
from app.models import Scan, DatabaseConnection

logger = logging.getLogger(__name__)

"""
    Methods for updating the Scan table in the database
"""

class ScansRepository:

    """ Returns a list of all the scans along with their latest scan date """
    @staticmethod
    def get_connections_with_latest_scan():
        
        # Find the ID of the latest completed scan for each connection
        latest_scan_id = (
            select(Scan.id)
            .where(
                Scan.database_connection_id == DatabaseConnection.id,
                Scan.status == "COMPLETED"
            )
            .order_by(
                Scan.completed_at.desc(),
                Scan.id.desc()
            )
            .limit(1)
            .correlate(DatabaseConnection)  # Stops the DatabaseConnection from being correlated out leaving no FROM
            .scalar_subquery()
        )

        # Return every connection, including those without a completed scan
        stmt = (
            select(DatabaseConnection, Scan)
            .outerjoin(
                Scan,
                Scan.id == latest_scan_id
            )
            .order_by(DatabaseConnection.connection_name)
        )

        return db.session.execute(stmt).all()


    """ 
        Create a new PENDING scan for a database connection in the Scans table 
        the Celery Worker will use this to identify the next extraction
        task that needs to be run in the background
    """
    @staticmethod
    def create_scan(connection_id):

        scan = Scan(
            database_connection_id=connection_id,
            status="PENDING",
            object_count=0
        )

        try:
            db.session.add(scan)
            db.session.commit()
            db.session.refresh(scan)

            return scan

        except Exception:
            db.session.rollback()
            raise


    """ Retrieve a scan by its ID """
    @staticmethod
    def get_scan_by_id(scan_id):

        return db.session.get(Scan, scan_id)



    """ 
        Update scan information 

        Requires a scan id and an arbitrary number of keyword
        arguments (**updates)
    """
    @staticmethod
    def update_scan(scan_id, **updates):

        scan = db.session.get(Scan, scan_id)

        if scan is None:
            return None

        allowed_fields = {
            "status",
            "started_at",
            "completed_at",
            "object_count",
            "output_location",
            "error_message"
        }

        invalid_fields = set(updates) - allowed_fields

        if invalid_fields:
            raise ValueError(
                f"Invalid scan fields: {', '.join(sorted(invalid_fields))}"
            )

        try:
            for field, value in updates.items():
                setattr(scan, field, value)

            db.session.commit()
            db.session.refresh(scan)

            return scan

        except Exception:
            db.session.rollback()
            raise


    # ----------------------------------------------------------
    # ORCHESTRATOR FOR EXTRACTING DATABASE STRUCTURE
    # ----------------------------------------------------------

    """
        Recursively extracts the structure of a database

        Args:
            engine: SQLAlchemy Engine connected to the target database
            schemas: Optional list of schemas to extract

        Returns:
          A dictionary representing the database structure
    """
    @staticmethod
    def extract_database_structure(engine, schemas=None):

        inspector = inspect(engine)

        # Retrieve available schemas
        available_schemas = ScansRepository.extract_schemas(engine)

        available_schema_names = [
            schema["name"] for schema in available_schemas
        ]

        # Determine selected schemas
        if schemas is None:
            selected_schemas = available_schema_names
        else:
            selected_schemas = schemas

        logger.info(
            "Starting database extraction: %s",
            engine.url.database
        )

        # Database structure
        structure = {
            "database": engine.url.database,
            "metadata": ScansRepository.extract_database_metadata(engine),
            "schemas": [
                schema for schema in available_schemas
                if schema["name"] in selected_schemas
            ],
            "tables": {},
            "views": {},
            "relationships": [],
            "stored_procedures": {},
            "functions": {},
            "triggers": {},
            "sequences": {},
            "synonyms": {}
        }

        # Extract tables and relationships
        structure["tables"], structure["relationships"] = (
            ScansRepository.extract_tables(
                engine,
                inspector,
                selected_schemas
            )
        )

        # Extract views
        structure["views"] = ScansRepository.extract_views(
            engine,
            inspector,
            selected_schemas
        )

        # Extract SQL modules
        modules = ScansRepository.extract_sql_modules(
            engine,
            selected_schemas
        )

        structure.update(modules)

        # Extract module parameters
        parameters = ScansRepository.extract_module_parameters(
            engine,
            selected_schemas
        )

        # Extract object dependencies
        dependencies = ScansRepository.extract_dependencies(
            engine,
            selected_schemas
        )

        # Attach parameters and dependencies to modules
        for category in (
            "stored_procedures",
            "functions",
            "triggers"
        ):
            for key, module in structure[category].items():
                module["parameters"] = parameters.get(key, [])
                module["dependencies"] = dependencies.get(key, [])

        # Attach dependencies to views
        for key, view in structure["views"].items():
            view["dependencies"] = dependencies.get(key, [])

        # Extract sequences
        structure["sequences"] = ScansRepository.extract_sequences(
            engine,
            selected_schemas
        )

        # Extract synonyms
        structure["synonyms"] = ScansRepository.extract_synonyms(
            engine,
            selected_schemas
        )

        logger.info(
            "Database extraction complete: "
            "schemas=%s, tables=%s, views=%s, "
            "procedues=%s, functions=%s, triggers=%s",
            len(structure["schemas"]),
            len(structure["tables"]),
            len(structure["views"]),
            len(structure["stored_procedures"]),
            len(structure["functions"]),
            len(structure["triggers"])
        )

        return structure


    # ----------------------------------------------------------
    # DATABASE METADATA
    # ----------------------------------------------------------
    @staticmethod
    def extract_database_metadata(engine):

        query = text("""
            SELECT
                DB_NAME() AS database_name,
                DATABASEPROPERTYEX(
                    DB_NAME(), 'Collation'
                ) AS collation,
                d.compatibility_level,
                d.recovery_model_desc AS recovery_model,
                d.state_desc AS state,
                d.user_access_desc AS user_access,
                d.create_date
            FROM sys.databases d
            WHERE d.name = DB_NAME()
        """)

        with engine.connect() as connection:
            result = connection.execute(query).mappings().first()

        if result is None:
            return {}

        return {
            "name": result["database_name"],
            "collation": result["collation"],
            "compatibility_level": result["compatibility_level"],
            "recovery_model": result["recovery_model"],
            "state": result["state"],
            "user_access": result["user_access"],
            "created_at": (
                result["create_date"].isoformat()
                if result["create_date"]
                else None
            )
        }


    # ---------------------------------------------------------
    # SCHEMAS
    # ---------------------------------------------------------
    @staticmethod
    def extract_schemas(engine):

        query = text("""
            SELECT
                s.name,
                USER_NAME(s.principal_id) AS owner
            FROM sys.schemas s
            WHERE s.name NOT IN (
                'sys',
                'INFORMATION_SCHEMA'
            )
            ORDER BY s.name
        """)

        with engine.connect() as connection:
            results = connection.execute(query).mappings().all()

        return [
            {
                "name": row["name"],
                "owner": row["owner"]
            }
            for row in results
        ]


    # ---------------------------------------------------------
    # TABLES
    # ---------------------------------------------------------
    @staticmethod
    def extract_tables(engine, inspector, schemas):

        tables = {}
        relationships = []

        for schema in schemas:

            table_names = inspector.get_table_names(schema=schema)

            native_types = ScansRepository.get_sql_server_column_types(
                engine,
                schema
            )

            for table_name in table_names:

                table_key = f"{schema}.{table_name}"

                # Columns
                columns = inspector.get_columns(
                    table_name,
                    schema=schema
                )


                column_details = []

                for column in columns:

                    column_name = column["name"]

                    column_details.append({
                        "name": column_name,
                        "type": native_types.get(table_name, {}).get(
                            column_name,
                            str(column["type"])
                        ),
                        "nullable": column["nullable"],
                        "default": column.get("default"),
                        "autoincrement": column.get("autoincrement")
                    })

                # Primary key
                primary_key = inspector.get_pk_constraint(
                    table_name,
                    schema=schema
                )

                # Foreign keys
                foreign_keys = inspector.get_foreign_keys(
                    table_name,
                    schema=schema
                )

                foreign_key_details = []
                related_tables = []

                for fk in foreign_keys:

                    referenced_schema = (
                        fk.get("referred_schema") or schema
                    )

                    referenced_table = fk["referred_table"]

                    referenced_key = (
                        f"{referenced_schema}.{referenced_table}"
                    )

                    foreign_key_details.append({
                        "name": fk["name"],
                        "columns": fk["constrained_columns"],
                        "referenced_schema": referenced_schema,
                        "referenced_table": referenced_table,
                        "referenced_columns": fk["referred_columns"],
                        "onupdate": fk.get("options", {}).get("onupdate"),
                        "ondelete": fk.get("options", {}).get("ondelete")
                    })

                    related_tables.append(referenced_key)

                    relationships.append({
                        "source": table_key,
                        "target": referenced_key,
                        "foreign_key": fk["name"],
                        "columns": fk["constrained_columns"],
                        "referenced_columns": fk["referred_columns"]
                    })

                # Indexes
                indexes = inspector.get_indexes(
                    table_name,
                    schema=schema
                )

                index_details = [
                    {
                        "name": index.get("name"),
                        "columns": index.get("column_names", []),
                        "unique": index.get("unique", False),
                        "type": index.get("type"),
                        "dialect_options": index.get("dialect_options", {})
                    }
                    for index in indexes
                ]

                # Unique constraints
                unique_constraints = ScansRepository.extract_unique_constraints(
                    engine,
                    schema,
                    table_name
                )


                # Extract check constraints
                check_constraints = (
                    ScansRepository.extract_check_constraints(
                        engine,
                        schema,
                        table_name
                    )
                )



                # Store table
                tables[table_key] = {
                    "schema": schema,
                    "name": table_name,
                    "columns": column_details,
                    "primary_key": {
                        "name": primary_key.get("name"),
                        "columns": primary_key.get(
                            "constrained_columns", []
                        )
                    },
                    "foreign_keys": foreign_key_details,
                    "indexes": index_details,
                    "unique_constraints": unique_constraints,
                    "check_constraints": check_constraints,
                    "related_tables": related_tables
                }

        return tables, relationships


    # ---------------------------------------------------------
    # VIEWS
    # ---------------------------------------------------------
    @staticmethod
    def extract_views(engine, inspector, schemas):

        views = {}

        for schema in schemas:

            view_names = inspector.get_view_names(schema=schema)

            # Retrieve native column types once per schema
            native_types = (
                ScansRepository.get_sql_server_column_types(
                    engine,
                    schema
                )
            )

            for view_name in view_names:

                view_key = f"{schema}.{view_name}"

                columns = inspector.get_columns(
                    view_name,
                    schema=schema
                )

                column_details = []

                for column in columns:

                    column_name = column["name"]

                    column_details.append({
                        "name": column_name,
                        "type": native_types.get(
                            view_name, {}
                        ).get(
                            column_name,
                            str(column["type"])
                        ),
                        "nullable": column["nullable"]
                    })


                    definition = inspector.get_view_definition(
                        view_name,
                        schema=schema
                    )

                views[view_key] = {
                    "schema": schema,
                    "name": view_name,
                    "columns": column_details,
                    "definition": definition,
                    "dependencies": []
                }

        return views


    # ---------------------------------------------------------
    # STORED PROCEDURES, FUNCTION AND TRIGGERS
    # ---------------------------------------------------------
    @staticmethod
    def extract_sql_modules(engine, schemas):

        query = text("""
            SELECT
                s.name AS schema_name,
                o.name AS object_name,
                o.type AS object_type,
                o.type_desc AS object_type_description,
                m.definition,
                o.create_date,
                o.modify_date
            FROM sys.objects o
            INNER JOIN sys.schemas s
                ON o.schema_id = s.schema_id
            LEFT JOIN sys.sql_modules m
                ON o.object_id = m.object_id
            WHERE o.type IN (
            'P',
            'FN',
            'IF',
            'TF',
            'TR'
            )
            AND o.is_ms_shipped = 0
            ORDER BY s.name, o.name
        """)

        modules = {
            "stored_procedures": {},
            "functions": {},
            "triggers": {}
        }

        with engine.connect() as connection:
            results = connection.execute(query).mappings().all()

        logger.info("SQL modules returne: %s", len(results))
        logger.info("Schemas supplied: %s", schemas)

        for row in results:

            schema = row["schema_name"]
            
            """
            if schema not in schemas:
                logger.warning("Skipping module because schema is not recognised: %s", schema)
                continue
            """

            key = f"{schema}.{row['object_name']}"

            details = {
                "schema": schema,
                "name": row["object_name"],
                "type": row["object_type_description"],
                "definition": row["definition"],
                "created_at": (
                    row["create_date"].isoformat()
                    if row["create_date"]
                    else None
                    ),
                "modified_at": (
                    row["modify_date"].isoformat()
                    if row["modify_date"]
                    else None),
                "parameters": [],
                "dependencies": []
            }

            object_type = (row["object_type"] or "").strip()

            if object_type == "P":
                modules["stored_procedures"][key] = details

            elif object_type in ("FN", "IF", "TF"):
                modules["functions"][key] = details

            elif object_type == "TR":
                modules["triggers"][key] = details

        logger.info(
            "Extracted SQL modules: procedures=%s, functions=%s, triggers=%s",
            len(modules["stored_procedures"]),
            len(modules["functions"]),
            len(modules["triggers"])
        )

        return modules


    # ---------------------------------------------------------
    # MODULE PARAMETERS
    # ---------------------------------------------------------
    @staticmethod
    def extract_module_parameters(engine, schemas):

        query = text("""
            SELECT
                s.name AS schema_name,
                o.name AS object_name,
                p.name AS parameter_name,
                p.parameter_id,
                TYPE_NAME(p.user_type_id) AS data_type,
                p.max_length,
                p.precision,
                p.scale,
                p.is_output,
                p.has_default_value,
                p.is_readonly
            FROM sys.parameters p
            INNER JOIN sys.objects o
                ON p.object_id = o.object_id
            INNER JOIN sys.schemas s
                ON o.schema_id = s.schema_id
            WHERE o.type IN (
                'P',
                'FN',
                'IF',
                'TF',
                'TR'
            )
            AND o.is_ms_shipped = 0
            AND p.parameter_id > 0
            ORDER BY s.name, o.name, p.parameter_id
        """)

        parameters = {}

        with engine.connect() as connection:
            results = connection.execute(query).mappings().all()

        for row in results:

            schema = row["schema_name"]

            if schema not in schemas:
                continue

            key = f"{schema}.{row['object_name']}"

            parameters.setdefault(key, []).append({
                "name": row["parameter_name"],
                "position": row["parameter_id"],
                "type": row["data_type"],
                "max_length": row["max_length"],
                "precision": row["precision"],
                "scale": row["scale"],
                "output": row["is_output"],
                "has_default_value": row["has_default_value"],
                "readonly": row["is_readonly"]
            })

        return parameters


    # ---------------------------------------------------------
    # OBJECT DEPENDENCIES
    # ---------------------------------------------------------
    @staticmethod
    def extract_dependencies(engine, schemas):

        query = text("""
            SELECT
                OBJECT_SCHEMA_NAME(
                    d.referencing_id
                ) AS referencing_schema,
                OBJECT_NAME(
                    d.referencing_id
                ) AS referencing_object,
                d.referenced_server_name,
                d.referenced_database_name,
                d.referenced_schema_name,
                d.referenced_entity_name,
                d.referenced_class_desc,
                d.is_ambiguous
            FROM sys.sql_expression_dependencies d
            WHERE d.referencing_id IS NOT NULL
            ORDER BY
                referencing_schema,
                referencing_object
        """)

        dependencies = {}

        with engine.connect() as connection:
            results = connection.execute(query).mappings().all()

        for row in results:

            schema = row["referencing_schema"]

            if schema not in schemas:
                continue
            
            key = f"{schema}.{row['referencing_object']}"

            dependencies.setdefault(key,[]).append({
                "server": row["referenced_server_name"],
                "database": row["referenced_database_name"],
                "schema": row["referenced_schema_name"],
                "object": row["referenced_entity_name"],
                "object_type": row["referenced_class_desc"],
                "ambiguous": row["is_ambiguous"]
            })

        return dependencies

    # ---------------------------------------------------------
    # SEQUENCES
    # ---------------------------------------------------------
    @staticmethod
    def extract_sequences(engine, schemas):

        query = text("""
            SELECT
                s.name AS schema_name,
                seq.name,
                TYPE_NAME(seq.user_type_id) AS data_type,
                seq.start_value,
                seq.increment,
                seq.minimum_value,
                seq.maximum_value,
                seq.is_cycling,
                seq.is_cached,
                seq.cache_size,
                seq.current_value
            FROM sys.sequences seq
            INNER JOIN sys.schemas s
                ON seq.schema_id = s.schema_id
            ORDER BY s.name, seq.name
        """)

        sequences = {}

        with engine.connect() as connection:
            results = connection.execute(query).mappings().all()

        for row in results:

            schema = row["schema_name"]

            if schema not in schemas:
                continue

            key = f"{schema}.{row['name']}"

            sequences[key] = {
                "schema": schema,
                "name": row["name"],
                "data_type": row["data_type"],
                "start_value": str(row["start_value"]),
                "increment": str(row["increment"]),
                "minimum_value": str(row["minimum_value"]),
                "maximum_value": str(row["maximum_value"]),
                "cycling": row["is_cycling"],
                "cached": row["is_cached"],
                "cache_size": row["cache_size"],
                "current_value": str(row["current_value"])
            }            

        return sequences


    # ---------------------------------------------------------
    # SYNONYMS
    # ---------------------------------------------------------
    @staticmethod
    def extract_synonyms(engine, schemas):

        query = text("""
            SELECT
                s.name AS schema_name,
                sy.name,
                sy.base_object_name
            FROM sys.synonyms sy
            INNER JOIN sys.schemas s
                ON sy.schema_id = s.schema_id
            ORDER BY s.name, sy.name
        """)

        synonyms = {}

        with engine.connect() as connection:
            results = connection.execute(query).mappings().all()

        for row in results:

            schema = row["schema_name"]

            if schema not in schemas:
                continue

            key = f"{schema}.{row['name']}"

            synonyms[key] = {
                "schema": schema,
                "name": row["name"],
                "base_object": row["base_object_name"]
            }

        return synonyms


    # ---------------------------------------------------------
    # SQL SERVER COLUMN TYPES
    # ---------------------------------------------------------
    @staticmethod
    def get_sql_server_column_types(engine, schema):

        query = text("""
            SELECT
                o.name AS table_name,
                c.name AS column_name,
                s.name AS schema_name,
                TYPE_NAME(c.system_type_id) AS system_data_type,
                ut.name AS user_data_type,
                SCHEMA_NAME(ut.schema_id) AS user_type_schema,
                ut.is_user_defined,
                ut.is_assembly_type,
                c.max_length,
                c.precision,
                c.scale
            FROM sys.columns c
            INNER JOIN sys.objects o
                ON c.object_id = o.object_id
            INNER JOIN sys.tables t
                ON c.object_id = t.object_id
            INNER JOIN sys.schemas s
                ON t.schema_id = s.schema_id
            INNER JOIN sys.types ut
                ON c.user_type_id = ut.user_type_id
            WHERE s.name = :schema_name
                AND o.type IN ('U', 'V')
            ORDER BY t.name, c.column_id
        """)

        with engine.connect() as connection:
            results = connection.execute(
                query,
                { "schema_name": schema}
            ).mappings().all()

        column_types = {}

        for row in results:

                system_type = row["system_data_type"]
                user_type = row["user_data_type"]
                
                data_type = (
                    system_type
                    or user_type
                    or "unknown"
                ).lower()

                max_length = row["max_length"]
                precision = row["precision"]
                scale = row["scale"]

                # CLR / assembly types (hierarchyid, geometry, geography)
                if row["is_assembly_type"]:
                    formatted_type = user_type

                else:

                    # Character and binary types
                    if data_type in ("varchar", "char", "varbinary", "binary"):

                        length = (
                            "max" if max_length == -1 else str(max_length)
                        )

                        formatted_type = f"{data_type}({length})"

                    elif data_type in ("nvarchar", "nchar"):

                        length = (
                            "max" if max_length == -1
                            else str(max_length // 2)
                        )

                        formatted_type = f"{data_type}({length})"

                    # Decimal and numeric types
                    elif data_type in ("decimal", "numeric"):

                        formatted_type = (
                            f"{data_type}({precision},{scale})"
                        )

                    # Date/time types
                    elif data_type in (
                        "datetime2",
                        "datetimeoffset",
                        "time"
                    ):

                        formatted_type = f"{data_type}({scale})"

                    # Other types
                    else:
                        formatted_type = data_type

                    # Preserve user-defined type information
                    if row["is_user_defined"]:
                        formatted_type = (
                            f"{row['user_type_schema']}."
                            f"{user_type} ({formatted_type})"
                        )

                table_name = row["table_name"]
                column_name = row["column_name"]

                column_types.setdefault(table_name, {})[
                    column_name
                ] = formatted_type

        return column_types


    @staticmethod
    def extract_unique_constraints(engine, schema, table_name):

        query = text("""
            SELECT
                kc.name AS constraint_name,
                c.name AS column_name,
                ic.key_ordinal
            FROM sys.key_constraints kc
            INNER JOIN sys.tables t
                ON kc.parent_object_id = t.object_id
            INNER JOIN sys.schemas s
                ON t.schema_id = s.schema_id
            INNER JOIN sys.index_columns ic
                ON kc.parent_object_id = ic.object_id
                AND kc.unique_index_id = ic.index_id
            INNER JOIN sys.columns c
                ON ic.object_id = c.object_id
                AND ic.column_id = c.column_id
            WHERE kc.type = 'UQ'
              AND s.name = :schema_name
              AND t.name = :table_name
              AND ic.key_ordinal > 0
            ORDER BY
                kc.name,
                ic.key_ordinal
        """)

        with engine.connect() as connection:
            rows = connection.execute(
                query,
                {
                    "schema_name": schema,
                    "table_name": table_name
                }
            ).mappings().all()

        constraints = {}

        for row in rows:
            constraint_name = row["constraint_name"]

            if constraint_name not in constraints:
                constraints[constraint_name] = {
                    "name": constraint_name,
                    "columns": []
                }

            constraints[constraint_name]["columns"].append(
                row["column_name"]
            )

        return list(constraints.values())


    
    @staticmethod
    def extract_check_constraints(engine, schema, table_name):

        query = text("""
            SELECT
                cc.name AS name,
                cc.definition AS definition,
                cc.is_disabled AS is_disabled,
                cc.is_not_trusted AS is_not_trusted
            FROM sys.check_constraints cc
            INNER JOIN sys.tables t
                ON cc.parent_object_id = t.object_id
            INNER JOIN sys.schemas s
                ON t.schema_id = s.schema_id
            WHERE s.name = :schema_name
                AND t.name = :table_name
            ORDER BY cc.name
        """)

        with engine.connect() as connection:

            results = connection.execute(
                query,
                {
                    "schema_name": schema,
                    "table_name": table_name
                }
            ).mappings().all()

        return [
            {
                "name": row["name"],
                "definition": row["definition"],
                "is_disabled": row["is_disabled"],
                "is_not_trusted": row["is_not_trusted"]
            }
            for row in results
        ]
