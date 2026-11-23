from app.extensions import db
from sqlalchemy import CheckConstraint, UniqueConstraint


class DatabaseConnection(db.Model):
    __tablename__ = "database_connection"

    __table_args__ = (
        CheckConstraint(
            "authentication_type IN ('SQL', 'WINDOWS')",
            name="ck_database_connections_authentication_type"
        ),
        UniqueConstraint(
            "connection_name",
            name="uq_database_connections_connection_name"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    connection_name = db.Column(db.String(200), nullable=False)
    server = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False, default=1433, server_default="1433")
    database = db.Column(db.String(255), nullable=False)
    authentication_type = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


    scans = db.relationship(
        "Scan",
        back_populates="database_connection",
        lazy="select"
    )