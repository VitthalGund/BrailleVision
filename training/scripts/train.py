"""
BrailleVision â€” YOLOv8 Training Script (Local)

Trains a YOLOv8n model to detect Braille dots.
Auto-detects CUDA / MPS / CPU.
On completion, copies best.pt to model/best.pt.

Usage:
    python training/scripts/train.py
    python training/scripts/train.py --epochs 50 --device cpu
    python training/scripts/train.py --resume  (continue from last checkpoint)
"""

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DATASET_YAML = ROOT / "dataset" / "data.yaml"
CONFIG_YAML  = Path(__file__).parent.parent / "configs" / "yolov8_braille.yaml"
RUNS_DIR     = Path(__file__).parent.parent / "runs"
MODEL_OUT    = ROOT / "model" / "best.pt"
MODEL_ONNX   = ROOT / "model" / "model.onnx"


def detect_device() -> str:
    """Auto-detect best available training device."""
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            print(f"  GPU detected: {name}")
            return "0"  # First CUDA device
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            print("  Apple MPS detected (M-series chip)")
            return "mps"
        else:
            print("  No GPU found â€” using CPU (training will be slow)")
            return "cpu"
    except ImportError:
        print("  PyTorch not found â€” using CPU")
        return "cpu"


def load_config(config_path: Path) -> dict:
    """Load YAML hyperparameter config."""
    try:
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"  Warning: Could not load config ({e}) â€” using defaults")
        return {}


def train(
    epochs: int,
    device: str,
    batch: int,
    imgsz: int,
    resume: bool,
    name: str,
):
    """Run YOLOv8 training."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Error: ultralytics not installed.")
        print("Install with: pip install ultralytics")
        sys.exit(1)

    if not DATASET_YAML.exists():
        print(f"Error: dataset/data.yaml not found at {DATASET_YAML}")
        print("Run these first:")
        print("  python training/scripts/download_datasets.py")
        print("  python training/scripts/generate_synthetic.py --count 500")
        print("  python training/scripts/merge_and_split.py")
        sys.exit(1)

    # Load hyperparameter overrides from config
    cfg = load_config(CONFIG_YAML)

    print("\n" + "=" * 60)
    print(" BrailleVision YOLOv8 Training")
    print("=" * 60)
    print(f"  Dataset:  {DATASET_YAML}")
    print(f"  Device:   {device}")
    print(f"  Epochs:   {epochs}")
    print(f"  Batch:    {batch}")
    print(f"  Img size: {imgsz}")
    print(f"  Output:   {RUNS_DIR / name}")
    print("=" * 60 + "\n")

    # Start from pretrained YOLOv8n (best accuracy/speed tradeoff for dots)
    model = YOLO("yolov8n.pt")

    train_args = {
        # Core
        "data":       str(DATASET_YAML),
        "epochs":     epochs,
        "imgsz":      imgsz,
        "batch":      batch,
        "device":     device,
        "project":    str(RUNS_DIR),
        "name":       name,
        "exist_ok":   True,

        # Optimiser
        "lr0":        cfg.get("lr0", 0.01),
        "lrf":        cfg.get("lrf", 0.01),
        "momentum":   cfg.get("momentum", 0.937),
        "weight_decay": cfg.get("weight_decay", 0.0005),
        "warmup_epochs": cfg.get("warmup_epochs", 3),

        # Augmentation
        "hsv_h":      cfg.get("hsv_h", 0.015),
        "hsv_s":      cfg.get("hsv_s", 0.3),
        "hsv_v":      cfg.get("hsv_v", 0.5),   # high for Braille lighting variation
        "degrees":    cfg.get("degrees", 10.0),
        "translate":  cfg.get("translate", 0.1),
        "scale":      cfg.get("scale", 0.5),
        "flipud":     cfg.get("flipud", 0.0),   # NO vertical flip (Braille has direction)
        "fliplr":     cfg.get("fliplr", 0.5),
        "mosaic":     cfg.get("mosaic", 1.0),
        "blur":       cfg.get("blur", 2),

        # Regularisation
        "patience":   cfg.get("patience", 25),  # early stopping
        "save":       True,
        "verbose":    True,
    }

    if resume:
        # Find last checkpoint
        last_ckpt = RUNS_DIR / name / "weights" / "last.pt"
        if last_ckpt.exists():
            print(f"Resuming from: {last_ckpt}")
            model = YOLO(str(last_ckpt))
            train_args["resume"] = True
        else:
            print(f"No checkpoint found at {last_ckpt}. Starting fresh.")

    results = model.train(**train_args)

    # --- Post-training ---
    best_pt = RUNS_DIR / name / "weights" / "best.pt"

    if best_pt.exists():
        MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best_pt, MODEL_OUT)
        print(f"\nâœ“ Best weights copied to: {MODEL_OUT}")

        # Export to ONNX for faster CPU inference
        print("\nExporting to ONNX...")
        try:
            export_model = YOLO(str(best_pt))
            export_model.export(format="onnx", imgsz=imgsz, simplify=True)
            onnx_src = best_pt.parent / "best.onnx"
            if onnx_src.exists():
                shutil.copy2(onnx_src, MODEL_ONNX)
                print(f"âœ“ ONNX model saved to: {MODEL_ONNX}")
        except Exception as e:
            print(f"  Warning: ONNX export failed: {e}")
    else:
        print(f"\nâš   best.pt not found at {best_pt}")

    # Print final metrics
    print("\n" + "=" * 60)
    print(" TRAINING COMPLETE")
    print("=" * 60)
    try:
        metrics = results.results_dict
        print(f"  mAP50:       {metrics.get('metrics/mAP50(B)', 'N/A'):.4f}")
        print(f"  mAP50-95:    {metrics.get('metrics/mAP50-95(B)', 'N/A'):.4f}")
        print(f"  Precision:   {metrics.get('metrics/precision(B)', 'N/A'):.4f}")
        print(f"  Recall:      {metrics.get('metrics/recall(B)', 'N/A'):.4f}")
    except Exception:
        pass
    print(f"  Best weights: {MODEL_OUT}")
    print("\nNext step: python training/scripts/evaluate.py")


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8n for Braille dot detection")
    parser.add_argument("--epochs",  type=int, default=100, help="Training epochs (default: 100)")
    parser.add_argument("--batch",   type=int, default=16,  help="Batch size (default: 16, use 8 for CPU)")
    parser.add_argument("--imgsz",   type=int, default=640, help="Input image size (default: 640)")
    parser.add_argument("--device",  type=str, default="",  help="Device: 0 (GPU), cpu, mps (auto if empty)")
    parser.add_argument("--name",    type=str, default="braille_dot_v1", help="Run name")
    parser.add_argument("--resume",  action="store_true", help="Resume from last checkpoint")
    args = parser.parse_args()

    device = args.device if args.device else detect_device()
    # CPU: reduce batch to avoid OOM
    batch = args.batch if device != "cpu" else min(args.batch, 8)

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
