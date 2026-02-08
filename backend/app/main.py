from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import engine
from app.routers import bookings, chat, users, ws
from app.services.pipeline import shutdown_pipeline_tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await shutdown_pipeline_tasks()
    await engine.dispose()


app = FastAPI(
    title="iConcierge API",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(users.router)
app.include_router(bookings.router)
app.include_router(chat.router)
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
