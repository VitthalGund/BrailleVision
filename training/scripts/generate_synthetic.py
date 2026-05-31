"""
BrailleVision â€” Synthetic Braille Dataset Generator

Generates synthetic Braille images with perfect YOLO-format annotations.
No manual labeling needed â€” dot positions are computed mathematically.

What it renders:
  - Random Grade 1 Braille words/sentences on paper-texture backgrounds
  - Dots as anti-aliased circles with realistic shadows and highlights
  - Varied: paper color, dot size, spacing, lighting, blur, noise, rotation

Output structure:
  output_dir/
    images/  â† .jpg synthetic Braille images
    labels/  â† .txt YOLO annotations (class cx cy w h, normalized)

Usage:
    python training/scripts/generate_synthetic.py --count 500
    python training/scripts/generate_synthetic.py --count 100 --output dataset/raw/synthetic
"""

import argparse
import math
import os
import random
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

# â”€â”€â”€ Grade 1 Braille dot patterns â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Each entry: character â†’ list of 6 bools [dot1,dot2,dot3,dot4,dot5,dot6]
# Dot layout:
#   1 4
#   2 5
#   3 6
BRAILLE_PATTERNS: dict[str, list[bool]] = {
    'a': [1,0,0,0,0,0], 'b': [1,1,0,0,0,0], 'c': [1,0,0,1,0,0],
    'd': [1,0,0,1,1,0], 'e': [1,0,0,0,1,0], 'f': [1,1,0,1,0,0],
    'g': [1,1,0,1,1,0], 'h': [1,1,0,0,1,0], 'i': [0,1,0,1,0,0],
    'j': [0,1,0,1,1,0], 'k': [1,0,1,0,0,0], 'l': [1,1,1,0,0,0],
    'm': [1,0,1,1,0,0], 'n': [1,0,1,1,1,0], 'o': [1,0,1,0,1,0],
    'p': [1,1,1,1,0,0], 'q': [1,1,1,1,1,0], 'r': [1,1,1,0,1,0],
    's': [0,1,1,1,0,0], 't': [0,1,1,1,1,0], 'u': [1,0,1,0,0,1],
    'v': [1,1,1,0,0,1], 'w': [0,1,0,1,1,1], 'x': [1,0,1,1,0,1],
    'y': [1,0,1,1,1,1], 'z': [1,0,1,0,1,1], ' ': [0,0,0,0,0,0],
    '1': [1,0,0,0,0,0], '2': [1,1,0,0,0,0], '3': [1,0,0,1,0,0],
    '4': [1,0,0,1,1,0], '5': [1,0,0,0,1,0], '6': [1,1,0,1,0,0],
    '7': [1,1,0,1,1,0], '8': [1,1,0,0,1,0], '9': [0,1,0,1,0,0],
    '0': [0,1,0,1,1,0],
}

SAMPLE_WORDS = [
    "hello", "world", "braille", "vision", "read", "book", "learn",
    "open", "door", "light", "hope", "help", "care", "life", "love",
    "yes", "no", "stop", "go", "fast", "slow", "home", "safe",
    "water", "food", "work", "play", "music", "art", "school",
    "india", "hindi", "english", "math", "science", "class",
    "abc", "xyz", "test", "data", "model", "train", "eval",
]


def make_paper_background(h: int, w: int) -> np.ndarray:
    """Generate a realistic paper/card texture background."""
    # Base paper color: warm white / cream / light gray
    base_colors = [
        (240, 238, 230),  # warm white
        (245, 243, 235),  # cream
        (250, 248, 245),  # bright white
        (230, 228, 220),  # off-white
        (220, 215, 200),  # aged paper
    ]
    base = random.choice(base_colors)
    img = np.full((h, w, 3), base, dtype=np.uint8)

    # Add paper grain noise
    noise_intensity = random.randint(2, 8)
    noise = np.random.randint(-noise_intensity, noise_intensity + 1, (h, w, 3), dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Add subtle directional lighting gradient (simulates raking light)
    if random.random() < 0.6:
        direction = random.choice(['left', 'right', 'top', 'bottom'])
        gradient = np.zeros((h, w), dtype=np.float32)
        intensity = random.uniform(0.05, 0.20)
        if direction == 'left':
            gradient = np.tile(np.linspace(1.0, 1.0 - intensity, w), (h, 1))
        elif direction == 'right':
            gradient = np.tile(np.linspace(1.0 - intensity, 1.0, w), (h, 1))
        elif direction == 'top':
            gradient = np.tile(np.linspace(1.0, 1.0 - intensity, h).reshape(-1, 1), (1, w))
        else:
            gradient = np.tile(np.linspace(1.0 - intensity, 1.0, h).reshape(-1, 1), (1, w))
        for c in range(3):
            img[:, :, c] = np.clip(img[:, :, c].astype(np.float32) * gradient, 0, 255).astype(np.uint8)

    return img


def draw_braille_dot(
    img: np.ndarray,
    cx: int, cy: int, radius: int,
    paper_color: Tuple[int, int, int],
    light_dir: str = 'top-left'
) -> None:
    """Draw a single realistic embossed Braille dot with shadow and highlight."""
    # Shadow (slightly darker, offset from light)
    shadow_offsets = {
        'top-left': (2, 2), 'top-right': (-2, 2),
        'bottom-left': (2, -2), 'bottom-right': (-2, -2),
        'top': (0, 3), 'left': (3, 0),
    }
    sx, sy = shadow_offsets.get(light_dir, (2, 2))
    shadow_color = tuple(max(0, c - random.randint(15, 35)) for c in paper_color)
    cv2.circle(img, (cx + sx, cy + sy), radius + 1, shadow_color, -1, cv2.LINE_AA)

    # Dot body: slightly darker than paper
    dot_darkness = random.randint(20, 55)
    dot_color = tuple(max(0, c - dot_darkness) for c in paper_color)
    cv2.circle(img, (cx, cy), radius, dot_color, -1, cv2.LINE_AA)

    # Highlight (specular reflection from raised bump)
    hl_offsets = {
        'top-left': (-1, -1), 'top-right': (1, -1),
        'bottom-left': (-1, 1), 'bottom-right': (1, 1),
        'top': (0, -2), 'left': (-2, 0),
    }
    hx, hy = hl_offsets.get(light_dir, (-1, -1))
    hl_radius = max(1, radius // 3)
    hl_color = tuple(min(255, c + random.randint(20, 50)) for c in paper_color)
    cv2.circle(img, (cx + hx, cy + hy), hl_radius, hl_color, -1, cv2.LINE_AA)


def generate_braille_image(
    text: str,
    img_w: int = 640,
    img_h: int = 480,
) -> Tuple[np.ndarray, List[Tuple[float, float, float, float]]]:
    """
    Render a Braille text string as an image.
    Returns (image, yolo_boxes) where each box is (cx, cy, w, h) normalized 0-1.
    """
    # Randomised rendering parameters
    dot_radius = random.randint(6, 12)
    dot_spacing_x = int(dot_radius * random.uniform(2.2, 3.5))  # horizontal dot gap
    dot_spacing_y = int(dot_radius * random.uniform(2.2, 3.5))  # vertical dot gap
    cell_gap_x = int(dot_spacing_x * random.uniform(1.3, 2.0))  # gap between cells
    line_gap_y = int(dot_spacing_y * random.uniform(2.0, 3.5))  # gap between lines

    # Margins
    margin_x = random.randint(30, 80)
    margin_y = random.randint(30, 80)

    # Choose light direction
    light_dir = random.choice(['top-left', 'top-right', 'bottom-left', 'top', 'left'])

    # Create background
    paper_base = random.choice([
        (240, 238, 230), (245, 243, 235), (250, 248, 245),
        (230, 228, 220), (220, 215, 200)
    ])
    img = make_paper_background(img_h, img_w)

    # Get average paper color from center region
    cy_region = img[img_h // 3: 2 * img_h // 3, img_w // 3: 2 * img_w // 3]
    paper_color = tuple(int(v) for v in cy_region.mean(axis=(0, 1)))

    yolo_boxes: List[Tuple[float, float, float, float]] = []  # (cx,cy,w,h) normalized

    # Word-wrap text to fit image width
    chars = [c.lower() for c in text if c.lower() in BRAILLE_PATTERNS]
    if not chars:
        chars = ['h', 'e', 'l', 'l', 'o']

    # Estimate how many chars fit per line
    cell_width = 2 * dot_spacing_x + cell_gap_x
    chars_per_line = max(1, (img_w - 2 * margin_x) // cell_width)

    lines = [chars[i:i + chars_per_line] for i in range(0, len(chars), chars_per_line)]

    pen_y = margin_y  # current top of Braille cell row

    for line in lines:
        pen_x = margin_x
        for char in line:
            pattern = BRAILLE_PATTERNS.get(char, [0]*6)

            # Cell consists of 2 columns Ã— 3 rows of dot positions
            # Left col: dots 1,2,3 (top to bottom), Right col: dots 4,5,6
            dot_positions = [
                # (dot_index, col_offset, row_offset)
                (0, 0, 0),  # dot 1: left col, row 0
                (1, 0, 1),  # dot 2: left col, row 1
                (2, 0, 2),  # dot 3: left col, row 2
                (3, 1, 0),  # dot 4: right col, row 0
                (4, 1, 1),  # dot 5: right col, row 1
                (5, 1, 2),  # dot 6: right col, row 2
            ]

            for dot_idx, col, row in dot_positions:
                if not pattern[dot_idx]:
                    continue  # this dot is absent

                dx = pen_x + col * dot_spacing_x
                dy = pen_y + row * dot_spacing_y

                # Check bounds
                if dx - dot_radius < 0 or dx + dot_radius >= img_w:
                    continue
                if dy - dot_radius < 0 or dy + dot_radius >= img_h:
                    continue

                draw_braille_dot(img, dx, dy, dot_radius, paper_color, light_dir)

                # YOLO annotation (normalized)
                box_w = (dot_radius * 2 + 2) / img_w
                box_h = (dot_radius * 2 + 2) / img_h
                cx_n = dx / img_w
                cy_n = dy / img_h

                # Clamp
                cx_n = max(box_w / 2, min(1 - box_w / 2, cx_n))
                cy_n = max(box_h / 2, min(1 - box_h / 2, cy_n))

                yolo_boxes.append((cx_n, cy_n, box_w, box_h))

            pen_x += cell_width

        pen_y += 3 * dot_spacing_y + line_gap_y

        # Stop if we've gone past the image bottom
        if pen_y + 3 * dot_spacing_y > img_h - margin_y:
            break

    # Post-processing augmentations
    img = _apply_augmentations(img)

    return img, yolo_boxes


def _apply_augmentations(img: np.ndarray) -> np.ndarray:
    """Apply random real-world augmentations."""
    # Gaussian blur (camera defocus)
    if random.random() < 0.4:
        ksize = random.choice([3, 5])
        img = cv2.GaussianBlur(img, (ksize, ksize), 0)

    # Gaussian noise
    if random.random() < 0.5:
        noise_std = random.uniform(2, 12)
        noise = np.random.normal(0, noise_std, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Brightness / contrast jitter
    if random.random() < 0.6:
        alpha = random.uniform(0.8, 1.2)  # contrast
        beta = random.uniform(-20, 20)    # brightness
        img = np.clip(alpha * img.astype(np.float32) + beta, 0, 255).astype(np.uint8)

    # Slight rotation (â‰¤ 8 degrees)
    if random.random() < 0.3:
        h, w = img.shape[:2]
        angle = random.uniform(-8, 8)
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h),
                             flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_REFLECT)

    # JPEG compression artifacts
    if random.random() < 0.3:
        quality = random.randint(70, 95)
        _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)

    return img


def generate_dataset(count: int, output_dir: Path):
    """Generate `count` synthetic Braille images with YOLO annotations."""
    out_img = output_dir / "images"
    out_lbl = output_dir / "labels"
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    print(f"Generating {count} synthetic images â†’ {output_dir}")

    # Build a pool of random words
    word_pool = SAMPLE_WORDS * (count // len(SAMPLE_WORDS) + 5)
    random.shuffle(word_pool)

    generated = 0
    skipped = 0

    for i in range(count):
        # Random text: 1â€“4 words
        n_words = random.randint(1, 4)
        words = random.sample(word_pool, min(n_words, len(word_pool)))
        text = ' '.join(words)

        # Random image size (near 640Ã—480 or 640Ã—640)
        w = random.choice([640, 800, 1024])
        h = random.choice([480, 640, 720])

        try:
            img, boxes = generate_braille_image(text, img_w=w, img_h=h)
        except Exception as e:
            print(f"  âš   Generation error at index {i}: {e}")
            skipped += 1
            continue

        if not boxes:
            skipped += 1
            continue  # Skip images with no dots (empty text)

        # Save image
        stem = f"synthetic_{i:06d}"
        img_path = out_img / f"{stem}.jpg"
        cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 92])

        # Save YOLO label
        lbl_lines = [f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}" for cx, cy, bw, bh in boxes]
        (out_lbl / f"{stem}.txt").write_text('\n'.join(lbl_lines))

        generated += 1

        # Progress
        if (i + 1) % 50 == 0 or i == count - 1:
            print(f"  Progress: {i+1}/{count} ({generated} saved, {skipped} skipped)", end="\r")

    print(f"\n  âœ“ Done. Generated: {generated}, Skipped: {skipped}")
    print(f"  Images: {out_img}")
    print(f"  Labels: {out_lbl}")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic Braille training images")
    parser.add_argument("--count", type=int, default=500,
                        help="Number of images to generate (default: 500)")
    parser.add_argument("--output", type=str,
                        default=str(Path(__file__).parent.parent.parent / "dataset" / "raw" / "synthetic"),
                        help="Output directory")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    output_dir = Path(args.output)
    generate_dataset(args.count, output_dir)

    print("\nNext step: python training/scripts/merge_and_split.py")


if __name__ == "__main__":
    main()
