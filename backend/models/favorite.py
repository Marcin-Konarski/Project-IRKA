from typing import TYPE_CHECKING, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Column, BigInteger, ForeignKey, Relationship

if TYPE_CHECKING:
    from .user import User

class FavoriteMessage(SQLModel, table=True):
    __tablename__ = "favorite_message"
    __table_args__ = (UniqueConstraint("user_id", "channel_id", "message_id", name="uq_favorite_user_channel_message"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    channel_id: int = Field(sa_column=Column(BigInteger))
    message_id: int = Field(sa_column=Column(BigInteger))
    channel_name: str = Field(default="")
    text: str = Field(default="")
    media_url: str | None = None
    media_type: str | None = None
    telegram_url: str | None = None
    date: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    owner: Optional["User"] = Relationship()
