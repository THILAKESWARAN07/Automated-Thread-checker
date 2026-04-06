# Automated Thread Checking System - v2.0 ADVANCED

Production-ready local project for threaded component inspection using OpenCV, CNN, FastAPI, SQLite, and a real-time advanced frontend dashboard with mobile camera and batch processing support.

## ✨ NEW IN v2.0 ADVANCED

### 🎥 Advanced Camera Support
- **Local Cameras**: Support for multiple local webcams/USB cameras (Camera 0, 1, 2...)
- **IP Cameras**: Full support for MJPEG/HTTP streams from mobile phones or IP cameras
- **Camera Detection**: Automatic camera scanning and availability checking
- **Camera Testing**: Built-in camera connectivity testing
- **Dynamic Camera Switching**: Switch between cameras on-the-fly without restarting

### 📦 Batch Processing
- **Multi-Image Processing**: Process 10s, 100s, or 1000s of images at once
- **Batch Upload**: Upload multiple images via web interface
- **Progress Tracking**: Real-time batch processing progress display
- **Batch Statistics**: Aggregate pass/fail rates for batch runs
- **Error Handling**: Gracefully handle failed images without stopping batch

### 📊 Advanced Analytics & Quality Assessment
- **Image Quality Scoring**: Automated sharpness, brightness, contrast analysis (0-100 score)
- **Quality Recommendations**: Real-time suggestions to improve image quality
- **Performance Metrics**: Track analysis speed, images processed, total inspections
- **Time Tracking**: Per-image analysis time monitoring
- **Advanced Dashboard**: Visual quality indicators with color-coded feedback

### 🎛 Enhanced Detection & Inspection
- **Image Quality Check**: Endpoint to assess camera feed quality before capture
- **Quality Result Integration**: Quality metrics included in inspection results
- **Improved Error Handling**: Better feedback when cameras fail
- **Performance Monitoring**: Real-time performance dashboard

## Features

- Real-time camera feed from webcam, USB camera, or IP/mobile camera
- Frame capture and on-demand analysis
- OpenCV pipeline: grayscale, Gaussian blur, Canny edges, contours
- Feature extraction: thread pitch and diameter estimation
- Calibration from pixel to mm using reference object
- Rule engine with tolerance and thread standards
- CNN-based GOOD/DEFECT classification with fallback heuristic
- Final decision engine: PASS/FAIL with quality assessment
- SQLite storage of all inspections
- **Advanced API endpoints** for camera, quality, batch, and performance
- FastAPI endpoints for capture, analyze, result, stats, settings, export
- **Batch processing** for high-volume inspection
- Dashboard with live feed, metrics, logs, analytics, and Chart.js charts
- Failed image storage and CSV export
- **Mobile camera support** and dynamic camera selection

## Project Structure

```text
project/
├── backend/
│   ├── __init__.py
│   ├── main.py (ENHANCED v2.0)
│   ├── vision.py
│   ├── ai_model.py
│   ├── train_model.py
│   ├── sample_dataset.py
│   └── database.py
├── frontend/
│   ├── index.html (ENHANCED v2.0)
│   ├── style.css (ENHANCED v2.0)
│   └── script.js (ENHANCED v2.0)
├── models/
│   └── README.md
├── data/
│   ├── images/
│   ├── batch/
│   ├── failed/
│   ├── exports/
│   └── images/
├── requirements.txt
└── README.md
```

## Setup (Windows PowerShell)

### 1. Create Virtual Environment

```powershell
python -m venv .venv
```

### 2. Activate Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

## Optional: Create Sample Dataset + Train CNN

### 1. Generate Tiny Synthetic Dataset

```powershell
python -m backend.sample_dataset
```

This creates:
- `data/dataset/GOOD`
- `data/dataset/DEFECT`

### 2. Train CNN Model

```powershell
python -m backend.train_model
```

Trained model saves to: `models/thread_model.h5`

If no model exists, backend automatically uses heuristic fallback.

## Running the System

### 1. Start Backend API

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 2. Open Frontend Dashboard

Open in browser: `frontend/index.html`

Or open at: `http://127.0.0.1:8000` (if serving frontend from backend)

## Web API Endpoints (v2.0)

### Camera Management
- `GET /cameras/available` - List available local cameras
- `POST /cameras/test?url=<source>` - Test camera connectivity
- `GET /image/quality` - Check current camera feed quality

### Inspection
- `POST /capture` - Capture single frame
- `POST /analyze` - Analyze captured frame
- `POST /analyze_upload` - Upload image and analyze
- **NEW** `POST /batch/process` - Process multiple images in batch
- **NEW** `GET /batch/status` - Check batch processing status

### Results & Analytics
- `GET /result` - Get latest inspection result
- `GET /stats` - Get statistics and trend data
- **NEW** `GET /performance` - Get system performance metrics

### Settings
- `GET /settings` - Get all settings
- `POST /settings` - Update settings (including camera source)

### Data Export
- `GET /export/csv` - Export inspections to CSV
- `GET /video_feed` - MJPEG video stream

## Advanced Features Usage

### Using Mobile Phone as Camera

1. Install IP Camera app on mobile phone (e.g., "IP Webcam" - free Android app)
2. Start the camera stream (usually http://phone-ip:8080/video)
3. In dashboard, select "Custom IP Camera"
4. Enter camera URL: `http://192.168.1.100:8080/video`
5. Click "Test Camera" to verify connection
6. Once connected, use normally for inspection

### Batch Processing

1. Prepare images in a folder
2. Click "Batch Upload" button in dashboard
3. Select multiple images (CTRL+Click or SHIFT+Click)
4. Configure thread type and tolerance
5. Click "Process Batch"
6. Monitor progress in real-time
7. View batch summary with aggregate statistics

### Image Quality Assessment

1. Click "Check Quality" button
2. Dashboard shows quality score (0-100) with color coding:
   - Green (80+): Excellent
   - Yellow (60-79): Good
   - Red (<60): Poor - adjust lighting/camera
3. Recommendations displayed for improvement
4. Quality metrics included in inspection results

### Performance Monitoring

1. Click "View Performance" button
2. See real-time metrics:
   - Total inspections performed
   - Images processed
   - Average analysis time per image
3. Use for optimization and troubleshooting

### Camera Selection & Testing

1. Click "Scan Cameras" to auto-detect connected cameras
2. Select from detected cameras or enter custom IP camera URL
3. Click "Test Camera" to verify connection before using
4. Successful test automatically switches to selected camera

## Configuration

### Default Tolerance

Set in Settings tab, configurable per-session:

```javascript
default_tolerance_pct: 8.0  // % tolerance for thread standards
```

### Thread Standards

Edit in database or via API:

```python
thread_standards: {
  "M8": {"pitch_mm": 1.25, "diameter_mm": 8.0},
  "M10": {"pitch_mm": 1.5, "diameter_mm": 10.0},
  "M12": {"pitch_mm": 1.75, "diameter_mm": 12.0},
}
```

### Calibration

Done via reference object in UI:
1. Place known-size object in frame
2. Enter reference length (mm)
3. Measure reference in pixels from analysis overlay
4. Enter pixel measurement
5. System auto-calibrates: `mm/pixel = reference_length_mm / reference_pixels`

## API Examples

### Test Camera Availability

```bash
curl -X POST "http://127.0.0.1:8000/cameras/test?url=0"
# or
curl -X POST "http://127.0.0.1:8000/cameras/test?url=http://192.168.1.100:8080/video"
```

### Check Image Quality

```bash
curl "http://127.0.0.1:8000/image/quality"
```

### Process Batch

```bash
curl -X POST "http://127.0.0.1:8000/batch/process" \
  -F "images=@image1.jpg" \
  -F "images=@image2.jpg" \
  -F "thread_type=M10" \
  -F "tolerance_pct=8"
```

### Get Performance Metrics

```bash
curl "http://127.0.0.1:8000/performance"
```

## Technology Stack

- **Backend**: FastAPI, Uvicorn
- **Vision**: OpenCV 4.12.0.88
- **ML**: TensorFlow 2.20.0, Keras
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, JavaScript, Chart.js
- **Data**: NumPy, Pandas, scikit-learn

## Production Deployment

For production use:

1. Set environment variables:
   ```powershell
   $env:HOST = "0.0.0.0"
   $env:PORT = "8000"
   ```

2. Run with production server:
   ```powershell
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

3. Use reverse proxy (nginx/Apache) for HTTPS and load balancing

4. Store database and images in persistent volumes

## Troubleshooting

### Camera Not Detected
- Check device manager for camera driver
- Try different camera indices (0, 1, 2...)
- For IP camera, verify network connectivity and URL

### Poor Image Quality Warning
- Adjust lighting conditions
- Clean camera lens
- Reduce distance to thread components
- Check for motion blur

### Batch Processing Fails
- Verify image formats (JPEG, PNG supported)
- Check disk space for outputs
- Reduce batch size if memory issues

### Slow Analysis
- Check CPU usage (analyze_time_ms in results)
- Disable other applications
- Consider processing in smaller batches
- Use GPU acceleration if available

### Camera Keeps Disconnecting
- Check USB cable connection (for local cameras)
- Verify IP camera network stability
- Try different camera URL if IP camera
- Restart camera and browser

## Advanced Configuration

### Enable Debug Logging

In `main.py`, add:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Adjust Vision Pipeline

Edit thresholds in `backend/vision.py`:
- Canny edges: Adjust `(60, 180)` threshold values
- Contour filtering: Modify `cv2.contourArea(c) > 120` threshold
- Gaussian blur: Change `(5, 5)` kernel size

### Customize AI Model

Retrain in `backend/train_model.py`:
- Modify dataset generation in `sample_dataset.py`
- Adjust CNN architecture
- Change training epochs and batch size

## System Requirements

- **OS**: Windows 10/11 (also Linux/macOS compatible)
- **Python**: 3.9, 3.10, 3.11, 3.12
- **RAM**: 4GB minimum (8GB+ recommended)
- **Storage**: 500MB+ for models and data
- **Camera**: USB webcam, built-in camera, or IP camera (MJPEG)
- **Disk**: SSD recommended for batch processing

## License & Support

Production-ready system for automated quality inspection. Built with OpenCV, TensorFlow, and FastAPI.

For issues or improvements, check the logs and API documentation at `/docs` endpoint.

## Changelog

### v2.0 ADVANCED (Latest)
- ✅ Mobile camera (IP camera) support
- ✅ Batch image processing
- ✅ Image quality assessment
- ✅ Performance metrics tracking
- ✅ Camera detection and testing
- ✅ Enhanced UI with advanced controls
- ✅ Improved error handling and feedback
- ✅ Analysis time tracking

### v1.0 (Previous)
- Basic webcam support
- Single image analysis
- Rule-based decision engine
- CNN fallback to heuristic
- CSV export
- frontend/index.html

The frontend connects to API base URL:
- http://127.0.0.1:8000

## 7. Camera Integration Notes

Default camera source is webcam index 0.

To use DroidCam / IP camera:
1. Open dashboard.
2. Update `camera_source` using `/settings` API to your stream URL.
3. Example URL format: `http://192.168.x.x:4747/video`

## 8. API Endpoints

- `POST /capture` : capture frame from live camera
- `POST /analyze` : analyze latest frame or current camera frame
- `POST /analyze_upload` : analyze uploaded image
- `GET /result` : latest inspection result
- `GET /stats` : total/pass/fail/trend/recent logs
- `GET /settings` : current settings
- `POST /settings` : update tolerance/calibration/standards/camera
- `GET /export/csv` : export inspection table as CSV
- `GET /video_feed` : MJPEG live stream
- `GET /health` : health check

## 9. Decision Logic

- Rule-based `PASS` if pitch and diameter are within selected tolerance against thread standard.
- AI `GOOD/DEFECT` predicted by CNN or fallback heuristic.
- Final result:
  - `PASS` only when Rule=PASS and AI=GOOD
  - otherwise `FAIL`

## 10. Database Schema

SQLite DB path:
- data/inspections.db

Tables:
- `inspections`:
  - timestamp, thread_type, pitch_mm, diameter_mm,
  - ai_result, ai_confidence,
  - rule_result, final_decision,
  - image_path, notes
- `settings`:
  - key, value (JSON)

## 11. Testing Instructions

1. Start backend and open dashboard.
2. Click `Capture Frame`.
3. Click `Analyze`.
4. Verify:
- result badges update
- chart counters update
- log row is inserted
- image is saved under data/images
- failed image copied to data/failed when final decision is FAIL
5. Export CSV and verify download contains inspection rows.

## 12. Production Hardening Next

- Add JWT authentication on API routes
- Add model versioning and confidence threshold config
- Add better thread geometry extraction tuned for your part orientation
- Add unit tests for vision metrics and decision logic
- Replace SQLite with PostgreSQL for multi-user production
