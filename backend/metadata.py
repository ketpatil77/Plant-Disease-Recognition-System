from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from pathlib import Path

from .localization import infer_class_name, localize_class, parse_class_name as localized_parse_class_name, translate_area_advice, translate_area_value
from .model import BACKGROUND_CLASS, IDX_TO_CLASSES

BASE_DIR = Path(__file__).resolve().parent.parent
DISEASE_INFO_PATH = BASE_DIR / "backend" / "data" / "disease_info.csv"
LOCAL_DISEASE_JSON_PATH = BASE_DIR / "plant_disease.json"
AREA_RECOMMENDATIONS_PATH = BASE_DIR / "MAHARASHTRA_REMEDIES_DATABASE.csv"

CLASS_LABEL_ALIASES = {
    BACKGROUND_CLASS: ["no leaf", "background"],
    "Corn___Cercospora_leaf_spot Gray_leaf_spot": ["cercospora leaf spot", "gray leaf spot"],
    "Grape___Esca_(Black_Measles)": ["esca", "black measles"],
    "Orange___Haunglongbing_(Citrus_greening)": ["haunglongbing", "citrus greening"],
    "Tomato___Spider_mites Two-spotted_spider_mite": ["spider mites", "two spotted spider mite", "two-spotted spider mite"],
    "Tomato___Target_Spot": ["target spot", "leaf spot"],
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": ["tomato yellow leaf curl virus", "tylcv"],
    "Tomato___Tomato_mosaic_virus": ["tomato mosaic virus", "tmv"],
}


def normalize_key(value: str) -> str:
    value = (value or "").lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[_/|(),:-]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def humanize_label(value: str) -> str:
    value = (value or "").replace("_", " ").replace(",", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def split_sentences(text: str, limit: int = 4):
    text = (text or "").replace("\r", "\n")
    pieces = re.split(r"(?:\.\s+|\n+|;\s+)", text)
    cleaned = [piece.strip(" \"'") for piece in pieces if piece and piece.strip(" \"'")]
    return cleaned[:limit]


def first_sentence(text: str, fallback: str) -> str:
    sentences = split_sentences(text, limit=1)
    return sentences[0] if sentences else fallback


def parse_class_name(class_name: str):
    return localized_parse_class_name(class_name)


def category_for(class_name: str, area_match: dict, cause_text: str) -> str:
    if class_name == BACKGROUND_CLASS:
        return "warning"
    if class_name.endswith("___healthy"):
        return "healthy"
    area_type = (area_match or {}).get("Disease_Type", "").strip().lower()
    if area_type and area_type not in {"preventive"}:
        return area_type
    lowered = f"{class_name} {cause_text}".lower()
    if "virus" in lowered:
        return "viral"
    if "bacteria" in lowered or "bacterial" in lowered:
        return "bacterial"
    if "mite" in lowered or "pest" in lowered or "insect" in lowered:
        return "pest"
    return "fungal"


def weather_note_for(category: str, class_name: str) -> str:
    if class_name == BACKGROUND_CLASS:
        return "नैसर्गिक प्रकाशात एकच पान फ्रेममध्ये भरून येईल असा फोटो पुन्हा घ्या."
    if class_name.endswith("___healthy"):
        return "तातडीच्या उपचाराची गरज नाही. नियमित पाहणी सुरू ठेवा आणि पाने जास्त वेळ ओलसर राहू देऊ नका."
    if category == "fungal":
        return "कोरड्या हवामानात फवारणी करा आणि उपचाराच्या आधी किंवा नंतर वरून पाणी देणे टाळा."
    if category == "bacterial":
        return "ओलसर पाने हाताळणे टाळा आणि एका झाडावरून दुसऱ्यावर जाण्यापूर्वी साधने निर्जंतुक करा."
    if category == "viral":
        return "वाहक कीटक नियंत्रणावर लक्ष द्या आणि जास्त संक्रमित वाढ लवकर काढून टाका."
    if category == "pest":
        return "जवळील पानांच्या खालच्या बाजूची तपासणी करा आणि सकाळी लवकर किंवा संध्याकाळी उपाय करा."
    return ""


def default_checklist(class_name: str):
    if class_name == BACKGROUND_CLASS:
        return ["एकच स्पष्ट पान निवडा", "धूसरपणा आणि सावल्या टाळा", "पानाने फ्रेम भरू द्या"]
    if class_name.endswith("___healthy"):
        return ["नियमित पाहणी सुरू ठेवा", "मातीच्या पातळीवर पाणी द्या", "जवळील पानांवर नवीन डाग दिसतात का ते पहा"]
    return ["जवळील पानांवर हीच लक्षणे आहेत का ते तपासा", "जास्त संक्रमित पाने काढून टाका", "फोटो धूसर असेल तर पुन्हा स्कॅन करा"]


def build_error_payload(message: str):
    return {
        "class_name": "",
        "image_url": "",
        "crop": "अपलोड",
        "disease": "त्रुटी",
        "marathi_name": message,
        "category": "error",
        "severity": "medium",
        "confidence": 0,
        "cause": message,
        "remedy": "एकाच पानाचा स्पष्ट JPEG, PNG किंवा WEBP फोटो अपलोड करून पुन्हा प्रयत्न करा.",
        "prevention": "नैसर्गिक प्रकाश वापरा आणि फ्रेममध्ये एकच पान मध्यभागी ठेवा.",
        "prevention_steps": [
            "फक्त JPEG, PNG किंवा WEBP प्रतिमा वापरा.",
            "प्रत्येक फोटोमध्ये एकच स्पष्ट पान घ्या.",
            "गडद, धूसर किंवा गोंधळलेल्या पार्श्वभूमीचे फोटो टाळा.",
        ],
        "weather_note": "विश्वासार्ह निकालासाठी अधिक स्पष्ट प्रतिमेसह पुन्हा प्रयत्न करा.",
        "remedy_sections": {
            "chemical": ["वैध निदान मिळेपर्यंत कोणताही उपचार सुचवलेला नाही."],
            "organic": ["अधिक स्पष्ट प्रतिमेसह स्कॅन पुन्हा करा."],
            "preventive": ["नैसर्गिक प्रकाश वापरा", "कॅमेरा स्थिर ठेवा", "एकमेकांवर आलेली पाने टाळा"],
        },
        "area_recommendations": {},
        "badge_variant": "medium",
        "status_summary": "कृती आवश्यक",
        "status_code": "error",
        "insights": {
            "likely_cause": message,
            "spray_time": "वैध निदान मिळेपर्यंत थांबा",
            "checklist": ["एकच पान वापरा", "चांगला प्रकाश ठेवा", "JPEG/PNG/WEBP स्वरूप वापरा"],
        },
        "report_payload": {"created_at": ""},
    }


def read_csv_rows(path: Path, encodings=("utf-8-sig", "cp1252")):
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, f"Unable to decode {path}")


@lru_cache(maxsize=1)
def load_support_data():
    disease_rows = read_csv_rows(DISEASE_INFO_PATH)
    area_rows = read_csv_rows(AREA_RECOMMENDATIONS_PATH, encodings=("utf-8-sig",))
    with LOCAL_DISEASE_JSON_PATH.open("r", encoding="utf-8") as handle:
        local_rows = json.load(handle)

    local_map = {item["name"]: item for item in local_rows}
    return {
        "disease_rows": disease_rows,
        "local_map": local_map,
        "area_rows": area_rows,
    }


def match_area_recommendation(class_name: str, crop: str, disease: str):
    rows = load_support_data()["area_rows"]
    target_crop = normalize_key(crop)
    search_terms = {normalize_key(disease)}
    search_terms.update(normalize_key(term) for term in CLASS_LABEL_ALIASES.get(class_name, []))

    for row in rows:
        row_crop = normalize_key(row.get("Crop_English", ""))
        if row_crop and row_crop not in target_crop and target_crop not in row_crop:
            continue

        row_disease = normalize_key(row.get("Disease", ""))
        if any(term and (term in row_disease or row_disease in term) for term in search_terms):
            return row
    return {}


def format_area_recommendation(row: dict):
    if not row:
        return {}
    return {
        "generic_advice": translate_area_advice(row.get("Generic_Advice", "")),
        "chemical_product": row.get("Chemical_Company_Product", ""),
        "chemical_verification": translate_area_value(row.get("Chemical_Verification", "")),
        "organic_product": row.get("Organic_Company_Product", ""),
        "organic_verification": translate_area_value(row.get("Organic_Verification", "")),
        "availability": translate_area_value(row.get("Maharashtra_Availability", "")),
        "withholding_period": row.get("Withholding_Period", ""),
    }


@lru_cache(maxsize=1)
def build_catalog():
    support = load_support_data()
    disease_rows = support["disease_rows"]
    catalog = {}

    for index, class_name in IDX_TO_CLASSES.items():
        crop, disease = parse_class_name(class_name)
        localized = localize_class(class_name)

        if class_name == BACKGROUND_CLASS:
            catalog[class_name] = {
                "class_name": class_name,
                "index": index,
                "crop": localized["crop"],
                "disease": localized["disease"],
                "title": localized["title"],
                "description": localized["cause"],
                "possible_steps": default_checklist(class_name),
                "cause": localized["cause"],
                "cure": localized["cure"],
                "area_recommendation": {},
            }
            continue

        disease_row = disease_rows[index] if index < len(disease_rows) else {}
        area_match = match_area_recommendation(class_name, crop, disease)

        catalog[class_name] = {
            "class_name": class_name,
            "index": index,
            "crop": localized["crop"],
            "disease": localized["disease"],
            "title": localized["title"],
            "description": localized["cause"] or (disease_row.get("description") or "").strip(),
            "possible_steps": default_checklist(class_name),
            "cause": localized["cause"],
            "cure": localized["cure"],
            "area_recommendation": area_match,
        }

    return catalog


def build_prediction_payload(class_name: str, confidence: float, image_url: str):
    catalog = build_catalog()
    item = catalog[class_name]
    crop = item["crop"]
    disease = item["disease"]
    area_recommendations = format_area_recommendation(item["area_recommendation"])
    category = category_for(class_name, item["area_recommendation"], item["cause"])

    is_healthy = class_name.endswith("___healthy")
    is_background = class_name == BACKGROUND_CLASS
    severity = "medium" if is_background else ("low" if is_healthy else ("high" if confidence >= 85 else "medium"))
    badge_variant = severity
    status_summary = "फोटो पुन्हा घ्या" if is_background else ("निरोगी" if is_healthy else f"रोग - {int(round(confidence))}%")
    status_code = "retake_photo" if is_background else ("healthy" if is_healthy else "disease")

    prevention_steps = default_checklist(class_name)

    chemical_steps = []
    if area_recommendations.get("chemical_product"):
        chemical = area_recommendations["chemical_product"]
        if area_recommendations.get("chemical_verification"):
            chemical = f"{chemical} ({area_recommendations['chemical_verification']})"
        chemical_steps.append(chemical)
    elif is_healthy:
        chemical_steps.append("निरोगी पिकासाठी रासायनिक उपचाराची गरज नाही.")
    else:
        chemical_steps.append(item["cure"])

    organic_steps = []
    if area_recommendations.get("organic_product"):
        organic = area_recommendations["organic_product"]
        if area_recommendations.get("organic_verification"):
            organic = f"{organic} ({area_recommendations['organic_verification']})"
        organic_steps.append(organic)
    elif is_background:
        organic_steps.append("कोणताही उपाय करण्यापूर्वी स्पष्ट प्रतिमेसह पुन्हा स्कॅन करा.")
    else:
        organic_steps.append(item["cure"])

    remedy_sections = {
        "chemical": chemical_steps,
        "organic": organic_steps,
        "preventive": prevention_steps[:3],
    }

    remedy = " ".join(
        [step for step in [chemical_steps[0] if chemical_steps else "", organic_steps[0] if organic_steps else ""] if step]
    )

    insights = {
        "likely_cause": item["cause"] or first_sentence(item["description"], "स्कॅन पाहून जवळील पाने तपासा."),
        "spray_time": "फवारणीची गरज नाही" if is_healthy else ("आधी फोटो पुन्हा घ्या" if is_background else "सकाळी लवकर किंवा संध्याकाळी"),
        "checklist": prevention_steps[:],
    }

    return {
        "class_name": class_name,
        "image_url": image_url,
        "crop": crop,
        "disease": disease,
        "marathi_name": item["title"],
        "category": category,
        "severity": severity,
        "confidence": int(round(confidence)),
        "cause": item["cause"] or item["description"],
        "remedy": remedy or item["cure"],
        "prevention": " ".join(prevention_steps),
        "prevention_steps": prevention_steps,
        "weather_note": weather_note_for(category, class_name),
        "remedy_sections": remedy_sections,
        "area_recommendations": area_recommendations,
        "badge_variant": badge_variant,
        "status_summary": status_summary,
        "status_code": status_code,
        "insights": insights,
        "report_payload": {"created_at": ""},
    }


def localize_prediction_payload(payload: dict):
    payload = dict(payload or {})
    class_name = payload.get("class_name") or infer_class_name(payload.get("crop", ""), payload.get("disease", ""))
    if not class_name:
        error_message = payload.get("marathi_name") or payload.get("cause") or "स्पष्ट निदान उपलब्ध नाही."
        localized = build_error_payload(error_message)
        localized["image_url"] = payload.get("image_url", "")
        localized["confidence"] = int(round(payload.get("confidence", 0) or 0))
        localized["report_payload"] = payload.get("report_payload", {"created_at": ""})
        return localized

    localized = build_prediction_payload(
        class_name,
        float(payload.get("confidence", 0) or 0),
        payload.get("image_url", ""),
    )
    localized["report_payload"] = payload.get("report_payload", localized["report_payload"])
    return localized


def build_library_view_model():
    catalog = build_catalog()
    items = []
    for class_name, item in catalog.items():
        if class_name == BACKGROUND_CLASS:
            continue
        items.append(
            {
                "crop": item["crop"],
                "disease": item["disease"],
                "description": item["cause"],
                "remedy": item["cure"],
            }
        )

    crop_filters = sorted({item["crop"] for item in items})
    return items, crop_filters
