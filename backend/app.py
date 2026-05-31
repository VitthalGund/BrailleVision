import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router, get_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-load ML model pipeline on startup."""
    logger.info("Starting BrailleVision API service...")
    try:
        # Pre-initialize pipeline singleton
        pipe = get_pipeline()
        logger.info("Braille pipeline loaded and ready ✅")
    except Exception as e:
        logger.error(f"Failed to load Braille pipeline on startup: {e}", exc_info=True)
    yield
    logger.info("Shutting down BrailleVision API service...")


app = FastAPI(
    title="Dotly API",
    description=(
        "Real-time physical Braille-to-text recognition API. "
        "Real-time Braille decoding in your pocket."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production security if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes with prefix /api
app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    """Service health endpoint."""
    from backend.api.routes import pipeline
    return {
        "status": "ok",
        "model_loaded": pipeline is not None,
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    # Load env variables from root .env if it exists
    from dotenv import load_dotenv
    load_dotenv()
    
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Running FastAPI on port {port}...")
    uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=True)
