# Quick Start Guide - v2.0 Advanced

Get the Automated Thread Checking System up and running in 5 minutes!

## Step 1: Initial Setup (3 minutes)

### 1.1 Open PowerShell
- Press `Win + X`, select "Windows PowerShell (Admin)"
- Navigate to project folder:
```powershell
cd "C:\Users\HP\OneDrive\Documents\Automated-Thread-checker\Automated thread checker"
```

If you moved the project folder recently, recreate the virtual environment so it points to the current location:
```powershell
if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }
python -m venv .venv
```

### 1.2 Create & Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

You should see `(.venv)` in the prompt.

### 1.3 Install Dependencies
```powershell
pip install -r requirements.txt
```

Wait ~2 minutes for installation to complete.

## Step 2: Start the System (2 minutes)

### 2.1 Start Backend
```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 2.2 Open Frontend in Browser
- Open file: `frontend/index.html` 
- Or navigate to: `http://127.0.0.1:8000`

You should see the dashboard with: **Hero banner v2.0 ADVANCED**

## Step 3: First Inspection (2 minutes)

### 3.1 Check Camera
- Look for "Camera Status" indicator (should show "Connected")
- If it shows "Disconnected":
  - Click "Scan Cameras"
  - Select your camera
  - Click "Test Camera"

### 3.2 Capture & Analyze
1. Click "📸 Capture Frame"
2. Click "🔍 Analyze"
3. View results in "Inspection Result" section
4. See pass/fail status
5. Check image quality score

**✓ You're ready!**

## Next Steps

### Use Mobile Phone as Camera
1. Install "IP Webcam" app on phone
2. Start the stream (note IP address)
3. In dashboard: Select "Custom IP Camera"
4. Enter phone URL: `http://192.168.1.100:8080/video`
5. Click "Test Camera"
6. Start using!

### Process Batch of Images
1. Click "📂 Batch Upload"
2. Select multiple images
3. Configure settings
4. Click "Process Batch"
5. Wait for results

### Check Performance
1. Click "📊 View Performance"
2. See metrics:
   - Total inspections
   - Average analysis time
   - Images processed

## Common Tasks

### Switch to Different Camera
```
1. Camera dropdown > Select camera
2. Click "Test Camera"
3. Done!
```

### Save Settings
```
1. Set tolerance in "Tolerance (%)"
2. Click "💾 Save Default Tolerance"
3. Settings saved!
```

### Export Results
```
1. Click "📥 Export CSV"
2. File downloads automatically
```

### Check Image Quality
```
1. Click "✓ Check Quality"
2. See quality score and recommendation
3. Adjust lighting if needed
```

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| Camera not showing | Click "Scan Cameras" and select from list |
| Quality score <60 | Add more light, clean lens, adjust distance |
| Slow analysis | Close other apps, check CPU usage |
| Mobile phone not connecting | Check phone IP, verify WiFi, restart app |
| Batch processing fails | Use smaller batches, check image formats |

## Environment Setup Info

- **Python**: Version 3.9+
- **Backend**: FastAPI + Uvicorn on port 8000
- **Frontend**: HTML5 + JavaScript
- **Database**: SQLite (auto-created in `data/`)
- **Models**: TensorFlow (auto-downloads on first run)

## Files & Directories

```
project/
├── backend/          # Python FastAPI backend
├── frontend/         # HTML/JS dashboard
├── models/           # AI models folder
├── data/             # Database & images
│   ├── images/       # Captured images
│   ├── failed/       # Failed inspections
│   └── exports/      # CSV exports
├── .venv/            # Virtual environment (auto-created)
└── README.md         # Full documentation
```

## Advanced Features

### 🎥 Camera Features
- Local webcams (Camera 0, 1, 2...)
- Mobile phone cameras (IP stream)
- Camera detection & testing
- Dynamic camera switching

### 📦 Batch Processing
- Process 100s of images at once
- Real-time progress tracking
- Aggregate statistics
- Error handling

### 📊 Quality Assessment
- Image sharpness analysis
- Brightness & contrast checking
- 0-100 quality score
- Recommendations

### 📈 Performance Metrics
- Real-time analysis speed
- Total inspections tracked
- Average time per image
- System performance dashboard

## API Quick Reference

### Live Feed
```
http://127.0.0.1:8000/video_feed
```

### API Documentation
```
http://127.0.0.1:8000/docs
```

### Sample API Calls

Check camera:
```bash
curl "http://127.0.0.1:8000/cameras/available"
```

Check quality:
```bash
curl "http://127.0.0.1:8000/image/quality"
```

Get performance:
```bash
curl "http://127.0.0.1:8000/performance"
```

Get stats:
```bash
curl "http://127.0.0.1:8000/stats"
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F5` | Refresh page |
| `Ctrl+Shift+I` | Open developer tools |
| `Ctrl+Shift+M` | Mobile view |

## Tips & Tricks

- ⚡ **Speed Up**: Reduce image resolution in camera settings
- 🎥 **Better Quality**: Use tripod for stable camera
- 💡 **Lighting**: Use soft, consistent lighting (avoid shadows)
- 📱 **Mobile Setup**: Mount phone at 15-20cm from object
- 🔄 **Calibration**: Do it once per setup for best accuracy

## Next Reading

After quickstart, check:
1. [README.md](README.md) - Full documentation
2. [ADVANCED_FEATURES.md](ADVANCED_FEATURES.md) - Detailed feature guide
3. [API Docs](http://127.0.0.1:8000/docs) - Interactive API reference

## Support

### Common Issues
- Camera not detected → Use "Scan Cameras"
- Mobile camera won't connect → Check WiFi connection
- Slow processing → Use smaller batch or adjust image size
- Poor quality score → Improve lighting

### Information
- Version: 2.0 ADVANCED
- Status: ✓ Production Ready
- License: Open Source

---

**Ready?** Start with Step 1 above and you'll be inspecting threads in 5 minutes!
