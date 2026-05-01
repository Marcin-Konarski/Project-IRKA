from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel, Field, Column, BigInteger, Relationship

if TYPE_CHECKING:
    from .backfill import BackfillJob
    from .monitor import MonitorJob
    from .message import Message

class Channel(SQLModel, table=True):
    id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    title: str
    photo: str | None = None
    creator: str | None = None
    link: str | None = None
    channel_name: str = Field(unique=True, index=True)
    message_count: int = 0

    backfill_job: Optional["BackfillJob"] = Relationship(back_populates="channel", cascade_delete=True)
    monitor_job: Optional["MonitorJob"] = Relationship(back_populates="channel", cascade_delete=True)
    messages: list["Message"] = Relationship(back_populates="channel", cascade_delete=True)
