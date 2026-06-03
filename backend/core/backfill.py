import random
import asyncio
from pathlib import Path
from uuid import UUID
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.sessions import MemorySession
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import FloodWaitError, TakeoutInitDelayError, UserAlreadyParticipantError
from telethon.tl.types import Message as TgMessage, User, Chat, Channel as TgChannel
from sqlmodel import select

from .config import config
from .channel_utils import resolve_telegram_channel, build_telegram_message_url
from .queue import JobQueue
from ..db.utility import insert_messages
from ..db.session import SessionLocal
from ..models import BackfillJob, Channel as DBChannel, ObservedChannel


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
                    str(Path(__file__).resolve().parent.parent / "session_backfill"),
                    config.api_id,
                    config.api_hash,
                    connection_retries=3,
                    flood_sleep_threshold=60,
                    receive_updates=False,
                )
                await self._client.connect()
                if not await self._client.is_user_authorized():
                    await self._client.disconnect()
                    self._client = None
                    raise EOFError("Telegram authentication not available")
        return self._client

    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def get_channel(self, client: TelegramClient, channel: str) -> TgChannel | Chat:
        if "t.me/" in channel:
            channel = channel.split("t.me/")[1]

        is_invite = channel.startswith("+")
        invite_hash = channel.lstrip("+")

        if is_invite:
            try:
                result = await client(ImportChatInviteRequest(invite_hash))
                return result.chats[0]
            except UserAlreadyParticipantError:
                raise ValueError(
                    "You are already a member of this private channel. "
                    "Private channels where the Telegram account is already a participant "
                    "are not currently supported. Please use a public channel instead."
                )
            except Exception as e:
                raise RuntimeError(f"Could not join private channel '{channel}': {e}")
        else:
            try:
                return await resolve_telegram_channel(client, channel)
            except ValueError:
                raise
            except Exception as e:
                raise RuntimeError(f"Could not resolve '{channel}': {e}")

    async def run_backfill_job_old(self, session_factory, job_id: UUID, batch_size: int = 500):
        from .monitor import MonitorWorker # Local import avoids circular dependency error

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
                        monitor = MonitorWorker()
                        await monitor.add_channel_monitor(SessionLocal, job.channel_name)
                        break

                    rows = []
                    for msg in batch:
                        media_url, media_type = self._build_media_link(msg, entity)
                        rows.append(
                            {
                                "channel_id": entity.id,
                                "message_id": msg.id,
                                "text": msg.text or "",
                                "media_url": media_url,
                                "media_type": media_type,
                                "telegram_url": build_telegram_message_url(msg.id, entity),
                                "sender_id": msg.sender_id,
                                "date": msg.date,
                            }
                        )

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
                        monitor = MonitorWorker()
                        await monitor.add_channel_monitor(SessionLocal, job.channel_name)
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
        existing_channel = session.get(DBChannel, entity.id)
        if not existing_channel:
            channel = DBChannel(
                id=entity.id,
                channel_name=getattr(entity, "username", None) or str(entity.id),
                title=getattr(entity, "title", ""),
                created_at=datetime.now(timezone.utc),
            )
            session.add(channel)
            session.commit()
        else:
            channel = existing_channel

        observed_channels = session.exec(
            select(ObservedChannel).where(ObservedChannel.channel_name == channel.channel_name)
        ).all()
        for observed in observed_channels:
            observed.channel_id = channel.id
            session.add(observed)

        if observed_channels:
            session.commit()

        job.channel_id = entity.id
        session.commit()

    def _complete_job(self, session, job):
        job.status = "done"
        session.commit()

    def _fail_job(self, session, job, error):
        job.status = "failed"
        job.error = str(error)
        session.commit()

    def _build_media_link(self, msg: TgMessage, entity: TgChannel | Chat) -> tuple[str | None, str | None]:
        if not getattr(msg, "media", None):
            return None, None

        media_type = "media"
        if getattr(msg, "photo", None):
            media_type = "photo"
        elif getattr(msg, "video", None):
            media_type = "video"
        elif getattr(msg, "document", None):
            media_type = "document"

        return build_telegram_message_url(msg.id, entity), media_type

    async def _process_messages(self, message_iter, session, job, queue, entity, batch_size, offset_id, total):

        batch = []
        async for msg in message_iter:
            if not isinstance(msg, TgMessage):
                continue

            media_url, media_type = self._build_media_link(msg, entity)
            batch.append({
                "media_url": media_url,
                "media_type": media_type,
                "telegram_url": build_telegram_message_url(msg.id, entity),
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

    async def _flush_batch(self, session, job, queue, batch, offset_id, total, actual_last_id=None):
        insert_messages(session, batch)

        offset_id = actual_last_id if actual_last_id is not None else batch[-1]["message_id"]
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

            takeout_entity = await self.get_channel(takeout_client, job.channel_name)

            async with takeout_client.takeout(finalize=True) as takeout:
                await takeout.get_me()
                await self._process_messages(
                    takeout.iter_messages(takeout_entity, offset_id=offset_id),
                    session, job, queue, takeout_entity, batch_size, offset_id, total,
                )
        finally:
            await takeout_client.disconnect()

    def _merge_group(self, group: list[TgMessage], entity) -> dict:
        group.sort(key=lambda m: m.id)
        first = group[0]

        text = ""
        for msg in group:
            if msg.text:
                text = msg.text
                break

        media_url, media_type = self._build_media_link(first, entity)

        return {
            "channel_id": entity.id,
            "message_id": first.id,
            "text": text,
            "media_url": media_url,
            "media_type": media_type,
            "telegram_url": build_telegram_message_url(first.id, entity),
            "sender_id": first.sender_id,
            "date": first.date,
        }

    async def _run_with_fallback(self, client, entity, session, job, queue, batch_size, offset_id, total):

        while True:
            try:
                batch_msgs = [
                    msg async for msg in client.iter_messages(entity, limit=batch_size, offset_id=offset_id)
                    if isinstance(msg, TgMessage)
                ]

                if not batch_msgs:
                    break

                batch = []
                group_buffer = []
                actual_last_id = offset_id

                for msg in batch_msgs:
                    actual_last_id = msg.id
                    if msg.grouped_id is not None:
                        group_buffer.append(msg)
                    else:
                        if group_buffer:
                            batch.append(self._merge_group(group_buffer, entity))
                            group_buffer = []
                        media_url, media_type = self._build_media_link(msg, entity)
                        batch.append({
                            "media_url": media_url,
                            "media_type": media_type,
                            "telegram_url": build_telegram_message_url(msg.id, entity),
                            "channel_id": entity.id,
                            "message_id": msg.id,
                            "text": msg.text or "",
                            "sender_id": msg.sender_id,
                            "date": msg.date,
                        })

                if group_buffer:
                    batch.append(self._merge_group(group_buffer, entity))

                offset_id, total = await self._flush_batch(session, job, queue, batch, offset_id, total, actual_last_id)

                await asyncio.sleep(0.4 + random.random() * 0.6)

            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 2)

    async def run_backfill_job(self, session_factory, job_id: UUID, batch_size: int = 100):
        from .monitor import MonitorWorker # Local import avoids circular dependency error

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
                await self._run_with_fallback(client, entity, session, job, queue, batch_size, offset_id, total)
                monitor = MonitorWorker()
                await monitor.add_channel_monitor(session_factory, job.channel_name)

            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 2)
                return

            except Exception as e:
                self._fail_job(session, job, e)
                await queue.put({"status": job.status, "total": total})
                return

            self._complete_job(session, job)
            await queue.put({"status": job.status, "total": job.progress_count})