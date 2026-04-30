import json
import asyncio


class SubscribersQueue:
    _instance: "SubscribersQueue | None" = None
    _subscribers: dict[str, list[asyncio.Queue]] = {}

    def __new__(cls) -> "SubscribersQueue":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers = {}
        return cls._instance

    def subscribe(self, channel_key: str) -> asyncio.Queue:
        q = asyncio.Queue()
        self._subscribers.setdefault(channel_key, []).append(q)
        return q

    def unsubscribe(self, channel_key: str, q: asyncio.Queue) -> None:
        subs = self._subscribers.get(channel_key, [])
        if q in subs:
            subs.remove(q)
        if not subs:
            self._subscribers.pop(channel_key, None)

    async def publish(self, channel_key: str, event: dict) -> None:
        queue = self._subscribers.get(channel_key, [])
        for q in queue:
            await q.put(event)

    async def generator(self, channel_key: str):
        q = self.subscribe(channel_key)
        try:
            while True:
                event = await q.get() # Blocks until a message arrives
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            self.unsubscribe(channel_key, q) # Runs when client disconnects

