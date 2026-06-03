from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from fastapi.responses import StreamingResponse
from sqlmodel import select, Session

from ..schemas.channel import ChannelRequest
from ..db.session import SessionDep, get_session
from ..models import Message, BackfillJob, MonitorJob, Channel, ObservedChannel, User
from ..core.security import get_user_and_session
from ..core.queue import JobQueue
from ..core.subscribers import SubscribersQueue
from ..core.channel_utils import normalize_telegram_channel_reference, build_telegram_message_url_from_channel
from ..core.monitor import MonitorWorker


router = APIRouter(tags=["core"], dependencies=[Depends(get_user_and_session)])


@router.post("/backfill-jobs", status_code=status.HTTP_201_CREATED)
async def start_backfill(
    body: Annotated[ChannelRequest, Body()],
    user_and_session: Annotated[tuple, Depends(get_user_and_session)],
):
    user, session = user_and_session
    channel_name = normalize_telegram_channel_reference(body.channel)
    job = BackfillJob(channel_name=channel_name)

    session.add(job)
    session.commit()
    session.refresh(job)

    existing_channel = session.exec(select(Channel).where(Channel.channel_name == channel_name)).first()
    observed = ObservedChannel(
        user_id=user.id,
        channel_id=existing_channel.id if existing_channel else None,
        channel_name=channel_name,
    )
    session.add(observed)
    session.commit()

    return {"job_id": str(job.id)}


@router.get("/backfill-jobs/{job_id}", status_code=status.HTTP_200_OK)
async def get_job_metadata(job_id: UUID, session: Session = Depends(get_session)):
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
async def get_job_progress(job_id: UUID, session: Session = Depends(get_session)):

    job = session.get(BackfillJob, job_id)

    if not job:
        raise HTTPException(404, "Job not found")

    queue = JobQueue()
    return StreamingResponse(
            queue.generator(str(job_id)),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@router.get("/backfill-jobs", status_code=status.HTTP_200_OK)
async def list_backfill_jobs(user_and_session: Annotated[tuple, Depends(get_user_and_session)]):
    user, session = user_and_session
    observed = session.exec(select(ObservedChannel).where(ObservedChannel.user_id == user.id)).all()
    channel_names = [entry.channel_name for entry in observed]
    jobs = session.exec(select(BackfillJob).where(BackfillJob.channel_name.in_(channel_names))).all() if channel_names else []
    return jobs


@router.get("/channels", response_model=list[Channel], status_code=status.HTTP_200_OK)
async def get_channels(user_and_session: Annotated[tuple, Depends(get_user_and_session)]):
    user, session = user_and_session
    observed = session.exec(
        select(ObservedChannel).where(ObservedChannel.user_id == user.id, ObservedChannel.channel_id != None)
    ).all()
    channel_ids = [entry.channel_id for entry in observed if entry.channel_id is not None]
    channels = session.exec(select(Channel).where(Channel.id.in_(channel_ids))).all() if channel_ids else []
    return channels


@router.get("/channels/{channel_id}/messages", status_code=status.HTTP_200_OK)
async def get_messages(channel_id: Annotated[int, Path()], user_and_session: Annotated[tuple, Depends(get_user_and_session)]):
    user, session = user_and_session

    observed = session.exec(
        select(ObservedChannel).where(
            ObservedChannel.user_id == user.id,
            ObservedChannel.channel_id == channel_id,
        )
    ).first()

    if not observed:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel = session.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    messages = session.exec(
        select(Message).where(Message.channel_id == channel_id)
    ).all()

    return [
        {
            **message.model_dump(),
            "telegram_url": message.telegram_url or build_telegram_message_url_from_channel(message.message_id, channel),
        }
        for message in messages
    ]


@router.get("/channels/{channel_id}/events", status_code=status.HTTP_200_OK)
async def subscribe_to_channel(channel_id: Annotated[int, Path()], user_and_session: Annotated[tuple, Depends(get_user_and_session)]):
    user, session = user_and_session
    channel = session.get(Channel, channel_id)
    observed = session.exec(
        select(ObservedChannel).where(
            ObservedChannel.user_id == user.id,
            ObservedChannel.channel_id == channel_id,
        )
    ).first()
    if not channel or not observed:
        raise HTTPException(404, "Channel not found")

    return StreamingResponse(
        SubscribersQueue().generator(f"monitor:{channel.channel_name}"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(channel_id: Annotated[int, Path()], user_and_session: Annotated[tuple, Depends(get_user_and_session)]):
    user, session = user_and_session

    observed_for_user = session.exec(
        select(ObservedChannel).where(
            ObservedChannel.user_id == user.id,
            ObservedChannel.channel_id == channel_id,
        )
    ).first()

    if not observed_for_user:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel = session.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Stop active monitor task for this channel before DB cleanup.
    await MonitorWorker().stop_monitor(channel.channel_name)

    observed_entries = session.exec(
        select(ObservedChannel).where(
            (ObservedChannel.channel_id == channel_id) | (ObservedChannel.channel_name == channel.channel_name)
        )
    ).all()
    for entry in observed_entries:
        session.delete(entry)

    messages = session.exec(select(Message).where(Message.channel_id == channel_id)).all()
    for message in messages:
        session.delete(message)

    backfill_jobs = session.exec(select(BackfillJob).where(BackfillJob.channel_id == channel_id)).all()
    for job in backfill_jobs:
        session.delete(job)

    monitor_jobs = session.exec(select(MonitorJob).where(MonitorJob.channel_id == channel_id)).all()
    for job in monitor_jobs:
        session.delete(job)

    session.delete(channel)
    session.commit()


@router.delete("/observed-channels/by-channel-name/{channel_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_observed_channel_by_name(channel_name: str, user_and_session: Annotated[tuple, Depends(get_user_and_session)]):
    user, session = user_and_session

    observed = session.exec(
        select(ObservedChannel).where(
            ObservedChannel.user_id == user.id,
            ObservedChannel.channel_name == channel_name,
        )
    ).all()

    for entry in observed:
        session.delete(entry)

    jobs = session.exec(
        select(BackfillJob).where(BackfillJob.channel_name == channel_name)
    ).all()
    for job in jobs:
        session.delete(job)

    session.commit()


@router.get("/profile/stats", status_code=status.HTTP_200_OK)
async def get_profile_stats(user_and_session: Annotated[tuple, Depends(get_user_and_session)]):
    user, session = user_and_session
    observed = session.exec(select(ObservedChannel).where(ObservedChannel.user_id == user.id, ObservedChannel.channel_id != None)).all()
    channel_ids = [entry.channel_id for entry in observed if entry.channel_id is not None]
    channels = session.exec(
        select(Channel).where(Channel.id.in_(channel_ids)).order_by(Channel.message_count.desc(), Channel.channel_name.asc())
    ).all() if channel_ids else []

    channels_sorted_by_messages = [
        {
            "id": channel.id,
            "title": channel.title,
            "channel_name": channel.channel_name,
            "message_count": channel.message_count,
        }
        for channel in channels
    ]

    return {
        "channels_count": len(channels_sorted_by_messages),
        "channels_sorted_by_messages": channels_sorted_by_messages,
    }