"""
BrailleVision â€” Dataset Verifier

Sanity-checks the YOLO dataset before training:
  - Counts images and labels per split
  - Checks for missing or empty label files
  - Checks for corrupted images
  - Renders a 3x4 sample grid with bounding boxes drawn
  - Reports statistics

Usage:
    python training/scripts/verify_dataset.py
    python training/scripts/verify_dataset.py --dataset dataset --samples 12
"""

import argparse
import random
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).parent.parent.parent
DEFAULT_DATASET = ROOT / "dataset"


def check_split(dataset_dir: Path, split: str) -> dict:
    """Check one split (train/val/test) and return stats."""
    img_dir = dataset_dir / "images" / split
    lbl_dir = dataset_dir / "labels" / split

    if not img_dir.exists():
        return {"split": split, "images": 0, "labels": 0, "missing_labels": 0,
                "empty_labels": 0, "corrupt_images": 0, "total_dots": 0}

    image_exts = {".jpg", ".jpeg", ".png"}
    img_files = sorted([f for f in img_dir.iterdir() if f.suffix.lower() in image_exts])

    missing_labels = []
    empty_labels = []
    corrupt_images = []
    total_dots = 0
    valid_labels = 0

    for img_path in img_files:
        lbl_path = lbl_dir / (img_path.stem + ".txt")

        if not lbl_path.exists():
            missing_labels.append(img_path.name)
            continue

        content = lbl_path.read_text().strip()
        if not content:
            empty_labels.append(img_path.name)
            continue

        lines = [l for l in content.split("\n") if l.strip()]
        total_dots += len(lines)
        valid_labels += 1

        # Quick image corruption check
        try:
            img = cv2.imread(str(img_path))
            if img is None:
                corrupt_images.append(img_path.name)
        except Exception:
            corrupt_images.append(img_path.name)

    stats = {
        "split": split,
        "images": len(img_files),
        "labels": valid_labels,
        "missing_labels": len(missing_labels),
        "empty_labels": len(empty_labels),
        "corrupt_images": len(corrupt_images),
        "total_dots": total_dots,
        "avg_dots_per_image": round(total_dots / max(valid_labels, 1), 1),
    }

    if missing_labels[:3]:
        stats["missing_examples"] = missing_labels[:3]
    if empty_labels[:3]:
        stats["empty_examples"] = empty_labels[:3]
    if corrupt_images[:3]:
        stats["corrupt_examples"] = corrupt_images[:3]

    return stats


def draw_boxes(img: np.ndarray, label_path: Path) -> np.ndarray:
    """Draw YOLO bounding boxes on an image."""
    h, w = img.shape[:2]
    if not label_path.exists():
        return img

    for line in label_path.read_text().strip().split("\n"):
        parts = line.strip().split()
        if len(parts) != 5:
            continue
        try:
            _, cx, cy, bw, bh = map(float, parts)
            x1 = int((cx - bw / 2) * w)
            y1 = int((cy - bh / 2) * h)
            x2 = int((cx + bw / 2) * w)
            y2 = int((cy + bh / 2) * h)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 1)
        except (ValueError, TypeError):
            continue
    return img


def render_sample_grid(dataset_dir: Path, n: int = 12, split: str = "train") -> str:
    """Render a grid of sample images with bboxes. Returns saved path."""
    img_dir = dataset_dir / "images" / split
    lbl_dir = dataset_dir / "labels" / split

    image_exts = {".jpg", ".jpeg", ".png"}
    all_images = [f for f in img_dir.iterdir() if f.suffix.lower() in image_exts]
    if not all_images:
        return ""

    samples = random.sample(all_images, min(n, len(all_images)))
    cell_w, cell_h = 320, 240
    cols = 4
    rows = (len(samples) + cols - 1) // cols

    grid = np.zeros((rows * cell_h, cols * cell_w, 3), dtype=np.uint8)

    for idx, img_path in enumerate(samples):
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        lbl_path = lbl_dir / (img_path.stem + ".txt")
        img = draw_boxes(img, lbl_path)
        img = cv2.resize(img, (cell_w, cell_h))

        row = idx // cols
        col = idx % cols
        grid[row * cell_h:(row + 1) * cell_h, col * cell_w:(col + 1) * cell_w] = img

    out_path = dataset_dir / "sample_grid.jpg"
    cv2.imwrite(str(out_path), grid, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return str(out_path)


def print_stats(all_stats: list):
    print("\n" + "=" * 65)
    print(" DATASET VERIFICATION REPORT")
    print("=" * 65)
    total_imgs = 0
    total_dots = 0
    issues = []

    for s in all_stats:
        split = s["split"].upper()
        print(f"\n [{split}]")
        print(f"   Images:          {s['images']}")
        print(f"   Labeled:         {s['labels']}")
        print(f"   Total dots:      {s['total_dots']}")
        print(f"   Avg dots/image:  {s.get('avg_dots_per_image', 0)}")

        if s["missing_labels"] > 0:
            print(f"   âš   Missing labels: {s['missing_labels']}")
            issues.append(f"{split}: {s['missing_labels']} missing labels")
        if s["empty_labels"] > 0:
            print(f"   âš   Empty labels:   {s['empty_labels']}")
            issues.append(f"{split}: {s['empty_labels']} empty labels")
        if s["corrupt_images"] > 0:
            print(f"   âš   Corrupt images: {s['corrupt_images']}")
            issues.append(f"{split}: {s['corrupt_images']} corrupt images")

        total_imgs += s["images"]
        total_dots += s["total_dots"]

    print(f"\n TOTAL: {total_imgs} images, {total_dots} dot annotations")

    if issues:
        print("\n âš   Issues found:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("\n âœ“ No issues found. Dataset looks good!")

    if total_imgs < 200:
        print("\n âš   Warning: Less than 200 images total. Model may underfit.")
        print("    Run generate_synthetic.py --count 500 to add more data.")
    elif total_imgs >= 500:
        print("\n âœ“ Dataset size looks good for training!")

    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Verify Braille YOLO dataset")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET),
                        help="YOLO dataset directory")
    parser.add_argument("--samples", type=int, default=12,
                        help="Number of sample images to render in grid")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset)
    if not dataset_dir.exists():
        print(f"Dataset directory not found: {dataset_dir}")
        print("Run merge_and_split.py first.")
        return

    all_stats = []
    for split in ["train", "val", "test"]:
        s = check_split(dataset_dir, split)
        all_stats.append(s)

    print_stats(all_stats)

    # Render sample grid
    print("\nRendering sample grid from train split...")
    grid_path = render_sample_grid(dataset_dir, n=args.samples)
    if grid_path:
        print(f"  âœ“ Sample grid saved: {grid_path}")
        print("  Open it to visually inspect dot annotations.")
    else:
        print("  No images found to render.")

    print("\nNext step: python training/scripts/train.py")


if __name__ == "__main__":
    main()
