# Plant Disease Recognition System

Farmer-oriented Flask and PyTorch application for crop disease detection, local guidance, and report generation. Built for practical use with image upload, prediction flow, Marathi-ready UX, weather context, and offline-friendly startup path.

## What It Does

- Accepts plant leaf images and runs disease prediction through local model inference.
- Returns disease label, confidence, and guidance for next action.
- Adds local weather context and market-oriented support data.
- Generates downloadable reports for field use and follow-up.
- Supports simple Windows startup through `START.bat`.

## Core Stack

- Python
- Flask
- PyTorch
- Pillow
- NumPy

## Project Structure

```text
Plant-Disease-Recognition-System/
  app.py
  backend/
  models/
  static/
  templates/
  uploadimages/
  START.bat
  requirements.txt
```

## Run Locally

Requirements:

- Python 3
- Model file at `models/plant_disease_model_1_latest.pt`

Install dependencies:

```bash
pip install -r requirements.txt
```

Start app:

```bat
START.bat
```

Manual fallback:

```bash
python app.py
```

Default local URL:

```text
http://127.0.0.1:5000
```

## Product Value

- Turns raw model output into usable guidance for farmers.
- Keeps workflow simple for local laptop deployment.
- Extends disease prediction with weather and report context instead of one-screen classification only.

## Current Repo Notes

- Main entrypoint: `app.py`
- Startup helper: `START.bat`
- Inference and service logic: `backend/`
- Model asset expected locally; repo does not auto-download it
