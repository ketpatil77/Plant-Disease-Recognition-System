# Comprehensive Testing & Deployment Guide

## Pre-Flight Checklist ✈️

Before running the application, ensure:

- [ ] Windows 10 or 11 system
- [ ] Python 3.8+ installed and in PATH (`python --version` in cmd should work)
- [ ] No existing Flask process on port 5000 (`netstat -ano | findstr :5000` returns nothing)
- [ ] At least 500MB free disk space
- [ ] All files from this archive present

## Step 1: Quick Validation Tests

### 1.1 Check Python Installation
```bash
# Open Command Prompt and run:
python --version
# Should show: Python 3.x.x

python -c "import sys; print(sys.executable)"
# Shows full path to Python executable
```

**Expected Result**: Python version 3.8 or higher, valid path returned

### 1.2 Verify Project Structure
```bash
cd "f:\PROJECT AGRO\Plant-Disease-Recognition-System"
dir
```

**Expected files/folders**:
```
app.py
START.bat
requirements.txt
config.json (newly created)
FIXES_APPLIED.md (newly created)
backend/
  inference.py
  model.py
  metadata.py
  reports.py
  __init__.py
models/
  plant_disease_model_1_latest.pt
templates/
static/
```

**Critical**: If `models/plant_disease_model_1_latest.pt` is missing, the application will not start.

### 1.3 Check Model File
```bash
# List model file with size
dir models\plant_disease_model_1_latest.pt /v
```

**Expected Result**: File exists, size typically 15-30MB for CNN model

## Step 2: Automated Startup Test

### 2.1 Run START.bat
```bash
cd "f:\PROJECT AGRO\Plant-Disease-Recognition-System"
START.bat
```

**During execution, you should see**:
```
Checking Python installation...
Looking for virtual environment...
Creating virtual environment...
[If venv doesn't exist]

Activating virtual environment...
Installing/updating dependencies from requirements.txt...
[pip installs packages]

Starting Plant Disease Recognition System...
Launching Flask server...
Waiting for server to initialize...
Opening browser...
Application opened in browser. Server is running in the background.
```

**Timing**: Process should complete in 30-60 seconds (first run takes longer for venv setup)

### 2.2 Verify Browser Opens
The application should automatically open in your default browser to `http://localhost:5000`

**If browser doesn't open automatically**:
1. Open browser manually
2. Navigate to `http://localhost:5000`
3. Check if plant disease app loads

## Step 3: Application Health Check

### 3.1 Check Application Startup Status
After START.bat completes, navigate to: `http://localhost:5000/api/health`

**Expected JSON Response**:
```json
{
  "ok": true,
  "model_path": "f:\\PROJECT AGRO\\Plant-Disease-Recognition-System\\models\\plant_disease_model_1_latest.pt",
  "startup_error": null
}
```

**If `startup_error` is not null**:
- Check the error message in the JSON
- Common errors:
  - `"Model file not found: ..."` → Verify model file exists at correct path
  - `"RuntimeError: Numpy is not available"` → Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
  - Permission denied → Check folder permissions

### 3.2 Check Home Page
Navigate to: `http://localhost:5000/`

**Expected**: 
- Page loads without JavaScript errors (check browser console: F12 → Console tab)
- Shows Plant Disease Recognition UI
- Weather data displays
- Navigation menu functional

## Step 4: Core Functionality Tests

### 4.1 Test Image Upload (Scanner)
1. Navigate to: `http://localhost:5000/scanner`
2. Click "Take Photo" or "Upload Image"
3. Select a plant disease image from disk (recommendations):
   - Tomato leaf blight
   - Apple scab
   - Corn rust
   - Any RGB image 100x100px to 2MB
4. Wait for prediction (typically 1-2 seconds)

**Expected Result**:
- Image displays in preview
- Disease name shows (e.g., "Tomato___Late_blight")
- Confidence percentage displays (90-99% is typical)
- Disease information (description, remedies) shows
- Can click to view detailed disease library

**If failed (red error box)**:
- **"Image is too large"**: File exceeds 2MB limit. Choose smaller file.
- **"Unsupported file type"**: Must be JPEG, PNG, or WEBP. Verify file extension.
- **"Uploaded file is not a valid image"**: File is corrupted. Try different image.
- **"Model is unavailable"**: Check `/api/health` endpoint for startup_error

### 4.2 Test Upload Size Validation
1. Create a test file > 2MB (e.g., copy large video or image and rename)
2. Try uploading at `http://localhost:5000/scanner`

**Expected Result**:
- Error message: "Image is too large. Upload a JPEG or PNG up to 2MB."
- HTTP 413 status (check network tab)

### 4.3 Test History Function
1. After prediction, navigate to: `http://localhost:5000/history`
2. Verify prediction appears in list with:
   - Date/time of prediction
   - Disease name
   - Confidence score
   - Thumbnail of image

**Expected**: Predictions persist and can be clicked to view full details

### 4.4 Test Prediction API (programmatic)
If you have curl or Postman:

```bash
# Replace with actual image path
curl -X POST http://localhost:5000/api/predict ^
  -F "image=@path/to/image.jpg"
```

**Expected JSON Response**:
```json
{
  "ok": true,
  "prediction_payload": {
    "class_name": "Tomato___Late_blight",
    "confidence": 95.3,
    "disease_info": {
      "description": "...",
      "remedies": [...]
    },
    "image_url": "/uploadimages/abc123.jpg"
  }
}
```

## Step 5: Advanced Diagnostics

### 5.1 Check Server Logs
```bash
# Open server log file
type "logs\backend.log"
# Or tail in PowerShell:
Get-Content "logs\backend.log" -Wait
```

**Expected log entries** (when everything works):
```
START Backend service initialized
INFO Model loaded successfully from f:\PROJECT AGRO\Plant-Disease-Recognition-System\models\plant_disease_model_1_latest.pt
INFO Generated random SECRET_KEY for session security
INFO Your uploaded image received...
```

**Problem indicators** (errors in log):
```
ERROR Model failed to load from ...
ERROR Failed to create required directories: ...
ERROR Unexpected prediction failure: ...
```

### 5.2 Check Browser Console for Errors
While app is running:
1. Press F12 to open Developer Tools
2. Click "Console" tab
3. Perform an action (upload image, navigate page)
4. Look for red error messages

**Common issues and solutions**:
- `CORS error` → Usually harmless, check /api/health works
- `Failed to load resource: the server responded with a status of 500` → Check logs
- `Uncaught ReferenceError` → JavaScript issue, unlikely with current code

### 5.3 Check Network Requests
1. Press F12 → Network tab
2. Upload an image
3. Look for POST requests to `/upload/` or `/api/predict`
4. Click the request to see:
   - Request headers
   - Response headers (should include `Content-Type: application/json`)
   - Response body (should be JSON with prediction)

**Expected Status Codes**:
- 200 OK → Prediction successful
- 302 Found → Redirect to /prediction page (expected for form POST)
- 400 Bad Request → Missing/invalid image file
- 413 Payload Too Large → File exceeds 2MB
- 500 Internal Server Error → Check logs for details

## Step 6: Performance Baselines

For reference, expected performance metrics:

| Operation | Expected Time | Max Acceptable |
|-----------|---------------|----------------|
| START.bat (first run) | 45-60s | 120s |
| START.bat (subsequent runs) | 15-30s | 45s |
| Model load at startup | 2-5s | 10s |
| Single image prediction | 0.5-1.5s | 3s |
| Browser page load | <500ms | 2s |
| History page load | <300ms | 1s |

## Troubleshooting Decision Tree

### Issue: START.bat exits with code 1
**Diagnosis**:
1. Check batch window for error message
2. Run `python --version` - if fails, Python not in PATH
3. Look in `.bat` file - check which line failed

**Solutions**:
- Add Python to System PATH (Windows Settings → Environment Variables)
- Or specify full path: `C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe`

### Issue: "Model startup failed" error in browser
**Diagnosis**: Check `/api/health` endpoint

**If startup_error says "Model file not found"**:
- Verify file exists: `dir models\plant_disease_model_1_latest.pt`
- Check file path in app.py matches actual location
- Ensure file isn't corrupted (copy from backup if available)

**If startup_error says "RuntimeError"**:
- Reinstall PyTorch and dependencies:
  ```bash
  pip uninstall torch torchvision numpy -y
  pip install torch==2.2.2 torchvision==0.17.2 numpy>=1.26.0,<2
  ```

### Issue: Prediction fails with "Numpy is not available"
**Solution**: 
- Force reinstall dependencies:
  ```bash
  pip install -r requirements.txt --force-reinstall --no-cache-dir
  ```
- This may take 5-10 minutes but ensures clean install

### Issue: "Image is too large" for 1MB file
**Diagnosis**: MAX_UPLOAD_SIZE might not be set correctly

**Solution**:
1. Check `app.py` line 30: should show `MAX_UPLOAD_SIZE = 2 * 1024 * 1024`
2. Restart Flask: Close browser, close START.bat window, run START.bat again

### Issue: Browser doesn't auto-open
**Diagnosis**: Windows batch `start` command might not be finding default browser

**Solutions**:
1. Manual workaround: Open browser, go to `http://localhost:5000`
2. Check Windows registry: Search for `http` protocol handler in HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.htm\UserChoice

### Issue: Port 5000 already in use
**Diagnosis**: Another application is using port 5000

**Solutions**:
1. Find and close the process:
   ```bash
   netstat -ano | findstr :5000
   # Note the PID from output
   taskkill /PID <PID> /F
   ```
2. Or modify app.py to use different port and update browser URL accordingly

## Success Indicators ✅

You'll know everything is working correctly when:

1. [ ] START.bat completes with no errors
2. [ ] Browser opens automatically to http://localhost:5000
3. [ ] `/api/health` returns `"ok": true` and `"startup_error": null`
4. [ ] Home page loads with UI elements visible
5. [ ] Scanner page loads with upload interface
6. [ ] Can upload plant image and get prediction back within 2 seconds
7. [ ] Prediction shows disease name, confidence, and remedies
8. [ ] Uploading 2MB+ file shows appropriate error
9. [ ] History page shows past predictions
10. [ ] Console has no JavaScript errors (F12 → Console tab)

## Deployment Ready Checklist

When all tests pass, your system is production-ready:

- [ ] All fixes verified and working
- [ ] Model file exists and loads successfully
- [ ] Predictions accurate for known test cases
- [ ] Upload validation works (size, format)
- [ ] Error messages clear and helpful
- [ ] Performance acceptable (< 2s per prediction)
- [ ] No security warnings in browser
- [ ] Startup automated via START.bat

## Next Steps

1. **Regular Testing**: Run predictions weekly with known test cases to ensure model performance
2. **Monitor Logs**: Check `logs/backend.log` periodically for errors
3. **User Training**: Show end users how to use scanner, history, and disease library
4. **Backup Model**: Keep backup of `models/plant_disease_model_1_latest.pt` file
5. **Update Config**: Keep `config.json` updated with latest disease info and market data

---

**Need Help?**

If issues persist after following this guide:
1. Check `/api/health` endpoint - provides detailed error info
2. Check `logs/backend.log` - contains server errors
3. Check browser console (F12) - shows client-side errors
4. Review FIXES_APPLIED.md for recent changes
5. Compare with AUDIT_REPORT.md for known issues
