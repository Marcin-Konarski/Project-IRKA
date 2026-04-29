import json
import asyncio

class JobQueue:

    _instance: "JobQueue | None" = None
    _job_queue: dict[str: asyncio.Queue] = {}

    def __new__(cls) -> "JobQueue":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_queue(self, job_id: str) -> asyncio.Queue:
        if job_id not in self._job_queue:
            self._job_queue[job_id] = asyncio.Queue()
        return self._job_queue[job_id]

    def remove_queue(self, job_id: str) -> None:
        self._job_queue.pop(job_id, None)

    async def generator(self, job_id: str, should_unsubscribe = False):
        queue = self.get_queue(job_id)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            if not should_unsubscribe:
                self.remove_queue(job_id)


