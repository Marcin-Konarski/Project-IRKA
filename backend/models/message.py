from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, BigInteger
from sqlalchemy import UniqueConstraint


class Message(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("channel_id", "message_id", name="uq_channel_message"),) # Must be tuple

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    channel_id: int = Field(index=True, sa_type=BigInteger)
    message_id: int = Field(sa_type=BigInteger) # Has to be BigInt due to Telegram's ids
    text: str
    sender_id: int | None = Field(default=None, sa_type=BigInteger)
    date: datetime = Field(index=True)


