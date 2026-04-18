# from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from .db.database import init_db
from .core.config import config
from .routers import users, core


# Init database before the app runs. Only use if Alembic migrations are not used
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     init_db()
#     yield

# app = FastAPI(title=config.app_name, lifespan=lifespan)
app = FastAPI(title=config.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in config.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(core.router)


@app.get("/")
async def root():
    return {"message": "DarkCTI IRKA Project"}
