from typing import TYPE_CHECKING
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, BigInteger, Column, ForeignKey, Relationship
from sqlalchemy import UniqueConstraint

if TYPE_CHECKING:
    from .channels import Channel

class Message(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("channel_id", "message_id", name="uq_channel_message"),) # Must be tuple

    id: int = Field(sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    # id: UUID = Field(default_factory=uuid4, primary_key=True)
    # channel_id: int = Field(index=True, sa_type=BigInteger)
    channel_id: int = Field(sa_column=Column(BigInteger, ForeignKey("channel.id"), index=True))
    message_id: int = Field(sa_column=Column(BigInteger))
    text: str = Field(default="")
    sender_id: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    date: datetime = Field(index=True)

    channel: "Channel" = Relationship(back_populates="messages")
