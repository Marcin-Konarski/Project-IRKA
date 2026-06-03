from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import TYPE_CHECKING, Optional
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Column, BigInteger, ForeignKey, Relationship

if TYPE_CHECKING:
    from .user import User
    from .channels import Channel


class ObservedChannel(SQLModel, table=True):
    __tablename__ = "observed_channel"
    __table_args__ = (UniqueConstraint("user_id", "channel_name", name="uq_observed_channel_user_name"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    channel_id: int | None = Field(default=None, sa_column=Column(BigInteger, ForeignKey("channel.id"), nullable=True))
    channel_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    owner: Optional["User"] = Relationship(back_populates="observed_channels")
    channel: Optional["Channel"] = Relationship()
