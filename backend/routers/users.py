from typing import Annotated, Any
from fastapi import APIRouter, Depends, Body, status

from ..db.session import SessionDep
from ..db.utility import commit_or_409
from ..core.security import get_password_hash, authenticate_user, get_user_and_session
from ..schemas.user import UserRequest, UserResponse, Token
from ..models import User


router = APIRouter(prefix="/auth", tags=["users"])


# Create user
@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup_user(user: Annotated[UserRequest, Body()], session: SessionDep) -> Any:
    hashed_password = get_password_hash(user.password.get_secret_value())
    user_db = User(username=user.username, password=hashed_password)
    session.add(user_db)

    commit_or_409(session=session, error_message="Username already exists.")

    session.refresh(user_db)
    return user_db


# Accepts application/json
@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
def login_user(user: Annotated[UserRequest, Body()], session: SessionDep) -> Any:
    access_token = authenticate_user(session, user.username, user.password.get_secret_value())
    return Token(access_token=access_token, token_type="bearer")


# Get informations about currently logged in user
@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user_info(session_and_user: tuple[User, SessionDep] = Depends(get_user_and_session)) -> Any:
    current_user, session = session_and_user
    return current_user
