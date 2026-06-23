# Architecture Overview

## Purpose

Plant Disease Recognition System helps users upload crop leaf images, run local disease inference, and receive practical guidance with weather and report context.

## System Shape

```text
User
  -> Flask web app
  -> image upload flow
  -> preprocessing helpers
  -> PyTorch model inference
  -> disease result, confidence, guidance, report
```

## Application Layers

- `app.py`: main Flask entrypoint and route wiring.
- `templates/`: browser-facing pages.
- `static/`: styling and public assets.
- `backend/`: service and helper logic.
- `models/`: local model artifact location.
- `uploadimages/`: uploaded image flow.

## Inference Flow

1. User uploads plant leaf image.
2. App validates and stores image for processing.
3. Backend prepares image input for model inference.
4. PyTorch model returns disease prediction and confidence.
5. UI displays result, guidance, and report context.

## Design Goals

- Local-first workflow for field or laptop use.
- Simple Windows startup with `START.bat`.
- Farmer-oriented UX rather than raw model output.
- Extensible space for weather, market, and report features.

## Operational Notes

- Model asset must exist locally.
- Inference behavior should fail clearly if model file is missing.
- Reports should avoid overwriting user data without clear naming.
