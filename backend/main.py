import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from .db.database import init_db
from .core.config import config
from .db.session import SessionLocal
from .routers import channels, users
from .core.backfill import BackfillWorker
from .core.worker import run_worker_safe

# Manage BackfillWorker during app lifetime
@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = BackfillWorker()
    await worker.get_client() # Connect once
    asyncio.create_task(run_worker_safe(SessionLocal, worker))
    yield
    await worker.disconnect() # Disconnect cleanly


app = FastAPI(title=config.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # allow_origin_regex=r"^http://localhost(:\d+)?$",
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(channels.router)


@app.get("/")
async def root():
    return {"message": "DarkCTI IRKA Project"}
