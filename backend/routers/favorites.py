from typing import Annotated
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select

from ..models import FavoriteMessage
from ..core.security import get_user_and_session


class FavoriteCreate(BaseModel):
    channel_id: int
    message_id: int
    channel_name: str = ""
    text: str = ""
    media_url: str | None = None
    media_type: str | None = None
    telegram_url: str | None = None
    date: str | None = None


router = APIRouter(tags=["favorites"], dependencies=[Depends(get_user_and_session)])


@router.post("/favorites", status_code=status.HTTP_201_CREATED)
async def add_favorite(
    body: FavoriteCreate,
    user_and_session: Annotated[tuple, Depends(get_user_and_session)],
):
    user, session = user_and_session

    existing = session.exec(
        select(FavoriteMessage).where(
            FavoriteMessage.user_id == user.id,
            FavoriteMessage.channel_id == body.channel_id,
            FavoriteMessage.message_id == body.message_id,
        )
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Message already favorited")

    parsed_date: datetime | None = None
    if body.date:
        try:
            parsed_date = datetime.fromisoformat(body.date.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            parsed_date = None

    favorite = FavoriteMessage(
        user_id=user.id,
        channel_id=body.channel_id,
        message_id=body.message_id,
        channel_name=body.channel_name,
        text=body.text,
        media_url=body.media_url,
        media_type=body.media_type,
        telegram_url=body.telegram_url,
        date=parsed_date,
    )
    session.add(favorite)
    session.commit()
    session.refresh(favorite)

    return {"id": str(favorite.id)}


@router.delete("/favorites/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    favorite_id: UUID,
    user_and_session: Annotated[tuple, Depends(get_user_and_session)],
):
    user, session = user_and_session

    favorite = session.get(FavoriteMessage, favorite_id)
    if not favorite or favorite.user_id != user.id:
        raise HTTPException(status_code=404, detail="Favorite not found")

    session.delete(favorite)
    session.commit()


@router.get("/favorites", status_code=status.HTTP_200_OK)
async def list_favorites(user_and_session: Annotated[tuple, Depends(get_user_and_session)]):
    user, session = user_and_session

    favorites = session.exec(
        select(FavoriteMessage).where(FavoriteMessage.user_id == user.id).order_by(FavoriteMessage.created_at.desc())
    ).all()

    return [
        {
            "id": str(f.id),
            "channel_id": f.channel_id,
            "message_id": f.message_id,
            "channel_name": f.channel_name,
            "text": f.text,
            "media_url": f.media_url,
            "media_type": f.media_type,
            "telegram_url": f.telegram_url,
            "date": f.date.isoformat() if f.date else None,
            "created_at": f.created_at.isoformat(),
        }
        for f in favorites
    ]
