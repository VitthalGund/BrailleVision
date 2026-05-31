# BrailleVision — Dataset Strategy

## Goal

Train a YOLOv8n model to detect individual Braille dots in real physical embossed Braille images, then use geometric reasoning to group dots into Braille cells (6-dot grids), then classify cells as characters.

---

## What We're Detecting

### Class Definitions

We train YOLO to detect **Braille dots** (not letters). Then post-processing groups them.

| YOLO Class | Label | Description                                 |
| ---------- | ----- | ------------------------------------------- |
| 0          | `dot` | A single embossed Braille dot (raised bump) |

That's it. One class. This is intentional — it dramatically reduces dataset complexity.

**Alternative approach** (harder but more accurate):
| Class | Label |
|---|---|
| 0–25 | `a` through `z` |
| 26–35 | `0` through `9` |

We recommend the **single-class dot detection** approach for hackathon speed. Post-process with geometry.

---

## Dataset Sources

### Source 1: Roboflow Universe (Primary)

**URL**: https://universe.roboflow.com/search?q=braille&t=metadata

Key public datasets:

1. **"Braille Alphabet Detection"** (search Roboflow Universe)
   - ~800-2000 images of Braille cells
   - Pre-annotated with bounding boxes
   - YOLOv8 format available
2. **"Braille Dot Detection"** datasets
   - Various contributors
   - Mix of real and synthetic

**How to download via API**:

```python
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_KEY")
project = rf.workspace("WORKSPACE").project("braille-detection")
dataset = project.version(1).download("yolov8")
```

### Source 2: Synthetic Data Generation (Critical Supplement)

Since real Braille datasets are small, we generate synthetic images.

**Method**: Use `generate_synthetic_braille.py` (see training/scripts/)

- Renders Braille dot patterns programmatically
- Varies: lighting direction, blur, noise, contrast, background texture
- Exports YOLO-format annotations automatically
- Can generate 1,000+ images in minutes

### Source 3: Custom Collection

- Photograph real Braille books/pages from multiple angles
- Use good raking light (light from the side makes dots cast shadows = visible)
- Annotate with Roboflow annotation tool (free tier)
- Target: 100–200 real images minimum

### Source 4: Public Research Datasets

- **BRL-100K** (if accessible) — 100k synthetic Braille images
- University accessibility lab datasets
- GitHub: search "braille dataset yolo"

---

## Dataset Pipeline

### Step 1: Download + Merge

```bash
# Download from Roboflow
python training/scripts/download_dataset.py

# Generate synthetic data
python training/scripts/generate_synthetic.py --count 500

# Merge all sources
python training/scripts/merge_datasets.py
```

### Step 2: Annotations Format (YOLO)

```
dataset/
  images/
    train/   ← 70% of data
    val/     ← 20% of data
    test/    ← 10% of data
  labels/
    train/   ← .txt files (one per image)
    val/
    test/
  data.yaml
```

**data.yaml**:

```yaml
path: ../dataset
train: images/train
val: images/val
test: images/test

nc: 1
names: ["dot"]
```

**Label format** (YOLO normalized):

```
# class cx cy w h (all normalized 0–1)
0 0.423 0.512 0.025 0.031
0 0.489 0.512 0.025 0.031
```

### Step 3: Augmentation Strategy

Apply during training (Ultralytics built-in augmentation):

```yaml
# In yolo config or training args:
hsv_h: 0.015 # Hue variation (Braille paper isn't always pure white)
hsv_s: 0.3 # Saturation
hsv_v: 0.4 # Brightness (critical — simulate poor lighting)
fliplr: 0.5 # Horizontal flip (Braille is symmetric)
mosaic: 1.0 # Mosaic augmentation
degrees: 10.0 # Rotation (held phone isn't always level)
translate: 0.1 # Position variation
scale: 0.5 # Scale variation (different distances from paper)
blur: 2 # Camera blur simulation
```

### Step 4: Dataset Split

- Train: 70% (~700 images minimum)
- Val: 20% (~200 images)
- Test: 10% (~100 images, held out for final evaluation)

---

## Annotation Guide (for manual labeling)

When annotating real Braille images:

1. Draw tight bounding boxes around each dot (the raised bump)
2. Include the full circular shadow around the bump, not just the highlight
3. For hard-to-see dots, zoom in to 400% in annotation tool
4. Label every dot in the image, not just clear ones
5. Skip images where dots are completely invisible (they'll hurt training)

**Roboflow annotation tool** (free, web-based):

1. Create project at roboflow.com
2. Upload images
3. Use "smart polygon" or "bounding box" tool
4. Label class = "dot"
5. Export → YOLOv8 format

---

## Quality Checklist

Before training:

- [ ] ≥ 500 total images
- [ ] ≥ 70% real Braille images (not just synthetic)
- [ ] Class balance: every Braille character has at least 20 examples
- [ ] Train/val/test split done properly (no leakage)
- [ ] data.yaml paths correct
- [ ] All label files non-empty
- [ ] Sample images verified (view 10 random with bboxes)

---

## Expected Dataset Size (Hackathon Realistic)

| Source                   | Count                | Quality           |
| ------------------------ | -------------------- | ----------------- |
| Roboflow public datasets | 500-1000 images      | Medium            |
| Synthetic generated      | 300-500 images       | High (augmented)  |
| Custom photographed      | 50-100 images        | High (real-world) |
| **Total**                | **~850-1600 images** | Mix               |

This is enough for a working demo. Commercial quality would require 10,000+.
