# BrailleVision — System Architecture

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     CLIENT (PWA)                               │
│  React + Tailwind + WebRTC Camera + Web Speech + Three.js      │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌───────────────────┐ │
│  │ Camera   │ │ Cardboard │ │ Spatial  │ │ AI Chat Assistant │ │
│  │ Feed     │ │ VR (SBS)  │ │ XR View  │ │ (Claude API)      │ │
│  └────┬─────┘ └─────┬─────┘ └────┬─────┘ └─────┬─────────────┘ │
│       │              │             │              │              │
│  ┌────▼──────────────▼─────────────▼──────────────▼──────────┐  │
│  │          State (Zustand): resultStore, settingsStore,      │  │
│  │          companionStore (VR mode, pairing code, role)      │  │
│  └────────────────────────────┬───────────────────────────────┘  │
└───────────────────────────────┼────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKEND API (FastAPI + Python)                  │
│  ┌──────────────────┐   ┌─────────────────────────────────┐ │
│  │ /api/detect      │   │ /api/translate                   │ │
│  │ /api/infer       │   │ /api/tts                         │ │
│  │ /api/stream      │   │ /api/chat                        │ │
│  └────────┬─────────┘   └─────────────────────────────────┘ │
│           │                                                  │
│  ┌────────▼──────────────────────────────────────────────┐  │
│  │           INFERENCE PIPELINE                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌─────────────────┐      │  │
│  │  │ OpenCV   │→ │ YOLOv8n  │→ │ Cell Classifier  │      │  │
│  │  │ Preproc  │  │ Dot Det. │  │ → Braille→Text  │      │  │
│  │  └──────────┘  └──────────┘  └─────────────────┘      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              EXTERNAL SERVICES                          │  │
│  │  Claude API (AI assistant + translation fallback)      │  │
│  │  LibreTranslate (primary translation, free)            │  │
│  │  Google TTS / Browser Web Speech (fallback)            │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack (Final)

### Frontend

| Layer     | Technology                       | Reason                            |
| --------- | -------------------------------- | --------------------------------- |
| Framework | React 18 + Vite                  | Fast dev, modern tooling          |
| Styling   | Tailwind CSS 3                   | Utility-first, fast theming       |
| PWA       | Vite PWA plugin                  | Offline, installable              |
| Camera    | `getUserMedia` + Canvas API      | Browser-native, no library needed |
| VR Mode   | SBS dual-canvas + `DeviceOrientationEvent` | Cardboard passthrough — only viable camera path inside a phone headset |
| XR Mode   | Three.js r169 + WebXR Device API (`immersive-ar`) | Spatial floating text for Quest / Vision Pro |
| Speech    | Web Speech API (SpeechSynthesis + SpeechRecognition) | Zero-cost, built-in; hands-free voice commands |
| State     | Zustand (resultStore, settingsStore, companionStore) | Lightweight global state |
| Routing   | React Router v6                  | SPA routing                       |

### Backend

| Layer        | Technology                                 | Reason                         |
| ------------ | ------------------------------------------ | ------------------------------ |
| API          | FastAPI (Python 3.11)                      | Fast, async, OpenAPI auto-docs |
| ML Runtime   | Python + OpenCV 4.x + YOLOv8 (Ultralytics) | Core detection pipeline        |
| Model format | `.pt` (PyTorch) → `.onnx` (for edge)       | Flexible deployment            |
| Translation  | LibreTranslate (self-hosted / API)         | Free, multilingual             |
| AI assistant | Anthropic Claude API                       | Conversational help            |
| TTS (server) | gTTS / pyttsx3 fallback                    | If browser API unavailable     |
| ASGI server  | Uvicorn                                    | Production-grade async         |

### ML Pipeline

| Step                | Tool                           | Notes                                            |
| ------------------- | ------------------------------ | ------------------------------------------------ |
| Image preprocessing | OpenCV 4                       | Grayscale, adaptive threshold, morphological ops |
| Dot detection       | YOLOv8n (custom trained)       | Detects individual dots                          |
| Cell grouping       | Geometric clustering algorithm | Groups 6 dots into Braille cells                 |
| Cell classification | Rule-based + CNN fallback      | Maps dot pattern → character                     |
| Post-processing     | Python dict lookup             | Grade 1 Braille alphabet mapping                 |

---

## VR/XR Modes — Architecture Detail

### Mode 1: Cardboard VR (Phone-in-Headset)

**Why SBS canvas, not WebXR `immersive-vr`?**
- `immersive-vr` WebXR blocks `getUserMedia` camera on all phones (browser security policy).
- SBS canvas + native `getUserMedia` stream is the **only viable camera passthrough path** for phone-based Cardboard headsets.

```
Phone (browser tab):
  getUserMedia (rear camera)
       │
       ▼
  StereoCardboardView.tsx
  ┌─────────────────────┬─────────────────────┐
  │   LEFT EYE canvas   │   RIGHT EYE canvas  │
  │  camera + text      │  camera + text       │
  │  parallax X = -8px  │  parallax X = +8px   │
  └─────────────────────┴─────────────────────┘
  DeviceOrientationEvent → gyro angles → text overlay offset
  Auto-capture every 2s → backend /api/infer → text update
```

### Mode 2: Standalone Headset / Smart Glasses (WebXR)

**Target devices:** Meta Quest (Horizon Browser), Apple Vision Pro (Safari WebXR)

```
Headset browser:
  SpatialXRView.tsx (Three.js)
  navigator.xr.requestSession('immersive-ar')
       │
       ▼
  THREE.WebGLRenderer (xr.enabled = true)
  THREE.PerspectiveCamera @ eye-level (y=1.6m)
  THREE.Mesh (PlaneGeometry) ← CanvasTexture (text billboard)
  Positioned 2m in front, always faces camera (billboard lookAt)

Fallback (no WebXR):
  Star field + GridHelper + mouse-drag orbit rotation
  (desktop 3D simulator for testing)
```

### Hands-Free Guidance System

| Layer | Hook | Mechanism |
|-------|------|-----------|
| Voice commands | `useVoiceCommands` | `webkitSpeechRecognition` continuous; triggers: "Read", "Stop", "Translate to [lang]" |
| Audio beeps | `useAudioGuidance` | Web Audio API oscillator; pitch ∝ cell count (more cells = higher pitch) |
| Verbal directions | `useVerbalGuidance` | `speechSynthesis` every 4s; analyses dot centroid offset from frame center |

---


### What the System Must Do

1. Accept: JPEG/PNG images OR video stream frames
2. Return: JSON `{ text: string, confidence: float, cells: Cell[] }`
3. Support: Grade 1 English Braille (A-Z, numbers, basic punctuation)
4. Latency: < 500ms per frame on modern GPU; < 2s on CPU

### What the System Must NOT Do

- Store raw camera images persistently (privacy — process and discard)
- Require user login for basic functionality (accessibility)
- Block on translation — translation is async and non-blocking

### API Contract

#### POST /api/infer

```json
Request:  { "image_b64": "base64...", "lang_out": "en" }
Response: {
  "text": "hello",
  "confidence": 0.87,
  "cells": [{ "bbox": [x,y,w,h], "char": "h", "conf": 0.91 }],
  "processing_time_ms": 145
}
```

#### POST /api/translate

```json
Request:  { "text": "hello", "target_lang": "hi" }
Response: { "translated": "नमस्ते", "source_lang": "en" }
```

#### POST /api/chat

```json
Request:  { "message": "what does this Braille symbol mean?", "context": "..." }
Response: { "reply": "..." }
```

---

## Storage Model

### Ephemeral (no persistence needed for MVP)

- Camera frames — processed in memory, never saved
- Inference results — returned immediately, not stored

### Session-level (browser localStorage)

- User language preference
- TTS voice preference
- Recent translation history (last 10 items)

### Optional (V1.1)

- Scan history — IndexedDB (browser-side)
- Exported files — File System Access API

---

## Deployment

### Hackathon Demo Setup

```
Local Machine:
  - Backend: uvicorn app:app --host 0.0.0.0 --port 8000
  - Frontend: npm run dev (Vite, port 5173)
  - Ngrok tunnel for mobile demo: ngrok http 8000

Judge Verification:
  - git clone + pip install -r requirements.txt + npm install
  - python inference/inference.py --source sample_inputs/test_braille.jpg
```

### GitHub Repo Structure (Matches submission requirements)

```
braillevision/
├── README.md
├── requirements.txt
├── setup_instructions.md
├── ai_tools_disclosure.md
├── frontend/          ← React PWA
├── backend/           ← FastAPI
├── model/
│   ├── best.pt
│   ├── model.onnx
│   └── model_info.md
├── training/
│   ├── train.py
│   ├── train.ipynb
│   └── training_logs/
├── dataset/
│   ├── data.yaml
│   ├── sample_images/
│   └── dataset_info.md
├── inference/
│   ├── inference.py
│   └── predict.py
├── demo/
│   └── screenshots/
└── tests/
```
