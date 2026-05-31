# BrailleVision — Code Standards

## General Principles

1. **Readable over clever** — this is a hackathon; judges read code
2. **Type everything** — TypeScript frontend, typed Python backend
3. **Fail loudly** — raise explicit errors with context, never swallow exceptions
4. **Document the unusual** — Braille cell logic is non-obvious; comment it

---

## Python (Backend)

### Style

- PEP 8 strictly; Black formatter
- Type hints on all function signatures
- Docstrings on all public functions (one-liner minimum)

### Naming

- `snake_case` for all Python identifiers
- Constants: `UPPER_SNAKE_CASE`
- Files: `snake_case.py`

### Error Handling

```python
# GOOD
def detect_dots(image: np.ndarray) -> list[Dot]:
    if image is None or image.size == 0:
        raise ValueError("detect_dots: received empty image")
    ...

# BAD — never
def detect_dots(image):
    try:
        ...
    except:
        return []
```

### API Responses

Always return structured JSON via Pydantic models:

```python
class InferenceResponse(BaseModel):
    text: str
    confidence: float
    cells: list[BrailleCell]
    processing_time_ms: int
    error: str | None = None
```

### Import Order (isort)

1. Standard library
2. Third-party (fastapi, cv2, torch, ultralytics)
3. Local modules

---

## TypeScript / React (Frontend)

### Style

- ESLint + Prettier
- Functional components only (no class components)
- Hooks for all stateful logic

### Naming

- `PascalCase` components and types
- `camelCase` functions, variables, hooks
- `SCREAMING_SNAKE_CASE` constants
- Files: `ComponentName.tsx`, `useHookName.ts`, `utilityName.ts`

### Component Structure

```tsx
// 1. Imports
// 2. Types / interfaces
// 3. Constants
// 4. Component function
// 5. Export default

interface CameraViewProps {
  onFrame: (imageData: ImageData) => void;
  isLive: boolean;
}

export function CameraView({ onFrame, isLive }: CameraViewProps) {
  // hooks first
  const videoRef = useRef<HTMLVideoElement>(null);

  // effects second
  useEffect(() => { ... }, [isLive]);

  // handlers third
  const handleCapture = () => { ... };

  // render last
  return <video ref={videoRef} />;
}
```

### State Management

- Local state: `useState` / `useReducer`
- Shared app state: Zustand store (e.g. `useResultStore`)
- Server state: fetch + local useState (no React Query needed for hackathon)

### API Calls

```typescript
// Always use the central api.ts utility
import { api } from "@/utils/api";

const result = await api.infer(imageData);
// Never use fetch() directly in components
```

---

## ML / Training Code

### Notebook Standards

- Cell 1: Description + imports
- Cell 2: Config (all hyperparameters as constants)
- Cell 3: Data loading + visualization
- Cell 4: Training
- Cell 5: Evaluation + metrics
- Cell 6: Export model

### Model File Naming

```
model/
  best.pt          ← best validation checkpoint
  last.pt          ← final epoch checkpoint
  model.onnx       ← exported for inference
  model_info.md    ← training metadata (accuracy, epochs, dataset)
```

### Reproducibility

```python
SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)
random.seed(SEED)
```

---

## Git Conventions

### Commit Messages

```
feat: add YOLOv8 dot detection pipeline
fix: correct Braille cell grouping for angled images
docs: update dataset_info.md with class counts
test: add unit tests for cell classifier
chore: pin ultralytics==8.1.0 in requirements
```

### Branch Strategy (Hackathon simplified)

- `main` — always demo-ready
- `dev` — active development
- Merge to main only when feature is working

---

## File Naming Conventions

```
frontend/src/
  components/
    CameraView.tsx
    ResultPanel.tsx
    AIAssistant.tsx
    BrailleCellDebugger.tsx
  pages/
    ScanPage.tsx
    HistoryPage.tsx
    SettingsPage.tsx
  hooks/
    useCamera.ts
    useBrailleInfer.ts
    useTTS.ts
  utils/
    api.ts
    brailleMap.ts       ← Braille dot pattern → character mapping
    imageUtils.ts
  stores/
    resultStore.ts
    settingsStore.ts

backend/
  app.py              ← FastAPI entry point
  api/
    routes.py
  models/
    schemas.py          ← Pydantic models
  inference/
    pipeline.py         ← Main inference pipeline
    dot_detector.py     ← YOLOv8 wrapper
    cell_grouper.py     ← Geometric cell grouping
    braille_decoder.py  ← Cell pattern → character
  utils/
    image_utils.py
    braille_table.py    ← Complete Braille alphabet
```
