import asyncio
from datetime import datetime, timezone
from sqlmodel import select, Session
from telethon import TelegramClient
from telethon.errors import FloodWaitError, UsernameNotOccupiedError, UsernameInvalidError
from telethon.tl.types import Message as TgMessage, User, Chat, Channel

from .config import config
from ..db.utility import insert_messages
from ..models import BackfillJob



async def worker_loop(session_factory, worker):
    """Polls for pending jobs and dispatches them as background tasks."""
    while True:
        with session_factory() as session:

            job = session.exec(
                select(BackfillJob).where(BackfillJob.status == "pending").limit(1)
            ).first()

            if not job:
                await asyncio.sleep(2)
                continue

            job_id = job.id
            job.status = "running"
            session.commit()

            # Pass only the ID — the task opens its own session
            asyncio.create_task(run_backfill_job_safe(session_factory, worker, job_id))
            await asyncio.sleep(0.5) # Brief pause to avoid starting the same job again


async def run_backfill_job_safe(session_factory, worker, job_id):
    """Wraps run_backfill_job and marks the job failed on unexpected errors."""
    try:
        await worker.run_backfill_job(session_factory, job_id)
    except Exception as e:
        print(f"Job {job_id} failed with unhandled error: {e}")
        with session_factory() as session:
            job = session.get(BackfillJob, job_id)
            if job:
                job.status = "failed"
                job.error = str(e)
                session.commit()


async def run_worker_safe(session_factory, worker):
    """Keeps the worker loop running even if it crashes."""
    # Reset any jobs that were left 'running' from a previous crash
    with session_factory() as session:
        stale = session.exec(
            select(BackfillJob).where(BackfillJob.status == "running")
        ).all()
        for job in stale:
            job.status = "pending"
        if stale:
            session.commit()
            print(f"Reset {len(stale)} stale running job(s) to pending")

    while True:
        try:
            await worker_loop(session_factory, worker)
        except Exception as e:
            print(f"Worker loop crashed: {e}")
            await asyncio.sleep(2)


class BackfillWorker:
    _instance: "BackfillWorker | None" = None
    _client: TelegramClient | None = None
    _client_lock: asyncio.Lock | None = None

    def __new__(cls) -> "BackfillWorker":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client_lock = asyncio.Lock()
        return cls._instance

    async def get_client(self) -> TelegramClient:
        async with self._client_lock:
            if self._client is None or not self._client.is_connected():
                self._client = TelegramClient(
                    "session_name",
                    config.api_id,
                    config.api_hash,
                    connection_retries=3,
                    flood_sleep_threshold=60,
                    receive_updates=False,
                )
                await self._client.start(phone=config.phone)
        return self._client

    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def get_channel(self, client: TelegramClient, channel: str) -> User | Chat | Channel:
        try:
            return await client.get_entity(channel)
        except (UsernameNotOccupiedError, UsernameInvalidError) as e:
            raise ValueError(f"Channel '{channel}' does not exist or is invalid: {e}")
        except Exception as e:
            raise RuntimeError(f"Could not resolve entity '{channel}': {e}")

    async def run_backfill_job(self, session_factory, job_id, batch_size: int = 100):
        # Each task owns its session for its entire lifetime
        with session_factory() as session:
            job = session.get(BackfillJob, job_id)
            if not job:
                print(f"Job {job_id} not found, skipping")
                return

            print(f"Starting job: {job.channel_name}")

            client = await self.get_client()
            entity = await self.get_channel(client, job.channel_name)

            job.channel_id = entity.id
            session.commit()

            offset_id = job.last_message_id or 0
            total = job.progress_count

            while True:
                try:
                    batch = [
                        msg
                        async for msg in client.iter_messages(
                            entity, limit=batch_size, offset_id=offset_id
                        )
                        if isinstance(msg, TgMessage)
                    ]

                    print(f"Fetched {len(batch)} messages")

                    if not batch:
                        job.status = "done"
                        session.commit()
                        break

                    rows = [
                        {
                            "channel_id": entity.id,
                            "message_id": msg.id,
                            "text": msg.text or "",
                            "sender_id": msg.sender_id,
                            "date": msg.date,
                        }
                        for msg in batch
                    ]

                    insert_messages(session, rows)

                    offset_id = batch[-1].id
                    total += len(batch)

                    job.last_message_id = offset_id
                    job.progress_count = total
                    job.updated_at = datetime.now(timezone.utc)
                    session.commit()

                    print(f"{job.channel_name}: +{len(batch)} (total={total})")

                    if total >= 10_000:
                        job.status = "done"
                        session.commit()
                        break

                except FloodWaitError as e:
                    print(f"Flood wait: sleeping {e.seconds}s")
                    await asyncio.sleep(e.seconds + 2)
                    continue
