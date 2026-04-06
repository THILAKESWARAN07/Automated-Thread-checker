"""FastAPI backend for automated thread checking system - ADVANCED with mobile camera support."""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import platform
import re
import threading
import time
from urllib.parse import urlparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.ai_model import ThreadDefectClassifier
from backend.database import (
    export_inspections_csv,
    get_all_settings,
    get_latest_result,
    get_recent_logs,
    get_setting,
    get_stats,
    init_db,
    insert_inspection,
    set_setting,
)
from backend.vision import analyze_thread, frame_to_jpeg_bytes, jpeg_bytes_to_frame

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
FAILED_DIR = DATA_DIR / "failed"
EXPORT_DIR = DATA_DIR / "exports"
BATCH_DIR = DATA_DIR / "batch"
MODEL_PATH = BASE_DIR / "models" / "thread_model.h5"
FRONTEND_DIR = BASE_DIR / "frontend"

logger = logging.getLogger("thread_checker.camera")


class SettingsUpdate(BaseModel):
    default_tolerance_pct: Optional[float] = Field(default=None, ge=0, le=100)
    calibration_factor_mm_per_px: Optional[float] = Field(default=None, gt=0)
    camera_source: Optional[str] = None
    thread_standards: Optional[Dict[str, Dict[str, float]]] = None


class AnalyzeRequest(BaseModel):
    thread_type: str = "M10"
    tolerance_pct: Optional[float] = Field(default=None, ge=0, le=100)
    reference_length_mm: Optional[float] = Field(default=None, gt=0)
    reference_pixels: Optional[float] = Field(default=None, gt=0)


class CameraInfo(BaseModel):
    id: int
    name: str
    type: str  # "local_camera", "ip_camera", "file"
    status: str  # "available", "unavailable"
    resolution: Optional[Dict[str, int]] = None


class BatchProcessRequest(BaseModel):
    thread_type: str = "M10"
    tolerance_pct: Optional[float] = Field(default=None, ge=0, le=100)
    auto_calibrate: bool = False


class ImageQualityResult(BaseModel):
    sharpness: float
    brightness: float
    contrast: float
    quality_score: float  # 0-100
    recommendation: str


class CameraStartRequest(BaseModel):
    source: Optional[str] = None


class CameraService:
    """Enhanced camera service with support for local cameras, IP cameras (MJPEG), and streams."""
    
    def __init__(self) -> None:
        self.capture: Optional[cv2.VideoCapture] = None
        self.lock = threading.Lock()
        self.last_frame: Optional[np.ndarray] = None
        self.frame_count: int = 0
        self.ip_camera_url: Optional[str] = None
        self.current_source: Optional[str] = None
        self.is_windows = platform.system().lower().startswith("win")
        self.last_error: Optional[str] = None

    @staticmethod
    def _parse_source(source: str) -> Any:
        """Parse camera source - supports local cameras (0, 1, 2), file paths, and HTTP URLs."""
        if source.isdigit():
            return int(source)
        elif source.startswith("http://") or source.startswith("https://"):
            return source
        else:
            return source

    @staticmethod
    def _normalize_network_source(source: str) -> str:
        """Accept raw IP/host inputs and convert them into usable HTTP URLs."""
        s = source.strip()
        if not s:
            return s
        if s.startswith("http://") or s.startswith("https://"):
            return s

        # Common user input: 192.168.1.100:8080 or 192.168.1.100
        host_like = re.match(r"^[A-Za-z0-9_.-]+(:\d+)?(/.*)?$", s)
        if host_like and not re.match(r"^[A-Za-z]:\\", s):
            return f"http://{s}"

        return s

    @staticmethod
    def _stream_source_candidates(source: str) -> List[str]:
        """Try common mobile/IP camera stream endpoints when a base URL is provided."""
        normalized = CameraService._normalize_network_source(source)
        if not (normalized.startswith("http://") or normalized.startswith("https://")):
            return [normalized]

        parsed = urlparse(normalized)
        base = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path.strip()
        query = f"?{parsed.query}" if parsed.query else ""

        if path and path != "/":
            return [f"{normalized}"]

        return [
            f"{base}/video{query}",
            f"{base}/video_feed{query}",
            f"{base}/mjpeg{query}",
            f"{base}/stream{query}",
            f"{base}/?action=stream",
            f"{base}{query}",
        ]

    def _release_locked(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def _create_capture(self, parsed_source: Any) -> cv2.VideoCapture:
        if isinstance(parsed_source, int):
            backend_flag = cv2.CAP_DSHOW if self.is_windows else cv2.CAP_ANY
            return cv2.VideoCapture(parsed_source, backend_flag)
        return cv2.VideoCapture(parsed_source)

    def is_active(self) -> bool:
        """Return True only when a capture object exists and is opened."""
        with self.lock:
            return bool(self.capture is not None and self.capture.isOpened())

    def _prepare_capture(self, source: str) -> tuple[Optional[cv2.VideoCapture], Optional[np.ndarray], str]:
        parsed_source = self._parse_source(source)
        capture: Optional[cv2.VideoCapture] = None
        warm_frame: Optional[np.ndarray] = None
        resolved_source = source

        if isinstance(parsed_source, int):
            for candidate in self._iter_int_captures(parsed_source):
                if not candidate or not candidate.isOpened():
                    if candidate:
                        candidate.release()
                    continue

                for _ in range(15):
                    ok, frame = candidate.read()
                    if ok and frame is not None:
                        warm_frame = frame.copy()
                        capture = candidate
                        resolved_source = str(parsed_source)
                        break
                    time.sleep(0.1)

                if capture is not None:
                    break

                candidate.release()
        else:
            source_candidates = self._stream_source_candidates(str(parsed_source))
            for stream_source in source_candidates:
                candidate = self._create_capture(stream_source)
                if not candidate or not candidate.isOpened():
                    if candidate:
                        candidate.release()
                    continue

                for _ in range(20):
                    ok, frame = candidate.read()
                    if ok and frame is not None:
                        warm_frame = frame.copy()
                        capture = candidate
                        resolved_source = stream_source
                        break
                    time.sleep(0.15)

                if capture is not None:
                    break

                candidate.release()

        return capture, warm_frame, resolved_source

    def _iter_int_captures(self, source_index: int):
        """Yield candidate VideoCapture instances for local camera indexes."""
        if self.is_windows:
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]

        for backend in backends:
            try:
                yield cv2.VideoCapture(source_index, backend)
            except Exception:
                continue

    def start(self, source: str) -> bool:
        """Start camera with given source. Returns True if successful."""
        try:
            capture, warm_frame, resolved_source = self._prepare_capture(source)
        except Exception as exc:
            with self.lock:
                self.last_error = f"Camera start error: {exc}"
            logger.exception("Camera start error for source %s: %s", source, exc)
            return False

        if capture is None or warm_frame is None:
            with self.lock:
                self.last_error = f"Unable to open camera source '{source}'."
            logger.warning("Camera source %s failed to open or provide frames", source)
            return False

        with self.lock:
            self._release_locked()
            self.capture = capture
            self.last_frame = warm_frame
            self.frame_count = 0
            self.current_source = resolved_source
            self.ip_camera_url = resolved_source if resolved_source.startswith("http") else None
            self.last_error = None

        logger.info("Camera source %s started", resolved_source)
        return True

    def read_frame(self):
        """Read frame from camera while keeping lock hold-time minimal."""
        with self.lock:
            if self.capture is None:
                raise RuntimeError("Camera is not initialized")
            capture = self.capture
            source = self.current_source

        read_error: Optional[str] = None
        for _ in range(5):
            try:
                ok, frame = capture.read()
                if ok and frame is not None:
                    with self.lock:
                        if self.capture is capture:
                            self.last_frame = frame.copy()
                            self.frame_count += 1
                            self.last_error = None
                    return frame
            except Exception as exc:
                read_error = str(exc)
            time.sleep(0.06)

        # Reconnect once without holding the lock during camera open attempts.
        if source:
            recovered_capture, warm_frame, resolved_source = self._prepare_capture(source)
            if recovered_capture is not None and warm_frame is not None:
                with self.lock:
                    if self.capture is capture:
                        self._release_locked()
                        self.capture = recovered_capture
                        self.current_source = resolved_source
                        self.ip_camera_url = resolved_source if resolved_source.startswith("http") else None
                        self.last_frame = warm_frame.copy()
                        self.frame_count += 1
                        self.last_error = None
                        logger.info("Camera recovered for source %s", resolved_source)
                        return warm_frame

                # Capture was swapped by another request; release extra handle.
                recovered_capture.release()

        message = "Failed to read frame from camera"
        if read_error:
            message = f"{message}: {read_error}"
        with self.lock:
            if self.capture is capture:
                self.last_error = message
        raise RuntimeError(message)

    def get_available_cameras(self) -> List[CameraInfo]:
        """Detect available local cameras."""
        cameras: List[CameraInfo] = []
        
        # Test local cameras 0-5
        for i in range(6):
            try:
                cap = self._create_capture(i)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        h, w = frame.shape[:2]
                        cameras.append(CameraInfo(
                            id=i,
                            name=f"Camera {i}",
                            type="local_camera",
                            status="available",
                            resolution={"width": w, "height": h}
                        ))
                    cap.release()
            except Exception:
                pass
        
        return cameras

    def test_ip_camera(self, url: str) -> Optional[CameraInfo]:
        """Test IP camera connectivity."""
        try:
            # Test direct frame grab
            cap = self._create_capture(url)
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                h, w = frame.shape[:2]
                return CameraInfo(
                    id=-1,
                    name="IP Camera",
                    type="ip_camera",
                    status="available",
                    resolution={"width": w, "height": h}
                )
        except Exception:
            pass
        
        return None

    def stop(self) -> None:
        with self.lock:
            self._release_locked()
            self.ip_camera_url = None
            self.current_source = None


app = FastAPI(title="Automated Thread Checking System ADVANCED", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend_static")

camera_service = CameraService()
classifier = ThreadDefectClassifier(MODEL_PATH)
state: Dict[str, Any] = {
    "latest_frame_path": None,
    "latest_result": None,
    "performance_metrics": {
        "avg_analysis_time_ms": 0,
        "total_inspections": 0,
        "images_processed": 0,
    }
}

# Advanced quality assessment
def assess_image_quality(frame: np.ndarray) -> ImageQualityResult:
    """Assess image quality for inspection."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Sharpness (Laplacian variance)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharpness_norm = min(sharpness / 500.0, 1.0) * 100
    
    # Brightness
    brightness = np.mean(gray)
    brightness_norm = min(abs(brightness - 128) / 128 * 100, 100)
    
    # Contrast
    contrast = np.std(gray)
    contrast_norm = min(contrast / 70 * 100, 100)
    
    quality_score = (sharpness_norm * 0.5 + (100 - brightness_norm) * 0.2 + contrast_norm * 0.3)
    
    if quality_score >= 80:
        recommendation = "Excellent - ready for inspection"
    elif quality_score >= 60:
        recommendation = "Good - proceed with caution"
    elif quality_score >= 40:
        recommendation = "Fair - may affect accuracy"
    else:
        recommendation = "Poor - adjust lighting or camera"
    
    return ImageQualityResult(
        sharpness=round(sharpness_norm, 2),
        brightness=round(brightness_norm, 2),
        contrast=round(contrast_norm, 2),
        quality_score=round(quality_score, 2),
        recommendation=recommendation
    )


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    FAILED_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    BATCH_DIR.mkdir(parents=True, exist_ok=True)

    source = str(get_setting("camera_source", "0"))
    if not camera_service.start(source):
        logger.warning("Camera failed to start on startup (source %s)", source)


@app.on_event("shutdown")
def shutdown_event() -> None:
    camera_service.stop()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "version": "2.0.0"}


@app.get("/")
def frontend_index() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="frontend/index.html not found")
    return FileResponse(index_path)


@app.get("/favicon.ico")
def favicon() -> FileResponse:
    # Return a tiny placeholder if no favicon is provided by the frontend.
    icon_path = FRONTEND_DIR / "favicon.ico"
    if icon_path.exists():
        return FileResponse(icon_path)
    raise HTTPException(status_code=404, detail="favicon.ico not found")


# Advanced camera endpoints
@app.get("/cameras/available")
def get_available_cameras() -> Dict[str, Any]:
    """Get list of available cameras (local and IP)."""
    cameras = camera_service.get_available_cameras()
    return {
        "cameras": [c.model_dump() for c in cameras],
        "count": len(cameras)
    }


@app.post("/cameras/test")
def test_camera(url: str) -> Dict[str, Any]:
    """Test a camera source and switch to it only if it opens successfully."""
    source = url.strip()
    if not source:
        raise HTTPException(status_code=400, detail="Camera source is required")

    success = camera_service.start(source)
    if not success:
        detail = camera_service.last_error or f"Unable to open camera source '{source}'."
        raise HTTPException(status_code=500, detail=detail)

    set_setting("camera_source", source)
    resolution = None
    if camera_service.last_frame is not None:
        height, width = camera_service.last_frame.shape[:2]
        resolution = {"width": width, "height": height}

    return {
        "message": "Camera test successful",
        "camera_ok": True,
        "source": source,
        "current_source": camera_service.current_source,
        "resolution": resolution,
    }


@app.get("/camera/status")
def camera_status() -> Dict[str, Any]:
    """Return current camera activity state."""
    return {
        "active": camera_service.is_active(),
        "source": str(get_setting("camera_source", "0")),
        "current_source": camera_service.current_source,
        "frame_count": camera_service.frame_count,
        "last_error": camera_service.last_error,
    }


@app.post("/camera/on")
def camera_on(request: CameraStartRequest) -> Dict[str, Any]:
    source = (request.source or str(get_setting("camera_source", "0"))).strip()
    if not source:
        source = "0"

    success = camera_service.start(source)
    if not success:
        detail = camera_service.last_error or "Failed to start camera"
        raise HTTPException(status_code=500, detail=detail)

    set_setting("camera_source", source)
    return {"message": "Camera started", "active": True, "source": source}


@app.post("/camera/off")
def camera_off() -> Dict[str, Any]:
    camera_service.stop()
    return {"message": "Camera stopped", "active": False}


@app.get("/image/quality")
def check_image_quality() -> Dict[str, Any]:
    """Check quality of current camera feed."""
    try:
        frame = camera_service.read_frame()
        quality = assess_image_quality(frame)
        return quality.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/capture")
def capture_frame() -> Dict[str, str]:
    # If camera was stopped/disconnected, try restarting from saved source.
    if not camera_service.is_active():
        source = str(get_setting("camera_source", "0")).strip() or "0"
        if not camera_service.start(source):
            detail = camera_service.last_error or "Failed to start camera"
            raise HTTPException(status_code=500, detail=detail)

    try:
        frame = camera_service.read_frame()
    except RuntimeError as exc:
        # A stale stream may fail reads while still marked active; restart once.
        source = str(get_setting("camera_source", "0")).strip() or camera_service.current_source or "0"
        if not camera_service.start(source):
            detail = camera_service.last_error or str(exc)
            raise HTTPException(status_code=500, detail=detail) from exc

        try:
            frame = camera_service.read_frame()
        except RuntimeError as retry_exc:
            raise HTTPException(status_code=500, detail=str(retry_exc)) from retry_exc

    ts = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:15]
    image_path = IMAGES_DIR / f"capture_{ts}.jpg"
    cv2.imwrite(str(image_path), frame)
    state["latest_frame_path"] = str(image_path)

    return {"message": "Frame captured", "image_path": str(image_path)}


def _evaluate_rule_result(
    pitch_mm: float,
    diameter_mm: float,
    thread_type: str,
    tolerance_pct: float,
    standards: Dict[str, Dict[str, float]],
) -> str:
    standard = standards.get(thread_type)
    if not standard:
        return "FAIL"

    std_pitch = standard.get("pitch_mm", 0.0)
    std_diameter = standard.get("diameter_mm", 0.0)

    pitch_ok = std_pitch > 0 and abs(pitch_mm - std_pitch) <= (tolerance_pct / 100.0) * std_pitch
    diameter_ok = std_diameter > 0 and abs(diameter_mm - std_diameter) <= (tolerance_pct / 100.0) * std_diameter

    return "PASS" if (pitch_ok and diameter_ok) else "FAIL"


def _build_overlay_base64(frame) -> str:
    jpg = frame_to_jpeg_bytes(frame)
    return base64.b64encode(jpg).decode("utf-8")


def _run_analysis(request: AnalyzeRequest, frame, include_quality: bool = True) -> JSONResponse:
    """Run comprehensive analysis including vision, AI, rules, and quality assessment."""
    start_time = time.time()
    
    # Check image quality if enabled
    quality_result = None
    if include_quality:
        quality_result = assess_image_quality(frame)
    
    calibration_factor = float(get_setting("calibration_factor_mm_per_px", 0.05))

    if request.reference_length_mm and request.reference_pixels:
        calibration_factor = request.reference_length_mm / request.reference_pixels
        set_setting("calibration_factor_mm_per_px", calibration_factor)

    vision_result = analyze_thread(frame, calibration_factor)
    ai = classifier.predict(frame)

    standards = get_setting("thread_standards", {})
    tolerance = (
        request.tolerance_pct
        if request.tolerance_pct is not None
        else float(get_setting("default_tolerance_pct", 8.0))
    )

    rule_result = _evaluate_rule_result(
        pitch_mm=vision_result.pitch_mm,
        diameter_mm=vision_result.diameter_mm,
        thread_type=request.thread_type,
        tolerance_pct=tolerance,
        standards=standards,
    )

    final_decision = "PASS" if (rule_result == "PASS" and ai["label"] == "GOOD") else "FAIL"

    ts = datetime.now().isoformat(timespec="seconds")
    notes = f"source={ai['source']} tolerance={tolerance}%"

    out_image_name = f"inspection_{datetime.now().strftime('%Y%m%d_%H%M%S%f')[:18]}.jpg"
    out_image_path = IMAGES_DIR / out_image_name

    cv2.putText(
        vision_result.overlay_frame,
        f"AI: {ai['label']} ({ai['confidence']:.2f})",
        (15, 58),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 0) if ai["label"] == "GOOD" else (0, 0, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        vision_result.overlay_frame,
        f"RULE: {rule_result}  FINAL: {final_decision}",
        (15, 86),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (50, 220, 50) if final_decision == "PASS" else (20, 20, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        vision_result.overlay_frame,
        f"Pitch(mm): {vision_result.pitch_mm:.3f}  Dia(mm): {vision_result.diameter_mm:.3f}",
        (15, 114),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    cv2.imwrite(str(out_image_path), vision_result.overlay_frame)

    if final_decision == "FAIL":
        fail_path = FAILED_DIR / out_image_name
        cv2.imwrite(str(fail_path), vision_result.overlay_frame)

    record = {
        "timestamp": ts,
        "thread_type": request.thread_type,
        "pitch_mm": round(vision_result.pitch_mm, 4),
        "diameter_mm": round(vision_result.diameter_mm, 4),
        "ai_result": ai["label"],
        "ai_confidence": float(ai["confidence"]),
        "rule_result": rule_result,
        "final_decision": final_decision,
        "image_path": str(out_image_path),
        "notes": notes,
    }

    row_id = insert_inspection(record)
    record["id"] = row_id

    # Update performance metrics
    analysis_time = (time.time() - start_time) * 1000
    state["performance_metrics"]["avg_analysis_time_ms"] = round(analysis_time, 2)
    state["performance_metrics"]["total_inspections"] += 1
    state["performance_metrics"]["images_processed"] += 1

    payload = {
        **record,
        "calibration_factor_mm_per_px": calibration_factor,
        "tolerance_pct": tolerance,
        "overlay_image_b64": _build_overlay_base64(vision_result.overlay_frame),
        "analysis_time_ms": analysis_time,
    }
    
    if quality_result:
        payload["image_quality"] = quality_result.model_dump()

    state["latest_result"] = payload
    return JSONResponse(payload)


@app.post("/analyze")
def analyze(request: AnalyzeRequest) -> JSONResponse:
    try:
        if state["latest_frame_path"]:
            frame = cv2.imread(state["latest_frame_path"])
            if frame is None:
                raise ValueError("Latest captured frame could not be loaded")
        else:
            frame = camera_service.read_frame()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Image input error: {exc}") from exc

    return _run_analysis(request, frame)


@app.post("/analyze_upload")
def analyze_upload(
    thread_type: str = "M10",
    tolerance_pct: Optional[float] = None,
    reference_length_mm: Optional[float] = None,
    reference_pixels: Optional[float] = None,
    image: UploadFile = File(...),
) -> JSONResponse:
    content = image.file.read()
    frame = jpeg_bytes_to_frame(content)
    request = AnalyzeRequest(
        thread_type=thread_type,
        tolerance_pct=tolerance_pct,
        reference_length_mm=reference_length_mm,
        reference_pixels=reference_pixels,
    )
    return _run_analysis(request, frame)


# Advanced batch processing
@app.post("/batch/process")
async def batch_process(
    images: List[UploadFile] = File(...),
    thread_type: str = Form("M10"),
    tolerance_pct: Optional[float] = Form(None),
    auto_calibrate: bool = Form(False),
) -> Dict[str, Any]:
    """Process multiple images in batch."""
    if not images:
        raise HTTPException(status_code=400, detail="No images provided")
    
    results = []
    failed = []
    
    for idx, image in enumerate(images):
        try:
            content = image.file.read()
            frame = jpeg_bytes_to_frame(content)
            analyze_req = AnalyzeRequest(
                thread_type=thread_type,
                tolerance_pct=tolerance_pct,
            )
            result = _run_analysis(analyze_req, frame, include_quality=True)
            results.append(json.loads(result.body))
        except Exception as e:
            failed.append({"index": idx, "filename": image.filename, "error": str(e)})
    
    pass_count = sum(1 for r in results if r.get("final_decision") == "PASS")
    fail_count = sum(1 for r in results if r.get("final_decision") == "FAIL")
    
    return {
        "summary": {
            "total": len(results),
            "pass": pass_count,
            "fail": fail_count,
            "pass_percentage": round(pass_count / len(results) * 100, 2) if results else 0,
            "failed_uploads": len(failed),
            "thread_type": thread_type,
            "tolerance_pct": tolerance_pct,
            "auto_calibrate": auto_calibrate,
        },
        "results": results,
        "failed": failed,
    }


@app.get("/batch/status")
def batch_status() -> Dict[str, Any]:
    """Get batch processing status and history."""
    batch_files = list(BATCH_DIR.glob("*.jpg"))
    return {
        "pending_images": len(batch_files),
        "batch_dir": str(BATCH_DIR),
        "images": [f.name for f in batch_files[:20]]
    }


@app.get("/result")
def latest_result() -> Dict[str, Any]:
    if state["latest_result"] is not None:
        return state["latest_result"]

    db_result = get_latest_result()
    if db_result is None:
        return {"message": "No inspection run yet"}
    return db_result


@app.get("/stats")
def stats() -> Dict[str, Any]:
    stat = get_stats()
    stat["recent_logs"] = get_recent_logs(limit=12)
    stat["performance_metrics"] = state["performance_metrics"]
    return stat


@app.get("/settings")
def settings() -> Dict[str, Any]:
    return get_all_settings()


@app.post("/settings")
def update_settings(update: SettingsUpdate) -> Dict[str, str]:
    data = update.model_dump(exclude_none=True)
    if not data:
        return {"message": "No settings updated"}

    for key, value in data.items():
        set_setting(key, value)

    if "camera_source" in data:
        success = camera_service.start(str(data["camera_source"]))
        if not success:
            return {"message": f"Settings updated but camera start failed", "camera_ok": False}

    return {"message": "Settings updated", "camera_ok": True}


@app.get("/export/csv")
def export_csv() -> FileResponse:
    path = export_inspections_csv(EXPORT_DIR / f"inspection_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    return FileResponse(path=path, filename=path.name, media_type="text/csv")


@app.get("/performance")
def get_performance() -> Dict[str, Any]:
    """Get system performance metrics."""
    return {
        "metrics": state["performance_metrics"],
        "camera_info": {
            "available": camera_service.capture is not None,
            "frame_count": camera_service.frame_count,
        }
    }


@app.get("/video_feed")
def video_feed() -> StreamingResponse:
    def generate():
        while True:
            try:
                frame = camera_service.read_frame()
                jpg = frame_to_jpeg_bytes(frame)
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
                )
                time.sleep(0.05)
            except Exception:
                time.sleep(0.2)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
