# BrailleVision — AI Workflow Rules

## Development Philosophy

This project was built with AI-assisted development (Claude). All AI assistance is disclosed per hackathon rules.

## AI Tools Used

- **Claude (Anthropic)** — Architecture, code generation, documentation, strategy
- **Roboflow** — Dataset annotation assistance
- **GitHub Copilot** — In-editor code completion

All AI tool usage is logged in `ai_tools_disclosure.md`.

---

## Development Workflow

### Phase Order (Hackathon Timeline)

#### Hour 0–2: Foundation

1. ✅ Setup project structure and context files
2. ✅ Initialize Git repo + README skeleton
3. Setup backend FastAPI skeleton (app.py, routes)
4. Setup frontend React + Vite + Tailwind

#### Hour 2–6: ML Pipeline (Core)

1. Collect/prepare dataset (see `plan/dataset-strategy.md`)
2. Train YOLOv8n on Braille dot dataset
3. Build OpenCV preprocessing pipeline
4. Implement Braille cell grouper
5. Implement Braille decoder (dot pattern → character)
6. Wire together in `inference/pipeline.py`
7. Test against sample images

#### Hour 6–10: Backend API

1. POST /api/infer — image → text
2. POST /api/translate — text → target language
3. POST /api/chat — AI assistant endpoint
4. Add CORS, validation, error handling
5. Test with Postman / curl

#### Hour 10–16: Frontend

1. Camera feed component (getUserMedia)
2. Capture / live mode toggle
3. Result panel with TTS
4. AI assistant chat UI
5. Language selector
6. PWA manifest + service worker

#### Hour 16–20: Integration

1. Connect frontend to backend API
2. End-to-end test with real Braille
3. Fix accuracy issues
4. Optimize latency

#### Hour 20–24: Polish + Submission

1. BrailleCellDebugger overlay (judge wow factor)
2. README.md (comprehensive)
3. Demo video recording
4. Submit all required materials

---

## Scoping Rules

### What to Do When Stuck

1. **Model accuracy bad?** → Add more preprocessing (adaptive threshold, morphological ops)
2. **Latency too high?** → Switch to ONNX export, reduce input resolution
3. **Camera issues?** → Fallback to image upload mode
4. **Translation broken?** → Fallback to Claude API for translation
5. **TTS broken?** → Browser Web Speech API is always the first choice

### What NOT to Spend Time On

- Perfect UI animations (judges care about function)
- Grade 2 Braille support (too complex, out of scope)
- User accounts and auth (unnecessary)
- Database setup (session-only storage is fine)
- Docker (only if time permits and it helps reproducibility)

---

## Delivery Approach

### Every Feature Must Have

1. Working demo (even if rough)
2. At least a smoke test
3. Documented in README or code comments

### Minimum Viable Demo Script

```
1. Open app (mobile or desktop browser)
2. Point camera at Braille book/paper
3. Tap "Scan" button
4. Text appears in result panel
5. TTS reads it aloud
6. User types question in AI assistant
7. AI assistant responds helpfully
```

### Judge Verification Checklist

- [ ] `git clone` → runs without errors
- [ ] `pip install -r requirements.txt` → succeeds
- [ ] `npm install` → succeeds
- [ ] `python app.py` → server starts on port 8000
- [ ] `npm run dev` → frontend starts on port 5173
- [ ] `python inference/inference.py --source sample_inputs/test_braille.jpg` → outputs text
- [ ] Model weights present in `model/best.pt`
- [ ] Training code present in `training/train.py`
- [ ] Dataset sample images present in `dataset/sample_images/`
- [ ] `data.yaml` present in `dataset/`

---

## Context File Update Rules

- Update `progress-tracker.md` after completing each phase
- If a tech stack decision changes, update `architecture.md` immediately
- If scope changes, update `project-overview.md`
- Never let context files fall more than one phase behind reality
