import asyncio
from telethon import TelegramClient, events
from telethon.errors import UsernameNotOccupiedError, UsernameInvalidError
from telethon.tl.types import Message as TgMessage, Chat, Channel
from sqlmodel import select

from .config import config
from .queue import JobQueue
from ..models import MonitorJob
from ..db.utility import insert_messages


class MonitorWorker:
    _instance: "MonitorWorker | None" = None
    _active_monitors: dict[str, asyncio.Task] = {}
    _client: TelegramClient | None = None
    _client_lock: asyncio.Lock | None = None

    def __new__(cls) -> "MonitorWorker":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client_lock = asyncio.Lock()
            cls._instance._active_monitors = {}
        return cls._instance

    async def get_client(self) -> TelegramClient:
        async with self._client_lock:
            if self._client is None or not self._client.is_connected():
                self._client = TelegramClient(
                    "session_monitor",
                    config.api_id,
                    config.api_hash,
                    connection_retries=3,
                    flood_sleep_threshold=60,
                    receive_updates=True,
                )
                await self._client.start(phone=config.phone)
        return self._client

    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def get_channel(self, client: TelegramClient, channel: str) -> Chat | Channel:
        try:
            return await client.get_entity(channel)
        except (UsernameNotOccupiedError, UsernameInvalidError) as e:
            raise ValueError(f"Channel '{channel}' does not exist or is invalid: {e}")
        except Exception as e:
            raise RuntimeError(f"Could not resolve entity '{channel}': {e}")

    def start_monitor(self, session_factory, channel_name: str, channel: Channel) -> bool:
        """Returns False if already running"""
        if channel_name in self._active_monitors:
            if not self._active_monitors[channel_name].done():
                return False

        task = asyncio.create_task(self.run_monitor_job(session_factory, channel_name, channel), name=f"monitor:{channel_name}")
        self._active_monitors[channel_name] = task
        return True

    async def stop_monitor(self, channel_name: str) -> bool:
        task = self._active_monitors.pop(channel_name, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return True
        return False

    async def restart_monitors(self, session_factory):
        with session_factory() as session:
            for job in self.get_channels(session):
                client = await self.get_client()
                channel = await self.get_channel(client, job.channel_name)
                self.start_monitor(session_factory, job.channel_name, channel)

    def list_monitors(self) -> list[str]:
        return [name for name, task in self._active_monitors.items() if not task.done()]

    async def run_monitor_job(self, session_factory, channel_name: str, channel: Channel) -> None:
        client = await self.get_client()
        queue = JobQueue().get_queue(f"monitor:{channel_name}")

        @client.on(events.NewMessage(chats=channel.id)) # I want to pass here a list of CHANNELS to listen, not usernames!!
        async def handler(event):

            print('\n', "="*20, event, "="*20, "\n")
            message: TgMessage = event.message
            row = row = {
                "channel_id": event.chat_id,
                "message_id": message.id,
                "text": message.text or "",
                "sender_id": message.sender_id,
                "date": message.date,
            }
            with session_factory() as session:
                insert_messages(session, [row])
                session.commit()

            await queue.put({"channel": channel_name, "new_message": message.text})

        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            pass
        finally:
            client.remove_event_handler(handler)
            JobQueue().remove_queue(f"monitor:{channel_name}")
            print(f"[monitor:{channel_name}] stopped")

    async def add_channel_monitor(self, session_factory, channel_name: str) -> MonitorJob:
        if channel_name in self._active_monitors:
            if not self._active_monitors[channel_name].done():
                return # In case where monitor for specific channel already exists do not create second one

        client = await self.get_client()
        channel = await self.get_channel(client, channel_name)

        with session_factory() as session:
            existing: MonitorJob = session.exec(
                select(MonitorJob).where(MonitorJob.channel_name == channel_name)
            ).first()

            if not existing:
                monitor_job = MonitorJob(channel_name=channel_name, channel_id=channel.id, status="running")
                session.add(monitor_job)
                session.commit()
                session.refresh(monitor_job)
            else:
                existing.status = "running"
                session.commit()

        self.start_monitor(session_factory, channel_name, channel)

    def get_channels(self, session) -> list[MonitorJob]:
        return session.exec(select(MonitorJob).where(MonitorJob.status == "running")).all()



