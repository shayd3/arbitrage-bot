import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.api.websocket import websocket_endpoint
from backend.config import settings
from backend.db import close_db, get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Kalshi environment: {'DEMO' if settings.kalshi_use_demo else 'PRODUCTION'}")
    await get_db()  # Initialize DB
    from backend.scanner.engine import sync_balance

    await sync_balance()
    from backend.scanner.engine import scanner

    await scanner.start()
    yield
    await scanner.stop()
    await close_db()
    logger.info("Shutting down")


app = FastAPI(title="Arbitrage Bot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
