import random
import asyncio
from uuid import UUID
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.sessions import MemorySession
from telethon.errors import FloodWaitError, UsernameNotOccupiedError, UsernameInvalidError, TakeoutInitDelayError
from telethon.tl.types import Message as TgMessage, User, Chat, Channel

from .config import config
from ..db.utility import insert_messages
from ..models import BackfillJob
from .queue import JobQueue


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

    async def run_backfill_job_old(self, session_factory, job_id: UUID, batch_size: int = 500):
        # Each task owns its session for its entire lifetime
        with session_factory() as session:
            job: BackfillJob = session.get(BackfillJob, job_id)
            if not job:
                print(f"Job {job_id} not found, skipping")
                return

            queue = JobQueue().get_queue(str(job_id))

            print(f"Starting job: {job.channel_name}")

            client = await self.get_client()
            entity = await self.get_channel(client, job.channel_name)

            job.channel_id = entity.id
            session.commit()

            offset_id = job.last_message_id or 0
            total = job.progress_count

            await queue.put({"status": job.status, "total": total})

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
                        await queue.put({"status": job.status, "total": total})
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

                    await queue.put({"status": job.status, "total": total})

                    print(f"{job.channel_name}: +{len(batch)} (total={total})")

                    if total >= 10_000:
                        job.status = "done"
                        session.commit()
                        await queue.put({"status": job.status, "total": total})
                        break

                except FloodWaitError as e:
                    print(f"Flood wait: sleeping {e.seconds}s")
                    await asyncio.sleep(e.seconds + 2)
                    continue





    def _load_job(self, session, job_id) -> BackfillJob | None:
        job = session.get(BackfillJob, job_id)
        if not job:
            print(f"Job {job_id} not found")
            return
        return job

    def _init_job(self, session, job, entity):
        job.channel_id = entity.id
        session.commit()

    def _complete_job(self, session, job):
        job.status = "done"
        session.commit()

    def _fail_job(self, session, job, error):
        job.status = "failed"
        job.error = str(error)
        session.commit()

    async def _process_messages(self, message_iter, session, job, queue, entity, batch_size, offset_id, total):

        batch = []
        async for msg in message_iter:
            if not isinstance(msg, TgMessage):
                continue

            batch.append({
                "channel_id": entity.id,
                "message_id": msg.id,
                "text": msg.text or "",
                "sender_id": msg.sender_id,
                "date": msg.date,
            })

            if len(batch) >= batch_size:
                offset_id, total = await self._flush_batch(session, job, queue, batch, offset_id, total)
                await asyncio.sleep(0.3 + random.random() * 0.5)

        if batch:
            offset_id, total = await self._flush_batch(session, job, queue, batch, offset_id, total)

        return offset_id, total

    async def _flush_batch(self, session, job, queue, batch, offset_id, total):
        insert_messages(session, batch)

        offset_id = batch[-1]["message_id"]
        total += len(batch)

        job.last_message_id = offset_id
        job.progress_count = total
        job.updated_at = datetime.now(timezone.utc)

        session.commit()
        await queue.put({"status": job.status, "total": total})

        batch.clear()
        return offset_id, total

    async def _run_with_takeout(self, client, entity, session, job, queue, batch_size, offset_id, total):
        # Build an in-memory session that reuses the already-authorized auth_key
        mem = MemorySession()
        mem.set_dc(client.session.dc_id, client.session.server_address, client.session.port)
        mem.auth_key = client.session.auth_key

        takeout_client = TelegramClient(
            mem,
            config.api_id,
            config.api_hash,
            receive_updates=False,
            connection_retries=3,
            flood_sleep_threshold=60,
        )
        await takeout_client.connect()

        try:
            if not await takeout_client.is_user_authorized():
                raise RuntimeError("Cloned takeout client is not authorized (auth_key copy failed)")

            takeout_entity = await takeout_client.get_entity(job.channel_name)

            async with takeout_client.takeout(finalize=True) as takeout:
                await takeout.get_me()
                await self._process_messages(
                    takeout.iter_messages(takeout_entity, offset_id=offset_id),
                    session, job, queue, takeout_entity, batch_size, offset_id, total,
                )
        finally:
            await takeout_client.disconnect()

    async def _run_with_fallback(self, client, entity, session, job, queue, batch_size, offset_id, total):

        while True:
            try:
                batch_msgs = [
                    msg async for msg in client.iter_messages(entity, limit=batch_size, offset_id=offset_id)
                    if isinstance(msg, TgMessage)
                ]

                if not batch_msgs:
                    break

                batch = [{
                    "channel_id": entity.id,
                    "message_id": msg.id,
                    "text": msg.text or "",
                    "sender_id": msg.sender_id,
                    "date": msg.date,
                } for msg in batch_msgs]

                offset_id, total = await self._flush_batch(session, job, queue, batch, offset_id, total)

                await asyncio.sleep(0.4 + random.random() * 0.6)

            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 2)

    async def run_backfill_job(self, session_factory, job_id: UUID, batch_size: int = 100):

        with session_factory() as session:
            job = self._load_job(session, job_id)
            if not job:
                return

            queue = JobQueue().get_queue(str(job_id))

            client = await self.get_client()
            entity = await self.get_channel(client, job.channel_name)

            self._init_job(session, job, entity)

            total = job.progress_count
            offset_id = job.last_message_id or 0

            await queue.put({"status": job.status, "total": total})

            try:
                await self._run_with_takeout(client, entity, session, job, queue, batch_size, offset_id, total)

            except TakeoutInitDelayError as e:
                await asyncio.sleep(e.seconds + 2)
                await self._run_with_fallback(client, entity, session, job, queue, batch_size, offset_id, total)

            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 2)
                return

            except Exception as e:
                self._fail_job(session, job, e)
                await queue.put({"status": job.status, "total": total})
                return

            self._complete_job(session, job)
            await queue.put({"status": job.status, "total": job.progress_count})