import pyodbc


"""
    Establish and test connections to target SQL Server Database 
"""

class ConnectionService:

    @staticmethod
    def connect(
        server
        ,database
        ,username
        ,password
        ,driver="ODBC Driver 18 for SQL Server"
    ):


        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password}"
            "Encypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=15;"
        )

        return pyodbc.connect(connection_string)

