from typing import TYPE_CHECKING, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, BigInteger, ForeignKey, Relationship

if TYPE_CHECKING:
    from .channels import Channel

class BackfillJob(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    channel_id: int | None = Field(default=None, sa_column=Column(BigInteger, ForeignKey("channel.id"), nullable=True))
    channel_name: str # Denormalized for convenience

    status: str = "pending"
    progress_count: int = 0
    last_message_id: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    error: str | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    channel: Optional["Channel"] = Relationship(back_populates="backfill_job")