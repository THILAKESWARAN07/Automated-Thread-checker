"""Create a tiny synthetic sample dataset for quick pipeline testing."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "data" / "dataset"


def _draw_thread_like_image(size=(256, 256), defect=False) -> np.ndarray:
    img = np.zeros((size[0], size[1], 3), dtype=np.uint8)
    img[:] = (25, 25, 25)

    for i in range(20, size[1] - 20, 14):
        cv2.line(img, (i, 20), (i + 30, size[0] - 20), (220, 220, 220), 2)

    if defect:
        cv2.rectangle(img, (110, 90), (150, 140), (10, 10, 10), -1)
        cv2.line(img, (60, 70), (180, 150), (0, 0, 255), 3)

    noise = np.random.normal(0, 10, img.shape).astype(np.int16)
    noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return noisy


def main() -> None:
    good_dir = DATASET_DIR / "GOOD"
    defect_dir = DATASET_DIR / "DEFECT"
    good_dir.mkdir(parents=True, exist_ok=True)
    defect_dir.mkdir(parents=True, exist_ok=True)

    for i in range(40):
        good = _draw_thread_like_image(defect=False)
        defect = _draw_thread_like_image(defect=True)
        cv2.imwrite(str(good_dir / f"good_{i:03d}.jpg"), good)
        cv2.imwrite(str(defect_dir / f"defect_{i:03d}.jpg"), defect)

    print(f"Sample dataset generated at {DATASET_DIR}")


if __name__ == "__main__":
    main()
