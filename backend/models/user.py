from typing import TYPE_CHECKING
from uuid import UUID, uuid4
from sqlmodel import SQLModel, VARCHAR, Column, Field, Relationship

if TYPE_CHECKING:
    from .observed_channel import ObservedChannel



class User(SQLModel, table=True):
    __tablename__ = "user"  # Explicit name is required for alembic to create this table as user is reserved keywork in postgres and it generates conflicts with this table
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(sa_column=Column("username", VARCHAR, unique=True))
    password: str

    observed_channels: list["ObservedChannel"] = Relationship(back_populates="owner")

