"""
BrailleVision â€” Preprocessing Diagnostic

Visually shows each stage of the OpenCV preprocessing pipeline for a given image.
Helps tune preprocessing parameters for best dot visibility.

Outputs a 6-panel side-by-side comparison image.

Usage:
    python training/scripts/test_preprocessing.py --image sample_inputs/test_braille.jpg
    python training/scripts/test_preprocessing.py --image my_braille.jpg --output debug_output.jpg
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).parent.parent.parent


def run_preprocessing_stages(img: np.ndarray) -> list[tuple[str, np.ndarray]]:
    """Run each preprocessing stage and return (name, image) pairs."""
    stages = []
    stages.append(("1. Original", img.copy()))

    # Stage 1: Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    stages.append(("2. Grayscale", cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)))

    # Stage 2: CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    stages.append(("3. CLAHE Enhanced", cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)))

    # Stage 3: Gaussian blur
    blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
    stages.append(("4. Gaussian Blur", cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)))

    # Stage 4: Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=11, C=2
    )
    stages.append(("5. Adaptive Threshold", cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)))

    # Stage 5: Morphological closing
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    stages.append(("6. Morphological Close", cv2.cvtColor(morph, cv2.COLOR_GRAY2BGR)))

    # Also show shadow removal
    kernel_lg = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    bg = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel_lg)
    diff = cv2.absdiff(bg, gray)
    shadow_removed = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
    stages.append(("Shadow Removed", cv2.cvtColor(shadow_removed, cv2.COLOR_GRAY2BGR)))

    return stages


def make_comparison_grid(stages: list[tuple[str, np.ndarray]], target_w: int = 1920) -> np.ndarray:
    """Arrange stages into a grid image with labels."""
    n = len(stages)
    cols = 3
    rows = (n + cols - 1) // cols

    cell_w = target_w // cols
    # Compute cell_h from first image aspect ratio
    h0, w0 = stages[0][1].shape[:2]
    cell_h = int(cell_w * h0 / w0)

    grid = np.zeros((rows * cell_h, cols * cell_w, 3), dtype=np.uint8)

    for i, (name, stage_img) in enumerate(stages):
        row = i // cols
        col = i % cols
        panel = cv2.resize(stage_img, (cell_w, cell_h))

        # Draw label banner
        cv2.rectangle(panel, (0, 0), (cell_w, 32), (30, 30, 30), -1)
        cv2.putText(panel, name, (8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1, cv2.LINE_AA)

        grid[row * cell_h:(row + 1) * cell_h, col * cell_w:(col + 1) * cell_w] = panel

    return grid


def main():
    parser = argparse.ArgumentParser(description="Visualise preprocessing pipeline stages")
    parser.add_argument("--image", required=True, help="Input Braille image path")
    parser.add_argument("--output", default="",
                        help="Output path (default: <input_stem>_preprocessed.jpg)")
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        # Try relative to project root
        img_path = ROOT / args.image
    if not img_path.exists():
        print(f"Error: Image not found: {args.image}")
        return

    print(f"Loading: {img_path}")
    img = cv2.imread(str(img_path))
    if img is None:
        print("Error: Could not load image (unsupported format or corrupt)")
        return

    print("Running preprocessing stages...")
    stages = run_preprocessing_stages(img)

    print("Building comparison grid...")
    grid = make_comparison_grid(stages)

    out_path = args.output or str(img_path.parent / f"{img_path.stem}_preprocessed.jpg")
    cv2.imwrite(out_path, grid, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"\nâœ“ Saved: {out_path}")
    print("  Open the image to compare preprocessing stages.")

    # Print blob count at each stage
    for name, stage_img in stages:
        gray_s = cv2.cvtColor(stage_img, cv2.COLOR_BGR2GRAY) if len(stage_img.shape) == 3 else stage_img
        params = cv2.SimpleBlobDetector_Params()
        params.filterByArea = True
        params.minArea = 8
        params.maxArea = 800
        detector = cv2.SimpleBlobDetector_create(params)
        kps = detector.detect(gray_s)
        print(f"  {name}: {len(kps)} blobs detected")


if __name__ == "__main__":
    main()
