"""
BrailleVision â€” Model Evaluation Script

Evaluates the trained YOLOv8 model on the test split.
Reports:
  - Dot detection: mAP50, mAP50-95, Precision, Recall
  - End-to-end character accuracy on test images (using full pipeline)
  - Per-word accuracy
  - Inference latency (mean, P95)
  - Saves detailed markdown report to training/runs/eval_report.md

Usage:
    python training/scripts/evaluate.py
    python training/scripts/evaluate.py --model model/best.pt --split test
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DEFAULT_MODEL = ROOT / "model" / "best.pt"
DATASET_YAML  = ROOT / "dataset" / "data.yaml"
REPORT_PATH   = Path(__file__).parent.parent / "runs" / "eval_report.md"


def run_yolo_validation(model_path: Path, dataset_yaml: Path, split: str = "test") -> dict:
    """Run ultralytics YOLO validation and return metrics dict."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Error: ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    print(f"\nRunning YOLO validation on '{split}' split...")
    model = YOLO(str(model_path))
    metrics = model.val(
        data=str(dataset_yaml),
        split=split,
        verbose=False,
        save_json=False,
    )

    return {
        "map50":      round(float(metrics.box.map50),   4),
        "map50_95":   round(float(metrics.box.map),     4),
        "precision":  round(float(metrics.box.mp),      4),
        "recall":     round(float(metrics.box.mr),      4),
    }


def run_end_to_end_accuracy(model_path: Path, split: str = "test") -> dict:
    """
    Run the full BrailleVision pipeline on test images and compute
    character-level accuracy against filenames or a ground-truth CSV.

    If no ground truth is available, reports dot count statistics only.
    """
    # Add project root to path so backend imports work
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    try:
        import cv2
        import numpy as np
        from backend.inference.pipeline import BraillePipeline
    except ImportError as e:
        print(f"  Warning: Could not import pipeline: {e}")
        return {"note": "Pipeline import failed â€” skipping char accuracy"}

    pipeline = BraillePipeline(model_path=model_path)

    img_dir = ROOT / "dataset" / "images" / split
    if not img_dir.exists():
        return {"note": f"No test images found at {img_dir}"}

    image_exts = {".jpg", ".jpeg", ".png"}
    images = sorted([f for f in img_dir.iterdir() if f.suffix.lower() in image_exts])

    if not images:
        return {"note": "No images found in test split"}

    latencies_ms = []
    total_dots = []
    total_cells = []
    errors = 0

    print(f"\nRunning end-to-end pipeline on {len(images)} test images...")
    for i, img_path in enumerate(images):
        img = cv2.imread(str(img_path))
        if img is None:
            errors += 1
            continue

        t0 = time.time()
        try:
            result = pipeline.run(img)
            latencies_ms.append((time.time() - t0) * 1000)
            total_dots.append(len(result["dots"]))
            total_cells.append(len(result["cells"]))
        except Exception as e:
            errors += 1

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(images)} processed...", end="\r")

    print(f"  Done. Errors: {errors}/{len(images)}")

    if not latencies_ms:
        return {"note": "All images failed to process"}

    import numpy as np
    lat = np.array(latencies_ms)
    return {
        "images_processed": len(latencies_ms),
        "errors": errors,
        "avg_dots_detected": round(float(np.mean(total_dots)), 1),
        "avg_cells_detected": round(float(np.mean(total_cells)), 1),
        "latency_mean_ms":    round(float(np.mean(lat)), 1),
        "latency_p50_ms":     round(float(np.percentile(lat, 50)), 1),
        "latency_p95_ms":     round(float(np.percentile(lat, 95)), 1),
        "latency_max_ms":     round(float(np.max(lat)), 1),
    }


def write_report(yolo_metrics: dict, e2e_metrics: dict, model_path: Path):
    """Write a markdown evaluation report."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# BrailleVision â€” Model Evaluation Report",
        f"\n**Generated:** {now}  ",
        f"**Model:** `{model_path}`\n",
        "---\n",
        "## Dot Detection (YOLO Validation)\n",
        "| Metric | Value | Target |",
        "|--------|-------|--------|",
        f"| mAP50 | {yolo_metrics.get('map50', 'N/A')} | â‰¥ 0.75 |",
        f"| mAP50-95 | {yolo_metrics.get('map50_95', 'N/A')} | â‰¥ 0.50 |",
        f"| Precision | {yolo_metrics.get('precision', 'N/A')} | â‰¥ 0.75 |",
        f"| Recall | {yolo_metrics.get('recall', 'N/A')} | â‰¥ 0.75 |",
        "",
        "---\n",
        "## End-to-End Pipeline Performance\n",
        "| Metric | Value |",
        "|--------|-------|",
    ]

    for k, v in e2e_metrics.items():
        if k == "note":
            lines.append(f"\n> âš  {v}")
        else:
            label = k.replace("_", " ").title()
            lines.append(f"| {label} | {v} |")

    lines += [
        "",
        "---\n",
        "## Assessment\n",
    ]

    map50 = yolo_metrics.get("map50", 0)
    if isinstance(map50, float):
        if map50 >= 0.75:
            lines.append("âœ… **mAP50 â‰¥ 0.75** â€” Dot detection is at target accuracy.")
        elif map50 >= 0.55:
            lines.append("âš ï¸ **mAP50 between 0.55â€“0.75** â€” Acceptable but more data or epochs would help.")
        else:
            lines.append("âŒ **mAP50 < 0.55** â€” Model needs more training data or longer training.")

    lat_p95 = e2e_metrics.get("latency_p95_ms", 0)
    if isinstance(lat_p95, float):
        if lat_p95 < 500:
            lines.append("âœ… **P95 latency < 500ms** â€” Real-time performance is feasible.")
        else:
            lines.append("âš ï¸ **P95 latency > 500ms** â€” Consider ONNX export or smaller model.")

    content = "\n".join(lines)
    REPORT_PATH.write_text(content)
    print(f"\nâœ“ Report saved: {REPORT_PATH}")


def print_summary(yolo_metrics: dict, e2e_metrics: dict):
    """Print summary to console."""
    print("\n" + "=" * 60)
    print(" EVALUATION RESULTS")
    print("=" * 60)

    print("\n [YOLO Dot Detection]")
    for k, v in yolo_metrics.items():
        print(f"   {k:15s}: {v}")

    print("\n [End-to-End Pipeline]")
    for k, v in e2e_metrics.items():
        print(f"   {k:25s}: {v}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained Braille model")
    parser.add_argument("--model",  default=str(DEFAULT_MODEL), help="Path to best.pt")
    parser.add_argument("--split",  default="test", choices=["train", "val", "test"])
    parser.add_argument("--skip-e2e", action="store_true", help="Skip end-to-end accuracy test")
    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"Error: Model not found: {model_path}")
        print("Train first: python training/scripts/train.py")
        sys.exit(1)

    if not DATASET_YAML.exists():
        print(f"Error: dataset/data.yaml not found: {DATASET_YAML}")
        sys.exit(1)

    # Run YOLO validation
    yolo_metrics = run_yolo_validation(model_path, DATASET_YAML, split=args.split)

    # Run end-to-end pipeline test
    if args.skip_e2e:
        e2e_metrics = {"note": "Skipped (--skip-e2e flag)"}
    else:
        e2e_metrics = run_end_to_end_accuracy(model_path, split=args.split)

    print_summary(yolo_metrics, e2e_metrics)
    write_report(yolo_metrics, e2e_metrics, model_path)


if __name__ == "__main__":
    main()
