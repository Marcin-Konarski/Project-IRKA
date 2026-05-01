from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Path, Body
from fastapi.responses import StreamingResponse
from sqlmodel import select

from ..schemas.channel import ChannelRequest
from ..db.session import SessionDep
from ..models import Message, BackfillJob, Channel
# from ..core.security import get_user_and_session
from ..core.queue import JobQueue
from ..core.subscribers import SubscribersQueue


router = APIRouter(tags=["core"])


@router.post("/backfill-jobs", status_code=status.HTTP_201_CREATED)
async def start_backfill(body: Annotated[ChannelRequest, Body()], session: SessionDep):

    job = BackfillJob(channel_name=body.channel)

    session.add(job)
    session.commit()
    session.refresh(job)

    return {"job_id": str(job.id)}


@router.get("/backfill-jobs/{job_id}", status_code=status.HTTP_200_OK)
async def get_job_metadata(job_id: Annotated[UUID, Path()], session: SessionDep):
    job = session.get(BackfillJob, job_id)

    if not job:
        raise HTTPException(404, "Job not found")

    return {
        "status": job.status,
        "progress": job.progress_count,
        "last_message_id": job.last_message_id,
        "channel_id": job.channel_id,
        "error": job.error
    }


@router.get("/backfill-jobs/{job_id}/events", status_code=status.HTTP_200_OK)
async def get_job_progress(job_id: Annotated[UUID, Path()], session: SessionDep):

    job = session.get(BackfillJob, job_id)

    if not job:
        raise HTTPException(404, "Job not found")

    queue = JobQueue()
    return StreamingResponse(
            queue.generator(str(job_id)),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@router.get("/channels/{channel_id}/messages", status_code=status.HTTP_200_OK)
async def get_messages(channel_id: Annotated[int, Path()], session: SessionDep):

    messages = session.exec(
        select(Message).where(Message.channel_id == channel_id)
    ).all()

    return messages


@router.get("/channels/{channel_id}/events", status_code=status.HTTP_200_OK)
async def subscribe_to_channel(channel_id: Annotated[int, Path()], session: SessionDep):
    channel = session.get(Channel, channel_id)
    if not channel:
        raise HTTPException(404, "Channel not found")

    return StreamingResponse(
        SubscribersQueue().generator(f"monitor:{channel.channel_name}"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )