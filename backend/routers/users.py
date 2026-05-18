from typing import Annotated, Any
from fastapi import APIRouter, Depends, Body, HTTPException, status

from ..db.session import SessionDep
from ..db.utility import commit_or_409
from ..core.security import get_password_hash, authenticate_user, get_user_and_session
from ..schemas.user import UserRequest, UserResponse, Token
from ..schemas.telegram import TelegramCodeRequest, TelegramCodeVerify, TelegramCodeResponse
from ..core.telegram_auth import request_telegram_code, verify_telegram_code
from ..core.monitor import MonitorWorker
from ..db.session import SessionLocal
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


# Telegram authentication
@router.post("/telegram/request", response_model=TelegramCodeResponse, status_code=status.HTTP_200_OK)
async def request_telegram_auth(request: Annotated[TelegramCodeRequest, Body()]) -> Any:
    """Request Telegram verification code."""
    try:
        phone_code_hash = await request_telegram_code(request.phone)
        return TelegramCodeResponse(
            phone_code_hash=phone_code_hash,
            message=f"Code sent to {request.phone}. Check your Telegram app."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/telegram/verify", status_code=status.HTTP_200_OK)
async def verify_telegram_auth(verify: Annotated[TelegramCodeVerify, Body()]) -> Any:
    """Verify Telegram code and authenticate."""
    try:
        success = await verify_telegram_code(verify.phone, verify.code, verify.phone_code_hash)
        if success:
            try:
                await MonitorWorker().restart_monitors(SessionLocal)
            except Exception as e:
                print(f"⚠️  Monitor restart after Telegram verify failed: {e}")

            return {
                "success": True,
                "message": "Successfully authenticated with Telegram",
                "phone": verify.phone
            }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
