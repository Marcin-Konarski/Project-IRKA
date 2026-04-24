# from typing import Tuple, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import select

from ..db.session import SessionDep
from ..models import Message, BackfillJob #, User
from ..schemas.channel import ChannelRequest
# from ..core.security import get_user_and_session
from ..core.queue import JobQueue


router = APIRouter(tags=["core"])


@router.post("/channel/backfill")
async def start_backfill(request: ChannelRequest, session: SessionDep):

    job = BackfillJob(channel_name=request.channel)

    session.add(job)
    session.commit()
    session.refresh(job)

    return {"job_id": job.id}


@router.get("/jobs/{job_id}")
async def get_job(job_id: UUID, session: SessionDep, http: bool | None = None):

    job = session.get(BackfillJob, job_id)

    if not job:
        raise HTTPException(404, "Job not found")

    if http:
        return {
            "status": job.status,
            "progress": job.progress_count,
            "last_message_id": job.last_message_id,
            "channel_id": job.channel_id,
            "error": job.error
        }

    queue = JobQueue()
    return StreamingResponse(
            queue.generator(str(job_id)),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@router.get("/channel/{channel_id}/messages")
async def get_messages(channel_id: int, session: SessionDep):

    messages = session.exec(
        select(Message).where(Message.channel_id == channel_id)
    ).all()

    return messages



