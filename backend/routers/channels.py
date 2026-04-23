import json
from typing import Any, Tuple
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from ..schemas.channels import ChannelsRequest
from ..db.session import SessionDep
from ..models import User
from ..core.backfill_worker import BackfillWorker
from ..core.security import get_user_and_session



router = APIRouter(tags=["core"])


@router.post("/channels")
async def get_channels(request: ChannelsRequest, user_and_session: Tuple[User, SessionDep] = Depends(get_user_and_session)) -> Any:
    """Fetch all messages from specified Telegram channels — returns when fully complete"""
    if not request.channels:
        raise HTTPException(status_code=400, detail="Channels list cannot be empty")

    try:
        worker = BackfillWorker()
        data = await worker.fetch_channels(request.channels)
        return JSONResponse(content=data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

