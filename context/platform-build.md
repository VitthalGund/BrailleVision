# BrailleVision — Platform Build Plan

## Platform Strategy

One codebase → Web + Mobile (PWA) + Desktop (Electron, post-hack)

All platforms are covered by a single React PWA.
AR overlay uses WebXR (mobile only, feature-detected).

---

## Frontend Build Plan

### Initial Setup

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install tailwindcss postcss autoprefixer @tailwindcss/forms
npm install zustand react-router-dom
npm install vite-plugin-pwa workbox-window
npm install lucide-react framer-motion
npx tailwindcss init -p
```

### Project Structure

```
frontend/
├── public/
│   ├── manifest.json       ← PWA manifest
│   ├── icons/              ← App icons (72, 96, 128, 144, 152, 192, 384, 512px)
│   └── braille-sample.jpg  ← Demo Braille image for judges
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── components/
│   │   ├── CameraView.tsx
│   │   ├── ResultPanel.tsx
│   │   ├── AIAssistant.tsx
│   │   ├── BrailleCellDebugger.tsx  ← The judge wow-factor feature
│   │   ├── LanguageSelector.tsx
│   │   ├── TTSControls.tsx
│   │   └── NavBar.tsx
│   ├── pages/
│   │   ├── ScanPage.tsx
│   │   ├── HistoryPage.tsx
│   │   └── SettingsPage.tsx
│   ├── hooks/
│   │   ├── useCamera.ts
│   │   ├── useBrailleInfer.ts
│   │   ├── useTTS.ts
│   │   └── useAIAssistant.ts
│   ├── stores/
│   │   ├── resultStore.ts
│   │   └── settingsStore.ts
│   └── utils/
│       ├── api.ts
│       ├── brailleMap.ts
│       └── imageUtils.ts
```

### Key Component Implementations

#### CameraView.tsx

```tsx
import { useRef, useEffect, useCallback } from "react";
import { useCamera } from "@/hooks/useCamera";

export function CameraView({ onFrame }: { onFrame: (blob: Blob) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { stream, isLive, startCamera, stopCamera } = useCamera();

  // Capture frame every 500ms in live mode
  useEffect(() => {
    if (!isLive || !videoRef.current || !canvasRef.current) return;

    const interval = setInterval(() => {
      const video = videoRef.current!;
      const canvas = canvasRef.current!;
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => blob && onFrame(blob), "image/jpeg", 0.85);
    }, 500);

    return () => clearInterval(interval);
  }, [isLive, onFrame]);

  return (
    <div className="relative w-full aspect-video bg-black rounded-xl overflow-hidden">
      <video
        ref={videoRef}
        className="w-full h-full object-cover"
        autoPlay
        playsInline
        muted
        aria-label="Camera feed for Braille scanning"
      />
      <canvas ref={canvasRef} className="hidden" width={640} height={480} />

      {/* Scanning overlay */}
      {isLive && (
        <div
          className="absolute inset-0 border-4 border-green-400 rounded-xl 
                        animate-pulse pointer-events-none"
        />
      )}

      {/* Controls */}
      <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-4">
        <button
          onClick={isLive ? stopCamera : startCamera}
          className="px-6 py-3 bg-vision-blue text-white rounded-full font-semibold
                     shadow-lg active:scale-95 transition-transform"
        >
          {isLive ? "⏸ Pause" : "📷 Scan"}
        </button>
      </div>
    </div>
  );
}
```

#### BrailleCellDebugger.tsx (Judge Wow Factor)

```tsx
import { useEffect, useRef } from "react";
import type { BrailleCell } from "@/utils/api";

interface Props {
  cells: BrailleCell[];
  imageWidth: number;
  imageHeight: number;
}

export function BrailleCellDebugger({ cells, imageWidth, imageHeight }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !cells.length) return;

    const ctx = canvas.getContext("2d")!;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    cells.forEach((cell) => {
      const { x, y, w, h, char, confidence } = cell;

      // Color based on confidence
      const color =
        confidence > 0.85
          ? "#10B981"
          : confidence > 0.65
            ? "#F59E0B"
            : "#EF4444";

      // Draw bounding box
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);

      // Draw character label
      ctx.fillStyle = color;
      ctx.font = "bold 14px Inter";
      ctx.fillText(`${char} ${Math.round(confidence * 100)}%`, x, y - 4);

      // Draw detected dot positions
      cell.dots.forEach((dotPresent, i) => {
        if (!dotPresent) return;
        const col = i < 3 ? 0 : 1;
        const row = i % 3;
        const dotX = x + col * (w / 2) + w / 4;
        const dotY = y + row * (h / 3) + h / 6;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(dotX, dotY, 3, 0, Math.PI * 2);
        ctx.fill();
      });
    });
  }, [cells]);

  return (
    <canvas
      ref={canvasRef}
      width={imageWidth}
      height={imageHeight}
      className="absolute inset-0 w-full h-full pointer-events-none"
      aria-hidden="true"
    />
  );
}
```

#### useTTS.ts — Web Speech API

```typescript
import { useCallback, useRef } from "react";
import { useSettingsStore } from "@/stores/settingsStore";

export function useTTS() {
  const { ttsLanguage, ttsRate, ttsPitch } = useSettingsStore();
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const speak = useCallback(
    (text: string, lang?: string) => {
      if (!window.speechSynthesis) return;

      // Cancel any current speech
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang ?? ttsLanguage;
      utterance.rate = ttsRate;
      utterance.pitch = ttsPitch;

      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [ttsLanguage, ttsRate, ttsPitch],
  );

  const stop = useCallback(() => {
    window.speechSynthesis.cancel();
  }, []);

  return { speak, stop };
}
```

---

## Backend Build Plan

### Initial Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn python-multipart
pip install ultralytics opencv-python-headless numpy
pip install anthropic httpx python-dotenv
pip install pydantic
```

### Main App: `backend/app.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI(
    title="BrailleVision API",
    description="Real-time physical Braille recognition API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": True}
```

### Routes: `backend/api/routes.py`

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import numpy as np
import cv2
import base64
import time

from models.schemas import InferenceRequest, InferenceResponse, TranslateRequest
from inference.pipeline import BraillePipeline
from utils.translator import translate_text
from utils.ai_assistant import get_ai_response

router = APIRouter()
pipeline = BraillePipeline()  # Load model once at startup

@router.post("/infer", response_model=InferenceResponse)
async def infer_braille(file: UploadFile = File(...)):
    """Detect and decode Braille from an uploaded image."""
    start = time.time()

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(400, "Invalid image")

    result = pipeline.run(img)
    result['processing_time_ms'] = int((time.time() - start) * 1000)

    return result

@router.post("/translate")
async def translate(req: TranslateRequest):
    """Translate recognized text to target language."""
    translated = await translate_text(req.text, req.target_lang)
    return {"translated": translated, "source_lang": "en"}

@router.post("/chat")
async def chat(message: str, context: str = ""):
    """AI assistant for Braille help."""
    reply = await get_ai_response(message, context)
    return {"reply": reply}
```

---

## PWA Configuration

### `frontend/public/manifest.json`

```json
{
  "name": "BrailleVision",
  "short_name": "BrailleVision",
  "description": "Real-time physical Braille recognition and translation",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0F1729",
  "theme_color": "#1A56DB",
  "orientation": "portrait",
  "icons": [
    { "src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    {
      "src": "icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "categories": ["accessibility", "utilities"],
  "screenshots": [
    { "src": "screenshots/scan.jpg", "sizes": "390x844", "type": "image/jpeg" }
  ]
}
```

### `vite.config.ts` — PWA Plugin

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["*.jpg", "*.png", "*.ico"],
      manifest: false, // Use our own manifest.json
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,jpg}"],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\./i,
            handler: "NetworkFirst",
            options: { cacheName: "api-cache", networkTimeoutSeconds: 5 },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: { "@": "/src" },
  },
});
```

---

## AR Overlay Plan (Stretch Goal)

### WebXR Implementation

```typescript
// hooks/useAROverlay.ts
export function useAROverlay() {
  const startAR = async () => {
    if (!("xr" in navigator)) {
      alert("AR not supported on this device");
      return;
    }

    const session = await navigator.xr!.requestSession("immersive-ar", {
      requiredFeatures: ["hit-test", "dom-overlay"],
      domOverlay: { root: document.getElementById("ar-overlay")! },
    });

    // Three.js text sprites at detected Braille positions
    // This is the WOW moment — English text floating over Braille
  };
}
```

---

## Testing Plan

### Frontend Tests

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom

# Run unit tests
npm run test

# Test camera (requires browser — use Playwright)
npm run test:e2e
```

### Test Cases

#### Camera Tests

- [x] Camera feed starts on button click
- [x] Frame captured at correct interval
- [x] Error shown when camera permission denied
- [x] Fallback image upload works

#### Inference Tests

- [x] API call made with correct Content-Type
- [x] Loading state shown during inference
- [x] Result displayed in ResultPanel
- [x] Error handled gracefully (API down)

#### TTS Tests

- [x] Speech starts when result arrives
- [x] Speech stops when new scan starts
- [x] Language change updates voice

#### AI Assistant Tests

- [x] Message sent on Enter key
- [x] Response shown in chat bubble
- [x] Loading indicator during API call
- [x] Suggested prompts clickable

#### PWA Tests

- [x] App installable (manifest.json valid)
- [x] Works offline (shows cached last result)
- [x] Service worker registered
