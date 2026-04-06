"""OpenCV utilities for thread inspection and measurement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import cv2
import numpy as np


@dataclass
class VisionResult:
    pitch_px: float
    diameter_px: float
    pitch_mm: float
    diameter_mm: float
    contour_count: int
    overlay_frame: np.ndarray


def _find_local_peaks(signal: np.ndarray, min_distance: int = 8) -> List[int]:
    """Simple local maxima detector without external scipy dependency."""
    peaks: List[int] = []
    if signal.size < 3:
        return peaks

    threshold = float(np.mean(signal) + 0.2 * np.std(signal))
    for i in range(1, len(signal) - 1):
        if signal[i - 1] < signal[i] > signal[i + 1] and signal[i] > threshold:
            if not peaks or (i - peaks[-1]) >= min_distance:
                peaks.append(i)
    return peaks


def _estimate_pitch_px(edges_roi: np.ndarray, horizontal_axis: bool) -> float:
    if horizontal_axis:
        profile = np.sum(edges_roi > 0, axis=0).astype(np.float32)
    else:
        profile = np.sum(edges_roi > 0, axis=1).astype(np.float32)

    if profile.size < 10:
        return 0.0

    # Smooth the profile to reduce noise before peak detection.
    smooth = cv2.GaussianBlur(profile.reshape(-1, 1), (1, 9), 0).reshape(-1)
    peaks = _find_local_peaks(smooth, min_distance=8)

    if len(peaks) < 2:
        return 0.0

    diffs = np.diff(peaks)
    return float(np.median(diffs))


def analyze_thread(frame: np.ndarray, calibration_factor_mm_per_px: float = 0.05) -> VisionResult:
    """Analyze one frame and return thread geometry measurements and overlay."""
    overlay = frame.copy()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 60, 180)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) > 120]

    pitch_px = 0.0
    diameter_px = 0.0

    if contours:
        main_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(main_contour)
        cv2.drawContours(overlay, [main_contour], -1, (0, 255, 255), 2)
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 215, 255), 2)

        diameter_px = float(min(w, h))

        # Choose axis by dominant shape direction.
        horizontal_axis = w >= h
        roi_edges = edges[y : y + h, x : x + w]
        pitch_px = _estimate_pitch_px(roi_edges, horizontal_axis)

        # Draw measurement lines.
        if horizontal_axis:
            cx = x + w // 2
            cv2.line(overlay, (x, y + h + 16), (x + w, y + h + 16), (0, 255, 0), 2)
            cv2.putText(
                overlay,
                f"Length px: {w}",
                (x, y + h + 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.line(overlay, (cx, y), (cx, y + h), (255, 180, 0), 2)
        else:
            cy = y + h // 2
            cv2.line(overlay, (x + w + 16, y), (x + w + 16, y + h), (0, 255, 0), 2)
            cv2.putText(
                overlay,
                f"Length px: {h}",
                (x + w + 24, y + h // 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.line(overlay, (x, cy), (x + w, cy), (255, 180, 0), 2)

    pitch_mm = pitch_px * calibration_factor_mm_per_px
    diameter_mm = diameter_px * calibration_factor_mm_per_px

    cv2.putText(
        overlay,
        f"Contours: {len(contours)}",
        (15, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    return VisionResult(
        pitch_px=pitch_px,
        diameter_px=diameter_px,
        pitch_mm=pitch_mm,
        diameter_mm=diameter_mm,
        contour_count=len(contours),
        overlay_frame=overlay,
    )


def frame_to_jpeg_bytes(frame: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        raise ValueError("Could not encode frame to JPEG")
    return encoded.tobytes()


def jpeg_bytes_to_frame(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Invalid image input")
    return frame
