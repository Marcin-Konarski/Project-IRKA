from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, BigInteger


class BackfillJob(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    channel_name: str
    channel_id: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True)) # Has to be BigInt due to Telegram's ids

    status: str = "pending" # pending | running | done | failed

    progress_count: int = 0
    last_message_id: int = Field(default=0, sa_column=Column(BigInteger, nullable=False)) # Has to be BigInt due to Telegram's ids

    error: str | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

