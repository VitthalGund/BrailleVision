# BrailleVision — Progress Tracker

## Current Phase

**Phase 3: Immersive VR/XR Modes** — Cardboard VR and Smart Glasses modes fully built and build-verified

## Last Updated

2026-06-01

---

## Completed Work

### ✅ Phase 0: Foundation

- [x] Full strategic research and analysis
- [x] Project directory structure created
- [x] context/project-overview.md
- [x] context/architecture.md
- [x] context/ui-context.md
- [x] context/code-standards.md
- [x] context/ai-workflow-rules.md
- [x] README.md skeleton

### ✅ Phase 1: Backend API Setup

- [x] FastAPI modular app configuration ([app.py](file:///c:/Users/vitth/OneDrive/Documents/SEM%20VI/BrailleVision/backend/app.py))
- [x] Modular API routing setup ([routes.py](file:///c:/Users/vitth/OneDrive/Documents/SEM%20VI/BrailleVision/backend/api/routes.py))
- [x] Request and response Pydantic schemas ([schemas.py](file:///c:/Users/vitth/OneDrive/Documents/SEM%20VI/BrailleVision/backend/models/schemas.py))
- [x] Reorganized start code into `backend/` package structures
- [x] Configured Python virtual environment and successfully installed dependencies
- [x] Modular AI assistant chat service supporting mock and API providers ([ai_assistant.py](file:///c:/Users/vitth/OneDrive/Documents/SEM%20VI/BrailleVision/backend/utils/ai_assistant.py))

### ✅ Phase 2: Frontend Setup & Components

- [x] Scaffolding React + TypeScript application via Vite ([frontend/](file:///c:/Users/vitth/OneDrive/Documents/SEM%20VI/BrailleVision/frontend/))
- [x] Tailwind CSS 3 and PostCSS configuration
- [x] PWA manifest and service worker plugin config ([vite.config.ts](file:///c:/Users/vitth/OneDrive/Documents/SEM%20VI/BrailleVision/frontend/vite.config.ts))
- [x] Zustand state stores for results and settings
- [x] Built core components: `NavBar`, `CameraView`, `BrailleCellDebugger`, `ResultPanel`, `AIAssistant`
- [x] Built app views: `ScanPage`, `HistoryPage`, `SettingsPage`
- [x] Generated mock Braille sheet sample image for offline testing

### ✅ Phase 2.5: Hands-Free Auditory AR

- [x] `useVoiceCommands.ts` — continuous WebKit Speech Recognition for hands-free triggers ("Read", "Stop", "Translate to Hindi")
- [x] `useAudioGuidance.ts` — Web Audio API pitch-based beep feedback (higher pitch = more cells aligned)
- [x] Wearable Glasses Mode toggle in `CameraView` with pulse-border indicator and auto-TTS loop

### ✅ Phase 3: Immersive VR/XR Modes

- [x] Installed `three` + `@types/three` npm packages
- [x] `companionStore.ts` — Zustand store for VR mode, device role, 4-digit pairing code, spatial streaming data
- [x] `useGyroscope.ts` — `DeviceOrientationEvent` head-tracking hook with iOS 13+ permission handling and exponential low-pass smoothing
- [x] `useVerbalGuidance.ts` — spoken directional alignment prompts every 4s (centroid offset + spread analysis)
- [x] `StereoCardboardView.tsx` — full-screen SBS stereo canvas; dual canvas with camera passthrough, ±8px parallax depth, gyro-driven text offset, lens vignette
- [x] `SpatialXRView.tsx` — Three.js WebXR scene (`immersive-ar`); spatial text billboard at 2m; desktop star-field simulator fallback with mouse-drag look-around
- [x] `CameraView.tsx` fully rebuilt with 4-tab mode switcher: Camera → Cardboard VR → Smart Glasses → Upload
- [x] **Build verified**: `tsc -b && vite build` — 1765 modules, 0 TypeScript errors

---

## In Progress

- [ ] End-to-end integration verification (connecting frontend live capture to backend `/api/infer`)
- [ ] Training YOLOv8 model on custom Braille dataset
- [ ] Multi-device pairing WebSocket relay (phone ↔ headset live sync for standalone XR headsets)

---

## Open Questions

| Question                                                      | Priority | Status                                                              |
| ------------------------------------------------------------- | -------- | ------------------------------------------------------------------- |
| LibreTranslate self-hosted or use Claude API for translation? | MEDIUM   | Resolved — Modular Fallbacks in routes                              |
| WebXR AR overlay — include in MVP or stretch?                 | LOW      | **Resolved — SHIPPED** (Cardboard SBS + Three.js WebXR both built) |
| Should we support image upload from the start?                | MEDIUM   | Resolved — Implemented as fallback                                  |
| WebSocket relay server for phone↔headset sync?               | MEDIUM   | Open — needed for live Quest/Vision Pro text streaming              |

---

## Next Steps (Priority Order)

1. **Verify integration** — Run the React dev server and test camera frames against backend `/health` and `/api/infer` endpoints
2. **Collect dataset** — Use Roboflow Braille public datasets
3. **Train YOLOv8n** — Train YOLOv8n model on dot dataset
4. **WebSocket bridge** — Build a lightweight relay server so a scanning phone can push live inference results to a paired standalone headset in real time

---

## Known Issues / Risks

| Risk                                      | Severity | Mitigation                                                                   |
| ----------------------------------------- | -------- | ---------------------------------------------------------------------------- |
| Model accuracy on real-world Braille      | HIGH     | Strong OpenCV preprocessing; data augmentation                               |
| Lighting variation ruins dot detection    | HIGH     | Adaptive histogram equalization; shadow removal                              |
| Physical Braille paper curvature          | MEDIUM   | Perspective correction in preprocessing                                      |
| GPU not available for training            | MEDIUM   | Use Google Colab; YOLOv8n is fast even on CPU                                |
| Camera access blocked in demo environment | LOW      | Have image upload fallback ready                                             |
| iOS DeviceOrientation requires user gesture | MEDIUM | `useGyroscope` calls `requestPermission()` on button tap before entering VR |
| WebXR `immersive-ar` not available on all devices | MEDIUM | Three.js scene falls back to desktop 3D simulator automatically          |
| AudioContext blocked by browser autoplay policy | LOW | `useAudioGuidance` auto-unlocks on first user tap event                  |

---

## Metrics Dashboard (to be filled during development)

| Metric                        | Target       | Current |
| ----------------------------- | ------------ | ------- |
| Char accuracy (clean Braille) | ≥ 85%        | TBD     |
| Char accuracy (noisy/angled)  | ≥ 70%        | TBD     |
| End-to-end latency            | < 2s         | TBD     |
| Model size                    | < 50MB       | TBD     |
| Training epochs               | ~100         | TBD     |
| Dataset size                  | ≥ 500 images | TBD     |
