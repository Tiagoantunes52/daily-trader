"""Main application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router
from src.database.db import init_db
from src.utils.config import config

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="Daily Market Tips",
    description="Expert-analyzed market insights delivered via email",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api", tags=["tips"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
