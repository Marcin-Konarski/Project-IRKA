from typing import Any, Tuple
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..schemas.core import ChannelsRequest
from ..db.session import SessionDep
from ..models import User
from ..core.telegram import fetch_telegram_data
from ..core.security import get_user_and_session



router = APIRouter(tags=["core"])


@router.post("/channels")
async def get_channels(request: ChannelsRequest, user_and_session: Tuple[User, SessionDep] = Depends(get_user_and_session)) -> Any:
    """Fetch messages from specified Telegram channels"""
    if not request.channels:
        raise HTTPException(status_code=400, detail="Channels list cannot be empty")

    try:
        data = await fetch_telegram_data(request.channels)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


