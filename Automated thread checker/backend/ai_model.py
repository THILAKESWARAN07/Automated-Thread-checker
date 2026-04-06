"""CNN model loading, inference, and fallback heuristic for thread defect detection."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

try:
    import tensorflow as tf
except Exception:  # pragma: no cover - allows running without tensorflow during setup
    tf = None


class ThreadDefectClassifier:
    """Wraps model inference and gracefully falls back if model is unavailable."""

    def __init__(self, model_path: Path, image_size: Tuple[int, int] = (128, 128)) -> None:
        self.model_path = model_path
        self.image_size = image_size
        self.model = None
        self.available = False

        if tf is not None and model_path.exists():
            self.model = tf.keras.models.load_model(str(model_path))
            self.available = True

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, self.image_size)
        tensor = resized.astype(np.float32) / 255.0
        return np.expand_dims(tensor, axis=0)

    def _heuristic(self, frame: np.ndarray) -> Dict[str, float | str]:
        """Simple fallback if trained model is missing."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        edges = cv2.Canny(gray, 70, 170)
        edge_density = float(np.mean(edges > 0))

        # Low edge density or very low sharpness often indicates blur/damage.
        defect_score = 0.0
        if sharpness < 60:
            defect_score += 0.45
        if edge_density < 0.05:
            defect_score += 0.35
        if edge_density > 0.40:
            defect_score += 0.25

        defect_score = min(defect_score, 0.95)
        label = "DEFECT" if defect_score >= 0.50 else "GOOD"
        confidence = defect_score if label == "DEFECT" else 1.0 - defect_score

        return {
            "label": label,
            "confidence": round(float(confidence), 4),
            "source": "heuristic",
        }

    def predict(self, frame: np.ndarray) -> Dict[str, float | str]:
        if self.available and self.model is not None:
            sample = self._preprocess(frame)
            pred = self.model.predict(sample, verbose=0)
            score = float(pred[0][0])
            label = "DEFECT" if score >= 0.5 else "GOOD"
            confidence = score if label == "DEFECT" else 1.0 - score
            return {
                "label": label,
                "confidence": round(float(confidence), 4),
                "source": "cnn",
            }

        return self._heuristic(frame)
