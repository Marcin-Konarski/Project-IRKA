from typing import TYPE_CHECKING, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, BigInteger, Relationship

if TYPE_CHECKING:
    from .channels import Channel

class MonitorJob(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    channel_id: int = Field(foreign_key="channel.id", sa_type=BigInteger)
    channel_name: str # Denormalized for convenience

    status: str = "running"
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    channel: Optional["Channel"] = Relationship(back_populates="monitor_job")