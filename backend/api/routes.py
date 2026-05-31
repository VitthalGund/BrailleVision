import logging
import os
import time
import cv2
import numpy as np
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from backend.models.schemas import (
    InferenceResponse,
    TranslateRequest,
    TranslateResponse,
    ChatRequest,
    ChatResponse,
    BrailleCell,
    BrailleDot
)
from backend.inference.pipeline import BraillePipeline
from backend.utils.ai_assistant import AIAssistant

logger = logging.getLogger(__name__)

router = APIRouter()

# Global pipeline instance initialized on backend/api/routes.py loading or startup
pipeline = None

def get_pipeline() -> BraillePipeline:
    """Retrieve or initialize the singleton inference pipeline."""
    global pipeline
    if pipeline is None:
        logger.info("Initializing BrailleVision inference pipeline in routes...")
        pipeline = BraillePipeline()
    return pipeline


@router.post("/infer", response_model=InferenceResponse)
async def infer_braille(file: UploadFile = File(...)):
    """
    Detect and decode physical Braille from an uploaded image.
    
    Accepts: JPEG/PNG image from camera
    Returns: Decoded English text + cell positions & confidence metadata
    """
    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg", "image/webp"):
        raise HTTPException(
            400, f"Invalid file type: {file.content_type}. Use JPEG, WebP, or PNG."
        )

    contents = await file.read()

    # Decode image
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(
            400, "Could not decode image. Ensure it's a valid image file."
        )

    # Run inference
    try:
        pipe = get_pipeline()
        result = pipe.run(img)
    except Exception as e:
        logger.error(f"Inference error: {e}", exc_info=True)
        raise HTTPException(500, f"Inference failed: {str(e)}")

    # Return structured response matching Pydantic response_model
    return InferenceResponse(
        text=result["text"],
        confidence=result["confidence"],
        cells=[
            BrailleCell(
                dots=c["dots"],
                char=c["char"],
                bbox=c["bbox"],
                confidence=c["confidence"]
            ) for c in result["cells"]
        ],
        dots=[
            BrailleDot(
                x=d["x"],
                y=d["y"],
                confidence=d["confidence"]
            ) for d in result["dots"]
        ],
        processing_time_ms=result["processing_time_ms"],
        error=result.get("error")
    )


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(req: TranslateRequest):
    """
    Translate recognized Braille text to any language.
    
    Primary: LibreTranslate (free, open-source)
    Fallback: OpenAI / Claude AI (depending on credentials)
    """
    if req.target_lang == "en" or not req.text.strip():
        return TranslateResponse(translated=req.text, source_lang="en")

    # Try LibreTranslate first (self-hosted or libre.translate.de)
    libre_url = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.de/translate")
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
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
                return TranslateResponse(
                    translated=data.get("translatedText", req.text),
                    source_lang="en"
                )
    except Exception as e:
        logger.warning(f"LibreTranslate failed: {e}. Falling back to AI translator.")

    # Fallback to configured LLM (OpenAI, Anthropic, etc.)
    ai_provider = os.getenv("AI_PROVIDER", "mock").lower()
    
    # Check if we can use an actual provider for translation
    api_key_anthropic = os.getenv("ANTHROPIC_API_KEY")
    api_key_openai = os.getenv("OPENAI_API_KEY")
    
    if api_key_anthropic or ai_provider == "anthropic":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key_anthropic)
            msg = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": f"Translate this English text to {req.target_lang}. Reply with ONLY the exact translated text, nothing else:\n\n{req.text}"
                    }
                ],
            )
            translated = msg.content[0].text.strip()
            return TranslateResponse(translated=translated, source_lang="en")
        except Exception as e:
            logger.error(f"Claude translation failed: {e}")

    elif api_key_openai or ai_provider == "openai":
        api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    f"{api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key_openai}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "user", "content": f"Translate this English text to {req.target_lang}. Reply with ONLY the exact translated text, nothing else:\n\n{req.text}"}
                        ],
                        "max_tokens": 200
                    }
                )
                if resp.status_code == 200:
                    translated = resp.json()["choices"][0]["message"]["content"].strip()
                    return TranslateResponse(translated=translated, source_lang="en")
        except Exception as e:
            logger.error(f"OpenAI translation failed: {e}")

    # Last resort fallback: original English text with warning
    return TranslateResponse(
        translated=req.text,
        source_lang="en",
        warning="Translation services offline/unconfigured"
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    AI assistant powered by modular LLM connection for Braille help and context.
    """
    try:
        reply = await AIAssistant.get_reply(
            message=req.message,
            context=req.context,
            history=req.history
        )
        return ChatResponse(reply=reply)
    except Exception as e:
        logger.error(f"Chat route error: {e}", exc_info=True)
        return ChatResponse(reply="I am having trouble connecting right now. Please try again.")
