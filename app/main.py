import asyncio
import contextlib
import logging

from fastapi import FastAPI

from app.config import settings
from app.database import init_db
from app.poller import poll_for_issues

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _run_poll_loop() -> None:
    while True:
        try:
            await poll_for_issues()
        except Exception:
            logger.exception("poll_for_issues iteration failed")
        await asyncio.sleep(settings.poll_interval_seconds)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    poll_task = asyncio.create_task(_run_poll_loop())
    yield
    poll_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await poll_task


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
