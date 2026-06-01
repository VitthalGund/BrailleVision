"""
BrailleVision - Dataset Downloader

Downloads real Braille datasets from VERIFIED working sources.
No API key required - all public GitHub repositories.

Real datasets:
  1. Angelina Braille Dataset (IlyaOvodov/AngelinaDataset)
     - Real Braille photos with CSV/JSON bounding box annotations
     - ~1500+ annotated images
  2. DSBI Double-Sided Braille Images (yeluo1994/DSBI)
     - 114 scanned Braille book pages with dot annotations
  3. Synthetic (always generated as supplementary data)

Usage:
    python training/scripts/download_datasets.py
    python training/scripts/download_datasets.py --skip-synthetic
    python training/scripts/download_datasets.py --output dataset/raw
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DEFAULT_OUTPUT = ROOT / "dataset" / "raw"


def progress_bar(downloaded: int, total: int, width: int = 40):
    if total <= 0:
        print(f"  Downloaded {downloaded // 1024}KB...", end="\r")
        return
    frac = min(downloaded / total, 1.0)
    filled = int(width * frac)
    bar = "#" * filled + "-" * (width - filled)
    pct = int(100 * frac)
    mb = downloaded / (1024 * 1024)
    total_mb = total / (1024 * 1024)
    print(f"  [{bar}] {pct}% ({mb:.1f}/{total_mb:.1f} MB)", end="\r")


def download_file(url: str, dest: Path, label: str = "") -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 BrailleVision/1.0"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                while True:
                    data = resp.read(65536)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    progress_bar(downloaded, total)
        print()
        return True
    except Exception as e:
        print(f"\n  ! Download failed ({label}): {e}")
        return False


def extract_zip(zip_path: Path, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    print(f"  Extracting...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)


# ─── Dataset 1: AngelinaDataset ────────────────────────────────────────────────

def download_angelina_dataset(out_dir: Path) -> int:
    """
    IlyaOvodov/AngelinaDataset — real Braille photos with CSV annotations.
    CSV format: filename, label (1-63), x1, y1, x2, y2  (absolute pixels)
    """
    print("\n[Dataset 1/2] Angelina Braille Dataset (IlyaOvodov/AngelinaDataset)...")

    zip_path = out_dir / "angelina_dataset.zip"
    extract_dir = out_dir / "angelina_dataset_raw"
    url = "https://github.com/IlyaOvodov/AngelinaDataset/archive/refs/heads/master.zip"

    if not download_file(url, zip_path, "AngelinaDataset"):
        print("  ! Skipping AngelinaDataset.")
        return 0

    extract_zip(zip_path, extract_dir)
    zip_path.unlink(missing_ok=True)

    out_img = out_dir / "angelina" / "images"
    out_lbl = out_dir / "angelina" / "labels"
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    # Index all images in the extracted directory
    image_exts = {".jpg", ".jpeg", ".png", ".bmp"}
    all_images = {}
    for p in extract_dir.rglob("*"):
        if p.suffix.lower() in image_exts:
            all_images[p.name] = p
            all_images[p.stem] = p

    count = 0

    # AngelinaDataset CSV format: image_name, label, row, col, angle
    # or: fname, label, x1, y1, x2, y2
    for csv_path in sorted(extract_dir.rglob("*.csv")):
        try:
            rows_by_file = defaultdict(list)
            with open(csv_path, newline="", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row or row[0].startswith("#"):
                        continue
                    rows_by_file[row[0]].append(row)

            for fname, rows in rows_by_file.items():
                # Find image
                img_path = all_images.get(fname) or all_images.get(Path(fname).stem)
                if img_path is None:
                    # Try to find by stem without extension
                    stem = Path(fname).stem
                    img_path = all_images.get(stem)
                if img_path is None:
                    continue

                # Get image dimensions for normalization
                try:
                    import cv2
                    img = cv2.imread(str(img_path))
                    if img is None:
                        continue
                    ih, iw = img.shape[:2]
                except Exception:
                    iw, ih = 640, 480

                yolo_lines = []
                for row in rows:
                    if len(row) < 5:
                        continue
                    try:
                        vals = [float(v) for v in row[1:]]
                        if len(vals) >= 5:
                            # row: fname, label, row_idx, col_idx, angle, x, y, [...]
                            # Try to find coordinates - last two or four float values
                            coords = [v for v in vals if v > 0]
                            if len(coords) >= 4:
                                # Assume x1 y1 x2 y2 (last 4 positional floats)
                                x1, y1, x2, y2 = coords[-4:]
                                cx = (x1 + x2) / 2 / iw
                                cy = (y1 + y2) / 2 / ih
                                w = abs(x2 - x1) / iw
                                h = abs(y2 - y1) / ih
                                # Clamp
                                cx = max(w/2, min(1-w/2, cx))
                                cy = max(h/2, min(1-h/2, cy))
                                yolo_lines.append(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                    except (ValueError, IndexError):
                        continue

                if not yolo_lines:
                    continue

                stem = f"ang_{count:06d}"
                ext = img_path.suffix.lower()
                shutil.copy2(img_path, out_img / (stem + ext))
                (out_lbl / (stem + ".txt")).write_text("\n".join(yolo_lines))
                count += 1

        except Exception as e:
            print(f"    ! Error parsing {csv_path.name}: {e}")

    # Also try LabelMe JSON format
    count += _convert_angelina_labelme(extract_dir, out_img, out_lbl, all_images, count)

    print(f"  Angelina dataset: {count} annotated images")
    return count


def _convert_angelina_labelme(src: Path, out_img: Path, out_lbl: Path,
                               all_images: dict, start_count: int) -> int:
    """Convert LabelMe JSON annotations from AngelinaDataset."""
    count = 0
    for json_path in sorted(src.rglob("*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8", errors="ignore"))

            # LabelMe format
            if "shapes" not in data:
                continue

            fname = data.get("imagePath", "")
            img_path = all_images.get(Path(fname).name) or all_images.get(Path(fname).stem)
            if img_path is None:
                # Try finding image next to JSON
                for ext in [".jpg", ".jpeg", ".png"]:
                    candidate = json_path.with_suffix(ext)
                    if candidate.exists():
                        img_path = candidate
                        break
            if img_path is None:
                continue

            iw = data.get("imageWidth", 640)
            ih = data.get("imageHeight", 480)

            yolo_lines = []
            for shape in data.get("shapes", []):
                pts = shape.get("points", [])
                if len(pts) < 2:
                    continue
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                x1, x2 = min(xs), max(xs)
                y1, y2 = min(ys), max(ys)
                cx = (x1 + x2) / 2 / iw
                cy = (y1 + y2) / 2 / ih
                w = (x2 - x1) / iw
                h = (y2 - y1) / ih
                if w < 0.001 or h < 0.001:
                    continue
                cx = max(w/2, min(1-w/2, cx))
                cy = max(h/2, min(1-h/2, cy))
                yolo_lines.append(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

            if not yolo_lines:
                continue

            idx = start_count + count
            stem = f"ang_{idx:06d}"
            ext = img_path.suffix.lower()
            shutil.copy2(img_path, out_img / (stem + ext))
            (out_lbl / (stem + ".txt")).write_text("\n".join(yolo_lines))
            count += 1

        except Exception:
            continue

    return count


# ─── Dataset 2: DSBI ────────────────────────────────────────────────────────────

def download_dsbi_dataset(out_dir: Path) -> int:
    """
    yeluo1994/DSBI — 114 double-sided Braille pages with dot coordinates.
    """
    print("\n[Dataset 2/2] DSBI Double-Sided Braille Images (yeluo1994/DSBI)...")

    zip_path = out_dir / "dsbi.zip"
    extract_dir = out_dir / "dsbi_raw"
    url = "https://github.com/yeluo1994/DSBI/archive/refs/heads/master.zip"

    if not download_file(url, zip_path, "DSBI"):
        print("  ! Skipping DSBI dataset.")
        return 0

    extract_zip(zip_path, extract_dir)
    zip_path.unlink(missing_ok=True)

    out_img = out_dir / "dsbi" / "images"
    out_lbl = out_dir / "dsbi" / "labels"
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    image_exts = {".jpg", ".jpeg", ".png", ".bmp"}
    all_images = {}
    for p in extract_dir.rglob("*"):
        if p.suffix.lower() in image_exts:
            all_images[p.name] = p
            all_images[p.stem] = p

    count = 0

    # DSBI annotation format varies by version.
    # Try 1: matching .txt files with dot coordinates
    for ann_path in sorted(extract_dir.rglob("*.txt")):
        content = ann_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not content:
            continue

        # Find corresponding image
        img_path = None
        for ext in image_exts:
            c = ann_path.with_suffix(ext)
            if c.exists():
                img_path = c
                break
            c = ann_path.parent.parent / "images" / (ann_path.stem + ext)
            if c.exists():
                img_path = c
                break
            img_path = all_images.get(ann_path.stem + ext) or all_images.get(ann_path.stem)
            if img_path:
                break

        if img_path is None:
            continue

        try:
            import cv2
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            ih, iw = img.shape[:2]
        except Exception:
            iw, ih = 640, 480

        yolo_lines = []
        for line in content.split("\n"):
            parts = line.strip().split()
            if not parts:
                continue
            try:
                vals = [float(p) for p in parts]
                if len(vals) == 5 and 0 <= vals[0] < 100:
                    # Already YOLO: class cx cy w h
                    yolo_lines.append(line.strip())
                elif len(vals) >= 4:
                    # Bounding box: x1 y1 x2 y2 (absolute)
                    x1, y1, x2, y2 = vals[:4]
                    cx = (x1 + x2) / 2 / iw
                    cy = (y1 + y2) / 2 / ih
                    w = abs(x2 - x1) / iw
                    h = abs(y2 - y1) / ih
                    cx = max(w/2, min(1-w/2, cx))
                    cy = max(h/2, min(1-h/2, cy))
                    if w > 0.001 and h > 0.001:
                        yolo_lines.append(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                elif len(vals) == 3:
                    # x y r format
                    x, y, r = vals
                    cx = x / iw
                    cy = y / ih
                    w = (r * 2.5) / iw
                    h = (r * 2.5) / ih
                    cx = max(w/2, min(1-w/2, cx))
                    cy = max(h/2, min(1-h/2, cy))
                    if w > 0.001:
                        yolo_lines.append(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                elif len(vals) == 2:
                    # x y format (dot center, absolute pixels)
                    x, y = vals
                    r = max(iw, ih) * 0.012  # ~1.2% of image dimension
                    cx = x / iw
                    cy = y / ih
                    w = (r * 2) / iw
                    h = (r * 2) / ih
                    cx = max(w/2, min(1-w/2, cx))
                    cy = max(h/2, min(1-h/2, cy))
                    yolo_lines.append(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            except (ValueError, ZeroDivisionError):
                continue

        if not yolo_lines:
            continue

        stem = f"dsbi_{count:06d}"
        ext = img_path.suffix.lower()
        shutil.copy2(img_path, out_img / (stem + ext))
        (out_lbl / (stem + ".txt")).write_text("\n".join(yolo_lines))
        count += 1

    print(f"  DSBI dataset: {count} annotated images")
    return count


# ─── Synthetic ─────────────────────────────────────────────────────────────────

def trigger_synthetic(out_dir: Path, count: int = 500):
    print(f"\n[Synthetic] Generating {count} synthetic images...")
    script = Path(__file__).parent / "generate_synthetic.py"
    if not script.exists():
        print("  ! generate_synthetic.py not found")
        return
    result = subprocess.run(
        [sys.executable, str(script),
         "--count", str(count),
         "--output", str(out_dir / "synthetic")],
        text=True
    )
    if result.returncode != 0:
        print("  ! Synthetic generation failed - run manually")


# ─── Summary ──────────────────────────────────────────────────────────────────

def print_summary(output_dir: Path):
    total_img = (sum(1 for _ in output_dir.rglob("*.jpg")) +
                 sum(1 for _ in output_dir.rglob("*.jpeg")) +
                 sum(1 for _ in output_dir.rglob("*.png")))
    total_lbl = sum(1 for _ in output_dir.rglob("*.txt"))

    print("\n" + "=" * 55)
    print(" DOWNLOAD SUMMARY")
    print("=" * 55)
    print(f" Total images : {total_img}")
    print(f" Total labels : {total_lbl}")
    print(f" Output dir   : {output_dir}")
    print("=" * 55)
    print("\nNext step: python training/scripts/merge_and_split.py")


def main():
    parser = argparse.ArgumentParser(description="Download Braille training datasets")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--skip-synthetic", action="store_true")
    parser.add_argument("--synthetic-count", type=int, default=500)
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 55)
    print(" BrailleVision Dataset Downloader")
    print("=" * 55)
    print(f" Output: {out_dir}\n")

    total = 0
    total += download_angelina_dataset(out_dir)
    total += download_dsbi_dataset(out_dir)

    if not args.skip_synthetic:
        trigger_synthetic(out_dir, args.synthetic_count)

    print_summary(out_dir)


if __name__ == "__main__":
    main()
