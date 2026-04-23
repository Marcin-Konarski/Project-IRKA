from typing import Annotated
from sqlmodel import Session
from fastapi import Depends

from .database import engine


def get_session():
    with Session(engine) as session:
        yield session

# Factory for DB sessions outside FastAPI
def SessionLocal():
    return Session(engine)

SessionDep = Annotated[Session, Depends(get_session)]
