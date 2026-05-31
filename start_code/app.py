"""
BrailleVision — FastAPI Backend

Run: uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import cv2
import numpy as np
import httpx
import anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Global pipeline instance ──────────────────────────────────────────────────
pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model on startup."""
    global pipeline
    from backend.inference.pipeline import BraillePipeline

    logger.info("Loading BrailleVision inference pipeline...")
    pipeline = BraillePipeline()
    logger.info("Pipeline ready ✅")
    yield
    logger.info("Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="BrailleVision API",
    description=(
        "Real-time physical Braille-to-text recognition API. "
        "Upload a camera image → get decoded English text + optional multilingual translation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────
class TranslateRequest(BaseModel):
    text: str
    target_lang: str = "en"


class ChatRequest(BaseModel):
    message: str
    context: str = ""
    history: list[dict] = []


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Check if the API and model are ready."""
    return {
        "status": "ok",
        "model_loaded": pipeline is not None,
        "version": "1.0.0",
    }


# ── Braille Inference ─────────────────────────────────────────────────────────
@app.post("/api/infer")
async def infer_braille(file: UploadFile = File(...)):
    """
    Detect and decode physical Braille from an uploaded image.

    - **file**: JPEG/PNG image from camera

    Returns:
    - `text`: decoded English text
    - `confidence`: overall confidence score (0-1)
    - `cells`: list of detected Braille cells with bounding boxes
    - `processing_time_ms`: how long inference took
    """
    if pipeline is None:
        raise HTTPException(503, "Inference pipeline not loaded")

    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg", "image/webp"):
        raise HTTPException(
            400, f"Invalid file type: {file.content_type}. Use JPEG or PNG."
        )

    contents = await file.read()

    # Decode image
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(
            400, "Could not decode image. Ensure it's a valid JPEG/PNG."
        )

    # Run inference
    try:
        result = pipeline.run(img)
    except Exception as e:
        logger.error(f"Inference error: {e}", exc_info=True)
        raise HTTPException(500, f"Inference failed: {str(e)}")

    return JSONResponse(content=result)


# ── Translation ───────────────────────────────────────────────────────────────
@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    """
    Translate recognized Braille text to any language.

    Primary: LibreTranslate (free, open-source)
    Fallback: Claude API
    """
    if req.target_lang == "en" or not req.text.strip():
        return {"translated": req.text, "source_lang": "en"}

    # Try LibreTranslate first (self-hosted or libre.translate.de)
    libre_url = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.de/translate")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                libre_url,
                json={
                    "q": req.text,
                    "source": "en",
                    "target": req.target_lang,
                    "format": "text",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "translated": data.get("translatedText", req.text),
                    "source_lang": "en",
                }
    except Exception as e:
        logger.warning(f"LibreTranslate failed: {e}. Falling back to Claude.")

    # Fallback: Claude API
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Translate this text to {req.target_lang}. "
                            f"Reply with ONLY the translated text, nothing else:\n\n{req.text}"
                        ),
                    }
                ],
            )
            translated = msg.content[0].text.strip()
            return {"translated": translated, "source_lang": "en"}
        except Exception as e:
            logger.error(f"Claude translation failed: {e}")

    # Last resort: return original
    return {
        "translated": req.text,
        "source_lang": "en",
        "warning": "Translation unavailable",
    }


# ── AI Assistant ──────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    AI assistant powered by Claude for Braille help and context.

    Helps users understand Braille symbols, guides on scanning technique,
    provides context for recognized text, and answers accessibility questions.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "reply": (
                "AI assistant is not configured. "
                "Set ANTHROPIC_API_KEY environment variable to enable it."
            )
        }

    system_prompt = """You are BrailleVision Assistant — a helpful, concise AI assistant built into a Braille reading app.

Your role:
- Help users understand Braille symbols and the Braille system
- Guide users on how to best scan physical Braille with their camera (lighting, angle, distance)
- Provide context for text that has been recognized from Braille
- Answer accessibility-related questions
- Support users in any language they prefer

Keep responses concise (2-4 sentences) and practical. If the user asks in a language other than English, respond in that language.

Current app context: {context}""".format(
        context=req.context or "No recent scan"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)

        # Build message history
        messages = []
        for turn in req.history[-10:]:  # last 10 turns
            if turn.get("role") in ("user", "assistant") and turn.get("content"):
                messages.append({"role": turn["role"], "content": turn["content"]})

        messages.append({"role": "user", "content": req.message})

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=system_prompt,
            messages=messages,
        )

        return {"reply": response.content[0].text.strip()}

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return {"reply": "I'm having trouble connecting right now. Please try again."}


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
