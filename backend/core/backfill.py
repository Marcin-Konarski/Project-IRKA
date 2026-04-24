import asyncio
from uuid import UUID
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.errors import FloodWaitError, UsernameNotOccupiedError, UsernameInvalidError
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

    async def run_backfill_job(self, session_factory, job_id: UUID, batch_size: int = 100):
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

            queue.put({"status": job.status, "total": total})

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
                        queue.put({"status": job.status, "total": total})
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

                    queue.put({"status": job.status, "total": total})

                    print(f"{job.channel_name}: +{len(batch)} (total={total})")

                    if total >= 10_000:
                        job.status = "done"
                        session.commit()
                        queue.put({"status": job.status, "total": total})
                        break

                except FloodWaitError as e:
                    print(f"Flood wait: sleeping {e.seconds}s")
                    await asyncio.sleep(e.seconds + 2)
                    continue
