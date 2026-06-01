"""
BrailleVision — YOLOv8 Training Script
Trains YOLOv8n to detect Braille dots. Works locally and on Google Colab.

Usage:
    python training/scripts/train.py
    python training/scripts/train.py --epochs 100 --device 0
    python training/scripts/train.py --resume
"""

import argparse
import shutil
import sys
from pathlib import Path


# ── Smart ROOT detection ───────────────────────────────────────────────────────
# Walk up from this file's location until we find the project root
# (identified by having a 'dataset' or 'training' folder).
# This prevents the triple-nesting bug when Colab extracts nested zips.
def find_project_root() -> Path:
    candidate = Path(__file__).resolve()
    for _ in range(8):  # max 8 levels up
        candidate = candidate.parent
        if (candidate / "dataset").exists() or (candidate / "training" / "scripts").exists():
            return candidate
    # Fallback: 3 levels up from this file
    return Path(__file__).resolve().parent.parent.parent

ROOT        = find_project_root()
DATASET_YAML = ROOT / "dataset" / "data.yaml"
RUNS_DIR    = ROOT / "training" / "runs"
MODEL_OUT   = ROOT / "model" / "best.pt"
MODEL_ONNX  = ROOT / "model" / "model.onnx"


def detect_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
            return "0"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            print("  Apple MPS detected")
            return "mps"
        print("  No GPU — using CPU (slow)")
        return "cpu"
    except ImportError:
        return "cpu"


def train(epochs: int, device: str, batch: int, imgsz: int, resume: bool, name: str):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    if not DATASET_YAML.exists():
        print(f"ERROR: data.yaml not found at {DATASET_YAML}")
        print("Run: python training/scripts/download_datasets.py")
        print("     python training/scripts/generate_synthetic.py --count 500")
        print("     python training/scripts/merge_and_split.py")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(" BrailleVision YOLOv8 Training")
    print("=" * 60)
    print(f"  Project root: {ROOT}")
    print(f"  Dataset:      {DATASET_YAML}")
    print(f"  Device:       {device}")
    print(f"  Epochs:       {epochs}")
    print(f"  Batch:        {batch}")
    print(f"  Img size:     {imgsz}")
    print(f"  Output:       {RUNS_DIR / name}")
    print("=" * 60 + "\n")

    model = YOLO("yolov8n.pt")

    # ── All valid YOLOv8 training arguments ──────────────────────────────────
    # Note: 'blur' is NOT a valid training arg (it's a solutions command).
    # Use only documented args from https://docs.ultralytics.com/usage/cfg/
    train_args = {
        # Core
        "data":           str(DATASET_YAML),
        "epochs":         epochs,
        "imgsz":          imgsz,
        "batch":          batch,
        "device":         device,
        "project":        str(RUNS_DIR),
        "name":           name,
        "exist_ok":       True,

        # Optimiser
        "lr0":            0.01,
        "lrf":            0.01,
        "momentum":       0.937,
        "weight_decay":   0.0005,
        "warmup_epochs":  3,

        # Augmentation (tuned for Braille)
        "hsv_h":          0.015,   # hue jitter
        "hsv_s":          0.3,     # saturation jitter
        "hsv_v":          0.5,     # brightness jitter (important: uneven lighting)
        "degrees":        10.0,    # rotation (mobile scan wobble)
        "translate":      0.1,
        "scale":          0.5,     # zoom variation
        "flipud":         0.0,     # NO vertical flip — Braille is directional
        "fliplr":         0.5,     # horizontal flip is fine
        "mosaic":         1.0,
        "close_mosaic":   10,      # disable mosaic for last 10 epochs

        # Early stopping & saving
        "patience":       25,
        "save":           True,
        "verbose":        True,
    }

    if resume:
        last_ckpt = RUNS_DIR / name / "weights" / "last.pt"
        if last_ckpt.exists():
            print(f"Resuming from: {last_ckpt}")
            model = YOLO(str(last_ckpt))
            train_args["resume"] = True
        else:
            print(f"No checkpoint at {last_ckpt} — starting fresh")

    results = model.train(**train_args)

    # ── Copy best weights to model/ ──────────────────────────────────────────
    best_pt = RUNS_DIR / name / "weights" / "best.pt"
    if best_pt.exists():
        MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best_pt, MODEL_OUT)
        print(f"\nBest weights -> {MODEL_OUT}")

        # Export ONNX for fast CPU inference
        print("Exporting ONNX...")
        try:
            YOLO(str(best_pt)).export(format="onnx", imgsz=imgsz, simplify=True)
            onnx_src = best_pt.parent / "best.onnx"
            if onnx_src.exists():
                shutil.copy2(onnx_src, MODEL_ONNX)
                print(f"ONNX model -> {MODEL_ONNX}")
        except Exception as e:
            print(f"ONNX export skipped: {e}")
    else:
        print(f"WARNING: best.pt not found at {best_pt}")

    # ── Print metrics ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(" TRAINING COMPLETE")
    print("=" * 60)
    try:
        m = results.results_dict
        print(f"  mAP50:     {m.get('metrics/mAP50(B)', 'N/A')}")
        print(f"  mAP50-95:  {m.get('metrics/mAP50-95(B)', 'N/A')}")
        print(f"  Precision: {m.get('metrics/precision(B)', 'N/A')}")
        print(f"  Recall:    {m.get('metrics/recall(B)', 'N/A')}")
    except Exception:
        pass
    print(f"  Weights: {MODEL_OUT}")
    print("\nNext: python training/scripts/evaluate.py")


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8n for Braille dot detection")
    parser.add_argument("--epochs", type=int,  default=100,              help="Training epochs")
    parser.add_argument("--batch",  type=int,  default=16,               help="Batch size (use 8 for CPU)")
    parser.add_argument("--imgsz",  type=int,  default=640,              help="Input image size")
    parser.add_argument("--device", type=str,  default="",               help="Device: 0 (GPU), cpu, mps")
    parser.add_argument("--name",   type=str,  default="braille_dot_v1", help="Run name")
    parser.add_argument("--resume", action="store_true",                  help="Resume last checkpoint")
    args = parser.parse_args()

    device = args.device if args.device else detect_device()
    batch  = args.batch if device != "cpu" else min(args.batch, 8)

    train(
        epochs=args.epochs,
        device=device,
        batch=batch,
        imgsz=args.imgsz,
        resume=args.resume,
        name=args.name,
    )


if __name__ == "__main__":
    main()
