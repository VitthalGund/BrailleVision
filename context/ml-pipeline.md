# BrailleVision — ML Pipeline & Model Training Plan

## Pipeline Overview

```
Camera Frame
    │
    ▼
[1] OpenCV Preprocessing
    ├── Grayscale conversion
    ├── CLAHE (contrast enhancement)
    ├── Adaptive Gaussian thresholding
    └── Morphological closing (connect dots)
    │
    ▼
[2] YOLOv8n Dot Detection
    ├── Input: 640×640 resized frame
    ├── Output: List of dot bounding boxes + confidence
    └── NMS threshold: 0.45
    │
    ▼
[3] Cell Grouper (Geometric Algorithm)
    ├── Sort dots by (row, column) position
    ├── Cluster dots into 6-dot Braille cells
    ├── Handle variable dot spacing
    └── Output: List of BrailleCell (6 binary positions)
    │
    ▼
[4] Braille Decoder (Table Lookup)
    ├── Convert 6-bit pattern to character
    ├── Apply Grade 1 Braille rules
    └── Output: Character string
    │
    ▼
[5] Post-Processing
    ├── Concatenate characters → words → sentences
    ├── Apply basic correction heuristics
    └── Output: Final text string
```

---

## Stage 1: OpenCV Preprocessing

### Why This Matters

Physical Braille dots are embossed (raised bumps on same-color paper). Under direct flat light, they're nearly invisible. Preprocessing is the difference between 20% and 80% accuracy.

### Code: `backend/inference/preprocessor.py`

```python
import cv2
import numpy as np

def preprocess_braille_image(img: np.ndarray) -> np.ndarray:
    """
    Preprocess a physical Braille image for dot detection.

    Args:
        img: BGR image from camera
    Returns:
        Preprocessed image ready for YOLO inference
    """
    # 1. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. CLAHE — Contrast Limited Adaptive Histogram Equalization
    # Makes dots visible even in uneven lighting
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # 3. Gaussian blur to reduce noise (preserves dot shapes)
    blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)

    # 4. Adaptive thresholding
    # Handles local lighting variations across the image
    thresh = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=11,
        C=2
    )

    # 5. Morphological operations
    # Close small gaps; connect broken dot outlines
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # 6. Convert back to 3-channel for YOLO input
    result = cv2.cvtColor(morph, cv2.COLOR_GRAY2BGR)

    return result

def enhance_shadows(img: np.ndarray) -> np.ndarray:
    """
    Shadow removal using morphological background estimation.
    Useful when there's directional lighting causing shadows under dots.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Large kernel to estimate background (ignores small dots)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    background = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel)
    # Subtract background to isolate dots
    diff = cv2.absdiff(background, gray)
    normalized = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
    return normalized
```

### Testing Preprocessing

```bash
python training/scripts/test_preprocessing.py --image sample_inputs/test_braille.jpg
# Saves: preprocessed_result.jpg with side-by-side comparison
```

---

## Stage 2: YOLOv8n Training

### Model Choice

- **YOLOv8n (nano)** — smallest, fastest, still accurate enough
- Single class: `dot`
- Input size: 640×640
- Expected training time: 2–3 hours on Colab GPU, ~8 hours on CPU

### Training Script: `training/train.py`

```python
from ultralytics import YOLO
import yaml
import os

# Configuration
CONFIG = {
    'model': 'yolov8n.pt',          # Start from pretrained nano
    'data': 'dataset/data.yaml',
    'epochs': 100,
    'imgsz': 640,
    'batch': 16,
    'device': 'cuda',               # 'cpu' if no GPU
    'patience': 20,                 # Early stopping
    'save': True,
    'project': 'training/runs',
    'name': 'braille_dot_v1',
    'lr0': 0.01,
    'lrf': 0.01,
    'momentum': 0.937,
    'weight_decay': 0.0005,
    'warmup_epochs': 3,
    'hsv_v': 0.4,                   # Brightness augmentation (critical)
    'degrees': 10.0,                # Rotation augmentation
    'translate': 0.1,
    'scale': 0.5,
    'flipud': 0.0,                  # Don't flip vertically (Braille has top/bottom)
    'fliplr': 0.5,
    'mosaic': 1.0,
}

def train():
    model = YOLO(CONFIG['model'])
    results = model.train(**CONFIG)

    # Export to ONNX for faster inference
    model.export(format='onnx', imgsz=640)

    print(f"Best model saved to: {results.save_dir}/weights/best.pt")
    print(f"mAP50: {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")

if __name__ == '__main__':
    train()
```

### Google Colab Training (Recommended)

```python
# In Colab notebook:
!pip install ultralytics roboflow

# Mount Drive for persistence
from google.colab import drive
drive.mount('/content/drive')

# Download dataset
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_KEY")
project = rf.workspace("ws").project("braille-dots")
dataset = project.version(1).download("yolov8")

# Train
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
model.train(data='data.yaml', epochs=100, imgsz=640, device='cuda')

# Copy weights to Drive
!cp runs/detect/train/weights/best.pt /content/drive/MyDrive/braillevision/
```

### Expected Metrics (Target)

| Metric          | Target        | Acceptable    |
| --------------- | ------------- | ------------- |
| mAP50           | ≥ 0.85        | ≥ 0.70        |
| Precision       | ≥ 0.85        | ≥ 0.70        |
| Recall          | ≥ 0.85        | ≥ 0.70        |
| Inference speed | < 100ms (GPU) | < 500ms (CPU) |

---

## Stage 3: Cell Grouper Algorithm

### The Problem

YOLO gives us a list of dot positions: `[(x1,y1), (x2,y2), ...]`
We need to group them into Braille cells: each cell = 6 dot positions in a 2×3 grid.

### Algorithm: `backend/inference/cell_grouper.py`

```python
import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class Dot:
    x: float  # center x
    y: float  # center y
    confidence: float
    radius: float

@dataclass
class BrailleCell:
    dots: list[bool]     # 6 booleans: [dot1, dot2, dot3, dot4, dot5, dot6]
    x: float             # cell top-left x
    y: float             # cell top-left y
    width: float
    height: float
    confidence: float

def group_dots_into_cells(dots: list[Dot],
                           dot_spacing_estimate: Optional[float] = None) -> list[BrailleCell]:
    """
    Group detected Braille dots into Braille cells.

    Braille cell structure:
        Dot 1 | Dot 4
        Dot 2 | Dot 5
        Dot 3 | Dot 6

    Algorithm:
    1. Estimate dot spacing from nearest-neighbor distances
    2. Sort dots by row (y-coordinate, clustered)
    3. Within each row, sort by column (x-coordinate)
    4. Pair adjacent dots into columns
    5. Pair adjacent column-pairs into cells
    """
    if not dots:
        return []

    # Step 1: Estimate dot spacing
    if dot_spacing_estimate is None:
        dot_spacing_estimate = estimate_dot_spacing(dots)

    cell_height = dot_spacing_estimate * 2.5  # 3 rows, 2 gaps
    cell_width = dot_spacing_estimate * 1.5   # 2 cols, 1 gap

    # Step 2: Cluster dots into rows
    dots_sorted_y = sorted(dots, key=lambda d: d.y)
    rows = cluster_by_proximity(dots_sorted_y, axis='y',
                                 threshold=dot_spacing_estimate * 0.6)

    # Step 3: Sort rows into groups of 3 (each cell has 3 rows of dots)
    cells = []
    i = 0
    while i < len(rows) - 2:
        row1, row2, row3 = rows[i], rows[i+1], rows[i+2]

        # Check rows are close enough to be one cell
        if (abs(row2[0].y - row1[0].y) < dot_spacing_estimate * 1.5 and
            abs(row3[0].y - row2[0].y) < dot_spacing_estimate * 1.5):

            cells.extend(rows_to_cells(row1, row2, row3,
                                        dot_spacing_estimate))
            i += 3
        else:
            i += 1

    return sorted(cells, key=lambda c: (c.y, c.x))

def estimate_dot_spacing(dots: list[Dot]) -> float:
    """Estimate inter-dot spacing from nearest neighbor distances."""
    if len(dots) < 2:
        return 20.0  # default fallback

    positions = np.array([(d.x, d.y) for d in dots])
    distances = []

    for i, pos in enumerate(positions):
        dists = np.linalg.norm(positions - pos, axis=1)
        dists[i] = np.inf  # exclude self
        distances.append(np.min(dists))

    return float(np.median(distances))

def dot_pattern_to_char(dots: list[bool]) -> str:
    """Convert 6-bit dot pattern to Braille character."""
    from backend.utils.braille_table import BRAILLE_UNICODE_TO_CHAR

    # Convert boolean list to integer (bit pattern)
    # Dot 1=bit0, Dot 2=bit1, ..., Dot 6=bit5
    pattern = sum(1 << i for i, v in enumerate(dots) if v)

    return BRAILLE_UNICODE_TO_CHAR.get(pattern, '?')
```

---

## Stage 4: Braille Decoder Table

### Complete Grade 1 Braille Mapping

`backend/utils/braille_table.py`

```python
# Braille dot patterns as 6-bit integers
# Bit 0 = dot 1 (top-left), Bit 1 = dot 2 (mid-left), Bit 2 = dot 3 (bottom-left)
# Bit 3 = dot 4 (top-right), Bit 4 = dot 5 (mid-right), Bit 5 = dot 6 (bottom-right)

BRAILLE_PATTERN_TO_CHAR = {
    0b000001: 'a',  # dot 1
    0b000011: 'b',  # dots 1,2
    0b001001: 'c',  # dots 1,4
    0b011001: 'd',  # dots 1,4,5
    0b011000: 'e',  # dots 1,5
    0b001011: 'f',  # dots 1,2,4
    0b011011: 'g',  # dots 1,2,4,5
    0b010011: 'h',  # dots 1,2,5
    0b001010: 'i',  # dots 2,4
    0b011010: 'j',  # dots 2,4,5
    0b000101: 'k',  # dots 1,3
    0b000111: 'l',  # dots 1,2,3
    0b001101: 'm',  # dots 1,3,4
    0b011101: 'n',  # dots 1,3,4,5
    0b011100: 'o',  # dots 1,3,5
    0b001111: 'p',  # dots 1,2,3,4
    0b011111: 'q',  # dots 1,2,3,4,5
    0b010111: 'r',  # dots 1,2,3,5
    0b001110: 's',  # dots 2,3,4
    0b011110: 't',  # dots 2,3,4,5
    0b100101: 'u',  # dots 1,3,6
    0b100111: 'v',  # dots 1,2,3,6
    0b111010: 'w',  # dots 2,4,5,6
    0b101101: 'x',  # dots 1,3,4,6
    0b111101: 'y',  # dots 1,3,4,5,6
    0b111100: 'z',  # dots 1,3,5,6
    0b000000: ' ',  # empty cell = space
}

# Number indicator: when preceded by 0b011010 (#), the next cells are digits
BRAILLE_NUMBER_MAP = {
    0b000001: '1',
    0b000011: '2',
    0b001001: '3',
    0b011001: '4',
    0b011000: '5',
    0b001011: '6',
    0b011011: '7',
    0b010011: '8',
    0b001010: '9',
    0b011010: '0',
}

# Capital indicator: 0b100000 (dot 6 alone)
CAPITAL_INDICATOR = 0b100000
NUMBER_INDICATOR = 0b111010  # dots 3,4,5,6
```

---

## Testing Strategy

### Unit Tests (`tests/unit/`)

```python
# test_braille_decoder.py
def test_decode_hello():
    # 'h' = dots 1,2,5 = 0b010011
    h_pattern = [True, True, False, False, True, False]
    assert decode_cell(h_pattern) == 'h'

def test_decode_space():
    space_pattern = [False]*6
    assert decode_cell(space_pattern) == ' '

# test_cell_grouper.py
def test_group_simple_row():
    dots = [Dot(10, 10, 0.9, 3), Dot(10, 30, 0.9, 3), Dot(10, 50, 0.9, 3),
            Dot(25, 10, 0.9, 3), Dot(25, 30, 0.9, 3), Dot(25, 50, 0.9, 3)]
    cells = group_dots_into_cells(dots)
    assert len(cells) == 1
```

### Integration Tests (`tests/integration/`)

```python
# test_pipeline.py
def test_pipeline_hello():
    img = cv2.imread('tests/fixtures/braille_hello.jpg')
    result = run_pipeline(img)
    assert result['text'].lower() == 'hello'
    assert result['confidence'] > 0.7
```

### Performance Tests

```bash
python tests/test_latency.py --image sample_inputs/test_braille.jpg --runs 10
# Expected output: Mean: 145ms, P95: 230ms, Max: 340ms
```
