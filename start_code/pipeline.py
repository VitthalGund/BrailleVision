"""
BrailleVision — Main Inference Pipeline

Orchestrates: OpenCV Preprocessing → YOLOv8 Dot Detection → Cell Grouping → Braille Decoding
"""

import time
import logging
from pathlib import Path

import cv2
import numpy as np
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "best.pt"
FALLBACK_MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "model.onnx"


@dataclass
class Dot:
    """A detected Braille dot."""

    x: float
    y: float
    confidence: float
    radius: float = 3.0

    @property
    def cx(self) -> float:
        return self.x

    @property
    def cy(self) -> float:
        return self.y


@dataclass
class BrailleCell:
    """A decoded Braille cell (6-dot group)."""

    dots: list[bool]  # [dot1, dot2, dot3, dot4, dot5, dot6]
    char: str  # Decoded character
    x: float  # Bounding box top-left x
    y: float  # Bounding box top-left y
    width: float
    height: float
    confidence: float

    def to_dict(self) -> dict:
        return {
            "dots": self.dots,
            "char": self.char,
            "bbox": [self.x, self.y, self.width, self.height],
            "confidence": round(self.confidence, 3),
        }


class BraillePreprocessor:
    """OpenCV-based image preprocessing for Braille dot visibility."""

    @staticmethod
    def preprocess(img: np.ndarray) -> np.ndarray:
        """
        Enhance Braille dot visibility from raw camera/image input.

        Pipeline:
          1. Grayscale → CLAHE → Gaussian blur
          2. Adaptive threshold → Morphological closing
          3. Back to 3-channel for YOLO
        """
        if img is None or img.size == 0:
            raise ValueError("preprocess: received empty/None image")

        # 1. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. CLAHE — Contrast Limited Adaptive Histogram Equalization
        # Makes Braille dots visible even under uneven/flat lighting
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 3. Slight Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)

        # 4. Adaptive thresholding — handles lighting gradients across image
        thresh = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=11,
            C=2,
        )

        # 5. Morphological closing — connects broken dot outlines
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # 6. Back to BGR for YOLO
        return cv2.cvtColor(morph, cv2.COLOR_GRAY2BGR)

    @staticmethod
    def remove_shadows(img: np.ndarray) -> np.ndarray:
        """
        Shadow removal using morphological background estimation.
        Use when directional lighting creates strong shadows under dots.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        background = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel)
        diff = cv2.absdiff(background, gray)
        normalized = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
        return normalized


class YOLODotDetector:
    """Wraps YOLOv8 for Braille dot detection."""

    def __init__(self, model_path: str | Path = MODEL_PATH):
        self.model = None
        self.model_path = Path(model_path)
        self._load_model()

    def _load_model(self):
        """Load YOLOv8 model. Falls back to ONNX if .pt unavailable."""
        try:
            from ultralytics import YOLO

            if self.model_path.exists():
                self.model = YOLO(str(self.model_path))
                logger.info(f"Loaded YOLO model: {self.model_path}")
            elif FALLBACK_MODEL_PATH.exists():
                self.model = YOLO(str(FALLBACK_MODEL_PATH))
                logger.info(f"Loaded fallback ONNX model: {FALLBACK_MODEL_PATH}")
            else:
                logger.warning("No model file found. Using OpenCV fallback detector.")
        except ImportError:
            logger.warning("ultralytics not installed. Using OpenCV fallback detector.")

    def detect(self, img: np.ndarray, conf_threshold: float = 0.35) -> list[Dot]:
        """
        Detect Braille dots in an image.

        Returns:
            List of Dot objects with position and confidence
        """
        if self.model is not None:
            return self._detect_yolo(img, conf_threshold)
        else:
            return self._detect_opencv_fallback(img)

    def _detect_yolo(self, img: np.ndarray, conf_threshold: float) -> list[Dot]:
        """Primary: YOLOv8 dot detection."""
        results = self.model(img, conf=conf_threshold, verbose=False)
        dots = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                radius = min(x2 - x1, y2 - y1) / 2
                dots.append(Dot(x=cx, y=cy, confidence=conf, radius=radius))

        return dots

    def _detect_opencv_fallback(self, img: np.ndarray) -> list[Dot]:
        """Fallback: OpenCV blob detector when YOLO is unavailable."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        # SimpleBlobDetector parameters tuned for Braille dots
        params = cv2.SimpleBlobDetector_Params()
        params.filterByArea = True
        params.minArea = 20
        params.maxArea = 500
        params.filterByCircularity = True
        params.minCircularity = 0.6
        params.filterByConvexity = True
        params.minConvexity = 0.8
        params.filterByInertia = True
        params.minInertiaRatio = 0.5

        detector = cv2.SimpleBlobDetector_create(params)
        keypoints = detector.detect(gray)

        return [
            Dot(x=kp.pt[0], y=kp.pt[1], confidence=0.7, radius=kp.size / 2)
            for kp in keypoints
        ]


class CellGrouper:
    """Groups detected dots into Braille cells using geometric reasoning."""

    def group(self, dots: list[Dot]) -> list[BrailleCell]:
        """
        Main entry point: dots → Braille cells.

        Returns cells sorted in reading order (left-to-right, top-to-bottom).
        """
        if not dots:
            return []

        spacing = self._estimate_dot_spacing(dots)
        rows = self._cluster_into_rows(dots, spacing)
        cells = self._rows_to_cells(rows, spacing)

        return sorted(cells, key=lambda c: (round(c.y / spacing), c.x))

    def _estimate_dot_spacing(self, dots: list[Dot]) -> float:
        """Estimate inter-dot spacing via nearest-neighbor distance median."""
        if len(dots) < 2:
            return 20.0

        positions = np.array([[d.x, d.y] for d in dots])
        nn_distances = []

        for i, pos in enumerate(positions):
            dists = np.linalg.norm(positions - pos, axis=1)
            dists[i] = np.inf
            nn_distances.append(float(np.min(dists)))

        return float(np.median(nn_distances))

    def _cluster_into_rows(self, dots: list[Dot], spacing: float) -> list[list[Dot]]:
        """Cluster dots into horizontal rows based on y-coordinate proximity."""
        sorted_dots = sorted(dots, key=lambda d: d.y)
        rows: list[list[Dot]] = []
        current_row: list[Dot] = [sorted_dots[0]]

        for dot in sorted_dots[1:]:
            if abs(dot.y - current_row[-1].y) < spacing * 0.6:
                current_row.append(dot)
            else:
                rows.append(sorted(current_row, key=lambda d: d.x))
                current_row = [dot]

        rows.append(sorted(current_row, key=lambda d: d.x))
        return rows

    def _rows_to_cells(
        self, rows: list[list[Dot]], spacing: float
    ) -> list[BrailleCell]:
        """Convert row-grouped dots into Braille cells."""
        from backend.utils.braille_table import decode_cell

        cells = []
        row_idx = 0

        while row_idx + 2 < len(rows):
            row1, row2, row3 = rows[row_idx], rows[row_idx + 1], rows[row_idx + 2]

            # Check rows form a valid Braille cell triplet (3 rows ≈ 2 dot-spacings apart)
            y_diff_12 = abs(row2[0].y - row1[0].y) if row1 and row2 else 999
            y_diff_23 = abs(row3[0].y - row2[0].y) if row2 and row3 else 999

            if y_diff_12 < spacing * 1.5 and y_diff_23 < spacing * 1.5:
                # These 3 rows form Braille cells
                all_dots = row1 + row2 + row3
                col_groups = self._group_by_column(all_dots, spacing)

                for col_pair_idx in range(0, len(col_groups) - 1, 2):
                    left_col = col_groups[col_pair_idx]
                    right_col = (
                        col_groups[col_pair_idx + 1]
                        if col_pair_idx + 1 < len(col_groups)
                        else []
                    )

                    dot_pattern = self._build_dot_pattern(
                        left_col, right_col, row1, row2, row3, spacing
                    )
                    char = decode_cell(dot_pattern)
                    confidence = float(
                        np.mean([d.confidence for d in left_col + right_col] or [0.5])
                    )

                    x = (
                        min((d.x for d in left_col + right_col), default=0)
                        - spacing * 0.5
                    )
                    y = min((d.y for d in row1), default=0) - spacing * 0.5
                    w = spacing * 2.5
                    h = spacing * 3.5

                    cells.append(
                        BrailleCell(
                            dots=dot_pattern,
                            char=char,
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            confidence=confidence,
                        )
                    )

                row_idx += 3
            else:
                row_idx += 1

        return cells

    def _group_by_column(self, dots: list[Dot], spacing: float) -> list[list[Dot]]:
        """Group dots by x-coordinate into columns."""
        sorted_x = sorted(dots, key=lambda d: d.x)
        columns: list[list[Dot]] = []
        current_col: list[Dot] = [sorted_x[0]] if sorted_x else []

        for dot in sorted_x[1:]:
            if abs(dot.x - current_col[-1].x) < spacing * 0.6:
                current_col.append(dot)
            else:
                columns.append(current_col)
                current_col = [dot]

        if current_col:
            columns.append(current_col)

        return columns

    def _build_dot_pattern(
        self, left_col, right_col, row1, row2, row3, spacing
    ) -> list[bool]:
        """Build the 6-bool dot pattern from detected dots."""

        def is_in_row(dot, row_dots):
            if not row_dots:
                return False
            row_y = np.mean([d.y for d in row_dots])
            return abs(dot.y - row_y) < spacing * 0.6

        def col_has_dot_in_row(col_dots, row_dots):
            return any(is_in_row(d, row_dots) for d in col_dots)

        return [
            col_has_dot_in_row(left_col, row1),  # dot 1
            col_has_dot_in_row(left_col, row2),  # dot 2
            col_has_dot_in_row(left_col, row3),  # dot 3
            col_has_dot_in_row(right_col, row1),  # dot 4
            col_has_dot_in_row(right_col, row2),  # dot 5
            col_has_dot_in_row(right_col, row3),  # dot 6
        ]


class BraillePipeline:
    """
    Full end-to-end Braille recognition pipeline.

    Usage:
        pipeline = BraillePipeline()
        result = pipeline.run(cv2.imread("braille.jpg"))
        print(result["text"])
    """

    def __init__(self, model_path: str | Path = MODEL_PATH):
        self.preprocessor = BraillePreprocessor()
        self.detector = YOLODotDetector(model_path)
        self.grouper = CellGrouper()

    def run(self, img: np.ndarray) -> dict:
        """
        Run full Braille recognition pipeline.

        Args:
            img: BGR image (from cv2.imread or camera frame)
        Returns:
            {
                "text": str,
                "confidence": float,
                "cells": list[dict],
                "dots": list[dict],
                "processing_time_ms": int
            }
        """
        from backend.utils.braille_table import decode_sequence

        start_ms = int(time.time() * 1000)

        # Stage 1: Preprocess
        processed = self.preprocessor.preprocess(img)

        # Stage 2: Detect dots
        dots = self.detector.detect(processed)
        logger.debug(f"Detected {len(dots)} dots")

        # Stage 3: Group into cells
        cells = self.grouper.group(dots)
        logger.debug(f"Formed {len(cells)} Braille cells")

        # Stage 4: Decode sequence
        text = decode_sequence([cell.dots for cell in cells])
        text = text.strip()

        # Stage 5: Compute overall confidence
        confidence = float(np.mean([c.confidence for c in cells])) if cells else 0.0

        end_ms = int(time.time() * 1000)

        return {
            "text": text,
            "confidence": round(confidence, 3),
            "cells": [c.to_dict() for c in cells],
            "dots": [{"x": d.x, "y": d.y, "confidence": d.confidence} for d in dots],
            "processing_time_ms": end_ms - start_ms,
            "error": None,
        }


if __name__ == "__main__":
    import sys

    # Quick CLI test
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <image_path>")
        sys.exit(1)

    img_path = sys.argv[1]
    img = cv2.imread(img_path)

    if img is None:
        print(f"Error: Could not load image: {img_path}")
        sys.exit(1)

    pipeline = BraillePipeline()
    result = pipeline.run(img)

    print(f"\n{'='*50}")
    print(f"Detected text: '{result['text']}'")
    print(f"Confidence:    {result['confidence']:.1%}")
    print(f"Cells found:   {len(result['cells'])}")
    print(f"Dots found:    {len(result['dots'])}")
    print(f"Latency:       {result['processing_time_ms']}ms")
    print("=" * 50)
