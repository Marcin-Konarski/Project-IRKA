from uuid import UUID
from typing import Any, Tuple
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlmodel import select

from ..schemas.channel import ChannelRequest
from ..models import User, Message, BackfillJob
from ..db.session import SessionDep
from ..core.security import get_user_and_session
from ..core.backfill_worker import BackfillWorker


router = APIRouter(tags=["core"])


@router.post("/channel/backfill")
async def start_backfill(request: ChannelRequest, session: SessionDep):

    job = BackfillJob(channel_name=request.channel)

    session.add(job)
    session.commit()
    session.refresh(job)

    return {"job_id": job.id, "channel_id": job.channel_id}


@router.get("/jobs/{job_id}")
async def get_job(job_id: UUID, session: SessionDep):

    job = session.get(BackfillJob, job_id)

    if not job:
        raise HTTPException(404, "Job not found")

    return {
        "status": job.status,
        "progress": job.progress_count,
        "last_message_id": job.last_message_id,
        "error": job.error
    }


@router.get("/channel/{channel_id}/messages")
async def get_messages(channel_id: int, session: SessionDep):

    msgs = session.exec(
        select(Message).where(Message.channel_id == channel_id)
    ).all()

    return msgs



