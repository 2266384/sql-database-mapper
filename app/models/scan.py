from app.extensions import db
from sqlalchemy import CheckConstraint


class Scan(db.Model):
    __tablename__ = "scans"

    # ENUM for scan states
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_scans_status"
        ),
        db.Index("ix_scans_database_connection_id", "database_connection_id"),
        db.Index("ix_scanes_status", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    database_connection_id = db.Column(db.Integer, db.ForeignKey('database_connection.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="PENDING")
    started_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    object_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    output_location = db.Column(db.String(500), nullable=True)
    error_message = db.Column(db.Text, nullable=True)


    database_connection = db.relationship(
        "DatabaseConnection"
        ,back_populates="scans"
    )