
from sqlalchemy import (
    Table,
    Column,
    String,
    Text,
    DateTime,
    MetaData,
    PrimaryKeyConstraint,
    Index,
)
from sqlalchemy.sql import func


webhook_metadata = MetaData()

webhook_events = Table(
    "webhook_events",
    webhook_metadata,
    Column("id", String(255), nullable=False),
    Column("provider", String(100), nullable=False),
    Column("event_type", String(255), nullable=False),
    Column("payload", Text, nullable=False),
    Column("status", String(30), nullable=False, default="pending"),
    Column("received_at", DateTime(timezone=True), server_default=func.now()),
    Column("processed_at", DateTime(timezone=True), nullable=True),
    PrimaryKeyConstraint("provider", "id"),
    Index("ix_webhook_provider_type", "provider", "event_type"),
)
