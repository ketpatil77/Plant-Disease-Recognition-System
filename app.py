from __future__ import annotations

import io
import json
import logging
import os
import textwrap
import traceback
import wave
from datetime import datetime
from pathlib import Path
from uuid import uuid4

try:
    import urllib.request as _urllib_req
except ImportError:  # pragma: no cover
    _urllib_req = None

from flask import Flask, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for
from PIL import Image, ImageDraw, ImageFont
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from backend.inference import InvalidImageError, PlantDiseaseService, PredictionError, UnsupportedFileError
from backend.localization import format_datetime_mr, to_marathi_digits, translate_district_name, translate_market_crop
from backend.metadata import build_error_payload, build_library_view_model
from backend.model import DEFAULT_MODEL_PATH, NUM_CLASSES
from backend.reports import ReportStore
from backend.weather import WeatherServiceError, get_live_weather

try:
    from gtts import gTTS
except Exception:  # pragma: no cover - optional dependency fallback
    gTTS = None


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploadimages"
LOGS_DIR = BASE_DIR / "logs"
MODEL_PATH = Path(os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH))
MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # 2MB max - typical plant disease images are ~200KB
PDF_FONT_PATH = BASE_DIR / "static" / "fonts" / "NotoSansDevanagari.ttf"

# Create required directories with error handling
try:
    UPLOAD_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
except OSError as exc:
    logging.error(f"Failed to create required directories: {exc}")
    raise

logging.basicConfig(
    filename=LOGS_DIR / "backend.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

app = Flask(__name__, template_folder="templates", static_folder="static")
# Generate random SECRET_KEY if not provided (security best practice)
if "SECRET_KEY" in os.environ:
    app.secret_key = os.environ["SECRET_KEY"]
else:
    app.secret_key = os.urandom(24).hex()
    logging.info("Generated random SECRET_KEY for session security")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE

report_store = ReportStore(BASE_DIR / "reports.db")
startup_error = None
TRENDS_DATA_PATH = BASE_DIR / "static" / "data" / "trends.json"

FORECAST_ITEMS = [
    {"day": "आज", "category": "fungal", "level": "high", "temperature": 29, "humidity": 78, "rain_chance": 50, "description": "पानांवर जास्त ओलावा राहण्याची शक्यता आहे. बुरशीजन्य रोगाविरुद्ध खबरदारी ठेवा."},
    {"day": "उद्या", "category": "bacterial", "level": "medium", "temperature": 30, "humidity": 68, "rain_chance": 30, "description": "उबदार व दमट हवामान जीवाणूजन्य रोग वाढवू शकते."},
    {"day": "तिसरा दिवस", "category": "pest", "level": "low", "temperature": 31, "humidity": 61, "rain_chance": 20, "description": "रोगदाब कमी राहू शकतो, पण किडीसाठी नियमित पाहणी सुरू ठेवा."},
]

# ──────────────────────────────────────────────────────────────────────────────
# DATA.GOV.IN  Agmarknet API  (free — no key required for public endpoints)
# Resource ID : 9ef84268-d588-465a-a308-a864a43d0070
# Fallback    : MARKET_BY_DISTRICT static table (used when API is unreachable)
# ──────────────────────────────────────────────────────────────────────────────
AGMARKNET_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
AGMARKNET_API_KEY     = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"  # open demo key
AGMARKNET_BASE_URL    = "https://api.data.gov.in/resource/{rid}"

WEATHER_BY_DISTRICT = {
    # Nashik Division
    "Nashik":     {"temperature": 27, "humidity": 69, "rain": "10%", "risk": "medium", "tip": "Inspect vineyards early morning for fresh lesions."},
    "Dhule":      {"temperature": 33, "humidity": 52, "rain": "5%",  "risk": "low",    "tip": "Dry conditions — monitor for aphid pressure on cotton."},
    "Nandurbar":  {"temperature": 34, "humidity": 55, "rain": "8%",  "risk": "low",    "tip": "High heat; irrigate early morning to reduce heat stress."},
    "Jalgaon":    {"temperature": 35, "humidity": 48, "rain": "3%",  "risk": "low",    "tip": "Watch for boll weevil on cotton fields this week."},
    "Ahmednagar": {"temperature": 30, "humidity": 65, "rain": "15%", "risk": "medium", "tip": "Moderate disease pressure on onion; scout for thrips."},
    # Pune Division
    "Pune":       {"temperature": 29, "humidity": 74, "rain": "20%", "risk": "high",   "tip": "Avoid evening irrigation if fungal spots are present."},
    "Solapur":    {"temperature": 32, "humidity": 61, "rain": "8%",  "risk": "medium", "tip": "Check grape bunches for downy mildew after light rain."},
    "Satara":     {"temperature": 28, "humidity": 76, "rain": "25%", "risk": "high",   "tip": "High humidity — apply preventive copper spray on potato."},
    "Sangli":     {"temperature": 30, "humidity": 70, "rain": "18%", "risk": "medium", "tip": "Moderate risk; scout sugarcane for red-rot symptoms."},
    # Konkan Division
    "Kolhapur":   {"temperature": 28, "humidity": 81, "rain": "35%", "risk": "high",   "tip": "High humidity favors fungal outbreaks. Keep leaves dry."},
    "Ratnagiri":  {"temperature": 30, "humidity": 85, "rain": "40%", "risk": "high",   "tip": "Mango hoppers active — spray neem oil in the evening."},
    "Sindhudurg": {"temperature": 29, "humidity": 83, "rain": "38%", "risk": "high",   "tip": "Very high humidity; delay foliar sprays until cloud cover breaks."},
    "Palghar":    {"temperature": 31, "humidity": 78, "rain": "28%", "risk": "high",   "tip": "Watch for paddy blast under prolonged wet spells."},
    "Thane":      {"temperature": 31, "humidity": 77, "rain": "25%", "risk": "high",   "tip": "High humidity — scout vegetable plots for downy mildew."},
    "Raigad":     {"temperature": 30, "humidity": 80, "rain": "32%", "risk": "high",   "tip": "Rice fields: check for brown planthopper after rain."},
    "Mumbai":     {"temperature": 31, "humidity": 79, "rain": "30%", "risk": "high",   "tip": "Urban farming: humid conditions raise leafy vegetable rot risk."},
    # Vidarbha
    "Nagpur":     {"temperature": 32, "humidity": 58, "rain": "5%",  "risk": "low",    "tip": "Heat stress is higher than foliar disease pressure today."},
    "Amravati":   {"temperature": 33, "humidity": 55, "rain": "6%",  "risk": "low",    "tip": "Cotton bollworm scouting recommended this week."},
    "Akola":      {"temperature": 34, "humidity": 50, "rain": "4%",  "risk": "low",    "tip": "Very hot and dry — drip-irrigate cotton to avoid heat stress."},
    "Washim":     {"temperature": 33, "humidity": 53, "rain": "5%",  "risk": "low",    "tip": "Low rain; scout for whitefly on soybean."},
    "Buldhana":   {"temperature": 33, "humidity": 54, "rain": "6%",  "risk": "low",    "tip": "Monitor cotton for pink bollworm early in the season."},
    "Wardha":     {"temperature": 32, "humidity": 59, "rain": "7%",  "risk": "medium", "tip": "Moderate blight risk on tomato under current humidity."},
    "Yavatmal":   {"temperature": 33, "humidity": 57, "rain": "5%",  "risk": "low",    "tip": "Cotton leaf curl virus alert — monitor whitefly vectors."},
    "Chandrapur": {"temperature": 31, "humidity": 64, "rain": "12%", "risk": "medium", "tip": "Moderate risk; paddy neck-blast possible if rain continues."},
    "Gadchiroli": {"temperature": 30, "humidity": 68, "rain": "15%", "risk": "medium", "tip": "Tribal agriculture zone: paddy blast pressure moderate."},
    "Bhandara":   {"temperature": 30, "humidity": 67, "rain": "14%", "risk": "medium", "tip": "Check paddy fields for sheath blight after recent rains."},
    "Gondia":     {"temperature": 30, "humidity": 66, "rain": "13%", "risk": "medium", "tip": "Paddy leaf folder alert in low-lying fields after rain."},
    # Marathwada
    "Aurangabad": {"temperature": 31, "humidity": 60, "rain": "9%",  "risk": "medium", "tip": "Moderate pressure; check grape clusters for anthracnose."},
    "Jalna":      {"temperature": 32, "humidity": 58, "rain": "7%",  "risk": "low",    "tip": "Scout cotton for sucking insects in early pod stage."},
    "Parbhani":   {"temperature": 32, "humidity": 57, "rain": "6%",  "risk": "low",    "tip": "Low humidity reduces fungal risk but aphid pressure persists."},
    "Hingoli":    {"temperature": 32, "humidity": 56, "rain": "6%",  "risk": "low",    "tip": "Dryland crops: watch for stem fly on soybean."},
    "Nanded":     {"temperature": 31, "humidity": 62, "rain": "10%", "risk": "medium", "tip": "Moderate disease risk on soybean; scout for pod blight."},
    "Latur":      {"temperature": 31, "humidity": 60, "rain": "9%",  "risk": "medium", "tip": "Tur dal: monitor for pigeonpea sterility mosaic virus."},
    "Osmanabad":  {"temperature": 31, "humidity": 61, "rain": "9%",  "risk": "medium", "tip": "Moderate risk; check soybean for collar rot after rain."},
    "Beed":       {"temperature": 32, "humidity": 59, "rain": "8%",  "risk": "low",    "tip": "Sugarcane ratoon: scout for pyrilla hopper infestation."},
    # Konkan (Sakri is a tehsil in Dhule; adding as alias)
    "Sakri":      {"temperature": 33, "humidity": 51, "rain": "4%",  "risk": "low",    "tip": "Banana plantation: watch for Fusarium wilt symptoms."},
}

MARKET_BY_DISTRICT = {
    # Nashik Division
    "Nashik":     [
        {"crop": "Onion",    "price": "1800", "trend": "down"},
        {"crop": "Grapes",   "price": "6200", "trend": "up"},
        {"crop": "Tomato",   "price": "2100", "trend": "steady"},
        {"crop": "Wheat",    "price": "2350", "trend": "steady"},
        {"crop": "Maize",    "price": "1820", "trend": "up"},
    ],
    "Dhule":      [
        {"crop": "Cotton",   "price": "6800", "trend": "up"},
        {"crop": "Soybean",  "price": "4600", "trend": "steady"},
        {"crop": "Maize",    "price": "1750", "trend": "up"},
        {"crop": "Wheat",    "price": "2280", "trend": "steady"},
        {"crop": "Onion",    "price": "1650", "trend": "down"},
    ],
    "Nandurbar":  [
        {"crop": "Maize",    "price": "1700", "trend": "up"},
        {"crop": "Cotton",   "price": "6700", "trend": "steady"},
        {"crop": "Banana",   "price": "1200", "trend": "up"},
        {"crop": "Soybean",  "price": "4500", "trend": "steady"},
        {"crop": "Paddy",    "price": "2100", "trend": "steady"},
    ],
    "Jalgaon":    [
        {"crop": "Banana",   "price": "1300", "trend": "up"},
        {"crop": "Cotton",   "price": "6900", "trend": "up"},
        {"crop": "Maize",    "price": "1780", "trend": "steady"},
        {"crop": "Wheat",    "price": "2300", "trend": "steady"},
        {"crop": "Onion",    "price": "1720", "trend": "down"},
    ],
    "Sakri":      [
        {"crop": "Banana",   "price": "1250", "trend": "up"},
        {"crop": "Cotton",   "price": "6750", "trend": "steady"},
        {"crop": "Maize",    "price": "1760", "trend": "up"},
        {"crop": "Wheat",    "price": "2290", "trend": "steady"},
        {"crop": "Groundnut","price": "5200", "trend": "up"},
    ],
    "Ahmednagar": [
        {"crop": "Onion",    "price": "1750", "trend": "down"},
        {"crop": "Tomato",   "price": "2150", "trend": "up"},
        {"crop": "Sugarcane","price": "350",  "trend": "steady"},
        {"crop": "Soybean",  "price": "4650", "trend": "steady"},
        {"crop": "Wheat",    "price": "2320", "trend": "steady"},
    ],
    # Pune Division
    "Pune":       [
        {"crop": "Tomato",   "price": "2200", "trend": "up"},
        {"crop": "Potato",   "price": "1750", "trend": "steady"},
        {"crop": "Grapes",   "price": "6400", "trend": "up"},
        {"crop": "Onion",    "price": "1900", "trend": "down"},
        {"crop": "Cabbage",  "price": "800",  "trend": "steady"},
    ],
    "Solapur":    [
        {"crop": "Grapes",   "price": "6100", "trend": "up"},
        {"crop": "Pomegranate","price": "8500","trend": "up"},
        {"crop": "Onion",    "price": "1680", "trend": "down"},
        {"crop": "Soybean",  "price": "4580", "trend": "steady"},
        {"crop": "Wheat",    "price": "2310", "trend": "steady"},
    ],
    "Satara":     [
        {"crop": "Tomato",   "price": "2180", "trend": "up"},
        {"crop": "Potato",   "price": "1800", "trend": "steady"},
        {"crop": "Strawberry","price": "12000","trend": "up"},
        {"crop": "Ginger",   "price": "9500", "trend": "steady"},
        {"crop": "Sugarcane","price": "345",  "trend": "steady"},
    ],
    "Sangli":     [
        {"crop": "Grapes",   "price": "6300", "trend": "up"},
        {"crop": "Turmeric", "price": "7200", "trend": "up"},
        {"crop": "Sugarcane","price": "342",  "trend": "steady"},
        {"crop": "Tomato",   "price": "2100", "trend": "steady"},
        {"crop": "Onion",    "price": "1730", "trend": "down"},
    ],
    # Konkan
    "Kolhapur":   [
        {"crop": "Sugarcane","price": "340",  "trend": "steady"},
        {"crop": "Tomato",   "price": "2250", "trend": "up"},
        {"crop": "Corn",     "price": "1920", "trend": "steady"},
        {"crop": "Ginger",   "price": "9800", "trend": "up"},
        {"crop": "Cabbage",  "price": "750",  "trend": "steady"},
    ],
    "Ratnagiri":  [
        {"crop": "Alphonso Mango","price": "28000","trend": "up"},
        {"crop": "Cashew",   "price": "9500", "trend": "steady"},
        {"crop": "Coconut",  "price": "2800", "trend": "steady"},
        {"crop": "Paddy",    "price": "2200", "trend": "steady"},
        {"crop": "Kokum",    "price": "5500", "trend": "up"},
    ],
    "Sindhudurg": [
        {"crop": "Coconut",  "price": "2900", "trend": "up"},
        {"crop": "Cashew",   "price": "9800", "trend": "steady"},
        {"crop": "Paddy",    "price": "2180", "trend": "steady"},
        {"crop": "Jackfruit","price": "1500", "trend": "up"},
        {"crop": "Kokum",    "price": "5600", "trend": "up"},
    ],
    "Palghar":    [
        {"crop": "Paddy",    "price": "2150", "trend": "steady"},
        {"crop": "Sapota",   "price": "3200", "trend": "up"},
        {"crop": "Coconut",  "price": "2750", "trend": "steady"},
        {"crop": "Brinjal",  "price": "900",  "trend": "up"},
        {"crop": "Banana",   "price": "1350", "trend": "steady"},
    ],
    "Thane":      [
        {"crop": "Paddy",    "price": "2120", "trend": "steady"},
        {"crop": "Vegetable Mix","price": "2000","trend": "up"},
        {"crop": "Coconut",  "price": "2700", "trend": "steady"},
        {"crop": "Banana",   "price": "1300", "trend": "up"},
        {"crop": "Brinjal",  "price": "850",  "trend": "steady"},
    ],
    "Raigad":     [
        {"crop": "Paddy",    "price": "2200", "trend": "steady"},
        {"crop": "Coconut",  "price": "2800", "trend": "steady"},
        {"crop": "Alphonso Mango","price": "25000","trend": "up"},
        {"crop": "Fish (dried)","price": "15000","trend": "steady"},
        {"crop": "Banana",   "price": "1280", "trend": "up"},
    ],
    "Mumbai":     [
        {"crop": "Tomato",   "price": "2800", "trend": "up"},
        {"crop": "Potato",   "price": "2000", "trend": "steady"},
        {"crop": "Onion",    "price": "2100", "trend": "down"},
        {"crop": "Cabbage",  "price": "900",  "trend": "steady"},
        {"crop": "Capsicum", "price": "4500", "trend": "up"},
    ],
    # Vidarbha
    "Nagpur":     [
        {"crop": "Orange",   "price": "4300", "trend": "up"},
        {"crop": "Soybean",  "price": "4700", "trend": "steady"},
        {"crop": "Tomato",   "price": "2050", "trend": "down"},
        {"crop": "Cotton",   "price": "6850", "trend": "up"},
        {"crop": "Wheat",    "price": "2340", "trend": "steady"},
    ],
    "Amravati":   [
        {"crop": "Cotton",   "price": "6820", "trend": "up"},
        {"crop": "Soybean",  "price": "4680", "trend": "steady"},
        {"crop": "Orange",   "price": "4200", "trend": "steady"},
        {"crop": "Wheat",    "price": "2330", "trend": "steady"},
        {"crop": "Tur Dal",  "price": "7100", "trend": "up"},
    ],
    "Akola":      [
        {"crop": "Cotton",   "price": "6750", "trend": "steady"},
        {"crop": "Soybean",  "price": "4620", "trend": "steady"},
        {"crop": "Wheat",    "price": "2300", "trend": "steady"},
        {"crop": "Sunflower","price": "5800", "trend": "up"},
        {"crop": "Tur Dal",  "price": "7050", "trend": "up"},
    ],
    "Washim":     [
        {"crop": "Soybean",  "price": "4600", "trend": "steady"},
        {"crop": "Cotton",   "price": "6780", "trend": "up"},
        {"crop": "Wheat",    "price": "2290", "trend": "steady"},
        {"crop": "Tur Dal",  "price": "7000", "trend": "up"},
        {"crop": "Maize",    "price": "1800", "trend": "steady"},
    ],
    "Buldhana":   [
        {"crop": "Cotton",   "price": "6800", "trend": "up"},
        {"crop": "Soybean",  "price": "4640", "trend": "steady"},
        {"crop": "Orange",   "price": "4150", "trend": "steady"},
        {"crop": "Wheat",    "price": "2310", "trend": "steady"},
        {"crop": "Onion",    "price": "1700", "trend": "down"},
    ],
    "Wardha":     [
        {"crop": "Cotton",   "price": "6900", "trend": "up"},
        {"crop": "Soybean",  "price": "4720", "trend": "steady"},
        {"crop": "Orange",   "price": "4250", "trend": "up"},
        {"crop": "Wheat",    "price": "2350", "trend": "steady"},
        {"crop": "Tomato",   "price": "2080", "trend": "steady"},
    ],
    "Yavatmal":   [
        {"crop": "Cotton",   "price": "6850", "trend": "up"},
        {"crop": "Soybean",  "price": "4700", "trend": "steady"},
        {"crop": "Tur Dal",  "price": "7150", "trend": "up"},
        {"crop": "Wheat",    "price": "2320", "trend": "steady"},
        {"crop": "Maize",    "price": "1810", "trend": "steady"},
    ],
    "Chandrapur": [
        {"crop": "Paddy",    "price": "2250", "trend": "steady"},
        {"crop": "Cotton",   "price": "6780", "trend": "up"},
        {"crop": "Soybean",  "price": "4650", "trend": "steady"},
        {"crop": "Tomato",   "price": "2050", "trend": "down"},
        {"crop": "Maize",    "price": "1790", "trend": "steady"},
    ],
    "Gadchiroli": [
        {"crop": "Paddy",    "price": "2200", "trend": "steady"},
        {"crop": "Bamboo",   "price": "3500", "trend": "steady"},
        {"crop": "Maize",    "price": "1770", "trend": "up"},
        {"crop": "Teak Wood","price": "45000","trend": "steady"},
        {"crop": "Black Pepper","price": "32000","trend": "up"},
    ],
    "Bhandara":   [
        {"crop": "Paddy",    "price": "2230", "trend": "steady"},
        {"crop": "Wheat",    "price": "2280", "trend": "steady"},
        {"crop": "Maize",    "price": "1760", "trend": "steady"},
        {"crop": "Soybean",  "price": "4600", "trend": "steady"},
        {"crop": "Groundnut","price": "5100", "trend": "up"},
    ],
    "Gondia":     [
        {"crop": "Paddy",    "price": "2210", "trend": "steady"},
        {"crop": "Wheat",    "price": "2270", "trend": "steady"},
        {"crop": "Maize",    "price": "1750", "trend": "up"},
        {"crop": "Soybean",  "price": "4580", "trend": "steady"},
        {"crop": "Groundnut","price": "5050", "trend": "steady"},
    ],
    # Marathwada
    "Aurangabad": [
        {"crop": "Grapes",   "price": "6000", "trend": "up"},
        {"crop": "Pomegranate","price": "8200","trend": "steady"},
        {"crop": "Cotton",   "price": "6800", "trend": "up"},
        {"crop": "Soybean",  "price": "4660", "trend": "steady"},
        {"crop": "Onion",    "price": "1760", "trend": "down"},
    ],
    "Jalna":      [
        {"crop": "Cotton",   "price": "6770", "trend": "up"},
        {"crop": "Soybean",  "price": "4620", "trend": "steady"},
        {"crop": "Sweet Orange","price": "4100","trend": "steady"},
        {"crop": "Wheat",    "price": "2300", "trend": "steady"},
        {"crop": "Mosambi",  "price": "3800", "trend": "up"},
    ],
    "Parbhani":   [
        {"crop": "Cotton",   "price": "6790", "trend": "steady"},
        {"crop": "Soybean",  "price": "4630", "trend": "steady"},
        {"crop": "Tur Dal",  "price": "7080", "trend": "up"},
        {"crop": "Wheat",    "price": "2295", "trend": "steady"},
        {"crop": "Onion",    "price": "1700", "trend": "down"},
    ],
    "Hingoli":    [
        {"crop": "Soybean",  "price": "4610", "trend": "steady"},
        {"crop": "Cotton",   "price": "6760", "trend": "up"},
        {"crop": "Tur Dal",  "price": "7020", "trend": "up"},
        {"crop": "Wheat",    "price": "2285", "trend": "steady"},
        {"crop": "Sesame",   "price": "12000","trend": "up"},
    ],
    "Nanded":     [
        {"crop": "Soybean",  "price": "4650", "trend": "steady"},
        {"crop": "Tur Dal",  "price": "7100", "trend": "up"},
        {"crop": "Cotton",   "price": "6810", "trend": "up"},
        {"crop": "Sugarcane","price": "338",  "trend": "steady"},
        {"crop": "Wheat",    "price": "2305", "trend": "steady"},
    ],
    "Latur":      [
        {"crop": "Soybean",  "price": "4700", "trend": "steady"},
        {"crop": "Tur Dal",  "price": "7200", "trend": "up"},
        {"crop": "Cotton",   "price": "6820", "trend": "up"},
        {"crop": "Onion",    "price": "1710", "trend": "down"},
        {"crop": "Wheat",    "price": "2315", "trend": "steady"},
    ],
    "Osmanabad":  [
        {"crop": "Soybean",  "price": "4680", "trend": "steady"},
        {"crop": "Tur Dal",  "price": "7120", "trend": "up"},
        {"crop": "Cotton",   "price": "6800", "trend": "steady"},
        {"crop": "Pomegranate","price": "8100","trend": "steady"},
        {"crop": "Onion",    "price": "1690", "trend": "down"},
    ],
    "Beed":       [
        {"crop": "Sugarcane","price": "336",  "trend": "steady"},
        {"crop": "Soybean",  "price": "4660", "trend": "steady"},
        {"crop": "Cotton",   "price": "6790", "trend": "up"},
        {"crop": "Onion",    "price": "1680", "trend": "down"},
        {"crop": "Pomegranate","price": "8050","trend": "steady"},
    ],
}

# Validate model file exists before attempting to load
if not MODEL_PATH.exists():
    startup_error = f"Model file not found at {MODEL_PATH}"
    predictor = None
    logging.error(startup_error)
else:
    try:
        predictor = PlantDiseaseService(model_path=MODEL_PATH)
        logging.info("Model loaded successfully from %s", MODEL_PATH)
    except Exception as exc:  # pragma: no cover - exercised during broken startup only
        predictor = None
        startup_error = str(exc)
        logging.exception("Model failed to load from %s", MODEL_PATH)


def wants_json_response() -> bool:
    """
    Determine if the client prefers JSON response based on request path or Accept headers.
    API routes always return JSON. HTML requests prefer JSON only if explicitly requested.
    Returns True for JSON preference, False for HTML/default preference.
    """
    if request.path.startswith("/api/"):
        return True
    best = request.accept_mimetypes.best
    if not best:
        return False
    return best == "application/json" and request.accept_mimetypes[best] >= request.accept_mimetypes["text/html"]


def current_reports():
    """Fetch the current list of stored prediction reports from the database."""
    return report_store.list_reports()


def available_districts():
    if TRENDS_DATA_PATH.exists():
        with TRENDS_DATA_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        districts = [item["name"] for item in payload.get("districts", []) if item.get("name")]
        if districts:
            return districts
    return list(WEATHER_BY_DISTRICT.keys())


def supported_crops():
    _, crop_filters = build_library_view_model()
    return crop_filters


def risk_label_mr(value: str) -> str:
    return {
        "high": "उच्च",
        "medium": "मध्यम",
        "low": "कमी",
    }.get((value or "medium").lower(), "मध्यम")


def category_label_mr(value: str) -> str:
    return {
        "fungal": "बुरशीजन्य",
        "bacterial": "जीवाणूजन्य",
        "viral": "विषाणूजन्य",
        "pest": "किडीचा",
        "healthy": "निरोगी",
        "warning": "इशारा",
        "error": "त्रुटी",
    }.get((value or "").lower(), value or "")


def fallback_weather_summary(risk: str) -> str:
    if risk == "high":
        return "दमट आणि ओलसर स्थितीमुळे पानांवरील रोग झपाट्याने वाढू शकतात."
    if risk == "medium":
        return "हवामान मिश्र आहे. संवेदनशील पट्ट्यांची वेळेवर पाहणी करा."
    return "सध्या रोगदाब कमी आहे, तरी नियमित पाहणी सुरू ठेवा."


def fallback_weather_tip(risk: str) -> str:
    if risk == "high":
        return "सकाळी लवकर पाहणी करा, हवेशीरपणा वाढवा आणि संध्याकाळी सिंचन टाळा."
    if risk == "medium":
        return "दाट झाडीत आणि ओलसर पट्ट्यांत लक्षणे दिसतात का ते तपासा."
    return "सध्या धोका कमी आहे, पण किडी आणि नवीन डागांसाठी नियमित निरीक्षण करा."


def translate_market_rows(rows):
    translated = []
    for item in rows or []:
        translated.append({**item, "crop": translate_market_crop(item.get("crop", ""))})
    return translated


def normalize_dashboard_weather(weather: dict | None) -> dict:
    weather = dict(weather or {})
    rain_mm_24h = weather.get("rain_mm_24h")
    if rain_mm_24h is not None:
        rain_display = f"{rain_mm_24h} mm"
    else:
        rain_display = weather.get("rain") or "—"

    wind_speed = weather.get("wind_speed")
    if wind_speed is not None:
        wind_display = f"{wind_speed} km/h"
    else:
        wind_display = "—"

    weather.setdefault("risk", "medium")
    weather["tip"] = fallback_weather_tip(weather.get("risk", "medium"))
    weather["summary"] = fallback_weather_summary(weather.get("risk", "medium"))
    weather["risk_label"] = risk_label_mr(weather.get("risk", "medium"))
    weather["rain_display"] = rain_display
    weather["wind_display"] = wind_display
    return weather


def history_summary(reports):
    latest = reports[0] if reports else None
    average_confidence = round(sum(report.get("confidence", 0) for report in reports) / len(reports)) if reports else 0
    return {
        "total_reports": len(reports),
        "high_priority": sum(1 for report in reports if (report.get("severity") or "").lower() == "high"),
        "average_confidence": average_confidence,
        "latest_disease": latest.get("disease", "") if latest else "",
        "latest_at": format_datetime_mr(latest.get("created_at")) if latest else "",
    }


def dashboard_context(selected_district: str | None, *, reports=None):
    reports = reports if reports is not None else current_reports()
    districts = available_districts()
    selected = selected_district if selected_district in districts else districts[0]
    crop_filters = supported_crops()
    fallback_weather = normalize_dashboard_weather(WEATHER_BY_DISTRICT.get(selected, WEATHER_BY_DISTRICT[districts[0]]))
    return {
        "forecast": FORECAST_ITEMS,
        "weather": fallback_weather,
        "districts": districts,
        "district_labels": {district: translate_district_name(district) for district in districts},
        "selected_district": selected,
        "market": translate_market_rows(MARKET_BY_DISTRICT.get(selected, MARKET_BY_DISTRICT[districts[0]])),
        "ui_summary": {
            "class_count": NUM_CLASSES,
            "crop_count": len(crop_filters),
            "report_count": len(reports),
            "district_count": len(districts),
        },
        "supported_crops": crop_filters[:8],
    }


def render_page(template_name: str, *, active_page: str, **context):
    context.setdefault("reports", current_reports())
    context.setdefault("active_page", active_page)
    return render_template(template_name, **context)


def json_error(message: str, status_code: int = 400):
    return jsonify({"ok": False, "error": message}), status_code


def save_uploaded_image(file_storage):
    """
    Save uploaded image file to disk with secure filename and unique identifier.
    Args:
        file_storage: Werkzeug FileStorage object from request.files
    Returns:
        Path object pointing to saved image file
    """
    original_name = secure_filename(file_storage.filename or "upload.jpg")
    suffix = Path(original_name).suffix.lower() or ".jpg"
    filename = f"{uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    file_storage.save(destination)
    return destination


def error_response(message: str, *, status_code: int = 400):
    payload = build_error_payload(message)
    if wants_json_response():
        return jsonify({"ok": False, "error": message, "prediction_payload": payload}), status_code
    session["prediction_payload"] = payload
    return redirect(url_for("prediction"))


def persist_prediction(payload: dict):
    report = report_store.save_report(payload)
    payload["report_payload"] = report["report_payload"]
    return payload


def handle_prediction_request():
    """
    Main request handler for plant disease prediction endpoint.
    Validates model availability, processes uploaded image, runs inference, 
    persists result to database, and returns prediction payload.
    Supports both HTML form POST and JSON API modes.
    Returns:
        Tuple of (response_data, status_code) or redirect Response object
    """
    if startup_error:
        return error_response(f"मॉडेल सुरू करण्यात अडचण आली: {startup_error}", status_code=500)
    if predictor is None:
        return error_response("मॉडेल सध्या उपलब्ध नाही.", status_code=500)

    file_storage = request.files.get("img") or request.files.get("image")
    if file_storage is None:
        return error_response("प्रतिमा अपलोड झालेली नाही. कृपया पानाचा फोटो निवडा.", status_code=400)
    if not file_storage.filename:
        return error_response("अपलोड केलेली फाइल रिकामी आहे.", status_code=400)

    saved_path = None
    try:
        saved_path = save_uploaded_image(file_storage)
        payload = predictor.predict_path(
            saved_path,
            image_url=url_for("uploaded_image", filename=saved_path.name),
        )
        payload = persist_prediction(payload)
        session["prediction_payload"] = payload
        if wants_json_response():
            return jsonify({"ok": True, "prediction_payload": payload})
        return redirect(url_for("prediction"))
    except (UnsupportedFileError, InvalidImageError) as exc:
        logging.warning("Invalid upload rejected: %s", exc)
        if saved_path and saved_path.exists():
            saved_path.unlink(missing_ok=True)
        return error_response(str(exc), status_code=400)
    except PredictionError as exc:
        logging.warning("Prediction request failed: %s", exc)
        if saved_path and saved_path.exists():
            saved_path.unlink(missing_ok=True)
        return error_response(str(exc), status_code=422)
    except Exception as exc:  # pragma: no cover - defensive guard
        logging.error("Unexpected prediction failure: %s\n%s", exc, traceback.format_exc())
        if saved_path and saved_path.exists():
            saved_path.unlink(missing_ok=True)
        return error_response("निदान करताना अनपेक्षित सर्व्हर त्रुटी आली.", status_code=500)


def silent_wav_bytes(duration_ms: int = 350) -> io.BytesIO:
    sample_rate = 22050
    frames = int(sample_rate * (duration_ms / 1000.0))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frames)
    buffer.seek(0)
    return buffer


def simple_pdf_bytes(lines):
    page = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(page)

    try:
        font = ImageFont.truetype(str(PDF_FONT_PATH), 34)
        title_font = ImageFont.truetype(str(PDF_FONT_PATH), 42)
    except OSError:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    y = 90
    max_chars = 44
    for index, line in enumerate(lines):
        active_font = title_font if index == 0 else font
        for wrapped in textwrap.wrap(str(line), width=max_chars) or [""]:
            draw.text((90, y), wrapped, fill="#101828", font=active_font)
            y += 62 if index == 0 else 52
        y += 14

    buffer = io.BytesIO()
    page.save(buffer, format="PDF", resolution=150.0)
    buffer.seek(0)
    return buffer


@app.route("/")
def home():
    reports = current_reports()
    return render_page(
        "home.html",
        active_page="home",
        reports=reports,
        **dashboard_context(request.args.get("district"), reports=reports),
    )


@app.route("/scanner")
def scanner():
    return render_page("scanner.html", active_page="scanner", supported_crops=supported_crops()[:10])


@app.route("/prediction")
def prediction():
    payload = session.get("prediction_payload") or build_error_payload("अजून निदान उपलब्ध नाही. सुरुवात करण्यासाठी पानाचा फोटो अपलोड करा.")
    return render_page("prediction.html", active_page="scanner", prediction_payload=payload)


@app.route("/upload/", methods=["POST"])
def uploadimage():
    return handle_prediction_request()


@app.route("/api/predict", methods=["POST"])
def api_predict():
    return handle_prediction_request()


@app.route("/scan-tutorial")
def scan_tutorial():
    return render_page("scan-tutorial.html", active_page="scanner")


@app.route("/history")
def history():
    reports = current_reports()
    filter_crops = sorted({report["crop"] for report in reports if report.get("crop")})
    return render_page(
        "history.html",
        active_page="history",
        reports=reports,
        filter_crops=filter_crops,
        history_summary=history_summary(reports),
    )


@app.route("/history/<int:report_id>")
def view_report(report_id: int):
    report = report_store.get_report(report_id)
    if not report:
        return redirect(url_for("history"))
    return render_page("prediction.html", active_page="history", prediction_payload=report["payload"])


@app.route("/history/download/<int:report_id>")
def history_download(report_id: int):
    report = report_store.get_report(report_id)
    if not report:
        return redirect(url_for("history"))

    payload = report["payload"]
    lines = [
        "अॅग्रो व्हिजन रोग निदान अहवाल",
        f"अहवाल क्रमांक: {to_marathi_digits(report_id)}",
        f"पीक: {payload.get('crop', '')}",
        f"रोग: {payload.get('disease', '')}",
        f"विश्वास: {to_marathi_digits(payload.get('confidence', 0))}%",
        f"श्रेणी: {category_label_mr(payload.get('category', ''))}",
        f"कारण: {payload.get('cause', '')}",
        f"उपाय: {payload.get('remedy', '')}",
    ]
    return send_file(
        simple_pdf_bytes(lines),
        as_attachment=True,
        download_name=f"agro-ahaval-{report_id}.pdf",
        mimetype="application/pdf",
    )


@app.route("/history/delete/<int:report_id>", methods=["POST"])
def history_delete(report_id: int):
    report_store.delete_report(report_id)
    return redirect(url_for("history"))


@app.route("/library")
def library():
    items, crop_filters = build_library_view_model()
    return render_page(
        "disease-library.html",
        active_page="library",
        items=items,
        crop_filters=crop_filters,
        library_summary={
            "item_count": len(items),
            "crop_count": len(crop_filters),
            "healthy_count": sum(1 for item in items if item.get("disease", "").lower() == "healthy"),
        },
    )


@app.route("/settings")
def settings():
    return render_page("settings.html", active_page="settings")


@app.route("/uploadimages/<path:filename>")
def uploaded_image(filename: str):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/manifest.json")
def manifest():
    return send_from_directory(BASE_DIR, "manifest.json")


@app.route("/sw.js")
def service_worker():
    return send_from_directory(BASE_DIR, "sw.js")


@app.route("/README_UI.md")
def readme_ui():
    path = BASE_DIR / "README_UI.md"
    if path.exists():
        return send_file(path)
    return redirect(url_for("home"))


@app.route("/speak")
def speak():
    text = (request.args.get("text") or "").strip()
    language = (request.args.get("lang") or "mr").strip() or "mr"

    if text and gTTS is not None:
        try:
            speech = io.BytesIO()
            gTTS(text=text, lang=language, slow=False).write_to_fp(speech)
            speech.seek(0)
            return send_file(speech, mimetype="audio/mpeg", download_name="speech.mp3")
        except Exception:
            logging.warning("gTTS generation failed; serving silent audio fallback.")

    return send_file(silent_wav_bytes(), mimetype="audio/wav", download_name="speech.wav")


@app.route("/api/health")
def api_health():
    return jsonify(
        {
            "ok": predictor is not None and startup_error is None,
            "model_path": str(MODEL_PATH),
            "startup_error": startup_error,
        }
    )


@app.route("/api/weather")
def api_weather():
    latitude = request.args.get("lat", type=float)
    longitude = request.args.get("lon", type=float)

    if latitude is None or longitude is None:
        return json_error("'lat' आणि 'lon' हे पॅरामीटर्स आवश्यक आहेत.", 400)

    try:
        return jsonify({"ok": True, **get_live_weather(latitude, longitude)})
    except ValueError as exc:
        return json_error(str(exc), 400)
    except WeatherServiceError as exc:
        logging.warning("Live weather fetch failed for (%s, %s): %s", latitude, longitude, exc)
        return json_error(str(exc), 502)


@app.route("/api/market-rates")
def api_market_rates():
    """
    Proxy endpoint for live Agmarknet commodity prices via data.gov.in.
    Query params:
      district – Maharashtra district name (e.g. "Nashik")
      commodity – optional commodity filter (e.g. "Onion")
    Falls back to MARKET_BY_DISTRICT static data when the upstream API
    is unreachable (network error, timeout, bad response).
    """
    district  = (request.args.get("district")  or "").strip()
    commodity = (request.args.get("commodity") or "").strip()

    # --- Try live Agmarknet API ---
    try:
        params = (
            f"api-key={AGMARKNET_API_KEY}"
            f"&format=json"
            f"&filters[state]=Maharashtra"
            f"&limit=20"
        )
        if district:
            params += f"&filters[district]={district}"
        if commodity:
            params += f"&filters[commodity]={commodity}"

        url = AGMARKNET_BASE_URL.format(rid=AGMARKNET_RESOURCE_ID) + "?" + params
        req = _urllib_req.Request(url, headers={"User-Agent": "AgroVision/1.0"})
        with _urllib_req.urlopen(req, timeout=5) as resp:
            raw = json.loads(resp.read().decode("utf-8"))

        records = raw.get("records", [])
        if records:
            rows = []
            seen = set()
            for rec in records:
                crop_name = rec.get("commodity") or rec.get("Commodity") or "—"
                modal_price = rec.get("modal_price") or rec.get("Modal_Price") or rec.get("modal price")
                min_price   = rec.get("min_price")   or rec.get("Min_Price")
                max_price   = rec.get("max_price")   or rec.get("Max_Price")
                key = crop_name.lower()
                if key in seen:
                    continue
                seen.add(key)
                try:
                    p = int(float(str(modal_price).replace(",", "")))
                    mn = int(float(str(min_price).replace(",", "")))  if min_price else None
                    mx = int(float(str(max_price).replace(",", "")))  if max_price else None
                except (ValueError, TypeError):
                    p = mn = mx = None

                rows.append({
                    "crop":      translate_market_crop(crop_name),
                    "price":     str(p) if p else "—",
                    "min_price": str(mn) if mn else None,
                    "max_price": str(mx) if mx else None,
                    "mandi":     rec.get("market") or rec.get("Market") or "",
                    "variety":   rec.get("variety") or rec.get("Variety") or "",
                    "date":      rec.get("arrival_date") or rec.get("Arrival_Date") or "",
                    "trend":     "steady",
                    "source":    "live",
                })

            return jsonify({
                "ok": True,
                "district": translate_district_name(district or "Maharashtra"),
                "source": "agmarknet_live",
                "fetched_at": format_datetime_mr(datetime.now()),
                "data": rows[:10],
            })

    except Exception as exc:
        logging.warning("Agmarknet API unreachable: %s", exc)

    # --- Static fallback ---
    fallback_key = district if district in MARKET_BY_DISTRICT else list(MARKET_BY_DISTRICT.keys())[0]
    static_rows = [
        {**item, "crop": translate_market_crop(item.get("crop", "")), "source": "static", "mandi": "", "variety": "", "date": "",
         "min_price": None, "max_price": None}
        for item in MARKET_BY_DISTRICT.get(fallback_key, [])
    ]
    return jsonify({
        "ok": True,
        "district": translate_district_name(fallback_key),
        "source": "static_fallback",
        "fetched_at": format_datetime_mr(datetime.now()),
        "data": static_rows,
    })


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_error):
    return error_response("प्रतिमा खूप मोठी आहे. 2MB पर्यंतची JPEG, PNG किंवा WEBP फाइल अपलोड करा.", status_code=413)


@app.errorhandler(404)
def not_found(_error):
    if wants_json_response():
        return json_error("ही मार्गिका उपलब्ध नाही.", 404)
    return redirect(url_for("home"))


@app.errorhandler(500)
def server_error(error):
    logging.error("Unhandled server error: %s", error)
    if wants_json_response():
        return json_error("आतील सर्व्हर त्रुटी.", 500)
    session["prediction_payload"] = build_error_payload("आतील सर्व्हर त्रुटी आली. कृपया पुन्हा प्रयत्न करा.")
    return redirect(url_for("prediction"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
