from pydantic import BaseModel, Field
from typing import List, Optional

class BrailleCell(BaseModel):
    dots: List[bool] = Field(..., description="6-dot boolean pattern [dot1, dot2, dot3, dot4, dot5, dot6]")
    char: str = Field(..., description="Decoded character mapped to this cell")
    bbox: List[float] = Field(..., description="Bounding box [x, y, width, height]")
    confidence: float = Field(..., description="Confidence of detection/decoding (0.0 to 1.0)")

class BrailleDot(BaseModel):
    x: float = Field(..., description="Center X position of dot")
    y: float = Field(..., description="Center Y position of dot")
    confidence: float = Field(..., description="Confidence of dot detection")

class InferenceResponse(BaseModel):
    text: str = Field(..., description="Overall decoded Grade 1 English text")
    confidence: float = Field(..., description="Average confidence score of the cells")
    cells: List[BrailleCell] = Field(..., description="List of recognized Braille cells")
    dots: List[BrailleDot] = Field(..., description="List of all raw detected dots")
    processing_time_ms: int = Field(..., description="Backend processing time in milliseconds")
    error: Optional[str] = Field(None, description="Optional error message if pipeline had non-fatal issues")

class TranslateRequest(BaseModel):
    text: str = Field(..., description="Text to translate")
    target_lang: str = Field("en", description="Target language ISO 639-1 code")

class TranslateResponse(BaseModel):
    translated: str = Field(..., description="Translated text")
    source_lang: str = Field("en", description="Source language ISO 639-1 code")
    warning: Optional[str] = Field(None, description="Warning warning message if translation fallback occurred")

class ChatRequest(BaseModel):
    message: str = Field(..., description="User question or input message")
    context: str = Field("", description="Context of the current scan (e.g. recognized text)")
    history: List[dict] = Field([], description="Chat message history list of dicts with role and content")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="Assistant reply message")
