"""Main application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.auth_routes import router as auth_router
from src.api.routes import router
from src.api.sentiment_routes import router as sentiment_router
from src.api.user_routes import router as user_router
from src.database.db import init_db
from src.services.scheduler_service import SchedulerService
from src.utils.config import config
from src.utils.event_store import EventStore

# Initialize database
init_db()

_scheduler: SchedulerService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    global _scheduler

    # Startup
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        raise

    _scheduler = SchedulerService(event_store=EventStore())
    _scheduler.schedule_deliveries(
        config.scheduler.morning_time,
        config.scheduler.evening_time,
    )

    yield

    # Shutdown
    if _scheduler:
        _scheduler.stop()


# Create FastAPI app
app = FastAPI(
    title="Daily Market Tips",
    description="Expert-analyzed market insights delivered via email",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware — must use specific origins when allow_credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(auth_router, tags=["authentication"])
app.include_router(user_router, tags=["user"])
app.include_router(router, prefix="/api", tags=["tips"])
app.include_router(sentiment_router, tags=["sentiment"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Static files mount must come last — the "/" mount intercepts all unmatched paths,
# so any routes defined after it would never be reached.
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=config.agent.port)
