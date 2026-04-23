from fastapi import HTTPException
import asyncio
from telethon import TelegramClient
from telethon.errors import FloodWaitError, UsernameNotOccupiedError, UsernameInvalidError
from telethon.tl.types import Message
from .config import config


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
                self._client = TelegramClient('session_name', config.api_id, config.api_hash, connection_retries=3, flood_sleep_threshold=60, receive_updates=False)
                await self._client.start(phone=config.phone)
        return self._client


    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()
            self._client = None


    async def fetch_channel(self, channel: str, limit: int | None = None, min_id: int = 0, max_id: int = 0, max_retries: int = 3) -> list[Message]:
        client = await self.get_client()
        messages: list[Message] = []
        retries = 0 # To handle FloodWaitError

        try:
            entity = await client.get_entity(channel)
        except (UsernameNotOccupiedError, UsernameInvalidError) as e:
            raise ValueError(f"Channel '{channel}' does not exist or is invalid: {e}")
        except Exception as e:
            raise RuntimeError(f"Could not resolve entity '{channel}': {e}")


        while retries <= max_retries:
            try:
                messages = [
                    msg async for msg in client.iter_messages(
                        entity,
                        limit=limit,
                        min_id=min_id,
                        max_id=max_id or 0,
                        reverse=False,
                        filter=None,
                    )
                    if isinstance(msg, Message) # Skip MessageService events etc.
                ]
                print(f"✓ {channel}: {len(messages)} messages")
                return messages

            except FloodWaitError as e:
                wait = e.seconds + 5 # Increase time between polls
                print(f"Flood wait {wait}s on {channel}")
                await asyncio.sleep(wait)
                retries += 1

            except Exception as e:
                raise RuntimeError(f"Unexpected error fetching '{channel}': {e}")

        raise RuntimeError(f"Exceeded max retries for '{channel}' due to FloodWaitError")


    async def fetch_channels(self, channels: list[str], concurrency: int = 5) -> dict[str, list[Message]]:
        semaphore = asyncio.Semaphore(concurrency) # Semaphore to avoid rate limit from Telegram

        async def guarded(channel: str) -> tuple[str, list[Message]]:
            async with semaphore:
                return channel, await self.fetch_channel(channel)

        results = await asyncio.gather(*[guarded(ch) for ch in channels], return_exceptions=True)

        output: dict[str, list[Message]] = {}
        errors: list[str] = []

        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            else:
                ch, msgs = result
                output[ch] = msgs

        if errors and not output:
            raise HTTPException(status_code=500, detail={"errors": errors})  # All channels failed — hard error
        if errors:
            print(f"Partial failure: {errors}")  # Some failed — log and return what we got

        return output


