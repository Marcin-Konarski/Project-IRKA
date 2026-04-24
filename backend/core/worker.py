import asyncio
from uuid import UUID
from sqlmodel import select

from ..models import BackfillJob
from .backfill import BackfillWorker




async def run_worker_safe(session_factory, worker: BackfillWorker):
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


async def worker_loop(session_factory, worker: BackfillWorker):
    """Polls for pending jobs and dispatches them as background tasks."""
    while True:
        with session_factory() as session:

            job: BackfillJob = session.exec(
                select(BackfillJob).where(BackfillJob.status == "pending").limit(1)
            ).first()

            if not job:
                await asyncio.sleep(2)
                continue

            job_id = job.id
            job.status = "running"
            session.commit()

            asyncio.create_task(run_backfill_job_safe(session_factory, worker, job_id)) # Pass only the ID — the task opens its own session
            await asyncio.sleep(0.5) # Brief pause to avoid starting the same job again


async def run_backfill_job_safe(session_factory, worker: BackfillWorker, job_id: UUID):
    """Wraps run_backfill_job and marks the job failed on unexpected errors."""
    _semaphore = asyncio.Semaphore(5)
    async with _semaphore:
        try:
            await worker.run_backfill_job(session_factory, job_id)
        except Exception as e:
            print(f"Job {job_id} failed with unhandled error: {e}")
            with session_factory() as session:
                job: BackfillJob = session.get(BackfillJob, job_id)
                if job:
                    job.status = "failed"
                    job.error = str(e)
                    session.commit()

