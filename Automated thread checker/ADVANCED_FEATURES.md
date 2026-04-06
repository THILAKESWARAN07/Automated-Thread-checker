# v2.0 ADVANCED FEATURES GUIDE

Complete documentation for all advanced features in Automated Thread Checking System v2.0.

## Table of Contents

1. [Mobile Camera Support](#mobile-camera-support)
2. [Batch Processing](#batch-processing)
3. [Image Quality Assessment](#image-quality-assessment)
4. [Performance Metrics](#performance-metrics)
5. [Camera Management](#camera-management)
6. [API Reference](#api-reference)
7. [Advanced Workflows](#advanced-workflows)
8. [Troubleshooting](#troubleshooting)

---

## Mobile Camera Support

### Overview

The v2.0 system supports multiple camera types:
- **Local cameras**: Built-in webcams, USB cameras (Camera 0, 1, 2, etc.)
- **IP cameras**: MJPEG streams from smartphones or dedicated IP cameras
- **File inputs**: Direct image/video file paths
- **Dynamic switching**: Change cameras without restarting

### Setup: Using Smartphone as Camera

#### Android with IP Webcam App

1. **Install IP Webcam** (free app on Google Play):
   - Search for "IP Webcam"
   - Install by App Maker
   - Launch app on phone

2. **Get Camera URL**:
   - Open app
   - Note the IP address shown (e.g., 192.168.1.100:8080)
   - Enable video stream
   - URL format: `http://192.168.1.100:8080/video`

3. **Connect in Dashboard**:
   - Select "Custom IP Camera" from camera dropdown
   - Enter: `http://192.168.1.100:8080/video`
   - Click "Test Camera"
   - Once verified, system auto-connects

#### iOS with Alternatives

1. **Option 1 - Continuity Camera** (Apple devices connected to Mac):
   - Automatically available in system
   - Select from camera list

2. **Option 2 - Third-party MJPEG app**:
   - Search "IP Webcam" on App Store
   - Follow same steps as Android

#### Network Requirements

- **Same LAN**: Phone and computer on same WiFi network
- **IP Range**: Ensure both devices can communicate (not isolated VLANs)
- **Firewall**: May need to allow app port through firewall
- **Stability**: 2G/3G minimum (5G recommended for batch processing)

### Camera Detection

The system can auto-detect available cameras:

1. **In Dashboard**:
   - Click "Scan Cameras" button
   - Wait 2-3 seconds for scan
   - View list of detected cameras
   - Click camera to select

2. **Via API**:
```bash
curl "http://127.0.0.1:8000/cameras/available"
```

Response:
```json
{
  "cameras": [
    {
      "id": 0,
      "name": "Camera 0",
      "type": "local_camera",
      "status": "available",
      "resolution": {"width": 1280, "height": 720}
    }
  ],
  "count": 1
}
```

### Camera Testing

Before using a camera for inspection:

1. **In Dashboard**:
   - Select camera from dropdown
   - Click "Test Camera"
   - Status shows: ✓ Available or ✗ Failed

2. **Via API**:
```bash
# Test local camera
curl -X POST "http://127.0.0.1:8000/cameras/test?url=0"

# Test IP camera
curl -X POST "http://127.0.0.1:8000/cameras/test?url=http://192.168.1.100:8080/video"
```

---

## Batch Processing

### Overview

Process 100s of images at once with automatic quality analysis and decision making.

### Workflow

1. **Prepare Images**:
   - Collect images in folder
   - Supported formats: JPEG, PNG
   - Any resolution (auto-resized)

2. **Upload**:
   - Click "Batch Upload" in dashboard
   - Select multiple files (Ctrl+Click)
   - Configure settings:
     - Thread Type (M8, M10, M12)
     - Tolerance %
   - Click "Process Batch"

3. **Monitor Progress**:
   - Progress bar shows completion %
   - Real-time image count
   - Auto-pauses on error

4. **Review Results**:
   - Summary statistics
   - Individual results for each image
   - Failed uploads listed with error

### Batch Settings

```javascript
{
  "thread_type": "M10",        // Standard type
  "tolerance_pct": 8.0,        // Tolerance percentage
  "auto_calibrate": false      // Future: auto-calibration from batch
}
```

### Performance

- **Speed**: ~200-500ms per image depending on hardware
- **Batch Size**: Recommended 50-500 images per batch
- **Memory**: ~200MB for 100 images
- **Output**: All results stored in database + individual overlays

### Example: 100-Image Batch

```bash
# Create 100 test images first
for i in {1..100}; do
  cp sample_image.jpg batch_images/image_$i.jpg
done

# Process via API
curl -X POST "http://127.0.0.1:8000/batch/process" \
  -F "images=@batch_images/image_1.jpg" \
  -F "images=@batch_images/image_2.jpg" \
  ... (repeat for all 100) \
  -F "thread_type=M10" \
  -F "tolerance_pct=8"
```

Response:
```json
{
  "summary": {
    "total": 100,
    "pass": 87,
    "fail": 13,
    "pass_percentage": 87.0,
    "failed_uploads": 0
  },
  "results": [ /* array of 100 results */ ],
  "failed": []
}
```

---

## Image Quality Assessment

### Quality Metrics

The system analyzes three key metrics:

#### 1. Sharpness (Laplacian Variance)
- **Measures**: Image focus clarity
- **Low**: Blurry, out-of-focus images
- **High**: Sharp, focused images
- **Formula**: Variance of Laplacian edge detection

#### 2. Brightness
- **Measures**: Overall illumination level
- **Optimal**: 80-180 out of 255
- **Too Dark**: <80 (underexposed)
- **Too Bright**: >180 (overexposed)

#### 3. Contrast
- **Measures**: Difference between light and dark areas
- **Low**: Flat, washed-out images
- **High**: Good detail visibility
- **Formula**: Standard deviation of pixel intensities

### Quality Score

Final score (0-100) calculated as:
```
quality_score = (sharpness * 0.5) + ((100 - brightness) * 0.2) + (contrast * 0.3)
```

### Recommendations

| Score | Rating | Recommendation |
|-------|--------|-----------------|
| 80-100 | Excellent | Ready for inspection |
| 60-79 | Good | Proceed with caution |
| 40-59 | Fair | May affect accuracy |
| 0-39 | Poor | Adjust lighting/camera |

### Image Quality Check

1. **In Dashboard**:
   - Click "Check Quality" button
   - See quality score, metrics, recommendation
   - Visual bar shows quality level

2. **During Inspection**:
   - Quality automatically assessed
   - Included in results
   - Warnings for poor quality

3. **Via API**:
```bash
curl "http://127.0.0.1:8000/image/quality"
```

Response:
```json
{
  "sharpness": 85.5,
  "brightness": 72.3,
  "contrast": 68.9,
  "quality_score": 76.2,
  "recommendation": "Good - proceed with caution"
}
```

### Improving Image Quality

| Issue | Solution |
|-------|----------|
| Low Sharpness | - Clean camera lens<br>- Increase focus distance<br>- Improve lighting |
| Too Dark | - Add more light<br>- Increase camera brightness setting<br>- Move light source closer |
| Too Bright | - Reduce light intensity<br>- Adjust camera exposure<br>- Move to less bright area |
| Low Contrast | - Improve lighting angle<br>- Use shadow reduction<br>- Adjust camera contrast |

---

## Performance Metrics

### Real-time Metrics

The system tracks performance automatically:

1. **Total Inspections**: Cumulative count of all inspections
2. **Images Processed**: Total images analyzed
3. **Average Analysis Time**: Per-image analysis speed (ms)
4. **Frame Count**: Total frames captured from camera

### Viewing Metrics

1. **In Dashboard**:
   - Click "📊 View Performance"
   - See performance modal
   - Real-time updates

2. **Via API**:
```bash
curl "http://127.0.0.1:8000/performance"
```

Response:
```json
{
  "metrics": {
    "avg_analysis_time_ms": 245.5,
    "total_inspections": 352,
    "images_processed": 352
  },
  "camera_info": {
    "available": true,
    "frame_count": 18543
  }
}
```

### Performance Analysis

| Metric | Good | Acceptable | Poor |
|--------|------|-----------|------|
| Analysis Time | <100ms | 100-300ms | >300ms |
| Frames/Sec | >15fps | 10-15fps | <10fps |
| Quality Score | >75 | 60-75 | <60 |

### Optimization Tips

- **Faster Analysis**:
  - Reduce image resolution
  - Use GPU acceleration (if available)
  - Close other applications

- **Better Quality**:
  - Improve lighting
  - Use higher-resolution camera
  - Reduce camera motion

- **Higher Throughput**:
  - Use batch processing
  - Increase tolerance (if acceptable)
  - Use smaller image sizes

---

## Camera Management

### Advanced Camera API

#### Get Available Cameras
```python
GET /cameras/available
```
Returns list of detected local cameras with resolution info.

#### Test Camera Connection
```python
POST /cameras/test?url=<camera_source>
```
Returns: `{"status": "ok/error", "message": "...", "info": {...}}`

#### Switch Active Camera
```python
POST /settings
{
  "camera_source": "0"  // or IP camera URL
}
```

### Camera Configuration

Store in settings:
```python
{
  "camera_source": "0",  // or "http://ip:port/stream"
  "camera_index": 0,
  "camera_resolution": "1280x720"  // optional
}
```

### Troubleshooting Cameras

#### Local Camera Not Working
```bash
# Check available cameras
curl "http://127.0.0.1:8000/cameras/available"

# Test specific camera
curl -X POST "http://127.0.0.1:8000/cameras/test?url=0"
curl -X POST "http://127.0.0.1:8000/cameras/test?url=1"
```

#### IP Camera Not Connecting
```bash
# Test connectivity
curl -X POST "http://127.0.0.1:8000/cameras/test?url=http://192.168.1.100:8080/video"

# Verify network
ping 192.168.1.100

# Check firewall
# Ensure port 8080 is accessible
```

---

## API Reference

### New v2.0 Endpoints

#### Camera Endpoints

**GET /cameras/available**
- Lists all available local cameras
- Response: `{"cameras": [...], "count": 0}`

**POST /cameras/test**
- Tests camera connectivity
- Query: `url` (camera index or URL)
- Response: `{"status": "ok/error", ...}`

#### Quality Endpoints

**GET /image/quality**
- Analyzes current camera feed
- Response: Quality metrics and score

#### Batch Endpoints

**POST /batch/process**
- Processes multiple images in batch
- Multipart form data with images
- Response: Summary + individual results

**GET /batch/status**
- Gets batch processing status
- Response: Pending images, status info

#### Performance Endpoints

**GET /performance**
- Gets system performance metrics
- Response: Metrics and camera info

### Request/Response Examples

#### Batch Process Request
```bash
curl -X POST "http://127.0.0.1:8000/batch/process" \
  -F "images=@image1.jpg" \
  -F "images=@image2.jpg" \
  -F "thread_type=M10" \
  -F "tolerance_pct=8"
```

#### Batch Process Response
```json
{
  "summary": {
    "total": 2,
    "pass": 1,
    "fail": 1,
    "pass_percentage": 50.0,
    "failed_uploads": 0
  },
  "results": [
    {
      "id": 1,
      "final_decision": "PASS",
      "pitch_mm": 1.534,
      ...
    }
  ],
  "failed": []
}
```

---

## Advanced Workflows

### Workflow 1: Mobile Camera Quality Control

**Scenario**: Use smartphone as camera for real-time quality inspection

1. **Setup**:
   - Install IP Webcam on phone
   - Get IP address (e.g., 192.168.1.100:8080)
   - Connect in dashboard

2. **Inspect**:
   - Check quality (should be >70)
   - Capture frames
   - Automatically analyze
   - View results

3. **Optimize**:
   - If quality low, adjust lighting
   - Reposition phone/light
   - Check quality again

### Workflow 2: High-Volume Batch Processing

**Scenario**: Process 500 thread images overnight

1. **Prepare**:
   - Organize images in folder
   - Ensure consistent resolution
   - Name logically (thread_0001.jpg, etc.)

2. **Upload**:
   - Select all images
   - Set tolerance based on standard
   - Start batch processing
   - System processes while you work

3. **Analyze Results**:
   - View aggregate statistics
   - Export detailed results to CSV
   - Review failed images

### Workflow 3: Quality-Based Filtering

**Scenario**: Only process high-quality images

1. **Check Quality First**:
   - "Check Quality" button
   - If score <70, adjust camera
   - Repeat until satisfied

2. **Batch with Quality Check**:
   - Quality automatically assessed per image
   - Poor quality images marked for review
   - Results include quality metrics

3. **Selective Processing**:
   - Use quality score to filter results
   - Export only high-quality inspections

### Workflow 4: Multi-Camera Comparison

**Scenario**: Compare webcam vs phone camera

1. **Setup Cameras**:
   - Configure local webcam (Camera 0)
   - Configure mobile phone (Custom IP)

2. **Capture Same Scene**:
   - Capture with webcam
   - Analyze and record quality
   - Switch to mobile camera
   - Capture same scene
   - Analyze and compare

3. **Evaluate**:
   - Compare analysis times
   - Compare quality scores
   - Compare inspection results
   - Choose best camera

---

## Troubleshooting

### Common Issues

#### "Camera not initialized" Error
```
Problem: Camera won't connect
Solution: 
1. Check camera index (0, 1, 2)
2. Verify device is not in use
3. Try different index
4. Restart application
```

#### "Failed to read frame from camera" Error
```
Problem: Frame capture fails
Solution:
1. Camera may have disconnected
2. Try to reconnect: Settings > Update camera source
3. Check if camera app is running (close it)
4. Plug camera in again if USB
```

#### Low Image Quality Warning
```
Problem: Quality score <60
Solution:
1. Improve lighting (add light source)
2. Clean camera lens
3. Reduce distance to object (~15-20cm optimal)
4. Avoid shadows on object
5. Use higher-resolution camera if available
```

#### Batch Processing Slow
```
Problem: Batch processing taking too long
Solution:
1. Close other applications
2. Check CPU usage (should be <90%)
3. Reduce image resolution if possible
4. Process in smaller batches (50-100 images)
5. Check average time per image in metrics
```

#### IP Camera Connection Failed
```
Problem: Can't connect to mobile camera
Solution:
1. Verify phone IP: Settings > About Phone > IP Address
2. Check firewall: Allow port 8080
3. Verify same WiFi: Both devices on same network
4. Test URL directly in browser: http://192.168.x.x:8080/video
5. Restart IP Webcam app
6. Check app permissions
```

#### Different Results on Same Image
```
Problem: Results vary between captures
Solution:
1. Variations normal due to image capture differences
2. Tolerance covers acceptable variation
3. Ensure consistent lighting
4. Ensure camera stable (use tripod)
5. Take multiple captures for averaging
```

---

## Performance Benchmarks

### Single Image Analysis
- **Average Time**: 150-400ms
- **Resolution**: 640x480 @ 100ms, 1920x1080 @ 350ms
- **Bottleneck**: CNN inference time

### Batch Processing (100 images)
- **Total Time**: 15-40 seconds
- **Per Image**: 150-400ms
- **Throughput**: 2.5-6.7 images/second

### Camera Streaming
- **FPS**: 10-30 fps depending on camera
- **Latency**: 100-500ms
- **Bandwidth**: 2-5 Mbps for 1080p MJPEG

### Quality Assessment
- **Check Time**: 50-150ms
- **Overhead**: <10% of analysis time
- **Accuracy**: 95%+ consistency

---

## Maintenance

### Data Cleanup

```python
# Clear old inspections from database
DELETE FROM inspections WHERE timestamp < date('now', '-30 days')

# Delete failed images older than 7 days
rm -r data/failed/*  # or use Windows file explorer
```

### Database Optimization

```bash
# Vacuum database (reduce size)
sqlite3 data/thread_inspection.db "VACUUM"

# Analyze and optimize
sqlite3 data/thread_inspection.db "ANALYZE"
```

### Log Rotation

Set up log rotation for production:
```bash
# Linux: use logrotate
# Windows: use Windows Event Viewer
```

---

## Support & Resources

- Full API docs: http://127.0.0.1:8000/docs
- OpenCV docs: https://docs.opencv.org/
- FastAPI docs: https://fastapi.tiangolo.com/
- TensorFlow docs: https://www.tensorflow.org/docs

For bug reports, include:
- System info (Windows/Linux, Python version)
- Error message and traceback
- Screenshot of UI (if applicable)
- API response (if API call failed)
