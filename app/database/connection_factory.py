import os

from sqlalchemy.engine import URL


"""
    Factory class to centralise logic for creating database connection string
"""
class ConnectionFactory:
    @staticmethod
    def build_sql_server_url(
        server,
    database,
    authentication_type="SQL",
    username=None,
    password=None,
    port=1433,
    driver=None,
    encrypt=None,
    trust_server_certificate=None
    ):

        connection_parameters = {
            "driver": driver or os.getenv(
                "DB_DRIVER",
                "ODBC Driver 17 for SQL Server"
            ),
            "Encrypt": encrypt or os.getenv("DB_ENCRYPT", "no"),
            "TrustServerCertificate": (
                trust_server_certificate
                or os.getenv("DB_TRUST_SERVER_CERTIFICATE", "no")
            )
        }

        if authentication_type == "WINDOWS":
            connection_parameters["Trusted_Connection"] = "yes"

        elif authentication_type == "SQL":

            if not username or not password:
                raise ValueError(
                    "Username and pasword are required for SQL authentications"
                )

        return URL.create(
            "mssql+pyodbc",
            username=username,
            password=password,
            host=server,
            port=int(port) if port else None,
            database=database,
            query=connection_parameters
        )