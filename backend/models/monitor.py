from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, BigInteger



class MonitorJob(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    channel_name: str
    channel_id: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True)) # Has to be BigInt due to Telegram's ids

    status: str = "running" # running | done | failed
    error: str | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

