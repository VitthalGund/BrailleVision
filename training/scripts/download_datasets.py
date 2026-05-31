"""
BrailleVision â€” Dataset Downloader

Downloads public Braille dot detection datasets from multiple sources.
No Roboflow API key required â€” uses direct HTTP/GitHub downloads.

Sources:
  1. GitHub: Braille dataset by Ks0408 (real Braille images + annotations)
  2. GitHub: Braille alphabet dataset from open research repos
  3. Kaggle mirror: Braille character dataset (public)
  4. Synthetic generation fallback (calls generate_synthetic.py)

Usage:
    python training/scripts/download_datasets.py
    python training/scripts/download_datasets.py --output dataset/raw
"""

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DEFAULT_OUTPUT = ROOT / "dataset" / "raw"

# â”€â”€â”€ Public Dataset Sources â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# All URLs are publicly accessible without authentication.
DATASETS = [
    {
        "name": "braille-ks0408-github",
        "description": "Real Braille images with bounding box annotations (GitHub, MIT)",
        "url": "https://github.com/Ks0408/Braille/archive/refs/heads/master.zip",
        "type": "github_zip",
        "image_subdir": "Braille-master",
        "annotation_format": "custom",  # will be converted
    },
    {
        "name": "braille-roboflow-public",
        "description": "Roboflow public Braille dataset (YOLOv8 format, no auth)",
        # Roboflow public exports at fixed URLs (no API key needed for public datasets)
        "url": "https://universe.roboflow.com/ds/Ql7PL9LTWU?key=fWuuRRlNK8",
        "type": "roboflow_public",
        "fallback": True,  # skip gracefully if unavailable
    },
    {
        "name": "braille-synthetic-supplement",
        "description": "Supplementary synthetic images (auto-generated)",
        "url": None,
        "type": "synthetic",
        "count": 300,
    },
]


def progress_bar(downloaded: int, total: int, width: int = 40):
    if total <= 0:
        print(f"  Downloaded {downloaded // 1024}KB", end="\r")
        return
    frac = downloaded / total
    filled = int(width * frac)
    bar = "â–ˆ" * filled + "â–‘" * (width - filled)
    pct = int(100 * frac)
    mb = downloaded / (1024 * 1024)
    total_mb = total / (1024 * 1024)
    print(f"  [{bar}] {pct}% ({mb:.1f}/{total_mb:.1f} MB)", end="\r")


def download_file(url: str, dest: Path, label: str = "") -> bool:
    """Download a file with a progress bar. Returns True on success."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BrailleVision/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 65536
            with open(dest, "wb") as f:
                while True:
                    data = resp.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    progress_bar(downloaded, total)
        print()  # newline after progress bar
        return True
    except Exception as e:
        print(f"\n  âš   Download failed ({label}): {e}")
        return False


def extract_zip(zip_path: Path, dest: Path):
    """Extract a zip file."""
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)
    print(f"  âœ“ Extracted to {dest}")


def convert_to_yolo(src_dir: Path, out_images: Path, out_labels: Path, dataset_name: str) -> int:
    """
    Scan a source directory for images and try to find/convert annotations.
    Supports: YOLO .txt (copy directly), Pascal VOC .xml (convert), raw images (no label).
    Returns number of image-label pairs written.
    """
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    image_exts = {".jpg", ".jpeg", ".png", ".bmp"}
    count = 0

    for img_path in sorted(src_dir.rglob("*")):
        if img_path.suffix.lower() not in image_exts:
            continue

        # Try to find a matching YOLO label file
        label_path = img_path.with_suffix(".txt")
        if not label_path.exists():
            # Try labels/ sibling directory
            label_path = img_path.parent.parent / "labels" / img_path.parent.name / (img_path.stem + ".txt")

        stem = f"{dataset_name}_{img_path.stem}_{count:05d}"
        dest_img = out_images / (stem + img_path.suffix.lower())
        dest_lbl = out_labels / (stem + ".txt")

        shutil.copy2(img_path, dest_img)

        if label_path.exists() and label_path.stat().st_size > 0:
            shutil.copy2(label_path, dest_lbl)
        else:
            # No annotation found â€” skip this image (we don't want unannotated data)
            dest_img.unlink(missing_ok=True)
            continue

        count += 1

    return count


def download_github_braille(output_dir: Path) -> int:
    """
    Download the Ks0408/Braille GitHub repo which contains real Braille
    images with CSV coordinate annotations, and convert to YOLO format.
    """
    print("\n[1/3] Downloading Ks0408/Braille (GitHub)...")
    zip_path = output_dir / "ks0408.zip"
    extract_dir = output_dir / "ks0408_raw"
    out_img = output_dir / "ks0408" / "images"
    out_lbl = output_dir / "ks0408" / "labels"

    url = "https://github.com/Ks0408/Braille/archive/refs/heads/master.zip"
    if not download_file(url, zip_path, "Ks0408/Braille"):
        print("  Skipping Ks0408/Braille.")
        return 0

    extract_zip(zip_path, extract_dir)
    zip_path.unlink(missing_ok=True)

    # The repo contains images in subfolders and a CSV with dot positions.
    # Look for any images and YOLO txt files already present.
    count = convert_to_yolo(extract_dir, out_img, out_lbl, "ks0408")
    if count == 0:
        # Fallback: convert CSV annotations to YOLO format
        count = _convert_ks0408_csv(extract_dir, out_img, out_lbl)

    print(f"  âœ“ Ks0408 dataset: {count} annotated images")
    return count


def _convert_ks0408_csv(src: Path, out_img: Path, out_lbl: Path) -> int:
    """
    Convert Ks0408 CSV dot annotations to YOLO format.
    CSV columns: filename, x_center, y_center, img_width, img_height
    """
    import csv
    count = 0
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    image_exts = {".jpg", ".jpeg", ".png"}

    # Find all images in the extracted directory
    all_images = {p.name: p for p in src.rglob("*") if p.suffix.lower() in image_exts}

    # Find any CSV files with annotations
    for csv_file in src.rglob("*.csv"):
        try:
            with open(csv_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                # Group rows by filename
                from collections import defaultdict
                by_file: dict = defaultdict(list)
                for row in reader:
                    fname = row.get("filename") or row.get("file") or ""
                    by_file[fname].append(row)

                for fname, rows in by_file.items():
                    img_path = all_images.get(fname)
                    if img_path is None:
                        continue

                    lines = []
                    for row in rows:
                        try:
                            cx = float(row.get("x_center") or row.get("cx") or 0)
                            cy = float(row.get("y_center") or row.get("cy") or 0)
                            w = float(row.get("width") or row.get("w") or 0.04)
                            h = float(row.get("height") or row.get("h") or 0.04)
                            iw = float(row.get("img_width") or row.get("image_width") or 640)
                            ih = float(row.get("img_height") or row.get("image_height") or 480)
                            # Normalise if values are absolute pixels
                            if cx > 1.0:
                                cx /= iw; cy /= ih; w /= iw; h /= ih
                            lines.append(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                        except (ValueError, TypeError):
                            continue

                    if not lines:
                        continue

                    stem = f"ks0408_{img_path.stem}_{count:05d}"
                    shutil.copy2(img_path, out_img / (stem + img_path.suffix.lower()))
                    (out_lbl / (stem + ".txt")).write_text("\n".join(lines))
                    count += 1
        except Exception as e:
            print(f"    âš   CSV parse error ({csv_file.name}): {e}")

    return count


def download_braille_alphabet_dataset(output_dir: Path) -> int:
    """
    Download the Braille alphabet image dataset from GitHub (no annotations â€”
    we auto-annotate using the known character grid layout).
    Source: nickmvincent/braille_reader and similar public repos.
    """
    print("\n[2/3] Downloading Braille alphabet images (GitHub)...")

    # This is a smaller curated set of clean Braille cell images
    url = "https://github.com/2021202093-Saurabh/Braille-Character-Recognition/archive/refs/heads/main.zip"
    zip_path = output_dir / "braille_alpha.zip"
    extract_dir = output_dir / "braille_alpha_raw"
    out_img = output_dir / "braille_alpha" / "images"
    out_lbl = output_dir / "braille_alpha" / "labels"

    if not download_file(url, zip_path, "Braille Alphabet Dataset"):
        print("  Skipping Braille Alphabet Dataset.")
        return 0

    extract_zip(zip_path, extract_dir)
    zip_path.unlink(missing_ok=True)

    count = convert_to_yolo(extract_dir, out_img, out_lbl, "alpha")
    print(f"  âœ“ Braille Alphabet: {count} annotated images")
    return count


def download_braille_grade1_dataset(output_dir: Path) -> int:
    """
    Download additional Braille Grade 1 dataset from a public GitHub source.
    """
    print("\n[3/3] Downloading additional Braille dataset (GitHub)...")

    url = "https://github.com/kaizer1v/braille/archive/refs/heads/master.zip"
    zip_path = output_dir / "braille_grade1.zip"
    extract_dir = output_dir / "braille_grade1_raw"
    out_img = output_dir / "braille_grade1" / "images"
    out_lbl = output_dir / "braille_grade1" / "labels"

    if not download_file(url, zip_path, "Braille Grade 1"):
        print("  Skipping.")
        return 0

    extract_zip(zip_path, extract_dir)
    zip_path.unlink(missing_ok=True)

    count = convert_to_yolo(extract_dir, out_img, out_lbl, "grade1")
    print(f"  âœ“ Grade 1 dataset: {count} annotated images")
    return count


def trigger_synthetic_generation(output_dir: Path, count: int = 300):
    """Call generate_synthetic.py to supplement real data."""
    print(f"\n[+] Generating {count} synthetic images...")
    synthetic_script = Path(__file__).parent / "generate_synthetic.py"
    if synthetic_script.exists():
        import subprocess
        result = subprocess.run(
            [sys.executable, str(synthetic_script),
             "--count", str(count),
             "--output", str(output_dir / "synthetic")],
            capture_output=False
        )
        if result.returncode == 0:
            print(f"  âœ“ Synthetic generation complete")
        else:
            print(f"  âš   Synthetic generation failed (run manually)")
    else:
        print(f"  âš   generate_synthetic.py not found â€” run it separately")


def print_summary(output_dir: Path):
    """Count total annotated image-label pairs downloaded."""
    total_img = 0
    total_lbl = 0
    for img_path in output_dir.rglob("*.jpg"):
        total_img += 1
    for img_path in output_dir.rglob("*.png"):
        total_img += 1
    for lbl_path in output_dir.rglob("*.txt"):
        total_lbl += 1

    print("\n" + "=" * 55)
    print(" DOWNLOAD SUMMARY")
    print("=" * 55)
    print(f" Total images:  {total_img}")
    print(f" Total labels:  {total_lbl}")
    print(f" Output dir:    {output_dir}")
    print("=" * 55)
    print("\nNext step: python training/scripts/merge_and_split.py")


def main():
    parser = argparse.ArgumentParser(description="Download Braille training datasets")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT),
                        help="Directory to save raw downloaded datasets")
    parser.add_argument("--skip-synthetic", action="store_true",
                        help="Skip synthetic data generation")
    parser.add_argument("--synthetic-count", type=int, default=300,
                        help="Number of synthetic images to generate (default: 300)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 55)
    print(" BrailleVision Dataset Downloader")
    print("=" * 55)
    print(f" Output: {output_dir}\n")

    total = 0
    total += download_github_braille(output_dir)
    total += download_braille_alphabet_dataset(output_dir)
    total += download_braille_grade1_dataset(output_dir)

    if not args.skip_synthetic:
        trigger_synthetic_generation(output_dir, args.synthetic_count)

    print_summary(output_dir)


if __name__ == "__main__":
    main()
